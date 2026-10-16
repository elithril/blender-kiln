// Kiln Studio. Talks to server.py; the 3D view is viewer.js; the Checks tab reads checks.py.
// Notes go open → addressed (Claude changed the model and replied) → resolved (you
// checked it) or won't fix. Each note keeps a screenshot of the model as it was; when
// Claude marks one addressed, the page renders the same view of the new version
// beside it, so every note carries its own before and after.
//
// The layout follows the approved prototype: the side panels resize the view and fold
// into 60 px rails ([ ] \), the list header stays under 150 px, Compare is a split
// with a divider (one camera) or side by side, pins stick to the surface and follow
// the animation, and History is one chronological feed.
import { Viewer, Offscreen, Superseded } from './viewer.js';
import { t, tp, applyI18n, fmtN, fmtK, fmtB, fmtD, fmtLen, fmtPct, ago, stamp } from './i18n.js';

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const enc = encodeURIComponent;
const fileUrl = (rel, h) => '/files/' + rel.split('/').map(enc).join('/') + (h ? `?h=${h}` : '');
// Same as studiolib.asset_key.
const keyOf = (id) => id.replaceAll('%', '%25').replaceAll('~', '%7E').replaceAll('/', '~');
const frac = (a, b) => (b ? (a - b) / b : 0);
const sign = (n) => (n > 0 ? '+' : n < 0 ? '−' : '±');
const ACTIVE = new Set(['open', 'addressed']);
const SHADES = ['lit', 'unlit', 'clay', 'normals', 'uv', 'faces'];
const statusLabel = (s) => ({ open: t('open'), addressed: t('addressed'), resolved: t('resolved'), wontfix: t("won't fix") }[s] || s);
// kiln's phases (studiolib.PHASES); rig and animate show only when a build reports them.
const PHASES = ['config', 'brief', 'source', 'import', 'cleanup', 'texture', 'rig', 'animate', 'optimize', 'export'];
const OPTIONAL_PHASES = new Set(['rig', 'animate']);
const fmtTok = (r) => (!r ? '–' : r[0] === r[1] ? t('~{a} tokens', { a: fmtK(r[0]) }) : t('~{a}–{b} tokens', { a: fmtK(r[0]), b: fmtK(r[1]) }));

// ── personal preferences: this browser only ──────────────────────────────────

const PREFS_KEY = 'kiln-studio:prefs';
const prefs = (() => { try { return JSON.parse(localStorage.getItem(PREFS_KEY) || '{}') || {}; } catch { return {}; } })();
function savePrefs() { try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch { /* storage blocked: this session only */ } }
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* storage blocked */ } },
};

const state = {
  root: '', name: '', assets: [], byId: new Map(), batches: {},
  id: null, detail: null, variant: null, clientStats: null,
  tags: new Set(), noteFilter: 'active', pill: null,
  pinsOn: prefs.pins ?? true, hideFixed: !!prefs.hideFixed, hideBehind: !!prefs.hideBehind,
  pinning: false, draft: null, hl: null, editing: null, replying: null,
  compare: null, // { mode: 'split' | 'side', target: 'baseline' | variant label }
  cmpStats: null, cmpSrc: null,
  work: null, // which models a kiln command is on: studiolib.work_view
  group: prefs.group || 'folders', density: prefs.density || 'normal',
  pointerInList: false, pending: new Set(), closedGroups: new Set(store.get('kiln-studio:collapsed', [])),
  occl: new Map(), lastOccl: 0, rowSig: new Map(), listed: false,
  loadSeq: 0,
};
let seen = {};

// ── api ──────────────────────────────────────────────────────────────────────

async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(path, {
    method, headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `${res.status} ${res.statusText}`);
  return data;
}
const assetApi = (id, rest = '', opts) => api(`/api/asset/${enc(id)}${rest}`, opts);

// ── panels: they resize the view, and fold into rails ────────────────────────

const left = $('#left'), right = $('#right'), stage = $('#stage');
const narrow = () => matchMedia('(max-width: 760px)').matches;
const isOpen = (el) => !el.classList.contains('collapsed');
function setPanel(el, open, save = true) {
  el.classList.toggle('collapsed', !open);
  if (save && !narrow()) { prefs[el.id + 'Open'] = open; savePrefs(); }
  // On a narrow screen a panel lies over the view: one at a time.
  if (narrow() && open) (el === left ? right : left).classList.add('collapsed');
}
const togglePanel = (el) => setPanel(el, !isOpen(el));
function initPanels() {
  if (narrow()) { setPanel(left, false, false); setPanel(right, false, false); }
  else { setPanel(left, prefs.leftOpen ?? true, false); setPanel(right, prefs.rightOpen ?? true, false); }
}
matchMedia('(max-width: 760px)').addEventListener('change', () => initPanels());
// The view changed size: fit the model again once the panel has finished moving.
for (const el of [left, right]) {
  el.addEventListener('transitionend', (e) => { if (e.target === el && e.propertyName === 'width' && viewer.a.model) viewer.frame(); });
}
let reframeT;
addEventListener('resize', () => { clearTimeout(reframeT); reframeT = setTimeout(() => viewer.a.model && viewer.frame(), 250); });
$$('[data-toggle]').forEach((b) => (b.onclick = () => togglePanel(b.dataset.toggle === 'left' ? left : right)));
document.addEventListener('pointerdown', (e) => {
  if (!narrow()) return;
  for (const el of [left, right]) if (isOpen(el) && !el.contains(e.target) && !e.target.closest('dialog')) setPanel(el, false, false);
});

// ── viewer ───────────────────────────────────────────────────────────────────

const viewer = new Viewer($('#view'));
viewer.fmtLen = fmtLen;
for (const k of ['shade', 'wire', 'grid', 'bounds', 'bg']) if (prefs[k] !== undefined) viewer.opts[k] = prefs[k];
stage.dataset.bg = viewer.opts.bg;
let offscreen = null;
const off = () => (offscreen ||= new Offscreen());

// Pins and labels move when the view or the pose does; whether a pin is behind the
// model is asked again until one pass has run after the last move.
let pinsDirty = true, occlDirty = true;
viewer.onChange = () => { pinsDirty = occlDirty = true; };
viewer.onFrame = () => {
  const moving = viewer.playing && viewer.a.mixer;
  if (moving) occlDirty = true;
  if (pinsDirty || moving || occlDirty) { placePins(); placeLabels(); pinsDirty = false; }
};
let scrubbing = false;
viewer.onAnimate = () => {
  const d = viewer.clipDuration;
  if (!d) return;
  const tm = viewer.clipTime % d;
  if (!scrubbing) $('#a-time').value = tm / d;
  $('#a-read').textContent = `${fmtD(tm, 2)} / ${fmtD(d, 2)} s`;
};

function syncToolbar() {
  const o = viewer.opts;
  $$('#toolbar [data-shade]').forEach((b) => { b.classList.toggle('on', b.dataset.shade === o.shade); b.setAttribute('aria-checked', String(b.dataset.shade === o.shade)); });
  $$('#toolbar [data-opt]').forEach((b) => { b.classList.toggle('on', !!o[b.dataset.opt]); b.setAttribute('aria-pressed', String(!!o[b.dataset.opt])); });
  $('#t-bg').textContent = `${t('Bg')} · ${{ dark: t('Dark'), mid: t('Mid'), light: t('Light') }[o.bg]}`;
  $('#t-compare').classList.toggle('on', !!state.compare);
  $('#t-compare').setAttribute('aria-pressed', String(!!state.compare));
  const eye = $('#t-pins');
  eye.classList.toggle('on', state.pinsOn);
  eye.classList.toggle('filtered', state.pinsOn && (state.hideFixed || state.hideBehind));
  eye.setAttribute('aria-pressed', String(state.pinsOn));
  eye.setAttribute('aria-label', state.pinsOn ? t('Hide pins (P)') : t('Show pins (P)'));
  eye.title = t('Pins (P)');
  $('#pm-all').setAttribute('aria-pressed', String(!state.pinsOn));
  $('#pm-fixed').setAttribute('aria-pressed', String(state.hideFixed));
  $('#pm-behind').setAttribute('aria-pressed', String(state.hideBehind));
  $('#t-pin').classList.toggle('on', state.pinning);
  $$('#cmp-mode button').forEach((b) => b.classList.toggle('on', b.dataset.m === state.compare?.mode));
}

function setOpt(k, v) {
  viewer.set(k, v);
  prefs[k] = v; savePrefs();
  if (k === 'bg') stage.dataset.bg = v;
  syncToolbar();
}
$$('#toolbar [data-shade]').forEach((b) => (b.onclick = () => setOpt('shade', b.dataset.shade)));
$$('#toolbar [data-opt]').forEach((b) => (b.onclick = () => setOpt(b.dataset.opt, !viewer.opts[b.dataset.opt])));
$('#t-bg').onclick = () => setOpt('bg', { dark: 'mid', mid: 'light', light: 'dark' }[viewer.opts.bg]);
$$('#views [data-view]').forEach((b) => (b.onclick = () => viewer.view(b.dataset.view)));
$('#t-frame').onclick = () => viewer.frame();
$('#t-keys').onclick = () => showKeys();
const cycleShade = (d) => setOpt('shade', SHADES[(SHADES.indexOf(viewer.opts.shade) + d + SHADES.length) % SHADES.length]);

// the pins' eye, and its menu
function togglePins() { state.pinsOn = !state.pinsOn; prefs.pins = state.pinsOn; savePrefs(); syncToolbar(); renderPins(); }
$('#t-pins').onclick = togglePins;
$('#pm-all').onclick = togglePins;
// Picking which pins to see also brings them back if they were hidden.
function setPinFilter(k, on) {
  state[k] = on; prefs[k] = on;
  if (on) state.pinsOn = prefs.pins = true;
  savePrefs(); syncToolbar(); renderPins();
}
$('#pm-fixed').onclick = () => setPinFilter('hideFixed', !state.hideFixed);
$('#pm-behind').onclick = () => setPinFilter('hideBehind', !state.hideBehind);

// ── toast, hint, dialogs ─────────────────────────────────────────────────────

let toastTimer;
// msg is HTML: whatever comes from a file or the user goes through esc() first.
function toast(msg, kind = '', ms = 3800) {
  const el = $('#toast');
  el.innerHTML = msg;
  el.className = 'show ' + kind;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.className = kind), ms);
}
function hint(msg) { $('#hint').hidden = !msg; $('#hint').textContent = msg || ''; }

function confirmDialog(text, ok = t('OK')) {
  const d = $('#confirm');
  $('p', d).textContent = text;
  $('button[value=ok]', d).textContent = ok;
  d.returnValue = '';
  d.showModal();
  return new Promise((res) => d.addEventListener('close', () => res(d.returnValue === 'ok'), { once: true }));
}

function lightbox(items, extra = '') {
  const fig = $('#lightbox figure');
  fig.innerHTML = items.map((it) => `<div><img src="${esc(it.src)}" alt=""><figcaption>${esc(it.caption || '')}</figcaption></div>`).join('');
  $('#lightbox .lb-extra').innerHTML = extra;
  $('#lightbox').showModal();
}

async function textDialog(title, rel) {
  const d = $('#textbox');
  $('h3', d).textContent = title;
  $('pre', d).textContent = t('Loading…');
  d.showModal();
  try { $('pre', d).textContent = await (await fetch(fileUrl(rel))).text(); } catch (e) { $('pre', d).textContent = String(e); }
}

async function copy(text) {
  try { await navigator.clipboard.writeText(text); toast(t('Copied {x}', { x: `<span class="mono">${esc(text)}</span>` }), 'ok'); }
  catch { toast(t('Copy this: {x}', { x: `<span class="mono">${esc(text)}</span>` })); }
}

// ── the model list ───────────────────────────────────────────────────────────

const counts = (a) => a.counts || { open: 0, addressed: 0, resolved: 0, wontfix: 0 };
const isBuilding = (a) => a.live?.state === 'building';
const dotOf = (a) => state.work?.dots[a.id]?.state;
const isNew = (a) => !!(seen[a.id] && seen[a.id] !== a.variants[0]?.hash && a.id !== state.id);
const catOf = (a) => a.category || '';

async function fetchAssets() {
  const data = await api('/api/assets');
  const before = new Map(state.byId);
  state.root = data.root;
  state.name = data.name;
  state.assets = data.assets;
  state.byId = new Map(data.assets.map((a) => [a.id, a]));
  state.batches = data.batches || {};
  state.work = data.work || null;
  if (!Object.keys(seen).length) seen = store.get(`kiln-studio:seen:${data.root}`, {});
  $('#project').textContent = data.root;
  $('#project').title = data.root;
  $('#logo').title = `Kiln Studio · ${data.root}`;
  document.title = `${data.name} · Kiln Studio`;
  renderTags();
  renderStrip();
  renderWork();
  // The same models in the same groups: patch the rows that changed, in place (or
  // move them, in State mode). Otherwise draw the list again.
  const sameSet = before.size === state.byId.size && [...state.byId.keys()].every((id) => before.has(id));
  const sameGroups = sameSet && state.assets.every((a) => catOf(a) === catOf(before.get(a.id)));
  if (state.listed && sameGroups) {
    const ids = state.assets.filter((a) => state.rowSig.get(a.id) !== rowSig(a)).map((a) => a.id);
    if (ids.length) changed(ids);
  } else {
    renderList();
  }
  renderEmpty();
  queuePendingShots();
}

// What a row shows: when it changes, the row is redrawn.
const rowSig = (a) => JSON.stringify([counts(a), a.live?.state, a.live?.phase, a.thumb, a.variants[0]?.hash, a.variants.length, a.tris, dotOf(a), isNew(a), a.tags]);

function markSeen(a) {
  if (!a) return;
  seen[a.id] = a.variants[0]?.hash;
  store.set(`kiln-studio:seen:${state.root}`, seen);
}

function renderTags() {
  const all = [...new Set(state.assets.flatMap((a) => a.tags))].sort();
  for (const tg of [...state.tags]) if (!all.includes(tg)) state.tags.delete(tg);
  $('#tagbar').innerHTML = all.map((tg) => `<button class="tag${state.tags.has(tg) ? ' on' : ''}" data-tag="${esc(tg)}" aria-pressed="${state.tags.has(tg)}">#${esc(tg)}</button>`).join('');
  $('#tagbar').hidden = !all.length;
  $$('#tagbar .tag').forEach((b) => (b.onclick = () => { const tg = b.dataset.tag; state.tags.has(tg) ? state.tags.delete(tg) : state.tags.add(tg); renderTags(); renderList(); }));
}

function visibleAssets() {
  const q = $('#search').value.trim().toLowerCase();
  const f = state.pill || $('#filter').value;
  const keep = (a) => {
    if (q && !(a.id.toLowerCase().includes(q) || a.tags.some((x) => x.includes(q)) || catOf(a).toLowerCase().includes(q))) return false;
    for (const tg of state.tags) if (!a.tags.includes(tg)) return false;
    const c = counts(a), any = Object.values(c).some((n) => n > 0);
    if (f === 'open') return c.open > 0;
    if (f === 'addressed') return c.addressed > 0;
    if (f === 'notes') return any;
    if (f === 'clean') return !any;
    if (f === 'working') return ['active', 'queued'].includes(dotOf(a));
    if (f === 'building') return isBuilding(a);
    return true;
  };
  const cmp = {
    name: (x, y) => x.name.localeCompare(y.name),
    updated: (x, y) => y.updated - x.updated,
    tris: (x, y) => (y.tris || 0) - (x.tris || 0),
  }[$('#sort').value] || ((x, y) => x.name.localeCompare(y.name));
  return state.assets.filter(keep).sort(cmp);
}

const SECTIONS = [
  ['works', 'Claude works', (a) => ['active', 'queued'].includes(dotOf(a))],
  ['building', 'Building', (a) => isBuilding(a)],
  ['check', 'To check', (a) => counts(a).addressed > 0 || dotOf(a) === 'done'],
  ['open', 'Open notes', (a) => counts(a).open > 0],
  ['clear', 'Nothing to do', () => true],
];
function groupsOf(items) {
  const groups = new Map();
  if (state.group === 'state') {
    for (const [k, label] of SECTIONS) groups.set(k, { label: t(label), items: [] });
    for (const a of items) groups.get(SECTIONS.find((s) => s[2](a))[0]).items.push(a);
    for (const [k, g] of groups) if (!g.items.length) groups.delete(k);
  } else {
    for (const a of [...items].sort((x, y) => catOf(x).localeCompare(catOf(y)))) {
      const c = catOf(a);
      if (!groups.has(c)) groups.set(c, { label: c || t('project root'), items: [] });
      groups.get(c).items.push(a);
    }
    for (const g of groups.values()) g.items.sort((x, y) => items.indexOf(x) - items.indexOf(y));
  }
  return groups;
}

function groupHead(key, g) {
  const open = g.items.reduce((s, a) => s + counts(a).open, 0);
  const b = state.group === 'folders' && state.batches[key];
  const est = b ? `<span class="est" title="${esc(t('Batch {name}: the wizard\'s token estimate for its {n} assets, ±50%. {left} left to run: {rest}.', { name: b.name, n: b.assets, left: b.remaining.assets, rest: fmtTok(b.remaining.range) }))}">${esc(fmtTok(b.range).replace(t(' tokens'), ' tok'))}</span>` : '';
  return `<svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg><span class="gl" title="${esc(g.label)}">${esc(g.label)}</span>${est}<span class="gn">${fmtN(g.items.length)}${open && state.group === 'folders' ? ` · <span class="o">${esc(t('{n} open', { n: fmtN(open) }))}</span>` : ''}</span>`;
}

function renderList() {
  const items = visibleAssets(), list = $('#list');
  list.className = (state.work ? 'working ' : '') + (state.density === 'compact' ? 'compact' : '');
  list.innerHTML = '';
  const filtering = $('#search').value || state.pill || $('#filter').value !== 'all' || state.tags.size;
  for (const [key, g] of groupsOf(items)) {
    const sec = document.createElement('section');
    const closed = !filtering && state.closedGroups.has(key) && !g.items.some((a) => a.id === state.id);
    sec.className = 'group' + (closed ? ' closed' : '');
    sec.dataset.key = key;
    sec.innerHTML = `<button class="ghead" aria-expanded="${!closed}">${groupHead(key, g)}</button><div class="gbody"></div>`;
    $('.ghead', sec).onclick = () => {
      const isClosed = sec.classList.toggle('closed');
      isClosed ? state.closedGroups.add(key) : state.closedGroups.delete(key);
      $('.ghead', sec).setAttribute('aria-expanded', String(!isClosed));
      store.set('kiln-studio:collapsed', [...state.closedGroups]);
    };
    for (const a of g.items) $('.gbody', sec).appendChild(itemEl(a));
    list.appendChild(sec);
  }
  if (!items.length && state.assets.length) list.innerHTML = `<p class="empty-list">${esc(t('Nothing matches. Clear the search, tags or filter.'))}</p>`;
  state.rowSig = new Map(state.assets.map((a) => [a.id, rowSig(a)]));
  state.listed = true;
  state.pending.clear();
  $('#resort').hidden = true;
  renderRail(items);
}

function itemInner(a) {
  const c = counts(a), dot = dotOf(a), building = isBuilding(a), v = a.variants[0];
  const n = a.variants.length;
  const sub = building ? `<span class="bld">${esc(t('building · {phase}', { phase: a.live.phase || t('starting') }))}</span>`
    : esc([a.tris != null ? t('{n} tris', { n: fmtK(a.tris) }) : v.ext.slice(1).toUpperCase(),
      n > 1 ? (a.kiln ? tp(n, '{n} stage', '{n} stages') : tp(n, '{n} file', '{n} files')) : fmtB(v.size)].join(' · '));
  const dotT = dot && workTitle(state.work.dots[a.id]);
  return `<img class="thumb" alt="" ${a.thumb ? `src="${esc(fileUrl(a.thumb))}"` : ''}>
    <div class="meta"><div class="name" title="${esc(a.id)}">${esc(a.name)}</div><div class="sub">${sub}</div></div>
    <span class="badges">${isNew(a) ? `<span class="badge new" title="${esc(t('Changed since you last looked'))}">${esc(t('new'))}</span>` : ''}${building && dot !== 'active' ? `<i class="bmark" title="${esc(t('kiln is building it: open it to watch'))}"></i>` : ''}${c.open ? `<span class="badge open" title="${esc(tp(c.open, '{n} open note', '{n} open notes'))}">${fmtN(c.open)}</span>` : ''}${c.addressed ? `<span class="badge addressed" title="${esc(tp(c.addressed, '{n} to check: Claude addressed it', '{n} to check: Claude addressed them'))}">${fmtN(c.addressed)}</span>` : ''}</span>
    <span class="wslot">${dot ? `<span class="wdot ${dot}" role="img" aria-label="${esc(dotT)}" title="${esc(dotT)}"></span>` : ''}</span>`;
}
function itemLabel(a) {
  const c = counts(a);
  return [a.name, c.open && t('{n} open', { n: c.open }), c.addressed && t('{n} to check', { n: c.addressed }),
    isBuilding(a) && t('building'), isNew(a) && t('new')].filter(Boolean).join(', ');
}
function itemEl(a) {
  const el = document.createElement('div');
  el.className = 'item' + (a.id === state.id ? ' sel' : '');
  el.dataset.id = a.id;
  el.tabIndex = 0;
  el.setAttribute('role', 'button');
  el.setAttribute('aria-label', itemLabel(a));
  el.innerHTML = itemInner(a);
  el.onclick = () => go(a.id);
  el.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(a.id); } };
  if (!a.thumb) thumbObserver.observe(el);
  return el;
}

function renderRail(items = visibleAssets()) {
  $('#lrail').innerHTML = items.map((a) => {
    const c = counts(a), dot = dotOf(a);
    const cnt = c.addressed ? `<span class="cnt addressed">${fmtN(c.addressed)}</span>` : c.open ? `<span class="cnt open">${fmtN(c.open)}</span>` : isNew(a) ? `<span class="cnt new" aria-label="${esc(t('new'))}">•</span>` : '';
    return `<button class="rbtn${a.id === state.id ? ' sel' : ''}" data-id="${esc(a.id)}" aria-label="${esc(itemLabel(a))}" title="${esc(a.name)}">${a.thumb ? `<img src="${esc(fileUrl(a.thumb))}" alt="">` : '<span class="ph"></span>'}${cnt}${isBuilding(a) ? '<i class="bmark"></i>' : ''}${dot ? `<span class="wdot ${dot}"></span>` : ''}</button>`;
  }).join('');
  $$('#lrail .rbtn').forEach((b) => (b.onclick = () => go(b.dataset.id)));
}

// A state change on some models: in Folders mode rows stay put and update in place;
// in State mode they move to their section (FLIP), deferred while the pointer is over
// the list so nothing jumps under it.
function changed(ids) {
  renderStrip();
  renderWork();
  if (state.group === 'state') {
    if (state.pointerInList) {
      ids.forEach((id) => state.pending.add(id));
      $('#resort').hidden = false;
      $('#resort-btn').textContent = tp(state.pending.size, '{n} change · re-sort', '{n} changes · re-sort');
      for (const id of ids) patchRow(id);
      renderRail();
      return;
    }
    flipRender(ids);
    return;
  }
  for (const id of ids) patchRow(id);
  const visible = new Set(visibleAssets().map((a) => a.id));
  for (const sec of $$('#list .group')) {
    const items = state.assets.filter((a) => catOf(a) === sec.dataset.key && visible.has(a.id));
    if (items.length) $('.ghead', sec).innerHTML = groupHead(sec.dataset.key, { label: sec.dataset.key || t('project root'), items });
  }
  renderRail();
}
function patchRow(id, flash = true) {
  const el = $(`#list .item[data-id="${CSS.escape(id)}"]`), a = state.byId.get(id);
  if (a) state.rowSig.set(id, rowSig(a));
  if (!el || !a) return;
  el.innerHTML = itemInner(a);
  el.setAttribute('aria-label', itemLabel(a));
  if (!a.thumb) thumbObserver.observe(el);
  if (flash) { el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash'); }
}
function flipRender(ids = []) {
  const first = new Map($$('#list .item').map((el) => [el.dataset.id, el.getBoundingClientRect().top]));
  renderList();
  for (const el of $$('#list .item')) {
    const f = first.get(el.dataset.id);
    if (f == null) continue;
    const dy = f - el.getBoundingClientRect().top;
    if (!dy) continue;
    el.style.transform = `translateY(${dy}px)`;
    el.style.transition = 'none';
    requestAnimationFrame(() => { el.style.transition = 'transform .45s cubic-bezier(.2,.7,.2,1)'; el.style.transform = ''; });
  }
  for (const id of ids) $(`#list .item[data-id="${CSS.escape(id)}"]`)?.classList.add('flash');
}
$('#list').addEventListener('pointerenter', () => (state.pointerInList = true));
$('#list').addEventListener('pointerleave', () => { state.pointerInList = false; if (state.pending.size) flipRender([...state.pending]); });
$('#resort-btn').onclick = () => flipRender([...state.pending]);

// The tracking strip: what needs you, across the project. Each pill filters the list.
function renderStrip() {
  const tot = state.assets.reduce((s, a) => { const c = counts(a); s.addressed += c.addressed; s.open += c.open; return s; }, { addressed: 0, open: 0 });
  const vals = {
    addressed: tot.addressed, open: tot.open,
    working: Object.values(state.work?.dots || {}).filter((d) => d.state !== 'done').length,
    building: state.assets.filter(isBuilding).length,
  };
  for (const p of $$('#strip .pill')) {
    const k = p.dataset.pill, b = $('b', p), v = fmtN(vals[k]);
    if (b.textContent !== v) { b.textContent = v; p.classList.remove('bump'); void p.offsetWidth; p.classList.add('bump'); }
    p.classList.toggle('zero', !vals[k]);
    p.classList.toggle('on', state.pill === k);
    p.setAttribute('aria-pressed', String(state.pill === k));
  }
}
$$('#strip .pill').forEach((p) => (p.onclick = () => { state.pill = state.pill === p.dataset.pill ? null : p.dataset.pill; renderStrip(); renderList(); }));

// ── what kiln is working on ──────────────────────────────────────────────────
// A kiln command run on models here reports them (studio.py work): a dot per model,
// waiting, breathing while kiln is on it, green once done until the user has looked.

function workTitle(d) {
  const base = { queued: t('Waiting: kiln works on it later in this run'), active: t('Kiln is working on it'), done: t('Kiln is done with it: open it to check') }[d.state];
  return [base, d.text].filter(Boolean).join(' · ');
}

function renderWork() {
  const w = state.work, bar = $('#workline');
  bar.hidden = !w;
  $('#list').classList.toggle('working', !!w);
  if (!w) return;
  const name = (id) => state.byId.get(id)?.name || id.split('/').pop();
  const done = Object.values(w.dots).filter((d) => d.state === 'done').length;
  if (w.running) {
    bar.innerHTML = `<span class="wdot active"></span><button class="go" ${w.active ? `data-id="${esc(w.active)}"` : ''} title="${esc(t('Open the model kiln is on'))}">${esc(t('Kiln'))}${w.label ? ` · ${esc(w.label)}` : ''} · ${esc(t('{i} of {n}', { i: Math.min(w.done + 1, w.total), n: w.total }))}${w.active ? ` · <b>${esc(name(w.active))}</b>` : ''}</button>`;
  } else {
    bar.innerHTML = `<span class="wdot done"></span><span>${esc(t('Kiln is done · {n} to check', { n: done }))}</span><button class="clear" title="${esc(t('Clear the green dots without opening each model'))}">${esc(t('Clear'))}</button>`;
  }
  const g = $('.go', bar);
  if (g) g.onclick = () => g.dataset.id && go(g.dataset.id);
  const clear = $('.clear', bar);
  if (clear) clear.onclick = () => checkWork(null);
}

// The user looked at these models (null: all of them): their green dots go.
async function checkWork(ids) {
  const w = state.work;
  if (!w) return;
  const done = Object.entries(w.dots).filter(([id, d]) => d.state === 'done' && (!ids || ids.includes(id))).map(([id]) => id);
  if (!done.length) return;
  for (const id of done) delete w.dots[id];
  if (!w.running && !Object.keys(w.dots).length) state.work = null;
  renderWork();
  changed(done.filter((id) => state.byId.has(id)));
  try { await api('/api/work/check', { method: 'POST', body: { assets: ids ? done : null } }); } catch { /* the next work event says */ }
}

function onWork(next, prev) {
  state.work = next;
  const ids = new Set([...Object.keys(prev?.dots || {}), ...Object.keys(next?.dots || {})]);
  renderWork();
  changed([...ids].filter((id) => state.byId.has(id)));
  if (!next) return;
  const name = (id) => esc(state.byId.get(id)?.name || id.split('/').pop());
  if (next.running && next.active && next.active !== prev?.active) {
    const finished = prev?.active && next.dots[prev.active]?.state === 'done';
    toast(finished ? t('Kiln is done with {a} · now on {b}', { a: `<b>${name(prev.active)}</b>`, b: `<b>${name(next.active)}</b>` })
      : t('Kiln is working on {a}', { a: `<b>${name(next.active)}</b>` }), 'ok');
    // Nothing open yet: open the model kiln is on.
    if (!state.id) go(next.active);
  } else if (!next.running && prev?.running && !next.stale) {
    const n = Object.values(next.dots).filter((d) => d.state === 'done').length;
    toast(tp(n, 'Kiln is done: {n} model to check', 'Kiln is done: {n} models to check'), 'ok');
  }
}

const thumbObserver = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    thumbObserver.unobserve(e.target);
    const a = state.byId.get(e.target.dataset.id);
    if (a && !a.thumb) queueThumb(a.id, a.variants[0]);
  }
}, { root: $('#list'), rootMargin: '300px' });

// the View popover: group, density, filter, sort
const pop = $('#viewpop');
function setPop(open) { pop.hidden = !open; $('#view-btn').setAttribute('aria-expanded', String(open)); $('#view-btn').classList.toggle('on', open); }
$('#view-btn').onclick = (e) => { e.stopPropagation(); setPop(pop.hidden); };
document.addEventListener('click', (e) => { if (!pop.hidden && !pop.contains(e.target) && e.target !== $('#view-btn')) setPop(false); });
function segInit(id, key, after) {
  const seg = $(id);
  const sync = () => $$('button', seg).forEach((b) => b.classList.toggle('on', b.dataset.v === state[key]));
  $$('button', seg).forEach((b) => (b.onclick = () => { state[key] = b.dataset.v; prefs[key] = state[key]; savePrefs(); sync(); after(); }));
  sync();
  return sync;
}
const syncGroup = segInit('#pg-group', 'group', () => flipRender());
const syncDensity = segInit('#pg-density', 'density', () => renderList());
$('#filter').onchange = () => { state.pill = null; renderStrip(); renderList(); };
$('#sort').onchange = () => { prefs.sort = $('#sort').value; savePrefs(); renderList(); };
if (prefs.sort) $('#sort').value = prefs.sort;
$('#search').oninput = () => renderList();

function go(id) {
  if (id === state.id) return;
  location.hash = id.split('/').map(enc).join('/');
}

// ↑ ↓: the model above or below, in the order the list shows them.
function step(d) {
  const order = $$('#list .item').map((el) => el.dataset.id);
  if (!order.length) return;
  const i = order.indexOf(state.id);
  go(order[(i + d + order.length) % order.length] ?? order[0]);
}

// ── opening a model ──────────────────────────────────────────────────────────

async function openAsset(id) {
  const a = state.byId.get(id);
  if (!a) { toast(t('No model "{id}" in this project', { id: esc(id) }), 'warn'); return; }
  if (state.compare) await setCompare(null);
  cancelDraft(false);
  const leaving = state.id;
  const wasNew = isNew(a);
  state.id = id;
  state.hl = null;
  state.editing = state.replying = null;
  $$('#list .item').forEach((e) => e.classList.toggle('sel', e.dataset.id === id));
  $('#list .item.sel')?.scrollIntoView({ block: 'nearest' });
  renderEmpty();
  $('#asset-name').textContent = a.name;
  $('#loading-t').textContent = t('Loading {name}…', { name: a.name });
  await fetchDetail();
  if (state.id !== id) return;
  const keep = state.detail.variants.find((v) => v.label === state.variant);
  await loadVariant(keep ? keep.label : state.detail.variants[0].label, { keepCamera: false });
  markSeen(a);
  if (wasNew) patchRow(id, false);
  if (leaving && state.byId.get(leaving)) patchRow(leaving, false);
  renderRail();
  // Opening a model kiln finished, or leaving the one you watched it finish: checked.
  checkWork([id, leaving].filter(Boolean));
  for (const v of state.detail.variants) if (!state.detail.thumbs.includes(v.hash)) queueThumb(id, v);
  queueAfterShots(state.detail);
  reportSelection();
}

async function fetchDetail() {
  const id = state.id;
  const d = await assetApi(id);
  if (id !== state.id) return;
  state.detail = d;
  const a = state.byId.get(id);
  if (a) Object.assign(a, { counts: d.counts, tags: d.tags, category: d.category, thumb: d.thumb, variants: d.variants.map(({ stats, ...v }) => v) });
  renderAll();
}

function currentVariant() {
  return state.detail?.variants.find((v) => v.label === state.variant) || state.detail?.variants[0];
}

async function loadVariant(label, { keepCamera = true } = {}) {
  state.variant = label;
  const v = currentVariant();
  const seq = ++state.loadSeq;
  if (!keepCamera) $('#loading').hidden = false;
  try {
    const stats = await viewer.load(fileUrl(v.file, v.hash), v.ext, { keepCamera });
    if (seq !== state.loadSeq) return;
    state.clientStats = stats;
    state.occl.clear();
    if (!keepCamera) viewer.frame(VIEW_DIRS[prefs.view || 'iso'], { animate: false });
    if (state.compare) await loadCompareTarget();
  } catch (e) {
    if (e instanceof Superseded) return;
    console.warn(e);
    // 409: re-exported while loading; the live event that follows loads the new one.
    if (seq === state.loadSeq && !/409/.test(String(e.message))) { state.clientStats = null; toast(t('Could not load {f}: {e}', { f: esc(v.file), e: esc(e.message || e) }), 'warn', 8000); }
  } finally {
    if (seq === state.loadSeq) $('#loading').hidden = true;
  }
  setupAnimBar();
  renderAll();
  reportSelection();
}
const VIEW_DIRS = { front: [0, 0, 1], back: [0, 0, -1], right: [1, 0, 0], left: [-1, 0, 0], top: [0, 1, 0.0001], iso: [1, 0.7, 1.3] };
for (const k in VIEW_DIRS) VIEW_DIRS[k] = new (viewer.camera.position.constructor)(...VIEW_DIRS[k]);

function renderAll() {
  if (!state.detail) return;
  renderTitle();
  renderNotes();
  renderPins();
  renderDetails();
  renderChecks();
  renderHistory();
  renderBuild();
  syncToolbar();
  $('#t-skel').hidden = !state.clientStats?.skinned;
  const compareOk = compareTargets().length > 0;
  $('#t-compare').disabled = !compareOk;
  $('#t-compare').title = compareOk ? t('Compare with the previous version (C)') : t('No previous version kept for this model');
}

// The middle when no model is open: what to do next.
function renderEmpty() {
  const none = !state.id;
  $('#empty').hidden = !none;
  $('#topbar').hidden = $('#views').hidden = $('#bottom').hidden = none;
  if (!none) return;
  $('#empty').innerHTML = state.assets.length
    ? `<div><p class="big">${esc(t('No model picked'))}</p><p>${esc(t('Choose one on the left. Models re-exported by Claude show up here on their own, and a model kiln is building opens here as it is built.'))}</p></div>`
    : `<div><p class="big">${esc(t('No models in this folder yet'))}</p><p>${esc(t('Export a .glb, .gltf, .fbx or .obj anywhere under it and it appears here.'))}</p></div>`;
}

function renderTitle() {
  const d = state.detail, v = currentVariant(), s = state.clientStats;
  $('#asset-name').textContent = d.name;
  $('#asset-name').title = d.id;
  const stages = $('#stages');
  stages.hidden = d.variants.length < 2;
  stages.innerHTML = d.variants.map((x) => `<button role="radio" aria-checked="${x.label === v.label}" class="${x.label === v.label ? 'on' : ''}" data-v="${esc(x.label)}" title="${esc(x.file)}">${esc(x.label)}</button>`).join('');
  $$('button', stages).forEach((b) => (b.onclick = () => { if (b.dataset.v !== state.variant) loadVariant(b.dataset.v); }));
  const tris = v.stats?.tris ?? s?.tris;
  const dims = v.stats?.dimensions_blender || s?.dims;
  const parts = [`<span>${esc(t('{n} tris', { n: fmtN(tris) }))}</span>`, `<span>${fmtB(v.size)}</span>`];
  if (dims) parts.push(`<span title="${esc(t('Blender X × Y × Z'))}">${fmtLen(dims[0])} × ${fmtLen(dims[1])} × ${fmtLen(dims[2])}</span>`);
  if (d.variants.length > 1 && v.label !== d.variants[0].label) parts.push(`<span>${esc(v.label)}</span>`);
  $('#stats').innerHTML = parts.join('<span class="sep">·</span>');
}

// ── build strip: the phases of the build kiln is running ─────────────────────

function renderBuild() {
  const live = state.detail?.live;
  const bar = $('#buildbar');
  const on = live?.state === 'building';
  bar.hidden = !on;
  stage.classList.toggle('building', on);
  if (!on) return;
  const steps = live.steps || [];
  const reported = new Set(steps.map((x) => x.phase).filter(Boolean));
  const cur = PHASES.indexOf(live.phase);
  const shown = PHASES.filter((p) => !OPTIONAL_PHASES.has(p) || reported.has(p));
  $('#phases').innerHTML = shown.map((p) => {
    const i = PHASES.indexOf(p);
    return `<li class="${i < cur ? 'done' : i === cur ? 'cur' : ''}" ${i === cur ? 'aria-current="step"' : ''}>${esc(t(p))}</li>`;
  }).join('');
  const last = steps[steps.length - 1];
  $('#bstep').textContent = [last?.text, ago(live.updated)].filter(Boolean).join(' · ');
  $('#bstep').title = t('Started {when}', { when: stamp(live.started) });
}
// "12 s ago" goes stale on its own.
setInterval(() => { if (state.detail?.live?.state === 'building') renderBuild(); }, 15000);

// ── compare: the previous version or another stage, one camera ───────────────

function compareTargets() {
  const d = state.detail, v = currentVariant(), out = [];
  if (!d) return out;
  if (d.baseline) out.push({ value: 'baseline', label: t('Previous · {when}', { when: ago(d.baseline.at) }) });
  for (const x of d.variants) if (x.label !== v.label) out.push({ value: x.label, label: x.label });
  return out;
}

async function setCompare(mode, target) {
  if (mode && !compareTargets().length) {
    toast(t('Nothing to compare yet. Studio keeps the previous version when you add a note; Details → Keep this version does it now.'), 'warn', 6500);
    return;
  }
  const was = state.compare;
  state.compare = mode ? { mode, target: target || was?.target } : null;
  viewer.setCompare(mode || null);
  $('#cmpbar').hidden = !mode;
  $('#split').hidden = mode !== 'split';
  $('#sidediv').hidden = mode !== 'side';
  $('#lab-prev').hidden = $('#lab-cur').hidden = !mode;
  syncToolbar();
  placeSplit();
  if (mode && (!was || target)) await loadCompareTarget();
  if (!mode) { state.cmpStats = state.cmpSrc = null; }
  renderPins();
}

async function loadCompareTarget() {
  const d = state.detail;
  const targets = compareTargets();
  if (!targets.length) { setCompare(null); return; }
  if (!targets.some((x) => x.value === state.compare.target)) state.compare.target = targets[0].value;
  const tg = state.compare.target;
  const src = tg === 'baseline'
    ? { label: t('Previous'), file: d.baseline.file, hash: d.baseline.hash, ext: d.baseline.name.slice(d.baseline.name.lastIndexOf('.')).toLowerCase(), size: d.baseline.size, at: d.baseline.at }
    : { ...d.variants.find((x) => x.label === tg) };
  const sel = $('#cmp-select');
  sel.innerHTML = targets.map((x) => `<option value="${esc(x.value)}"${x.value === tg ? ' selected' : ''}>${esc(x.label)}</option>`).join('');
  sel.hidden = targets.length < 2;
  sel.onchange = (e) => setCompare(state.compare.mode, e.target.value);
  $('#cmp-delta').textContent = t('Loading the other version…');
  try {
    state.cmpStats = await viewer.loadCompare(fileUrl(src.file, src.hash), src.ext);
    state.cmpSrc = src;
    renderDelta();
  } catch (e) {
    if (!(e instanceof Superseded)) toast(t('Could not load {f}: {e}', { f: esc(src.file), e: esc(e.message) }), 'warn');
  }
}

// Δ: the current file against the one compared, read from both files.
function renderDelta() {
  const p = state.cmpStats, c = state.clientStats, src = state.cmpSrc, v = currentVariant();
  if (!p || !c || !src) return;
  const dt = c.tris - p.tris, db = v.size - src.size, dh = c.dims[2] - p.dims[2];
  const cls = (n) => (n > 0 ? 'up' : n < 0 ? 'down' : '');
  $('#cmp-delta').innerHTML = `${esc(t('Δ tris'))} <span class="${cls(dt)}">${sign(dt)}${fmtN(Math.abs(dt))} (${fmtPct(frac(c.tris, p.tris), true)})</span> · ${esc(t('Δ file'))} <span class="${cls(db)}">${sign(db)}${fmtB(Math.abs(db))} (${fmtPct(frac(v.size, src.size), true)})</span> · ${esc(t('Δ height'))} <span>${Math.abs(dh) < 0.0005 ? '±0' : sign(dh) + fmtLen(Math.abs(dh))}</span>`;
  $('#lab-prev').textContent = [src.label, src.at && ago(src.at), t('{n} tris', { n: fmtK(p.tris) }), fmtB(src.size)].filter(Boolean).join(' · ');
  $('#lab-cur').textContent = [t('Current'), v.label, t('{n} tris', { n: fmtK(c.tris) }), fmtB(v.size)].join(' · ');
}

function placeSplit() {
  const w = stage.clientWidth;
  const lp = $('#lab-prev'), lc = $('#lab-cur');
  if (state.compare?.mode === 'split') {
    $('#split').style.left = `${viewer.split * w}px`;
    $('#split').setAttribute('aria-valuenow', String(Math.round(viewer.split * 100)));
    lp.style.left = '14px'; lp.style.right = 'auto';
    lc.style.right = '70px'; lc.style.left = 'auto';
  } else if (state.compare?.mode === 'side') {
    $('#sidediv').style.left = `${w / 2}px`;
    lp.style.left = '14px'; lp.style.right = 'auto';
    lc.style.left = `${w / 2 + 14}px`; lc.style.right = 'auto';
  }
}
new ResizeObserver(placeSplit).observe(stage);
$('#t-compare').onclick = () => setCompare(state.compare ? null : 'split');
$('#cmp-close').onclick = () => setCompare(null);
$$('#cmp-mode button').forEach((b) => (b.onclick = () => switchCompareMode(b.dataset.m)));
function switchCompareMode(m) {
  if (!state.compare || state.compare.mode === m) return;
  state.compare.mode = m;
  viewer.setCompare(m);
  $('#split').hidden = m !== 'split';
  $('#sidediv').hidden = m !== 'side';
  syncToolbar(); placeSplit(); renderPins();
}
{
  const s = $('#split');
  let drag = false;
  const setAt = (k) => { viewer.split = Math.min(0.95, Math.max(0.05, k)); placeSplit(); pinsDirty = true; };
  s.addEventListener('pointerdown', (e) => { drag = true; s.setPointerCapture(e.pointerId); e.preventDefault(); });
  s.addEventListener('pointermove', (e) => { if (drag) { const r = stage.getBoundingClientRect(); setAt((e.clientX - r.left) / r.width); } });
  s.addEventListener('pointerup', () => (drag = false));
  s.addEventListener('keydown', (e) => { if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { setAt(viewer.split + (e.key === 'ArrowLeft' ? -0.05 : 0.05)); e.preventDefault(); } });
}

// ── pins ─────────────────────────────────────────────────────────────────────

function noteNumber(n) { return state.detail.notes.indexOf(n) + 1; }
function shownNotes() {
  const all = state.detail?.notes || [];
  return state.noteFilter === 'all' ? all : all.filter((n) => ACTIVE.has(n.status) || n.id === state.hl);
}
function pinnedNotes() {
  if (!state.detail || !state.pinsOn) return [];
  return shownNotes().filter((n) => n.anchor && (!state.hideFixed || n.status === 'open' || n.id === state.hl));
}

function renderPins() {
  const box = $('#pins');
  box.innerHTML = '';
  // The eye only appears once there is a pin on the model to hide.
  $('#pinsctl').hidden = !(state.detail?.notes || []).some((n) => n.anchor);
  for (const n of pinnedNotes()) {
    const b = document.createElement('button');
    const num = noteNumber(n);
    b.className = `pin ${n.status}${n.id === state.hl ? ' hl' : ''}`;
    b.dataset.id = n.id;
    b.setAttribute('aria-label', t('Note {n}, {status}: {text}', { n: num, status: statusLabel(n.status), text: n.text }));
    b.innerHTML = `<span>${num}</span><div class="tip"><b>${num} · ${esc(statusLabel(n.status))}</b><br>${esc(n.text.slice(0, 220))}</div>`;
    b.onclick = (e) => { e.stopPropagation(); highlight(n.id, { scroll: true }); };
    b.ondblclick = (e) => { e.stopPropagation(); if (n.camera) viewer.setCamera(n.camera); };
    box.appendChild(b);
  }
  if (state.draft?.anchor) {
    const b = document.createElement('button');
    b.className = 'pin draft';
    b.dataset.id = 'draft';
    b.setAttribute('aria-label', t('New note being written'));
    b.innerHTML = '<span>+</span>';
    box.appendChild(b);
  }
  state.lastOccl = 0;
  pinsDirty = occlDirty = true;
}

// Each frame the view moved: pins follow their bone or mesh. Whether each is behind the
// model is a real ray from the camera against the model as posed, a few times a second.
function placePins() {
  const els = $('#pins').children;
  if (!els.length || !viewer.a.model || !state.detail) return;
  const now = performance.now();
  const doOccl = occlDirty && now - state.lastOccl > 160;
  if (doOccl) { state.lastOccl = now; occlDirty = false; viewer.ensureProxies(viewer.playing ? 150 : 1e9); }
  const byId = new Map(state.detail.notes.map((n) => [n.id, n]));
  const w = stage.clientWidth;
  for (const el of els) {
    const id = el.dataset.id;
    const anchor = id === 'draft' ? state.draft?.anchor : byId.get(id)?.anchor;
    const p = anchor && viewer.anchorWorld(anchor);
    if (!p) { el.style.display = 'none'; continue; }
    const s = viewer.toScreen(p);
    const hiddenBySplit = state.compare?.mode === 'split' && s.x < viewer.split * w;
    if (s.behind || !s.inView || hiddenBySplit) { el.style.display = 'none'; continue; }
    if (doOccl) state.occl.set(id, viewer.occluded(p));
    const behind = state.occl.get(id) && id !== state.hl && id !== 'draft';
    el.style.display = behind && state.hideBehind ? 'none' : '';
    el.classList.toggle('behind', !!behind);
    el.style.transform = `translate(${s.x.toFixed(1)}px, ${(s.y - 26).toFixed(1)}px) rotate(-45deg)`;
  }
}

function placeLabels() {
  const box = $('#labels');
  const ls = viewer.boundsLabels();
  let html = ls.filter((l) => !l.behind).map((l) => `<span class="blabel" style="transform:translate(${l.x.toFixed(1)}px,${l.y.toFixed(1)}px) translate(-50%,-50%)">${esc(l.text)}</span>`).join('');
  if (viewer.opts.grid && viewer.frontAt && viewer.a.model) {
    const s = viewer.toScreen(viewer.frontAt);
    if (!s.behind && s.inView) html += `<span class="flabel" style="transform:translate(${s.x.toFixed(1)}px,${s.y.toFixed(1)}px) translate(-50%,-50%)">${esc(t('FRONT'))}</span>`;
  }
  if (box._h !== html) { box.innerHTML = html; box._h = html; }
}

function highlight(id, { scroll = false } = {}) {
  state.hl = state.hl === id && !scroll ? null : id;
  const n = state.detail?.notes.find((x) => x.id === id);
  if (scroll) {
    ensureRight('notes');
    if (n && !ACTIVE.has(n.status) && state.noteFilter === 'active') setNoteFilter('all');
  }
  renderNotes();
  renderPins();
  if (state.hl) {
    const el = $(`#note-list .note[data-id="${CSS.escape(id)}"]`);
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    if (scroll && el) { el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash'); }
  }
  reportSelection();
}

// ── composing a note ─────────────────────────────────────────────────────────

function ensureRight(tab = 'notes') { if (!isOpen(right)) setPanel(right, true); setTab(tab); }

function startPin() {
  if (!state.detail || !viewer.a.model) return;
  ensureRight('notes');
  cancelDraft(false);
  state.pinning = true;
  stage.classList.add('pinning');
  hint(t('Click the model where the note goes · Esc cancels'));
  syncToolbar();
}

function startGeneral(text = '') {
  if (!state.detail || !viewer.a.model) return;
  ensureRight('notes');
  cancelDraft(false);
  openComposer({ anchor: null });
  if (text) $('#composer-text').value = text;
}

function openComposer(draft) {
  state.draft = draft;
  state.pinning = false;
  stage.classList.remove('pinning');
  hint('');
  const a = draft.anchor;
  const where = a
    ? `${esc(a.object || a.mesh || t('the model'))}${a.material ? ` · ${esc(a.material)}` : ''}${a.bone ? ` · ${esc(t('bone {b}', { b: a.bone }))}` : ''} · ${esc(a.region)}<br>${esc(t('Blender {p}', { p: a.point_blender.map((x) => fmtD(x, 3)).join(', ') }))}`
    : esc(t('Whole model · the current view is saved with the note'));
  $('#composer-where').innerHTML = `<i class="${a ? '' : 'whole'}"></i><span>${where}</span>`;
  $('#composer').hidden = false;
  $('#composer-text').value = '';
  $('#tab-notes').scrollTop = 0;
  setTimeout(() => $('#composer-text').focus(), 30);
  renderPins();
  syncToolbar();
}

function cancelDraft(render = true) {
  state.pinning = false;
  state.draft = null;
  stage.classList.remove('pinning');
  $('#composer').hidden = true;
  $('#composer-text').value = '';
  hint('');
  if (render) { renderPins(); syncToolbar(); }
}

async function saveNote() {
  const text = $('#composer-text').value.trim();
  if (!text || !state.draft) { $('#composer-text').focus(); return; }
  const draft = state.draft, id = state.id;
  const btn = $('#composer-save');
  btn.disabled = true;
  try {
    // The view as it is now, and for a pin a close-up of it: what you asked about.
    const pin = draft.anchor ? viewer.anchorWorld(draft.anchor)?.toArray() : null;
    const { shot, detail, view } = viewer.screenshot({ pin });
    const anchor = draft.anchor && pin ? { ...draft.anchor, point: pin.map((x) => +x.toFixed(4)) } : draft.anchor;
    const note = await assetApi(id, '/notes', {
      method: 'POST',
      body: { text, variant: state.variant, anchor, camera: viewer.cameraState(), view, shot, detail },
    });
    cancelDraft(false);
    if (state.noteFilter !== 'active') setNoteFilter('active');
    await fetchDetail();
    state.hl = note.id;
    renderNotes(); renderPins();
    const n = state.detail.notes.findIndex((x) => x.id === note.id) + 1;
    toast(t('Note {n} saved with its screenshot{cu}. Claude picks it up on {cmd}', { n, cu: draft.anchor ? t(' and close-up') : '', cmd: `<span class="mono">/kiln studio ${esc(state.detail.name)}</span>` }), 'ok', 4200);
    requestAnimationFrame(() => $(`#note-list .note[data-id="${CSS.escape(note.id)}"]`)?.classList.add('flash'));
  } catch (e) {
    toast(t('Could not save the note: {e}', { e: esc(e.message) }), 'warn', 8000);
  } finally {
    btn.disabled = false;
  }
}
$('#t-pin').onclick = () => (state.pinning ? cancelDraft() : startPin());
$('#t-general').onclick = () => startGeneral();
$('#r-pin').onclick = () => startPin();
$('#r-general').onclick = () => startGeneral();
$('#composer-save').onclick = saveNote;
$('#composer-cancel').onclick = () => cancelDraft();
$('#composer-text').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); saveNote(); }
  if (e.key === 'Escape') { e.preventDefault(); cancelDraft(); }
});

// clicks on the model: pin placement (a drag still orbits), or a plain click to clear the highlight
const canvas = $('#view');
let down = null;
canvas.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY }; });
canvas.addEventListener('pointerup', (e) => {
  if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5) { down = null; return; }
  down = null;
  if (state.pinning) {
    const hit = viewer.pick(e.clientX, e.clientY);
    if (!hit) { toast(state.compare?.mode === 'split' ? t('Pin on the current version, right of the divider') : t('That missed the model: click on its surface'), 'warn', 2400); return; }
    openComposer({ anchor: hit });
  } else if (state.hl) {
    highlight(state.hl);
  }
});
let hoverRaf = 0;
canvas.addEventListener('pointermove', (e) => {
  if (e.buttons || hoverRaf) return;
  hoverRaf = requestAnimationFrame(() => {
    hoverRaf = 0;
    const h = viewer.pick(e.clientX, e.clientY);
    const el = $('#hover');
    if (!h) { el.hidden = true; return; }
    el.innerHTML = `${esc(h.object || h.mesh)}${h.material ? ` · ${esc(h.material)}` : ''}${h.bone ? ` · ${esc(t('bone {b}', { b: h.bone }))}` : ''}<br>${esc(t('Blender {p}', { p: h.point_blender.map((x) => fmtD(x, 3)).join(', ') }))} m`;
    el.hidden = false;
  });
});
canvas.addEventListener('pointerleave', () => ($('#hover').hidden = true));

// ── right panel ──────────────────────────────────────────────────────────────

function setTab(name) {
  $$('.tabs [role=tab]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === name)));
  for (const k of ['notes', 'checks', 'details', 'history']) $(`#tab-${k}`).hidden = k !== name;
  $$('#right .rail [data-rtab]').forEach((b) => b.classList.toggle('on', b.dataset.rtab === name));
  prefs.tab = name; savePrefs();
}
$$('.tabs [role=tab]').forEach((b) => (b.onclick = () => setTab(b.dataset.tab)));
$$('#right .rail [data-rtab]').forEach((b) => (b.onclick = () => { setPanel(right, true); setTab(b.dataset.rtab); }));
function setNoteFilter(f) {
  state.noteFilter = f;
  $$('#nf button').forEach((x) => x.classList.toggle('on', x.dataset.nf === f));
}
$$('#nf button').forEach((b) => (b.onclick = () => { setNoteFilter(b.dataset.nf); renderNotes(); renderPins(); }));

function renderCounts() {
  const d = state.detail;
  const c = d ? d.counts : { open: 0, addressed: 0 };
  const active = c.open + c.addressed;
  const tn = $('#tc-notes'), rn = $('#rc-notes');
  tn.textContent = active ? fmtN(active) : '';
  tn.className = 'tc ' + (c.addressed ? 'cnt addressed' : c.open ? 'cnt open' : '');
  rn.hidden = !active; rn.textContent = fmtN(active); rn.className = 'cnt ' + (c.addressed ? 'addressed' : 'open');
  const w = d?.checks ? checksFor(currentVariant()?.label).filter((r) => r.level === 'warn').length : 0;
  $('#tc-checks').textContent = w ? fmtN(w) : '';
  $('#tc-checks').className = 'tc ' + (w ? 'cnt warn' : '');
  $('#rc-checks').hidden = !w; $('#rc-checks').textContent = fmtN(w); $('#rc-checks').className = 'cnt warn';
}

function latestShot(n) {
  for (let i = (n.thread || []).length - 1; i >= 0; i--) if (n.thread[i].shot) return n.thread[i];
  return null;
}
const isStale = (n) => {
  const cur = state.detail.variants.find((v) => v.label === n.version?.variant);
  return !!(cur && n.version?.hash && cur.hash !== n.version.hash);
};

function shotHtml(x, cap, cls = '') {
  if (!x) return `<div class="shot loading" aria-label="${esc(t('Rendering the picture'))}"></div>`;
  return `<button class="shot" data-act="view" aria-label="${esc(t('Open the {cap} picture', { cap }))}"><img src="${esc(fileUrl(x.shot))}" alt="">${x.detail ? `<img class="inset" src="${esc(fileUrl(x.detail))}" alt="${esc(t('Close-up of the pin'))}">` : ''}<span class="cap ${cls}">${esc(cap)}</span></button>`;
}

function replyHtml(r) {
  const st = r.status ? ` <span class="status ${r.status}">${esc(statusLabel(r.status))}</span>` : '';
  const ver = r.status === 'addressed' && r.version ? ` · ${esc(t('on {v}', { v: `${r.version.variant} ${r.version.hash.slice(0, 7)}` }))}` : '';
  return `<div class="reply ${r.by === 'claude' ? 'claude' : 'you'}"><div class="who"><b>${r.by === 'claude' ? 'Claude' : esc(t('You'))}</b> · <span title="${esc(stamp(r.at))}">${esc(ago(r.at))}</span>${ver}${st}</div>${r.text ? `<div class="body">${esc(r.text)}</div>` : ''}</div>`;
}

function actionsHtml(n) {
  const b = (act, label, cls = '') => `<button class="btn sm ${cls}" data-act="${act}">${esc(t(label))}</button>`;
  const view = n.shot ? b('view', 'View', 'ghost') : '';
  if (n.status === 'open') return b('reply', 'Reply') + b('wontfix', "Won't fix") + b('edit', 'Edit', 'ghost') + b('delete', 'Delete', 'ghost') + view;
  if (n.status === 'addressed') return b('resolve', 'Looks right', 'accent') + b('reopen', 'Not yet…') + b('reply', 'Reply', 'ghost') + view;
  return b('reopen', 'Reopen…') + b('delete', 'Delete', 'ghost') + view;
}

function noteEl(n) {
  const d = state.detail;
  const stale = isStale(n);
  const after = latestShot(n);
  const lastAddressed = [...(n.thread || [])].reverse().find((r) => r.status === 'addressed');
  const waiting = lastAddressed && !lastAddressed.shot && d.pending.some((p) => p.reply === lastAddressed.id);
  const a = n.anchor, num = noteNumber(n);
  const before = n.shot ? { shot: n.shot, detail: n.detail } : null;
  let shots = '';
  if (after) shots = shotHtml(before, t('before')) + shotHtml(after, t('after'), 'after');
  else if (waiting) shots = shotHtml(before, t('before')) + shotHtml(null, '');
  else if (before) shots = shotHtml(before, stale ? t('on an earlier version') : t('when noted'));
  const el = document.createElement('article');
  el.className = `note${state.hl === n.id ? ' hl' : ''}`;
  el.dataset.id = n.id;
  el.innerHTML = `
    <header><span class="num ${a ? n.status : 'whole'}" aria-hidden="true"><span>${a ? num : 'M'}</span></span><span class="status ${n.status}">${esc(statusLabel(n.status))}</span><span class="kind">${esc(a ? t('pin {n}', { n: num }) : t('note {n} · whole model', { n: num }))}${d.variants.length > 1 && n.version?.variant ? ` · ${esc(n.version.variant)}` : ''}</span><time title="${esc(stamp(n.created))}">${esc(ago(n.created))}</time></header>
    ${state.editing === n.id
      ? `<textarea class="edit-text" rows="3" aria-label="${esc(t('Note text'))}">${esc(n.text)}</textarea><div class="actions" style="margin-bottom:8px"><button class="btn sm accent" data-act="save-edit">${esc(t('Save'))}</button><button class="btn sm" data-act="cancel-edit">${esc(t('Cancel'))}</button></div>`
      : `<p class="text">${esc(n.text)}</p>`}
    ${a ? `<div class="where">${esc(a.object || a.mesh || '')}${a.material ? ` · ${esc(a.material)}` : ''}${a.bone ? ` · ${esc(t('bone {b}', { b: a.bone }))}` : ''} · ${esc(a.region || '')}</div>` : ''}
    ${stale && n.status === 'open' ? `<div class="stale">${esc(t('Made on an earlier version ({h}); the model has changed since.', { h: n.version.hash.slice(0, 7) }))}</div>` : ''}
    ${shots ? `<div class="shots${after || waiting ? '' : ' one'}">${shots}</div>` : ''}
    ${(n.thread || []).length ? `<div class="thread">${n.thread.map(replyHtml).join('')}</div>` : ''}
    ${state.replying?.id === n.id ? `<div class="reply-box"><textarea class="reply-text" rows="2" placeholder="${esc(state.replying.status === 'open' ? t('What still needs to change?') : t('Reply…'))}" aria-label="${esc(t('Reply'))}"></textarea><div class="row"><button class="btn sm accent" data-act="send-reply">${esc(state.replying.status === 'open' ? t('Reopen') : t('Send'))}</button><button class="btn sm" data-act="cancel-reply">${esc(t('Cancel'))}</button></div></div>` : ''}
    <div class="actions">${actionsHtml(n)}</div>`;
  el.onclick = (e) => {
    const act = e.target.closest('[data-act]')?.dataset.act;
    if (act) { e.stopPropagation(); noteAction(n, act, el); return; }
    if (!e.target.closest('textarea, button')) highlight(n.id);
  };
  el.ondblclick = (e) => { if (!e.target.closest('textarea, button') && n.camera) viewer.setCamera(n.camera); };
  return el;
}

async function postReply(n, text, status) {
  await assetApi(state.id, `/notes/${n.id}/thread`, { method: 'POST', body: { text, status } });
  state.replying = null;
  await fetchDetail();
}

async function noteAction(n, act, el) {
  try {
    if (act === 'view') { openViewer(n); return; }
    if (act === 'resolve') { await postReply(n, '', 'resolved'); toast(t('Note {n} resolved', { n: noteNumber(n) }), 'ok'); return; }
    if (act === 'wontfix') { await postReply(n, '', 'wontfix'); return; }
    if (act === 'reply' || act === 'reopen') {
      state.replying = { id: n.id, status: act === 'reopen' ? 'open' : null };
      renderNotes();
      $(`#note-list .note[data-id="${CSS.escape(n.id)}"] .reply-box textarea`)?.focus();
      return;
    }
    if (act === 'cancel-reply') { state.replying = null; renderNotes(); return; }
    if (act === 'send-reply') {
      const text = $('.reply-box textarea', el).value.trim();
      if (!text && !state.replying.status) return;
      const reopen = state.replying.status === 'open';
      await postReply(n, text, state.replying.status);
      if (reopen) toast(t('Note {n} reopened: Claude sees it on the next pass', { n: noteNumber(n) }));
      return;
    }
    if (act === 'edit') { state.editing = n.id; renderNotes(); $('.edit-text', $(`#note-list .note[data-id="${CSS.escape(n.id)}"]`))?.focus(); return; }
    if (act === 'cancel-edit') { state.editing = null; renderNotes(); return; }
    if (act === 'save-edit') {
      const text = $('.edit-text', el).value.trim();
      if (!text) return;
      await assetApi(state.id, `/notes/${n.id}`, { method: 'PATCH', body: { text } });
      state.editing = null;
      await fetchDetail();
      return;
    }
    if (act === 'delete') {
      if (!(await confirmDialog(t('Delete note {n} and its pictures?', { n: noteNumber(n) }), t('Delete')))) return;
      await assetApi(state.id, `/notes/${n.id}`, { method: 'DELETE' });
      await fetchDetail();
    }
  } catch (e) {
    toast(esc(e.message), 'warn', 8000);
  }
}

// Live updates re-render the panels; whatever is being typed there survives it.
function keepTyping(root, render) {
  const kept = $$('textarea, input[type=text], input:not([type])', root).map((el) => ({
    sel: el.id ? `#${el.id}`
      : `${el.closest('[data-id]') ? `[data-id="${el.closest('[data-id]').dataset.id}"] ` : ''}${el.classList.length ? '.' + [...el.classList].join('.') : el.tagName.toLowerCase()}`,
    value: el.value, focus: el === document.activeElement, start: el.selectionStart, end: el.selectionEnd,
  })).filter((k) => k.value || k.focus);
  render();
  for (const k of kept) {
    const el = $(k.sel, root);
    if (!el) continue;
    el.value = k.value;
    if (k.focus) { el.focus(); try { el.setSelectionRange(k.start, k.end); } catch { /* not a text input */ } }
  }
}

function renderNotes() {
  keepTyping($('#note-list'), renderNotesNow);
}

function renderNotesNow() {
  const d = state.detail;
  const list = $('#note-list');
  list.innerHTML = '';
  if (!d) { renderCounts(); return; }
  const notes = shownNotes();
  for (const n of notes) list.appendChild(noteEl(n));
  if (!notes.length) {
    const total = d.notes.length;
    list.innerHTML = `<div class="empty-notes"><b>${esc(total ? t('Nothing active') : t('No notes yet'))}</b>${esc(total
      ? tp(total, '{n} closed note under All.', '{n} closed notes under All.')
      : t('Pin a note on the model (N) or write one about the whole model (M). Claude reads them, changes the model, and replies here.'))}</div>`;
  }
  const c = d.counts;
  const cmd = `/kiln studio ${d.id}`;
  $('#handoff').innerHTML = [
    c.addressed ? `<div>${tp(c.addressed, '<b>{n} note to check</b>: Claude changed the model. Look, then mark it <b>Looks right</b> or <b>Not yet</b>.', '<b>{n} notes to check</b>: Claude changed the model. Look, then mark each one <b>Looks right</b> or <b>Not yet</b>.')}</div>` : '',
    c.open ? `<div${c.addressed ? ' style="margin-top:8px"' : ''}>${esc(tp(c.open, '{n} open note. In Claude Code, run:', '{n} open notes. In Claude Code, run:'))}<div class="cmd"><code>${esc(cmd)}</code><button class="btn sm" data-copy="${esc(cmd)}">${esc(t('Copy'))}</button></div></div>` : '',
  ].join('');
  $$('#handoff [data-copy]').forEach((b) => (b.onclick = () => copy(b.dataset.copy)));
  renderCounts();
}

// The "View" overlay: the before and after, large, with a slider; the close-ups below.
function openViewer(n) {
  const dlg = $('#viewer2');
  const after = latestShot(n);
  $('#v2-status').className = `status ${n.status}`;
  $('#v2-status').textContent = statusLabel(n.status);
  $('#v2-text').textContent = `${n.anchor ? t('Pin {n}', { n: noteNumber(n) }) : t('Note {n}', { n: noteNumber(n) })} · ${n.text}`;
  const ba = $('#v2-ba');
  $('.before', ba).src = n.shot ? fileUrl(n.shot) : '';
  $('.after', ba).src = after?.shot ? fileUrl(after.shot) : '';
  const two = !!after;
  $('.after', ba).hidden = $('.bar2', ba).hidden = $('.lab.r', ba).hidden = !two;
  const stale = isStale(n);
  $('.lab.l', ba).textContent = two ? `${t('Before')} · ${stale ? t('earlier version') : t('when noted')}` : (stale ? t('Earlier version') : t('When noted'));
  $('.lab.r', ba).textContent = `${t('After')} · ${after?.version ? `${after.version.variant} ${after.version.hash.slice(0, 7)}` : t('current')}`;
  ba.style.setProperty('--cut', '50%');
  const cu = [n.detail && `<figure><img src="${esc(fileUrl(n.detail))}" alt="">${esc(two ? t('Close-up · before') : t('Close-up'))}</figure>`,
    two && after.detail && `<figure><img src="${esc(fileUrl(after.detail))}" alt="">${esc(t('Close-up · after'))}</figure>`].filter(Boolean).join('');
  $('#v2-close').innerHTML = `${cu}<div class="thr">${(n.thread || []).map(replyHtml).join('') || `<span class="dim">${esc(t('No reply yet.'))}</span>`}</div>`;
  $('#v2-look').hidden = !n.camera;
  $('#v2-look').onclick = () => { if (n.camera) viewer.setCamera(n.camera); dlg.close(); highlight(n.id, { scroll: true }); };
  dlg.showModal();
}
{
  const ba = $('#v2-ba');
  let drag = false;
  const set = (x) => { const r = ba.getBoundingClientRect(); const k = Math.min(100, Math.max(0, ((x - r.left) / r.width) * 100)); ba.style.setProperty('--cut', `${k}%`); $('.bar2', ba).setAttribute('aria-valuenow', String(Math.round(k))); };
  ba.addEventListener('pointerdown', (e) => { if ($('.after', ba).hidden) return; drag = true; ba.setPointerCapture(e.pointerId); set(e.clientX); });
  ba.addEventListener('pointermove', (e) => drag && set(e.clientX));
  ba.addEventListener('pointerup', () => (drag = false));
  $('.bar2', ba).addEventListener('keydown', (e) => {
    const k = parseFloat(ba.style.getPropertyValue('--cut')) || 50;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { e.preventDefault(); ba.style.setProperty('--cut', `${Math.min(100, Math.max(0, k + (e.key === 'ArrowLeft' ? -5 : 5)))}%`); }
  });
}

// ── checks: kiln's rules, the reference photo, the batch estimate ────────────

function checksFor(label) {
  const c = state.detail?.checks;
  return c ? c.health[label] || [] : [];
}

// `/kiln optimize chair` in a fix: shown as code, and copied from the row below it.
const cmdsIn = (s) => [...String(s || '').matchAll(/`([^`]+)`/g)].map((m) => m[1]);
const codeIn = (s) => esc(s).replace(/`([^`]+)`/g, (_, c) => `<code class="icmd" data-copy="${c}" title="${esc(t('Copy, then run it in Claude Code'))}">${c}</code>`);

function checkRow(r) {
  let more = '';
  if (r.entries?.length) more = `<ul class="sub">${r.entries.map((e) => `<li class="${e.level}">${esc(e.label || e.kind)}: ${esc(e.text)}</li>`).join('')}</ul>`;
  if (r.images?.length) more = `<ul class="sub">${r.images.map((i) => `<li>${esc(i.slots.join(', ') || i.name)} · ${i.w ? `${i.w}×${i.h}` : esc(t('size unknown'))} ${esc((i.format || '').toUpperCase())}</li>`).join('')}</ul>`;
  const cmds = cmdsIn(r.fix);
  const fix = r.level !== 'ok' && (r.fix || r.ask)
    ? `<div class="fix">${r.fix ? `<span><b style="display:inline">${esc(t('How to fix:'))}</b> ${codeIn(r.fix)}</span>${cmds.map((c) => `<div class="cmd"><code>${esc(c)}</code><button class="btn sm" data-copy="${esc(c)}">${esc(t('Copy'))}</button></div>`).join('')}` : ''}${r.ask ? `<div><button class="btn sm" data-ask="${esc(r.ask)}" title="${esc(t('Write it as a note on this model, for /kiln studio to pick up'))}">${esc(t('Ask Claude'))}</button></div>` : ''}</div>`
    : '';
  const lvl = { warn: t('to look at'), ok: t('fine'), info: t('note') }[r.level];
  return `<div class="check ${r.level}"><span class="lvl" role="img" aria-label="${esc(lvl)}" title="${esc(lvl)}"></span><div><b>${esc(r.label)}</b><div class="txt">${esc(r.text)}</div>${fix}${more}</div></div>`;
}

function renderChecks() {
  const d = state.detail, tab = $('#tab-checks');
  const c = d?.checks, v = currentVariant();
  if (!c) { tab.innerHTML = ''; renderCounts(); return; }
  const rows = checksFor(v.label);
  const isShip = c.shipped === v.label;
  const head = d.kiln ? (isShip ? t('{v} · the shipped file', { v: v.label }) : c.shipped ? t('{v} · not the shipped file ({s} is)', { v: v.label, s: c.shipped }) : t('{v} · not the shipped file', { v: v.label })) : v.label;
  const blocks = [];
  const cfg = Object.entries(c.config || {}).filter(([k]) => ['type', 'tier', 'target', 'style'].includes(k));
  blocks.push(`<div class="block"><h3>${esc(t('Health'))} · ${esc(head)}</h3>${rows.map(checkRow).join('') || `<p class="dim">${esc(t('Nothing to check.'))}</p>`}
    ${cfg.length ? `<p class="dim small" style="margin:10px 0 0">${esc(t('From the production log:'))} ${cfg.map(([k, x]) => `${esc(t(k))} <b>${esc(x)}</b>`).join(' · ')}</p>` : ''}</div>`);
  if (c.fidelity.length) blocks.push(fidelityBlock(c.fidelity));
  if (c.batch) blocks.push(batchBlock(c.batch));
  tab.innerHTML = blocks.join('');
  $$('[data-img]', tab).forEach((x) => (x.onclick = () => lightbox(JSON.parse(x.dataset.img))));
  $$('[data-copy]', tab).forEach((x) => (x.onclick = () => copy(x.dataset.copy)));
  $$('[data-ask]', tab).forEach((x) => (x.onclick = () => startGeneral(x.dataset.ask)));
  $$('[data-photo-view]', tab).forEach((x) => (x.onclick = () => photoView(JSON.parse(x.dataset.photoView))));
  $$('[data-fv]', tab).forEach((x) => (x.onclick = () => {
    const run = x.closest('.run');
    $$('[data-fv]', run).forEach((y) => y.classList.toggle('on', y === x));
    $$('img[data-which]', run).forEach((img) => (img.hidden = img.dataset.which !== x.dataset.fv));
  }));
  renderCounts();
}

// The direction fidelity_check.py's camera looked from (its render(): Blender front is -Y,
// azimuth turns toward +X, elevation tilts down), in three.js coordinates (Blender x, z, -y).
function photoDir(run) {
  const base = { front: [0, -1], back: [0, 1], left: [-1, 0], right: [1, 0] }[run.view];
  if (!base) return [0, 1, 0.0001];
  const a = (run.azimuth || 0) * Math.PI / 180, e = (run.elevation || 0) * Math.PI / 180;
  const hx = base[0] * Math.cos(a) - base[1] * Math.sin(a), hy = base[0] * Math.sin(a) + base[1] * Math.cos(a);
  return [hx * Math.cos(e), Math.sin(e), -(hy * Math.cos(e))];
}
function photoView(run) {
  viewer.lookFrom(photoDir(run));
  const parts = [t(run.view)];
  if (run.elevation) parts.push(t('{n}° up', { n: run.elevation }));
  if (run.azimuth) parts.push(t('{n}° round', { n: run.azimuth }));
  toast(esc(t("The photo's view: {where}. Perspective here, orthographic in the measure.", { where: parts.join(', ') })));
}

function fidelityBlock(runs) {
  const one = (r, i) => {
    const iou = typeof r.iou === 'number' ? fmtD(r.iou, 3) : '–';
    const trend = (r.trend || []).filter((x) => typeof x.iou === 'number').map((x) => fmtD(x.iou, 3));
    const where = [t(r.view), r.elevation ? t('{n}° up', { n: r.elevation }) : '', r.azimuth ? t('{n}° round', { n: r.azimuth }) : ''].filter(Boolean).join(' · ');
    const on = r.measured ? `${esc(t('measured on'))} <b>${esc(r.measured)}</b> <span class="mono dim">${esc((r.model_hash || '').slice(0, 7))}</span> <span class="status addressed">${esc(t('file current'))}</span>`
      : r.current === false ? `${esc(t('on an earlier version'))} <span class="mono dim">${esc((r.model_hash || '').slice(0, 7))}</span> <span class="status open">${esc(t('re-measure'))}</span>` : esc(r.model || '');
    const imgs = [r.overlay && { src: fileUrl(r.overlay), caption: t('Overlay: red is the photo only, cyan the model only'), which: 'overlay' },
      r.side_by_side && { src: fileUrl(r.side_by_side), caption: t('The photo and the render, side by side'), which: 'side' }].filter(Boolean);
    const joints = (r.joints || []).map((j) => ({ src: fileUrl(j), caption: j.split('/').pop() }));
    const body = `
      <div class="iou"><span class="big">${iou}</span><span class="dim">${esc(t('how closely the outline matches the photo (IoU: 1 is identical) · a guide, not a target'))}</span></div>
      ${trend.length > 1 ? `<div class="rounds">${esc(t('rounds'))} ${trend.map((x) => `<span>${x}</span>`).join('→')}</div>` : ''}
      <p class="meta">${esc(where)} · ${on}${r.reference_name ? ` · ${esc(t('photo {p}', { p: r.reference_name }))}` : ''}</p>
      ${imgs.length ? `<div class="fvrow"><div class="seg small fv">${imgs.map((m, k) => `<button data-fv="${m.which}" class="${k ? '' : 'on'}">${esc(m.which === 'overlay' ? t('Overlay') : t('Side by side'))}</button>`).join('')}</div><button class="btn sm" data-photo-view='${esc(JSON.stringify(r))}' title="${esc(t("Turn the model to where the photo's camera stood"))}">${esc(t("Photo's view"))}</button></div>
        <div class="fv-img">${imgs.map((m, k) => `<img src="${esc(m.src)}" alt="${esc(m.caption)}" data-which="${m.which}" ${k ? 'hidden' : ''} data-img='${esc(JSON.stringify(imgs.map(({ src, caption }) => ({ src, caption }))))}'>`).join('')}</div>` : ''}
      ${r.gaps?.length ? `<h4>${esc(t('Gaps, largest first'))}</h4><ol class="gaps">${r.gaps.map((g) => `<li>${esc(g)}</li>`).join('')}</ol>` : `<p class="dim">${esc(t('No gap above tolerance.'))}</p>`}
      ${r.shape?.length ? `<h4>${esc(t('Per height band (1 = top)'))}</h4><table class="vt"><tr><th>${esc(t('Band'))}</th><th class="num">${esc(t('Width'))}</th><th class="num">${esc(t('Core'))}</th><th class="num">IoU</th></tr>${r.shape.map((b) => `<tr><td>${b.band}</td><td class="num">${pctS(b.full_width)}</td><td class="num">${pctS(b.core_width)}</td><td class="num">${fmtD(b.iou, 2)}</td></tr>`).join('')}</table>` : ''}
      ${joints.length ? `<h4>${esc(t('Joints: look at each'))}</h4><div class="joints">${joints.map((j) => `<img src="${esc(j.src)}" alt="${esc(j.caption)}" data-img='${esc(JSON.stringify(joints))}'>`).join('')}</div>` : ''}`;
    return `<details class="run" ${i ? '' : 'open'}><summary>${esc(r.dir)} · ${esc(t(r.view))} · ${iou}${r.at ? ` · ${esc(ago(r.at))}` : ''}</summary>${body}</details>`;
  };
  return `<div class="block fidelity"><h3>${esc(t('Against the reference photo'))}</h3>${runs.map(one).join('')}</div>`;
}
const pctS = (x) => (typeof x === 'number' ? fmtPct(x, true) : '–');

function batchBlock(b) {
  const a = b.asset;
  const methods = Object.entries(b.by_method).map(([m, n]) => `${fmtN(n)} ${esc(m)}`).join(', ');
  return `<div class="block"><h3>${esc(t('Batch'))} · ${esc(b.name)}</h3><dl class="kv">
    ${a ? `<dt>${esc(t('This asset'))}</dt><dd>${esc(a.method || '?')} · ${esc(t(a.status))} · ${esc(fmtTok(a.range))}</dd>` : ''}
    <dt>${esc(t('Whole batch'))}</dt><dd>${esc(tp(b.assets, '{n} asset', '{n} assets'))} (${methods || '–'}) · ${esc(fmtTok(b.range))}</dd>
    <dt>${esc(t('Left to run'))}</dt><dd>${fmtN(b.remaining.assets)} · ${esc(fmtTok(b.remaining.range))}</dd>
    ${b.unknown.length ? `<dt>${esc(t('No estimate'))}</dt><dd>${b.unknown.map(esc).join(', ')} (${esc(t('unknown method'))})</dd>` : ''}
  </dl><p class="dim small" style="margin:8px 0 0">${esc(t("Estimate ±50%. The wizard's formula: scripted ~30K, marketplace ~20K, geometry nodes ~40K, AI ~60–80K per asset; high end ×1.5. From {f}.", { f: b.manifest }))}</p></div>`;
}

// ── details ──────────────────────────────────────────────────────────────────

function renderDetails() {
  keepTyping($('#tab-details'), renderDetailsNow);
}

function renderDetailsNow() {
  const d = state.detail, tab = $('#tab-details');
  if (!d) { tab.innerHTML = ''; return; }
  const v = currentVariant(), st = v.stats || {}, cs = state.clientStats || {};
  const cats = [...new Set(state.assets.map((a) => a.category).filter(Boolean))].sort();
  const textures = cs.textures || [];
  const b = d.baseline;
  const blocks = [];
  blocks.push(`<div class="block"><h3>${esc(d.kiln ? t('Pipeline stages') : t('Files'))}</h3><table class="vt">
    <tr><th>${esc(d.kiln ? t('Stage') : t('Format'))}</th><th class="num">${esc(t('Size'))}</th><th class="num">${esc(t('Tris'))}</th><th></th></tr>
    ${d.variants.map((x) => `<tr class="${x.label === v.label ? 'cur' : ''}"><td><button data-v="${esc(x.label)}">${esc(x.label)}</button></td><td class="num">${fmtB(x.size)}</td><td class="num">${fmtN(x.stats?.tris)}</td><td class="num"><button data-copy="${esc(x.file)}" title="${esc(t('Copy the path'))}">${esc(t('Path'))}</button></td></tr>`).join('')}
  </table></div>`);
  const dims = st.dimensions_blender || cs.dims;
  const rows = [
    [t('Triangles'), fmtN(st.tris ?? cs.tris)], [t('Vertices'), fmtN(st.verts ?? cs.verts)],
    [t('Meshes'), fmtN(st.meshes ?? cs.meshes)],
    [t('Size (Blender)'), dims ? `X ${fmtLen(dims[0])} · Y ${fmtLen(dims[1])} · Z ${fmtLen(dims[2])}` : '–'],
    [t('File'), fmtB(v.size)],
    [t('Materials'), (st.materials || cs.materials || []).map(esc).join(', ') || '–'],
    [t('Textures'), textures.length ? textures.map((x) => `${esc(x.slot.replace('Map', '').replace(/^map$/, t('base colour')))} ${x.w}×${x.h}`).join('<br>') : (st.textures ? fmtN(st.textures) : esc(t('none in the file')))],
    [t('Animations'), (st.animations?.length ? st.animations.map((a) => `${esc(a.name)} ${fmtD(a.duration, 2)} s`) : (cs.clips || []).map((c) => `${esc(c.name)} ${fmtD(c.duration, 2)} s`)).join(', ') || '–'],
    [t('Skins'), st.skins != null ? fmtN(st.skins) : (cs.skinned ? t('yes') : '–')],
    [t('Extensions'), (st.extensions || []).map(esc).join(', ') || esc(t('none'))],
    [t('Exported by'), esc(st.generator || '–')],
  ];
  const fmt = v.ext.slice(1).toUpperCase();
  blocks.push(`<div class="block"><h3>${v.label.toUpperCase() === fmt ? fmt : `${esc(v.label)} · ${fmt}`}</h3><dl class="kv">${rows.map(([k, val]) => `<dt>${esc(k)}</dt><dd>${val}</dd>`).join('')}</dl></div>`);
  blocks.push(`<div class="block"><h3>${esc(t('Organise'))}</h3><div class="meta-form">
    <label>${esc(t('Category'))}<input id="m-cat" list="m-cats" value="${esc(d.category)}" placeholder="${esc(d.folder)}" aria-label="${esc(t('Category'))}"><datalist id="m-cats">${cats.map((c) => `<option value="${esc(c)}">`).join('')}</datalist></label>
    <label>${esc(t('Tags'))}<div class="tags-edit">${d.tags.map((x) => `<span class="tg">#${esc(x)}<button data-untag="${esc(x)}" aria-label="${esc(t('Remove tag {t}', { t: x }))}">×</button></span>`).join('')}<input id="m-tag" placeholder="${esc(t('add a tag ↵'))}" aria-label="${esc(t('Add a tag'))}"></div></label>
  </div></div>`);
  blocks.push(`<div class="block"><h3>${esc(t('Previous version'))}</h3>${b
    ? `<p class="small" style="margin:0;color:var(--text-2)">${esc(b.variant)} <span class="mono">${esc(b.hash.slice(0, 7))}</span> · ${fmtB(b.size)} · ${esc(t('kept {when} ({why})', { when: ago(b.at), why: b.reason }))}</p>
       <div class="btns"><button class="btn sm" data-act="cmp-prev">${esc(t('Compare'))}</button><button class="btn sm" data-act="revert">${esc(t('Put it back'))}</button><button class="btn sm ghost" data-act="snapshot" title="${esc(t('Replace it with the version shown now'))}">${esc(t('Keep this one instead'))}</button></div>`
    : `<p class="small dim" style="margin:0">${esc(t('Studio keeps one previous copy: the version your first note on it was made on, so a review pass can be compared and undone.'))}</p>
       <div class="btns"><button class="btn sm" data-act="snapshot">${esc(t('Keep this version now'))}</button></div>`}</div>`);
  const files = d.files || [];
  if (files.length) {
    blocks.push(`<div class="block"><h3>${esc(t('Beside it'))}</h3><ul class="files">${files.map((f) => {
      const ext = f.slice(f.lastIndexOf('.')).toLowerCase();
      const name = f.split('/').pop();
      const act = ['.png', '.jpg', '.jpeg', '.webp'].includes(ext) ? `<button class="btn sm ghost" data-img="${esc(f)}">${esc(t('View'))}</button>`
        : ['.md', '.txt', '.json', '.yaml', '.yml', '.py'].includes(ext) ? `<button class="btn sm ghost" data-text="${esc(f)}">${esc(t('Read'))}</button>` : '';
      return `<li><span class="f" title="${esc(f)}">${esc(name)}</span>${act}<button class="btn sm ghost" data-copy="${esc(f)}">${esc(t('Path'))}</button></li>`;
    }).join('')}</ul></div>`);
  }
  tab.innerHTML = blocks.join('');
  $$('[data-v]', tab).forEach((x) => (x.onclick = () => loadVariant(x.dataset.v)));
  $$('[data-copy]', tab).forEach((x) => (x.onclick = () => copy(x.dataset.copy)));
  $$('[data-img]', tab).forEach((x) => (x.onclick = () => lightbox([{ src: fileUrl(x.dataset.img), caption: x.dataset.img }])));
  $$('[data-text]', tab).forEach((x) => (x.onclick = () => textDialog(x.dataset.text.split('/').pop(), x.dataset.text)));
  $$('[data-untag]', tab).forEach((x) => (x.onclick = () => saveMeta({ tags: d.tags.filter((y) => y !== x.dataset.untag) })));
  const cat = $('#m-cat', tab);
  cat.onchange = () => saveMeta({ category: cat.value });
  $('#m-tag', tab).onkeydown = (e) => {
    if (e.key === 'Enter' && e.target.value.trim()) {
      const add = e.target.value.split(',').map((x) => x.trim().replace(/^#/, '').toLowerCase()).filter(Boolean);
      e.target.value = '';
      saveMeta({ tags: [...d.tags, ...add] });
    }
  };
  $$('[data-act]', tab).forEach((x) => (x.onclick = () => baselineAction(x.dataset.act)));
}

async function saveMeta(body) {
  try {
    await assetApi(state.id, '/meta', { method: 'PUT', body });
    await fetchAssets();
    await fetchDetail();
    if (body.category != null) toast(t('{a} moved to {c}', { a: esc(state.detail.name), c: `<b>${esc(body.category || state.detail.folder)}</b>` }));
  } catch (e) { toast(esc(e.message), 'warn'); }
}

async function baselineAction(act) {
  try {
    if (act === 'cmp-prev') return setCompare('split', 'baseline');
    if (act === 'snapshot') {
      await assetApi(state.id, '/snapshot', { method: 'POST', body: { variant: state.variant } });
      toast(t('This version is now the previous one'), 'ok');
      await fetchDetail();
      if (state.compare?.target === 'baseline') await loadCompareTarget();
      return;
    }
    if (act === 'revert') {
      const b = state.detail.baseline;
      if (!(await confirmDialog(t('Put {f} back to {h} ({when})? The version on disk now becomes the previous one, so this can be undone the same way.', { f: b.source, h: b.hash.slice(0, 7), when: ago(b.at) }), t('Put it back')))) return;
      await assetApi(state.id, '/revert', { method: 'POST', body: {} });
      toast(t('Reverted. The replaced version is kept as the previous one.'), 'ok');
    }
  } catch (e) { toast(esc(e.message), 'warn', 8000); }
}

// ── history: one chronological feed ──────────────────────────────────────────

function renderHistory() {
  const d = state.detail, tab = $('#tab-history');
  if (!d) { tab.innerHTML = ''; return; }
  // Size and triangle change against the version before, per variant.
  const lastBy = {};
  const ev = d.history.map((e) => {
    const out = { ...e };
    if (e.type === 'version') { out.prev = lastBy[e.variant] || null; lastBy[e.variant] = e; }
    return out;
  });
  for (const n of d.notes) {
    ev.push({ type: 'note', at: n.created, n });
    for (const r of n.thread || []) ev.push({ type: 'reply', at: r.at, n, r });
  }
  // The build's steps; a step that a live export closed is already its version's entry.
  if (d.live) {
    const filed = new Set(d.history.filter((e) => e.type === 'version' && e.phase).map((e) => `${e.phase}|${e.step || ''}`));
    ev.push({ type: 'build', at: d.live.started, text: t('Build started') });
    for (const s of d.live.steps || []) if (!filed.has(`${s.phase}|${s.text || ''}`)) ev.push({ type: 'step', at: s.at, st: s });
    if (d.live.ended) ev.push({ type: 'build', at: d.live.ended, text: t('Build done') });
  }
  // Checks on the shipped file: where it stands now, at the newest version.
  const warns = d.checks && d.checks.shipped ? checksFor(d.checks.shipped).filter((r) => r.level === 'warn').length : 0;
  const shippedV = d.checks?.shipped && d.history.filter((e) => e.type === 'version' && e.variant === d.checks.shipped).slice(-1)[0];
  if (shippedV) ev.push({ type: 'check', at: shippedV.at, text: warns ? tp(warns, 'Checks on {v}: {n} to look at', 'Checks on {v}: {n} to look at', { v: d.checks.shipped }) : t('Checks on {v}: all fine', { v: d.checks.shipped }), after: true });
  ev.sort((x, y) => (x.at < y.at ? 1 : x.at > y.at ? -1 : x.after ? -1 : y.after ? 1 : 0));
  const current = new Map(d.variants.map((v) => [v.label, v.hash]));
  const key = keyOf(d.id);
  const li = (cls, e, body) => `<li class="ev-${cls}"><div class="t">${esc(ago(e.at))} · ${esc(stamp(e.at))}</div>${body}</li>`;
  const pctSpan = (x, what) => (x ? `<span class="${x > 0 ? 'up' : 'down'}">${fmtPct(x, true)} ${esc(what)}</span>` : '');
  const items = ev.map((e) => {
    if (e.type === 'version') {
      const p = e.prev;
      const dz = p ? frac(e.size, p.size) : 0, dt = p && p.tris && e.tris != null ? frac(e.tris, p.tris) : 0;
      const img = d.thumbs.includes(e.hash) ? `<img src="${esc(fileUrl(`.kiln-studio/cache/thumbs/${key}/${e.hash}.webp`))}" alt="${esc(t('Render of this version'))}" data-full="${esc(e.hash)}">` : '';
      const isCur = current.get(e.variant) === e.hash;
      const phase = e.phase ? ` <span class="phase">${esc(t(e.phase))}</span>${e.step ? ` ${esc(e.step)}` : ''}` : '';
      return li('version', e, `<div class="h">${esc(e.first ? t('First seen') : t('New version'))} · ${esc(e.variant)} · ${fmtB(e.size)}${e.tris != null ? ` · ${esc(t('{n} tris', { n: fmtK(e.tris) }))}` : ''} ${pctSpan(dz, t('size'))} ${pctSpan(dt, t('tris'))}</div><div class="b"><span class="mono">${esc(e.hash.slice(0, 7))}</span>${isCur ? ` <span class="status addressed">${esc(t('current'))}</span>` : ''}${phase}</div>${img}`);
    }
    if (e.type === 'build') return li('build', e, `<div class="h">${esc(t('Build'))} · ${esc(e.text)}</div>`);
    if (e.type === 'step') return li('build', e, `<div class="h">${esc(t('Build'))} · <span class="phase">${esc(t(e.st.phase || 'step'))}</span></div>${e.st.text ? `<div class="b">${esc(e.st.text)}</div>` : ''}`);
    if (e.type === 'check') return li('check', e, `<div class="h">${esc(e.text)}</div>`);
    if (e.type === 'log') return li('log', e, `<div class="h">${esc(e.by === 'claude' ? t('Claude: changelog') : t('You: changelog'))}</div><div class="b">${esc(e.text)}</div>`);
    if (e.type === 'baseline') return li('baseline', e, `<div class="h">${esc(t('Kept {v} {h} as the previous version', { v: e.variant, h: e.hash.slice(0, 7) }))}</div><div class="b dim">${esc(e.reason)}</div>`);
    if (e.type === 'revert') return li('revert', e, `<div class="h">${esc(t('Put back {v} {h}', { v: e.variant, h: e.hash.slice(0, 7) }))}</div>`);
    if (e.type === 'note') return li('note', e, `<div class="h">${esc(e.n.anchor ? t('You noted pin {n}', { n: noteNumber(e.n) }) : t('You noted note {n} (whole model)', { n: noteNumber(e.n) }))}</div><div class="b">${esc(e.n.text)}</div>`);
    if (e.type === 'reply') {
      const who = e.r.by === 'claude' ? 'Claude' : t('You');
      return li(`reply-${e.r.by === 'claude' ? 'claude' : 'you'}`, e, `<div class="h">${esc(who)} ${e.r.status ? `${esc(t('marked note {n}', { n: noteNumber(e.n) }))} <span class="status ${e.r.status}">${esc(statusLabel(e.r.status))}</span>` : esc(t('replied on note {n}', { n: noteNumber(e.n) }))}</div>${e.r.text ? `<div class="b">${esc(e.r.text)}</div>` : ''}`);
    }
    return '';
  });
  tab.innerHTML = items.length
    ? `<ol class="feed">${items.join('')}</ol>`
    : `<div class="empty-notes"><b>${esc(t('No history yet'))}</b>${esc(t('Studio records each new version of the model it sees, with its size and triangle count, and every note and reply.'))}</div>`;
  $$('img[data-full]', tab).forEach((img) => (img.onclick = () => lightbox([{ src: img.src, caption: img.dataset.full }])));
}

// ── animation ────────────────────────────────────────────────────────────────

const PLAY_SVG = '<svg viewBox="0 0 24 24"><path d="M7 5l12 7-12 7z"/></svg>', PAUSE_SVG = '<svg viewBox="0 0 24 24"><path d="M8 5v14M16 5v14"/></svg>';
function setupAnimBar() {
  const clips = state.clientStats?.clips || [];
  $('#animbar').hidden = !clips.length;
  stage.classList.toggle('has-anim', !!clips.length);
  if (!clips.length) return;
  $('#a-clip').innerHTML = clips.map((c) => `<option value="${esc(c.name)}"${c.name === viewer.clipName ? ' selected' : ''}>${esc(c.name)} · ${fmtD(c.duration, 2)} s</option>`).join('');
  setPlaying(viewer.playing);
}
function setPlaying(on) {
  viewer.playing = on;
  $('#a-play').innerHTML = on ? PAUSE_SVG : PLAY_SVG;
  $('#a-play').setAttribute('aria-label', on ? t('Pause (Space)') : t('Play (Space)'));
  viewer.a.proxyAt = -1;
}
$('#a-play').onclick = () => setPlaying(!viewer.playing);
$('#a-clip').onchange = (e) => viewer.playClip(e.target.value);
$('#a-speed').onchange = (e) => (viewer.speed = +e.target.value);
$('#a-time').addEventListener('input', (e) => { scrubbing = true; viewer.seek(+e.target.value * viewer.clipDuration); viewer.onAnimate(); pinsDirty = true; });
$('#a-time').addEventListener('change', () => { scrubbing = false; });

// ── background renders: thumbnails, and "after" views of addressed notes ─────

const jobs = [];
const queued = new Set();
let working = false;

function queueThumb(id, v) {
  const key = `thumb:${id}:${v.hash}`;
  if (queued.has(key)) return;
  queued.add(key);
  jobs.push({ key, run: async () => {
    const shot = await off().render(fileUrl(v.file, v.hash), v.ext, { w: 320, h: 240 });
    const r = await assetApi(id, '/thumb', { method: 'POST', body: { hash: v.hash, shot } });
    const a = state.byId.get(id);
    if (a && a.variants[0].hash === v.hash) {
      a.thumb = r.thumb;
      patchRow(id, false);
      renderRail();
    }
    if (state.detail?.id === id && !state.detail.thumbs.includes(v.hash)) { state.detail.thumbs.push(v.hash); renderHistory(); }
  } });
  pump();
}

function queueAfterShots(detail) {
  for (const p of detail.pending || []) {
    const key = `after:${detail.id}:${p.reply}`;
    if (queued.has(key)) continue;
    const n = detail.notes.find((x) => x.id === p.note);
    const v = detail.variants.find((x) => x.label === p.variant);
    if (!n || !v || !n.camera) continue;
    queued.add(key);
    jobs.unshift({ key, run: async () => {
      // The note's own view and close-up, of the version Claude exported.
      const shots = await off().noteShots(fileUrl(v.file, v.hash), v.ext, n, { bg: viewer.opts.bg });
      await assetApi(detail.id, `/notes/${n.id}/thread/${p.reply}/shot`, { method: 'POST', body: shots });
    } });
  }
  pump();
}

async function queuePendingShots() {
  for (const a of state.assets) {
    if (a.pending_shots && a.id !== state.id && !queued.has(`detail:${a.id}`)) {
      queued.add(`detail:${a.id}`);
      try { queueAfterShots(await assetApi(a.id)); } catch { /* next time */ }
      queued.delete(`detail:${a.id}`);
    }
  }
}

async function pump() {
  if (working) return;
  working = true;
  try {
    while (jobs.length) {
      const j = jobs.shift();
      try { await j.run(); } catch (e) { console.warn('kiln-studio job', j.key, e); }
      await new Promise((r) => setTimeout(r, 30)); // keep the main view smooth
    }
  } finally { working = false; }
}

// ── live updates from the server ─────────────────────────────────────────────

let assetsTimer, detailTimer, lost = false;
function liveEvents() {
  const es = new EventSource('/api/events');
  es.onopen = () => { if (lost) { lost = false; toast(t('Reconnected to Studio'), 'ok'); fetchAssets(); if (state.id) fetchDetail(); } };
  es.onerror = () => { if (!lost) { lost = true; toast(t('Lost the Studio server. Restart it with /kiln studio; this page reconnects on its own.'), 'warn', 12000); } };
  es.onmessage = async (msg) => {
    const ev = JSON.parse(msg.data);
    if (ev.type === 'assets') {
      clearTimeout(assetsTimer);
      assetsTimer = setTimeout(async () => {
        await fetchAssets();
        if (state.id && !state.byId.has(state.id)) { toast(t('This model is gone from the project'), 'warn'); state.id = null; state.detail = null; renderEmpty(); renderAll(); }
      }, 150);
    }
    if (ev.type === 'model' && ev.id === state.id) {
      const v = currentVariant();
      const wasNewest = v && v.label === state.detail.variants[0].label;
      const old = new Map(state.detail.variants.map((x) => [x.label, x.hash]));
      await fetchDetail();
      const changedLabels = Object.entries(ev.variants).filter(([l, h]) => old.get(l) !== h).map(([l]) => l);
      const newest = state.detail.variants[0].label;
      if (changedLabels.length && !(changedLabels.length === 1 && changedLabels[0] === 'live')) toast(t('{a} reloaded: {v}', { a: `<b>${esc(state.detail.name)}</b>`, v: esc(changedLabels.join(', ')) }), 'ok');
      // Watching the newest stage (the live build, then _final): follow it.
      if (wasNewest && newest !== v.label) await loadVariant(newest, { keepCamera: true });
      else if (v && changedLabels.includes(v.label)) await loadVariant(v.label, { keepCamera: true });
      // A model being built grows: keep the angle the user chose, fit it again.
      if (currentVariant()?.label === 'live' && state.detail.live?.state === 'building' && !state.compare) viewer.frame();
      else if (!v || !state.detail.variants.some((x) => x.label === v.label)) await loadVariant(state.detail.variants[0].label, { keepCamera: true });
      markSeen(state.byId.get(state.id));
      for (const x of state.detail.variants) if (!state.detail.thumbs.includes(x.hash)) queueThumb(state.id, x);
      queueAfterShots(state.detail);
    }
    if (ev.type === 'work') {
      const prev = state.work;
      if (ev.work?.active && !state.byId.has(ev.work.active)) await fetchAssets();
      onWork(ev.work, prev);
    }
    if (ev.type === 'live') {
      // Nothing open yet: open the model being built, to watch it.
      if (!state.id && ev.live?.state === 'building') {
        if (!state.byId.has(ev.id)) await fetchAssets();
        go(ev.id);
        return;
      }
      if (ev.id === state.id) {
        const before = state.detail?.live?.phase;
        await fetchDetail();
        const live = state.detail.live;
        if (live?.state === 'building' && live.phase && live.phase !== before) {
          const last = (live.steps || []).slice(-1)[0];
          toast(esc(t('Building: {p}', { p: t(live.phase) }) + (last?.text ? ` · ${last.text}` : '')));
        } else if (live?.state === 'done') toast(t('Build done'), 'ok');
      }
    }
    if (ev.type === 'notes' && ev.id === state.id) {
      clearTimeout(detailTimer);
      detailTimer = setTimeout(async () => {
        const before = new Set(state.detail.notes.flatMap((n) => (n.thread || []).map((r) => r.id)));
        await fetchDetail();
        const fresh = state.detail.notes.flatMap((n) => (n.thread || []).filter((r) => !before.has(r.id) && r.by === 'claude').map((r) => ({ n, r })));
        if (fresh.length) {
          toast(fresh.length === 1 ? t('Claude replied on note {n}', { n: noteNumber(fresh[0].n) }) : t('Claude replied on {n} notes', { n: fresh.length }), 'ok');
          requestAnimationFrame(() => fresh.forEach(({ n }) => $(`#note-list .note[data-id="${CSS.escape(n.id)}"]`)?.classList.add('flash')));
        }
        queueAfterShots(state.detail);
      }, 120);
    }
    onEvent(ev);
  };
}
// Further listeners (the MCP bridge, …) hook here.
const eventHooks = [];
function onEvent(ev) { for (const h of eventHooks) h(ev); }
function reportSelection() { for (const h of selectionHooks) h(); }
const selectionHooks = [];

// ── keys ─────────────────────────────────────────────────────────────────────

const KEYS = [
  ['/', 'Find a model'],
  ['↑ ↓', 'Previous, next model'],
  ['[  ]  \\', 'Collapse or expand the left panel, the right panel, both'],
  ['1 – 6', 'Front, back, left, right, top, three-quarter'],
  ['F', 'Frame the model'],
  ['S · ⇧S', 'Next, previous shading'],
  ['W G B K', 'Wire, grid, size, bones'],
  ['P', 'Show or hide the pins'],
  ['C · ⇧C', 'Compare with the previous version · switch split / side by side'],
  ['N', 'Pin a note, then click the model'],
  ['M', 'Note on the whole model'],
  ['⌘↵ · Esc', 'Save the note · cancel'],
  ['Space', 'Play, pause the animation'],
  ['⌘K', 'Every command, by name'],
  ['?', 'This list'],
];
function showKeys() {
  $('#keys-list').innerHTML = KEYS.map(([k, what]) => `<dt>${esc(k)}</dt><dd>${esc(t(what))}</dd>`).join('');
  $('#keys').showModal();
}

const keyActions = {
  '/': () => { if (!isOpen(left)) setPanel(left, true); setTimeout(() => $('#search').focus(), narrow() ? 0 : 50); },
  '[': () => togglePanel(left), ']': () => togglePanel(right),
  '\\': () => { const open = !(isOpen(left) && isOpen(right)); setPanel(left, open); setPanel(right, open); },
  '?': () => showKeys(),
  ArrowDown: () => step(1), ArrowUp: () => step(-1),
};
const modelKeys = {
  1: () => viewer.view('front'), 2: () => viewer.view('back'), 3: () => viewer.view('left'), 4: () => viewer.view('right'), 5: () => viewer.view('top'), 6: () => viewer.view('iso'),
  f: () => viewer.frame(), s: () => cycleShade(1), S: () => cycleShade(-1),
  w: () => setOpt('wire', !viewer.opts.wire), g: () => setOpt('grid', !viewer.opts.grid), b: () => setOpt('bounds', !viewer.opts.bounds),
  k: () => { if (state.clientStats?.skinned) setOpt('skeleton', !viewer.opts.skeleton); },
  p: () => { if (!$('#pinsctl').hidden) togglePins(); },
  c: () => setCompare(state.compare ? null : 'split'), C: () => switchCompareMode(state.compare?.mode === 'split' ? 'side' : 'split'),
  n: () => (state.pinning ? cancelDraft() : startPin()), m: () => startGeneral(),
  ' ': () => { if (state.clientStats?.clips?.length) setPlaying(!viewer.playing); },
};

document.addEventListener('keydown', (e) => {
  const typing = e.target.closest?.('input, textarea, select, [contenteditable]');
  if (e.key === 'Escape') {
    if (document.querySelector('dialog[open]')) return;
    if (state.pinning || state.draft) { cancelDraft(); return; }
    if (typing) { e.target.blur?.(); return; }
    if (!pop.hidden) { setPop(false); return; }
    if (state.compare) { setCompare(null); return; }
    if (state.hl) highlight(state.hl);
    return;
  }
  if (typing || e.metaKey || e.ctrlKey || e.altKey || document.querySelector('dialog[open]')) return;
  const k = e.key;
  // Shift picks the other way where it means something (⇧S, ⇧C); otherwise the same key.
  const fn = keyActions[k] || (state.detail ? (modelKeys[k] ?? (k.length === 1 ? modelKeys[k.toLowerCase()] : null)) : null);
  if (fn) { e.preventDefault(); fn(); }
});

// ── command palette (⌘K): every action, with its key ────────────────────────
// Each command: its group, its words, the key that does the same, and whether it
// applies now (`when`). Typing filters on every word; Enter runs the one picked.

const hasModel = () => !!state.detail && !!viewer.a.model;
function commands() {
  const C = [];
  // label: English, translated when shown; or { text } already in the user's language.
  const add = (group, label, keys, run, when = () => true) => C.push({ group, label, keys, run, when });
  add('List', 'Find a model', ['/'], keyActions['/']);
  add('List', 'Next model', ['↓'], () => step(1), () => state.assets.length > 1);
  add('List', 'Previous model', ['↑'], () => step(-1), () => state.assets.length > 1);
  add('List', 'Group by folders', [], () => { state.group = prefs.group = 'folders'; savePrefs(); syncGroup(); flipRender(); }, () => state.group !== 'folders');
  add('List', 'Group by state', [], () => { state.group = prefs.group = 'state'; savePrefs(); syncGroup(); flipRender(); }, () => state.group !== 'state');
  add('List', 'Compact rows', [], () => { state.density = prefs.density = 'compact'; savePrefs(); syncDensity(); renderList(); }, () => state.density !== 'compact');
  add('List', 'Normal rows', [], () => { state.density = prefs.density = 'normal'; savePrefs(); syncDensity(); renderList(); }, () => state.density !== 'normal');
  for (const [k, label] of [['addressed', 'Show the notes to check'], ['open', 'Show the open notes'], ['working', "Show the models in Claude's run"], ['building', 'Show the models being built']]) {
    add('List', label, [], () => { state.pill = k; renderStrip(); renderList(); if (!isOpen(left)) setPanel(left, true); });
  }
  add('List', 'Show every model', [], () => { state.pill = null; state.tags.clear(); $('#search').value = ''; $('#filter').value = 'all'; renderTags(); renderStrip(); renderList(); }, () => state.pill || state.tags.size || $('#search').value || $('#filter').value !== 'all');
  add('Panels', 'Fold or unfold the model list', ['['], keyActions['[']);
  add('Panels', 'Fold or unfold the notes panel', [']'], keyActions[']']);
  add('Panels', 'Fold or unfold both panels', ['\\'], keyActions['\\']);
  for (const [tab, label] of [['notes', 'Notes'], ['checks', 'Checks'], ['details', 'Details'], ['history', 'History']]) add('Panels', `Open the ${label} tab`, [], () => ensureRight(tab), hasModel); // the four strings are in the dictionary
  for (const [k, v, label] of [['1', 'front', 'Front view'], ['2', 'back', 'Back view'], ['3', 'left', 'Left view'], ['4', 'right', 'Right view'], ['5', 'top', 'Top view'], ['6', 'iso', 'Three-quarter view']]) add('View', label, [k], () => viewer.view(v), hasModel);
  add('View', 'Frame the model', ['F'], () => viewer.frame(), hasModel);
  for (const [m, label] of [['lit', 'Lit'], ['unlit', 'Unlit'], ['clay', 'Clay'], ['normals', 'Normals'], ['uv', 'UV checker'], ['faces', 'Faces: back faces in red']]) add('Shading', `Shading: ${label}`, [], () => setOpt('shade', m), () => hasModel() && viewer.opts.shade !== m);
  add('Shading', 'Next shading', ['S'], () => cycleShade(1), hasModel);
  add('Shading', 'Previous shading', ['⇧S'], () => cycleShade(-1), hasModel);
  add('View', 'Wireframe on or off', ['W'], () => setOpt('wire', !viewer.opts.wire), hasModel);
  add('View', 'Grid on or off', ['G'], () => setOpt('grid', !viewer.opts.grid), hasModel);
  add('View', 'Sizes on or off', ['B'], () => setOpt('bounds', !viewer.opts.bounds), hasModel);
  add('View', 'Bones on or off', ['K'], () => setOpt('skeleton', !viewer.opts.skeleton), () => hasModel() && state.clientStats?.skinned);
  add('View', 'Next background', [], () => setOpt('bg', { dark: 'mid', mid: 'light', light: 'dark' }[viewer.opts.bg]), hasModel);
  add('View', 'Play or pause the animation', ['Space'], () => setPlaying(!viewer.playing), () => hasModel() && state.clientStats?.clips?.length);
  add('Pins', 'Show or hide the pins', ['P'], togglePins, () => hasModel() && !$('#pinsctl').hidden);
  add('Pins', 'Hide fixed pins on or off', [], () => setPinFilter('hideFixed', !state.hideFixed), () => hasModel() && !$('#pinsctl').hidden);
  add('Pins', 'Hide pins behind the model on or off', [], () => setPinFilter('hideBehind', !state.hideBehind), () => hasModel() && !$('#pinsctl').hidden);
  add('Compare', 'Compare with the previous version', ['C'], () => setCompare('split'), () => hasModel() && !state.compare && compareTargets().length);
  add('Compare', 'Compare side by side', ['⇧C'], () => (state.compare ? switchCompareMode('side') : setCompare('side')), () => hasModel() && state.compare?.mode !== 'side' && compareTargets().length);
  add('Compare', 'Compare with a divider', ['⇧C'], () => switchCompareMode('split'), () => state.compare?.mode === 'side');
  add('Compare', 'Stop comparing', ['C'], () => setCompare(null), () => !!state.compare);
  add('Notes', 'Pin a note, then click the model', ['N'], startPin, hasModel);
  add('Notes', 'Note on the whole model', ['M'], () => startGeneral(), hasModel);
  add('Notes', 'Copy the command for Claude', [], () => copy(`/kiln studio ${state.detail.id}`), () => hasModel() && state.detail.counts.open > 0);
  add('Notes', 'Show all notes, closed ones too', [], () => { setNoteFilter('all'); renderNotes(); renderPins(); ensureRight('notes'); }, () => hasModel() && state.noteFilter !== 'all');
  add('Notes', 'Show the active notes only', [], () => { setNoteFilter('active'); renderNotes(); renderPins(); }, () => hasModel() && state.noteFilter !== 'active');
  add('Help', 'Keyboard shortcuts', ['?'], showKeys);
  for (const run of paletteExtras) run(add);
  for (const a of state.assets) add('Model', { text: t('Open {name}', { name: a.name }) }, [], () => go(a.id), () => a.id !== state.id);
  return C.filter((c) => { try { return c.when(); } catch { return false; } });
}
const paletteExtras = [];

let palItems = [], palSel = 0;
const labelOf = (c) => c.label.text || t(c.label);
function openPalette() {
  const d = $('#palette');
  if (d.open) { d.close(); return; }
  document.querySelector('dialog[open]')?.close();
  $('#pal-q').value = '';
  renderPalette();
  d.showModal();
  $('#pal-q').focus();
}
function renderPalette() {
  const words = $('#pal-q').value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  palItems = commands().filter((c) => {
    const hay = `${t(c.group)} ${labelOf(c)} ${c.label.text || c.label} ${c.keys.join(' ')}`.toLowerCase();
    return words.every((w) => hay.includes(w));
  });
  // Models only once you type: the list starts with what you can do.
  if (!words.length) palItems = palItems.filter((c) => c.group !== 'Model');
  palSel = Math.min(palSel, Math.max(0, palItems.length - 1));
  $('#pal-list').innerHTML = palItems.length
    ? palItems.map((c, i) => `<li role="option" id="pal-${i}" data-i="${i}" aria-selected="${i === palSel}"><span class="g">${esc(t(c.group))}</span><span class="l">${esc(labelOf(c))}</span><span class="k">${c.keys.map((k) => `<kbd>${esc(k)}</kbd>`).join('')}</span></li>`).join('')
    : `<li class="empty">${esc(t('No command matches'))}</li>`;
  $('#pal-q').setAttribute('aria-activedescendant', palItems.length ? `pal-${palSel}` : '');
  $$('#pal-list li[data-i]').forEach((li) => {
    li.onmousemove = () => { if (palSel !== +li.dataset.i) { palSel = +li.dataset.i; markPalette(); } };
    li.onclick = () => runPalette(+li.dataset.i);
  });
}
function markPalette() {
  $$('#pal-list li[data-i]').forEach((li) => li.setAttribute('aria-selected', String(+li.dataset.i === palSel)));
  $(`#pal-${palSel}`)?.scrollIntoView({ block: 'nearest' });
  $('#pal-q').setAttribute('aria-activedescendant', `pal-${palSel}`);
}
function runPalette(i) {
  const c = palItems[i];
  if (!c) return;
  $('#palette').close();
  setTimeout(() => c.run(), 0);
}
$('#pal-q').addEventListener('input', () => { palSel = 0; renderPalette(); });
$('#pal-q').addEventListener('keydown', (e) => {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); palSel = (palSel + (e.key === 'ArrowDown' ? 1 : -1) + palItems.length) % Math.max(1, palItems.length); markPalette(); }
  if (e.key === 'Enter') { e.preventDefault(); runPalette(palSel); }
});
$('#palette').addEventListener('click', (e) => { if (e.target === $('#palette')) $('#palette').close(); });
$('#t-palette').onclick = openPalette;
// ⌘K / Ctrl+K from anywhere, typing or not.
document.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && !e.altKey && e.key.toLowerCase() === 'k') { e.preventDefault(); e.stopImmediatePropagation(); openPalette(); }
}, true);

// ── boot ─────────────────────────────────────────────────────────────────────

function fromHash() {
  const id = location.hash.slice(1).split('/').map(decodeURIComponent).join('/');
  if (id && id !== state.id) openAsset(id);
}
window.addEventListener('hashchange', fromHash);

(async () => {
  applyI18n();
  initPanels();
  setTab(prefs.tab || 'notes');
  syncToolbar();
  syncGroup(); syncDensity();
  renderEmpty();
  try {
    await fetchAssets();
  } catch (e) {
    toast(t('Could not reach the Studio server: {e}', { e: esc(e.message) }), 'warn', 15000);
    return;
  }
  liveEvents();
  fromHash();
  window.__studio = { state, viewer, openAsset, setCompare, startPin, startGeneral, get detail() { return state.detail; } };
})();

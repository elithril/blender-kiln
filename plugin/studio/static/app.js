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
import { t, tp, N_, applyI18n, setUnits, getUnits, setLang, getLang, loadLanguage, setCheckMessages, renderMsg, LANGS, fmtN, fmtK, fmtB, fmtD, fmtLen, fmtPct, ago, stamp } from './i18n.js';

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
// Words shown through t() from a variable: listed so the extractor finds them.
N_('config'); N_('brief'); N_('source'); N_('import'); N_('cleanup'); N_('texture'); N_('rig'); N_('animate'); N_('optimize'); N_('export'); N_('step');
N_('front'); N_('back'); N_('left'); N_('right'); N_('top'); N_('type'); N_('tier'); N_('target'); N_('style');
N_('done'); N_('pending'); N_('failed'); N_('running'); N_('skipped');
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
// Commands other parts add to the ⌘K palette: fn(add).
const paletteExtras = [];

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
viewer.onChange = () => { pinsDirty = occlDirty = true; if (state.detail) reportCamera(); };
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
  $$('[data-opt]').forEach((b) => { b.classList.toggle('on', !!o[b.dataset.opt]); b.setAttribute('aria-pressed', String(!!o[b.dataset.opt])); });
  $('#tb-shade-select').value = o.shade;
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
  if (k === 'shade') reportSelection();
  prefs[k] = v; savePrefs();
  if (k === 'bg') stage.dataset.bg = v;
  syncToolbar();
}
$$('#toolbar [data-shade]').forEach((b) => (b.onclick = () => setOpt('shade', b.dataset.shade)));
$$('#tb-toggles [data-opt]').forEach((b) => (b.onclick = () => setOpt(b.dataset.opt, !viewer.opts[b.dataset.opt])));
$('#t-bg').onclick = () => setOpt('bg', { dark: 'mid', mid: 'light', light: 'dark' }[viewer.opts.bg]);
$$('#views [data-view]').forEach((b) => (b.onclick = () => viewer.view(b.dataset.view)));
$('#t-frame').onclick = () => viewer.frame();
$('#t-keys').onclick = () => showKeys();
const cycleShade = (d) => setOpt('shade', SHADES[(SHADES.indexOf(viewer.opts.shade) + d + SHADES.length) % SHADES.length]);
$('#tb-shade-select').onchange = (e) => setOpt('shade', e.target.value);

// The bottom bar fits the view, whatever the language and the panels: first the six
// shading buttons become one list, then the display toggles fold into Options (a row
// that opens above the bar), and only then does the bar wrap. Measured, not guessed:
// each step is taken only while the bar's content is wider than the bar.
function fitToolbar() {
  const tb = $('#toolbar'), toggles = $('#tb-toggles'), more = $('#t-more'), pop = $('#tb-more-pop');
  const wasOpen = !pop.hidden && toggles.parentElement === pop;
  tb.classList.remove('tb-select-on', 'tb-wrap');
  $('#tb-shade').hidden = false; $('#tb-shade-select').hidden = true;
  if (toggles.parentElement !== tb) tb.insertBefore(toggles, more);
  more.hidden = true; pop.hidden = true; more.setAttribute('aria-expanded', 'false');
  if ($('#bottom').hidden) return;
  const fits = () => tb.scrollWidth <= tb.clientWidth + 1;
  if (fits()) return;
  tb.classList.add('tb-select-on');
  $('#tb-shade').hidden = true; $('#tb-shade-select').hidden = false;
  if (fits()) return;
  pop.appendChild(toggles);
  more.hidden = false;
  if (wasOpen) { pop.hidden = false; more.setAttribute('aria-expanded', 'true'); }
  if (fits()) return;
  tb.classList.add('tb-wrap');
}
$('#t-more').onclick = (e) => {
  e.stopPropagation();
  const pop = $('#tb-more-pop');
  pop.hidden = !pop.hidden;
  $('#t-more').setAttribute('aria-expanded', String(!pop.hidden));
};
document.addEventListener('click', (e) => {
  const pop = $('#tb-more-pop');
  if (!pop.hidden && !pop.contains(e.target) && !e.target.closest('#t-more')) { pop.hidden = true; $('#t-more').setAttribute('aria-expanded', 'false'); }
});
let fitRaf = 0;
const fitSoon = () => { cancelAnimationFrame(fitRaf); fitRaf = requestAnimationFrame(fitToolbar); };
new ResizeObserver(fitSoon).observe(stage);

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
// Claude's own runs from this page (worker.py) first, then a kiln command's (studio.py work).
const dotOf = (a) => claudeDot(a) || state.work?.dots[a.id]?.state;
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
  // The folder's name, the whole path on hover: the end of a long path is what tells projects apart.
  $('#project').textContent = data.name;
  $('#project').title = data.root;
  $('#logo').title = `Kiln Studio · ${data.root}`;
  document.title = `${data.name} · Kiln Studio`;
  if (claude.status) claudeChanged();
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
    if (f === 'working') return ['active', 'queued', 'waiting'].includes(dotOf(a));
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
  ['works', N_('Claude works'), (a) => ['active', 'queued', 'waiting'].includes(dotOf(a))],
  ['building', N_('Building'), (a) => isBuilding(a)],
  ['check', N_('To check'), (a) => counts(a).addressed > 0 || dotOf(a) === 'done'],
  ['open', N_('Open notes'), (a) => counts(a).open > 0],
  ['clear', N_('Nothing to do'), () => true],
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
  const dotT = dot && (claudeDot(a) ? claudeDotTitle(a) : workTitle(state.work.dots[a.id]));
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
    working: state.assets.filter((a) => ['active', 'queued', 'waiting'].includes(dotOf(a))).length,
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
  $('#list').classList.toggle('working', !!w || claudeLive().length > 0);
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
  claude.partial = null;
  claude.view = null;
  if (!$('#tab-claude').hidden) claudeLoad(); else renderClaudeBadge();
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
    if (!keepCamera) {
      viewer.frame(VIEW_DIRS[prefs.view || 'iso'], { animate: false });
      // Settings → "A model opens in": that shading, whatever was used last.
      if (prefs.defaultShade && viewer.opts.shade !== prefs.defaultShade) { viewer.set('shade', prefs.defaultShade); syncToolbar(); }
    }
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
  fitSoon();
  const compareOk = compareTargets().length > 0;
  $('#t-compare').disabled = !compareOk;
  $('#t-compare').title = compareOk ? t('Compare with the previous version (C)') : t('No previous version kept for this model');
}

// The middle when no model is open: what to do next.
function renderEmpty() {
  const none = !state.id;
  document.body.classList.toggle('no-model', none);
  $('#empty').hidden = !none;
  $('#topbar').hidden = $('#views').hidden = $('#bottom').hidden = none;
  fitSoon();
  if (!none) return;
  if (state.assets.length) {
    $('#empty').innerHTML = `<div><p class="big">${esc(t('No model picked'))}</p><p>${esc(t('Choose one on the left. Models re-exported by Claude show up here on their own, and a model kiln is building opens here as it is built.'))}</p></div>`;
    return;
  }
  renderWelcome();
}

// ── welcome: an empty project ────────────────────────────────────────────────
// What to do first (welcomeCards: Create, Import, See an example), and what Studio can
// see of the setup. "unknown" where it cannot see: Claude's /kiln setup is the full scan.

const welcomeCards = [];
let setup = null;
function renderWelcome() {
  const el = $('#empty');
  // With Claude on, the form above is the way to create: the Create card would say it twice.
  const cards = welcomeCards.filter((c) => !(claude.status?.enabled && c.key === 'create')).map((c) => `<button class="wcard" data-w="${c.key}">${c.icon}<b>${esc(t(c.title))}</b><span>${esc(t(c.text))}</span></button>`).join('');
  el.innerHTML = `<div class="welcome">
    <div class="wlogo" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M16 3c3 6 9 8 9 16a9 9 0 0 1-18 0c0-5 3-7 4-11 1 3 3 4 3 4s-1-5 2-9z"/></svg></div>
    ${claude.status?.enabled ? `<p class="big">${esc(t('What do you want to make?'))}</p>
    <p>${esc(t('Describe a model in your words — what it is, its style, its size. Claude builds it in Studio\'s Blender and you watch it appear here.'))}</p>
    <form class="whero" id="w-hero"><textarea id="w-brief" rows="3" required placeholder="${esc(t('A sturdy oak barrel with iron hoops, worn, for a tavern game'))}" aria-label="${esc(t('Brief'))}"></textarea>
      <div class="row"><select id="w-target" aria-label="${esc(t('Made for'))}">${['web', 'desktop', 'ar', 'print'].map((v) => `<option value="${v}">${esc(t({ web: 'Web (glTF)', desktop: 'Unity / Unreal (FBX)', ar: 'AR (USDZ)', print: '3D print' }[v]))}</option>`).join('')}</select><span class="sp"></span><button class="btn accent" type="submit">${esc(t('Make it with Claude'))} <kbd>⌘↵</kbd></button></div></form>
    <p>${esc(t('Or start another way:'))}</p>` : `<p class="big">${esc(t('Nothing here yet'))}</p>
    <p>${esc(t('Studio shows every .glb, .gltf, .fbx and .obj under {root}. Start one of three ways:', { root: state.name || state.root }))}</p>`}
    <div class="wcards">${cards}</div>
    <h4>${esc(t('Your setup'))}${setup?.kiln ? ` <span class="dim">· kiln ${esc(setup.kiln)}</span>` : ''}</h4>
    <ul class="setup">${setup ? setup.rows.map(setupRow).join('') : `<li class="dim">${esc(t('Looking…'))}</li>`}</ul>
    <p class="dim small">${t('The full check, and help installing what is missing: {cmd} in Claude Code.', { cmd: '<code>/kiln setup</code>' })}</p>
  </div>`;
  $$('.wcard', el).forEach((b) => (b.onclick = () => welcomeCards.find((c) => c.key === b.dataset.w).run()));
  const hero = $('#w-hero', el);
  if (hero) {
    $('#w-brief').addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); hero.requestSubmit(); } });
    hero.onsubmit = async (e) => {
      e.preventDefault();
      const brief = $('#w-brief').value.trim();
      if (!brief) return;
      try {
        const r = await api('/api/requests', { method: 'POST', body: { brief, target: $('#w-target').value } });
        await api('/api/claude/jobs', { method: 'POST', body: { kind: 'create', request: r.id, lang: getLang() } });
        await claudeStatus();
        openClaudeView(`request:${r.id}`);
      } catch (err) { toast(esc(err.message), 'warn', 6000); }
    };
  }
  if (!setup) api('/api/status').then((s) => { setup = s; if (!state.assets.length && !state.id) renderWelcome(); }).catch(() => {});
}
function setupRow(r) {
  const d = r.data || {};
  const mark = { ok: '✓', missing: '✕', partial: '!', unknown: '?' }[r.state];
  const word = { ok: t('found'), missing: t('not found'), partial: t('in part'), unknown: t('unknown') }[r.state];
  let name = r.key, detail = r.detail;
  if (r.key === 'blender') {
    name = 'Blender';
    detail = r.state === 'ok' ? `${d.version || 'Blender'} · ${d.path}` : t('Kiln needs Blender 4.4 or later (blender.org); or set $BLENDER to where it is.');
  } else if (r.key === 'mcp') {
    name = t('Blender MCP connection');
    detail = [d.configured?.length ? t('set up in Claude Code: {names}', { names: d.configured.join(', ') }) : t('no Blender MCP server in Claude Code\'s settings for this project'),
      d.listening ? t('the add-on answers on port {p}', { p: d.port }) : t('nothing answers on port {p} (Blender closed, or the add-on off)', { p: d.port }),
      t('whether Claude is connected, only Claude can say')].join(' · ');
  } else if (r.key === 'skintokens') {
    name = t('SkinTokens (learned auto-rig)');
    detail = d.reason === 'no-tool' ? t('this version of kiln has no auto-rig tool to ask') : r.state === 'ok' ? t('installed') : r.state === 'missing' ? t('not installed') : (d.output || r.detail);
  } else if (r.key === 'claude') {
    name = 'Claude Code';
    detail = r.state === 'ok' ? `${d.version || ''} · ${d.path}` : t('Install it from claude.com/claude-code, then log in once in a terminal.');
  } else if (r.key === 'optimizers') {
    name = t('Optimisers (gltf-transform, gltfpack)');
    detail = r.state === 'ok' ? t('both found: kiln compresses meshes and textures with them') : t('found: {list} — without them kiln still exports, uncompressed', { list: (d.found || []).join(', ') || t('neither') });
  } else if (r.key === 'unimate') {
    name = t('UniMate (text to motion)');
    detail = d.reason === 'no-tool' ? t('this version of kiln has no UniMate tool') : r.state === 'ok' ? t('installed') : t('not installed: animates non-human bipeds and winged creatures from a sentence');
  }
  if (r.key === 'mcp' && claude.status?.enabled) detail = `${t('Studio\'s own Blender installs its add-on by itself.')} ${t('For your terminal:')} ${detail}`;
  const need = { required: t('required'), recommended: t('recommended'), optional: t('optional') }[r.need] || '';
  const meta = [need, r.size, r.licence].filter(Boolean).join(' · ');
  const canInstall = r.install && ['missing', 'partial'].includes(r.state) && claude.status?.enabled;
  return `<li class="${r.state}"><span class="mk" role="img" aria-label="${esc(word)}">${mark}</span><div><b>${esc(name)}</b> <span class="st">${esc(word)}</span>${meta ? `<div class="meta">${esc(meta)}</div>` : ''}<div class="dim small">${esc(detail)}</div></div>${canInstall ? `<button class="btn sm" data-install="${esc(r.key)}">${esc(t('Install with Claude'))}</button>` : ''}</li>`;
}
// Install with Claude: /kiln setup <part>, in the setup conversation, sizes and licences said first.
document.addEventListener('click', async (e) => {
  const b = e.target.closest('[data-install]');
  if (!b) return;
  try {
    await api('/api/claude/jobs', { method: 'POST', body: { kind: 'setup', text: b.dataset.install, lang: getLang() } });
    document.querySelector('dialog[open]')?.close();
    await claudeStatus();
    openClaudeView('setup');
  } catch (err) { toast(esc(err.message), 'warn', 6000); }
});
welcomeCards.push({
  key: 'example', title: N_('See an example'),
  text: N_("Adds kiln's barrel to this project, in kiln-example/, to try pins, checks and compare on. Delete the folder to remove it."),
  icon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4h10l2 4v12H5V8z M5 8h14 M9 4v4 M15 4v4"/></svg>',
  async run() {
    try {
      const { id } = await api('/api/example', { method: 'POST', body: {} });
      await fetchAssets();
      go(id);
      toast(t('The example is in {f}: pin a note on it with N.', { f: '<span class="mono">kiln-example/</span>' }), 'ok', 5000);
    } catch (e) { toast(esc(e.message), 'warn'); }
  },
});

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
  reportSelection();
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
  if (!$('#tab-claude').hidden) renderClaude();   // the note chip
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
  for (const k of ['notes', 'checks', 'details', 'history', 'claude']) $(`#tab-${k}`).hidden = k !== name;
  if (name === 'claude') claudeOpen();
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
  const view = n.shot ? b('view', N_('View'), 'ghost') : '';
  if (n.status === 'open') return b('reply', N_('Reply')) + b('wontfix', N_("Won't fix")) + b('edit', N_('Edit'), 'ghost') + b('delete', N_('Delete'), 'ghost') + view;
  if (n.status === 'addressed') return b('resolve', N_('Looks right'), 'accent') + b('reopen', N_('Not yet…')) + b('reply', N_('Reply'), 'ghost') + view;
  return b('reopen', N_('Reopen…')) + b('delete', N_('Delete'), 'ghost') + view;
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
    <header><span class="num ${a ? n.status : 'whole'}" aria-hidden="true"><span>${a ? num : 'M'}</span></span><span class="status ${n.status}">${esc(statusLabel(n.status))}</span><span class="kind">${esc(a ? t('pin {n}', { n: num }) : (n.by === 'claude' ? t('note {n} · from Claude', { n: num }) : t('note {n} · whole model', { n: num })))}${d.variants.length > 1 && n.version?.variant ? ` · ${esc(n.version.variant)}` : ''}</span><time title="${esc(stamp(n.created))}">${esc(ago(n.created))}</time></header>
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
  // The words come from the finding's codes, in the page's language; the English text
  // the server rendered is the fallback.
  const text = renderMsg(r.msg) || r.text, fixT = renderMsg(r.fix_msg) || r.fix, askT = renderMsg(r.ask_msg) || r.ask;
  r = { ...r, text, fix: fixT, ask: askT, label: t(r.label) };
  let more = '';
  if (r.entries?.length) more = `<ul class="sub">${r.entries.map((e) => `<li class="${e.level}">${esc(t(e.label || e.kind))}: ${esc(e.text)}</li>`).join('')}</ul>`;
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
    if (e.type === 'note') return li('note', e, `<div class="h">${esc(e.n.anchor ? t('You noted pin {n}', { n: noteNumber(e.n) }) : (e.n.by === 'claude' ? t('Claude noted note {n} (whole model)', { n: noteNumber(e.n) }) : t('You noted note {n} (whole model)', { n: noteNumber(e.n) })))}</div><div class="b">${esc(e.n.text)}</div>`);
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
// ── what the page shows, for Claude (the kiln-studio MCP server) ─────────────
// The page tells the server which model, stage, camera and note it shows (get_selection),
// and takes camera moves from it (set_camera).

let selTimer = 0;
function reportSelection() {
  clearTimeout(selTimer);
  selTimer = setTimeout(() => {
    const n = state.hl && state.detail?.notes.find((x) => x.id === state.hl);
    const body = {
      asset: state.id, variant: state.variant,
      camera: viewer.a.model ? viewer.cameraState() : null,
      note: n ? { id: n.id, number: noteNumber(n) } : null,
      compare: state.compare ? `${state.compare.mode}:${state.compare.target || ''}` : null,
      shading: viewer.opts.shade,
      visible: document.visibilityState === 'visible',
    };
    api('/api/selection', { method: 'POST', body }).catch(() => { /* the server is gone: the events say */ });
  }, 150);
}
// A camera that settles is worth reporting; one moving is not: at the end of an orbit at
// once, after a preset view's or a note's camera move once it stops.
let camSettle = 0;
const reportCamera = () => { clearTimeout(camSettle); camSettle = setTimeout(reportSelection, 500); };
viewer.controls.addEventListener('end', () => { clearTimeout(camSettle); camSettle = setTimeout(reportSelection, 250); });
document.addEventListener('visibilitychange', reportSelection);
// And every 15 s while the page is open, unchanged or not: Claude then knows the report
// is current (get_selection's confirmed_seconds_ago), not merely the last one sent.
setInterval(reportSelection, 15000);

// Open a model and wait for it to load, at most 15 s.
async function openAndWait(id) {
  if (!id || id === state.id || !state.byId.has(id)) return;
  go(id);
  const t0 = Date.now();
  while (!(state.detail?.id === id && $('#loading').hidden && viewer.a.model) && Date.now() - t0 < 15000) await new Promise((r) => setTimeout(r, 100));
}

// Present: the model alone, full window, for a second screen; Claude drives it from the
// terminal (kiln-studio MCP: present). Esc or the button leaves it.
function setPresent(on) {
  document.body.classList.toggle('present', on);
  $('#present-exit').hidden = !on;
  fitSoon();
}
$('#present-exit').onclick = () => setPresent(false);
if (new URLSearchParams(location.search).has('present')) setPresent(true);

// What Claude does to the page from the kiln-studio MCP server, said in a toast.
async function onControl(ev) {
  if (ev.action === 'open') {
    if (!state.byId.has(ev.asset)) { toast(t('Claude asked for "{id}", not in this project', { id: esc(ev.asset) }), 'warn'); return; }
    await openAndWait(ev.asset);
    if (ev.stage && ev.stage !== state.variant && state.detail?.variants.some((v) => v.label === ev.stage)) await loadVariant(ev.stage);
    toast(esc(t('Claude opened {name}', { name: state.detail?.name || ev.asset })), 'ok', 2500);
  } else if (ev.action === 'view') {
    if (ev.shading) setOpt('shade', ev.shading);
    if (ev.background) setOpt('bg', ev.background);
    for (const k of ['wire', 'grid', 'bounds', 'skeleton']) if (k in ev) setOpt(k, ev[k]);
    if (ev.view) viewer.view(ev.view);
    if (ev.frame) viewer.frame();
    toast(esc(t('Claude changed the view')), 'ok', 2000);
  } else if (ev.action === 'compare') {
    await setCompare(ev.mode === 'off' ? null : ev.mode, ev.target);
  } else if (ev.action === 'play') {
    const clips = state.clientStats?.clips || [];
    if (ev.clip && !clips.some((c) => c.name === ev.clip)) { toast(t('This model has no clip "{c}"', { c: esc(ev.clip) }), 'warn'); return; }
    if (ev.clip) { viewer.playClip(ev.clip); $('#a-clip').value = ev.clip; }
    if (ev.speed) { viewer.speed = ev.speed; $('#a-speed').value = String(ev.speed); }
    if ('time' in ev) { viewer.seek(Math.min(ev.time, viewer.clipDuration)); viewer.onAnimate(); }
    setPlaying('playing' in ev ? ev.playing : true);
  } else if (ev.action === 'present') {
    setPresent(ev.on);
  }
  reportSelection();
}

async function onCapture(ev) {
  // Every open page is asked and the first answer is kept: a hidden tab waits, so the one
  // the user has in front of them answers first.
  if (document.hidden) await new Promise((r) => setTimeout(r, 1500));
  try {
    const { shot } = viewer.screenshot({ whole: ev.full !== false });
    await api(`/api/view-image/${enc(ev.id)}`, { method: 'POST', body: { image: shot } });
  } catch (e) { console.warn('view image', e); }
}

async function onEvent(ev) {
  if (ev.type === 'claude' || ev.type === 'claude-text') return onClaude(ev);
  if (ev.type === 'control') return onControl(ev);
  if (ev.type === 'capture') return onCapture(ev);
  if (ev.type !== 'camera') return;
  await openAndWait(ev.asset);
  if (ev.view) viewer.view(ev.view);
  else if (ev.note) {
    const n = state.detail?.notes.find((x) => x.id === ev.note);
    if (n?.camera) viewer.setCamera(n.camera);
    if (n) highlight(n.id, { scroll: true });
  } else if (ev.position_blender && ev.target_blender) {
    // Blender (x, y, z), Z up → three.js (x, z, −y).
    const toThree = ([x, y, z]) => [x, z, -y];
    viewer.setCamera({ position: toThree(ev.position_blender), target: toThree(ev.target_blender) });
  }
  toast(esc(t('Claude turned the view')), 'ok', 2500);
}

// ── Claude in Studio: a conversation per model (worker.py runs `claude -p`) ───
// The worker answers one request at a time on the user's Claude login. The tab shows the
// model's conversation: your messages, Claude's, each tool call on one line, and the two
// things Claude waits on — a proposal (Accept / Decline) and a tool call outside the safe
// list (Allow once / Deny). What Claude writes streams in as it comes.

const claude = { status: null, thread: null, key: null, view: null, partial: null, open: new Set(), ctxNote: true, ctxView: false, menu: false };
// The conversation the tab shows: the project's or a Create request's when picked
// (claude.view), else the open model's.
const claudeKey = () => claude.view || (state.id ? `asset:${state.id}` : null);
// The key the server files it under: a model made from a request keeps the request's.
const threadKey = () => claude.thread?.key || claudeKey();
function openClaudeView(key) {
  claude.view = key && !key.startsWith('asset:') ? key : null;
  if (key?.startsWith('asset:') && key.slice(6) !== state.id) go(key.slice(6));
  claude.partial = null;
  setPanel(right, true);
  setTab('claude');
}

async function claudeStatus() {
  try { claude.status = await api('/api/claude'); } catch { claude.status = null; }
  claudeChanged();
  return claude.status;
}

// The page's live jobs, newest first: what the list, the pill and the title show.
const claudeLive = () => (claude.status?.jobs || []).filter((j) => ['queued', 'running', 'waiting'].includes(j.state)).reverse();
function claudeDot(a) {
  const j = claudeLive().find((x) => x.asset === a.id);
  return j ? { running: 'active', queued: 'queued', waiting: 'waiting' }[j.state] : null;
}
function claudeDotTitle(a) {
  const j = claudeLive().find((x) => x.asset === a.id);
  return !j ? '' : j.state === 'waiting' ? t('Claude waits for your answer') : j.state === 'running' ? t('Claude is working on it') : t('Waiting in line for Claude ({n})', { n: j.position || 1 });
}
// Something changed in Claude's runs: the rows, the counters, the pill, the page title.
function claudeChanged() {
  // The dots' column shows while a kiln command or Claude's runs have any.
  $('#list').classList.toggle('working', !!state.work || claudeLive().length > 0);
  for (const a of state.assets) if (state.rowSig.has(a.id) && state.rowSig.get(a.id) !== rowSig(a)) patchRow(a.id, false);
  renderStrip();
  renderClaudeBadge();
  renderClaudePill();
  const waiting = claudeLive().filter((j) => j.state === 'waiting').length;
  const base = state.name ? `${state.name} · Kiln Studio` : 'Kiln Studio';
  document.title = waiting ? `(${waiting}) ${base}` : base;
}

async function claudeOpen() {
  if (!claude.status) await claudeStatus();
  await claudeLoad();
}

async function claudeLoad() {
  const key = claudeKey();
  claude.key = key;
  if (!key) { claude.thread = null; renderClaude(); return; }
  try {
    const th = await api(`/api/claude/thread?key=${enc(key)}`);
    if (claude.key === key) claude.thread = th;
  } catch (e) { claude.thread = { key, messages: [], jobs: [], error: e.message }; }
  renderClaude();
}

// The job on this conversation that runs, waits in the queue or waits for you.
function claudeJob() {
  const jobs = claude.thread?.jobs || [];
  return [...jobs].reverse().find((j) => ['queued', 'running', 'waiting'].includes(j.state)) || null;
}

function renderClaudeBadge() {
  const st = claude.status;
  const mine = st?.jobs?.filter((j) => j.key === threadKey() && ['queued', 'running', 'waiting'].includes(j.state)) || [];
  const waiting = mine.some((j) => j.state === 'waiting');
  const el = $('#tc-claude');
  el.textContent = waiting ? '!' : mine.length ? '•' : '';
  el.className = `tc${waiting ? ' warn' : mine.length ? ' run' : ''}`;
  const rc = $('#rc-claude');
  rc.hidden = !mine.length;
  rc.textContent = waiting ? '!' : '•';
}

// Claude's text: escaped, then **bold**, `code` and line breaks; nothing else.
// The proposal's own line is the card below, not text to read twice.
const mdLite = (s) => esc(String(s ?? '').replace(/^\s*KILN-PROPOSAL:.*$/gm, '').trim()).replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');

function claudeEntry(e, results, job) {
  const live = job && e.job === job.id && job.state === 'waiting';
  switch (e.role) {
    case 'user':
      if (e.kind === 'setup') return `<div class="cl-msg me"><span class="dim small">${esc(t('Install'))}</span><br>${esc(partName(e.text.replace(/^\/\S+\s+setup\s+/, '')))}</div>`;
      if (e.kind === 'create') return `<div class="cl-msg me"><span class="dim small">${esc(t('New model'))}</span><br>${mdLite(createBrief(e.text))}</div>`;
      return `<div class="cl-msg me">${e.kind === 'notes' ? `<span class="dim">${esc(t('Work on the open notes'))}</span>` : mdLite(e.text)}</div>`;
    case 'assistant':
      return `<div class="cl-msg cl"><div class="who"><b>Claude</b> · <span title="${esc(stamp(e.at))}">${esc(ago(e.at))}</span></div>${mdLite(e.text)}</div>`;
    case 'tool': {
      const r = results.get(e.id);
      const name = String(e.tool || '').replace(/^mcp__(plugin_[^_]+(?:-[^_]+)*_)?/, '').replace(/__/g, ' · ');
      const open = claude.open.has(e.id);
      return `<div class="cl-tool${open ? ' open' : ''}" data-tool="${esc(e.id)}"><button class="cl-tl"><span class="car">${open ? '▾' : '▸'}</span><b>${esc(name)}</b><span class="in">${esc(e.input)}</span><span class="r ${r ? (r.error ? 'err' : 'ok') : 'run'}">${r ? (r.error ? '✕' : '✓') : '…'}</span></button>${open ? `<pre class="cl-io">${esc(e.input)}${r ? `\n— \n${esc(r.text)}` : ''}</pre>` : ''}</div>`;
    }
    case 'system':
      return `<div class="cl-sys">${esc(systemWords(e.text))}</div>`;
    case 'error':
      return `<div class="cl-card err"><div class="k">${esc(t('Claude could not go on'))}</div><p>${esc(e.text)}</p></div>`;
    case 'result': {
      if (e.text) return `<div class="cl-sys">${esc(t(e.text))}</div>`;
      // A Create request done: its model, one click away.
      const made = job == null && claude.view?.startsWith('request:') && (claude.status?.jobs || []).find((j) => j.id === e.job)?.asset;
      const open = made && state.byId.has(made) ? `<button class="btn sm accent" data-open-key="asset:${esc(made)}">${esc(t('Open {name}', { name: state.byId.get(made).name }))}</button>` : '';
      return `<div class="cl-res">${esc([e.turns != null && tp(e.turns, '{n} turn', '{n} turns'), e.duration_ms != null && fmtSecs(e.duration_ms / 1000), e.cost_usd != null && t('≈ ${c} API-equivalent, included in your subscription', { c: fmtD(e.cost_usd, 2) })].filter(Boolean).join(' · '))}</div>${open}`;
    }
    case 'proposal':
      return `<div class="cl-card prop"><div class="k">${esc(t('Claude proposes'))}</div><p>${mdLite(e.question)}</p>${live
        ? `<div class="acts"><button class="btn sm accent" data-cl="accept">${esc(t('Accept'))}</button><button class="btn sm" data-cl="decline">${esc(t('Decline'))}</button><button class="btn sm ghost" data-cl="other">${esc(t('Answer something else…'))}</button></div>`
        : ''}</div>`;
    case 'approval':
      return `<div class="cl-card appr"><div class="k">${esc(t('Approval asked'))}</div><p>${esc(t('Claude wants to use a tool outside the safe list:'))}</p><pre class="code">${esc(approvalText(e))}</pre>${live
        ? `<div class="acts"><button class="btn sm warn" data-cl="allow">${esc(t('Allow once'))}</button><button class="btn sm" data-cl="deny">${esc(t('Deny'))}</button></div>`
        : ''}</div>`;
    case 'approval-answer':
      return `<div class="cl-sys">${esc(e.decision === 'allow' ? t('You allowed {tool}', { tool: e.tool }) : t('You denied {tool}', { tool: e.tool }))}</div>`;
    default:
      return '';
  }
}
const approvalShort = (w) => { const x = approvalText(w || {}); return x.length > 60 ? `${x.slice(0, 59)}…` : x; };
// A shell command reads as one; anything else as the tool and its input.
function approvalText(e) {
  try { const i = JSON.parse(e.input); if (i && typeof i.command === 'string') return `$ ${i.command}`; if (i?.file_path) return `${e.tool} ${i.file_path}`; } catch { /* cut short: shown as is */ }
  return `${e.tool}\n${e.input}`;
}
// A Create request's prompt, as the user wrote it: the brief, without kiln's command around it.
const createBrief = (text) => String(text || '').replace(/^\/\S+\s+/, '').replace(/\s*\(Studio request q_\w+\)\s*$/, '');
// The worker's own notes, in the page's language.
function systemWords(text) {
  const m = /^Started Studio's Blender on port (\d+)/.exec(text || '');
  if (m) return t('Studio\'s Blender started, on port {p}', { p: m[1] });
  if (/^New session: the Claude account changed/.test(text || '')) return t('New session: the Claude account changed since the last message');
  return text;
}
const partName = (k) => ({ blender: 'Blender', optimizers: t('Optimisers (gltf-transform, gltfpack)'), skintokens: t('SkinTokens (learned auto-rig)'), unimate: t('UniMate (text to motion)') }[k] || k);
const fmtSecs = (s) => (s < 90 ? t('{s} s', { s: Math.round(s) }) : t('{m} min {s}', { m: Math.floor(s / 60), s: String(Math.round(s % 60)).padStart(2, '0') }));

function renderClaude() {
  const tab = $('#tab-claude');
  if (tab.hidden) { renderClaudeBadge(); return; }
  const st = claude.status, head = $('#cl-head'), thread = $('#cl-thread');
  const composer = $('#cl-composer');
  renderClaudeBadge();
  if (!st) { head.innerHTML = ''; thread.innerHTML = `<div class="empty-notes"><b>${esc(t('Claude is not reachable'))}</b>${esc(t('This Studio server has no Claude worker.'))}</div>`; composer.hidden = true; return; }
  if (!st.enabled) {
    head.innerHTML = '';
    thread.innerHTML = `<div class="empty-notes cl-off"><b>${esc(t('Claude in Studio is off'))}</b>${esc(t('Turn it on and Claude works on your models from here: one request at a time, on your Claude subscription, in a Blender of its own (port {p}) — yours is never touched.', { p: st.port }))}<div style="margin-top:12px"><button class="btn sm accent" data-cl="enable">${esc(t('Turn on'))}</button></div></div>`;
    composer.hidden = true;
    return;
  }
  if (!claudeKey()) { head.innerHTML = ''; thread.innerHTML = `<div class="empty-notes"><b>${esc(t('No model open'))}</b>${esc(t('Open a model to talk to Claude about it, or talk about the whole project.'))}<div style="margin-top:12px"><button class="btn sm" data-cl="project">${esc(t('Project conversation'))}</button></div></div>`; composer.hidden = true; return; }
  composer.hidden = false;
  const job = claudeJob();
  const msgs = claude.thread?.messages || [];
  const req = claude.view?.startsWith('request:') ? (st.jobs || []).find((j) => `request:${j.request}` === claude.view) : null;
  const name = claude.view === 'project' ? t('the project') : claude.view === 'setup' ? t('the setup') : req ? (req.brief || t('the new model')) : state.detail?.name || state.id;
  const title = claude.view === 'project' ? t('Project conversation') : claude.view === 'setup' ? t('Setup') : req ? t('Making: {brief}', { brief: req.brief || '' }) : t('Conversation on {name}', { name });
  const back = claude.view && state.id ? `<button class="btn sm ghost" data-cl="back" title="${esc(t('Back to the conversation on {name}', { name: state.detail?.name || state.id }))}">↩ ${esc(state.detail?.name || '')}</button>` : '';
  const stateLine = !job ? (msgs.length ? t('{n} messages', { n: msgs.filter((m) => m.role === 'user' || m.role === 'assistant').length }) : t('new conversation'))
    : job.state === 'running' ? t('Claude is working') : job.state === 'queued' ? t('waiting in line ({n})', { n: job.position || 1 }) : t('waiting for your answer');
  head.innerHTML = `<div class="ttl"><b>${esc(title)}</b><span>${esc(stateLine)}</span></div>${back}${job && ['running', 'queued'].includes(job.state) ? `<button class="btn sm" data-cl="stop">■ ${esc(t('Stop'))}</button>` : ''}`;
  const results = new Map(msgs.filter((m) => m.role === 'tool-result').map((m) => [m.id, m]));
  // Tool calls in a row are one block.
  let html = '', inTools = false;
  for (const e of msgs) {
    if (e.role === 'tool-result') continue;
    const tool = e.role === 'tool';
    if (tool && !inTools) { html += '<div class="cl-tools">'; inTools = true; }
    if (!tool && inTools) { html += '</div>'; inTools = false; }
    html += claudeEntry(e, results, job);
  }
  if (inTools) html += '</div>';
  if (claude.partial && job && claude.partial.job === job.id && job.state === 'running') html += `<div class="cl-msg cl"><div class="who"><b>Claude</b> · ${esc(t('now'))}</div>${mdLite(claude.partial.text)}<span class="caret"></span></div>`;
  else if (job?.state === 'running') html += `<div class="cl-sys"><span class="dot pulse"></span> ${esc(t('Claude is working…'))}</div>`;
  if (!msgs.length && !job) html = `<div class="empty-notes"><b>${esc(t('Ask Claude about {name}', { name }))}</b>${esc(t('It sees the model you have open, your notes and your view, and changes the model in its own Blender. Studio shows each new version here.'))}${!claude.view && (state.detail?.counts?.open || 0) ? `<div style="margin-top:12px"><button class="btn sm" data-cl="notes">${esc(tp(state.detail.counts.open, 'Work on the open note', 'Work on the {n} open notes'))}</button></div>` : ''}</div>`;
  const atEnd = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 40;
  thread.innerHTML = html;
  if (atEnd || claude.stick) { thread.scrollTop = thread.scrollHeight; claude.stick = false; }
  // composer
  const tool = job?.state === 'waiting' && (claude.thread?.jobs || []).some((j) => j.id === job.id && j.waiting?.type === 'tool');
  const busy = job && ['running', 'queued'].includes(job.state);
  $('#cl-text').placeholder = tool ? t('Answer the approval first') : t('Ask Claude about {name}…', { name });
  $('#cl-text').disabled = !!tool;
  $('#cl-send').disabled = !!tool || !!busy;
  const hl = !claude.view && state.hl && state.detail?.notes.find((n) => n.id === state.hl);
  $('#cl-ctx').innerHTML = [
    hl ? `<button class="chip${claude.ctxNote ? ' on' : ''}" data-cl="ctx-note" title="${esc(t('Send the highlighted note with the message'))}">● ${esc(t('note {n}', { n: noteNumber(hl) }))}</button>` : '',
    `<button class="chip${claude.ctxView ? ' on' : ''}" data-cl="ctx-view" title="${esc(t('Claude looks at your view first'))}">${esc(t('my view'))}</button>`,
  ].join('');
  const a = st.auth || {};
  $('#cl-hint').innerHTML = busy ? esc(t('Claude is working: send when it is done, or stop it.'))
    : a.ok === false ? `<span class="warn-t">${esc(accountWords(a))}</span>`
    : esc(t('On {who} · Blender of Studio, port {p}', { who: accountWords(a), p: st.port }));
}

function claudeCompose(text) {
  const parts = [];
  const hl = !claude.view && state.hl && state.detail?.notes.find((n) => n.id === state.hl);
  if (hl && claude.ctxNote) parts.push(`(About note ${noteNumber(hl)}, ${hl.id}: “${hl.text}”.)`);
  if (claude.ctxView) parts.push('(Look at my current Studio view first: kiln-studio get_view_image.)');
  return [...parts, text].join('\n');
}

async function claudeSend(kind, text = '') {
  try {
    const body = claude.view ? { kind, key: claude.view, text, lang: getLang() } : { kind, asset: state.id, text, lang: getLang() };
    await api('/api/claude/jobs', { method: 'POST', body });
    claude.stick = true;
    await claudeStatus();
    await claudeLoad();
    return true;
  } catch (e) { toast(esc(e.message), 'warn', 6000); return false; }
}

$('#cl-send').onclick = async () => {
  const ta = $('#cl-text'), text = ta.value.trim();
  if (!text) return;
  const job = claudeJob();
  const kind = job?.state === 'waiting' ? 'answer' : 'chat';
  if (await claudeSend(kind, claudeCompose(text))) ta.value = '';
};
$('#cl-text').addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); $('#cl-send').click(); } });
$('#tab-claude').addEventListener('click', async (e) => {
  const tl = e.target.closest('.cl-tl');
  if (tl) { const id = tl.parentElement.dataset.tool; claude.open.has(id) ? claude.open.delete(id) : claude.open.add(id); renderClaude(); return; }
  const act = e.target.closest('[data-cl]')?.dataset.cl;
  if (!act) return;
  const job = claudeJob();
  if (act === 'enable') {
    try { await api('/api/config', { method: 'PUT', body: { claude_worker: true } }); await claudeStatus(); renderClaude(); } catch (err) { toast(esc(err.message), 'warn'); }
  } else if (act === 'stop' && job) {
    try { await api(`/api/claude/jobs/${enc(job.id)}/stop`, { method: 'POST', body: {} }); } catch (err) { toast(esc(err.message), 'warn'); }
  } else if (act === 'notes') {
    claudeSend('notes');
  } else if (act === 'accept') {
    claudeSend('answer', 'Yes, go ahead.');
  } else if (act === 'decline') {
    claudeSend('answer', 'No, do not do that.');
  } else if (act === 'other') {
    $('#cl-text').focus();
  } else if ((act === 'allow' || act === 'deny') && job) {
    try { await api(`/api/claude/jobs/${enc(job.id)}/answer`, { method: 'POST', body: { decision: act } }); claude.stick = true; await claudeStatus(); await claudeLoad(); } catch (err) { toast(esc(err.message), 'warn'); }
  } else if (act === 'project') { openClaudeView('project'); }
  else if (act === 'back') { openClaudeView(null); }
  else if (act === 'ctx-note') { claude.ctxNote = !claude.ctxNote; renderClaude(); }
  else if (act === 'ctx-view') { claude.ctxView = !claude.ctxView; renderClaude(); }
});

// ── what Claude is doing, at a glance: the pill over the view and its menu ──
// The quota as Claude Code last said it: the 5-hour session and the week (unifiedWindows),
// each used 0–1 and when it resets; an older event has only the window it hit.
function quotaWindows(rate) {
  if (!rate) return [];
  const w = rate.unifiedWindows || {};
  const out = ['five_hour', 'seven_day'].filter((k) => w[k]?.utilization != null).map((k) => ({ key: k, used: w[k].utilization, resets: w[k].resetsAt }));
  if (!out.length && rate.utilization != null) out.push({ key: rate.rateLimitType, used: rate.utilization, resets: rate.resetsAt });
  return out;
}
const quotaName = (k) => ({ five_hour: t('Session (5 h)'), seven_day: t('Week') }[k] || t('Usage'));
const resetWords = (ts) => {
  if (!ts) return '';
  const d = new Date(ts * 1000), today = new Date().toDateString() === d.toDateString();
  return t('resets {at}', { at: today ? d.toLocaleTimeString(getLang(), { hour: '2-digit', minute: '2-digit' }) : d.toLocaleDateString(getLang(), { weekday: 'short', hour: '2-digit', minute: '2-digit' }) });
};
const jobLabel = (j) => j.key === 'project' ? t('Project conversation') : j.key === 'setup' ? t('Setup')
  : j.asset ? (state.byId.get(j.asset)?.name || j.asset.split('/').pop())
  : j.request ? t('New: {brief}', { brief: j.brief || '' }) : '?';
// Where a job's conversation is shown: on its model when there is one.
const jobKey = (j) => (j.asset ? `asset:${j.asset}` : j.key);

function renderClaudePill() {
  const st = claude.status, pill = $('#cl-pill');
  pill.hidden = !st?.enabled;
  if (pill.hidden) return;
  const live = claudeLive();
  const run = live.find((j) => j.state === 'running'), wait = live.filter((j) => j.state === 'waiting'), queue = live.filter((j) => j.state === 'queued');
  // The pill shows the fuller window: a week at 91 % matters more than a session at 42 %.
  const wins = quotaWindows(st.rate), session = wins.reduce((a, x) => (!a || x.used > a.used ? x : a), null);
  const util = st.account === 'api_key' ? null : session?.used;
  const btn = $('#cl-pill-btn');
  btn.className = `cl-pill-btn${wait.length ? ' wait' : run ? ' run' : ''}`;
  btn.innerHTML = `<span class="dot${run && !wait.length ? ' pulse' : ''}"></span><b>Claude</b><span>${esc(
    wait.length ? tp(wait.length, 'waits for you', '{n} wait for you') : run ? t('on {name}', { name: jobLabel(run) }) : t('ready'))}</span>${queue.length ? `<span class="sep"></span><span>${esc(t('{n} in line', { n: queue.length }))}</span>` : ''}${util != null ? `<span class="sep"></span><span class="qbar" title="${esc(quotaName(session.key))}"><i class="${util >= 0.9 ? 'hot' : ''}" style="width:${Math.round(util * 100)}%"></i></span><span>${Math.round(util * 100)} %</span>` : ''}`;
  btn.setAttribute('aria-expanded', String(claude.menu));
  $('#cl-act').hidden = !claude.menu;
  if (!claude.menu) return;
  const row = (j) => `<button class="it" data-key="${esc(jobKey(j))}"><span class="t"><b>${esc(jobLabel(j))}</b><span>${esc(j.state === 'waiting' ? (j.waiting?.type === 'tool' ? t('approval: {tool}', { tool: approvalShort(j.waiting) }) : t('a proposal to answer')) : j.state === 'running' ? t('working · since {ago}', { ago: ago(j.started) }) : t('in line · {n}', { n: j.position || 1 }))}</span></span><span class="state ${j.state}">${esc({ running: t('running'), waiting: t('waits for you'), queued: t('in line') }[j.state])}</span></button>`;
  const group = (title, js) => js.length ? `<div class="g">${esc(title)}</div>${js.map(row).join('')}` : '';
  const quota = st.account === 'api_key' ? '' : wins.length
    ? `<div class="g">${esc(t('Quota'))} <span class="when">${esc(t('updated {ago}', { ago: ago(st.rate.at) }))}</span></div>${wins.map((x) => `<div class="qrow"><span class="qn">${esc(quotaName(x.key))}</span><span class="qbar"><i class="${x.used >= 0.9 ? 'hot' : ''}" style="width:${Math.max(2, Math.round(x.used * 100))}%"></i></span><span class="qv">${Math.round(x.used * 100)} %</span><span class="qr">${esc(resetWords(x.resets))}</span></div>`).join('')}`
    : `<div class="g">${esc(t('Quota'))}</div><div class="none">${esc(t('Known after Claude\'s first request: Claude Code tells it during each run.'))}</div>`;
  const u = (st.usage?.by_account || {})[st.account] || { runs: 0, cost_usd: 0 };
  $('#cl-act').innerHTML = `<div class="h"><b>${esc(t("Claude's activity"))}</b><span>${esc(st.auth ? accountWords(st.auth) : '')}</span></div>
    ${group(t('Waits for your answer'), wait)}${group(t('Running'), run ? [run] : [])}${group(t('In line'), queue)}
    ${live.length ? '' : `<div class="none">${esc(t('Nothing running. Ask from a model\'s ✦ tab, the project conversation, or New model.'))}</div>`}
    <button class="it proj" data-key="project"><span class="t"><b>${esc(t('Project conversation'))}</b><span>${esc(t('What concerns several models at once'))}</span></span></button>
    ${quota}<div class="foot">${esc(tp(u.runs || 0, '{n} request', '{n} requests'))}${u.cost_usd ? ` · ${esc(st.account === 'api_key' ? t('≈ ${c} on your API key', { c: fmtD(u.cost_usd, 2) }) : t('≈ ${c} API-equivalent, included in your subscription', { c: fmtD(u.cost_usd, 2) }))}` : ''}${'Notification' in window && Notification.permission === 'default' ? ` · <button class="linkish" data-notify>${esc(t('Notify me when Claude waits'))}</button>` : ''}</div>`;
}
$('#cl-pill-btn').onclick = (e) => { e.stopPropagation(); claude.menu = !claude.menu; renderClaudePill(); };
$('#cl-act').addEventListener('click', (e) => {
  e.stopPropagation();
  if (e.target.closest('[data-notify]')) { Notification.requestPermission().then(renderClaudePill); return; }
  const it = e.target.closest('[data-key]');
  if (!it) return;
  claude.menu = false; renderClaudePill();
  openClaudeView(it.dataset.key);
});
document.addEventListener('click', (e) => { if (claude.menu && !e.target.closest('#cl-pill')) { claude.menu = false; renderClaudePill(); } });

// Claude waits on a conversation you are not looking at: a toast you can follow, and a
// system notification when the page is in the background (if allowed).
function claudeWaits(job) {
  const name = jobLabel(job);
  const what = job.waiting?.type === 'tool' ? t('Claude asks to run {tool} on {name}', { tool: approvalShort(job.waiting), name }) : t('Claude waits for your answer on {name}', { name });
  toast(`${esc(what)} · <button class="linkish" data-open-key="${esc(jobKey(job))}">${esc(t('Answer'))}</button>`, 'warn', 9000);
  if ('Notification' in window && Notification.permission === 'granted' && document.hidden) {
    const n = new Notification('Kiln Studio', { body: what, tag: `claude-${job.id}` });
    n.onclick = () => { window.focus(); openClaudeView(jobKey(job)); n.close(); };
  }
}
document.addEventListener('click', (e) => { const b = e.target.closest('[data-open-key]'); if (b) openClaudeView(b.dataset.openKey); });

let claudeTimer = 0;
async function onClaude(ev) {
  if (ev.type === 'claude-text') {
    if (ev.key !== threadKey()) return;
    claude.partial = { job: ev.job, text: ev.text };
    cancelAnimationFrame(claudeTimer);
    claudeTimer = requestAnimationFrame(renderClaude);
    return;
  }
  // A job changed, or a message was added: the status always, the thread if it is this one.
  if (ev.entry?.role === 'assistant' && claude.partial?.job === ev.job?.id) claude.partial = null;
  if (claude.status) {
    const jobs = claude.status.jobs || [];
    const i = jobs.findIndex((j) => j.id === ev.job.id);
    if (i >= 0) jobs[i] = { ...jobs[i], ...ev.job }; else jobs.push(ev.job);
  }
  if (ev.job?.key === threadKey() && claude.thread) {
    if (ev.entry) claude.thread.messages.push(ev.entry);
    const jobs = claude.thread.jobs;
    const i = jobs.findIndex((j) => j.id === ev.job.id);
    if (i >= 0) jobs[i] = { ...jobs[i], ...ev.job }; else jobs.push(ev.job);
  }
  if (ev.job && !['queued', 'running'].includes(ev.job.state)) claudeStatus().then(renderClaude);
  if (ev.job?.kind === 'create' && ev.job.state === 'done' && ev.job.asset && ev.entry?.role === 'result')
    setTimeout(() => toast(`${esc(t('Claude made {name}', { name: ev.job.asset.split('/').pop() }))} · <button class="linkish" data-open-key="asset:${esc(ev.job.asset)}">${esc(t('Open'))}</button>`, 'ok', 9000), 600);
  claudeChanged();
  renderClaude();
  if (ev.job?.state === 'waiting' && ev.entry && ['proposal', 'approval'].includes(ev.entry.role) && (ev.job.key !== threadKey() || $('#tab-claude').hidden || !isOpen(right) || document.hidden))
    claudeWaits(ev.job);
}

// ── keys ─────────────────────────────────────────────────────────────────────

const KEYS = [
  ['/', N_('Find a model')],
  ['↑ ↓', N_('Previous, next model')],
  ['[  ]  \\', N_('Collapse or expand the left panel, the right panel, both')],
  ['1 – 6', N_('Front, back, left, right, top, three-quarter')],
  ['F', N_('Frame the model')],
  ['S · ⇧S', N_('Next, previous shading')],
  ['W G B K', N_('Wire, grid, size, bones')],
  ['P', N_('Show or hide the pins')],
  ['C · ⇧C', N_('Compare with the previous version · switch split / side by side')],
  ['N', N_('Pin a note, then click the model')],
  ['M', N_('Note on the whole model')],
  ['⌘↵ · Esc', N_('Save the note · cancel')],
  ['Space', N_('Play, pause the animation')],
  ['⌘K', N_('Every command, by name')],
  ['?', N_('This list')],
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
    if (document.body.classList.contains('present')) { setPresent(false); return; }
    if (state.hl) highlight(state.hl);
    return;
  }
  if (typing || e.metaKey || e.ctrlKey || e.altKey || document.querySelector('dialog[open]')) return;
  const k = e.key;
  // Shift picks the other way where it means something (⇧S, ⇧C); otherwise the same key.
  const fn = keyActions[k] || (state.detail ? (modelKeys[k] ?? (k.length === 1 ? modelKeys[k.toLowerCase()] : null)) : null);
  if (fn) { e.preventDefault(); fn(); }
});

// ── create: ask Claude for a model that does not exist yet ───────────────────
// The form writes a request into .kiln-studio/requests.json (open, like a note) and
// gives the command to paste in Claude Code; the skill closes it once the model is built.

let crPhoto = null;
async function openCreate() {
  document.querySelector('dialog[open]')?.close();
  $('#cr-form').hidden = false;
  $('#cr-done').hidden = true;
  $('#cr-status').textContent = '';
  try { const pt = (await api('/api/config')).settings.target; if ($(`#cr-target option[value="${pt}"]`)) $('#cr-target').value = pt; } catch { /* web */ }
  await claudeStatus();
  renderCreateMode();
  renderRequests();
  $('#create').showModal();
  $('#cr-brief').focus();
}
// With Claude in Studio on, the request goes straight to Claude; the dialog says first
// whether it waits behind another run. Off, it is saved for a terminal, as before.
function renderCreateMode() {
  const on = !!claude.status?.enabled;
  $('#cr-launch').hidden = !on;
  $('#cr-save').classList.toggle('accent', !on);
  $('#cr-save').textContent = on ? t('Save without making it') : t('Save the request');
  const live = claudeLive(), run = live.find((j) => j.state === 'running');
  const q = $('#cr-queue');
  q.hidden = !on || !live.length;
  if (!q.hidden) q.textContent = run
    ? tp(live.filter((j) => j.state === 'queued').length + 1, 'Claude is working on {name}: this model comes next.', 'Claude is working on {name}: this model comes after {n} others.', { name: jobLabel(run) })
    : t('Claude waits for your answer elsewhere: this model starts once you have answered.');
}
async function renderRequests() {
  let items = [];
  try { items = (await api('/api/requests')).requests.filter((r) => r.status === 'open').reverse(); } catch { /* none to show */ }
  $('#cr-list').innerHTML = items.length ? `<h4>${esc(tp(items.length, '{n} request waiting for Claude', '{n} requests waiting for Claude'))}</h4>${items.slice(0, 5).map((r) => `<div class="rq"><span>${esc(r.brief)} <span class="dim small">· ${esc(ago(r.created))}</span></span><div class="cmd"><code>${esc(r.command)}</code><button class="btn sm" data-copy="${esc(r.command)}">${esc(t('Copy'))}</button></div></div>`).join('')}` : '';
  $$('#cr-list [data-copy]').forEach((b) => (b.onclick = () => copy(b.dataset.copy)));
}
// A photo larger than 2048 px is brought down to it: enough for Claude to read, lighter to keep.
function readPhoto(file) {
  return new Promise((res, rej) => {
    const img = new Image();
    img.onload = () => {
      const k = Math.min(1, 2048 / Math.max(img.width, img.height));
      const c = document.createElement('canvas');
      c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(img.src);
      res(c.toDataURL('image/jpeg', 0.9));
    };
    img.onerror = () => rej(new Error(t('not an image this browser can read')));
    img.src = URL.createObjectURL(file);
  });
}
$('#cr-file').onchange = async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  try {
    crPhoto = await readPhoto(f);
    $('#cr-thumb').src = crPhoto; $('#cr-thumb').hidden = $('#cr-nophoto').hidden = false;
  } catch (err) { $('#cr-status').textContent = err.message; }
};
$('#cr-nophoto').onclick = () => { crPhoto = null; $('#cr-file').value = ''; $('#cr-thumb').hidden = $('#cr-nophoto').hidden = true; };
$('#cr-form').onsubmit = async (e) => {
  e.preventDefault();
  const brief = $('#cr-brief').value.trim();
  if (!brief) { $('#cr-brief').focus(); return; }
  const launch = e.submitter?.id === 'cr-launch' || (!e.submitter && !$('#cr-launch').hidden);
  $('#cr-save').disabled = $('#cr-launch').disabled = true;
  $('#cr-status').textContent = t('Saving…');
  try {
    const r = await api('/api/requests', { method: 'POST', body: { brief, target: $('#cr-target').value, photo: crPhoto } });
    if (launch) {
      await api('/api/claude/jobs', { method: 'POST', body: { kind: 'create', request: r.id, lang: getLang() } });
      $('#cr-brief').value = ''; $('#cr-nophoto').click();
      $('#create').close();
      await claudeStatus();
      openClaudeView(`request:${r.id}`);
      toast(esc(t('Claude makes it: follow it in the ✦ tab and the pill above the view')), 'ok', 5000);
      return;
    }
    $('#cr-cmd').textContent = r.command;
    $('#cr-copy').onclick = () => copy(r.command);
    $('#cr-form').hidden = true;
    $('#cr-done').hidden = false;
    $('#cr-brief').value = ''; $('#cr-nophoto').click();
    renderRequests();
  } catch (err) { $('#cr-status').textContent = t('Not saved: {e}', { e: err.message }); }
  finally { $('#cr-save').disabled = $('#cr-launch').disabled = false; }
};
$('#cr-another').onclick = () => { $('#cr-form').hidden = false; $('#cr-done').hidden = true; $('#cr-status').textContent = ''; $('#cr-brief').focus(); };
$('#t-create').onclick = openCreate;

// ── import: drop model files on the page, or pick them ───────────────────────
// Saved into imports/ (a glTF or OBJ with the files it needs: imports/<its name>/),
// never over a file already there; the first one opens.

const MODEL_EXT = ['.glb', '.gltf', '.fbx', '.obj'];
const extOf = (n) => n.slice(n.lastIndexOf('.')).toLowerCase();
async function importFiles(files) {
  files = [...files];
  const models = files.filter((f) => MODEL_EXT.includes(extOf(f.name)));
  if (!models.length) { toast(t('Nothing to import: drop a .glb, .gltf, .fbx or .obj file'), 'warn'); return; }
  const lead = models.find((f) => ['.gltf', '.obj'].includes(extOf(f.name)));
  const others = files.filter((f) => !models.includes(f));
  // A glTF or OBJ with its .bin, .mtl or textures: one folder for all of them.
  const folder = lead && others.length ? lead.name.slice(0, lead.name.lastIndexOf('.')).replace(/[^\w.-]+/g, '-').slice(0, 60) || 'import' : null;
  const send = folder ? files : models;
  const saved = [];
  toast(tp(send.length, 'Importing {n} file…', 'Importing {n} files…'));
  for (const f of send) {
    try {
      const q = new URLSearchParams({ name: f.name, ...(folder ? { folder } : {}) });
      const res = await fetch(`/api/import?${q}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: f });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || res.statusText);
      saved.push(data.path);
    } catch (e) { toast(t('Could not import {f}: {e}', { f: esc(f.name), e: esc(e.message) }), 'warn', 8000); return; }
  }
  await fetchAssets();
  const first = saved.find((x) => MODEL_EXT.includes(extOf(x)));
  const a = state.assets.find((x) => x.variants.some((v) => v.file === first));
  toast(tp(saved.length, '{n} file imported into {f}', '{n} files imported into {f}', { f: `<span class="mono">${esc(first.slice(0, first.lastIndexOf('/') + 1))}</span>` }), 'ok', 5000);
  if (a) go(a.id);
  if (others.length && !folder) toast(t('Left out: {f} (only beside a .gltf or .obj)', { f: esc(others.map((f) => f.name).join(', ')) }), 'warn', 6000);
}
$('#t-import').onclick = () => $('#import-input').click();
$('#import-input').onchange = (e) => { if (e.target.files.length) importFiles(e.target.files); e.target.value = ''; };
{
  let depth = 0;
  const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes('Files');
  addEventListener('dragenter', (e) => { if (!hasFiles(e)) return; depth++; $('#drop').hidden = false; e.preventDefault(); });
  addEventListener('dragover', (e) => { if (hasFiles(e)) e.preventDefault(); });
  addEventListener('dragleave', () => { depth = Math.max(0, depth - 1); if (!depth) $('#drop').hidden = true; });
  addEventListener('drop', (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault(); depth = 0; $('#drop').hidden = true;
    importFiles(e.dataTransfer.files);
  });
}
welcomeCards.unshift(
  { key: 'create', title: N_('Create'), text: N_('Describe the model, add a photo if you have one: Studio gives you the command for Claude.'),
    icon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>', run: () => openCreate() },
  { key: 'import', title: N_('Import'), text: N_('A GLB, glTF, FBX or OBJ you already have: drop it anywhere on this page, or pick it.'),
    icon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg>', run: () => $('#import-input').click() },
);
paletteExtras.push((add) => {
  add('Help', 'Ask Claude for a new model', [], openCreate);
  add('Help', 'Import a model file', [], () => $('#import-input').click());
});

// ── settings: personal (this browser) and the project's (shared with Claude) ──

const settingsRows = []; // further personal rows (theme, language) register here
let project = null;
async function openSettings(pane) {
  document.querySelector('dialog[open]')?.close();
  syncPersonal();
  $('#set-status').textContent = '';
  setPane(pane || prefs.setPane || 'display');
  syncClaudeSettings();
  $('#settings').showModal();
  try {
    projectInfo = await api('/api/config');
    project = projectInfo.settings;
    syncProject();
  } catch (e) { $('#set-status').textContent = t('Could not read the project settings: {e}', { e: e.message }); }
}
// Display (this browser), Project, Claude, Account (this computer): one pane at a time.
async function syncSetup(fresh = false) {
  const ul = $('#set-setup');
  if (!ul.children.length) ul.innerHTML = `<li class="dim">${esc(t('Looking…'))}</li>`;
  try { setup = await api(`/api/status${fresh ? '?fresh=1' : ''}`); ul.innerHTML = setup.rows.map(setupRow).join(''); }
  catch (e) { ul.innerHTML = `<li class="dim">${esc(e.message)}</li>`; }
}
$('#set-setup-again').onclick = () => syncSetup(true);
function setPane(name) {
  if (name === 'setup') syncSetup();
  $$('#settings .set-nav [data-pane]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.pane === name)));
  $$('#settings .set-pane').forEach((x) => (x.hidden = x.dataset.pane !== name));
  prefs.setPane = name; savePrefs();
}
$$('#settings .set-nav [data-pane]').forEach((b) => (b.onclick = () => { $('#set-status').textContent = ''; setPane(b.dataset.pane); }));
let projectInfo = null;
const targetName = (v) => ({ web: t('Web'), desktop: t('Unity / Unreal'), print: t('3D print') }[v] || v);
function segSet(id, value) { $$(`${id} button`).forEach((b) => b.classList.toggle('on', b.dataset.v === value)); }
function switchSet(id, on) { $(id).setAttribute('aria-checked', String(!!on)); }
// Language: English or French, switched in place — every word drawn again.
function syncLang() {
  $('#set-lang').innerHTML = Object.entries(LANGS).map(([k, name]) => `<button data-v="${k}" lang="${k}">${esc(name)}</button>`).join('');
  segSet('#set-lang', getLang());
  $$('#set-lang button').forEach((b) => (b.onclick = () => switchLang(b.dataset.v)));
}
async function switchLang(v) {
  if (v === getLang()) return;
  try { await loadLanguage(v); } catch (e) { $('#set-status').textContent = t('Not saved: {e}', { e: e.message }); return; }
  setLang(v);
  prefs.lang = v; savePrefs();
  document.documentElement.lang = v;
  refreshWords();
  syncPersonal(); syncProject();
  claudeChanged(); renderClaude(); syncClaudeSettings(false);
  if (!$('#settings .set-pane[data-pane="setup"]').hidden && setup) $('#set-setup').innerHTML = setup.rows.map(setupRow).join('');
  if (!state.assets.length && !state.id) renderWelcome();
}
function syncPersonal() {
  syncLang();
  segSet('#set-density', state.density);
  $('#set-shade').value = prefs.defaultShade || '';
  $('#set-view').value = prefs.view || 'iso';
  segSet('#set-units', getUnits());
  switchSet('#set-hidefixed', state.hideFixed);
  for (const r of settingsRows) r.sync?.();
}
function syncProject() {
  if (!project) return;
  switchSet('#set-live', project.live_view);
  switchSet('#set-autoopen', project.auto_open);
  // "Default (Web)": the project follows the computer's default until it chooses.
  const def = projectInfo?.user_defaults?.target || 'web';
  $('#set-target-inherit').textContent = t('Default ({t})', { t: targetName(def) });
  $('#set-target').value = projectInfo?.target_source === 'project' ? project.target : '';
  segSet('#set-target-default', def);
  if (document.activeElement !== $('#set-exclude')) $('#set-exclude').value = project.exclude.join('\n');
}
async function saveProject(updates, what) {
  $('#set-status').textContent = t('Saving…');
  try {
    projectInfo = { ...projectInfo, ...(await api('/api/config', { method: 'PUT', body: updates })) };
    project = projectInfo.settings;
    syncProject();
    $('#set-status').textContent = t('Saved in .kiln-studio/config.json: {what}', { what });
    if ('target' in updates && state.id) await fetchDetail();
    if ('exclude' in updates) await fetchAssets();
  } catch (e) { $('#set-status').textContent = t('Not saved: {e}', { e: e.message }); syncProject(); }
}
$$('#set-density button').forEach((b) => (b.onclick = () => { state.density = prefs.density = b.dataset.v; savePrefs(); syncDensity(); syncPersonal(); renderList(); }));
$('#set-shade').onchange = (e) => { prefs.defaultShade = e.target.value; savePrefs(); };
$('#set-view').onchange = (e) => { prefs.view = e.target.value; savePrefs(); };
$$('#set-units button').forEach((b) => (b.onclick = () => { prefs.units = b.dataset.v; savePrefs(); setUnits(b.dataset.v); syncPersonal(); refreshWords(); }));
$('#set-hidefixed').onclick = () => { setPinFilter('hideFixed', !state.hideFixed); syncPersonal(); };
$('#set-live').onclick = () => project && saveProject({ live_view: !project.live_view }, t('Live view'));
$('#set-autoopen').onclick = () => project && saveProject({ auto_open: !project.auto_open }, t('Opening Studio'));
$('#set-target').onchange = (e) => project && saveProject({ target: e.target.value }, t('Made for'));
$$('#set-target-default button').forEach((b) => (b.onclick = async () => {
  try {
    projectInfo = { ...projectInfo, ...(await api('/api/defaults', { method: 'PUT', body: { target: b.dataset.v } })) };
    project = projectInfo.settings;
    syncProject();
    $('#set-status').textContent = t('Saved for every project on this computer: {what}', { what: t('Made for, by default') });
    if (state.id) await fetchDetail();
  } catch (e) { $('#set-status').textContent = t('Not saved: {e}', { e: e.message }); }
}));
$('#set-exclude').onchange = (e) => saveProject({ exclude: e.target.value.split('\n').map((x) => x.trim()).filter(Boolean) }, t('Left out of the list'));
$('#t-settings').onclick = () => openSettings();

// ── Settings → Claude in Studio ──────────────────────────────────────────────
// The account is this computer's (worker.py: ~/.kiln-studio/claude.json, the key in the
// keychain); the rest is the project's, beside the other project settings.

async function syncClaudeSettings(fresh = true) {
  const st = fresh ? await claudeStatus() : claude.status;
  $('#settings .set-nav [data-pane="claude"]').hidden = $('#settings .set-nav [data-pane="account"]').hidden = !st;
  if (!st) return;
  switchSet('#set-claude', st.enabled);
  switchSet('#set-behind', st.blender_behind);
  segSet('#set-paid', st.paid);
  $('#set-paid-help').textContent = st.paid === 'auto'
    ? t('⚠ Started without asking: Hyper3D Rodin, Hunyuan3D… spend your credits with those services.')
    : t('Hyper3D Rodin, Hunyuan3D… wait for your OK each time: they spend credits.');
  const b = st.blender || {};
  $('#set-blender-state').textContent = b.state === 'running' ? t('Running on port {p}', { p: b.port }) : t('Starts with Claude\'s first request, closes with Studio.');
  $('#set-stop-blender').disabled = b.state !== 'running';
  segSet('#set-account', st.account);
  segSet('#set-approvals', st.approvals);
  segSet('#set-mcp', st.mcp);
  if (document.activeElement !== $('#set-port')) $('#set-port').value = st.port;
  $('#set-model').value = ['', 'opus', 'sonnet', 'haiku'].includes(st.model) ? st.model : '';
  const a = st.auth || {};
  $('#set-acc-help').textContent = { subscription: t('Claude Code as it is logged in on this computer.'),
    account: t('A second Claude login of Studio\'s own: your terminal keeps its account.'),
    api_key: t('Billed per token, in real dollars, to your Anthropic account.') }[st.account];
  // The account's state, once, and what that kind of account needs.
  $('#set-acc-state').className = `sstate ${a.ok ? 'ok' : 'bad'}`;
  $('#set-acc-state').innerHTML = `<i>${a.ok ? '✓' : '!'}</i>${esc(accountWords(a))}`;
  let more = '';
  if (st.account === 'account') more = `<div class="srow in"><div class="st"><b>${esc(a.ok ? t('Log in again') : t('Log in'))}</b><span>${esc(t('Opens claude.ai in your browser.'))}</span></div><div class="sc"><button class="btn sm" id="set-login">${esc(t('Log in…'))}</button></div></div>`;
  else if (st.account === 'api_key') more = `<div class="srow in"><div class="st"><b>${esc(t('API key'))}</b><span>${esc(t('Kept in the macOS keychain; never shown again.'))}</span></div><div class="sc set-key"><input id="set-key" type="password" autocomplete="off" spellcheck="false" placeholder="sk-ant-…" aria-label="${esc(t('API key'))}"><button class="btn sm" id="set-key-save">${esc(a.ok ? t('Replace') : t('Save'))}</button>${a.ok ? `<button class="btn sm ghost" id="set-key-forget">${esc(t('Forget it'))}</button>` : ''}</div></div>
      <div class="srow in"><div class="st"><label for="set-budget"><b>${esc(t('Cap per request'))}</b></label><span>${esc(t('A request stops when it has spent this much.'))}</span></div><div class="sc"><input id="set-budget" type="number" min="0.1" max="100" step="0.5" class="num" value="${esc(st.budget_usd)}"> <span class="dim small">$</span></div></div>`;
  $('#set-acc').innerHTML = more;
  $('#set-acc').hidden = !more;
  $('#set-approvals-help').textContent = st.approvals === 'auto'
    ? t('Claude Code decides alone; what it judges risky is refused, without asking you.')
    : t('Reading, the project\'s files and kiln\'s scripts go through; anything else waits for your OK.');
  const m = st.machine || {}, max = Math.max(1, m.max_parallel || 1);
  $('#set-parallel').innerHTML = [1, 2, 3, 4].map((n) => `<button data-v="${n}"${n > max ? ` title="${esc(t('More than this computer takes comfortably'))}" class="over"` : ''}>${n}</button>`).join('');
  segSet('#set-parallel', String(st.parallel));
  $$('#set-parallel button').forEach((b) => (b.onclick = () => saveClaude({ claude_parallel: +b.dataset.v }, t('At once'))));
  $('#set-parallel-help').textContent = t('Each its own Blender, never two on one model; the quota goes faster. This computer ({ram} GB, {cores} cores): up to {max}.', { ram: m.ram_gb ?? '?', cores: m.cores ?? '?', max });
  // This account's runs: an API key's are billed, a subscription's are API-equivalent.
  const u = (st.usage?.by_account || {})[st.account] || { runs: 0, cost_usd: 0 };
  $('#set-usage').textContent = [tp(u.runs || 0, '{n} request', '{n} requests'), u.cost_usd ? (st.account === 'api_key' ? t('≈ ${c} billed', { c: fmtD(u.cost_usd, 2) }) : t('≈ ${c} API-equivalent', { c: fmtD(u.cost_usd, 2) })) : ''].filter(Boolean).join(' · ');
  // the per-mode controls
  $('#set-login')?.addEventListener('click', async () => {
    try { await api('/api/claude/login', { method: 'POST', body: {} }); claudeNote(t('Finish logging in in the browser, then come back: Studio checks again in a few seconds.')); setTimeout(() => syncClaudeSettings(), 8000); } catch (e) { claudeNote(t('Not started: {e}', { e: e.message })); }
  });
  $('#set-key-save')?.addEventListener('click', async () => {
    const key = $('#set-key').value.trim();
    if (!key) { $('#set-key').focus(); return; }
    try { claude.status = await api('/api/claude/key', { method: 'POST', body: { key } }); claudeNote(t('API key saved in the keychain')); syncClaudeSettings(false); claudeChanged(); } catch (e) { claudeNote(t('Not saved: {e}', { e: e.message })); }
  });
  $('#set-key-forget')?.addEventListener('click', async () => {
    try { claude.status = await api('/api/claude/key', { method: 'POST', body: { key: null } }); claudeNote(t('API key forgotten')); syncClaudeSettings(false); claudeChanged(); } catch (e) { claudeNote(t('Not saved: {e}', { e: e.message })); }
  });
  $('#set-key')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') $('#set-key-save').click(); });
  $('#set-budget')?.addEventListener('change', (e) => saveClaude({ claude_budget_usd: +e.target.value }, t('Cap per request')));
}
const claudeNote = (msg) => { $('#set-status').textContent = msg; };
// The account as the page words it; the server's English stands for the rarer failures.
function accountWords(a) {
  const plan = a.subscription ? a.subscription[0].toUpperCase() + a.subscription.slice(1) : '';
  if (a.ok && a.account === 'api_key') return t('your Anthropic API key (…{end})', { end: (a.message.match(/…(\S{4})/) || [])[1] || '' });
  if (a.ok && a.account === 'account') return t('another Claude account ({who})', { who: a.email || plan });
  if (a.ok) return plan ? t('your Claude {plan} subscription', { plan }) : t('your Claude subscription');
  if (a.account === 'api_key') return t('No API key yet: paste one below.');
  if (a.account === 'account' && /not logged in/.test(a.message)) return t('This account is not logged in yet: Log in…');
  return a.message || t('Claude Code is not ready');
}
async function saveClaude(updates, what) {
  claudeNote(t('Saving…'));
  try {
    await api('/api/config', { method: 'PUT', body: updates });
    claudeNote(t('Saved in .kiln-studio/config.json: {what}', { what }));
    await syncClaudeSettings();
    renderClaude();
  } catch (e) { claudeNote(t('Not saved: {e}', { e: e.message })); syncClaudeSettings(false); }
}
$('#set-claude').onclick = () => claude.status && saveClaude({ claude_worker: !claude.status.enabled }, t('Ask Claude from Studio'));
$$('#set-account button').forEach((b) => (b.onclick = async () => {
  if (claude.status?.account === b.dataset.v) return;
  claudeNote(t('Checking the account…'));
  try { claude.status = await api('/api/claude/account', { method: 'PUT', body: { account: b.dataset.v } }); claudeNote(t('Account: {a}', { a: b.textContent })); syncClaudeSettings(false); claudeChanged(); renderClaude(); }
  catch (e) { claudeNote(t('Not saved: {e}', { e: e.message })); }
}));
$$('#set-approvals button').forEach((b) => (b.onclick = () => claude.status?.approvals !== b.dataset.v && saveClaude({ claude_approvals: b.dataset.v }, t('Approvals'))));
$('#set-behind').onclick = () => claude.status && saveClaude({ blender_behind: !claude.status.blender_behind }, t('Open Blender behind'));
$$('#set-paid button').forEach((b) => (b.onclick = () => claude.status?.paid !== b.dataset.v && saveClaude({ claude_paid: b.dataset.v }, t('Paid generation'))));
$$('#set-mcp button').forEach((b) => (b.onclick = () => claude.status?.mcp !== b.dataset.v && saveClaude({ blender_mcp: b.dataset.v }, t('Blender MCP server'))));
$('#set-port').onchange = (e) => saveClaude({ blender_port: +e.target.value }, t('Port'));
$('#set-model').onchange = (e) => saveClaude({ claude_model: e.target.value }, t('Model'));
$('#set-stop-blender').onclick = async () => { try { await api('/api/claude/blender/stop', { method: 'POST', body: {} }); claudeNote(t('Studio\'s Blender stopped')); syncClaudeSettings(); } catch (e) { claudeNote(e.message); } };

// ── themes: Dark (the approved design), Light, High contrast; an accent colour ──

// Each accent in each theme: a tone that reads on that theme's background, and the
// ink that reads on the accent.
const ACCENTS = {
  cyan: { name: N_('Cyan'), dark: ['#5CE1E6', '#062A2C'], light: ['#08737A', '#FFFFFF'], contrast: ['#3DF2FF', '#000000'] },
  blue: { name: N_('Blue'), dark: ['#6CB6FF', '#06182C'], light: ['#1A5FB4', '#FFFFFF'], contrast: ['#8CCBFF', '#000000'] },
  pink: { name: N_('Pink'), dark: ['#FF7AB6', '#2C0618'], light: ['#C2185B', '#FFFFFF'], contrast: ['#FF9ECF', '#000000'] },
  lime: { name: N_('Lime'), dark: ['#C3E85A', '#1A2406'], light: ['#40690C', '#FFFFFF'], contrast: ['#D8FF6B', '#000000'] },
};
// The themes: the three of the approved design, and four from the design boards
// (CockpitForge, CockpitNeon, CockpitClair, CockpitMinimal). Forge, Neon and Studio have
// their own accent; the others take the one picked in Settings.
const THEMES = [
  { key: 'dark', name: N_('Dark'), swatch: ['#0B0D11', '#5CE1E6', '#FFB547'] },
  { key: 'light', name: N_('Light'), swatch: ['#F4F6F9', '#08737A', '#994F00'] },
  { key: 'contrast', name: N_('High contrast'), swatch: ['#000000', '#3DF2FF', '#FFD23D'] },
  { key: 'forge', name: N_('Forge'), swatch: ['#0E0907', '#FF8A3D', '#7FC8FF'], own: true },
  { key: 'neon', name: N_('Neon'), swatch: ['#0B0618', '#3EF2FF', '#FF4FD8'], own: true },
  { key: 'studio', name: N_('Studio'), swatch: ['#F6F7F9', '#C2401A', '#1F4FB8'], own: true },
  { key: 'minimal', name: N_('Minimal'), swatch: ['#0A0A0A', '#EDEDED', '#8F8F8F'] },
];
const themeOf = () => THEMES.find((x) => x.key === prefs.theme) || THEMES[0];
// The accent tones per theme family: Minimal and Forge read like Dark, Studio like Light.
const ACCENT_TONE = { dark: 'dark', light: 'light', contrast: 'contrast', minimal: 'dark' };
function applyTheme() {
  const th = themeOf(), root = document.documentElement;
  if (th.key === 'dark') delete root.dataset.theme; else root.dataset.theme = th.key;
  if (th.own) {
    root.style.removeProperty('--accent'); root.style.removeProperty('--accent-ink');
  } else {
    const [accent, ink] = (ACCENTS[prefs.accent] || ACCENTS.cyan)[ACCENT_TONE[th.key]];
    root.style.setProperty('--accent', accent);
    root.style.setProperty('--accent-ink', ink);
  }
  if (th.key === 'forge') lightEmbers();
  // A light theme on the dark stage reads badly: until the user picks a background
  // (Bg), the stage follows the theme.
  if (prefs.bg === undefined) {
    const bg = ['light', 'studio'].includes(th.key) ? 'light' : 'dark';
    if (viewer.opts.bg !== bg) { viewer.set('bg', bg); stage.dataset.bg = bg; syncToolbar(); }
  }
}
// Forge's embers: made once, then pure CSS animation.
let embersLit = false;
function lightEmbers() {
  if (embersLit) return;
  embersLit = true;
  $('#embers').innerHTML = Array.from({ length: 18 }, (_, i) => {
    const r = (k) => ((Math.sin(i * 12.9898 + k * 78.233) * 43758.5453) % 1 + 1) % 1;
    return `<i style="left:${(r(1) * 100).toFixed(1)}%;--dx:${((r(2) - 0.5) * 120).toFixed(0)}px;animation-duration:${(9 + r(3) * 9).toFixed(1)}s;animation-delay:-${(r(4) * 18).toFixed(1)}s;transform:scale(${(0.6 + r(5)).toFixed(2)})"></i>`;
  }).join('');
}
settingsRows.push({
  sync() {
    const th = themeOf();
    $('#set-theme').innerHTML = THEMES.map((x) => `<button role="radio" aria-checked="${x.key === th.key}" data-v="${x.key}" class="theme-card"><span class="sw3">${x.swatch.map((c) => `<i style="background:${c}"></i>`).join('')}</span>${esc(t(x.name))}</button>`).join('');
    $$('#set-theme button').forEach((b) => (b.onclick = () => { prefs.theme = b.dataset.v; savePrefs(); applyTheme(); syncPersonal(); }));
    $('#set-accent').innerHTML = th.own ? `<span class="dim small">${esc(t('This theme has its own accent.'))}</span>`
      : Object.entries(ACCENTS).map(([k, a]) => `<button role="radio" aria-checked="${(prefs.accent || 'cyan') === k}" data-v="${k}" style="--sw:${a[ACCENT_TONE[th.key]][0]}" title="${esc(t(a.name))}" aria-label="${esc(t(a.name))}"></button>`).join('');
    $$('#set-accent button').forEach((b) => (b.onclick = () => { prefs.accent = b.dataset.v; savePrefs(); applyTheme(); syncPersonal(); }));
  },
});

// Units or language changed: everything that shows a number or a word again.
function refreshWords() {
  applyI18n();
  fitSoon();
  syncToolbar();
  renderTags(); renderStrip(); renderWork(); renderList(); renderEmpty();
  if (state.detail) { renderAll(); if (state.compare) renderDelta(); setupAnimBar(); }
  placeLabels();
}

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
  for (const [k, label] of [['addressed', N_('Show the notes to check')], ['open', N_('Show the open notes')], ['working', N_("Show the models in Claude's run")], ['building', N_('Show the models being built')]]) {
    add('List', label, [], () => { state.pill = k; renderStrip(); renderList(); if (!isOpen(left)) setPanel(left, true); });
  }
  add('List', 'Show every model', [], () => { state.pill = null; state.tags.clear(); $('#search').value = ''; $('#filter').value = 'all'; renderTags(); renderStrip(); renderList(); }, () => state.pill || state.tags.size || $('#search').value || $('#filter').value !== 'all');
  add('Panels', 'Fold or unfold the model list', ['['], keyActions['[']);
  add('Panels', 'Fold or unfold the notes panel', [']'], keyActions[']']);
  add('Panels', 'Fold or unfold both panels', ['\\'], keyActions['\\']);
  for (const [tab, label] of [['notes', N_('Open the Notes tab')], ['checks', N_('Open the Checks tab')], ['details', N_('Open the Details tab')], ['history', N_('Open the History tab')]]) add('Panels', label, [], () => ensureRight(tab), hasModel);
  for (const [k, v, label] of [['1', 'front', N_('Front view')], ['2', 'back', N_('Back view')], ['3', 'left', N_('Left view')], ['4', 'right', N_('Right view')], ['5', 'top', N_('Top view')], ['6', 'iso', N_('Three-quarter view')]]) add('View', label, [k], () => viewer.view(v), hasModel);
  add('View', 'Frame the model', ['F'], () => viewer.frame(), hasModel);
  for (const [m, label] of [['lit', N_('Shading: Lit')], ['unlit', N_('Shading: Unlit')], ['clay', N_('Shading: Clay')], ['normals', N_('Shading: Normals')], ['uv', N_('Shading: UV checker')], ['faces', N_('Shading: Faces, back faces in red')]]) add('Shading', label, [], () => setOpt('shade', m), () => hasModel() && viewer.opts.shade !== m);
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
  add('Help', 'Settings', [], () => openSettings());
  for (const [th, label] of [['dark', N_('Theme: Dark')], ['light', N_('Theme: Light')], ['contrast', N_('Theme: High contrast')], ['forge', N_('Theme: Forge')], ['neon', N_('Theme: Neon')], ['studio', N_('Theme: Studio')], ['minimal', N_('Theme: Minimal')]]) add('Help', label, [], () => { prefs.theme = th; savePrefs(); applyTheme(); }, () => themeOf().key !== th);
  for (const run of paletteExtras) run(add);
  for (const a of state.assets) add('Model', { text: t('Open {name}', { name: a.name }) }, [], () => go(a.id), () => a.id !== state.id);
  return C.filter((c) => { try { return c.when(); } catch { return false; } });
}

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
  applyTheme();
  setUnits(prefs.units);
  // The language: the one chosen, else the browser's when Studio speaks it.
  const want = prefs.lang || ((navigator.language || '').toLowerCase().startsWith('fr') ? 'fr' : 'en');
  try { await loadLanguage(want); setLang(want); } catch { setLang('en'); }
  try { setCheckMessages((await api('/api/messages')).messages); } catch { /* the server's English text stands in */ }
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
  claudeStatus().then(() => { renderClaude(); if (!state.assets.length && !state.id) renderWelcome(); });
  fromHash();
  // The fonts change the bar's width once they load.
  document.fonts?.ready.then(fitSoon);
  window.__studio = { state, viewer, openAsset, setCompare, startPin, startGeneral, get detail() { return state.detail; } };
})();

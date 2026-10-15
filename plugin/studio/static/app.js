// Kiln Studio. Talks to server.py; the 3D view is viewer.js; the Checks tab reads checks.py.
// Notes go open → addressed (Claude changed the model and replied) → resolved (you
// checked it) or won't fix. Each note keeps a screenshot of the model as it was; when
// Claude marks one addressed, the page renders the same view of the new version
// beside it, so every note carries its own before and after.
import { Viewer, Offscreen, Superseded, fmtM } from './viewer.js';

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const enc = encodeURIComponent;
const fileUrl = (rel, h) => '/files/' + rel.split('/').map(enc).join('/') + (h ? `?h=${h}` : '');
// Same as studiolib.asset_key.
const keyOf = (id) => id.replaceAll('%', '%25').replaceAll('~', '%7E').replaceAll('/', '~');
const fmtN = (n) => (n == null ? '–' : n.toLocaleString('en-US'));
const fmtB = (b) => (b >= 1e6 ? (b / 1e6).toFixed(2) + ' MB' : (b / 1e3).toFixed(1) + ' kB');
const pct = (a, b) => (b ? Math.round(((a - b) / b) * 100) : 0);
const ACTIVE = new Set(['open', 'addressed']);
const SHADES = ['lit', 'unlit', 'clay', 'normals', 'uv', 'faces'];
const STATUS_LABEL = { open: 'open', addressed: 'addressed', resolved: 'resolved', wontfix: "won't fix" };
// kiln's phases (studiolib.PHASES); rig and animate show only when a build reports them.
const PHASES = ['config', 'brief', 'source', 'import', 'cleanup', 'texture', 'rig', 'animate', 'optimize', 'export'];
const OPTIONAL_PHASES = new Set(['rig', 'animate']);
const LEVEL_LABEL = { ok: 'ok', info: 'note', warn: 'check' };
// 1500 → 1.5K, as checks.kfmt.
const fmtK = (n) => (n >= 1e6 ? `${+(n / 1e6).toFixed(2)}M` : n >= 1000 ? `${+(n / 1000).toFixed(1)}K` : `${n}`);
const fmtTok = (r) => (!r ? '–' : r[0] === r[1] ? `~${fmtK(r[0])} tokens` : `~${fmtK(r[0])}–${fmtK(r[1])} tokens`);

function ago(iso) {
  if (!iso) return '';
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 45) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  if (s < 86400 * 14) return `${Math.round(s / 86400)} d ago`;
  return new Date(iso).toLocaleDateString();
}

// ── state ────────────────────────────────────────────────────────────────────

const prefs = JSON.parse(localStorage.getItem('kiln-studio:prefs') || '{}');
const savePrefs = () => localStorage.setItem('kiln-studio:prefs', JSON.stringify(prefs));
const state = {
  root: '', assets: [], byId: new Map(), batches: {},
  id: null, detail: null, variant: null, clientStats: null,
  tags: new Set(), noteFilter: 'active', pinsOn: prefs.pins ?? true,
  pinning: false, draft: null, hl: null, editing: null, replying: null,
  compare: null, // { target: 'baseline' | variant label }
  work: null, // which models a kiln command is on: studiolib.work_view
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

// ── viewer ───────────────────────────────────────────────────────────────────

const stage = $('#stage');
const viewer = new Viewer($('#view'));
for (const k of ['shade', 'wire', 'grid', 'bounds', 'bg']) if (prefs[k] !== undefined) viewer.opts[k] = prefs[k];
stage.dataset.bg = viewer.opts.bg;
let offscreen = null;
const off = () => (offscreen ||= new Offscreen());

let pinsDirty = true;
viewer.onChange = () => { pinsDirty = true; occlusionSoon(); };
viewer.onFrame = () => { if (pinsDirty) { placePins(); pinsDirty = false; } };
viewer.onAnimate = () => {
  const d = viewer.clipDuration;
  if (!d) return;
  $('#a-time').value = (viewer.clipTime % d) / d;
  $('#a-readout').textContent = `${(viewer.clipTime % d).toFixed(2)} / ${d.toFixed(2)} s`;
  pinsDirty = true;
};

function syncToolbar() {
  $$('#toolbar [data-shade]').forEach((b) => b.classList.toggle('on', b.dataset.shade === viewer.opts.shade));
  $$('#toolbar [data-opt]').forEach((b) => b.classList.toggle('on', !!viewer.opts[b.dataset.opt]));
  const pins = $('#t-pins'), label = state.pinsOn ? 'Hide pins' : 'Show pins';
  pins.classList.toggle('on', state.pinsOn);
  pins.setAttribute('aria-pressed', String(state.pinsOn));
  pins.setAttribute('aria-label', label);
  pins.title = `${label} (P)`;
  $('#t-compare').classList.toggle('on', !!state.compare);
  $('#t-pin').classList.toggle('on', state.pinning);
  $('#t-bg').textContent = { dark: 'Dark', mid: 'Mid', light: 'Light' }[viewer.opts.bg];
}

function setOpt(k, v) {
  viewer.set(k, v);
  prefs[k] = v; savePrefs();
  if (k === 'bg') stage.dataset.bg = v;
  syncToolbar();
}

$$('#toolbar [data-shade]').forEach((b) => (b.onclick = () => setOpt('shade', b.dataset.shade)));
$$('#toolbar [data-opt]').forEach((b) => (b.onclick = () => setOpt(b.dataset.opt, !viewer.opts[b.dataset.opt])));
$$('#views [data-view]').forEach((b) => (b.onclick = () => viewer.view(b.dataset.view)));
$('#t-frame').onclick = () => viewer.frame();
$('#t-bg').onclick = () => setOpt('bg', { dark: 'mid', mid: 'light', light: 'dark' }[viewer.opts.bg]);
$('#t-pins').onclick = () => { state.pinsOn = !state.pinsOn; prefs.pins = state.pinsOn; savePrefs(); renderPins(); syncToolbar(); };
$('#t-compare').onclick = () => toggleCompare();
$('#t-pin').onclick = () => (state.pinning ? cancelDraft() : startPin());
$('#t-general').onclick = () => startGeneral();

// ── toast, hint, dialogs ─────────────────────────────────────────────────────

let toastTimer;
function toast(msg, warn = false, ms = 3800) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.toggle('warn', warn);
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), ms);
}
function hint(msg) { $('#hint').hidden = !msg; $('#hint').textContent = msg || ''; }

function confirmDialog(text, ok = 'OK') {
  const d = $('#confirm');
  $('p', d).textContent = text;
  $('button[value=ok]', d).textContent = ok;
  d.returnValue = '';
  d.showModal();
  return new Promise((res) => d.addEventListener('close', () => res(d.returnValue === 'ok'), { once: true }));
}

// extra: trusted HTML shown under the images (already escaped by the caller).
function lightbox(items, extra = '') {
  const fig = $('#lightbox figure');
  fig.innerHTML = items.map((it) => `<div><img src="${esc(it.src)}" alt=""><figcaption>${esc(it.caption || '')}</figcaption></div>`).join('');
  $('#lightbox .lb-extra').innerHTML = extra;
  $('#lightbox').showModal();
}

async function textDialog(title, rel) {
  const d = $('#textbox');
  $('h3', d).textContent = title;
  $('pre', d).textContent = 'Loading…';
  d.showModal();
  try { $('pre', d).textContent = await (await fetch(fileUrl(rel))).text(); } catch (e) { $('pre', d).textContent = String(e); }
}

async function copy(text) {
  try { await navigator.clipboard.writeText(text); toast(`Copied: ${text}`); } catch { toast(text); }
}

// ── the model list ───────────────────────────────────────────────────────────

async function fetchAssets() {
  const data = await api('/api/assets');
  state.root = data.root;
  state.assets = data.assets;
  state.byId = new Map(data.assets.map((a) => [a.id, a]));
  state.batches = data.batches || {};
  state.work = data.work || null;
  if (!Object.keys(seen).length) seen = JSON.parse(localStorage.getItem(`kiln-studio:seen:${data.root}`) || '{}');
  $('#project').textContent = data.root;
  $('#project').title = data.root;
  document.title = `${data.name} · Kiln Studio`;
  renderTags();
  renderList();
  renderWork();
  queuePendingShots();
}

function markSeen(a) {
  if (!a) return;
  seen[a.id] = a.variants[0]?.hash;
  localStorage.setItem(`kiln-studio:seen:${state.root}`, JSON.stringify(seen));
  $(`#list .item[data-id="${CSS.escape(a.id)}"] .badge.changed`)?.remove();
}

function renderTags() {
  const all = new Set(state.assets.flatMap((a) => a.tags));
  for (const t of [...state.tags]) if (!all.has(t)) state.tags.delete(t);
  $('#tagbar').innerHTML = [...all].sort().map((t) => `<button class="tag${state.tags.has(t) ? ' on' : ''}" data-tag="${esc(t)}">#${esc(t)}</button>`).join('');
  $$('#tagbar .tag').forEach((b) => (b.onclick = () => {
    const t = b.dataset.tag;
    state.tags.has(t) ? state.tags.delete(t) : state.tags.add(t);
    renderTags(); renderList();
  }));
}

function visibleAssets() {
  const q = $('#search').value.trim().toLowerCase();
  const f = $('#filter').value;
  const keep = (a) => {
    if (q && !(a.id.toLowerCase().includes(q) || a.tags.some((t) => t.includes(q)) || (a.category || '').toLowerCase().includes(q))) return false;
    for (const t of state.tags) if (!a.tags.includes(t)) return false;
    const c = a.counts;
    if (f === 'open') return c.open > 0;
    if (f === 'addressed') return c.addressed > 0;
    if (f === 'notes') return Object.values(c).some((n) => n > 0);
    if (f === 'clean') return !Object.values(c).some((n) => n > 0);
    return true;
  };
  const sort = $('#sort').value;
  const cmp = {
    name: (a, b) => a.name.localeCompare(b.name),
    updated: (a, b) => b.updated - a.updated,
    tris: (a, b) => (b.tris || 0) - (a.tris || 0),
  }[sort];
  return state.assets.filter(keep).sort(cmp);
}

const collapsed = new Set(JSON.parse(localStorage.getItem('kiln-studio:collapsed') || '[]'));
function renderList() {
  const items = visibleAssets();
  const groups = new Map();
  for (const a of items) {
    const c = a.category || '';
    if (!groups.has(c)) groups.set(c, []);
    groups.get(c).push(a);
  }
  const filtering = $('#search').value || $('#filter').value !== 'all' || state.tags.size;
  const list = $('#list');
  list.innerHTML = '';
  for (const [cat, group] of [...groups].sort((x, y) => x[0].localeCompare(y[0]))) {
    const d = document.createElement('details');
    d.open = filtering || !collapsed.has(cat) || group.some((a) => a.id === state.id);
    const open = group.reduce((s, a) => s + a.counts.open, 0);
    const b = state.batches[cat];
    const est = b ? `<span class="est" title="Batch ${esc(b.name)}: token estimate for its ${b.assets} assets, ±50% (batch-mode.md). ${b.remaining.assets} left to run: ${esc(fmtTok(b.remaining.range))}.">${esc(fmtTok(b.range).replace(' tokens', ' tok'))}</span>` : '';
    d.innerHTML = `<summary><span class="cat" title="${esc(cat || 'project root')}">${esc(cat || 'project root')}</span><span class="n">${group.length}${open ? ` · ${open} open` : ''}${est}</span></summary>`;
    d.addEventListener('toggle', () => {
      if (filtering) return;
      d.open ? collapsed.delete(cat) : collapsed.add(cat);
      localStorage.setItem('kiln-studio:collapsed', JSON.stringify([...collapsed]));
    });
    for (const a of group) d.appendChild(itemEl(a));
    list.appendChild(d);
  }
  if (!items.length) list.innerHTML = `<p class="dim" style="padding:12px">${state.assets.length ? 'Nothing matches.' : 'No models in this folder yet. Export a .glb, .gltf, .fbx or .obj anywhere under it and it appears here.'}</p>`;
  const t = state.assets.reduce((s, a) => ({ open: s.open + a.counts.open, addr: s.addr + a.counts.addressed }), { open: 0, addr: 0 });
  $('#totals').textContent = `${state.assets.length} model${state.assets.length === 1 ? '' : 's'} · ${t.open} open · ${t.addr} to check`;
}

function itemEl(a) {
  const el = document.createElement('div');
  el.className = 'item' + (a.id === state.id ? ' sel' : '');
  el.dataset.id = a.id;
  el.tabIndex = 0;
  const v = a.variants[0];
  const changed = seen[a.id] && seen[a.id] !== v.hash && a.id !== state.id;
  const building = a.live?.state === 'building';
  const dot = state.work?.dots[a.id];
  const sub = building ? `building · ${a.live.phase || 'starting'}` : [a.tris != null ? `${fmtN(a.tris)} tris` : v.ext.slice(1).toUpperCase(),
    a.variants.length > 1 ? `${a.variants.length} ${a.kiln ? 'stages' : 'files'}` : fmtB(v.size)].join(' · ');
  el.innerHTML = `<img class="thumb" alt="" ${a.thumb ? `src="${esc(fileUrl(a.thumb))}"` : ''}>
    <div style="min-width:0"><div class="name" title="${esc(a.id)}">${esc(a.name)}</div><div class="sub">${esc(sub)}</div></div>
    <span class="badges">${building && dot?.state !== 'active' ? '<span class="badge building" title="kiln is building it: open it to watch">●</span>' : ''}${changed ? '<span class="badge changed" title="Changed since you last looked">new</span>' : ''}${a.counts.open ? `<span class="badge open" title="Open notes">${a.counts.open}</span>` : ''}${a.counts.addressed ? `<span class="badge addressed" title="Addressed by Claude: check them">${a.counts.addressed}</span>` : ''}<span class="wslot">${workDot(dot)}</span></span>`;
  el.onclick = () => go(a.id);
  el.onkeydown = (e) => { if (e.key === 'Enter') go(a.id); };
  if (!a.thumb) thumbObserver.observe(el);
  return el;
}

// ── what kiln is working on ──────────────────────────────────────────────────
// A kiln command run on models here reports them (studio.py work): a dot per model,
// waiting, breathing while kiln is on it, green once done until the user has looked.

const WORK_TITLE = {
  queued: 'Waiting: kiln works on it later in this run',
  active: 'Kiln is working on it',
  done: 'Kiln is done with it: open it to check',
};
function workDot(d) {
  if (!d) return '';
  const title = [WORK_TITLE[d.state], d.text].filter(Boolean).join(' · ');
  return `<span class="wdot ${d.state}" role="img" aria-label="${esc(title)}" title="${esc(title)}"></span>`;
}

function renderWork() {
  const w = state.work;
  // While a run shows, every row keeps the dot's slot at its right edge: dots in one
  // column, chips that do not move as dots come and go.
  $('#list').classList.toggle('working', !!w);
  for (const el of $$('#list .item')) {
    const d = w?.dots[el.dataset.id];
    const cur = $('.wdot', el);
    if (!d) { cur?.remove(); continue; }
    if (cur?.classList.contains(d.state)) continue;
    cur?.remove();
    $('.wslot', el).innerHTML = workDot(d);
    $('.badge.building', el)?.toggleAttribute('hidden', d.state === 'active');
  }
  const bar = $('#work');
  bar.hidden = !w;
  if (!w) return;
  const left = Object.values(w.dots).filter((d) => d.state === 'done').length;
  const name = (id) => state.byId.get(id)?.name || id.split('/').pop();
  const what = w.label ? ` · ${esc(w.label)}` : '';
  bar.innerHTML = w.running
    ? `<span class="wdot active"></span><button class="go" ${w.active ? `data-id="${esc(w.active)}"` : ''}>Kiln${what} · ${w.done} of ${w.total}${w.active ? ` · ${esc(name(w.active))}` : ''}</button>`
    : `<span class="wdot done"></span><span title="${esc(w.label || '')}">Kiln is done · ${left} to check</span><button class="clear" title="Clear the green dots without opening each model">Clear</button>`;
  const go_ = $('.go', bar);
  if (go_) go_.onclick = () => go_.dataset.id && go(go_.dataset.id);
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
  try { await api('/api/work/check', { method: 'POST', body: { assets: ids ? done : null } }); } catch { /* the next work event says */ }
}

function onWork(next, prev) {
  state.work = next;
  renderWork();
  if (!next) return;
  const name = (id) => state.byId.get(id)?.name || id.split('/').pop();
  if (next.running && next.active && next.active !== prev?.active) {
    const finished = prev?.active && next.dots[prev.active]?.state === 'done';
    toast(finished ? `Kiln is done with ${name(prev.active)} · now on ${name(next.active)}` : `Kiln is working on ${name(next.active)}`);
    // Nothing open yet: open the model kiln is on.
    if (!state.id) go(next.active);
  } else if (!next.running && prev?.running && !next.stale) {
    const n = Object.values(next.dots).filter((d) => d.state === 'done').length;
    toast(`Kiln is done: ${n} model${n === 1 ? '' : 's'} to check`);
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

$('#search').oninput = renderList;
$('#filter').onchange = renderList;
$('#sort').onchange = () => { prefs.sort = $('#sort').value; savePrefs(); renderList(); };
if (prefs.sort) $('#sort').value = prefs.sort;

function go(id) {
  if (id === state.id) return;
  location.hash = id.split('/').map(enc).join('/');
}

function step(dir) {
  const ids = $$('#list .item').map((e) => e.dataset.id);
  if (!ids.length) return;
  const i = ids.indexOf(state.id);
  go(ids[(i + dir + ids.length) % ids.length] ?? ids[0]);
}

// ── opening a model ──────────────────────────────────────────────────────────

async function openAsset(id) {
  const a = state.byId.get(id);
  if (!a) { toast(`No model "${id}" in this project`, true); return; }
  if (state.compare) toggleCompare(false);
  cancelDraft();
  const left = state.id;
  state.id = id;
  state.hl = null;
  state.editing = state.replying = null;
  $$('#list .item').forEach((e) => e.classList.toggle('sel', e.dataset.id === id));
  $('#list .item.sel')?.scrollIntoView({ block: 'nearest' });
  $('#empty').hidden = true;
  $('#titlebar').hidden = $('#toolbar').hidden = $('#views').hidden = $('#side').hidden = false;
  await fetchDetail();
  const keep = state.detail.variants.find((v) => v.label === state.variant);
  await loadVariant(keep ? keep.label : state.detail.variants[0].label, { keepCamera: false });
  markSeen(a);
  // Opening a model kiln finished, or leaving the one you watched it finish: checked.
  checkWork([id, left].filter(Boolean));
  for (const v of state.detail.variants) if (!state.detail.thumbs.includes(v.hash)) queueThumb(id, v);
  queueAfterShots(state.detail);
}

async function fetchDetail() {
  const id = state.id;
  const d = await assetApi(id);
  if (id !== state.id) return;
  state.detail = d;
  const a = state.byId.get(id);
  if (a) Object.assign(a, { counts: d.counts, tags: d.tags, category: d.category, thumb: d.thumb, variants: d.variants });
  renderAll();
}

function currentVariant() {
  return state.detail?.variants.find((v) => v.label === state.variant) || state.detail?.variants[0];
}

async function loadVariant(label, { keepCamera = true } = {}) {
  state.variant = label;
  const v = currentVariant();
  const seq = ++state.loadSeq;
  $('#loading').hidden = false;
  try {
    const stats = await viewer.load(fileUrl(v.file, v.hash), v.ext, { keepCamera });
    if (seq !== state.loadSeq) return;
    state.clientStats = stats;
    if (!keepCamera) viewer.view(prefs.view || 'iso');
    if (state.compare) await loadCompareTarget();
  } catch (e) {
    if (e instanceof Superseded) return;
    console.error(e);
    // 409: re-exported while loading; the live event that follows loads the new one.
    if (seq === state.loadSeq && !/409/.test(String(e.message))) { state.clientStats = null; toast(`Could not load ${v.file}: ${e.message || e}`, true, 8000); }
  } finally {
    if (seq === state.loadSeq) $('#loading').hidden = true;
  }
  setupAnimBar();
  renderAll();
}

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
}

function renderTitle() {
  const d = state.detail, v = currentVariant(), s = state.clientStats;
  $('#asset-name').textContent = d.name;
  $('#asset-name').title = d.id;
  $('#variants').innerHTML = d.variants.length > 1
    ? d.variants.map((x) => `<button role="tab" class="${x.label === v.label ? 'on' : ''}" data-v="${esc(x.label)}" title="${esc(x.file)}">${esc(x.label)}</button>`).join('')
    : '';
  $$('#variants button').forEach((b) => (b.onclick = () => loadVariant(b.dataset.v)));
  const tris = v.stats?.tris ?? s?.tris;
  const dims = v.stats?.dimensions_blender || s?.dims;
  $('#asset-stats').innerHTML = [
    `<b>${fmtN(tris)}</b> tris`, fmtB(v.size),
    dims ? `${fmtM(dims[0])} × ${fmtM(dims[1])} × ${fmtM(dims[2])}` : '',
  ].filter(Boolean).join(' · ');
  $('#asset-stats').title = 'Triangles · file size · Blender X × Y × Z';
}

// ── pins ─────────────────────────────────────────────────────────────────────

function noteNumber(n) { return state.detail.notes.indexOf(n) + 1; }
function shownNotes() {
  const all = state.detail?.notes || [];
  return state.noteFilter === 'all' ? all : all.filter((n) => ACTIVE.has(n.status));
}

function renderPins() {
  const box = $('#pins');
  box.innerHTML = '';
  const pinned = state.detail ? shownNotes().filter((n) => n.anchor) : [];
  // The eye only appears once there is a pin on the model to hide.
  $('#t-pins').hidden = !pinned.length;
  if (!state.detail) return;
  const notes = state.pinsOn ? pinned : [];
  for (const n of notes) {
    const el = document.createElement('div');
    el.className = `pin ${n.status}${state.hl === n.id ? ' hl' : ''}`;
    el.dataset.id = n.id;
    el.innerHTML = `<span>${noteNumber(n)}</span>`;
    el.title = n.text.slice(0, 140);
    el.onclick = (e) => { e.stopPropagation(); highlight(n.id, { scroll: true }); };
    el.ondblclick = (e) => { e.stopPropagation(); if (n.camera) viewer.setCamera(n.camera); };
    box.appendChild(el);
  }
  if (state.draft?.anchor) {
    const el = document.createElement('div');
    el.className = 'pin draft';
    el.dataset.draft = '1';
    el.innerHTML = '<span>+</span>';
    box.appendChild(el);
  }
  pinsDirty = true;
  occlusionSoon();
}

function placePins() {
  if (!state.detail) return;
  const byId = new Map(state.detail.notes.map((n) => [n.id, n]));
  for (const el of $('#pins').children) {
    const p = el.dataset.draft ? state.draft?.anchor?.point : byId.get(el.dataset.id)?.anchor?.point;
    if (!p) continue;
    const s = viewer.toScreen(p);
    el.style.display = s.behind || !s.inView ? 'none' : '';
    el.style.left = `${s.x}px`;
    el.style.top = `${s.y}px`;
  }
  const labels = viewer.boundsLabels();
  $('#overlay').innerHTML = labels.filter((l) => !l.behind).map((l) => `<div class="size-label" style="left:${l.x}px;top:${l.y}px">${esc(l.text)}</div>`).join('');
}

let occTimer;
function occlusionSoon() {
  clearTimeout(occTimer);
  occTimer = setTimeout(() => {
    if (!state.detail) return;
    const byId = new Map(state.detail.notes.map((n) => [n.id, n]));
    for (const el of $('#pins').children) {
      const n = byId.get(el.dataset.id);
      if (n?.anchor) el.classList.toggle('hidden-behind', viewer.occluded(n.anchor.point));
    }
  }, 140);
}

function highlight(id, { scroll = false } = {}) {
  state.hl = state.hl === id && !scroll ? null : id;
  $$('#pins .pin').forEach((p) => p.classList.toggle('hl', p.dataset.id === state.hl));
  $$('#note-list .note').forEach((n) => n.classList.toggle('hl', n.dataset.id === state.hl));
  if (scroll && state.hl) {
    switchTab('notes');
    $(`#note-list .note[data-id="${state.hl}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
}

// ── composing a note ─────────────────────────────────────────────────────────

function startPin() {
  if (!state.detail) return;
  cancelDraft();
  state.pinning = true;
  stage.classList.add('pinning');
  hint('Click the model where the note applies · Esc cancels');
  syncToolbar();
}

function startGeneral() {
  if (!state.detail) return;
  cancelDraft();
  openComposer({ anchor: null });
}

function openComposer(draft) {
  state.draft = draft;
  state.pinning = false;
  stage.classList.remove('pinning');
  hint('');
  switchTab('notes');
  const a = draft.anchor;
  $('#composer-where').innerHTML = a
    ? `Pinned on <b>${esc(a.object || a.mesh || 'the model')}</b>${a.material ? ` · ${esc(a.material)}` : ''} · ${esc(a.region)}`
    : 'About the whole model, as seen from this view';
  $('#composer').hidden = false;
  $('#composer-text').value = '';
  $('#composer-text').focus();
  renderPins();
  syncToolbar();
}

function cancelDraft() {
  state.pinning = false;
  state.draft = null;
  stage.classList.remove('pinning');
  $('#composer').hidden = true;
  hint('');
  renderPins();
  syncToolbar();
}

async function saveNote() {
  const text = $('#composer-text').value.trim();
  if (!text) { $('#composer-text').focus(); return; }
  const draft = state.draft, id = state.id;
  const btn = $('#composer-save');
  btn.disabled = true;
  try {
    // The view as it is now, the pin ringed: what the model looked like when you asked.
    const shot = viewer.screenshot({ ring: draft.anchor?.point });
    const note = await assetApi(id, '/notes', {
      method: 'POST',
      body: { text, variant: state.variant, anchor: draft.anchor, camera: viewer.cameraState(), shot },
    });
    cancelDraft();
    state.noteFilter = 'active';
    await fetchDetail();
    highlight(note.id);
    toast(`Note saved. Hand it to Claude with /kiln studio ${id}`);
  } catch (e) {
    toast(`Could not save the note: ${e.message}`, true, 8000);
  } finally {
    btn.disabled = false;
  }
}
$('#composer-save').onclick = saveNote;
$('#composer-cancel').onclick = cancelDraft;
$('#composer-text').onkeydown = (e) => {
  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); saveNote(); }
  if (e.key === 'Escape') { e.preventDefault(); cancelDraft(); }
};

// clicks on the model: pin placement, or a plain click to clear the highlight
const canvas = $('#view');
let down = null;
canvas.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY }; });
canvas.addEventListener('pointerup', (e) => {
  if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4) { down = null; return; }
  down = null;
  if (state.pinning) {
    const anchor = viewer.pick(e.clientX, e.clientY);
    if (!anchor) { hint(viewer.compare ? 'Pin on the right-hand model · Esc cancels' : 'That missed the model. Click on it · Esc cancels'); return; }
    openComposer({ anchor });
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
    const p = h.point_blender.map((x) => x.toFixed(3)).join(', ');
    el.innerHTML = `${esc(h.object || h.mesh)}${h.material ? ` · ${esc(h.material)}` : ''}<br>Blender (${p}) m`;
    el.hidden = false;
  });
});
canvas.addEventListener('pointerleave', () => ($('#hover').hidden = true));

// ── notes panel ──────────────────────────────────────────────────────────────

function switchTab(name) {
  $$('.tabs [data-tab]').forEach((b) => b.classList.toggle('on', b.dataset.tab === name));
  for (const t of ['notes', 'checks', 'details', 'history']) $(`#tab-${t}`).hidden = t !== name;
}
$$('.tabs [data-tab]').forEach((b) => (b.onclick = () => switchTab(b.dataset.tab)));
$$('[data-nf]').forEach((b) => (b.onclick = () => {
  state.noteFilter = b.dataset.nf;
  $$('[data-nf]').forEach((x) => x.classList.toggle('on', x === b));
  renderNotes(); renderPins();
}));

function latestShot(n) {
  for (let i = (n.thread || []).length - 1; i >= 0; i--) if (n.thread[i].shot) return n.thread[i];
  return null;
}

function noteEl(n) {
  const d = state.detail;
  const cur = d.variants.find((v) => v.label === n.version?.variant);
  // Expected once Claude has re-exported; worth a word only while the note is still open.
  const stale = n.status === 'open' && cur && n.version?.hash && cur.hash !== n.version.hash;
  const after = latestShot(n);
  const lastAddressed = [...(n.thread || [])].reverse().find((r) => r.status === 'addressed');
  const waiting = lastAddressed && !lastAddressed.shot && d.pending.some((p) => p.reply === lastAddressed.id);
  const a = n.anchor;
  const shots = [];
  if (n.shot) shots.push(`<figure><img src="${esc(fileUrl(n.shot))}" alt="The model when the note was made" data-shot="before"><figcaption>Before</figcaption></figure>`);
  if (after) shots.push(`<figure><img src="${esc(fileUrl(after.shot))}" alt="The model after the change" data-shot="after"><figcaption>After</figcaption></figure>`);
  else if (waiting) shots.push('<div class="pending">Rendering the after view…</div>');
  const el = document.createElement('article');
  el.className = `note ${n.status}${state.hl === n.id ? ' hl' : ''}`;
  el.dataset.id = n.id;
  el.innerHTML = `
    <header><span class="num ${a ? '' : 'general'}">${noteNumber(n)}</span>
      <span class="status ${n.status}">${STATUS_LABEL[n.status]}</span>
      <span class="dim">${a ? 'pin' : 'whole model'}${d.variants.length > 1 ? ` · ${esc(n.version?.variant || '')}` : ''}</span>
      <span class="when" title="${esc(n.created)}">${ago(n.created)}</span></header>
    ${state.editing === n.id
      ? `<textarea class="edit-text" rows="3">${esc(n.text)}</textarea><div class="actions"><button class="accent" data-act="save-edit">Save</button><button data-act="cancel-edit">Cancel</button></div>`
      : `<div class="text">${esc(n.text)}</div>`}
    ${a ? `<div class="where">${esc(a.object || a.mesh || '')}${a.material ? ` · ${esc(a.material)}` : ''} · ${esc(a.region || '')}</div>` : ''}
    ${stale ? `<div class="stale">Made on an earlier version (${esc(n.version.hash.slice(0, 7))}); the pin may have moved.</div>` : ''}
    ${shots.length ? `<div class="shots${shots.length === 1 ? ' one' : ''}">${shots.join('')}</div>` : ''}
    ${(n.thread || []).length ? `<div class="thread">${n.thread.map(replyHtml).join('')}</div>` : ''}
    ${state.replying?.id === n.id ? replyBox(state.replying.status) : ''}
    <div class="actions">${actionsHtml(n)}</div>`;
  el.onclick = (e) => {
    const act = e.target.closest('[data-act]')?.dataset.act;
    if (act) { e.stopPropagation(); noteAction(n, act, el); return; }
    const img = e.target.closest('img[data-shot]');
    if (img) { openShots(n); return; }
    if (!e.target.closest('textarea, button')) highlight(n.id);
  };
  el.ondblclick = (e) => { if (!e.target.closest('textarea, button') && n.camera) viewer.setCamera(n.camera); };
  return el;
}

function replyHtml(r) {
  const st = r.status ? ` <span class="status ${r.status}">${STATUS_LABEL[r.status]}</span>` : '';
  const ver = r.status === 'addressed' && r.version ? ` · on ${esc(r.version.variant)} ${esc(r.version.hash.slice(0, 7))}` : '';
  return `<div class="reply ${r.by}"><div class="who"><b>${r.by === 'claude' ? 'Claude' : 'You'}</b> · ${ago(r.at)}${ver}${st}</div>${r.text ? `<div class="body">${esc(r.text)}</div>` : ''}</div>`;
}

function replyBox(status) {
  const ph = status === 'open' ? 'What still needs to change?' : 'Reply…';
  const label = status === 'open' ? 'Reopen' : 'Send';
  return `<div class="reply-box"><textarea class="reply-text" rows="2" placeholder="${ph}"></textarea><div class="row"><button class="accent" data-act="send-reply">${label}</button><button data-act="cancel-reply">Cancel</button></div></div>`;
}

function actionsHtml(n) {
  const view = n.camera ? '<button class="ghost" data-act="view" title="Go to the view the note was made from (double-click)">View</button>' : '';
  if (n.status === 'open') return `<button data-act="reply">Reply</button><button data-act="wontfix">Won't fix</button><button class="ghost" data-act="edit">Edit</button><button class="ghost" data-act="delete">Delete</button>${view}`;
  if (n.status === 'addressed') return `<button class="accent" data-act="resolve">Looks right</button><button data-act="reopen">Not yet…</button><button class="ghost" data-act="reply">Reply</button>${view}`;
  return `<button data-act="reopen">Reopen…</button><button class="ghost" data-act="delete">Delete</button>${view}`;
}

async function postReply(n, text, status) {
  await assetApi(state.id, `/notes/${n.id}/thread`, { method: 'POST', body: { text, status } });
  state.replying = null;
  await fetchDetail();
}

async function noteAction(n, act, el) {
  try {
    if (act === 'view') { if (n.camera) viewer.setCamera(n.camera); highlight(n.id); return; }
    if (act === 'resolve') { await postReply(n, '', 'resolved'); toast('Resolved'); return; }
    if (act === 'wontfix') { await postReply(n, '', 'wontfix'); return; }
    if (act === 'reply' || act === 'reopen') {
      state.replying = { id: n.id, status: act === 'reopen' ? 'open' : null };
      renderNotes();
      $(`#note-list .note[data-id="${n.id}"] .reply-box textarea`)?.focus();
      return;
    }
    if (act === 'cancel-reply') { state.replying = null; renderNotes(); return; }
    if (act === 'send-reply') {
      const text = $('.reply-box textarea', el).value.trim();
      if (!text && !state.replying.status) return;
      await postReply(n, text, state.replying.status);
      return;
    }
    if (act === 'edit') { state.editing = n.id; renderNotes(); $('.edit-text', $(`#note-list .note[data-id="${n.id}"]`))?.focus(); return; }
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
      if (!(await confirmDialog(`Delete note ${noteNumber(n)} and its screenshots?`, 'Delete'))) return;
      await assetApi(state.id, `/notes/${n.id}`, { method: 'DELETE' });
      await fetchDetail();
    }
  } catch (e) {
    toast(e.message, true, 8000);
  }
}

function openShots(n) {
  const items = [];
  if (n.shot) items.push({ src: fileUrl(n.shot), caption: `Before · ${n.version?.variant || ''} ${n.version?.hash?.slice(0, 7) || ''} · ${ago(n.created)}` });
  const after = latestShot(n);
  if (after) items.push({ src: fileUrl(after.shot), caption: `After · ${after.version?.variant || ''} ${after.version?.hash?.slice(0, 7) || ''} · ${ago(after.at)}` });
  if (!items.length) return;
  // The ask under the pictures, with the thread: what to look for in the after.
  const a = n.anchor;
  lightbox(items, `<div class="lb-note">
    <header><span class="status ${n.status}">${STATUS_LABEL[n.status]}</span><span class="dim">Note ${noteNumber(n)} · ${ago(n.created)}</span></header>
    <div class="text">${esc(n.text)}</div>
    ${a ? `<div class="where">${esc(a.object || a.mesh || '')}${a.material ? ` · ${esc(a.material)}` : ''} · ${esc(a.region || '')}</div>` : ''}
    ${(n.thread || []).length ? `<div class="thread">${n.thread.map(replyHtml).join('')}</div>` : ''}
  </div>`);
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
  const notes = shownNotes();
  const list = $('#note-list');
  list.innerHTML = '';
  for (const n of notes) list.appendChild(noteEl(n));
  if (!notes.length) {
    const total = d.notes.length;
    list.innerHTML = `<div class="empty-notes"><b>${total ? 'Nothing active' : 'No notes yet'}</b>${total
      ? `${total} closed note${total === 1 ? '' : 's'} under All.`
      : 'Pin a note on the model (N) or write one about the whole model (M). Claude reads them, changes the model, and replies here.'}</div>`;
  }
  const active = d.notes.filter((n) => ACTIVE.has(n.status)).length;
  $('#n-count').textContent = active ? `(${active})` : '';
  const open = d.counts.open;
  const cmd = `/kiln studio ${d.id}`;
  $('#handoff').innerHTML = open
    ? `${open} open note${open === 1 ? '' : 's'}. In Claude Code, run:<div class="cmd"><code>${esc(cmd)}</code><button data-copy>Copy</button></div>`
    : d.counts.addressed ? `${d.counts.addressed} note${d.counts.addressed === 1 ? '' : 's'} to check: Claude changed the model. Look, then mark each one <b>Looks right</b> or <b>Not yet</b>.` : '';
  $('#handoff [data-copy]')?.addEventListener('click', () => copy(cmd));
}

// ── details panel ────────────────────────────────────────────────────────────

function renderDetails() {
  keepTyping($('#tab-details'), renderDetailsNow);
}

function renderDetailsNow() {
  const d = state.detail, v = currentVariant(), st = v.stats || {}, cs = state.clientStats || {};
  const cats = [...new Set(state.assets.map((a) => a.category).filter(Boolean))].sort();
  const textures = cs.textures || [];
  const b = d.baseline;
  const blocks = [];
  blocks.push(`<div class="block"><h3>${d.kiln ? 'Pipeline stages' : 'Files'}</h3><table class="vt">
    <tr><th>${d.kiln ? 'Stage' : 'Format'}</th><th style="text-align:right">Size</th><th style="text-align:right">Tris</th><th></th></tr>
    ${d.variants.map((x) => `<tr class="${x.label === v.label ? 'cur' : ''}"><td><a href="#" data-v="${esc(x.label)}">${esc(x.label)}</a></td><td class="num">${fmtB(x.size)}</td><td class="num">${fmtN(x.stats?.tris)}</td><td><button class="ghost" data-copy="${esc(x.file)}" title="Copy the path">Path</button></td></tr>`).join('')}
  </table></div>`);
  const dims = st.dimensions_blender || cs.dims;
  const rows = [
    ['Triangles', fmtN(st.tris ?? cs.tris)], ['Vertices', fmtN(st.verts ?? cs.verts)],
    ['Meshes', fmtN(st.meshes ?? cs.meshes)],
    ['Size (Blender)', dims ? `X ${fmtM(dims[0])} · Y ${fmtM(dims[1])} · Z ${fmtM(dims[2])}` : '–'],
    ['Materials', (st.materials || cs.materials || []).map(esc).join(', ') || '–'],
    ['Textures', textures.length ? textures.map((t) => `${esc(t.slot)} ${t.w}×${t.h}`).join(', ') : (st.textures ? `${st.textures}` : '–')],
    ['Animations', (st.animations?.length ? st.animations.map((a) => `${esc(a.name)} ${a.duration}s`) : (cs.clips || []).map((c) => `${esc(c.name)} ${c.duration.toFixed(2)}s`)).join(', ') || '–'],
    ['Skins', st.skins ?? (cs.skinned ? 'yes' : '–')],
    ['Extensions', (st.extensions || []).map(esc).join(', ') || '–'],
    ['Exported by', esc(st.generator || '–')],
  ];
  const fmt = v.ext.slice(1).toUpperCase();
  blocks.push(`<div class="block"><h3>${v.label.toUpperCase() === fmt ? fmt : `${esc(v.label)} · ${fmt}`}</h3><dl class="kv">${rows.map(([k, val]) => `<dt>${k}</dt><dd>${val}</dd>`).join('')}</dl></div>`);
  blocks.push(`<div class="block"><h3>Organise</h3><div class="meta-form">
    <label>Category<input id="m-cat" list="m-cats" value="${esc(d.category)}" placeholder="${esc(d.folder)}"><datalist id="m-cats">${cats.map((c) => `<option value="${esc(c)}">`).join('')}</datalist></label>
    <label>Tags<div class="tags-edit">${d.tags.map((t) => `<span class="tag">#${esc(t)}<button data-untag="${esc(t)}" aria-label="Remove ${esc(t)}">×</button></span>`).join('')}<input id="m-tag" placeholder="add a tag ↵"></div></label>
  </div></div>`);
  blocks.push(`<div class="block"><h3>Previous version</h3>${b
    ? `<p class="dim" style="margin:0">${esc(b.variant)} ${esc(b.hash.slice(0, 7))} · ${fmtB(b.size)} · kept ${ago(b.at)} (${esc(b.reason)})</p>
       <div class="btns"><button data-act="cmp-prev">Compare</button><button data-act="revert">Put it back</button><button class="ghost" data-act="snapshot" title="Replace it with the version shown now">Keep this one instead</button></div>`
    : `<p class="dim" style="margin:0">Studio keeps one previous copy of the model: the version your first note on it was made on, so a review pass can be compared and undone.</p>
       <div class="btns"><button data-act="snapshot">Keep this version now</button></div>`}</div>`);
  const files = d.files || [];
  if (files.length) {
    blocks.push(`<div class="block"><h3>Beside it</h3><ul class="files">${files.map((f) => {
      const ext = f.slice(f.lastIndexOf('.')).toLowerCase();
      const name = f.split('/').pop();
      const act = ['.png', '.jpg', '.jpeg', '.webp'].includes(ext) ? `<button data-img="${esc(f)}">View</button>`
        : ['.md', '.txt', '.json', '.yaml', '.yml', '.py'].includes(ext) ? `<button data-text="${esc(f)}">Read</button>` : '';
      return `<li><span class="f" title="${esc(f)}">${esc(name)}</span>${act}<button class="ghost" data-copy="${esc(f)}">Path</button></li>`;
    }).join('')}</ul></div>`);
  }
  const tab = $('#tab-details');
  tab.innerHTML = blocks.join('');
  $$('[data-v]', tab).forEach((x) => (x.onclick = (e) => { e.preventDefault(); loadVariant(x.dataset.v); }));
  $$('[data-copy]', tab).forEach((x) => (x.onclick = () => copy(x.dataset.copy)));
  $$('[data-img]', tab).forEach((x) => (x.onclick = () => lightbox([{ src: fileUrl(x.dataset.img), caption: x.dataset.img }])));
  $$('[data-text]', tab).forEach((x) => (x.onclick = () => textDialog(x.dataset.text.split('/').pop(), x.dataset.text)));
  $$('[data-untag]', tab).forEach((x) => (x.onclick = () => saveMeta({ tags: d.tags.filter((t) => t !== x.dataset.untag) })));
  const cat = $('#m-cat', tab);
  cat.onchange = () => saveMeta({ category: cat.value });
  $('#m-tag', tab).onkeydown = (e) => {
    if (e.key === 'Enter' && e.target.value.trim()) {
      const add = e.target.value.split(',');
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
  } catch (e) { toast(e.message, true); }
}

async function baselineAction(act) {
  try {
    if (act === 'cmp-prev') return toggleCompare('baseline');
    if (act === 'snapshot') {
      await assetApi(state.id, '/snapshot', { method: 'POST', body: { variant: state.variant } });
      toast('This version is now the previous one');
      await fetchDetail();
      if (state.compare?.target === 'baseline') await loadCompareTarget();
      return;
    }
    if (act === 'revert') {
      const b = state.detail.baseline;
      if (!(await confirmDialog(`Put ${b.source} back to ${b.hash.slice(0, 7)} (${ago(b.at)})? The version on disk now becomes the previous one, so this can be undone the same way.`, 'Put it back'))) return;
      await assetApi(state.id, '/revert', { method: 'POST', body: {} });
      toast('Reverted. The replaced version is kept as the previous one.');
    }
  } catch (e) { toast(e.message, true, 8000); }
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
  $('.state', bar).textContent = 'Building';
  $('.phases', bar).innerHTML = shown.map((p) => {
    const i = PHASES.indexOf(p);
    const cls = i < cur ? 'done' : i === cur ? 'cur' : '';
    return `<li class="${cls}" title="${esc(p)}">${esc(p)}</li>`;
  }).join('');
  const last = steps[steps.length - 1];
  $('.step', bar).textContent = [last?.text, ago(live.updated)].filter(Boolean).join(' · ');
  $('.step', bar).title = `Started ${new Date(live.started).toLocaleString()}`;
}
// "12 s ago" goes stale on its own.
setInterval(() => { if (state.detail?.live?.state === 'building') renderBuild(); }, 15000);

// ── checks panel: kiln's rules, the reference photo, the batch estimate ──────

function checksFor(label) {
  const c = state.detail?.checks;
  return c ? c.health[label] || [] : [];
}

function renderChecks() {
  const d = state.detail, c = d.checks, v = currentVariant();
  const tab = $('#tab-checks');
  if (!c) { tab.innerHTML = ''; return; }
  const rows = checksFor(v.label);
  const warn = rows.filter((r) => r.level === 'warn').length;
  $('#c-count').textContent = warn ? `(${warn})` : '';
  const blocks = [];
  const isShip = c.shipped === v.label;
  const head = d.kiln ? (isShip ? `${esc(v.label)} · the shipped file` : `${esc(v.label)} · not the shipped file${c.shipped ? ` (${esc(c.shipped)} is)` : ''}`) : esc(v.label);
  blocks.push(`<div class="block"><h3>Health · ${head}</h3>${rows.map(checkRow).join('') || '<p class="dim">Nothing to check.</p>'}
    ${c.config && Object.keys(c.config).length ? `<p class="dim small">From the production log: ${Object.entries(c.config).filter(([k]) => ['type', 'tier', 'target', 'style'].includes(k)).map(([k, x]) => `${esc(k)} <b>${esc(x)}</b>`).join(' · ')}</p>` : ''}</div>`);
  if (c.fidelity.length) blocks.push(fidelityBlock(c.fidelity));
  if (c.batch) blocks.push(batchBlock(c.batch));
  tab.innerHTML = blocks.join('');
  $$('[data-img]', tab).forEach((x) => (x.onclick = () => lightbox(JSON.parse(x.dataset.img))));
  $$('[data-copy]', tab).forEach((x) => (x.onclick = () => copy(x.dataset.copy)));
  $$('[data-ask]', tab).forEach((x) => (x.onclick = () => askClaude(x.dataset.ask)));
  $$('[data-photo-view]', tab).forEach((x) => (x.onclick = () => photoView(JSON.parse(x.dataset.photoView))));
  $$('[data-fv]', tab).forEach((x) => (x.onclick = () => {
    const run = x.closest('.run');
    $$('[data-fv]', run).forEach((y) => y.classList.toggle('on', y === x));
    $$('img[data-which]', run).forEach((img) => (img.hidden = img.dataset.which !== x.dataset.fv));
  }));
}

// `/kiln optimize chair` in a fix: a command, copied on click.
const withCmds = (t) => esc(t).replace(/`([^`]+)`/g, (_, c) => `<code class="cmd" data-copy="${c}" title="Copy, then run it in Claude Code">${c}</code>`);

function checkRow(r) {
  let more = '';
  if (r.entries?.length) more = `<ul class="sub">${r.entries.map((e) => `<li class="${e.level}">${esc(e.label || e.kind)}: ${esc(e.text)}</li>`).join('')}</ul>`;
  if (r.images?.length) more = `<ul class="sub">${r.images.map((i) => `<li>${esc(i.slots.join(', ') || i.name)} · ${i.w ? `${i.w}×${i.h}` : 'size unknown'} ${esc((i.format || '').toUpperCase())}</li>`).join('')}</ul>`;
  const fix = r.level !== 'ok' && (r.fix || r.ask)
    ? `<div class="fix">${r.fix ? `<span><b>How to fix:</b> ${withCmds(r.fix)}</span>` : ''}${r.ask ? `<button class="small" data-ask="${esc(r.ask)}" title="Write it as a note on this model, for /kiln studio to pick up">Ask Claude</button>` : ''}</div>`
    : '';
  return `<div class="check ${r.level}"><span class="lvl" title="${LEVEL_LABEL[r.level]}"></span><div><b>${esc(r.label)}</b><div class="txt">${esc(r.text)}</div>${fix}${more}</div></div>`;
}

// "Ask Claude" on a check: the whole-model note, written for the user to read and save.
function askClaude(text) {
  startGeneral();
  $('#composer-text').value = text;
  $('#composer-text').focus();
}

// The direction fidelity_check.py's camera looked from (its render(): Blender front is -Y,
// azimuth turns toward +X, elevation tilts down), in three.js coordinates (Blender x, z, -y).
function photoDir(run) {
  const base = { front: [0, -1], back: [0, 1], left: [-1, 0], right: [1, 0] }[run.view];
  if (!base) return [0, 1, 0.0001];
  const a = (run.azimuth || 0) * Math.PI / 180, e = (run.elevation || 0) * Math.PI / 180;
  const hx = base[0] * Math.cos(a) - base[1] * Math.sin(a), hy = base[0] * Math.sin(a) + base[1] * Math.cos(a);
  const bx = hx * Math.cos(e), by = hy * Math.cos(e), bz = Math.sin(e);
  return [bx, bz, -by];
}
function photoView(run) {
  viewer.lookFrom(photoDir(run));
  toast(`The photo's view: ${run.view}${run.elevation ? `, ${run.elevation}° up` : ''}${run.azimuth ? `, ${run.azimuth}° round` : ''}. Perspective here, orthographic in the measure.`);
}

function fidelityBlock(runs) {
  const one = (r, i) => {
    const iou = typeof r.iou === 'number' ? r.iou.toFixed(3) : '–';
    const trend = (r.trend || []).filter((t) => typeof t.iou === 'number').map((t) => t.iou.toFixed(3));
    const where = [r.view, r.elevation ? `${r.elevation}° up` : '', r.azimuth ? `${r.azimuth}° round` : ''].filter(Boolean).join(' · ');
    const on = r.measured ? `on ${esc(r.measured)} <span class="mono">${esc((r.model_hash || '').slice(0, 7))}</span> <span class="status addressed">current</span>`
      : r.current === false ? `on an earlier version <span class="mono">${esc((r.model_hash || '').slice(0, 7))}</span> <span class="status open">re-measure</span>` : esc(r.model || '');
    const imgs = [r.overlay && { src: fileUrl(r.overlay), caption: 'Overlay: red is the photo only, cyan the model only', which: 'overlay' },
      r.side_by_side && { src: fileUrl(r.side_by_side), caption: 'The photo and the render, side by side', which: 'side' }].filter(Boolean);
    const joints = (r.joints || []).map((j) => ({ src: fileUrl(j), caption: j.split('/').pop() }));
    const body = `
      <div class="iou"><span class="big">${iou}</span><span class="dim">how closely the outline matches the photo (IoU: 1 is identical) · a guide, not a target${trend.length > 1 ? `<br>rounds ${trend.join(' → ')}` : ''}</span></div>
      <p class="meta">${esc(where)} · ${on}${r.reference_name ? ` · photo ${esc(r.reference_name)}` : ''}</p>
      ${imgs.length ? `<div class="seg small fv">${imgs.map((m, k) => `<button data-fv="${m.which}" class="${k ? '' : 'on'}">${m.which === 'overlay' ? 'Overlay' : 'Side by side'}</button>`).join('')}<button class="ghost" data-photo-view='${esc(JSON.stringify(r))}' title="Turn the model to where the photo's camera stood">Photo's view</button></div>
        <div class="fv-img">${imgs.map((m, k) => `<img src="${esc(m.src)}" alt="${esc(m.caption)}" data-which="${m.which}" ${k ? 'hidden' : ''} data-img='${esc(JSON.stringify(imgs.map(({ src, caption }) => ({ src, caption }))))}'>`).join('')}</div>` : ''}
      ${r.gaps?.length ? `<h4>Gaps, largest first</h4><ol class="gaps">${r.gaps.map((g) => `<li>${esc(g)}</li>`).join('')}</ol>` : '<p class="dim">No gap above tolerance.</p>'}
      ${r.shape?.length ? `<h4>Per height band (1 = top)</h4><table class="vt"><tr><th>Band</th><th style="text-align:right">Width</th><th style="text-align:right">Core</th><th style="text-align:right">IoU</th></tr>${r.shape.map((b) => `<tr><td>${b.band}</td><td class="num">${pctS(b.full_width)}</td><td class="num">${pctS(b.core_width)}</td><td class="num">${b.iou.toFixed(2)}</td></tr>`).join('')}</table>` : ''}
      ${joints.length ? `<h4>Joints: look at each</h4><div class="joints">${joints.map((j) => `<img src="${esc(j.src)}" alt="${esc(j.caption)}" data-img='${esc(JSON.stringify(joints))}'>`).join('')}</div>` : ''}`;
    return `<details class="run" ${i ? '' : 'open'}><summary>${esc(r.dir)} · ${esc(r.view)} · ${iou}${r.at ? ` · ${ago(r.at)}` : ''}</summary>${body}</details>`;
  };
  return `<div class="block fidelity"><h3>Against the reference photo</h3>${runs.map(one).join('')}</div>`;
}
const pctS = (x) => (typeof x === 'number' ? `${x > 0 ? '+' : ''}${Math.round(x * 100)}%` : '–');

function batchBlock(b) {
  const a = b.asset;
  const methods = Object.entries(b.by_method).map(([m, n]) => `${n} ${esc(m)}`).join(', ');
  return `<div class="block"><h3>Batch · ${esc(b.name)}</h3><dl class="kv">
    ${a ? `<dt>This asset</dt><dd>${esc(a.method || '?')} · ${esc(a.status)} · ${esc(fmtTok(a.range))}</dd>` : ''}
    <dt>Whole batch</dt><dd>${b.assets} assets (${methods || '–'}) · ${esc(fmtTok(b.range))}</dd>
    <dt>Left to run</dt><dd>${b.remaining.assets} · ${esc(fmtTok(b.remaining.range))}</dd>
    ${b.unknown.length ? `<dt>No estimate</dt><dd>${b.unknown.map(esc).join(', ')} (unknown method)</dd>` : ''}
  </dl><p class="dim small">${esc(b.note)}. The wizard's formula: scripted ~30K, marketplace ~20K, geometry nodes ~40K, AI ~60–80K per asset; high end ×1.5. From <span class="mono">${esc(b.manifest)}</span>.</p></div>`;
}

// ── history panel ────────────────────────────────────────────────────────────

function renderHistory() {
  const d = state.detail;
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
    ev.push({ type: 'build', at: d.live.started, text: 'Build started' });
    for (const st of d.live.steps || []) if (!filed.has(`${st.phase}|${st.text || ''}`)) ev.push({ type: 'step', at: st.at, st });
    if (d.live.ended) ev.push({ type: 'build', at: d.live.ended, text: 'Build done' });
  }
  ev.sort((x, y) => (x.at < y.at ? 1 : x.at > y.at ? -1 : 0));
  const current = new Map(d.variants.map((v) => [v.label, v.hash]));
  const key = keyOf(d.id);
  const li = (cls, head, body = '', extra = '') => `<li class="${cls}"><div class="t">${ago(head.at)} · ${esc(new Date(head.at).toLocaleString())}</div>${body}${extra}</li>`;
  const items = ev.map((e) => {
    if (e.type === 'version') {
      const p = e.prev;
      const dz = p ? pct(e.size, p.size) : 0, dt = p && p.tris && e.tris != null ? pct(e.tris, p.tris) : 0;
      const delta = p ? ` <span class="${dz > 0 ? 'up' : 'down'}">${dz > 0 ? '+' : ''}${dz}% size</span>${dt ? ` <span class="${dt > 0 ? 'up' : 'down'}">${dt > 0 ? '+' : ''}${dt}% tris</span>` : ''}` : '';
      const img = d.thumbs.includes(e.hash) ? `<img src="${esc(fileUrl(`.kiln-studio/cache/thumbs/${key}/${e.hash}.webp`))}" alt="" data-full="${esc(e.hash)}">` : '';
      const isCur = current.get(e.variant) === e.hash;
      const phase = e.phase ? ` <span class="phase">${esc(e.phase)}</span>${e.step ? ` ${esc(e.step)}` : ''}` : '';
      return li('version', e, `<div class="h">${e.first ? 'First seen' : 'New version'}: ${esc(e.variant)} <span class="mono">${esc(e.hash.slice(0, 7))}</span>${isCur ? ' <span class="status addressed">current</span>' : ''}${phase}</div>`,
        `<div class="d">${fmtB(e.size)}${e.tris != null ? ` · ${fmtN(e.tris)} tris` : ''}${delta}</div>${img}`);
    }
    if (e.type === 'build') return li('build', e, `<div class="h">${esc(e.text)}</div>`);
    if (e.type === 'step') return li('step', e, `<div class="h"><span class="phase">${esc(e.st.phase || 'step')}</span></div>`, e.st.text ? `<div class="d">${esc(e.st.text)}</div>` : '');
    if (e.type === 'log') return li('log', e, `<div class="h">${e.by === 'claude' ? 'Claude' : 'You'}: changelog</div>`, `<div class="d">${esc(e.text)}</div>`);
    if (e.type === 'baseline') return li('baseline', e, `<div class="h">Kept ${esc(e.variant)} <span class="mono">${esc(e.hash.slice(0, 7))}</span> as the previous version</div>`, `<div class="d dim">${esc(e.reason)}</div>`);
    if (e.type === 'revert') return li('revert', e, `<div class="h">Put back ${esc(e.variant)} <span class="mono">${esc(e.hash.slice(0, 7))}</span></div>`);
    if (e.type === 'note') return li('note', e, `<div class="h">Note ${noteNumber(e.n)} by you</div>`, `<div class="d">${esc(e.n.text)}</div>`);
    if (e.type === 'reply') return li('reply', e, `<div class="h">${e.r.by === 'claude' ? 'Claude' : 'You'} on note ${noteNumber(e.n)}${e.r.status ? ` → ${STATUS_LABEL[e.r.status]}` : ''}</div>`, e.r.text ? `<div class="d">${esc(e.r.text)}</div>` : '');
    return '';
  });
  const tab = $('#tab-history');
  tab.innerHTML = items.length
    ? `<ul class="timeline">${items.join('')}</ul>`
    : '<div class="empty-notes"><b>No history yet</b>Studio records each new version of the model it sees, with its size and triangle count, and every note and reply.</div>';
  $$('img[data-full]', tab).forEach((img) => (img.onclick = () => lightbox([{ src: img.src, caption: img.dataset.full }])));
}

// ── compare ──────────────────────────────────────────────────────────────────

function compareTargets() {
  const d = state.detail, v = currentVariant(), out = [];
  if (d.baseline) out.push({ value: 'baseline', label: `Previous (${d.baseline.hash.slice(0, 7)}, ${ago(d.baseline.at)})` });
  for (const x of d.variants) if (x.label !== v.label) out.push({ value: x.label, label: x.label });
  return out;
}

async function toggleCompare(target) {
  if (target === false || (state.compare && target === undefined)) {
    state.compare = null;
    viewer.setCompare(false);
    stage.classList.remove('compare');
    $('#compare-labels').hidden = true;
    syncToolbar();
    return;
  }
  const targets = compareTargets();
  if (!targets.length) {
    toast('Nothing to compare yet. Studio keeps the previous version when you add a note; Details → Keep this version does it now.', true, 6500);
    return;
  }
  state.compare = { target: targets.some((t) => t.value === target) ? target : targets[0].value };
  viewer.setCompare(true);
  stage.classList.add('compare');
  $('#compare-labels').hidden = false;
  syncToolbar();
  await loadCompareTarget();
}

async function loadCompareTarget() {
  const d = state.detail, v = currentVariant();
  const targets = compareTargets();
  if (!targets.length) { toggleCompare(false); return; }
  if (!targets.some((t) => t.value === state.compare.target)) state.compare.target = targets[0].value;
  const t = state.compare.target;
  const src = t === 'baseline' ? { file: d.baseline.file, hash: d.baseline.hash, ext: d.baseline.name.slice(d.baseline.name.lastIndexOf('.')).toLowerCase(), size: d.baseline.size }
    : d.variants.find((x) => x.label === t);
  $('#cmp-left').innerHTML = `<select id="cmp-select" style="pointer-events:auto" aria-label="Compare with">${targets.map((x) => `<option value="${esc(x.value)}"${x.value === t ? ' selected' : ''}>${esc(x.label)}</option>`).join('')}</select>`;
  $('#cmp-select').onchange = (e) => { state.compare.target = e.target.value; loadCompareTarget(); };
  try {
    const left = await viewer.loadCompare(fileUrl(src.file, src.hash), src.ext);
    const right = state.clientStats || {};
    const dz = pct(v.size, src.size), dt = pct(right.tris || 0, left.tris || 0);
    const cls = (x) => (x > 0 ? 'delta-up' : x < 0 ? 'delta-down' : '');
    $('#cmp-left').insertAdjacentHTML('beforeend', ` <span class="dim">${fmtB(src.size)} · ${fmtN(left.tris)} tris</span>`);
    $('#cmp-right').innerHTML = `${esc(v.label)} · ${fmtB(v.size)} <span class="${cls(dz)}">${dz > 0 ? '+' : ''}${dz}%</span> · ${fmtN(right.tris)} tris <span class="${cls(dt)}">${dt > 0 ? '+' : ''}${dt}%</span>`;
  } catch (e) {
    if (!(e instanceof Superseded)) toast(`Could not load ${src.file}: ${e.message}`, true);
  }
}

// ── animation ────────────────────────────────────────────────────────────────

function setupAnimBar() {
  const clips = state.clientStats?.clips || [];
  $('#animbar').hidden = !clips.length;
  stage.classList.toggle('has-anim', !!clips.length);
  if (!clips.length) return;
  $('#a-clip').innerHTML = clips.map((c) => `<option${c.name === viewer.clipName ? ' selected' : ''}>${esc(c.name)}</option>`).join('');
  $('#a-play').textContent = viewer.playing ? '❚❚' : '▶';
}
$('#a-clip').onchange = (e) => viewer.playClip(e.target.value);
$('#a-play').onclick = () => togglePlay();
function togglePlay() {
  viewer.playing = !viewer.playing;
  $('#a-play').textContent = viewer.playing ? '❚❚' : '▶';
}
$('#a-time').oninput = (e) => {
  viewer.playing = false;
  $('#a-play').textContent = '▶';
  viewer.seek(+e.target.value * viewer.clipDuration);
  viewer.onAnimate();
};
$('#a-speed').onchange = (e) => (viewer.speed = +e.target.value);

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
      const img = $(`#list .item[data-id="${CSS.escape(id)}"] img`);
      if (img) img.src = fileUrl(r.thumb);
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
      // The same view as the note's own screenshot, of the version Claude exported.
      const aspect = n.camera.aspect || 4 / 3;
      const w = 1200, h = Math.round(w / aspect);
      const shot = await off().render(fileUrl(v.file, v.hash), v.ext, {
        w, h, camera: n.camera, ring: n.anchor?.point, type: 'image/jpeg', quality: 0.88, bg: viewer.opts.bg,
      });
      await assetApi(detail.id, `/notes/${n.id}/thread/${p.reply}/shot`, { method: 'POST', body: { shot } });
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
  es.onopen = () => { if (lost) { lost = false; toast('Reconnected to Studio'); fetchAssets(); if (state.id) fetchDetail(); } };
  es.onerror = () => { if (!lost) { lost = true; toast('Lost the Studio server. Restart it with /kiln studio; this page reconnects on its own.', true, 12000); } };
  es.onmessage = async (msg) => {
    const ev = JSON.parse(msg.data);
    if (ev.type === 'assets') {
      clearTimeout(assetsTimer);
      assetsTimer = setTimeout(async () => {
        await fetchAssets();
        if (state.id && !state.byId.has(state.id)) { toast('This model is gone from the project', true); state.id = null; }
      }, 150);
    }
    if (ev.type === 'model' && ev.id === state.id) {
      const v = currentVariant();
      const wasNewest = v && v.label === state.detail.variants[0].label;
      const old = new Map(state.detail.variants.map((x) => [x.label, x.hash]));
      await fetchDetail();
      const changed = Object.entries(ev.variants).filter(([l, h]) => old.get(l) !== h).map(([l]) => l);
      const newest = state.detail.variants[0].label;
      if (changed.length && !(changed.length === 1 && changed[0] === 'live')) toast(`Model updated: ${changed.join(', ')}`);
      // Watching the newest stage (the live build, then _final): follow it.
      if (wasNewest && newest !== v.label) await loadVariant(newest, { keepCamera: true });
      else if (v && changed.includes(v.label)) await loadVariant(v.label, { keepCamera: true });
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
          toast(`Building: ${live.phase}${last?.text ? ` · ${last.text}` : ''}`);
        } else if (live?.state === 'done') toast('Build done');
      }
    }
    if (ev.type === 'notes' && ev.id === state.id) {
      clearTimeout(detailTimer);
      detailTimer = setTimeout(async () => {
        const before = new Set(state.detail.notes.flatMap((n) => (n.thread || []).map((r) => r.id)));
        await fetchDetail();
        const fresh = state.detail.notes.flatMap((n) => (n.thread || []).filter((r) => !before.has(r.id) && r.by === 'claude').map((r) => ({ n, r })));
        if (fresh.length) toast(fresh.length === 1 ? `Claude replied on note ${noteNumber(fresh[0].n)}` : `Claude replied on ${fresh.length} notes`);
        queueAfterShots(state.detail);
      }, 120);
    }
  };
}

// ── keys ─────────────────────────────────────────────────────────────────────

document.addEventListener('keydown', (e) => {
  const typing = e.target.closest('input, textarea, select, [contenteditable]');
  if (e.key === 'Escape') {
    if (state.pinning || state.draft) { cancelDraft(); return; }
    if (typing) { e.target.blur(); return; }
    if (state.compare) { toggleCompare(false); return; }
    if (state.hl) highlight(state.hl);
    return;
  }
  if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key;
  if (k === '/') { e.preventDefault(); $('#search').focus(); return; }
  if (k === '?') { $('#keys').showModal(); return; }
  if (k === 'j' || k === 'ArrowDown') { e.preventDefault(); step(1); return; }
  if (k === 'k' || k === 'ArrowUp') { e.preventDefault(); step(-1); return; }
  if (!state.detail) return;
  const views = { 1: 'front', 2: 'back', 3: 'left', 4: 'right', 5: 'top', 6: 'iso' };
  if (views[k]) { viewer.view(views[k]); return; }
  const lower = k.toLowerCase();
  if (lower === 'f') viewer.frame();
  else if (lower === 'w') setOpt('wire', !viewer.opts.wire);
  else if (lower === 'g') setOpt('grid', !viewer.opts.grid);
  else if (lower === 'b') setOpt('bounds', !viewer.opts.bounds);
  else if (lower === 'k' && state.clientStats?.skinned) setOpt('skeleton', !viewer.opts.skeleton);
  else if (lower === 'p' && !$('#t-pins').hidden) $('#t-pins').click();
  else if (lower === 'c') toggleCompare();
  else if (lower === 'n') { e.preventDefault(); state.pinning ? cancelDraft() : startPin(); }
  else if (lower === 'm') { e.preventDefault(); startGeneral(); }
  else if (k === ' ' && state.clientStats?.clips?.length) { e.preventDefault(); togglePlay(); }
  else if (k === '[' || k === ']') {
    const i = SHADES.indexOf(viewer.opts.shade);
    setOpt('shade', SHADES[(i + (k === ']' ? 1 : -1) + SHADES.length) % SHADES.length]);
  }
});

// ── boot ─────────────────────────────────────────────────────────────────────

function fromHash() {
  const id = location.hash.slice(1).split('/').map(decodeURIComponent).join('/');
  if (id && id !== state.id) openAsset(id);
}
window.addEventListener('hashchange', fromHash);

(async () => {
  syncToolbar();
  try {
    await fetchAssets();
  } catch (e) {
    toast(`Could not reach the Studio server: ${e.message}`, true, 15000);
    return;
  }
  liveEvents();
  fromHash();
})();

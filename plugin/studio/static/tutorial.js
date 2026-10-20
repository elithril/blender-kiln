// Kiln Studio's tutorial: a scripted walk through the whole page — the list, the 3D view,
// notes, Claude working on a note, checks, making a new model step by step, approvals, the
// activity pill and settings. Everything is simulated: no Claude runs, no quota is used,
// nothing is written to the project. While it runs, app.js asks this file instead of the
// server (hooks.api), and the server's events wait; the models are static/tutorial/*.glb,
// their stats and checks static/tutorial/fixtures.json (made from those files by Studio).
//
// Each step lights one thing up and waits for the user to do it (the step moves on by
// itself), or shows Next for a step that only explains.

import { t, N_, getLang } from './i18n.js';

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const md = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');   // **bold**, the rest as text
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => new Date().toISOString();

const BARREL = 'tavern/barrel', LANTERN = 'tavern/lantern';
let X = null;        // app.js internals (start's ctx)
let FX = null;       // fixtures: stats, size, hash and checks per model file
let run = null;      // the running tutorial

// ── the fake server ──────────────────────────────────────────────────────────

function variant(key, label = 'final') {
  const f = FX[key];
  return { label, file: `@tuto/${key}.glb`, size: f.size, mtime: Date.now() / 1000, hash: f.hash, ext: '.glb', stats: f.stats };
}
function checksFor(key, label) {
  const c = JSON.parse(JSON.stringify(FX[key].checks));
  if (c.health && label !== 'final') { c.health[label] = c.health.final; delete c.health.final; }
  return c;
}
function counts(notes) {
  const c = { open: 0, addressed: 0, resolved: 0, wontfix: 0 };
  for (const n of notes) c[n.status] = (c[n.status] || 0) + 1;
  return c;
}
function makeAsset(id, key, label = 'final') {
  const v = variant(key, label);
  return {
    id, name: id.split('/').pop(), folder: id, kiln: true, category: 'tavern', category_custom: false, tags: [],
    variants: [v], thumb: null, tris: v.stats.tris, updated: Date.now() / 1000, baseline: null, pending_shots: 0, live: null,
    files: [], log: null, blend: null, notes: [], history: [{ type: 'version', at: now(), variant: label, file: v.file, hash: v.hash, size: v.size, tris: v.stats.tris, first: true }],
    pending: [], thumbs: [], checks: checksFor(key, label), key,
  };
}
const summary = (a) => ({ ...a, variants: a.variants.map(({ stats, ...v }) => v), counts: counts(a.notes), notes: undefined, history: undefined, checks: undefined });

function setModel(a, key, label = 'final') {
  const v = variant(key, label);
  a.variants = [v];
  a.key = key;
  a.tris = v.stats.tris;
  a.checks = checksFor(key, label);
  a.history.push({ type: 'version', at: now(), variant: label, file: v.file, hash: v.hash, size: v.size, tris: v.stats.tris });
  return v;
}

const claudeState = () => ({
  enabled: true, port: 9877, mcp: 'ahujasid', approvals: 'ask', paid: 'ask', blender_behind: true, model: '', budget_usd: 2, parallel: 1,
  machine: { ram_gb: 16, cores: 8, max_parallel: 4 }, account: 'subscription', account_dir: '',
  auth: { ok: true, account: 'subscription', method: 'claude.ai', subscription: 'max', message: '' },
  blender: { state: 'running', port: 9877, ours: true, message: '' }, blenders: [],
  running: run.jobs.find((j) => j.state === 'running')?.id || null, running_all: [],
  jobs: run.jobs.map(jobView), rate: run.rate, usage: { runs: run.jobs.length, cost_usd_equiv: 0.62 * run.jobs.length, by_account: { subscription: { runs: run.jobs.length, cost_usd: 0.62 * run.jobs.length } } },
  api_key_in_env: false,
});
const jobView = ({ run: _, ...j }) => ({ ...j, asset: j.asset || (j.request && run.assets.get(LANTERN) ? LANTERN : null) });

async function fakeApi(path, { method = 'GET', body } = {}) {
  const u = new URL(path, location.origin), p = u.pathname.split('/').slice(1).map(decodeURIComponent);
  const asset = p[1] === 'asset' ? run.assets.get(p[2]) : null;
  if (p[0] !== 'api') return {};
  if (p[1] === 'assets') return { root: t('Tutorial'), name: t('Tutorial'), assets: [...run.assets.values()].map(summary), batches: {}, work: null };
  if (p[1] === 'asset' && asset) {
    const rest = p.slice(3);
    if (!rest.length) return { ...asset, counts: counts(asset.notes), pending: asset.notes.flatMap((n) => (n.thread || []).filter((r) => r.status === 'addressed' && !r.shot).map((r) => ({ note: n.id, reply: r.id, variant: r.version?.variant || 'final' }))) };
    if (rest[0] === 'thumb') { asset.thumb = body.shot || null; return { thumb: asset.thumb }; }
    if (rest[0] === 'notes' && rest.length === 1 && method === 'POST') {
      const v = asset.variants[0];
      const n = { id: `n_tuto${++run.n}`, kind: body.anchor ? 'pin' : 'general', text: body.text, status: 'open', by: 'user', created: now(),
        version: { variant: v.label, file: v.file, hash: v.hash }, anchor: body.anchor || null, camera: body.camera || null, view: body.view || null,
        shot: body.shot || null, detail: body.detail || null, thread: [] };
      asset.notes.push(n);
      asset.baseline = { hash: v.hash, variant: v.label, at: now(), file: v.file, name: v.file.split('/').pop(), size: v.size };
      return n;
    }
    const n = rest[0] === 'notes' && asset.notes.find((x) => x.id === rest[1]);
    if (n && rest[2] === 'thread' && rest[3] && rest[4] === 'shot') {
      const r = n.thread.find((x) => x.id === rest[3]);
      if (r) Object.assign(r, { shot: body.shot || null, detail: body.detail || null });
      setTimeout(() => run && X.handleEvent({ type: 'notes', id: asset.id }), 0);   // as the server tells the page
      return { ok: true };
    }
    if (n && rest[2] === 'thread' && method === 'POST') {
      const r = { id: `r_tuto${++run.n}`, by: 'user', at: now(), text: body.text || '', status: body.status || null };
      n.thread.push(r);
      if (body.status) n.status = body.status;
      return r;
    }
    if (n && method === 'PATCH') { n.text = body.text; return n; }
    if (n && method === 'DELETE') { asset.notes = asset.notes.filter((x) => x !== n); return { ok: true }; }
    return { ok: true };
  }
  if (p[1] === 'claude') {
    if (p.length === 2) return claudeState();
    // The estimates are this project's real ones (read only): the tutorial plays the rest.
    if (p[2] === 'estimate') return fetch(path).then((r) => r.json()).catch(() => null);
    if (p[2] === 'thread') {
      const key = u.searchParams.get('key');
      const k = key === `asset:${LANTERN}` && run.threads.has(run.createKey) ? run.createKey : key;
      const th = run.threads.get(k) || { messages: [] };
      return { key: k, messages: th.messages.slice(), session: null, jobs: run.jobs.filter((j) => j.key === k).map(jobView) };
    }
    if (p[2] === 'jobs' && p.length === 3 && method === 'POST') return submitJob(body);
    if (p[2] === 'jobs' && p[4] === 'answer') { run.answer?.(body.decision); return { ok: true }; }
    if (p[2] === 'jobs' && p[4] === 'stop') return { ok: true };
    return {};
  }
  if (p[1] === 'requests' && method === 'POST') {
    run.request = { id: 'q_tuto1', brief: body.brief, target: body.target, status: 'open', command: `/kiln ${body.brief} (Studio request q_tuto1)` };
    return run.request;
  }
  if (p[1] === 'requests') return { requests: [] };
  if (p[1] === 'config') return { settings: { live_view: true, auto_open: true, exclude: [], target: 'web', claude_worker: true }, target_source: 'default', user_defaults: { target: 'web' }, claude_md: { exists: false, lines: 0, path: '' } };
  if (p[1] === 'status') return { kiln: '3.0', rows: [] };
  return { ok: true };
}

// ── Claude, played ───────────────────────────────────────────────────────────

function submitJob(body) {
  const kind = body.kind;
  const key = kind === 'create' ? `request:${body.request}` : body.key || `asset:${body.asset}`;
  const job = { run, id: `j_tuto${++run.n}`, kind, key, asset: body.asset || null, request: body.request || null, brief: run.request?.brief,
    text: body.text || '', state: 'running', created: now(), started: now() };
  if (kind === 'create') run.createKey = key;
  run.jobs.push(job);
  say(job, { role: 'user', kind, text: kind === 'create' ? run.request.command : body.text, ...(body.context ? { context: body.context } : {}) });
  // A play ends quietly when its tutorial does (left, or started again): see say().
  (kind === 'create' ? playCreate : kind === 'answer' ? playAnswer : playNote)(job).catch(() => {});
  return jobView(job);
}
function thread(key) {
  if (!run.threads.has(key)) run.threads.set(key, { messages: [] });
  return run.threads.get(key);
}
function say(job, entry) {
  if (run !== job.run) throw new Error('tutorial left');   // stops the play before it touches the page
  const e = { at: now(), job: job.id, ...entry };
  thread(job.key).messages.push(e);
  X.onClaude({ type: 'claude', job: jobView(job), entry: e });
}
async function type(job, text) {
  let acc = '';
  for (const w of text.split(' ')) {
    if (run !== job.run) return;
    acc += (acc ? ' ' : '') + w;
    X.onClaude({ type: 'claude-text', job: job.id, key: job.key, text: acc });
    await sleep(45);
  }
  say(job, { role: 'assistant', text });
}
async function tool(job, name, input, result, ms = 700) {
  const id = `toolu_${++run.n}`;
  say(job, { role: 'tool', tool: name, id, input: JSON.stringify(input) });
  await sleep(ms);
  say(job, { role: 'tool-result', id, error: false, text: result });
}
function finish(job, extra = {}) {
  Object.assign(job, { state: 'done', ended: now(), turns: 4, duration_ms: 42000, cost_usd: 0.62, ...extra });
  say(job, { role: 'result', turns: job.turns, duration_ms: job.duration_ms, cost_usd: job.cost_usd });
  X.claudeStatus();
}
const fr = () => getLang() === 'fr';

// Claude works on the note: looks, changes the hoops, exports, answers the note.
async function playNote(job) {
  const a = run.assets.get(BARREL);
  await sleep(500);
  await type(job, fr() ? 'Je lis la note 1 et je regarde le tonneau tel que vous le voyez.' : 'I read note 1 and look at the barrel as you see it.');
  await tool(job, 'mcp__kiln-studio__get_notes', { asset: BARREL }, '1 open note: the iron hoops are too thin');
  await tool(job, 'mcp__blender__get_viewport_screenshot', { max_size: 800 }, 'image');
  await type(job, fr() ? 'Les cercles font 2 cm : je les passe à 5 cm et je les fais ressortir de 15 mm, sans toucher au bois.' : 'The hoops are 2 cm tall: I take them to 5 cm and 15 mm proud, the wood untouched.');
  await tool(job, 'mcp__blender__execute_blender_code', { code: 'thicken_hoops(height=2.6, proud=0.015)' }, 'ok: 4 hoops', 1200);
  await tool(job, 'Bash', { command: 'python3 tools/export.py tavern/barrel --target web' }, 'barrel_final.glb · 117 KB', 900);
  // The new version lands: Studio reloads it, as for a real export.
  const v = setModel(a, 'barrel_after');
  X.handleEvent({ type: 'model', id: BARREL, variants: { final: v.hash } });
  await sleep(900);
  const n = a.notes[a.notes.length - 1];
  if (n) {
    n.status = 'addressed';
    n.thread.push({ id: `r_tuto${++run.n}`, by: 'claude', at: now(), status: 'addressed', version: { variant: 'final', hash: v.hash },
      text: fr() ? 'Cercles 2,6 fois plus hauts et 15 mm plus saillants. Export web refait.' : 'Hoops 2.6 times taller and 15 mm prouder. Web export done again.' });
    X.handleEvent({ type: 'notes', id: BARREL });
  }
  await type(job, fr() ? 'C\'est fait : la note 1 est marquée traitée, avec sa vue après. Regardez, puis dites si c\'est bon.' : 'Done: note 1 is marked addressed, with its after view. Look, then say whether it is right.');
  finish(job);
  run.flags.noteDone = true;
}

// Claude makes a lantern: brief, block-out, details, materials (an approval on the way), final.
async function playCreate(job) {
  const stage = async (key, phase, text) => {
    const a = run.assets.get(LANTERN);
    const v = a ? setModel(a, key, 'live') : null;
    if (!a) {
      run.assets.set(LANTERN, makeAsset(LANTERN, key, 'live'));
      await X.fetchAssets();
      X.go(LANTERN);   // the model being built, in the view (as Studio opens it when nothing is open)
    }
    const asset = run.assets.get(LANTERN);
    asset.live = { asset: LANTERN, state: 'building', phase, started: asset.live?.started || now(), updated: now(),
      steps: [...(asset.live?.steps || []), { at: now(), phase, text }] };
    if (v) X.handleEvent({ type: 'model', id: LANTERN, variants: { live: v.hash } });
    X.handleEvent({ type: 'live', id: LANTERN, live: asset.live });
  };
  await sleep(500);
  await type(job, fr() ? 'Brief : une lanterne de fiacre, fer forgé et verre, environ 40 cm, 2–3K triangles pour le web. Je la modélise par script : pas de génération payante.' : 'Brief: a carriage lantern, wrought iron and glass, about 40 cm, 2–3K triangles for the web. I model it by script: no paid generation.');
  await tool(job, 'mcp__blender__execute_blender_code', { code: 'blockout(body, roof, ring)' }, 'ok', 900);
  await stage('lantern_1_blockout', 'source', fr() ? 'blocage : corps, toit, anneau' : 'block-out: body, roof, ring');
  await sleep(2600);
  await type(job, fr() ? 'Le blocage tient. J\'ajoute les montants, les vitres, le socle et la bougie.' : 'The block-out holds. I add the posts, the panes, the base and the candle.');
  await tool(job, 'mcp__blender__execute_blender_code', { code: 'details(posts, panes, base, candle)' }, 'ok', 900);
  await stage('lantern_2_details', 'cleanup', fr() ? 'détails : montants, vitres, bougie' : 'details: posts, panes, candle');
  await sleep(2600);
  await tool(job, 'mcp__blender__execute_blender_code', { code: 'materials(iron, glass, wax, flame)' }, 'ok', 900);
  await stage('lantern_3_materials', 'texture', fr() ? 'matériaux : fer, verre, cire, flamme' : 'materials: iron, glass, wax, flame');
  await sleep(1200);
  // A tool outside the safe list: the run stops and waits for the user.
  await type(job, fr() ? 'Pour compresser le fichier web, il me faut gltfpack, qui n\'est pas installé.' : 'To compress the web file I need gltfpack, which is not installed.');
  job.state = 'waiting';
  job.waiting = { type: 'tool', id: 'toolu_tuto_ok', tool: 'Bash', input: JSON.stringify({ command: 'brew install gltfpack' }) };
  say(job, { role: 'approval', ...job.waiting });
  X.claudeStatus();
  const decision = await new Promise((res) => { run.answer = res; });
  if (run !== job.run) return;
  run.flags.approved = true;
  job.state = 'done';
  say(job, { role: 'approval-answer', decision, tool: 'Bash', id: 'toolu_tuto_ok' });
  const next = { run, id: `j_tuto${++run.n}`, kind: 'resume', key: job.key, request: job.request, brief: job.brief, state: 'running', created: now(), started: now() };
  run.jobs.push(next);
  X.onClaude({ type: 'claude', job: jobView(next) });
  if (decision === 'allow') await tool(next, 'Bash', { command: 'brew install gltfpack' }, '==> gltfpack 0.22 installed', 1100);
  await tool(next, 'Bash', { command: 'python3 tools/export.py tavern/lantern --target web' }, 'lantern_final.glb · 141 KB', 900);
  const a = run.assets.get(LANTERN);
  const v = setModel(a, 'lantern_4_final', 'final');
  a.live = { ...a.live, state: 'done', phase: 'export', ended: now(), updated: now() };
  X.handleEvent({ type: 'model', id: LANTERN, variants: { final: v.hash } });
  X.handleEvent({ type: 'live', id: LANTERN, live: a.live });
  X.handleEvent({ type: 'assets' });
  await type(next, fr() ? 'La lanterne est prête : 1 932 triangles, 141 Ko, compressée pour le web. Les contrôles sont au vert.' : 'The lantern is ready: 1,932 triangles, 141 KB, compressed for the web. The checks are green.');
  finish(next);
  run.flags.made = true;
}
async function playAnswer(job) { await sleep(300); finish(job); }

// ── the steps ────────────────────────────────────────────────────────────────
// `do`: the user does it (`done`), and the step moves on at once; › does it for them (`skip`).
// `next`: it explains; Next moves on (`ready`: Next waits for something, as Claude finishing).
// `enter` sets the page up for the step, whichever way it is reached (‹, › or done), so it
// must hold if run twice; `undo` takes back what a `do` step did, when ‹ comes back to it.
// `back: false`: ‹ cannot go before this step (what came before cannot be played again).
// What the user can touch: a `do` step's target, or `allow` (selectors) in its place; a `next`
// step, only its `allow`; never `block`. Every other click, and every key but Esc, Tab and
// `keys`, is held back: the page cannot leave the tutorial's path.
// `beside`: on a big target, the card stands beside it, not over it (what to look at is all of it).
// `lost`: the page left the step's state (a dialog closed by hand): back to that step.
// While Claude is working, ‹ and › wait.

const shadeTarget = () => ($('#tb-shade')?.offsetParent ? '#tb-shade [data-shade="clay"]' : '#tb-shade-select');
const lit = () => ($('#tb-shade')?.offsetParent ? '#tb-shade [data-shade="lit"]' : '#tb-shade-select');
const note = () => X.state.detail?.notes?.[X.state.detail.notes.length - 1];
const folded = () => !$('#tb-shade')?.offsetParent;
const shade = (m) => {
  if (!folded()) return $(`#tb-shade [data-shade="${m}"]`)?.click();
  const s = $('#tb-shade-select');
  if (s) { s.value = m; s.dispatchEvent(new Event('change', { bubbles: true })); }
};
const click = (sel) => $(sel)?.click();
const openBarrel = () => { if (X.state.id !== BARREL) X.go(BARREL); };
const compareOn = async (mode) => {
  if (!X.state.compare) await X.setCompare(mode || 'split');   // straight to that layout, no other on the way
  else if (mode && X.state.compare.mode !== mode) click(`#cmp-mode [data-m="${mode}"]`);
};
// A click on the model, as the user's: on one of the barrel's hoops (any of its surface else).
function pinHoop() {
  const r = $('#view').getBoundingClientRect(), x = r.left + r.width / 2;
  let any = null, best = null;
  for (let y = r.top + r.height * 0.15; y < r.bottom - r.height * 0.15; y += 6) {
    const h = X.viewer.pick(x, y);
    if (!h) continue;
    any = any || { x, y };
    if (/hoop|iron|metal|ring|cercle|fer/i.test(`${h.object} ${h.mesh} ${h.material}`)) { best = { x, y }; break; }
  }
  const p = best || any;
  if (!p) return;
  const ev = (type) => new PointerEvent(type, { clientX: p.x, clientY: p.y, bubbles: true, pointerId: 1, isPrimary: true });
  $('#view').dispatchEvent(ev('pointerdown'));
  $('#view').dispatchEvent(ev('pointerup'));
}
function nudgeCamera() {
  const { camera, controls } = X.viewer;
  const o = camera.position.clone().sub(controls.target);
  const a = 0.6, c = Math.cos(a), s = Math.sin(a);
  camera.position.set(controls.target.x + o.x * c - o.z * s, camera.position.y, controls.target.z + o.x * s + o.z * c);
  controls.update();
  run.flags.orbited = true;
}

// Each card: `ch` its chapter, `lead` one sentence, `points` a short list, `act` what to do now
// (shown apart, so it is never lost in the text). **x** is bold.
const C_START = N_('Welcome'), C_MAKE = N_('Make a model'), C_LOOK = N_('Look'), C_NOTE = N_('Notes'),
  C_CLAUDE = N_('Claude'), C_CMP = N_('Compare'), C_CHECK = N_('Checks'), C_MORE = N_('And also');

const STEPS = [
  { ch: C_START, center: true, next: true, title: N_('Welcome to the Kiln Studio tutorial'),
    lead: N_('A guided tour of Studio, about five minutes.'),
    points: [N_('**Nothing is real**: no Claude runs, its answers are played by the tutorial'),
      N_('**Nothing is spent**: no quota, nothing written to your project'),
      N_('**‹ ›** go back and forth, **Leave** at any time')] },
  { ch: C_START, target: '#left .full', next: true, title: N_('Your models'),
    lead: N_('Every 3D file of the folder Studio was opened on, by subfolder.'),
    points: [N_('The counters on top: notes to check, notes open, what Claude works on, what is being built')] },
  { ch: C_START, target: '.lfoot', next: true, title: N_('Add a model, or open another folder'),
    points: [N_('**+** asks Claude for a new model'),
      N_('**The arrow** imports a file you have (GLB, glTF, FBX, OBJ), or drop it anywhere on the page'),
      N_('**Another folder**: run /kiln studio in it, or studio.py open <folder>')] },
  { id: 'create', ch: C_MAKE, target: '#t-create', do: true, title: N_('Make a new model'),
    act: N_('Click **+** to ask Claude for a model.'),
    done: () => $('#create')?.open, skip: () => click('#t-create'), undo: () => $('#create')?.open && $('#create').close() },
  { ch: C_MAKE, target: '#cr-form', do: true, title: N_('Describe it'),
    enter: () => {
      if (!$('#create')?.open) click('#t-create');
      const b = $('#cr-brief'); if (b) b.value = fr() ? 'Une lanterne de fiacre en fer forgé et verre, avec une bougie, environ 40 cm' : 'A carriage lantern in wrought iron and glass, with a candle, about 40 cm';
    },
    lead: N_('Say what it is, its style and its size, in your words.'),
    points: [N_('**Made for** sets the budgets and the file format'), N_('A photo helps'),
      N_('Under it, the time and cost to expect: from your past requests, or kiln\'s bench')],
    act: N_('The description is filled in: a carriage lantern. Click **Make it with Claude**.'),
    allow: '#cr-brief, #cr-target, #cr-launch',
    done: () => !!run.createKey, skip: () => $('#cr-form')?.requestSubmit(),
    lost: () => !$('#create')?.open && !run.createKey && 'create' },
  { ch: C_MAKE, target: '#stage', allow: '#view', do: true, back: false, title: N_('Watch it being built'),
    lead: N_('The lantern appears in the list, and the view shows each stage as it lands. The bar on top follows kiln\'s steps:'),
    points: [N_('**config**, **brief**: the settings, then what to make — size, budget'),
      N_('**source**, **import**: the shape, modelled by script or generated'),
      N_('**cleanup**, **texture**: a clean mesh, then its materials'),
      N_('**optimize**, **export**: lighter, then the final file')],
    act: N_('Watch: the tour goes on by itself.'),
    done: () => run.jobs.some((j) => j.state === 'waiting') },
  { ch: C_MAKE, target: () => '[data-cl="allow"]', do: true, back: false, title: N_('An approval'),
    enter: () => X.openClaudeView(`asset:${LANTERN}`),
    lead: N_('Claude wants to run a command outside the safe list: it stops and asks.'),
    points: [N_('The **✦** tab, the pill and the page title say so, wherever you are')],
    act: N_('Click **Allow once**.'),
    done: () => run.flags.approved, skip: () => click('[data-cl="allow"]') },
  { ch: C_MAKE, target: '#view', next: true, back: false, ready: () => run.flags.made, allow: '#view', title: N_('Made'),
    lead: N_('The lantern is exported: a model like the others, with its checks and its conversation.'),
    points: [N_('Next, the barrel: everything you can do with a model')] },
  { ch: C_LOOK, target: () => `#list .item[data-id="${BARREL}"]`, do: true, back: false, title: N_('Open a model'),
    act: N_('Click the **barrel** in the list.'),
    done: () => X.state.id === BARREL && X.viewer.a.model, skip: openBarrel },
  { ch: C_LOOK, target: '#view', do: true, title: N_('Turn around it'),
    enter: openBarrel,
    points: [N_('**Drag** to turn around'), N_('**Scroll** to zoom'), N_('**Right-drag** to move')],
    act: N_('Turn around the barrel.'),
    done: () => run.flags.orbited, skip: nudgeCamera, undo: () => { run.flags.orbited = false; } },
  { ch: C_LOOK, target: '#views', do: true, title: N_('The set views'),
    lead: N_('Front, back, each side, top or three-quarters: keys **1** to **6**.'),
    act: N_('Click one.'), keys: /^[1-6]$/,
    enter: () => { run.flags.view = false; }, done: () => run.flags.view,
    skip: () => { click('#views [data-view="front"]'); run.flags.view = true; } },
  { ch: C_LOOK, target: shadeTarget, do: true, title: N_('Clay: the shape alone'),
    lead: N_('A grey render without colours or textures: you judge the shape alone — dents, bumps, seams.'),
    act: () => (folded() ? t('Pick **Clay** in this list of renders.') : t('Click **Clay**.')),
    done: () => X.viewer.opts.shade === 'clay', skip: () => shade('clay'), undo: () => shade('lit') },
  { ch: C_LOOK, target: lit, do: true, title: N_('Back to Lit'),
    enter: () => { if (X.viewer.opts.shade === 'lit') shade('clay'); },
    lead: N_('Lit shows the materials under a studio light, as in a game. The other renders:'),
    points: [N_('**Unlit**: the colours only'), N_('**Normals**: which way the faces point'), N_('**UV**: how textures are laid'), N_('**Faces**: the polygons')],
    act: () => (folded() ? t('Pick **Lit** in the list.') : t('Click **Lit**.')),
    done: () => X.viewer.opts.shade === 'lit', skip: () => shade('lit'), undo: () => shade('clay') },
  { ch: C_LOOK, target: '#outputs', next: true, title: N_('Outputs'),
    enter: () => { if (X.viewer.opts.shade !== 'lit') shade('lit'); },
    lead: N_('One model, a file per use.'),
    points: [N_('**Web** is there: the file for a website'),
      N_('**+ Game**, **+ AR**, **+ 3D print**: Claude prepares the one missing'),
      N_('**✓** up to date; **↻** made before the model changed: to redo'),
      N_('**Download**: pick the outputs, with a sheet to send them')] },
  { ch: C_LOOK, target: '[data-decline]', next: true, title: N_('Make variations'),
    lead: N_('Another size, other colours, a version for printing: new models from a copy of this one.'),
    points: [N_('A card per variation: **what changes**, its name, what it is for'),
      N_('Each is a new model under the original, which is never changed'),
      N_('Claude makes them, as many at once as Settings allow')] },
  { id: 'pin', ch: C_NOTE, target: '#t-pin', do: true, title: N_('Pin a note'),
    enter: () => { if (X.viewer.opts.shade !== 'lit') shade('lit'); X.ensureRight('notes'); },
    lead: N_('Something to change? Pin a note to the place.'),
    act: N_('Click **Pin a note**.'),
    done: () => X.state.pinning || !$('#composer').hidden, skip: () => click('#t-pin'),
    undo: () => { if (X.state.pinning || !$('#composer').hidden) X.cancelDraft(); } },
  { ch: C_NOTE, target: '#view', do: true, title: N_('Click where it is'),
    enter: () => { if (!X.state.pinning && $('#composer').hidden) click('#t-pin'); },
    act: N_('Click one of the barrel\'s **iron hoops**.'),
    done: () => !$('#composer').hidden, skip: pinHoop,
    undo: () => { if (!$('#composer').hidden) { X.cancelDraft(); click('#t-pin'); } },
    lost: () => !X.state.pinning && $('#composer').hidden && 'pin' },
  { ch: C_NOTE, target: '#composer', next: true, title: N_('Say what should change'),
    enter: () => { const ta = $('#composer-text'); if (ta && !ta.value) ta.value = fr() ? 'Les cercles en fer sont trop fins : les épaissir.' : 'The iron hoops are too thin: make them thicker.'; },
    lead: N_('We wrote it for you.'), allow: '#composer-text',
    points: [N_('Studio keeps the note with a picture of your view and the spot you pinned')],
    lost: () => $('#composer').hidden && 'pin' },
  { ch: C_NOTE, target: '#composer-save', do: true, title: N_('Save the note'),
    act: N_('Click **Save note**.'), allow: '#composer-text, #composer-save',
    enter: () => { run.notes = X.state.detail?.notes.length || 0; },
    done: () => (X.state.detail?.notes.length || 0) > run.notes, skip: () => click('#composer-save'),
    lost: () => $('#composer').hidden && (X.state.detail?.notes.length || 0) <= run.notes && 'pin' },
  { ch: C_NOTE, target: '#note-list .note', next: true, back: false, title: N_('Your note'),
    enter: () => X.ensureRight('notes'),
    lead: N_('It is in the **Notes** tab, numbered like its pin on the model.'),
    points: [N_('Pin as many as you like before asking Claude: they go together'),
      N_('A note about the whole model: **Whole model**')] },
  { ch: C_CLAUDE, target: '#work', allow: '#work [data-ask-notes]', do: true, title: N_('Hand it to Claude'),
    enter: () => X.ensureRight('notes'),
    lead: N_('One click sends every open note to Claude: nothing to type, and you stay here.'),
    points: [N_('Under the count, the time and cost to expect, once this project has a few like it'),
      N_('Prefer the terminal? In Claude Code, the command below does the same')],
    act: N_('Click **Work on it with Claude**.'),
    done: () => run.jobs.some((j) => j.asset === BARREL), skip: () => click('#work [data-ask-notes]') },
  { ch: C_CLAUDE, target: '#work', do: true, back: false, title: N_('Claude works'),
    enter: () => X.ensureRight('notes'),
    lead: N_('Claude reads the note, changes the model in its own Blender — never yours — and exports.'),
    points: [N_('Its last action shows here'), N_('The note turns **addressed** when it is done')],
    act: N_('Watch: the tour goes on when Claude is done.'),
    done: () => run.flags.noteDone },
  { ch: C_CLAUDE, target: '#note-list .note', next: true, back: false, title: N_('The note, addressed'),
    enter: () => X.ensureRight('notes'),
    lead: N_('Claude marked it addressed.'),
    points: [N_('Studio rendered the same view of the new version beside the old one: before and after')] },
  { ch: C_CLAUDE, target: '#tb-claude', do: true, title: N_('Something particular?'),
    enter: () => X.ensureRight('notes'),
    lead: N_('A question, a change no note covers: the **✦** tab talks to Claude about this model.'),
    act: N_('Open it.'),
    done: () => !$('#tab-claude').hidden, skip: () => click('#tb-claude'), undo: () => X.ensureRight('notes') },
  { ch: C_CLAUDE, target: '#tab-claude', next: true, allow: '#cl-thread', block: '[data-cl]', title: N_('The conversation'),
    enter: () => X.ensureRight('claude'),
    points: [N_('One conversation per model, kept between sessions'),
      N_('What Claude did on the note is here, line by line: open one to see what went in and out'),
      N_('Write in the box below; **view capture** lets Claude look at your view first'),
      N_('Another conversation covers the whole project')] },
  { id: 'compare', ch: C_CMP, target: '#t-compare', do: true, title: N_('Compare'),
    enter: () => X.ensureRight('notes'),
    lead: N_('Both versions in the 3D view.'),
    act: N_('Click **Compare**.'),
    done: () => !!X.state.compare, skip: () => compareOn(), undo: () => X.state.compare && X.setCompare(null) },
  { ch: C_CMP, target: '#stage', allow: '#split, #view', beside: true, do: true, title: N_('Drag the divider'),
    enter: async () => { await compareOn('split'); run.split = X.viewer.split ?? 0.5; run.flags.dragged = false; },
    points: [N_('**Left**: the version you noted'), N_('**Right**: the current one'), N_('You can still turn around it')],
    act: N_('Drag the divider across the barrel, and let go.'),
    done: () => run.flags.dragged,
    skip: () => { for (let k = 0; k < 3; k++) $('#split')?.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true })); run.flags.dragged = true; },
    undo: () => { run.split = X.viewer.split ?? 0.5; run.flags.dragged = false; },
    lost: () => !X.state.compare && 'compare' },
  { ch: C_CMP, target: '#cmp-mode', do: true, title: N_('Side by side'),
    enter: () => compareOn(),
    lead: N_('Or both whole, turning together.'),
    act: N_('Click **Side by side**.'),
    done: () => X.state.compare?.mode === 'side', skip: () => compareOn('side'), undo: () => compareOn('split'),
    lost: () => !X.state.compare && 'compare' },
  { ch: C_CMP, target: '#cmpbar', do: true, title: N_('What changed'),
    enter: () => compareOn(),
    lead: N_('The bar gives the difference in triangles, file size and height.'),
    points: [N_('Prefer the old one? Details → **Compare and choose** keeps one or the other')],
    act: N_('Close it with **×** or **Esc**.'), allow: '#cmp-close',
    done: () => !X.state.compare, skip: () => X.setCompare(null), undo: () => compareOn('side') },
  { ch: C_CMP, target: () => '#note-list [data-act="resolve"]', do: true, title: N_('Say it is right'),
    enter: async () => { if (X.state.compare) await X.setCompare(null); X.ensureRight('notes'); },
    points: [N_('**Looks right** closes the note'), N_('**Not yet** sends it back to Claude with a word')],
    act: N_('Mark it **Looks right**.'),
    done: () => note()?.status === 'resolved', skip: () => click('#note-list [data-act="resolve"]') },
  { ch: C_CHECK, target: '#tb-checks', do: true, back: false, title: N_('The checks'),
    enter: () => X.ensureRight('notes'),
    lead: N_('Checks reads the file against kiln\'s rules: triangles, size, ground, compression, licences.'),
    act: N_('Open the tab.'),
    done: () => !$('#tab-checks').hidden, skip: () => click('#tb-checks'), undo: () => X.ensureRight('notes') },
  { ch: C_CHECK, target: '#tab-checks', next: true, title: N_('What it says'),
    enter: () => { X.ensureRight('checks'); if (!$('#cl-act').hidden) click('#cl-pill-btn'); },
    points: [N_('**Green**: fine'), N_('**Amber**: worth a look, with what to do'), N_('A check Claude can fix comes with the words to ask for it')] },
  { ch: C_MORE, target: '#cl-pill-btn', do: true, title: N_('Claude, at a glance'),
    lead: N_('The pill says what Claude does, what waits for you and how much of your quota is used.'),
    act: N_('Open it.'),
    done: () => !$('#cl-act').hidden, skip: () => click('#cl-pill-btn'),
    undo: () => { if (!$('#cl-act').hidden) click('#cl-pill-btn'); } },
  { ch: C_MORE, target: '#cl-act', next: true, title: N_('What Claude does, what you use'),
    enter: () => { if ($('#cl-act').hidden) click('#cl-pill-btn'); },
    points: [N_('**On top**: what Claude is doing or waiting for you on, one click away'),
      N_('**Quota**: your 5-hour session and your week, and when each resets'),
      N_('**Requests**, and what they would cost on the API — included in your subscription'),
      N_('**Notify me**: a notification when Claude waits, even in another window')] },
  { ch: C_MORE, target: '#t-settings', next: true, title: N_('Settings'),
    enter: () => { if (!$('#cl-act').hidden) click('#cl-pill-btn'); },
    points: [N_('**Display**: how this browser shows Studio'), N_('**Project**: what models are made for, its CLAUDE.md'),
      N_('**Claude**: approvals, paid generation, how many at once'), N_('**Account**: which one pays'),
      N_('**Setup**: what kiln uses, and installs what is missing')] },
  { ch: C_MORE, center: true, next: true, last: true, title: N_('That is Studio'),
    points: [N_('**⌘K** finds every command, **?** lists the keys'),
      N_('From the terminal, Claude can drive this page too: /kiln studio, and present mode for a second screen'),
      N_('**Finish** takes you back to your project: the tutorial wrote nothing in it')] },
];

// ── the spotlight ────────────────────────────────────────────────────────────
// The overlay is a popover: it sits in the top layer, above the page's own dialogs (it is
// raised again whenever one opens).

function ui() {
  if ($('#tuto')) return;
  document.body.insertAdjacentHTML('beforeend', `
    <div id="tuto" class="tuto" popover="manual"><div class="tuto-dim" id="tuto-dim"></div><div class="tuto-ring" id="tuto-ring"></div>
      <div class="tuto-card" id="tuto-card" role="dialog" aria-live="polite" aria-labelledby="tuto-title">
        <div class="tuto-head"><span class="tuto-step" id="tuto-step"></span><span class="tuto-count" id="tuto-count"></span><span class="tuto-sim" title="${esc(t('A simulation: no Claude runs, no quota is used, nothing is written to your project.'))}">${esc(t('Simulation'))}</span></div>
        <div class="tuto-bar" aria-hidden="true"><i id="tuto-bar"></i></div>
        <h4 id="tuto-title"></h4><div class="tuto-body" id="tuto-body"></div>
        <div class="tuto-act" id="tuto-act"><span class="tuto-act-ico" aria-hidden="true">→</span><span id="tuto-act-text"></span></div>
        <div class="tuto-acts"><button class="btn sm ghost" id="tuto-quit">${esc(t('Leave'))}</button><span class="tuto-hint" id="tuto-hint"></span><span class="sp"></span>
          <button class="btn sm icon" id="tuto-prev" aria-label="${esc(t('Previous step'))}" title="${esc(t('Previous step'))}">‹</button>
          <button class="btn sm icon" id="tuto-skip" aria-label="${esc(t('Do it for me'))}" title="${esc(t('Do it for me'))}">›</button>
          <button class="btn sm accent" id="tuto-next"></button></div>
      </div></div>`);
  $('#tuto-quit').onclick = () => stop();
  $('#tuto-next').onclick = () => go(run.i + 1);
  $('#tuto-skip').onclick = () => skip();
  $('#tuto-prev').onclick = () => go(run.i - 1);
  $('#tuto').showPopover?.();
}
function target(st) {
  const sel = typeof st.target === 'function' ? st.target() : st.target;
  const el = sel && $(sel);
  return el && el.getClientRects().length ? el : null;
}
function raise() {
  // A modal dialog makes everything outside it inert, the card's buttons too (Chrome and
  // Safari both): while one is open the overlay lives inside it, shown again on top. It goes
  // back the moment the dialog closes (a closed dialog hides what it holds), before a frame.
  const dlg = document.querySelector('dialog[open]');
  if (dlg === run.dialog) return;
  run.dialog = dlg;
  run.dialogWatch?.disconnect();
  move(dlg || document.body);
  if (dlg) {
    run.dialogWatch = new MutationObserver(() => { if (!dlg.open && run?.dialog === dlg) { run.dialog = null; run.dialogWatch.disconnect(); move(document.body); } });
    run.dialogWatch.observe(dlg, { attributes: true, attributeFilter: ['open'] });
  }
}
function move(parent) {
  const o = $('#tuto');
  if (!o) return;
  if (o.parentElement !== parent) {
    if (o.matches?.(':popover-open')) o.hidePopover();
    parent.appendChild(o);
  } else if (o.matches?.(':popover-open')) o.hidePopover();
  o.showPopover?.();   // last in the top layer: above the dialog
}
function place() {
  if (!run || run.swapping) return;   // the card is fading to the next step: it stays put
  raise();
  const st = STEPS[run.i], el = !st.center && target(st);
  const ring = $('#tuto-ring'), card = $('#tuto-card'), dim = $('#tuto-dim');
  const vw = innerWidth, vh = innerHeight, cw = card.offsetWidth, ch = card.offsetHeight;
  if (!el) {
    // A target gone for a moment (a button that left on its click, a panel redrawn): nothing
    // moves until it is back. Only a centred step centres the card.
    if (!st.center) return;
    ring.style.opacity = '0';
    dim.style.clipPath = 'none';
    dim.style.opacity = '1';
    Object.assign(card.style, { left: `${Math.round((vw - cw) / 2)}px`, top: `${Math.round((vh - ch) / 2)}px` });
    return;
  }
  const r = el.getBoundingClientRect(), pad = 6;
  const hx = r.left - pad, hy = r.top - pad, hw = r.width + 2 * pad, hh = r.height + 2 * pad;
  Object.assign(ring.style, { opacity: '1', left: `${hx}px`, top: `${hy}px`, width: `${hw}px`, height: `${hh}px` });
  // The page dimmed but for a hole on what to do; inside a dialog, its own backdrop does it.
  dim.style.opacity = el.closest('dialog') ? '0' : '1';
  dim.style.clipPath = `path(evenodd, "M0 0H${vw}V${vh}H0Z M${hx} ${hy}h${hw}v${hh}h${-hw}Z")`;
  const gap = 14;
  let x, y;
  const big = r.width > vw * 0.4 && r.height > vh * 0.4;
  if (big && st.beside) { x = r.right + gap; y = r.top + 80; }   // out of the way of what to look at (over the panel beside)
  else if (big) { x = r.left + 24; y = r.bottom - ch - 84; }   // a big area: inside, low (its top shows the build)
  else if (r.right + gap + cw < vw - 12) { x = r.right + gap; y = r.top; }
  else if (r.left - gap - cw > 12) { x = r.left - gap - cw; y = r.top; }
  else if (r.bottom + gap + ch < vh - 12) { x = r.left + r.width / 2 - cw / 2; y = r.bottom + gap; }
  else { x = r.left + r.width / 2 - cw / 2; y = r.top - gap - ch; }
  x = Math.max(12, Math.min(vw - cw - 12, x)); y = Math.max(12, Math.min(vh - ch - 12, y));
  Object.assign(card.style, { left: `${Math.round(x)}px`, top: `${Math.round(y)}px` });
}
// Claude is working (a run going, not one waiting for an answer): nothing to go back or skip to.
const working = () => run.jobs.some((j) => j.state === 'running');
const stepAt = (id) => STEPS.findIndex((s) => s.id === id);
// Only what the step asks for: the user's own clicks and keys elsewhere stop here (the
// tutorial's own, untrusted, go through).
function guard(e) {
  if (!run || !e.isTrusted || e.target.closest?.('#tuto-card')) return;
  const st = STEPS[run.i];
  if (!st) return;
  if (e.type === 'keydown') {
    if (e.key === 'Escape' || e.key === 'Tab' || st.keys?.test(e.key)) return;
    const typing = e.target.closest?.('textarea, input, select');
    // Typing where the step allows it; ⌘↵ too, but not on a step that only explains (it
    // would save the note before the step that asks for it).
    if (typing && inside(st, typing) && !(e.key === 'Enter' && (e.metaKey || e.ctrlKey) && !st.do)) return;
  } else if (inside(st, e.target)) return;
  e.preventDefault();
  e.stopImmediatePropagation();
}
function inside(st, el) {
  if (st.block && el.closest?.(st.block)) return false;
  const sel = st.allow || (st.do && (typeof st.target === 'function' ? st.target() : st.target));
  if (!sel) return false;
  return [...document.querySelectorAll(sel)].some((a) => a.contains(el));
}
// (A release is never held: a drag begun where it may goes on wherever it ends.)
const GUARDED = ['pointerdown', 'mousedown', 'click', 'dblclick', 'contextmenu', 'keydown', 'dragover', 'drop'];
function buttons() {
  const st = STEPS[run.i], busy = working() || run.swapping;
  $('#tuto-prev').disabled = busy || run.i === 0 || st.back === false;
  $('#tuto-skip').hidden = !st.do;
  $('#tuto-skip').disabled = busy || !st.skip;
  $('#tuto-next').hidden = !st.next;
  const ready = !st.ready || !!st.ready();
  $('#tuto-next').disabled = busy || !ready;
  $('#tuto-hint').textContent = run.ok ? '✓' : !ready || (st.do && working()) ? t('Wait for Claude…') : !run.armed ? t('Already done') : '';
}
function check() {
  if (!run || run.swapping) return;
  const st = STEPS[run.i], i = run.i;
  place();
  if (st.do) {
    const done = !!st.done?.();
    // A step reached already done (coming back to it) waits for › rather than bouncing on.
    if (!done) run.armed = true;
    if (done && run.armed && !run.ok) {
      run.ok = true;
      $('#tuto-card').classList.add('ok');
      // A target that left on the click (a note closed): straight on, no light on nothing.
      setTimeout(() => { if (run && run.i === i && run.ok) go(i + 1); }, target(st) ? 150 : 0);
    }
  }
  const lost = st.lost?.();
  if (lost && !run.ok) { go(stepAt(lost)); return; }
  buttons();
}
function skip() {
  const st = STEPS[run.i];
  if (!st.do || working() || run.swapping) return;
  if (st.done?.()) return go(run.i + 1);   // already done: › just moves on
  // After this click has gone through the page: a menu opened by the action would be closed by it.
  setTimeout(async () => { await st.skip?.(); check(); }, 0);
}
async function go(i) {
  if (!run || run.swapping || i < 0) return;
  if (i >= STEPS.length) return stop(true);
  const from = run.i;
  // The card fades out, the page is set for the step, and the card fades back in at its
  // place: it never slides while its words and size change, nor shows a half-set page.
  run.swapping = true;
  const card = $('#tuto-card'), ring = $('#tuto-ring');
  ring.classList.add('jump');
  if (from >= 0) { card.classList.add('out'); ring.style.opacity = '0'; await sleep(120); if (!run) return; }
  const st = STEPS[i];
  if (i < from) for (let k = from - 1; k >= i; k--) await STEPS[k].undo?.();   // ‹: take back what was done
  if (!run) return;
  run.i = i;
  run.ok = false;
  await st.enter?.();
  if (!run) return;
  await sleep(60);   // let the page settle (a dialog opening, a tab drawn) before placing the card
  if (!run) return;
  run.armed = !(st.do && st.done?.());
  const say = (s) => (typeof s === 'function' ? s() : t(s));
  $('#tuto-step').textContent = t(st.ch);
  $('#tuto-count').textContent = `${i + 1} / ${STEPS.length}`;
  $('#tuto-bar').style.width = `${((i + 1) / STEPS.length) * 100}%`;
  $('#tuto-title').textContent = t(st.title);
  $('#tuto-body').innerHTML = (st.lead ? `<p>${md(say(st.lead))}</p>` : '')
    + (st.points?.length ? `<ul>${st.points.map((p) => `<li>${md(say(p))}</li>`).join('')}</ul>` : '');
  $('#tuto-body').hidden = !st.lead && !st.points?.length;
  $('#tuto-act').hidden = !st.act;
  $('#tuto-act-text').innerHTML = st.act ? md(say(st.act)) : '';
  $('#tuto-next').textContent = st.last ? t('Finish') : t('Next');
  card.classList.remove('ok');
  run.swapping = false;
  buttons();
  place();
  requestAnimationFrame(() => { card.classList.remove('out'); requestAnimationFrame(() => ring.classList.remove('jump')); });
  check();
}

export async function start(ctx) {
  if (run) return;
  X = ctx;
  FX = FX || await (await fetch('/static/tutorial/fixtures.json')).json();
  run = { i: -1, n: 0, jobs: [], threads: new Map(), flags: {}, assets: new Map(),
    rate: { unifiedWindows: { five_hour: { utilization: 0.18, resetsAt: Math.round(Date.now() / 1000) + 9000 }, seven_day: { utilization: 0.34, resetsAt: Math.round(Date.now() / 1000) + 4 * 86400 } }, at: now() },
    back: { hash: [BARREL, LANTERN].some((id) => location.hash.includes(id)) ? '' : location.hash, id: X.state.id } };
  run.assets.set(BARREL, makeAsset(BARREL, 'barrel_before'));
  document.querySelector('dialog[open]')?.close();
  X.hooks.api = fakeApi;
  document.body.classList.add('tutorial');
  ui();
  addEventListener('resize', place);
  X.claude.view = null;
  if (X.state.compare) await X.setCompare(null);
  X.state.id = null; X.state.detail = null;
  X.viewer.a.clear(); X.viewer.seqA = (X.viewer.seqA || 0) + 1;   // the project's model leaves the view
  history.replaceState(null, '', location.pathname);
  await X.fetchAssets();
  await X.claudeStatus();
  X.renderEmpty();
  // What the user does, as it happens: a click is checked at once, not at the next tick.
  run.onClick = (e) => { if (e.target.closest?.('#views [data-view]')) run.flags.view = true; setTimeout(check, 0); };
  run.onEnd = () => { if (run.cam0 && X.viewer.camera.position.distanceTo(run.cam0) > 0.05) run.flags.orbited = true; };
  run.onStart = () => { run.cam0 = X.viewer.camera.position.clone(); };
  for (const ty of GUARDED) addEventListener(ty, guard, true);
  document.addEventListener('click', run.onClick, true);
  document.addEventListener('input', run.onClick, true);
  document.addEventListener('change', run.onClick, true);
  run.onSplitUp = () => { if (Math.abs((X.viewer.split ?? 0.5) - (run.split ?? 0.5)) > 0.05) { run.flags.dragged = true; setTimeout(check, 0); } };
  $('#split').addEventListener('pointerup', run.onSplitUp);
  X.viewer.controls.addEventListener('start', run.onStart);
  X.viewer.controls.addEventListener('end', run.onEnd);
  run.timer = setInterval(check, 120);
  go(0);
}

export async function stop(finished = false) {
  if (!run) return;
  clearInterval(run.timer);
  for (const ty of GUARDED) removeEventListener(ty, guard, true);
  document.removeEventListener('click', run.onClick, true);
  document.removeEventListener('input', run.onClick, true);
  document.removeEventListener('change', run.onClick, true);
  $('#split').removeEventListener('pointerup', run.onSplitUp);
  X.viewer.controls.removeEventListener('start', run.onStart);
  X.viewer.controls.removeEventListener('end', run.onEnd);
  run.answer?.('deny');
  run.dialogWatch?.disconnect();
  const back = run.back;
  run = null;
  removeEventListener('resize', place);
  $('#tuto')?.hidePopover?.(); $('#tuto')?.remove();
  document.body.classList.remove('tutorial');
  document.querySelector('dialog[open]')?.close();
  X.hooks.api = null;
  X.claude.view = null; X.claude.thread = null; X.claude.partial = null;
  if (X.state.compare) await X.setCompare(null);
  X.state.id = null; X.state.detail = null;
  X.viewer.a.clear(); X.viewer.seqA = (X.viewer.seqA || 0) + 1;
  history.replaceState(null, '', location.pathname + (back.hash || ''));
  await X.fetchAssets();
  await X.claudeStatus();
  if (back.id && X.state.byId.has(back.id)) X.openAsset(back.id); else X.renderEmpty();
  if (finished) X.toast(esc(t('Back to your project. The tutorial wrote nothing in it.')), 'ok', 6000);
}

// For checking the tutorial in a browser: would a user's click on `el` reach it at this step?
// 'ok', or what stops it: 'dim' (outside the lit area), 'covered', 'guard' (not this step's).
export function probe(el) {
  if (!run || !el?.getClientRects().length) return 'hidden';
  const r = el.getBoundingClientRect(), top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  if (top?.closest('#tuto')) return top.closest('#tuto-card') ? 'covered' : 'dim';
  if (!top || !(el.contains(top) || top.contains(el))) return 'covered';
  return inside(STEPS[run.i], top) ? 'ok' : 'guard';
}

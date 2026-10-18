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
const jobView = (j) => ({ ...j, asset: j.asset || (j.request && run.assets.get(LANTERN) ? LANTERN : null) });

async function fakeApi(path, { method = 'GET', body } = {}) {
  const u = new URL(path, location.origin), p = u.pathname.split('/').slice(1).map(decodeURIComponent);
  const asset = p[1] === 'asset' ? run.assets.get(p[2]) : null;
  if (p[0] !== 'api') return {};
  if (p[1] === 'assets') return { root: t('Tutorial'), name: t('Tutorial'), assets: [...run.assets.values()].map(summary), batches: {}, work: null };
  if (p[1] === 'asset' && asset) {
    const rest = p.slice(3);
    if (!rest.length) return { ...asset, counts: counts(asset.notes), pending: asset.notes.flatMap((n) => (n.thread || []).filter((r) => r.status === 'addressed' && !r.shot).map((r) => ({ note: n.id, reply: r.id }))) };
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
  const job = { id: `j_tuto${++run.n}`, kind, key, asset: body.asset || null, request: body.request || null, brief: run.request?.brief,
    text: body.text || '', state: 'running', created: now(), started: now() };
  if (kind === 'create') run.createKey = key;
  run.jobs.push(job);
  say(job, { role: 'user', kind, text: kind === 'create' ? run.request.command : body.text, ...(body.context ? { context: body.context } : {}) });
  (kind === 'create' ? playCreate : kind === 'answer' ? playAnswer : playNote)(job);
  return jobView(job);
}
function thread(key) {
  if (!run.threads.has(key)) run.threads.set(key, { messages: [] });
  return run.threads.get(key);
}
function say(job, entry) {
  const e = { at: now(), job: job.id, ...entry };
  thread(job.key).messages.push(e);
  X.onClaude({ type: 'claude', job: jobView(job), entry: e });
}
async function type(job, text) {
  let acc = '';
  for (const w of text.split(' ')) {
    if (!run) return;
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
  run.flags.approved = true;
  job.state = 'done';
  say(job, { role: 'approval-answer', decision, tool: 'Bash', id: 'toolu_tuto_ok' });
  const next = { id: `j_tuto${++run.n}`, kind: 'resume', key: job.key, request: job.request, brief: job.brief, state: 'running', created: now(), started: now() };
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

const shadeTarget = () => ($('#tb-shade')?.offsetParent ? '#tb-shade [data-shade="clay"]' : '#tb-shade-select');
const lit = () => ($('#tb-shade')?.offsetParent ? '#tb-shade [data-shade="lit"]' : '#tb-shade-select');
const note = () => X.state.detail?.notes?.[X.state.detail.notes.length - 1];

const STEPS = [
  { center: true, title: N_('Welcome to the Kiln Studio tutorial'), next: true,
    text: N_('This is a demonstration: no Claude runs, no quota is used, nothing is written to your project. Every answer from Claude is played by the tutorial, to show how it goes. About five minutes; Leave at any time.') },
  { target: '#left .full', title: N_('Your models'), next: true,
    text: N_('Studio shows every 3D file of the project, by folder. The counters on top: notes to check, notes open, what Claude is working on, what is being built.') },
  { target: () => `#list .item[data-id="${BARREL}"]`, title: N_('Open a model'), text: N_('Click the barrel.'),
    done: () => X.state.id === BARREL && X.viewer.a.model },
  { target: '#view', title: N_('Turn around it'), text: N_('Drag on the model to turn around it, scroll to zoom, right-drag to move.'),
    enter: () => { run.cam = X.viewer.camera.position.clone(); }, done: () => X.viewer.camera.position.distanceTo(run.cam) > 0.05 },
  { target: '#views', title: N_('The set views'), text: N_('These frame it from the front, the back, each side, the top or three-quarters (keys 1 to 6). Click one.'),
    enter: () => { run.cam = X.viewer.camera.position.clone(); }, done: () => X.viewer.camera.position.distanceTo(run.cam) > 0.05 },
  { target: shadeTarget, title: N_('Clay: the shape alone'), text: () => ($('#tb-shade')?.offsetParent ? t('Clay is a grey render without colours or textures: you judge the shape alone — dents, bumps, seams. Click Clay.') : t('Clay is a grey render without colours or textures: you judge the shape alone — dents, bumps, seams. Pick Clay in this list of renders.')),
    done: () => X.viewer.opts.shade === 'clay' },
  { target: lit, title: N_('Back to Lit'), text: () => t('Lit shows the materials under a studio light, as in a game. The other renders: Unlit (colours only), Normals (the faces\' direction), UV (how textures are laid), Faces (the polygons).') + ' ' + ($('#tb-shade')?.offsetParent ? t('Click Lit.') : t('Pick Lit in the list.')),
    done: () => X.viewer.opts.shade === 'lit' },
  { target: '#t-pin', title: N_('Pin a note'), text: N_('Something to change? Pin a note to the place. Click Pin a note.'),
    enter: () => X.ensureRight('notes'), done: () => X.state.pinning },
  { target: '#view', title: N_('Click where it is'), text: N_('Now click on one of the iron hoops of the barrel.'),
    done: () => !$('#composer').hidden },
  { target: '#composer-text', title: N_('Say what should change'), next: true,
    enter: () => { const ta = $('#composer-text'); if (ta && !ta.value) ta.value = fr() ? 'Les cercles en fer sont trop fins : les épaissir.' : 'The iron hoops are too thin: make them thicker.'; },
    text: N_('We wrote it for you. Studio keeps the note with a picture of what you see and where you pinned it.') },
  { target: '#composer-save', title: N_('Save the note'), text: N_('Click Save note.'),
    enter: () => { run.notes = X.state.detail?.notes.length || 0; }, done: () => (X.state.detail?.notes.length || 0) > run.notes },
  { target: '#tb-claude', title: N_('Ask Claude'), text: N_('The ✦ tab talks to Claude about this model. Open it.'),
    done: () => !$('#tab-claude').hidden },
  { target: '#cl-send', title: N_('Send the request'), text: N_('We wrote the request. Send it — in this tutorial, the answer is played, not asked of Claude.'),
    enter: () => { const ta = $('#cl-text'); if (ta) ta.value = fr() ? 'Traite ma note sur les cercles.' : 'Work on my note about the hoops.'; },
    done: () => run.jobs.length > 0 },
  { target: '#tab-claude', title: N_('Claude works'), text: N_('The answer comes as Claude writes it. Each action is one line — open one to see what went in and out. Claude works in a Blender of its own, never yours.'),
    done: () => run.flags.noteDone },
  { target: '#note-list .note', title: N_('The note, addressed'), next: true,
    enter: () => X.ensureRight('notes'),
    text: N_('Claude marked it addressed: Studio rendered the same view of the new version beside the old one. Before and after, side by side.') },
  { target: '#t-compare', title: N_('Compare'), text: N_('Compare shows both versions in the 3D view, split by a divider or side by side, with their triangles and file size. Click Compare.'),
    done: () => !!X.state.compare },
  { target: () => '#note-list [data-act="resolve"]', title: N_('Say it is right'), text: N_('Right? Mark the note Looks right: it closes. Not yet sends it back to Claude with a word.'),
    enter: async () => { if (X.state.compare) await X.setCompare(null); X.ensureRight('notes'); }, done: () => note()?.status === 'resolved' },
  { target: '#tb-checks', title: N_('The checks'), text: N_('Checks reads the file against kiln\'s rules: triangles, size, ground, compression, licences. Open the tab.'),
    done: () => !$('#tab-checks').hidden },
  { target: '#tab-checks', title: N_('What it says'), next: true,
    text: N_('Green is fine, amber is worth a look, with what to do. A check Claude can fix comes with the words to ask for it.') },
  { target: '#t-create', title: N_('Make a new model'), text: N_('Click + to ask Claude for a new model.'),
    done: () => $('#create')?.open },
  { target: '#cr-launch', title: N_('Describe it'), text: N_('Say what it is, its style and its size, in your words; Made for sets the budgets. We wrote a lantern. Click Make it with Claude.'),
    enter: () => { const b = $('#cr-brief'); if (b) b.value = fr() ? 'Une lanterne de fiacre en fer forgé et verre, avec une bougie, environ 40 cm' : 'A carriage lantern in wrought iron and glass, with a candle, about 40 cm'; },
    done: () => !!run.createKey },
  { target: '#view', title: N_('Watch it being built'), text: N_('The lantern appears in the list as it is built, and the view follows each stage: block-out, details, materials. The strip on top says where kiln is.'),
    enter: () => { if (X.state.id !== LANTERN && run.assets.has(LANTERN)) X.go(LANTERN); },
    done: () => run.jobs.some((j) => j.state === 'waiting') },
  { target: () => '[data-cl="allow"]', title: N_('An approval'), text: N_('Claude wants to run a command outside the safe list: it stops and asks. The ✦ tab, the pill and the page title say so, wherever you are. Click Allow once.'),
    enter: () => X.openClaudeView(run.createKey), done: () => run.flags.approved },
  { target: '#view', title: N_('Done'), text: N_('The lantern is exported: it is a model like the others now, with its checks and its conversation.'),
    done: () => run.flags.made },
  { target: '#cl-pill-btn', title: N_('Claude, at a glance'), text: N_('The pill says what Claude does, what waits for you and how much of your quota is used. Open it.'),
    done: () => !$('#cl-act').hidden },
  { target: '#t-settings', title: N_('Settings'), next: true,
    enter: () => { if (!$('#cl-act').hidden) $('#cl-pill-btn').click(); },
    text: N_('In Settings: the display, the project (what models are made for, its CLAUDE.md), how Claude works (approvals, paid generation, how many at once) and which account pays. Setup lists what kiln uses and installs what is missing.') },
  { center: true, title: N_('That is Studio'), next: true, last: true,
    text: N_('⌘K finds every command, ? lists the keys. From the terminal, Claude can drive this page too (/kiln studio, present mode for a second screen). Finish to go back to your project: the tutorial wrote nothing in it.') },
];

// ── the spotlight ────────────────────────────────────────────────────────────

function ui() {
  if ($('#tuto')) return;
  document.body.insertAdjacentHTML('beforeend', `
    <div id="tuto" class="tuto"><div class="tuto-dim" id="tuto-dim"></div><div class="tuto-ring" id="tuto-ring"></div>
      <div class="tuto-card" id="tuto-card" role="dialog" aria-live="polite" aria-labelledby="tuto-title">
        <div class="tuto-head"><span class="tuto-step" id="tuto-step"></span><span class="tuto-sim" title="${esc(t('A simulation: no Claude runs, no quota is used, nothing is written to your project.'))}">${esc(t('Simulation'))}</span></div>
        <h4 id="tuto-title"></h4><p id="tuto-text"></p>
        <div class="tuto-acts"><button class="btn sm ghost" id="tuto-quit">${esc(t('Leave'))}</button><span class="tuto-hint" id="tuto-hint"></span><span class="sp"></span><button class="btn sm accent" id="tuto-next"></button></div>
      </div></div>`);
  $('#tuto-quit').onclick = () => stop();
  $('#tuto-next').onclick = () => go(run.i + 1);
}
function target(st) {
  const sel = typeof st.target === 'function' ? st.target() : st.target;
  const el = sel && $(sel);
  return el && el.getClientRects().length ? el : null;
}
function place() {
  if (!run) return;
  const st = STEPS[run.i], el = !st.center && target(st);
  const ring = $('#tuto-ring'), card = $('#tuto-card'), dim = $('#tuto-dim');
  const vw0 = innerWidth, vh0 = innerHeight;
  if (!el) {
    // Nothing to point at: the whole page dimmed, the card in the middle.
    ring.style.opacity = '0';
    dim.style.clipPath = 'none';
    Object.assign(card.style, { left: '50%', top: '50%', transform: 'translate(-50%, -50%)' });
    return;
  }
  const r = el.getBoundingClientRect(), pad = 6;
  const hx = r.left - pad, hy = r.top - pad, hw = r.width + 2 * pad, hh = r.height + 2 * pad;
  Object.assign(ring.style, { opacity: '1', left: `${hx}px`, top: `${hy}px`, width: `${hw}px`, height: `${hh}px` });
  // The page dimmed but for a hole where the user acts (a box-shadow that wide does not draw).
  dim.style.clipPath = `path(evenodd, "M0 0H${vw0}V${vh0}H0Z M${hx} ${hy}h${hw}v${hh}h${-hw}Z")`;
  const cw = card.offsetWidth, ch = card.offsetHeight, vw = innerWidth, vh = innerHeight, gap = 14;
  let x, y;
  if (r.width > vw * 0.4 && r.height > vh * 0.4) { x = r.left + 24; y = r.bottom - ch - 84; }   // a big area: inside, bottom-left (its top shows the build)
  else if (r.right + gap + cw < vw - 12) { x = r.right + gap; y = r.top; }                        // right of it
  else if (r.left - gap - cw > 12) { x = r.left - gap - cw; y = r.top; }                           // left of it
  else if (r.bottom + gap + ch < vh - 12) { x = r.left + r.width / 2 - cw / 2; y = r.bottom + gap; } // below
  else { x = r.left + r.width / 2 - cw / 2; y = r.top - gap - ch; }                                 // above
  x = Math.max(12, Math.min(vw - cw - 12, x)); y = Math.max(12, Math.min(vh - ch - 12, y));
  Object.assign(card.style, { left: `${x}px`, top: `${y}px`, transform: 'none' });
}
async function go(i) {
  if (!run) return;
  clearInterval(run.timer);
  if (i >= STEPS.length) return stop(true);
  run.i = i;
  const st = STEPS[i];
  $('#tuto-step').textContent = t('Step {n} of {m}', { n: i + 1, m: STEPS.length });
  $('#tuto-title').textContent = t(st.title);
  $('#tuto-text').textContent = typeof st.text === 'function' ? st.text() : t(st.text);
  $('#tuto-next').hidden = !st.next;
  $('#tuto-next').textContent = st.last ? t('Finish') : t('Next');
  $('#tuto-hint').textContent = st.next ? '' : t('Do it to go on');
  $('#tuto-card').classList.remove('ok');
  await st.enter?.();
  place();
  run.timer = setInterval(() => {
    place();
    if (!st.next && st.done?.()) {
      clearInterval(run.timer);
      $('#tuto-card').classList.add('ok');
      $('#tuto-hint').textContent = '✓';
      setTimeout(() => run && run.i === i && go(i + 1), 700);
    }
  }, 250);
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
  go(0);
}

export async function stop(finished = false) {
  if (!run) return;
  clearInterval(run.timer);
  run.answer?.('deny');
  const back = run.back;
  run = null;
  removeEventListener('resize', place);
  $('#tuto')?.remove();
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

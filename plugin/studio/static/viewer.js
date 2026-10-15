// Kiln Studio's 3D view: loading, shading, compare, picking, screenshots.
// three.js/glTF is Y-up with the model front on +Z. Blender, which kiln models in,
// reads that as (x, -z, y): front on -Y, Z up. Every coordinate the page shows or
// saves for Claude is also given in Blender's frame.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const CDN = 'https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/libs/';
export const toBlender = (v) => [v.x, -v.z, v.y];
const r4 = (a) => a.map((x) => +x.toFixed(4));

export const BACKGROUNDS = {
  dark: ['#2a2420', '#0f0c0a'],
  mid: ['#5b5550', '#34302c'],
  light: ['#e9e4dd', '#bdb6ad'],
};

// ── loading ──────────────────────────────────────────────────────────────────

function makeLoaders(renderer) {
  const draco = new DRACOLoader().setDecoderPath(CDN + 'draco/gltf/');
  const ktx2 = new KTX2Loader().setTranscoderPath(CDN + 'basis/').detectSupport(renderer);
  const gltf = new GLTFLoader().setDRACOLoader(draco).setKTX2Loader(ktx2).setMeshoptDecoder(MeshoptDecoder);
  return { gltf, fbx: new FBXLoader(), obj: new OBJLoader() };
}

async function loadModel(loaders, url, ext) {
  if (ext === '.fbx') {
    const root = await loaders.fbx.loadAsync(url);
    // FBX from Blender comes in centimetres unless exported with scale 1.0 and
    // "Apply Transform"; kiln's are, so nothing is rescaled here.
    return { root, animations: root.animations || [], parser: null };
  }
  if (ext === '.obj') {
    const root = await loaders.obj.loadAsync(url);
    return { root, animations: [], parser: null };
  }
  const g = await loaders.gltf.loadAsync(url);
  return { root: g.scene, animations: g.animations || [], parser: g.parser };
}

// ── materials per shading mode ───────────────────────────────────────────────

function checkerTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d');
  const n = 8;
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      g.fillStyle = (x + y) % 2 ? '#e9e1d6' : '#d67e2c';
      g.fillRect((x * 256) / n, (y * 256) / n, 256 / n, 256 / n);
    }
  }
  g.fillStyle = '#140d07';
  g.font = 'bold 22px ui-monospace, monospace';
  g.fillText('F', 10, 30); // a glyph shows flipped and rotated islands
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

function facesMaterial() {
  // Front faces clay, back faces red: flipped normals and holes in one look.
  const m = new THREE.MeshStandardMaterial({ color: 0xbdb6ac, roughness: 0.85, side: THREE.DoubleSide });
  m.onBeforeCompile = (s) => {
    s.fragmentShader = s.fragmentShader.replace('#include <dithering_fragment>',
      '#include <dithering_fragment>\n if (!gl_FrontFacing) gl_FragColor = vec4(0.86, 0.16, 0.12, 1.0);');
  };
  return m;
}

const SHARED = {
  clay: () => new THREE.MeshStandardMaterial({ color: 0xbdb6ac, roughness: 0.85, metalness: 0 }),
  normals: () => new THREE.MeshNormalMaterial(),
  uv: () => new THREE.MeshBasicMaterial({ map: checkerTexture() }),
  faces: facesMaterial,
};

function unlitOf(m) {
  if (!m.userData.unlit) {
    m.userData.unlit = new THREE.MeshBasicMaterial({
      map: m.map || null, color: m.color ? m.color.clone() : 0xffffff, vertexColors: !!m.vertexColors,
      transparent: m.transparent, opacity: m.opacity, alphaTest: m.alphaTest, side: m.side,
    });
  }
  return m.userData.unlit;
}

export class Superseded extends Error {
  constructor() { super('superseded by a newer load'); this.name = 'Superseded'; }
}

// Geometry, materials and their textures (and the ImageBitmaps behind them).
function disposeTree(root) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.geometry?.dispose();
    for (const m of [].concat(o.userData.orig || o.material)) {
      for (const k in m) {
        const t = m[k];
        if (t?.isTexture) { t.image?.close?.(); t.dispose(); }
      }
      m.userData?.unlit?.dispose();
      m.dispose?.();
    }
  });
}

// ── a loaded model, for one side of the view ─────────────────────────────────

class Slot {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group();
    scene.add(this.group);
    this.model = null;
    this.meshes = [];
    this.mixer = null;
    this.clips = [];
    this.action = null;
    this.parser = null;
    this.box = new THREE.Box3();
    this.skeleton = null;
  }
  clear() {
    if (this.model) {
      this.group.remove(this.model);
      disposeTree(this.model);
    }
    if (this.skeleton) { this.scene.remove(this.skeleton); this.skeleton = null; }
    this.model = null; this.meshes = []; this.mixer = null; this.clips = []; this.action = null; this.parser = null;
  }
  set(loaded) {
    this.clear();
    this.model = loaded.root;
    this.parser = loaded.parser;
    this.group.add(this.model);
    this.model.traverse((o) => {
      if (o.isMesh) { o.userData.orig = o.material; this.meshes.push(o); }
    });
    this.clips = loaded.animations;
    if (this.clips.length) this.mixer = new THREE.AnimationMixer(this.model);
    this.model.updateMatrixWorld(true);
    this.box.setFromObject(this.model);
    if (this.box.isEmpty()) this.box.set(new THREE.Vector3(-0.5, 0, -0.5), new THREE.Vector3(0.5, 1, 0.5));
  }
  stats() {
    let tris = 0, verts = 0;
    const mats = new Map(), texs = new Map();
    for (const m of this.meshes) {
      const g = m.geometry;
      const n = g.index ? g.index.count : g.attributes.position?.count || 0;
      tris += Math.floor(n / 3);
      verts += g.attributes.position?.count || 0;
      for (const mat of [].concat(m.userData.orig)) {
        mats.set(mat.uuid, mat);
        for (const k of ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'emissiveMap', 'alphaMap']) {
          const t = mat[k];
          if (t?.image) texs.set(t.uuid, { slot: k, name: t.name || mat.name, w: t.image.width, h: t.image.height });
        }
      }
    }
    const s = this.box.getSize(new THREE.Vector3());
    return {
      tris, verts, meshes: this.meshes.length,
      materials: [...mats.values()].map((m) => m.name || '(unnamed)'),
      textures: [...texs.values()],
      dims: [s.x, s.z, s.y], // Blender X, Y, Z
      clips: this.clips.map((c) => ({ name: c.name, duration: c.duration })),
      skinned: this.meshes.some((m) => m.isSkinnedMesh),
    };
  }
}

// ── the viewer ───────────────────────────────────────────────────────────────

export class Viewer {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    this.loaders = makeLoaders(this.renderer);
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

    this.camera = new THREE.PerspectiveCamera(35, 1, 0.01, 5000);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.12;
    this.controls.addEventListener('change', () => this.onChange?.());

    this.a = new Slot(this.makeScene());
    this.b = new Slot(this.makeScene());
    this.helpers = new THREE.Group();
    this.a.scene.add(this.helpers);
    this.helpersB = new THREE.Group();
    this.b.scene.add(this.helpersB);

    this.opts = { shade: 'lit', wire: false, grid: true, bounds: false, skeleton: false, bg: 'dark' };
    this.compare = false;
    this.shared = {};
    this.wireMat = new THREE.MeshBasicMaterial({ color: 0x140d07, wireframe: true, transparent: true, opacity: 0.35 });
    this.raycaster = new THREE.Raycaster();
    this.timer = new THREE.Timer();
    this.playing = true;
    this.speed = 1;
    this.size = { w: 1, h: 1 };
    new ResizeObserver(() => this.resize()).observe(canvas.parentElement);
    this.resize();
    this.renderer.setAnimationLoop((t) => this.tick(t));
  }

  makeScene() {
    const s = new THREE.Scene();
    s.environment = this.env;
    const key = new THREE.DirectionalLight(0xfff1e0, 1.1);
    key.position.set(3, 6, 4);
    s.add(key, new THREE.HemisphereLight(0xf4ede4, 0x2a2420, 0.35));
    return s;
  }

  resize() {
    const r = this.canvas.parentElement.getBoundingClientRect();
    this.size = { w: Math.max(r.width, 1), h: Math.max(r.height, 1) };
    this.renderer.setSize(this.size.w, this.size.h, false);
    this.updateAspect();
    this.onChange?.();
  }

  updateAspect() {
    const w = this.compare ? this.size.w / 2 : this.size.w;
    this.camera.aspect = w / this.size.h;
    this.camera.updateProjectionMatrix();
  }

  // The region of the canvas the current model is drawn in: the right half in compare.
  viewRect() {
    return this.compare
      ? { x: this.size.w / 2, y: 0, w: this.size.w / 2, h: this.size.h }
      : { x: 0, y: 0, w: this.size.w, h: this.size.h };
  }

  // A load that finishes after a newer one started is dropped, not shown.
  async load(url, ext, { keepCamera = false } = {}) {
    const seq = (this.seqA = (this.seqA || 0) + 1);
    const loaded = await loadModel(this.loaders, url, ext);
    if (seq !== this.seqA) { disposeTree(loaded.root); throw new Superseded(); }
    this.a.set(loaded);
    this.afterLoad(this.a);
    this.rebuildHelpers();
    if (!keepCamera) this.frame();
    return this.a.stats();
  }

  async loadCompare(url, ext) {
    const seq = (this.seqB = (this.seqB || 0) + 1);
    const loaded = await loadModel(this.loaders, url, ext);
    if (seq !== this.seqB || !this.compare) { disposeTree(loaded.root); throw new Superseded(); }
    this.b.set(loaded);
    this.afterLoad(this.b);
    this.rebuildHelpers();
    this.syncClip();
    return this.b.stats();
  }

  setCompare(on) {
    this.compare = on;
    if (!on) this.b.clear();
    this.updateAspect();
    if (this.a.model) this.frame(); // half the width: refit, same direction
    this.rebuildHelpers();
    this.onChange?.();
  }

  afterLoad(slot) {
    this.applyShading(slot);
    if (slot.clips.length) {
      const name = this.clipName && slot.clips.find((c) => c.name === this.clipName) ? this.clipName : slot.clips[0].name;
      this.playClip(name, slot);
    }
  }

  // shading
  set(opt, value) {
    this.opts[opt] = value;
    if (opt === 'shade') { this.applyShading(this.a); this.applyShading(this.b); }
    if (opt === 'grid' || opt === 'bounds' || opt === 'skeleton') this.rebuildHelpers();
    this.onChange?.();
  }

  applyShading(slot) {
    const mode = this.opts.shade;
    for (const m of slot.meshes) {
      const orig = m.userData.orig;
      if (mode === 'lit') m.material = orig;
      else if (mode === 'unlit') m.material = Array.isArray(orig) ? orig.map(unlitOf) : unlitOf(orig);
      else m.material = this.shared[mode] ||= SHARED[mode]();
    }
  }

  // helpers: grid with the front marked, bounds with sizes, skeleton
  rebuildHelpers() {
    for (const [g, slot] of [[this.helpers, this.a], [this.helpersB, this.b]]) {
      for (const c of [...g.children]) { g.remove(c); c.geometry?.dispose(); c.material?.dispose?.(); }
      if (slot.skeleton) { slot.scene.remove(slot.skeleton); slot.skeleton = null; }
      if (!slot.model) continue;
      const box = slot.box;
      const size = box.getSize(new THREE.Vector3());
      const span = Math.max(size.x, size.z, size.y * 0.5, 0.01);
      if (this.opts.grid) {
        // 1 m cells, or 10 cm when the model is small: always a readable scale.
        const cell = span < 1.5 ? 0.1 : 1;
        const half = Math.max(Math.ceil((span * 1.2) / cell) * cell, cell * 5);
        const light = this.opts.bg === 'light';
        const grid = new THREE.GridHelper(half * 2, Math.round((half * 2) / cell), light ? 0x8a8279 : 0x6d655e, light ? 0xb3aca3 : 0x3a332e);
        grid.material.transparent = true;
        grid.material.opacity = 0.55;
        grid.position.y = 0;
        g.add(grid);
        // Front: +Z here, Blender's -Y. An arrow on the ground, just past the model.
        const front = new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1),
          new THREE.Vector3(0, 0.001, Math.max(box.max.z, 0) + span * 0.08), span * 0.25, 0xffb547, span * 0.08, span * 0.05);
        g.add(front);
      }
      if (this.opts.bounds) g.add(new THREE.Box3Helper(box.clone(), 0x2bb5d6));
      if (this.opts.skeleton && slot.meshes.some((m) => m.isSkinnedMesh)) {
        slot.skeleton = new THREE.SkeletonHelper(slot.model);
        slot.skeleton.material.depthTest = false;
        slot.scene.add(slot.skeleton);
      }
    }
  }

  // Corners of the bounds in screen space, for the size labels.
  boundsLabels() {
    if (!this.opts.bounds || !this.a.model) return [];
    const b = this.a.box;
    const s = b.getSize(new THREE.Vector3());
    const mid = b.getCenter(new THREE.Vector3());
    return [
      { text: `X ${fmtM(s.x)}`, p: new THREE.Vector3(mid.x, b.min.y, b.max.z) },
      { text: `Y ${fmtM(s.z)}`, p: new THREE.Vector3(b.max.x, b.min.y, mid.z) },
      { text: `Z ${fmtM(s.y)}`, p: new THREE.Vector3(b.max.x, mid.y, b.max.z) },
    ].map((l) => ({ ...l, ...this.toScreen(l.p) }));
  }

  // camera
  frame(dir) {
    const box = this.a.model ? this.a.box : new THREE.Box3(new THREE.Vector3(-1, 0, -1), new THREE.Vector3(1, 1, 1));
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const d = (dir || this.camera.position.clone().sub(this.controls.target)).clone().normalize();
    if (d.lengthSq() === 0) d.set(1, 0.7, 1.3).normalize();
    const fov = THREE.MathUtils.degToRad(this.camera.fov);
    const fit = Math.min(fov, 2 * Math.atan(Math.tan(fov / 2) * this.camera.aspect));
    const dist = (sphere.radius / Math.sin(fit / 2)) * 1.08;
    this.controls.target.copy(sphere.center);
    this.camera.position.copy(sphere.center).addScaledVector(d, dist);
    this.camera.near = Math.max(dist / 1000, 0.001);
    this.camera.far = dist * 100;
    this.camera.updateProjectionMatrix();
    this.controls.update();
  }

  // Frame the model from a direction given as [x, y, z] (three.js axes).
  lookFrom(dir) {
    this.frame(new THREE.Vector3(...dir));
  }

  view(name) {
    const dirs = {
      front: [0, 0, 1], back: [0, 0, -1], right: [1, 0, 0], left: [-1, 0, 0],
      top: [0, 1, 0.0001], iso: [1, 0.7, 1.3],
    };
    this.frame(new THREE.Vector3(...dirs[name]));
  }

  cameraState() {
    const p = this.camera.position, t = this.controls.target;
    return {
      position: r4(p.toArray()), target: r4(t.toArray()), fov: this.camera.fov, aspect: +this.camera.aspect.toFixed(4),
      position_blender: r4(toBlender(p)), target_blender: r4(toBlender(t)),
    };
  }

  setCamera(c) {
    this.camera.position.fromArray(c.position);
    this.controls.target.fromArray(c.target);
    const dist = this.camera.position.distanceTo(this.controls.target);
    this.camera.near = Math.max(dist / 1000, 0.001);
    this.camera.far = dist * 100;
    this.camera.updateProjectionMatrix();
    this.controls.update();
  }

  // animation
  playClip(name, slot = this.a) {
    if (!slot.mixer) return;
    const clip = slot.clips.find((c) => c.name === name) || slot.clips[0];
    slot.mixer.stopAllAction();
    slot.action = slot.mixer.clipAction(clip).play();
    if (slot === this.a) { this.clipName = clip.name; this.syncClip(); }
  }
  syncClip() {
    if (this.b.mixer && this.clipName) {
      const c = this.b.clips.find((x) => x.name === this.clipName);
      if (c) { this.b.mixer.stopAllAction(); this.b.action = this.b.mixer.clipAction(c).play(); this.b.action.time = this.a.action?.time || 0; }
    }
  }
  seek(t) {
    for (const s of [this.a, this.b]) if (s.action) { s.action.time = t; s.mixer.update(0); }
    this.onChange?.();
  }
  get clipTime() { return this.a.action?.time || 0; }
  get clipDuration() { return this.a.action?.getClip().duration || 0; }

  // picking: the current model only, in its own half of the view
  pick(clientX, clientY) {
    if (!this.a.model) return null;
    const rect = this.canvas.getBoundingClientRect();
    const v = this.viewRect();
    const x = clientX - rect.left - v.x, y = clientY - rect.top - v.y;
    if (x < 0 || y < 0 || x > v.w || y > v.h) return null;
    this.raycaster.setFromCamera(new THREE.Vector2((x / v.w) * 2 - 1, -(y / v.h) * 2 + 1), this.camera);
    const hits = this.raycaster.intersectObjects(this.a.meshes.filter((m) => m.visible), false);
    const hit = hits[0];
    if (!hit) return null;
    const n = hit.face ? hit.face.normal.clone().transformDirection(hit.object.matrixWorld).normalize() : new THREE.Vector3(0, 1, 0);
    if (n.dot(this.raycaster.ray.direction) > 0) n.negate();
    let o = hit.object, object = null;
    while (o && !object) { if (o.userData.name) object = o.userData.name; o = o.parent; }
    const assoc = this.a.parser?.associations.get(hit.object);
    const meshName = assoc && assoc.meshes !== undefined ? this.a.parser.json.meshes[assoc.meshes]?.name : hit.object.name;
    const mat = Array.isArray(hit.object.userData.orig)
      ? hit.object.userData.orig[hit.face?.materialIndex || 0] : hit.object.userData.orig;
    return {
      point: r4(hit.point.toArray()), normal: r4(n.toArray()),
      point_blender: r4(toBlender(hit.point)), normal_blender: r4(toBlender(n)),
      object: object || hit.object.name || '', mesh: meshName || '', material: mat?.name || '',
      face: hit.faceIndex ?? null, region: this.region(hit.point),
    };
  }

  // A rough place on the model in words, in Blender's frame: "top, front (-Y), +X side".
  region(p) {
    const b = this.a.box, s = b.getSize(new THREE.Vector3());
    const f = (v, lo, size) => (size < 1e-6 ? 0.5 : (v - lo) / size);
    const h = f(p.y, b.min.y, s.y), d = f(p.z, b.min.z, s.z), w = f(p.x, b.min.x, s.x);
    const parts = [h > 0.67 ? 'top' : h < 0.33 ? 'bottom' : 'middle height'];
    parts.push(d > 0.67 ? 'front (-Y)' : d < 0.33 ? 'back (+Y)' : 'mid depth');
    parts.push(w > 0.67 ? '+X side' : w < 0.33 ? '-X side' : 'centre');
    return parts.join(', ');
  }

  // Screen position of a world point inside the canvas, with whether it faces us.
  toScreen(p) {
    const v = this.viewRect();
    const q = new THREE.Vector3().fromArray(Array.isArray(p) ? p : p.toArray()).project(this.camera);
    return { x: v.x + ((q.x + 1) / 2) * v.w, y: ((1 - q.y) / 2) * v.h, behind: q.z > 1, inView: Math.abs(q.x) <= 1.02 && Math.abs(q.y) <= 1.02 };
  }

  // Whether a pinned point is hidden behind the model from where the camera is.
  occluded(point) {
    const p = new THREE.Vector3().fromArray(point);
    const dir = p.clone().sub(this.camera.position);
    const dist = dir.length();
    this.raycaster.set(this.camera.position, dir.normalize());
    const hit = this.raycaster.intersectObjects(this.a.meshes, false)[0];
    return !!hit && hit.distance < dist - Math.max(dist * 0.01, 0.002);
  }

  // drawing
  tick(t) {
    this.timer.update(t);
    const dt = Math.min(this.timer.getDelta(), 0.1);
    this.controls.update();
    if (this.playing) {
      for (const s of [this.a, this.b]) s.mixer?.update(dt * this.speed);
      if (this.a.mixer) this.onAnimate?.();
    }
    this.draw();
    this.onFrame?.();
  }

  draw() {
    const r = this.renderer, { w, h } = this.size;
    r.setScissorTest(this.compare);
    r.autoClear = false;
    r.clear();
    const passes = this.compare ? [[this.b.scene, 0], [this.a.scene, w / 2]] : [[this.a.scene, 0]];
    for (const [scene, x] of passes) {
      const vw = this.compare ? w / 2 : w;
      r.setViewport(x, 0, vw, h);
      r.setScissor(x, 0, vw, h);
      r.render(scene, this.camera);
      if (this.opts.wire) {
        scene.overrideMaterial = this.wireMat;
        this.wireMat.color.set(this.opts.bg === 'light' || this.opts.shade !== 'lit' ? 0x140d07 : 0xf4ede4);
        r.render(scene, this.camera);
        scene.overrideMaterial = null;
      }
    }
    r.setScissorTest(false);
  }

  // A note's pictures, as the user sees the model now (shading, wireframe, pose):
  // `shot`, the view cropped to the model (and the pin), and for a pin `detail`, a
  // close-up rendered nearer along the user's line of sight to it, the spot marked
  // without being covered. `view` is what an "after" render needs to frame both again.
  screenshot({ pin = null } = {}) {
    this.draw();
    const src = this.renderer.domElement;
    const v = this.viewRect(), k = src.width / this.size.w;
    const crop = this.a.model ? modelCrop(this.a.box, this.camera, pin) : [0, 0, 1, 1];
    const full = document.createElement('canvas');
    full.width = Math.round(v.w * k); full.height = Math.round(v.h * k);
    const g = full.getContext('2d');
    paintBackground(g, full.width, full.height, this.opts.bg);
    g.drawImage(src, v.x * k, v.y * k, full.width, full.height, 0, 0, full.width, full.height);
    let mark = null;
    if (pin) {
      const q = new THREE.Vector3().fromArray(pin).project(this.camera);
      mark = [(q.x + 1) / 2, (1 - q.y) / 2];
    }
    const view = { crop };
    const out = { shot: finishShot(full, { crop, max: SHOT_MAX, mark }), view };
    if (pin && this.a.model) {
      const cam = closeUpCamera(this.camera, pin, this.a.box);
      view.detail = { position: r4(cam.position.toArray()), target: r4(pin), fov: +cam.fov.toFixed(3) };
      cam.aspect = 1;
      cam.updateProjectionMatrix();
      // One square frame in the corner of the canvas, read back at once, then the view
      // is drawn again: nothing shows on screen.
      const side = Math.min(src.width, src.height), r = this.renderer;
      r.setScissorTest(true);
      r.setViewport(0, 0, side / r.getPixelRatio(), side / r.getPixelRatio());
      r.setScissor(0, 0, side / r.getPixelRatio(), side / r.getPixelRatio());
      r.clear();
      r.render(this.a.scene, cam);
      if (this.opts.wire) {
        this.a.scene.overrideMaterial = this.wireMat;
        r.render(this.a.scene, cam);
        this.a.scene.overrideMaterial = null;
      }
      r.setScissorTest(false);
      const sq = document.createElement('canvas');
      sq.width = sq.height = side;
      const gs = sq.getContext('2d');
      paintBackground(gs, side, side, this.opts.bg);
      gs.drawImage(src, 0, src.height - side, side, side, 0, 0, side, side);
      out.detail = finishShot(sq, { max: DETAIL_MAX, mark: [0.5, 0.5], quality: 0.82 });
      this.draw();
    }
    return out;
  }

  dispose() {
    this.renderer.setAnimationLoop(null);
    this.a.clear(); this.b.clear();
    this.renderer.dispose();
  }
}

export function paintBackground(g, w, h, bg) {
  const [inner, outer] = BACKGROUNDS[bg] || BACKGROUNDS.dark;
  const grad = g.createRadialGradient(w / 2, h * 0.45, 0, w / 2, h * 0.45, Math.hypot(w, h) * 0.6);
  grad.addColorStop(0, inner);
  grad.addColorStop(1, outer);
  g.fillStyle = grad;
  g.fillRect(0, 0, w, h);
}

// ── note pictures ──────────────────────────────────────────────────────────
// Small enough to keep (WebP, ~10-20 kB), sharp enough for Claude to read the spot.

const SHOT_MAX = 1024;   // the view, long edge
const DETAIL_MAX = 640;  // the close-up, square

// Four ticks pointing at the spot from around it: the spot itself stays visible.
function drawMark(g, x, y, r) {
  const gap = r * 0.45, len = r * 0.55;
  const ticks = (w, color) => {
    g.lineWidth = w; g.strokeStyle = color; g.lineCap = 'round';
    g.beginPath();
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      g.moveTo(x + dx * gap, y + dy * gap);
      g.lineTo(x + dx * (gap + len), y + dy * (gap + len));
    }
    g.stroke();
  };
  ticks(Math.max(4, r / 5) + 3, 'rgba(20,13,7,0.85)');
  ticks(Math.max(4, r / 5), '#ff5a14');
}

// Crop (fractions of the view) and scale a picture, mark the spot, and encode it:
// WebP, or JPEG where the browser cannot write WebP (Safari gives a PNG back).
function finishShot(src, { crop = [0, 0, 1, 1], max, mark = null, quality = 0.8 }) {
  const sx = crop[0] * src.width, sy = crop[1] * src.height;
  const sw = (crop[2] - crop[0]) * src.width, sh = (crop[3] - crop[1]) * src.height;
  const scale = Math.min(1, max / Math.max(sw, sh));
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(sw * scale)); c.height = Math.max(1, Math.round(sh * scale));
  const g = c.getContext('2d');
  g.imageSmoothingQuality = 'high';
  g.drawImage(src, sx, sy, sw, sh, 0, 0, c.width, c.height);
  if (mark) {
    const x = (mark[0] * src.width - sx) * scale, y = (mark[1] * src.height - sy) * scale;
    drawMark(g, x, y, Math.max(14, Math.max(c.width, c.height) / 34));
  }
  const webp = c.toDataURL('image/webp', quality);
  return webp.startsWith('data:image/webp') ? webp : c.toDataURL('image/jpeg', Math.min(0.9, quality + 0.05));
}

// The model's outline on screen (and the pin), with a margin, as fractions of the view.
function modelCrop(box, camera, pin) {
  const pts = [];
  for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) pts.push(new THREE.Vector3(x, y, z));
  if (pin) pts.push(new THREE.Vector3().fromArray(pin));
  let x0 = 1, y0 = 1, x1 = 0, y1 = 0;
  for (const p of pts) {
    const q = p.project(camera);
    if (q.z > 1) return [0, 0, 1, 1];   // a corner behind the camera: inside the model
    const x = (q.x + 1) / 2, y = (1 - q.y) / 2;
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
  }
  const m = 0.06 * Math.max(x1 - x0, y1 - y0) + 0.02;
  const c = [x0 - m, y0 - m, x1 + m, y1 + m].map((v) => Math.min(1, Math.max(0, v)));
  // Next to nothing to cut: keep the whole view.
  return (c[2] - c[0]) * (c[3] - c[1]) > 0.8 ? [0, 0, 1, 1] : c.map((v) => +v.toFixed(4));
}

// Nearer the pin along the line the user looked at it: what they saw past stays clear.
// It spans 30% of the model's size, or 60% of what the view shows there if zoomed in.
function closeUpCamera(camera, pin, box) {
  const p = new THREE.Vector3().fromArray(pin);
  const u = p.clone().sub(camera.position);
  const dPin = u.length();
  u.normalize();
  const half = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
  const span = Math.min(0.3 * box.getSize(new THREE.Vector3()).length(), 0.6 * 2 * dPin * half);
  const dist = span / 2 / half;
  const cam = new THREE.PerspectiveCamera(camera.fov, 1, Math.max(dist / 100, 0.0005), dist * 200);
  cam.position.copy(p).addScaledVector(u, -dist);
  cam.lookAt(p);
  return cam;
}

export function fmtM(m) {
  if (m >= 1) return `${m.toFixed(2)} m`;
  if (m >= 0.01) return `${(m * 100).toFixed(1)} cm`;
  return `${(m * 1000).toFixed(1)} mm`;
}

// ── offscreen renders: sidebar/version thumbnails and "after" screenshots ────

export class Offscreen {
  constructor() {
    this.canvas = document.createElement('canvas');
    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    this.loaders = makeLoaders(this.renderer);
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  }

  // camera: a saved note camera, or null to frame three-quarter front.
  async render(url, ext, { w = 320, h = 240, camera = null, type = 'image/webp', quality = 0.82, bg = 'dark' } = {}) {
    const c = await this.draw(url, ext, { w, h, camera, bg });
    return c.toDataURL(type, quality);
  }

  // A note's "after": its view and close-up again, framed as the note's own (studio's
  // screenshot()), of the version Claude exported. Without a saved view (older notes),
  // the whole view as it was.
  async noteShots(url, ext, note, { bg = 'dark' } = {}) {
    const cam = note.camera, view = note.view || {}, pin = note.anchor?.point || null;
    const crop = view.crop || [0, 0, 1, 1];
    const aspect = cam.aspect || 4 / 3;
    // Large enough that the cropped part still makes SHOT_MAX pixels.
    const w = Math.min(4096, Math.ceil(SHOT_MAX / Math.max(crop[2] - crop[0], (crop[3] - crop[1]) / aspect)));
    const loaded = await loadModel(this.loaders, url, ext);
    try {
      const full = this.paint(loaded, w, Math.round(w / aspect), cam, bg);
      let mark = null;
      if (pin) {
        const q = new THREE.Vector3().fromArray(pin).project(this.lastCamera);
        mark = [(q.x + 1) / 2, (1 - q.y) / 2];
      }
      const out = { shot: finishShot(full, { crop, max: SHOT_MAX, mark }) };
      if (pin && view.detail) {
        const sq = this.paint(loaded, DETAIL_MAX, DETAIL_MAX, { ...view.detail, aspect: 1 }, bg);
        out.detail = finishShot(sq, { max: DETAIL_MAX, mark: [0.5, 0.5], quality: 0.82 });
      }
      return out;
    } finally {
      disposeTree(loaded.root);
      this.renderer.renderLists.dispose();
    }
  }

  async draw(url, ext, { w, h, camera, bg }) {
    const loaded = await loadModel(this.loaders, url, ext);
    try {
      return this.paint(loaded, w, h, camera, bg);
    } finally {
      disposeTree(loaded.root);
      this.renderer.renderLists.dispose();
    }
  }

  paint(loaded, w, h, camera, bg) {
    const scene = new THREE.Scene();
    scene.environment = this.env;
    const key = new THREE.DirectionalLight(0xfff1e0, 1.1);
    key.position.set(3, 6, 4);
    scene.add(key, new THREE.HemisphereLight(0xf4ede4, 0x2a2420, 0.35), loaded.root);
    loaded.root.updateMatrixWorld(true);
    const cam = new THREE.PerspectiveCamera(camera?.fov || 35, w / h, 0.001, 5000);
    if (camera) {
      cam.position.fromArray(camera.position);
      cam.lookAt(new THREE.Vector3().fromArray(camera.target));
      const dist = cam.position.distanceTo(new THREE.Vector3().fromArray(camera.target));
      cam.near = Math.max(dist / 1000, 0.001); cam.far = dist * 100;
    } else {
      const box = new THREE.Box3().setFromObject(loaded.root);
      const sphere = box.getBoundingSphere(new THREE.Sphere());
      const dir = new THREE.Vector3(1, 0.7, 1.3).normalize();
      const fov = THREE.MathUtils.degToRad(cam.fov);
      const dist = (sphere.radius / Math.sin(Math.min(fov, 2 * Math.atan(Math.tan(fov / 2) * cam.aspect)) / 2)) * 1.05;
      cam.position.copy(sphere.center).addScaledVector(dir, dist);
      cam.lookAt(sphere.center);
      cam.near = Math.max(dist / 1000, 0.001); cam.far = dist * 100;
    }
    cam.updateProjectionMatrix();
    this.lastCamera = cam;
    this.renderer.setSize(w, h, false);
    this.renderer.render(scene, cam);
    scene.remove(loaded.root);   // the model is drawn again for the close-up
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const g = c.getContext('2d');
    paintBackground(g, w, h, bg);
    g.drawImage(this.canvas, 0, 0);
    return c;
  }
}

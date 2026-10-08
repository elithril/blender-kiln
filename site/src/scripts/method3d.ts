import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

export interface MethodScene {
  glb: string; photo: string; mask: string; crops: string[];
  scans: { name: string; img: string }[]; joints: string[];
  camera: { azimuth: number; elevation: number };
}

const sm = (a: number, b: number, x: number) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const bell = (a: number, b: number, x: number, f = 0.15) => Math.min(sm(a, a + f, x), 1 - sm(b - f, b, x));

/** The ammo box session, replayed on its real GLB. `s` runs 0..5, one unit per step:
 *  read (parts assemble, crops float), texture (two scans orbit, then wrap the clay), measure
 *  (photo camera, red/cyan silhouettes), look (camera dives on three joints), ship (spin). */
export function mountMethod(canvas: HTMLCanvasElement, base: string, cfg: MethodScene) {
  let renderer: THREE.WebGLRenderer;
  try { renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' }); }
  catch { return null; }
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;
  const key = new THREE.DirectionalLight(0xffe6cc, 2.2); key.position.set(-1.2, 2.2, 1.6); scene.add(key);
  const ember = new THREE.PointLight(0xff5a14, 2.5, 4, 1.5); ember.position.set(0.6, 0.05, -0.5); scene.add(ember);
  const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 30);

  const tex = new THREE.TextureLoader();
  const load = (u: string) => { const t = tex.load(`${base}${u}`); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; };

  // ---- the box: thirteen parts, each with its exploded offset; clay first, scans after
  const box = new THREE.Group(); scene.add(box);
  type Part = { mesh: THREE.Mesh; home: THREE.Vector3; out: THREE.Vector3; real: THREE.Material | THREE.Material[] };
  const parts: Part[] = [];
  // clay is an overlay drawn just in front of the real surface, so texturing is a crossfade, not a swap
  const clay = new THREE.MeshStandardMaterial({ color: 0x8a817a, roughness: 0.75, metalness: 0, transparent: true, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
  const clayParts: THREE.Mesh[] = [];
  const flat = new THREE.MeshBasicMaterial({ color: 0x1fa6c4, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false });
  const joints = new Map<string, THREE.Vector3>();
  const realMats: THREE.MeshStandardMaterial[] = [];
  const flatParts: THREE.Mesh[] = [];
  let size = new THREE.Vector3(0.3, 0.2, 0.1), ready = false;

  const draco = new DRACOLoader().setDecoderPath(`${base}/draco/`);
  new GLTFLoader().setDRACOLoader(draco).loadAsync(`${base}${cfg.glb}`).then((g) => {
    const root = g.scene;
    const b = new THREE.Box3().setFromObject(root); size = b.getSize(new THREE.Vector3());
    const c = b.getCenter(new THREE.Vector3());
    root.position.sub(new THREE.Vector3(c.x, b.min.y, c.z));
    box.add(root); root.updateMatrixWorld(true);
    root.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const pc = new THREE.Box3().setFromObject(m).getCenter(new THREE.Vector3());
      const dir = pc.clone().sub(new THREE.Vector3(0, size.y * 0.45, 0));
      if (dir.lengthSq() < 1e-6) dir.set(0, 1, 0);
      dir.normalize().multiplyScalar(size.x * 0.3); dir.y *= 0.45; // spread mostly sideways, clear of the heading above
      parts.push({ mesh: m, home: m.position.clone(), out: dir, real: m.material });
      (Array.isArray(m.material) ? m.material : [m.material]).forEach((mm) => { if (!realMats.includes(mm as THREE.MeshStandardMaterial)) realMats.push(mm as THREE.MeshStandardMaterial); });
      const fc = new THREE.Mesh(m.geometry, flat); fc.visible = false; fc.renderOrder = 2; m.parent!.add(fc);
      fc.quaternion.copy(m.quaternion); fc.scale.copy(m.scale); flatParts.push(fc);
      const cc = new THREE.Mesh(m.geometry, clay); cc.renderOrder = 1; m.parent!.add(cc);
      cc.quaternion.copy(m.quaternion); cc.scale.copy(m.scale); clayParts.push(cc);
      const name = m.name || m.parent?.name || '';
      cfg.joints.forEach((j) => { if (name.startsWith(j) && !joints.has(j)) joints.set(j, pc); });
    });
    ready = true;
  });

  // ---- the photo and the session's crops, as cards in the scene
  const card = (url: string, h: number) => {
    const t = load(url);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: t, transparent: true, toneMapped: false, depthWrite: false }));
    t.addEventListener?.('load', () => {});
    m.userData.h = h;
    scene.add(m);
    return m;
  };
  const photo = card(cfg.photo, 0.13);
  const crops = cfg.crops.map((u) => card(u, 0.06));
  const mask = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: load(cfg.mask), color: 0xd23c41, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false, toneMapped: false }));
  scene.add(mask);
  // aspect from the textures once loaded
  const aspect = (m: THREE.Mesh) => { const im = ((m.material as THREE.MeshBasicMaterial).map?.image as HTMLImageElement | undefined); return im && im.width ? im.width / im.height : 1; };

  // ---- the two scans that were kept, as spheres
  const scans = cfg.scans.map((s) => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.045, 48, 32), new THREE.MeshStandardMaterial({ map: load(s.img), roughness: 0.8 }));
    scene.add(m); return m;
  });

  let s = 0, shown = 0, t0 = 0, spinAngle = 0;
  const az0 = THREE.MathUtils.degToRad(cfg.camera.azimuth), el0 = THREE.MathUtils.degToRad(cfg.camera.elevation);

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(canvas); resize();
  let visible = false;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(canvas);

  const clock = new THREE.Clock();
  const tgt = new THREE.Vector3(), pos = new THREE.Vector3();
  renderer.setAnimationLoop(() => {
    if (!visible) return;
    const dt = Math.min(0.05, clock.getDelta()); t0 += dt;
    // time-based smoothing: catches up in the same time whatever the frame rate
    shown = reduce ? s : lerp(shown, s, 1 - Math.exp(-dt * 7));
    const x = shown, H = size.y, L = size.x;
    const portrait = camera.aspect < 1;
    const cx = 0;

    // 1. read: exploded parts come home over the first step
    const ex = 1 - sm(0.15, 0.85, x);
    parts.forEach((p, i) => {
      p.mesh.position.copy(p.home).addScaledVector(p.out, ex * (1 + 0.15 * Math.sin(t0 * 0.8 + i)));
    });
    // 2. texture: the scans wrap the clay at 1.6; 3. measure: flat cyan for the silhouette
    const tex = sm(1.3, 1.8, x); // the scans' surface comes up through the clay
    const meas = bell(2.0, 3.0, x, 0.18); // 0..1, eased in and out: a crossfade, never a swap
    clay.opacity = 1 - tex;
    clayParts.forEach((c, i) => { c.visible = tex < 0.999; c.position.copy(parts[i].mesh.position); });
    realMats.forEach((m) => { m.transparent = meas > 0.001; m.opacity = 1 - meas; m.depthWrite = meas < 0.5; });
    flatParts.forEach((f, i) => { f.visible = meas > 0.001; f.position.copy(parts[i].mesh.position); });
    flat.opacity = 0.85 * meas;

    // box turn: slow spin, stopped for the measure and the joints
    const stop = sm(1.8, 2.05, x) * (1 - sm(3.95, 4.3, x)); // held still for the measure and the joints
    if (!reduce) spinAngle += dt * 0.25 * (1 - stop);
    const home = Math.round(spinAngle / (Math.PI * 2)) * Math.PI * 2;
    box.rotation.y = lerp(spinAngle, home, stop);
    box.position.set(cx * (1 - bell(2.0, 3.0, x, 0.1)), 0, 0);

    // camera: orbit framing; photo angle for the measure; dives for the joints
    const R = size.length() / 2, fovh = THREE.MathUtils.degToRad(camera.fov) / 2;
    const r = (R / Math.sin(fovh)) * (portrait ? 3.1 : 1.85);
    let az = az0 - 0.25 + Math.sin(t0 * 0.12) * 0.05, el = el0 + 0.06;
    // (meas, declared above, also steers the camera to the photo angle)
    az = lerp(az, az0, meas); el = lerp(el, el0, meas);
    pos.set(Math.sin(az) * Math.cos(el), Math.sin(el), Math.cos(az) * Math.cos(el)).multiplyScalar(r).add(new THREE.Vector3(box.position.x, H * 0.45, 0));
    tgt.set(box.position.x, H * 0.45, 0);
    const look = bell(2.9, 4.1, x, 0.38); // a long dive in and a long pull out: no cut
    if (look > 0 && joints.size) {
      const js = cfg.joints.map((n) => joints.get(n)).filter(Boolean) as THREE.Vector3[];
      const u = Math.min(js.length - 1, Math.max(0, ((x - 3.2) / 0.6) * (js.length - 1)));
      const i0 = Math.floor(u), i1 = Math.min(js.length - 1, i0 + 1), f = sm(0.2, 0.8, u - i0);
      const j = js.length ? js[i0].clone().lerp(js[i1], f) : null;
      if (j) {
        const jw = j.clone().applyMatrix4(box.matrixWorld);
        const near = jw.clone().add(new THREE.Vector3(Math.sin(az0), 0.45, Math.cos(az0)).normalize().multiplyScalar(R * (portrait ? 5.2 : 3.0)));
        pos.lerp(near, look); tgt.lerp(jw, look);
      }
    }
    camera.position.copy(pos); camera.lookAt(tgt);
    // composition: the text column owns the left on wide screens, so the scene is offset right and a
    // little down, clear of the heading; on phones it sits in the upper half, above the step card
    const W = canvas.clientWidth, Hh = canvas.clientHeight;
    if (W && Hh) {
      if (portrait) camera.setViewOffset(W, Hh, 0, Hh * 0.16, W, Hh);
      else camera.setViewOffset(W, Hh, -W * 0.17, -Hh * 0.06, W, Hh);
    }

    // photo and crops: on stage for the read, the photo returns as the red silhouette for the measure
    const read = bell(-0.2, 1.05, x, 0.18);
    const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0), up = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
    const centre = tgt.clone();
    photo.visible = false; // step 1 is geometry only in 3D: the photo and crops sit in the step text
    photo.position.copy(centre).addScaledVector(right, portrait ? L * 0.55 : L * 1.05).addScaledVector(up, portrait ? H * 0.95 : H * 0.35);
    photo.quaternion.copy(camera.quaternion);
    photo.scale.set(photo.userData.h * aspect(photo), photo.userData.h, 1).multiplyScalar(lerp(0.6, 1, read));
    (photo.material as THREE.MeshBasicMaterial).opacity = read;
    crops.forEach((c, i) => {
      const a = (i / crops.length) * Math.PI * 2 + t0 * 0.15;
      const v = bell(0.05 + i * 0.05, 1.05, x, 0.15);
      c.visible = false;
      c.position.copy(centre).addScaledVector(right, Math.cos(a) * L * 1.0).addScaledVector(up, Math.sin(a) * H * 1.15 + H * 0.05);
      c.quaternion.copy(camera.quaternion);
      c.scale.set(c.userData.h * aspect(c), c.userData.h, 1);
      (c.material as THREE.MeshBasicMaterial).opacity = v;
    });

    // scans orbit outside the box's bounding sphere while the step plays, then dissolve outward as their
    // surface comes up on the box: they never pass through it
    scans.forEach((m, i) => {
      const v = bell(0.95, 1.95, x, 0.2);
      m.visible = v > 0.01;
      const R0 = size.length() * 0.5 * 1.35 + 0.05;
      const a = i * Math.PI + t0 * 0.6;
      const out = 1 + 0.35 * tex;
      m.position.set(box.position.x + Math.cos(a) * R0 * out, H * 0.5 + Math.sin(a * 0.5) * H * 0.18, Math.sin(a) * R0 * out);
      m.scale.setScalar(Math.max(0.001, lerp(0.3, 1, v) * (1 - 0.6 * tex)));
      const mm = m.material as THREE.MeshStandardMaterial; mm.transparent = true; mm.opacity = v * (1 - tex * 0.85);
      m.rotation.y = t0;
    });

    // the measure: the photo's silhouette in red, sized to the box as the camera sees it
    mask.visible = meas > 0.001;
    (mask.material as THREE.MeshBasicMaterial).opacity = meas;
    if (mask.visible) {
      const bb = new THREE.Box3().setFromObject(box);
      const pts = [0, 1].flatMap((ix) => [0, 1].flatMap((iy) => [0, 1].map((iz) => new THREE.Vector3(ix ? bb.max.x : bb.min.x, iy ? bb.max.y : bb.min.y, iz ? bb.max.z : bb.min.z))));
      const cam = camera.matrixWorldInverse;
      const vs = pts.map((p) => p.clone().applyMatrix4(cam));
      const hx = Math.max(...vs.map((v) => v.x)) - Math.min(...vs.map((v) => v.x));
      const hy = Math.max(...vs.map((v) => v.y)) - Math.min(...vs.map((v) => v.y));
      const c = bb.getCenter(new THREE.Vector3());
      mask.position.copy(c).addScaledVector(camera.getWorldDirection(new THREE.Vector3()), L * 0.8);
      mask.quaternion.copy(camera.quaternion);
      mask.scale.set(Math.max(hx, hy * aspect(mask)) * 1.02, hy * 1.02, 1);
    }

    renderer.render(scene, camera);
  });

  return { setStep(v: number) { s = v; }, ready: () => ready };
}

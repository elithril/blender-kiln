import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

export interface Specimen { id: string; glb: string }

const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** The forge (a kiln-made GLB of the logo), its embers, and the objects that rise out of it.
 *  `progress` (0..1) is the scroll through the theatre; `windows` says when each specimen is on stage. */
export function mountForge(canvas: HTMLCanvasElement, base: string, specimens: Specimen[], windows: [number, number][]) {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  } catch {
    return null;
  }
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const dpr = Math.min(devicePixelRatio, 1.75);
  renderer.setPixelRatio(dpr);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0908);
  scene.fog = new THREE.Fog(0x0b0908, 6, 14);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.12; // the forge is the light; the room only keeps shadows from going flat

  const camera = new THREE.PerspectiveCamera(32, 1, 0.05, 40);

  // light: the fire inside, a cold rim from behind, a faint fill
  const fire = new THREE.PointLight(0xff6a1a, 26, 7, 1.6);
  fire.position.set(0, 0.95, 0);
  scene.add(fire);
  const rim = new THREE.DirectionalLight(0x6f86ff, 0.9);
  rim.position.set(-2.5, 3, -3);
  scene.add(rim);
  const fill = new THREE.DirectionalLight(0xffd2a8, 0.35);
  fill.position.set(2, 2, 3);
  scene.add(fill);
  // the stage light: a warm key and a cool rim that come up when an object has risen, so its real
  // textures read (the fire alone would only light it from below)
  const key = new THREE.SpotLight(0xffe2c4, 0, 12, 0.5, 0.6, 1.2);
  key.position.set(-2.2, 4.6, 3.4);
  key.target.position.set(0, 2.0, 0);
  scene.add(key, key.target);
  const back_ = new THREE.DirectionalLight(0xff8a3a, 0);
  back_.position.set(1.5, 2.5, -3);
  scene.add(back_);

  // floor that catches the firelight
  const fade = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 256;
    const g = c.getContext('2d')!; const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gr.addColorStop(0, 'rgba(255,255,255,0.9)'); gr.addColorStop(0.25, 'rgba(255,255,255,0.35)'); gr.addColorStop(0.6, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
    return new THREE.CanvasTexture(c);
  })();
  // the floor catches the firelight and dissolves into the night: no visible rim
  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(7, 64),
    new THREE.MeshStandardMaterial({ color: 0x15110e, roughness: 0.95, metalness: 0, alphaMap: fade, transparent: true, opacity: 0.7, depthWrite: false }),
  );
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);

  const forgeRoot = new THREE.Group();
  scene.add(forgeRoot);
  const stage = new THREE.Group(); // where specimens rise to
  scene.add(stage);

  // embers: additive points rising from the mouth, recycled
  const N = reduce ? 0 : 420;
  const pos = new Float32Array(N * 3), vel = new Float32Array(N * 3), life = new Float32Array(N);
  const spawn = (i: number) => {
    const a = Math.random() * Math.PI * 2, r = Math.random() * 0.3;
    pos[i * 3] = Math.cos(a) * r; pos[i * 3 + 1] = 1.05 + Math.random() * 0.1; pos[i * 3 + 2] = Math.sin(a) * r;
    vel[i * 3] = (Math.random() - 0.5) * 0.18; vel[i * 3 + 1] = 0.35 + Math.random() * 0.9; vel[i * 3 + 2] = (Math.random() - 0.5) * 0.18;
    life[i] = Math.random();
  };
  for (let i = 0; i < N; i++) { spawn(i); pos[i * 3 + 1] += Math.random() * 2.5; }
  const eg = new THREE.BufferGeometry();
  eg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const dot = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 64;
    const g = c.getContext('2d')!; const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,220,160,1)'); gr.addColorStop(0.35, 'rgba(255,120,30,0.8)'); gr.addColorStop(1, 'rgba(255,60,0,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
  })();
  const embers = new THREE.Points(eg, new THREE.PointsMaterial({ size: 0.05, map: dot, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: 0xffffff }));
  scene.add(embers);

  // post: bloom on what glows
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.55, 0.5, 0.82);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  const draco = new DRACOLoader().setDecoderPath(`${base}/draco/`);
  const loader = new GLTFLoader().setDRACOLoader(draco);
  const emissives: THREE.MeshStandardMaterial[] = [];

  loader.loadAsync(`${base}/assets/glb/forge.glb`).then((g) => {
    g.scene.traverse((o) => {
      const m = (o as THREE.Mesh).material as THREE.MeshStandardMaterial | undefined;
      if (m && m.emissive && m.emissiveIntensity > 0 && m.emissive.getHex() !== 0) { emissives.push(m); m.userData.base = m.emissiveIntensity * 0.5; m.toneMapped = true; }
      if (m) { m.flatShading = true; m.needsUpdate = true; }
    });
    forgeRoot.add(g.scene);
    ready();
  });

  // specimens, normalised to one height, hidden until their window
  const specs: { obj: THREE.Object3D; h: number }[] = [];
  specimens.forEach((s, i) => {
    loader.loadAsync(`${base}${s.glb}`).then((g) => {
      const o = g.scene;
      // one presence for every object: the same bounding-sphere radius, wide or tall
      const sphere = new THREE.Box3().setFromObject(o).getBoundingSphere(new THREE.Sphere());
      const k = 0.62 / sphere.radius;
      o.scale.setScalar(k);
      const b2 = new THREE.Box3().setFromObject(o), c = b2.getCenter(new THREE.Vector3());
      o.position.set(-c.x, -b2.min.y, -c.z);
      const holder = new THREE.Group(); holder.add(o); holder.visible = false;
      stage.add(holder);
      specs[i] = { obj: holder, h: b2.max.y - b2.min.y };
    });
  });

  let tail = 0, tailShown = 0, closing = 0, closeShown = 0, foot = 0, footShown = 0;
  let progress = 0, shown = 0, px = 0, py = 0, tx = 0, ty = 0;
  const onReady: (() => void)[] = [];
  let isReady = false;
  function ready() { isReady = true; onReady.forEach((f) => f()); }

  addEventListener('pointermove', (e) => { tx = (e.clientX / innerWidth - 0.5); ty = (e.clientY / innerHeight - 0.5); }, { passive: true });

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    composer.setSize(w, h);
    bloom.setSize(w * dpr, h * dpr);
    camera.aspect = w / h;
    camera.fov = w < h ? 44 : 32; // phones: wider lens so the forge fits
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(canvas);
  resize();

  let visible = true;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(canvas);

  const clock = new THREE.Clock();
  renderer.setAnimationLoop(() => {
    if (!visible) return;
    const dt = Math.min(0.05, clock.getDelta()), t = clock.elapsedTime;
    shown = reduce ? progress : lerp(shown, progress, 1 - Math.exp(-dt * 7));
    px = lerp(px, tx, 0.05); py = lerp(py, ty, 0.05);
    const p = shown;

    // tail: the rest of the page. The forge comes back up, banked low behind the sections, and flares
    // again for the close (tail 0..1 = scroll from the end of the theatre to the end of the page)
    tailShown = lerp(tailShown, tail, reduce ? 1 : 0.1);
    closeShown = lerp(closeShown, closing, reduce ? 1 : 0.1);
    footShown = lerp(footShown, foot, reduce ? 1 : 0.15);
    const tl = tailShown, back = smooth(0.0, 0.05, tl), close = smooth(0.25, 0.9, closeShown);
    const portrait = camera.aspect < 1;

    // camera: wide on the forge, then falls toward the mouth, then frames the stage above it
    const dive = smooth(0.0, 0.22, p) * (1 - back), rise = smooth(0.18, 0.34, p) * (1 - back);
    const camY = lerp(lerp(1.55, 1.9, dive), 2.35, rise);
    const camZ = lerp(lerp(4.9, 3.0, dive), 3.2, rise);
    camera.position.set(px * 0.35 + Math.sin(t * 0.15) * 0.05, camY - py * 0.2, camZ);
    camera.lookAt(0, lerp(lerp(1.35, 1.05, dive), portrait ? 1.45 : 2.1, rise), 0); // phones: object high, clear of the chip and reading
    // hero composition: the forge stands clear of the type, right of it on wide screens and below it on
    // phones; the offset melts away as the camera dives, and comes back for the close
    const W = canvas.clientWidth, H = canvas.clientHeight;
    const off = Math.max(1 - smooth(0.02, 0.16, p), close);
    if (W && H) {
      if (portrait) camera.setViewOffset(W, H, 0, -H * 0.24 * off + H * (0.02 * close + 0.7 * footShown), W, H); // phones: the footer lies over the base, the flame stays under the links
      // at the close the forge rides higher, its base clear of the footer below it
      else camera.setViewOffset(W, H, -W * 0.22 * off, H * (0.04 * off + 0.17 * close + footShown), W, H);
    }

    // the forge sinks out of frame once the object is up, is hidden while the objects are on stage
    // (so it never pokes under the type), and rises back for the tail
    const sunk = smooth(0.3, 0.42, p) * (1 - back);
    const banks = back * (1 - close); // behind the data sections only its crown glows, at the bottom edge
    forgeRoot.position.y = lerp(0, portrait ? -1.6 : -1.0, sunk) - (portrait ? 1.4 : 2.1) * banks;
    forgeRoot.visible = sunk < 0.98;
    forgeRoot.rotation.y = t * 0.06;
    const banked = lerp(1, 0.5, back * (1 - close)); // embers and heat behind the reading sections
    const flare = (1 + 0.7 * Math.exp(-Math.pow((p - 0.24) / 0.05, 2))) * banked * (1 + 0.5 * close);
    const flicker = reduce ? 1 : 0.9 + 0.1 * Math.sin(t * 7.3) * Math.sin(t * 3.1);
    for (const m of emissives) m.emissiveIntensity = m.userData.base * flare * flicker;
    fire.intensity = 26 * flare * flicker;
    fire.position.y = 0.95 + forgeRoot.position.y;
    bloom.strength = (0.55 + 0.3 * Math.max(0, flare - 1) / 0.7) * lerp(1, 0.75, back * (1 - close));
    key.intensity = (portrait ? 140 : 90) * rise; back_.intensity = 1.6 * rise;
    scene.environmentIntensity = 0.12 + 0.38 * rise * (1 - back);
    (embers.material as THREE.PointsMaterial).opacity = 1 - 0.6 * rise;

    // specimens: each rises out of the fire inside its window and sinks back after
    stage.position.y = 1.55;
    specs.forEach((s, i) => {
      if (!s) return;
      const [a, b] = windows[i];
      const inn = smooth(a, a + 0.06, p), out = 1 - smooth(b - 0.06, b, p);
      const v = Math.min(inn, out) * (1 - back);
      s.obj.visible = v > 0.001;
      s.obj.position.y = lerp(portrait ? -0.45 : -1.3, 0, v); // phones: a short rise, so it never passes under the readout below it
      s.obj.scale.setScalar(lerp(0.35, 1, v) * (portrait ? 0.72 : 1));
      s.obj.rotation.y = t * 0.35 + p * 9;
    });

    // embers
    if (N) {
      for (let i = 0; i < N; i++) {
        life[i] += dt * 0.35;
        pos[i * 3] += vel[i * 3] * dt + Math.sin(t + i) * 0.002;
        pos[i * 3 + 1] += vel[i * 3 + 1] * dt * flare * 0.8;
        pos[i * 3 + 2] += vel[i * 3 + 2] * dt;
        if (pos[i * 3 + 1] > 4.2 || life[i] > 1) { spawn(i); life[i] = 0; pos[i * 3 + 1] += forgeRoot.position.y; }
      }
      eg.attributes.position.needsUpdate = true;
    }

    composer.render();
  });

  return {
    setProgress(v: number) { progress = v; },
    setTail(v: number) { tail = v; },
    setClose(v: number) { closing = v; },
    /** share of the viewport the footer covers: the forge rises by exactly that much */
    setFoot(v: number) { foot = v; },
    whenReady(f: () => void) { isReady ? f() : onReady.push(f); },
  };
}

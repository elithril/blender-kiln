import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { clone as cloneSkinned } from 'three/examples/jsm/utils/SkeletonUtils.js';

/** kiln's animated GLBs, played live: one at a time on an ember-lit floor, crossfaded on change. */
export function mountCreatures(canvas: HTMLCanvasElement, base: string) {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  } catch {
    return null;
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.35;
  const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 50);

  const key = new THREE.SpotLight(0xffe6cc, 60, 20, 0.55, 0.7, 1.4);
  key.position.set(-2.5, 5, 3.5);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.bias = -0.0004;
  scene.add(key, key.target);
  const ember = new THREE.PointLight(0xff5a14, 14, 6, 1.6);
  ember.position.set(1.4, 0.4, -1.2);
  scene.add(ember);
  const rim = new THREE.DirectionalLight(0x7f95ff, 0.8);
  rim.position.set(2, 3, -4);
  scene.add(rim);

  const floor = new THREE.Mesh(new THREE.CircleGeometry(6, 64), new THREE.ShadowMaterial({ opacity: 0.55 }));
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  const draco = new DRACOLoader().setDecoderPath(`${base}/draco/`);
  const loader = new GLTFLoader().setDRACOLoader(draco);
  const cache = new Map<string, Promise<{ scene: THREE.Object3D; clip: THREE.AnimationClip | undefined }>>();
  const load = (url: string) => {
    if (!cache.has(url)) cache.set(url, loader.loadAsync(url).then((g) => ({ scene: g.scene, clip: g.animations[0] })));
    return cache.get(url)!;
  };

  let current: { root: THREE.Group; mixer: THREE.AnimationMixer; r: number; model: string; action: THREE.AnimationAction | null } | null = null;
  let outgoing: { root: THREE.Group; t: number } | null = null;
  let ticket = 0, radius = 1, spin = 0;

  /** `model` names the rig: two clips of the same model (villager walk and jump, cat walk and idle)
   *  share their bones, so the change is a crossfade on the model already on stage, not a swap. */
  async function show(url: string, model: string) {
    const t = ++ticket;
    const { scene: src, clip } = await load(url);
    if (t !== ticket) return;
    if (current && current.model === model && clip) {
      const next = current.mixer.clipAction(clip);
      next.reset().play();
      if (current.action && current.action !== next) current.action.crossFadeTo(next, 0.45, false);
      current.action = next;
      return;
    }
    const obj = cloneSkinned(src); // a plain clone keeps the skin bound to the source skeleton: it would never move
    obj.traverse((o) => { if ((o as THREE.Mesh).isMesh) { o.castShadow = true; (o as THREE.Mesh).frustumCulled = false; } });
    const holder = new THREE.Group();
    holder.add(obj);
    // fit on the envelope of the whole clip (skinned positions, sampled), not the rest pose:
    // a walk or a wing flap reaches well outside its T-pose
    const mixer = new THREE.AnimationMixer(obj);
    const action = clip ? mixer.clipAction(clip) : null;
    action?.play();
    const env = new THREE.Box3();
    const steps = clip ? 10 : 1;
    for (let k = 0; k < steps; k++) {
      if (clip) mixer.setTime((clip.duration * k) / steps);
      obj.updateMatrixWorld(true);
      env.union(new THREE.Box3().setFromObject(obj, true));
    }
    if (clip) mixer.setTime(0);
    const size = env.getSize(new THREE.Vector3());
    const k = 1.6 / Math.max(size.y, size.x * 0.75, size.z * 0.75);
    obj.scale.setScalar(k);
    const c = env.getCenter(new THREE.Vector3());
    obj.position.set(-c.x * k, -env.min.y * k, -c.z * k);
    const fitR = Math.max(size.y, Math.hypot(size.x, size.z)) * k * 0.5;
    // a model still on its way out is dropped now: overwritten, it would stay on stage for good
    if (outgoing) { scene.remove(outgoing.root); outgoing = null; }
    if (current) outgoing = { root: current.root, t: 0 };
    holder.scale.setScalar(0.001);
    scene.add(holder);
    current = { root: holder, mixer, r: size.y * k, model, action };
    radius = fitR;
  }

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(canvas);
  resize();

  let visible = false;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(canvas);
  let dragging = false, lastX = 0, idle = 0;
  canvas.addEventListener('pointerdown', (e) => { dragging = true; lastX = e.clientX; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', (e) => { if (dragging) { spin += (e.clientX - lastX) * 0.01; lastX = e.clientX; } });
  canvas.addEventListener('pointerup', () => { dragging = false; idle = performance.now(); });

  const clock = new THREE.Clock();
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  renderer.setAnimationLoop((now) => {
    const dt = Math.min(0.05, clock.getDelta());
    if (!visible) return;
    if (current) {
      current.mixer.update(reduce ? 0 : dt);
      const s = current.root.scale.x;
      current.root.scale.setScalar(s + (1 - s) * 0.12);
      if (!dragging && now - idle > 1500 && !reduce) spin += dt * 0.25;
      current.root.rotation.y = -0.5 + spin;
    }
    if (outgoing) {
      outgoing.t += dt * 3;
      outgoing.root.scale.setScalar(Math.max(0.001, 1 - outgoing.t));
      outgoing.root.position.y = -outgoing.t * 0.3;
      if (outgoing.t >= 1) { scene.remove(outgoing.root); outgoing = null; }
    }
    const h = current ? current.r : 1;
    const fov = THREE.MathUtils.degToRad(camera.fov);
    const dist = (radius * 1.15) / Math.sin(fov / 2) / Math.min(1, camera.aspect);
    camera.position.set(0, h * 0.5 + dist * 0.22, dist);
    camera.lookAt(0, h * 0.5, 0);
    key.target.position.set(0, h * 0.4, 0);
    ember.intensity = 14 * (0.85 + 0.15 * Math.sin(now * 0.006) * Math.sin(now * 0.0023));
    renderer.render(scene, camera);
  });

  return { show };
}

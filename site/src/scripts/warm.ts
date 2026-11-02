import type * as THREE from 'three';

/** Prepares a freshly loaded model before it first shows: uploads its textures and compiles its shaders in
 *  the background (KHR_parallel_shader_compile). Left to the first frame it appears in, that work stalls
 *  the page 30-75 ms on a Mac, measured, and longer on a weaker machine. Hidden parts are included: the
 *  compiler only walks what is visible, so they are shown for the synchronous walk and hidden again at once.
 *  `target`: where the scene really draws. A composer's target compiles other shaders than the canvas (no tone
 *  mapping, linear colour), and warming the wrong ones leaves the real ones to the first frame. */
export function warm(renderer: THREE.WebGLRenderer, root: THREE.Object3D, camera: THREE.Camera, scene: THREE.Scene, target: THREE.WebGLRenderTarget | null = null) {
  const hidden: THREE.Object3D[] = [];
  root.traverse((o) => {
    if (!o.visible) { hidden.push(o); o.visible = true; }
    const m = (o as THREE.Mesh).material;
    if (!m) return;
    for (const mm of Array.isArray(m) ? m : [m])
      for (const v of Object.values(mm)) if ((v as THREE.Texture)?.isTexture && (v as THREE.Texture).image) renderer.initTexture(v as THREE.Texture);
  });
  const prev = renderer.getRenderTarget();
  renderer.setRenderTarget(target);
  const done = renderer.compileAsync(root, camera, scene).catch(() => {});
  renderer.setRenderTarget(prev);
  hidden.forEach((o) => { o.visible = false; });
  return done;
}

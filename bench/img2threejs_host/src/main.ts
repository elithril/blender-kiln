// Bench host for img2threejs. The session writes src/model.ts exporting
// `createModel(): THREE.Group` (or a default export). This page only frames and
// lights it — the same way for every subject — and exposes a GLB export the
// bench calls afterwards, so no session is asked to do the conversion itself.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFExporter } from "three/examples/jsm/exporters/GLTFExporter.js";
import * as M from "./model";

const factory: any = (M as any).createModel ?? (M as any).default ??
  Object.values(M).find((v) => typeof v === "function");
const model: THREE.Object3D = factory();

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(1);
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x2b2d31);
scene.add(new THREE.HemisphereLight(0xffffff, 0x404050, 1.6));
const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(3, 5, 4); scene.add(key);
scene.add(model);

const box = new THREE.Box3().setFromObject(model);
const size = box.getSize(new THREE.Vector3()).length() || 1;
const center = box.getCenter(new THREE.Vector3());
const camera = new THREE.PerspectiveCamera(35, innerWidth / innerHeight, size / 100, size * 100);
camera.position.copy(center).add(new THREE.Vector3(0.9, 0.55, 1.2).multiplyScalar(size * 1.1));
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(center); controls.update();
renderer.setAnimationLoop((t) => { (model as any).userData?.tick?.(t / 1000); renderer.render(scene, camera); });

(window as any).__exportGLB = () => new Promise((resolve, reject) =>
  new GLTFExporter().parse(model, (buf) => resolve(Array.from(new Uint8Array(buf as ArrayBuffer))),
    reject, { binary: true, onlyVisible: true }));
(window as any).__ready = true;

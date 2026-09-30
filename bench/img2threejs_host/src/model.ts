// Placeholder: the session replaces this file with the reconstruction.
import * as THREE from "three";
export function createModel(): THREE.Group {
  const g = new THREE.Group();
  g.add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ color: 0x888888 })));
  return g;
}

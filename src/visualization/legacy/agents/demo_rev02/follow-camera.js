import * as DefaultTHREE from 'three';

/**
 * Camera-only tracking; actor states and trajectories are never changed.
 * World convention: metres, Y up, heading 0 = +Z, heading PI/2 = +X.
 * Call update(state, deltaSeconds) before the render loop's controls.update().
 * A null state retains the selected ID and stops camera tracking until it returns.
 */
export function createFollowCamera({camera, controls, THREE = DefaultTHREE, onModeChange = () => {}}) {
  if (!camera?.position || !controls?.target) throw new TypeError('A camera and OrbitControls are required');
  const profiles = {
    car: {distance: 12, height: 8, targetHeight: .8, jumpDistance: 80},
    uav: {distance: 25, height: 15, targetHeight: .5, jumpDistance: 100},
    bird: {distance: 5, height: 1.7, targetHeight: 0, jumpDistance: 60},   // close enough to see the pigeon's wing beat (0.66 m wingspan)
  };
  let selected = null, mode = 'orbit', latest = null, anchor = null;
  let available = false, pendingReframe = false, heading = 0, disposed = false;
  const desiredEye = new THREE.Vector3(), desiredTarget = new THREE.Vector3();
  const displacement = new THREE.Vector3();
  const angle = value => Math.atan2(Math.sin(value), Math.cos(value));

  function readState(state) {
    if (state == null) return null;
    if (!['x', 'y', 'z'].every(k => Number.isFinite(state[k])) ||
        (state.headingRadians !== undefined && !Number.isFinite(state.headingRadians))) {
      throw new TypeError('Follow state needs finite world coordinates and heading');
    }
    return {x: state.x, y: state.y, z: state.z,
      headingRadians: angle(state.headingRadians ?? 0), airborne: !!state.airborne};
  }

  function setDesired(state, yaw = state.headingRadians) {
    const p = profiles[selected.kind];
    desiredTarget.set(state.x, state.y + p.targetHeight, state.z);
    desiredEye.set(state.x - Math.sin(yaw) * p.distance,
      state.y + p.height, state.z - Math.cos(yaw) * p.distance);
  }

  function reframe(state) {
    heading = state.headingRadians; setDesired(state);
    camera.position.copy(desiredEye); controls.target.copy(desiredTarget);
    anchor = new THREE.Vector3(state.x, state.y, state.z);
    pendingReframe = false;
  }

  function changeMode(next, reason) {
    if (next !== 'orbit' && next !== 'behind') throw new TypeError('Unknown follow camera mode');
    if (mode === next) return;
    mode = next;
    // Re-entering behind mode eases from the user's present view on the next tick.
    if (latest) heading = latest.headingRadians;
    onModeChange(mode, {reason, selection: selected ? {...selected} : null});
  }

  const onControlsStart = () => {
    if (!disposed && selected && mode === 'behind') changeMode('orbit', 'user-interaction');
  };
  controls.addEventListener?.('start', onControlsStart);

  return {
    select(selection, state = null) {
      if (disposed) throw new Error('Follow camera has been disposed');
      if (!selection || !['car', 'uav', 'bird'].includes(selection.kind) ||
          !['string', 'number'].includes(typeof selection.id) ||
          (typeof selection.id === 'number' && !Number.isFinite(selection.id)) ||
          (typeof selection.id === 'string' && !selection.id.length)) {
        throw new TypeError('Select a car, UAV or bird using its real ID');
      }
      const next = readState(state);
      selected = {kind: selection.kind, id: selection.id};
      latest = next; available = !!next; anchor = null; pendingReframe = true;
      if (next) {reframe(next); controls.update?.();}
      return this.getState();
    },

    setMode(next) {
      if (disposed) throw new Error('Follow camera has been disposed');
      changeMode(next, 'mode-selection');
      return mode;
    },

    update(state, deltaSeconds = 1 / 60, {discontinuous = false} = {}) {
      if (disposed || !selected) return false;
      const next = readState(state);
      if (!next) {
        available = false; latest = null; pendingReframe = true;
        return false;
      }
      const hadState = available; available = true; latest = next;
      const p = profiles[selected.kind];
      const jump = anchor ? Math.hypot(next.x - anchor.x, next.y - anchor.y, next.z - anchor.z) : Infinity;
      const snap = !!discontinuous || pendingReframe || !hadState || jump > p.jumpDistance;
      if (snap) {
        if (mode === 'orbit' && anchor && hadState && !pendingReframe) {
          // A seek keeps the user's orbit angle/zoom, moving instantly to the ID.
          displacement.set(next.x - anchor.x, next.y - anchor.y, next.z - anchor.z);
          camera.position.add(displacement); controls.target.add(displacement);
          anchor.set(next.x, next.y, next.z); heading = next.headingRadians;
        } else reframe(next);
        return true;
      }
      if (mode === 'orbit') {
        displacement.set(next.x - anchor.x, next.y - anchor.y, next.z - anchor.z);
        camera.position.add(displacement); controls.target.add(displacement);
      } else {
        const dt = Number.isFinite(deltaSeconds) ? Math.max(0, Math.min(.25, deltaSeconds)) : 1 / 60;
        heading += angle(next.headingRadians - heading) * (1 - Math.exp(-8 * dt));
        setDesired(next, heading);
        const alpha = 1 - Math.exp(-6 * dt);
        camera.position.lerp(desiredEye, alpha); controls.target.lerp(desiredTarget, alpha);
      }
      anchor.set(next.x, next.y, next.z);
      return true;
    },

    clear() {
      selected = null; latest = null; anchor = null;
      available = false; pendingReframe = false;
    },

    getState() {
      return {selection: selected ? {...selected} : null, mode,
        targetAvailable: available, awaitingTarget: !!selected && !available};
    },

    dispose() {
      this.clear(); controls.removeEventListener?.('start', onControlsStart); disposed = true;
    },
  };
}

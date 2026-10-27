/** Sample recorded SUMO positions without future-window smoothing or invented gaps. */
export function recordedSampler(frames, dt, maxSpeed = 55) {
  if (!(dt > 0) || !frames.length) throw new Error('Invalid recorded timeline');
  const indices = frames.map((frame) => new Map(Array.from(frame.idx, (id, i) => [id, i])));
  return function sample(time) {
    const t = Math.max(0, Math.min(time, (frames.length - 1) * dt));
    const a = Math.floor(t / dt),
      fraction = t / dt - a;
    const first = frames[a],
      second = frames[a + 1];
    const result = [];
    for (let i = 0; i < first.idx.length; i++) {
      const id = first.idx[i];
      let [x, y, heading] = first.xyh.slice(i * 3, i * 3 + 3);
      if (fraction > 1e-9) {
        const j = indices[a + 1]?.get(id);
        // An absent vehicle or a teleport is not a continuous trajectory.
        if (j === undefined) continue;
        const [nx, ny, nh] = second.xyh.slice(j * 3, j * 3 + 3);
        if (Math.hypot(nx - x, ny - y) > maxSpeed * dt) continue;
        x += (nx - x) * fraction;
        y += (ny - y) * fraction;
        heading += Math.atan2(Math.sin(nh - heading), Math.cos(nh - heading)) * fraction;
      }
      result.push({ id, x, y, heading });
    }
    return result;
  };
}
export function advancePlayback(time, elapsed, speed, duration) {
  return Math.min(duration, Math.max(0, time + Math.max(0, elapsed) * speed));
}

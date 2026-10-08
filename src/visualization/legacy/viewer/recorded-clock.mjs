// Legacy scenes start at one step interval; recorded adapters may start at t=0.
export function timelineTime(timeline, step) {
  return (timeline.t0_s ?? timeline.step_s) + (step - 1) * timeline.step_s;
}
export function layerSpan(timeline, layer) {
  const startTime = timelineTime(timeline, 1);
  return {
    start: Math.max(1, 1 + Math.ceil((layer.t0_s - startTime) / timeline.step_s - 1e-6)),
    end: Math.min(timeline.steps, 1 + Math.floor((layer.t0_s + (layer.frames - 1) * layer.step_s - startTime) / timeline.step_s + 1e-6)),
  };
}

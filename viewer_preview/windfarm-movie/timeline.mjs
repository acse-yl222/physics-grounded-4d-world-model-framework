// Saved physical times are authoritative; never infer them from frame indices.
export function createTimeline(times) {
  if (!Array.isArray(times) || !times.length || times.some((t, i) =>
    !Number.isFinite(t) || (i > 0 && t <= times[i - 1]))) {
    throw new Error('Wind frames require finite, strictly increasing saved times');
  }
  const samples = [...times], start = samples[0], end = samples.at(-1);
  return {
    start, end, duration: end - start,
    sample(time) {
      if (!Number.isFinite(time)) throw new Error('Wind playback time must be finite');
      if (time <= start) return {a: 0, b: 0, mix: 0};
      if (time >= end) return {a: samples.length - 1, b: samples.length - 1, mix: 0};
      let low = 0, high = samples.length - 1;
      while (high - low > 1) {
        const middle = (low + high) >> 1;
        if (samples[middle] <= time) low = middle; else high = middle;
      }
      return {a: low, b: high, mix: (time - samples[low]) / (samples[high] - samples[low])};
    },
    advance(time, elapsed, rate) {
      if (![time, elapsed, rate].every(Number.isFinite) || elapsed < 0 || rate < 0)
        throw new Error('Invalid playback advance');
      if (end === start) return start;
      return start + (((time - start + elapsed * rate) % (end - start)) + end - start) % (end - start);
    }
  };
}

export function sample(values, times, seconds, mode) {
  if (mode === 'static') return values;
  if (!Number.isFinite(seconds) || !times.length || seconds < times[0] || seconds > times.at(-1))
    return null;
  let lo = 0,
    hi = times.length - 1;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (times[mid] <= seconds) lo = mid;
    else hi = mid - 1;
  }
  if (mode === 'step' || lo === times.length - 1 || times[lo] === seconds) return values[lo];
  if (mode !== 'linear') throw new Error(`Unsupported sampling: ${mode}`);
  const weight = (seconds - times[lo]) / (times[lo + 1] - times[lo]);
  const blend = (a, b) =>
    Array.isArray(a) ? a.map((v, i) => blend(v, b[i])) : a + (b - a) * weight;
  return blend(values[lo], values[lo + 1]);
}
export const enuToWorld = ([x, y, z]) => [x, z, -y];
export const worldToEnu = ([x, y, z]) => [x, -z, y];
export function assetURL(base, asset) {
  if (
    typeof asset !== 'string' ||
    !asset ||
    asset.startsWith('/') ||
    /[:\\%?#]/.test(asset) ||
    asset.split('/').includes('..')
  )
    throw new Error('Asset must be a plain relative path within its run');
  return new URL(asset, base).href;
}
export function sampleTrajectories(frames, times, seconds, mode) {
  if (!Number.isFinite(seconds) || !times.length || seconds < times[0] || seconds > times.at(-1))
    return null;
  let lo = 0,
    hi = times.length - 1;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (times[mid] <= seconds) lo = mid;
    else hi = mid - 1;
  }
  const a = frames[lo];
  if (mode === 'step' || lo === times.length - 1 || seconds === times[lo]) return a;
  if (mode !== 'linear') throw new Error('Unsupported trajectory sampling');
  const b = frames[lo + 1],
    next = new Map(b.ids.map((id, i) => [id, b.positions[i]])),
    weight = (seconds - times[lo]) / (times[lo + 1] - times[lo]);
  return {
    ids: a.ids,
    positions: a.positions.map((position, i) => {
      const end = next.get(a.ids[i]);
      return end ? position.map((v, k) => v + (end[k] - v) * weight) : position;
    }),
  };
}

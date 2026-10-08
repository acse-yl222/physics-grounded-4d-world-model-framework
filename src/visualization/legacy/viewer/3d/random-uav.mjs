// Independent random walks on directed Wave PDE paths. No orders or scheduler.
export function randomFlights(routes, { count = 300, seed = 20261007, duration = 3600 } = {}) {
  if (!routes.length || !Number.isInteger(count) || count < 1 || count > 300)
    throw Error('Invalid random UAV configuration');
  let state = seed >>> 0;
  const random = () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
  const outgoing = new Map();
  for (const r of routes) {
    if (
      !(r.duration_s > 0) ||
      r.points_m.length !== r.times_s.length ||
      r.times_s[0] !== 0 ||
      r.times_s.some((t, i) => !Number.isFinite(t) || (i && t <= r.times_s[i - 1]))
    )
      throw Error('Invalid route timing');
    if (!outgoing.has(r.from_station)) outgoing.set(r.from_station, []);
    outgoing.get(r.from_station).push(r);
  }
  for (const r of routes)
    if (!outgoing.has(r.to_station)) throw Error('Route destination has no outgoing flight');
  const origins = [...outgoing.keys()];
  const flights = [];
  for (let id = 0; id < count; id++) {
    let from = origins[Math.floor(random() * origins.length)],
      t = 0;
    const legs = [];
    while (t < duration) {
      const choices = outgoing.get(from),
        route = choices[Math.floor(random() * choices.length)];
      if (!legs.length) t = -random() * route.duration_s;
      legs.push({ start: t, end: t + route.duration_s, route });
      t += route.duration_s;
      from = route.to_station;
    }
    flights.push(legs);
  }
  function sample(t) {
    t = Math.max(0, Math.min(duration - 1e-6, t));
    return flights.map((legs, id) => {
      const leg = legs.find((l) => t >= l.start && t < l.end),
        r = leg.route,
        elapsed = t - leg.start;
      let lo = 0,
        hi = r.times_s.length - 1;
      while (lo + 1 < hi) {
        const mid = (lo + hi) >> 1;
        if (r.times_s[mid] <= elapsed) lo = mid;
        else hi = mid;
      }
      const a = r.points_m[lo],
        b = r.points_m[hi],
        f = (elapsed - r.times_s[lo]) / (r.times_s[hi] - r.times_s[lo]);
      return {
        idIndex: id,
        x: a[0] + (b[0] - a[0]) * f,
        y: a[1] + (b[1] - a[1]) * f,
        z: a[2] + (b[2] - a[2]) * f,
        headingRadians: Math.atan2(b[0] - a[0], b[2] - a[2]),
        airborne: true,
        station: null,
        from: r.from_station,
        to: r.to_station,
        activity: 'RANDOM_FLIGHT',
        color: '#4f8cff',
        opacity: 1,
        visible: true,
      };
    });
  }
  return { sample, flights, duration, count, seed };
}

export async function loadRandomUav(url, options = {}) {
  const response = await fetch(url);
  if (!response.ok) throw Error(`Wave PDE routes: ${response.status}`);
  const data = await response.json();
  if (
    data.schema_version !== 'wavepde-uav-preview-1' ||
    data.dtype !== '<f4' ||
    data.coordinate_frame !== 'world-y-up'
  )
    throw Error('Unsupported Wave PDE route export');
  const r = await fetch(new URL(data.binary, url));
  if (!r.ok) throw Error('Wave PDE route binary unavailable');
  const buffer = await r.arrayBuffer();
  if (buffer.byteLength % 16) throw Error('Truncated route records');
  const view = new DataView(buffer),
    records = buffer.byteLength / 16;
  const routes = data.routes.map((route) => {
    if (
      !Number.isInteger(route.offset_records) ||
      !Number.isInteger(route.count) ||
      route.count < 2 ||
      route.offset_records < 0 ||
      route.offset_records + route.count > records
    )
      throw Error('Invalid route bounds');
    const points_m = [],
      times_s = [];
    for (let i = 0; i < route.count; i++) {
      const o = (route.offset_records + i) * 16;
      const p = [0, 4, 8].map((k) => view.getFloat32(o + k, true));
      const t = view.getFloat32(o + 12, true);
      if (!p.every(Number.isFinite) || !Number.isFinite(t)) throw Error('Invalid route sample');
      points_m.push(p);
      times_s.push(t);
    }
    return { ...route, points_m, times_s };
  });
  return {
    stations: data.stations,
    routes,
    model: randomFlights(routes, {
      count: data.uav_count,
      seed: data.seed,
      duration: data.duration_s,
      ...options,
    }),
    metadata: data,
  };
}

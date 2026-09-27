// Parking is a display allocation inside the already certified Hub footprint.
// It does not change the scheduler's station, time, owner or energy records.
export function allocateHubParking(replay, stations, parking, bayLibrary) {
  const hubs = new Set(stations.filter(s => s.role === 'hub').map(s => s.station_id));
  const stays = [], byUav = new Map();
  for (const u of replay.uavs) {
    let station = u.birth_station, start = 0, arrival = null;
    const own = []; byUav.set(u.id, own);
    const add = (end, departure) => {
      if (!hubs.has(station)) return;
      const stay = {uav: u.id, station, start, end, arrival, departure, offset: null};
      stays.push(stay); own.push(stay);
    };
    for (const segment of u.segments) {
      if (segment.from_station === segment.to_station) continue;
      add(segment.t0_s, segment);
      station = segment.to_station; start = segment.t1_s; arrival = segment;
    }
    add(replay.metadata.duration_s, null);
  }
  if (bayLibrary?.status !== 'PASS_STATIC_VISUAL_ENDPOINT_GEOMETRY') throw new Error('Hub flight endpoints have not passed geometry checks');
  const slotsByHub = new Map(bayLibrary.hubs.map(h => [h.station_id, h.slots.map(s => s.offset_from_station_m)]));
  for (const p of parking) {
    const offset = slotsByHub.get(p.hub_station_id)?.[p.uav_id % 100];
    if (!offset || offset.some((v, i) => v !== p.offset_from_station_m[i])) throw new Error('Initial Hub positions must remain unchanged');
  }
  const active = new Map([...hubs].map(h => [h, []]));
  let overflowStays = 0;
  const maximum = Object.fromEntries([...hubs].map(h => [h, 0]));
  for (const stay of stays.sort((a, b) => a.start - b.start || a.uav - b.uav)) {
    const slots = slotsByHub.get(stay.station);
    if (!slots?.length) throw new Error(`Missing certified flight endpoints for Hub ${stay.station}`);
    const remaining = active.get(stay.station).filter(s => s.end > stay.start);
    const used = new Set(remaining.map(s => s.slot));
    const preferred = stay.uav % 100;
    const slot = !used.has(preferred) ? preferred : slots.findIndex((_, i) => !used.has(i));
    stay.slot = slot; stay.offset = slot < 0 ? [0, 0, 0] : slots[slot];
    if (slot < 0) overflowStays++;
    if (stay.end > stay.start) remaining.push(stay);
    active.set(stay.station, remaining); maximum[stay.station] = Math.max(maximum[stay.station], remaining.length);
    if (stay.arrival) { stay.arrival._arrivalOffset = stay.offset; stay.arrival._fadeIntoHub = true; }
    if (stay.departure) { stay.departure._departureOffset = stay.offset; stay.departure._fadeOutOfHub = !!stay.arrival; }
  }
  return {
    offset(uav, station, t) {
      return byUav.get(uav)?.find(s => s.station === station && s.start <= t && (t < s.end || t === replay.metadata.duration_s && t === s.end))?.offset ?? [0, 0, 0];
    },
    isReturnedStay(uav, station, t) {
      return !!byUav.get(uav)?.find(s => s.station === station && s.arrival && s.start <= t && (t < s.end || t === replay.metadata.duration_s && t === s.end));
    },
    audit: {maximum_stationary_at_hub: maximum, overflow_stays: overflowStays,
      endpoint_capacity: Object.fromEntries([...slotsByHub].map(([h, slots]) => [h, slots.length])),
      meaning: 'Visual flight endpoint allocation only. Returned aircraft are hidden while at Hub; initial positions remain visible. Rooftop stationary aircraft are aggregated.'},
  };
}

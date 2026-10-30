/** Select existing computed paths only; keep a bidirectional connected station ring. */
export function selectFlightNetwork(routes, limit) {
  if (limit == null || limit >= routes.length) return routes;
  const ids = [...new Set(routes.flatMap(r => [r.from_station, r.to_station]))].sort();
  if (!Number.isInteger(limit) || limit < 2 * ids.length) throw Error('Route limit cannot cover a bidirectional station ring');
  const byPair = new Map(routes.map(r => [`${r.from_station}\0${r.to_station}`, r]));
  const chosen = new Set();
  const add = (a,b) => { const r=byPair.get(`${a}\0${b}`); if(!r)throw Error('Requested connected network requires missing computed route');chosen.add(r); };
  for(let i=0;i<ids.length;i++){const a=ids[i],b=ids[(i+1)%ids.length];add(a,b);add(b,a);}
  const sorted=[...routes].sort((a,b)=>a.duration_s-b.duration_s || `${a.from_station}/${a.to_station}`.localeCompare(`${b.from_station}/${b.to_station}`));
  for(const r of sorted){if(chosen.size>=limit)break;chosen.add(r);}
  return routes.filter(r=>chosen.has(r));
}

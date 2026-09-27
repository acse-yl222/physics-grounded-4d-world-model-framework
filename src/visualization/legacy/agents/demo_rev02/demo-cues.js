// Presentation bookmarks from the released result; they only seek the replay.
export function installDemoCues({element, cues, replay, onChoose}) {
  if (cues?.source?.result_sha256 !== replay?.metadata?.result_sha256) {
    throw new Error('Presentation bookmarks refer to a different scheduling result');
  }
  const entries = [
    {id:'busy',label:'UAVs in flight',time_s:cues.maximum_simultaneous_flight.recommended_view_s},
    {id:'delivery',label:'A delivery',time_s:cues.complete_collection_to_dropoff.recommended_playback_window_s[0],uav_id:cues.complete_collection_to_dropoff.uav_id_zero_based},
    {id:'swap',label:'Return & battery swap',time_s:cues.return_swap_service.recommended_playback_window_s[0],uav_id:cues.return_swap_service.uav_id_zero_based},
    {id:'complete',label:'600 delivered',time_s:cues.completion.recommended_view_s},
  ];
  const byId = new Map();
  for (const entry of entries) {
    if (!Number.isFinite(entry.time_s) || entry.time_s < 0 || entry.time_s > replay.metadata.duration_s ||
        entry.uav_id !== undefined && !replay.uavs.some(u => u.id === entry.uav_id)) {
      throw new Error(`Invalid presentation bookmark: ${entry.id}`);
    }
    byId.set(entry.id,entry);
    const option=document.createElement('option');option.value=entry.id;option.textContent=entry.label;element.append(option);
  }
  element.disabled=false;
  element.addEventListener('change',()=>{
    const entry=byId.get(element.value);
    if(entry)onChoose(entry);
    element.value='';
  });
  return {entries};
}

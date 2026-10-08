// Keep detail-scale depth precision when viewing a scene from far outside it.
// ENU bounds map to world x=east, y=up, z=-north.
export function nearPlaneForSceneBounds(worldPosition, bounds, worldForward) {
  const low=[bounds.min[0],bounds.min[2],-bounds.max[1]];
  const high=[bounds.max[0],bounds.max[2],-bounds.min[1]];
  const span=Math.max(1,...bounds.max.map((value,i)=>value-bounds.min[i]));
  const floor=Math.max(span/10000,.001);
  const distance=Math.hypot(...worldPosition.map((value,i)=>Math.max(low[i]-value,0,value-high[i])));
  // A near plane clips axial depth, not Euclidean distance. The signed minimum
  // over the entire box also handles off-axis views and boxes behind the eye.
  const length=Math.hypot(...worldForward);
  const forward=worldForward.map(value=>value/length);
  const minimumDepth=forward.reduce((depth,value,i)=>depth+
    ((value>=0?low[i]:high[i])-worldPosition[i])*value,0);
  // Never select only positive corners: a box crossing the eye plane needs the
  // original floor. All other box points are beyond minimumDepth.
  return Math.max(floor,Math.min(distance,Math.max(0,minimumDepth))/4);
}

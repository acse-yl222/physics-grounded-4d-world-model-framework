/** Recorded traffic time for replay clock t: t itself inside [traffic.firstTime, traffic.lastTime], otherwise null
 *  (no traffic data). The recorded sample is never looped or held to fill the rest of the replay clock. */
export function recordedTrafficTime(t, traffic) {
  return traffic && t >= traffic.firstTime && t <= traffic.lastTime ? t : null;
}

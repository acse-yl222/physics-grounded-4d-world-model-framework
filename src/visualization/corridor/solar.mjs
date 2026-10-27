/** Approximate geometric solar position; ENU direction, no atmospheric refraction.
 * Julian-date solar longitude/obliquity and sidereal hour angle. Not irradiance.
 */
export function solarPosition(date, latitude, longitude) {
  const rad = Math.PI / 180;
  const d = date.getTime() / 86400000 + 2440587.5 - 2451545;
  const mean = (357.529 + 0.98560028 * d) * rad;
  const lon = (280.459 + 0.98564736 * d + 1.915 * Math.sin(mean) + 0.02 * Math.sin(2 * mean)) * rad;
  const obliquity = (23.439 - 0.00000036 * d) * rad;
  const ra = Math.atan2(Math.cos(obliquity) * Math.sin(lon), Math.cos(lon));
  const dec = Math.asin(Math.sin(obliquity) * Math.sin(lon));
  const hour = (280.16 + 360.9856235 * d + longitude) * rad - ra;
  const lat = latitude * rad;
  const east = -Math.cos(dec) * Math.sin(hour);
  const north = Math.sin(dec) * Math.cos(lat) - Math.cos(dec) * Math.cos(hour) * Math.sin(lat);
  const up = Math.sin(dec) * Math.sin(lat) + Math.cos(dec) * Math.cos(hour) * Math.cos(lat);
  return { east, north, up, altitude: Math.asin(up) / rad };
}
/** Convert a London wall clock to UTC using the platform's IANA time-zone rules.
 * UI uses noon by default; ambiguous autumn hours choose the earlier occurrence.
 */
export function londonInstant(day, hour) {
  const naive = Date.parse(`${day}T00:00:00Z`) + hour * 3600000;
  const format = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/London',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  });
  for (const offset of [1, 0]) {
    const candidate = new Date(naive - offset * 3600000);
    const parts = Object.fromEntries(format.formatToParts(candidate).map((p) => [p.type, p.value]));
    if (Math.abs(Number(parts.hour) + Number(parts.minute) / 60 - hour) < 0.017) return candidate;
  }
  throw new Error('This London time does not exist because the clocks move forward.');
}

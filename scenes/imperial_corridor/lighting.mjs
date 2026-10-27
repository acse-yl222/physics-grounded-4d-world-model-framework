import { solarPosition, londonInstant } from './solar.mjs';
export function installLighting({ scene, sun, renderer, direction, controls, setShadows, redraw }) {
  const panel = document.createElement('details');
  panel.innerHTML = `<summary>Sunlight & shadows</summary>
    <div class="note">London local time · independent of traffic replay</div>
    <label><input id="sun-shadows" type="checkbox" checked> Building shadows</label>
    <label>Date <input id="sun-date" type="date" value="2026-06-25"></label>
    <label>Time <input id="sun-time" type="range" min="0" max="23.75" step="0.25" value="13"></label>
    <output id="sun-state" class="note" aria-live="polite"></output>
    <label>Cloud cover <input id="sun-cloud" type="range" min="0" max="1" step="0.05" value="0.2"></label>
    <p class="note">High quality adds ambient occlusion and finer shadows. Sun direction is calculated; clouds and sky brightness are illustrative, not measured irradiance.</p>`;
  document.querySelector('.card').append(panel);
  const get = (id) => document.getElementById(id);
  const ambient = scene.children.find((child) => child.isHemisphereLight);
  function update() {
    try {
      const hour = Number(get('sun-time').value);
      const position = solarPosition(
        londonInstant(get('sun-date').value, hour),
        51.506427,
        -0.200473,
      );
      const cloud = Number(get('sun-cloud').value);
      const daylight = Math.max(0, position.up);
      direction.set(position.east, position.up, -position.north);
      sun.target.position.copy(controls.target);
      sun.position.copy(controls.target).addScaledVector(direction, 3000);
      sun.intensity = daylight > 0 ? (1.1 + 2 * Math.sqrt(daylight)) * (1 - 0.85 * cloud) : 0;
      sun.color.setHSL(0.09, 0.12 + 0.5 * (1 - Math.sqrt(daylight)), 0.88);
      ambient.intensity = 0.12 + 1.2 * Math.sqrt(daylight);
      scene.environmentIntensity = 0.05 + 0.5 * Math.sqrt(daylight);
      scene.background.setHSL(0.58, 0.25 * (1 - cloud), 0.035 + 0.78 * Math.sqrt(daylight));
      if (scene.fog) scene.fog.color.copy(scene.background);
      renderer.toneMappingExposure = 1.05;
      get('sun-state').textContent =
        `${String(Math.floor(hour)).padStart(2, '0')}:${String(Math.round((hour % 1) * 60)).padStart(2, '0')} · sun ${position.altitude.toFixed(1)}°${daylight ? '' : ' · night'}`;
      window.cityLighting = { update, position, sun, direction };
      renderer.shadowMap.needsUpdate = true;
      redraw();
    } catch (error) {
      get('sun-state').textContent = error.message;
    }
  }
  get('sun-shadows').addEventListener('change', () => setShadows(get('sun-shadows').checked));
  setShadows(true);
  panel.addEventListener('input', update);
  update();
}

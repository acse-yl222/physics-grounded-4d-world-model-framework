// Scene bird layer (bird-layer.js): needs a served viewer with the scene's data and a bird replay
// (python -m urban_geometry.birds.scene.run ...). Example:
//   p4d serve --port 8769 &
//   UWM_VIEWER_URL='http://127.0.0.1:8769/src/visualization/legacy/viewer/3d/?scene=white_city&lite=1&pose=campus&shot=birds&hold=1' \
//   CHROME_PATH=/path/to/chrome node tests/browser_scene_birds.cjs
(async () => {
  const { default: puppeteer } = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome',
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1000, height: 750, deviceScaleFactor: 1 });
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('console', (m) => {
      if (m.type() === 'error') console.log('console:', m.text());
    });
    await page.goto(
      process.env.UWM_VIEWER_URL ||
        'http://127.0.0.1:8769/src/visualization/legacy/viewer/3d/?scene=white_city&lite=1&pose=campus&shot=birds&hold=1',
      { waitUntil: 'domcontentloaded', timeout: 60000 },
    );
    await page.waitForFunction(
      () => window.viewer?.birds && document.querySelector('#loading').classList.contains('hide'),
      { timeout: 240000 },
    );
    const report = await page.evaluate(() => {
      const b = viewer.birds;
      const layer = b.layer ?? b; // stand-alone layer, or the South Kensington replay's bird layer
      const manifest = b.manifest;
      const at = (t) => {
        if (b.update) b.update(t);
        else layer.update(t);
        return Array.from({ length: 5 }, (_, i) => layer.getState(i));
      };
      if (b.playing !== undefined) b.playing = false;
      const t0 = at(0),
        mid = at(manifest ? manifest.last_frame_t_s / 2 : 1800),
        again = at(0),
        end = at(1e9);
      const roost = manifest?.sites?.roosts?.[0]?.center;
      const button = document.querySelector('[data-shot="birds"]');
      return {
        scene: viewer.SCENE.id,
        birds: layer.stats?.birds,
        frames: layer.stats?.frames,
        start: t0.map((s) => s.stateName),
        startOnRoost: roost
          ? t0.every(
              (s) =>
                Math.hypot(s.x - roost[0], s.z + roost[1]) < 15 && Math.abs(s.y - roost[2]) < 2,
            )
          : null,
        moved: JSON.stringify(t0) !== JSON.stringify(mid),
        seekReproducible: JSON.stringify(t0) === JSON.stringify(again),
        heldAtEnd: end.every((s) => s.visible),
        midStates: mid.map((s) => s.stateName),
        button: button ? { text: button.textContent, disabled: button.disabled } : null,
        timeLabel: document.querySelector('#time-label')?.textContent ?? null,
      };
    });
    console.log(JSON.stringify(report, null, 1));
    const ok =
      report.birds > 0 &&
      report.moved &&
      report.seekReproducible &&
      report.heldAtEnd &&
      report.startOnRoost !== false &&
      (!report.button || !report.button.disabled) &&
      errors.length === 0;
    if (!ok) {
      console.error('FAIL', errors);
      process.exitCode = 1;
    } else console.log('PASS');
  } finally {
    await browser.close();
  }
})();

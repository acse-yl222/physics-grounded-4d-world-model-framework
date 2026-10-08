(async () => {
  const { default: puppeteer } = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const fs = require('fs');
  const path = require('path');
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome',
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1000, height: 750, deviceScaleFactor: 1 });
    const errors = [],
      requests = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('request', (r) => requests.push(r.url()));
    page.on('console', (m) => {
      if (m.type() === 'error') console.log(m.text());
    });
    // Test a draft Pages overlay against the published full geometry before deploying it.
    if (process.env.PAGES_OVERLAY) {
      await page.setRequestInterception(true);
      page.on('request', async (r) => {
        const rel = new URL(r.url()).pathname.replace(
          /^\/physics-grounded-4d-world-model-framework\//,
          '',
        );
        if (/^(viewer\/3d\/(main.js|uav-layer.js)|project\/white_city\/)/.test(rel)) {
          const file = path.join(process.env.PAGES_OVERLAY, rel);
          if (fs.existsSync(file)) {
            await r.respond({
              status: 200,
              contentType: rel.endsWith('.js')
                ? 'application/javascript'
                : rel.endsWith('.json')
                  ? 'application/json'
                  : 'application/octet-stream',
              body: fs.readFileSync(file),
            });
            return;
          }
        }
        await r.continue();
      });
    }
    await page.goto(
      process.env.UWM_VIEWER_URL ||
        'http://127.0.0.1:8785/viewer/3d/?scene=white_city&lite=1&pose=campus&shot=uavs&hold=1',
      { waitUntil: 'domcontentloaded', timeout: 60000 },
    );
    await page.waitForFunction(
      () =>
        window.viewer?.uavs?.uavMode === 'random_wavepde' &&
        document.querySelector('#loading').classList.contains('hide'),
      { timeout: 240000 },
    );
    const report = await page.evaluate(() => {
      const r = viewer.uavs;
      r.playing = false;
      r.update(60);
      const a = r.uavs.map((u) => [u.x, u.y, u.z]);
      r.update(80);
      const b = r.uavs.map((u) => [u.x, u.y, u.z]);
      r.update(60);
      return {
        scene: viewer.SCENE.id,
        count: r.uavs.length,
        instances: r.actors.uavs.activeCount,
        routes: r.flightData.routes.length,
        stations: r.flightData.stations.length,
        maxStationHeight: Math.max(...r.flightData.stations.map((s) => s.y_m)),
        moved: JSON.stringify(a) !== JSON.stringify(b),
        seekReproducible: JSON.stringify(a) === JSON.stringify(r.uavs.map((u) => [u.x, u.y, u.z])),
        stationOne: r.flightData.stations[0],
        corridorsVisible: r.corridors.visible,
        stats: r.stats,
      };
    });
    if (
      requests.some((u) =>
        /schedule.json|parking.json|hub-bays.json|data\/birds|data\/traffic\/current_replay/.test(
          u,
        ),
      )
    )
      throw Error('Cross-scene or scheduling request');
    if (
      report.scene !== 'white_city' ||
      report.count !== 300 ||
      report.instances !== 300 ||
      report.routes !== 870 ||
      !report.moved ||
      !report.seekReproducible ||
      report.maxStationHeight > 1
    )
      throw Error(JSON.stringify(report));
    console.log('Flight data validated', JSON.stringify(report));
    await page.click('[data-shot="uavs"]');
    await new Promise((r) => setTimeout(r, 3500));
    await page.evaluate(() => {
      const r = viewer.uavs;
      r.playing = false;
      document.querySelector('#l-uavs').click();
      if (r.markers.visible || r.corridors.visible || r.actors.uavs.group.visible)
        throw Error('UAV toggle failed');
      document.querySelector('#l-uavs').click();
    });
    if (!process.env.SKIP_FIELD_CHECK) {
      await page.click('[data-field="wind"]');
      await new Promise((r) => setTimeout(r, 200));
      if (await page.evaluate(() => viewer.uavs.group.visible))
        throw Error('UAV visible in physics view');
      await page.click('[data-shot="uavs"]');
      await new Promise((r) => setTimeout(r, 3000));
    }
    await page.evaluate(() => {
      const r = viewer.uavs;
      r.playing = false;
      const slider = document.querySelector('#step');
      slider.value = '120';
      slider.dispatchEvent(new Event('input'));
      if (r.t !== 120) throw Error('Time slider failed');
    });
    fs.mkdirSync('cache/framework', { recursive: true });
    await page.screenshot({
      path: 'cache/framework/white-city-uavs.png',
      captureBeyondViewport: false,
    });
    report.errors = errors;
    console.log(JSON.stringify(report));
    fs.writeFileSync(
      'cache/framework/white-city-uavs-browser.json',
      JSON.stringify(report, null, 2),
    );
    if (errors.length) throw Error(errors.join('\n'));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});

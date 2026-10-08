(async () => {
  const { default: puppeteer } = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const assert = require('node:assert/strict');
  const browser = await puppeteer.launch({
    executablePath: '/opt/google/chrome/chrome',
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  const base = process.env.P4D_SITE_URL || 'http://127.0.0.1:8773/';
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(
      new URL(
        'src/visualization/viewer/?manifest=../../../examples/contract-v1/manifest.json',
        base,
      ).href,
    );
    await page.waitForFunction(() => window.urbanViewer?.widgets.length === 5);
    await wait(500);
    const initial = await page.evaluate(() => urbanViewer.performanceStats.renders);
    await wait(1200);
    assert.equal(
      await page.evaluate(() => urbanViewer.performanceStats.renders),
      initial,
      'Unified viewer must settle when idle',
    );
    await page.click('#play');
    await wait(500);
    assert.ok(await page.evaluate((n) => urbanViewer.performanceStats.renders > n, initial));
    await page.click('#play');
    await wait(200);
    const paused = await page.evaluate(() => urbanViewer.performanceStats.renders);
    await wait(800);
    assert.equal(await page.evaluate(() => urbanViewer.performanceStats.renders), paused);
    await page.click('#layers input[type=checkbox]');
    await page.waitForFunction((n) => urbanViewer.performanceStats.renders > n, {}, paused);
    console.log('PASS: unified viewer idle, play, pause and layer invalidation');
    await page.goto(new URL('viewer/3d/?scene=south_kensington&lite=1&expansion=0', base).href);
    await page.waitForFunction(
      () => document.querySelector('#loading').classList.contains('hide'),
      { timeout: 120000 },
    );
    await page.click('#play');
    await wait(300);
    const city = await page.evaluate(() => ({
      renders: viewer.performanceStats.renders,
      time: viewer.replay.t,
    }));
    await wait(1200);
    assert.equal(
      await page.evaluate(() => viewer.performanceStats.renders),
      city.renders,
      'Paused city must not redraw',
    );
    assert.equal(await page.evaluate(() => viewer.replay.t), city.time);
    await page.click('#play');
    await wait(250);
    const other = await browser.newPage();
    await other.bringToFront();
    await page.waitForFunction(() => document.hidden);
    await wait(150);
    const hidden = await page.evaluate(() => ({
      renders: viewer.performanceStats.renders,
      time: viewer.replay.t,
    }));
    await wait(1000);
    assert.deepEqual(
      await page.evaluate(() => ({
        renders: viewer.performanceStats.renders,
        time: viewer.replay.t,
      })),
      hidden,
      'Hidden city must freeze its animation',
    );
    await page.bringToFront();
    await page.waitForFunction((n) => viewer.performanceStats.renders > n, {}, hidden.renders);
    await other.close();
    assert.deepEqual(errors, []);
    console.log('PASS: city paused rendering, hidden-tab freeze and resume');
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});

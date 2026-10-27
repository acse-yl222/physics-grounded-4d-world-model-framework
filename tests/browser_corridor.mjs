/** Run against a packaged scene (local or published); requires Chrome and full data. */
import puppeteer from 'puppeteer';
import assert from 'node:assert/strict';
const url = process.argv[2] || 'http://127.0.0.1:8792/scenes/imperial_corridor/';
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome',
  headless: true,
  args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
  protocolTimeout: 300000,
});
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 800 });
  const errors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') console.log('console:', message.text());
  });
  page.on('pageerror', (error) => errors.push(error.message));
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 300000 });
  await page.waitForFunction(() => window.cityTraffic?.data.meta?.frames > 0, {
    timeout: 300000,
  });
  console.log('scene loaded');
  await page.evaluate(() => {
    window.cityTraffic.playback.playing = false;
    window.cityTraffic.playback.dirty = true;
  });
  const frame = () =>
    page.evaluate(
      () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
    );
  for (const [period, t0] of [
    ['inter_peak', 49800],
    ['pm_peak', 64200],
    ['am_peak', 31800],
  ]) {
    await page.click(`[data-period="${period}"]`);
    await page.waitForFunction(
      (t0) => window.cityTraffic.data.meta.t0 === t0,
      { timeout: 60000 },
      t0,
    );
    assert.equal(await page.evaluate(() => window.cityTraffic.playback.t), 0);
  }
  console.log('periods passed');
  if (await page.$('#traffic-model')) {
    await page.select('#traffic-model', 'recorded');
    await page.waitForFunction(() => !window.cityTraffic.data.meta.provenance.rebuilt, {
      timeout: 60000,
    });
    await page.select('#traffic-model', 'rebuilt');
    await page.waitForFunction(() => window.cityTraffic.data.meta.provenance.rebuilt, {
      timeout: 60000,
    });
  }
  await page.evaluate(() => {
    const p = window.cityTraffic.playback;
    p.t = 599;
    p.playing = true;
    p.last = performance.now();
  });
  await frame();
  assert.deepEqual(
    await page.evaluate(() => ({
      t: window.cityTraffic.playback.t,
      playing: window.cityTraffic.playback.playing,
    })),
    { t: 599, playing: false },
  );
  await page.click('#t-play');
  await frame();
  assert.ok(await page.evaluate(() => window.cityTraffic.playback.t < 10));
  await page.click('#t-play');
  await page.evaluate(() => {
    document.querySelector('#sun-time').closest('details').open = true;
  });
  await frame();
  console.log('playback passed');
  await page.screenshot({ path: 'cache/corridor-day.png' });
  await page.evaluate(() => {
    const input = document.getElementById('sun-time');
    input.value = '0';
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await frame();
  assert.equal(await page.evaluate(() => window.cityLighting.sun.intensity), 0);
  await page.screenshot({ path: 'cache/corridor-night.png' });
  await page.evaluate(() => {
    const input = document.getElementById('sun-time');
    input.value = '17';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    const shadows = document.getElementById('sun-shadows');
    if (!shadows.checked) shadows.click();
  });
  await frame();
  assert.equal(await page.evaluate(() => window.cityLighting.sun.castShadow), true);
  await page.screenshot({ path: 'cache/corridor-shadows.png' });
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      passed: true,
      periods: 3,
      endStops: true,
      replay: true,
      night: true,
      shadows: true,
      pageErrors: errors,
    }),
  );
} finally {
  await browser.close();
}

(async () => {
  const { default: puppeteer } = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const assert = require('node:assert/strict');
  const base = process.env.P4D_SITE_URL || 'http://127.0.0.1:8773/';
  const browser = await puppeteer.launch({
    executablePath: '/opt/google/chrome/chrome',
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  try {
    for (const target of ['scene', 'mask', 'wind']) {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', (e) => errors.push(e.message));
      await page.setRequestInterception(true);
      page.on('request', (r) => {
        const fail =
          target === 'scene'
            ? r.url().includes('/south_kensington/scene.json')
            : target === 'mask'
              ? r.url().includes('/masks/building_footprint')
              : r.url().endsWith('/windfarm-movie/resources.json');
        if (fail) r.respond({ status: 503, body: 'Test outage' });
        else r.continue();
      });
      await page.goto(
        new URL(
          target === 'wind'
            ? 'viewer/windfarm-movie/'
            : 'viewer/3d/?scene=south_kensington&lite=1&expansion=0',
          base,
        ).href,
      );
      await page.waitForSelector('#viewer-error', { visible: true, timeout: 90000 });
      assert.ok((await page.$eval('#viewer-error-message', (e) => e.textContent)).length);
      assert.equal(await page.$eval('#viewer-retry', (e) => e.href), page.url());
      if (target !== 'wind')
        assert.equal(
          new URL(await page.$eval('#viewer-lite', (e) => e.href)).searchParams.get('lite'),
          '1',
        );
      await Promise.all([page.waitForNavigation(), page.click('#viewer-home')]);
      await page.waitForSelector('[data-scene="windfarm"] a');
      assert.deepEqual(errors, []);
      console.log('PASS: recoverable', target, 'failure');
      await page.close();
    }
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});

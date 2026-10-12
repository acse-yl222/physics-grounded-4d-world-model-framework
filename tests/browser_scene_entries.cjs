// Real-data website navigation checks; the unconditional E2E smoke stays synthetic.
(async () => {
  const { default: puppeteer } = await import(process.env.PUPPETEER_MODULE || 'puppeteer');
  const assert = require('node:assert/strict');
  const fs = require('node:fs');
  const base = process.env.P4D_SCENE_WEB_URL || 'http://127.0.0.1:8774/';
  const output = process.env.UWM_BROWSER_OUTPUT || 'cache/framework/web-preview-20261012/browser';
  fs.mkdirSync(output, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome',
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  try {
    const page = await browser.newPage(),
      errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.setViewport({ width: 1440, height: 1100 });
    await page.goto(base, { waitUntil: 'networkidle0' });
    const cards = await page.$$eval('.card', (nodes) =>
      nodes.map((n) => ({
        id: n.dataset.scene,
        title: n.querySelector('h3').textContent,
        url: n.querySelector('.button').href,
        lite: n.querySelector('.quick-preview')?.href,
      })),
    );
    assert.deepEqual(
      cards.map((n) => n.id),
      ['south_ken', 'white_city', 'windfarm', 'delhi_karol_bagh', 'thapar_university'],
    );
    for (const id of ['delhi_karol_bagh', 'thapar_university']) {
      const card = cards.find((n) => n.id === id);
      assert.equal(new URL(card.url).searchParams.get('scene'), id);
      assert.ok(new URL(card.url).searchParams.get('run'));
      assert.equal(new URL(card.lite).searchParams.get('lite'), '1');
    }
    await page.screenshot({ path: output + '/homepage.png', fullPage: true });
    await page.setViewport({ width: 390, height: 844 });
    assert.ok(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      'Mobile homepage overflows',
    );
    await page.screenshot({ path: output + '/mobile.png', fullPage: true });
    await page.setViewport({ width: 1440, height: 1000 });
    await page.click('[data-scene="delhi_karol_bagh"] .button');
    await page.waitForFunction(
      () =>
        window.viewer &&
        viewer.SCENE.id === 'delhi_karol_bagh' &&
        document.getElementById('loading').classList.contains('hide') &&
        !viewer.state.loading,
      { timeout: 180000 },
    );
    assert.deepEqual(
      await page.$$eval('#scene-select option', (nodes) => nodes.map((n) => n.value)),
      cards.map((n) => n.id),
    );
    await page.screenshot({ path: output + '/delhi.png' });
    // Carry the existing lightweight preference through the scene switch.
    await page.evaluate(() => history.replaceState(null, '', location.href + '&lite=1'));
    await page.goto(cards.find((n) => n.id === 'delhi_karol_bagh').lite);
    await page.waitForFunction(
      () => window.viewer && document.getElementById('loading').classList.contains('hide'),
      { timeout: 180000 },
    );
    await page.select('#scene-select', 'thapar_university');
    await page.waitForFunction(
      () =>
        window.viewer &&
        viewer.SCENE.id === 'thapar_university' &&
        document.getElementById('loading').classList.contains('hide') &&
        !viewer.state.loading,
      { timeout: 180000 },
    );
    assert.equal(new URL(page.url()).searchParams.get('lite'), '1');
    await page.screenshot({ path: output + '/thapar.png' });
    for (const phase of ['temp', 'poll', 'solar']) {
      await page.click('[data-field="' + phase + '"]');
      await page.waitForFunction(
        (k) => viewer.state.phase === k && !viewer.state.loading && viewer.state.fields[k],
        { timeout: 60000 },
        phase,
      );
    }
    assert.deepEqual(errors, []);
    const report = {
      passed: true,
      cards,
      scene_switch: true,
      lightweight_preference: true,
      thapar_fields: ['temp', 'poll', 'solar'],
      page_errors: errors,
    };
    fs.writeFileSync(output + '/report.json', JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});

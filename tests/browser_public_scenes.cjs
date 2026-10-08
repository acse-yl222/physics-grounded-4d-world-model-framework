(async () => {
  const { default: puppeteer } = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const fs = require('node:fs');
  const base = new URL(process.env.P4D_SITE_URL || 'http://127.0.0.1:8773/');
  const output = process.env.P4D_BROWSER_OUTPUT || 'cache/framework/browser/public-scenes';
  fs.mkdirSync(output, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome',
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  const report = { scenes: [] };
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 950 });
    await page.goto(base.href, { waitUntil: 'networkidle0' });
    await page.waitForSelector('[data-scene="windfarm"] a');
    report.links = await page.$$eval('#scenes article', (cards) =>
      cards.map((c) => ({ id: c.dataset.scene, url: c.querySelector('a').href })),
    );
    if (report.links.map((s) => s.id).join(',') !== 'south_ken,white_city,windfarm')
      throw Error('Homepage scene entries missing');
    await page.screenshot({ path: output + '/homepage.png' });
    await page.goto(
      new URL(
        'src/visualization/viewer/?manifest=../../../examples/contract-v1/manifest.json',
        base,
      ).href,
      { waitUntil: 'networkidle0' },
    );
    await page.waitForFunction(() => window.urbanViewer?.widgets.length === 5);
    report.viewerOptions = await page.$$eval('#scene option', (options) =>
      options.map((o) => o.value),
    );
    for (const id of ['south_ken', 'white_city', 'windfarm'])
      if (!report.viewerOptions.includes('published:' + id))
        throw Error('Unified viewer has no published ' + id + ' entry');
    await page.close();
    for (const entry of report.links) {
      const page = await browser.newPage();
      await page.setViewport({ width: 1280, height: 900 });
      const errors = [];
      page.on('pageerror', (e) => {
        errors.push(e.message);
        console.error(entry.id, e.message);
      });
      const url = new URL(entry.url);
      if (entry.id !== 'windfarm') {
        url.searchParams.set('lite', '1');
        url.searchParams.set('expansion', '0');
      }
      await page.goto(url.href, { waitUntil: 'domcontentloaded', timeout: 60000 });
      if (errors.length) throw Error(errors.join('\n'));
      if (entry.id === 'windfarm') {
        await page.waitForFunction(() => window.movie?.ready, { timeout: 120000 });
        const frames = await page.evaluate(() => movie.meta.times.length);
        if (frames !== 151) throw Error('Wind frame count changed');
        await page.select('#model', 'mac_live');
        await page.evaluate(() => movie.render(100, 1, 'CHECK'));
        report.scenes.push({ id: entry.id, frames, ready: true });
      } else {
        await page.waitForFunction(
          () => document.querySelector('#loading')?.classList.contains('hide'),
          { timeout: 120000 },
        );
        report.scenes.push({
          id: entry.id,
          title: await page.title(),
          ready: true,
          mode: 'lite geometry; real published fields',
        });
      }
      if (errors.length) throw Error(entry.id + ': ' + errors.join('\n'));
      await page.screenshot({ path: output + '/' + entry.id + '.png' });
      await page.close();
      console.log('Ready:', entry.id);
    }
    fs.writeFileSync(output + '/report.json', JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});

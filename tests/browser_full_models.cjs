// Local preview emulates Pages to load the real model chunks from resource hosting.
(async () => {
  const {default: puppeteer} = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const fs = require('node:fs');
  const base = process.env.P4D_SITE_URL || 'http://127.0.0.1:8773/';
  const output = process.env.P4D_BROWSER_OUTPUT || 'cache/framework/browser/stability-fixed';
  fs.mkdirSync(output, {recursive: true});
  const browser = await puppeteer.launch({executablePath: '/opt/google/chrome/chrome', headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage']});
  const results = [];
  try {
    for (const scene of ['south_kensington', 'white_city']) {
      const page = await browser.newPage();
      await page.setViewport({width: 1280, height: 900});
      if (new URL(base).hostname === '127.0.0.1') {
        await page.setRequestInterception(true);
        page.on('request', r => r.url().endsWith('/viewer/config.js')
          ? r.respond({status: 200, contentType: 'text/javascript', body: 'export const ON_PAGES=true;'}) : r.continue());
      }
      const errors = [], failures = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('response', r => { if (r.status() >= 400) failures.push({url: r.url(), status: r.status()}); });
      const start = Date.now();
      try {
        await page.goto(new URL(`viewer/3d/?scene=${scene}&lite=0`, base).href,
          {waitUntil: 'domcontentloaded', timeout: 60000});
        await page.waitForFunction(() => document.querySelector('#loading')?.classList.contains('hide'), {timeout: 240000});
        await page.waitForFunction(() => viewer.renderer.info.render.triangles > 0);
        await page.screenshot({path: `${output}/${scene}-full.png`});
        results.push({scene, seconds: (Date.now()-start)/1000, errors, failures,
          ...await page.evaluate(() => ({ready: true, drawCalls: viewer.renderer.info.render.calls,
            triangles: viewer.renderer.info.render.triangles, contextLost: viewer.renderer.getContext().isContextLost(),
            meshes: viewer.model.children.length, birdControlDisabled: document.querySelector('#l-birds').disabled}))});
      } catch (error) {
        results.push({scene, ready: false, error: error.message, errors, failures,
          loading: await page.$eval('#loading', e => e.innerText).catch(() => null)});
      }
      console.log(JSON.stringify(results.at(-1)));
      await page.close();
    }
  } finally {
    fs.writeFileSync(output+'/full-models.json', JSON.stringify(results, null, 2));
    await browser.close();
  }
  if (results.some(r => !r.ready || r.contextLost || r.errors.length)) throw Error('Full-model regression failed; see report');
})().catch(e => {console.error(e);process.exit(1);});

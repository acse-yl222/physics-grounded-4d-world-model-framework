// Static RSI summaries must preserve recorded task labels and values.
(async () => {
  const {default: puppeteer} = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const fs = require('node:fs'), path = require('node:path');
  if (!process.env.RSI_MANIFEST || !process.env.UWM_VIEWER_URL || !process.env.UWM_BROWSER_OUTPUT) throw Error('Set RSI_MANIFEST, UWM_VIEWER_URL and UWM_BROWSER_OUTPUT');
  const file = path.resolve(process.env.RSI_MANIFEST), manifest = JSON.parse(fs.readFileSync(file));
  const output = path.resolve(process.env.UWM_BROWSER_OUTPUT); fs.mkdirSync(output, {recursive: true});
  const browser = await puppeteer.launch({executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome', headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader']});
  try {
    const page = await browser.newPage(); await page.setViewport({width: 1280, height: 900});
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(process.env.UWM_VIEWER_URL, {waitUntil: 'networkidle0'});
    await page.waitForFunction(n => window.urbanViewer?.widgets.length === n, {}, manifest.layers.length);
    const checks = [];
    for (const layer of manifest.layers) {
      const expected = JSON.parse(fs.readFileSync(path.join(path.dirname(file), layer.asset)));
      const actual = await page.evaluate(id => {
        const w = urbanViewer.widgets.find(w => w.layer.id === id); w.setTime(1000000);
        return {labels: w.data.labels, values: w.current, available: w.available};
      }, layer.id);
      if (JSON.stringify(expected.labels) !== JSON.stringify(actual.labels) || JSON.stringify(expected.values) !== JSON.stringify(actual.values) || !actual.available) throw Error('Static result mismatch: ' + layer.id);
      checks.push({id: layer.id, labels_and_values_match: true, static_available: true});
    }
    await page.click('#layers .layer:first-child input[type=checkbox]');
    if (await page.evaluate(() => urbanViewer.widgets[0].group.visible)) throw Error('Visibility toggle failed');
    await page.click('#layers .layer:first-child input[type=checkbox]');
    await page.screenshot({path: path.join(output, 'rsi.png')});
    const disposed = await page.evaluate(() => {urbanViewer.dispose(); return urbanViewer.widgets.every(w => w.disposed);});
    if (!disposed || errors.length) throw Error('Disposal or page error');
    const result = {checks, disposed, errors}; fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(result, null, 2)); console.log(JSON.stringify(result));
  } finally {await browser.close();}
})().catch(error => {console.error(error); process.exit(1);});

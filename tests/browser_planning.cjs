// Existing unified scalar-field widgets must preserve exported planning values.
(async () => {
  const {default: puppeteer} = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const fs = require('node:fs'), path = require('node:path');
  if (!process.env.PLANNING_MANIFEST || !process.env.UWM_VIEWER_URL) throw Error('Set PLANNING_MANIFEST and UWM_VIEWER_URL');
  const file = path.resolve(process.env.PLANNING_MANIFEST);
  const manifest = JSON.parse(fs.readFileSync(file));
  const output = process.env.UWM_BROWSER_OUTPUT || path.join(path.dirname(file), 'browser');
  fs.mkdirSync(output, {recursive: true});
  const browser = await puppeteer.launch({executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome',
    headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader']});
  try {
    const page = await browser.newPage();
    await page.setViewport({width: 1280, height: 900});
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(process.env.UWM_VIEWER_URL, {waitUntil: 'networkidle0'});
    await page.waitForFunction(n => window.urbanViewer?.widgets.length === n, {}, manifest.layers.length);
    const results = [];
    for (const layer of manifest.layers) {
      const expected = JSON.parse(fs.readFileSync(path.join(path.dirname(file), layer.asset)));
      const actual = await page.evaluate(id => {
        const w = urbanViewer.widgets.find(w => w.layer.id === id);
        return {id, positions: w.data.positions, values: w.current, available: w.available};
      }, layer.id);
      if (JSON.stringify(expected.positions) !== JSON.stringify(actual.positions)) throw Error('Position mismatch');
      if (JSON.stringify(expected.values) !== JSON.stringify(actual.values)) throw Error('Value mismatch');
      if (!actual.available) throw Error('Static planning layer unavailable');
      results.push({id: layer.id, receptor_count: actual.positions.length, values_match: true});
    }
    await page.click('#layers .layer:first-child input[type=checkbox]');
    if (await page.evaluate(() => urbanViewer.widgets[0].group.visible)) throw Error('Visibility toggle failed');
    await page.click('#layers .layer:first-child input[type=checkbox]');
    // Frame only the pilot window for the screenshot; source coordinates stay intact.
    await page.evaluate(() => {
      const points = urbanViewer.widgets[0].data.positions;
      urbanViewer.manifest.spatial.bounds_m = {
        min: [Math.min(...points.map(p => p[0])), Math.min(...points.map(p => p[1])), Math.min(...points.map(p => p[2]))],
        max: [Math.max(...points.map(p => p[0])), Math.max(...points.map(p => p[1])), Math.max(...points.map(p => p[2])) + 1]
      };
      for (const w of urbanViewer.widgets) w.instances.geometry.scale(.15, .15, .15);
      urbanViewer.fit();
    });
    for (let i = 2; i <= manifest.layers.length; i++) {
      await page.click(`#layers .layer:nth-child(${i}) input[type=checkbox]`);
    }
    await page.screenshot({path: path.join(output, 'planning.png')});
    const disposal = await page.evaluate(() => {urbanViewer.dispose(); return urbanViewer.widgets.every(w => w.disposed);});
    if (!disposal || errors.length) throw Error('Viewer errors: ' + errors.join(';'));
    const report = {layers: results, disposal, errors};
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exit(1);});

(async () => {
  const { default: puppeteer } = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const path = require('node:path');
  const fs = require('node:fs');
  const output = process.env.UWM_BROWSER_OUTPUT || 'cache/framework/browser';
  fs.mkdirSync(output, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome',
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(
      process.env.UWM_VIEWER_URL ||
        'http://127.0.0.1:8769/src/visualization/viewer/?manifest=../../../examples/contract-v1/manifest.json',
      { waitUntil: 'networkidle0' },
    );
    await page.waitForFunction(() => window.urbanViewer?.widgets.length === 5, { timeout: 15000 });
    const initial = await page.evaluate(() => ({
      status: document.getElementById('status').textContent,
      kinds: urbanViewer.widgets.map((w) => w.layer.kind),
    }));
    const target = await page.evaluate(() => {
      const w = urbanViewer.widgets[0],
        camera = w.context.camera;
      camera.updateMatrixWorld();
      const point = camera.position
        .clone()
        .set(10 / 3, 0, -10 / 3)
        .project(camera);
      const rect = document.querySelector('#viewport>canvas').getBoundingClientRect();
      return {
        x: rect.left + ((point.x + 1) / 2) * rect.width,
        y: rect.top + ((1 - point.y) / 2) * rect.height,
      };
    });
    await page.mouse.click(target.x, target.y);
    const selected = await page.$eval('#selection', (el) => el.textContent);
    if (!selected.includes('"layer_id": "mesh"')) throw Error('Mesh selection failed: ' + selected);
    await page.evaluate(() => urbanViewer.setTime(0.5));
    const mid = await page.evaluate(() => ({
      vector: urbanViewer.widgets.find((w) => w.layer.kind === 'vector_field').current,
      position: urbanViewer.widgets.find((w) => w.layer.kind === 'trajectories').current,
      scalar: urbanViewer.widgets.find((w) => w.layer.kind === 'scalar_field').current,
    }));
    if (mid.vector[0][0] !== 1.5 || mid.position[0][0] !== 0.5 || mid.scalar[0] !== 290.5)
      throw Error('Interpolation mismatch');
    await page.click('#layers .layer:nth-child(2) input[type=checkbox]');
    if (await page.evaluate(() => urbanViewer.widgets[1].group.visible))
      throw Error('Visibility toggle failed');
    await page.click('#layers .layer:nth-child(2) input[type=checkbox]');
    await new Promise((resolve) => setTimeout(resolve, 1000));
    await page.screenshot({ path: path.join(output, 'unified-viewer.png') });
    const after = await page.evaluate(() => {
      urbanViewer.setTime(99);
      return urbanViewer.widgets.map((w) => ({ kind: w.layer.kind, available: w.available }));
    });
    if (after.some((w) => w.kind !== 'mesh' && w.available))
      throw Error('Out-of-range data stayed visible');
    const disposal = await page.evaluate(() => {
      urbanViewer.dispose();
      urbanViewer.dispose();
      return urbanViewer.widgets.every((w) => w.disposed && w.group.parent === null);
    });
    if (!disposal) throw Error('Disposal failed');
    if (errors.length) throw Error(errors.join('\n'));
    const report = { initial, selected, mid, outOfRange: after, disposal, errors };
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});

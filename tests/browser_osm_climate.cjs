const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const {default: puppeteer} = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const base = process.env.UWM_VIEWER_URL || 'http://127.0.0.1:8773';
  const output = 'cache/thapar_university/browser';
  fs.mkdirSync(output, {recursive: true});
  const browser = await puppeteer.launch({executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome',
    headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader']});
  const reports = [];
  try {
    for (const scenario of ['summer', 'winter', 'traffic']) {
      const config = JSON.parse(fs.readFileSync(`project/thapar_university/configs/${scenario}_result.json`));
      const page = await browser.newPage();
      await page.setViewport({width: 1440, height: 1000});
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(`${base}/src/visualization/viewer/?scene=thapar_university&view=${config.view_id}`, {waitUntil: 'networkidle0'});
      await page.waitForFunction(() => window.urbanViewer?.widgets.length >= 4 && document.getElementById('status').textContent.includes('ready'), {timeout: 30000});
      const report = await page.evaluate(() => {
        urbanViewer.setTime(600);
        return {status: document.getElementById('status').textContent,
          layers: urbanViewer.widgets.map(widget => ({id: widget.layer.id, kind: widget.layer.kind, available: widget.available})),
          scene: document.getElementById('scene').value, error: document.getElementById('error').textContent};
      });
      if (report.scene !== 'thapar_university' || report.error || errors.length) throw new Error(JSON.stringify({report, errors}));
      if (scenario !== 'traffic') {
        await page.waitForFunction(() => urbanViewer.widgets.find(widget => widget.layer.id === 'temperature').loadedTime === 600);
        report.numeric = await page.evaluate(async () => {
          const widget = urbanViewer.widgets.find(item => item.layer.id === 'temperature');
          const raw = await widget.source.frame(10);
          const THREE = await import('/src/visualization/vendor/three/build/three.module.js');
          const [east, north, height] = widget.data.positions[0];
          widget.group.updateMatrixWorld(true);
          const hit = widget.pick({raycaster: new THREE.Raycaster(new THREE.Vector3(east, height + 20, -north), new THREE.Vector3(0, -1, 0))});
          return {displayed: widget.current[0], raw: raw[widget.indices[0]], range: widget.range, hit};
        });
        if (Math.abs(report.numeric.displayed - report.numeric.raw) > 1e-5) throw new Error('Temperature display differs from retained NPY');
        if (report.numeric.range[1] - report.numeric.range[0] < 1) throw new Error('Temperature legend is stuck at the initial condition');
        if (!report.numeric.hit || Math.abs(report.numeric.hit.value - report.numeric.raw) > 1e-5) throw new Error('Temperature selection differs from retained NPY');
      }
      const counts = report.status.match(/(\d+)\s*\/\s*(\d+)/);
      if (!counts || counts[1] !== counts[2]) throw new Error('Some layers failed to load');
      if (scenario === 'traffic') {
        if (!report.layers.some(layer => layer.kind === 'trajectories')) throw new Error('Missing traffic replay');
      } else if (['wind', 'temperature', 'surface'].some(id => !report.layers.some(layer => layer.id === id))) {
        throw new Error('Missing climate layer');
      }
      await page.screenshot({path: path.join(output, `${scenario}.png`)});
      const checks = await page.evaluate(() => {
        const dynamic = urbanViewer.widgets.find(widget => widget.layer.sampling !== 'static');
        dynamic.setVisible(false);
        const hidden = !dynamic.group.visible;
        dynamic.setVisible(true);
        urbanViewer.setTime(601);
        const outside = urbanViewer.widgets.filter(widget => widget.layer.sampling !== 'static').every(widget => !widget.available);
        urbanViewer.dispose();
        return {hidden, outside, disposed: urbanViewer.widgets.every(widget => widget.disposed)};
      });
      if (!Object.values(checks).every(Boolean)) throw new Error(JSON.stringify(checks));
      reports.push({scenario, ...report, checks, errors});
      await page.close();
    }
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(reports, null, 2));
    console.log(JSON.stringify(reports, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });

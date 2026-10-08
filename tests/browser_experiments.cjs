(async () => {
  const { default: puppeteer } = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const fs = require('node:fs'),
    cp = require('node:child_process');
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome',
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  const reports = [];
  try {
    for (const scene of ['actuator_lab', 'windfarm']) {
      const page = await browser.newPage();
      await page.setViewport({ width: 1280, height: 900 });
      const errors = [];
      page.on('pageerror', (e) => errors.push(e.message));
      await page.goto(`http://127.0.0.1:8770/?scene=${scene}`, { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => window.urbanViewer?.widgets.length === 1, {
        timeout: 60000,
      });
      const time = scene === 'windfarm' ? 3 : 1.25;
      await page.evaluate((t) => urbanViewer.setTime(t), time);
      await page.waitForFunction(
        (t) => urbanViewer.widgets[0].loadedTime === t,
        { timeout: 60000 },
        time,
      );
      const report = await page.evaluate(() => {
        const w = urbanViewer.widgets[0];
        return {
          scene: urbanViewer.manifest.scene_id,
          run: urbanViewer.manifest.run_id,
          time: w.loadedTime,
          index: w.indices[0],
          position: w.data.positions[0],
          velocity: w.current[0],
          status: document.getElementById('status').textContent,
        };
      });
      const expected = JSON.parse(
        cp.execFileSync(
          'python3',
          [
            '-c',
            `import json,numpy as np,sys\nfrom pathlib import Path\nr=json.loads(sys.argv[1]);p=Path('project')/r['scene']/'runs'/r['run'];m=json.loads((p/'manifest.json').read_text());l=m['layers'][0];e=l['encoding'];ts=m['time']['samples'];t=r['time'];i=max(i for i,v in enumerate(ts) if v<=t);j=min(i+1,len(ts)-1);w=0 if i==j else (t-ts[i])/(ts[j]-ts[i]);read=lambda k:np.load(p/e['frame_assets'][k])[0] if l['format']=='npy_frames' else np.load(p/l['asset'])[k];a,b=read(i).reshape(3,-1),read(j).reshape(3,-1);k=r['index'];v=a[:,k].astype(float)*(1-w)+b[:,k].astype(float)*w;ny,nx=e['shape'][-2:];y,x=divmod(k,nx);h=float(np.load(p/e['height_asset'])[y,x]) if 'height_asset' in e else 0;pos=[e['origin_m'][0]+(x+.5)*e['spacing_m'][0],e['origin_m'][1]+(y+.5)*e['spacing_m'][1],e['origin_m'][2]+h];print(json.dumps({'velocity':v.tolist(),'position':pos}))`,
            JSON.stringify(report),
          ],
          { encoding: 'utf8' },
        ),
      );
      for (const field of ['position', 'velocity'])
        if (report[field].some((v, i) => Math.abs(v - expected[field][i]) > 1e-6))
          throw Error(`${scene}: ${field} differs from source`);
      if (errors.length) throw Error(errors.join('\n'));
      report.errors = errors;
      reports.push(report);
      await page.screenshot({ path: `cache/framework/browser/${scene}.png` });
      await page.close();
    }
    fs.writeFileSync(
      'cache/framework/browser/experiments-report.json',
      JSON.stringify(reports, null, 2),
    );
    console.log(JSON.stringify(reports, null, 2));
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});

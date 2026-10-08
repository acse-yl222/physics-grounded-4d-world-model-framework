(async () => {
  const {default: puppeteer} = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const assert = require('node:assert/strict');
  const fs = require('node:fs');
  const base = process.env.UWM_VIEWER_URL || 'http://127.0.0.1:8773/';
  const output = 'cache/thapar_university/city-browser';
  fs.mkdirSync(output, {recursive: true});
  const browser = await puppeteer.launch({executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome',
    headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader']});
  try {
    const page = await browser.newPage();
    await page.setViewport({width: 1440, height: 960});
    const errors = [], failures = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => {if (response.status() >= 400 && !response.url().endsWith('favicon.ico')) failures.push([response.status(), response.url()]);});
    await page.goto(new URL('src/visualization/legacy/viewer/3d/?scene=thapar_university&lite=0&expansion=0', base).href);
    await page.waitForFunction(() => window.viewer && document.querySelector('#loading').classList.contains('hide'), {timeout: 180000});
    assert.equal(await page.$eval('#scene-select', element => element.value), 'thapar_university');
    await page.screenshot({path: output + '/overview.png'});
    const results = [];
    for (const field of ['wind', 'temp', 'solar']) {
      await page.click(`.tab[data-field="${field}"]`);
      await page.evaluate(() => {
        document.querySelector('#auto').checked = false;
        if (viewer.state.playing) document.querySelector('#play').click();
        const slider = document.querySelector('#step');
        slider.value = Math.round((Number(slider.min) + Number(slider.max)) / 2);
        slider.dispatchEvent(new Event('input', {bubbles: true}));
      });
      await page.waitForFunction(key => viewer.state.phase === key && !viewer.state.loading && viewer.state.fields[key], {timeout: 60000}, field);
      results.push(await page.evaluate(async key => {
        const current = viewer.state.fields[key];
        const step = viewer.state.step;
        const info = viewer.LAYERS[key];
        const report = {key, step, length: current.length, finite: current.every(Number.isFinite),
          minimum: current.reduce((value, next) => Math.min(value, next), Infinity),
          maximum: current.reduce((value, next) => Math.max(value, next), -Infinity),
          clock: document.querySelector('#time-label').textContent};
        if (key !== 'solar') {
          const {getFrame, f16} = await import('/src/visualization/legacy/viewer/npy.js');
          const frame = Math.max(0, Math.min(info.frames - 1, Math.round((step * viewer.SCENE.timeline.step_s - info.t0_s) / info.step_s)));
          const raw = f16(await getFrame(info.file, frame));
          let maximumError = 0;
          const range = info.web_range;
          for (let index = 0; index < raw.length; index++) {
            const value = Math.max(range[0], Math.min(range[1], raw[index]));
            maximumError = Math.max(maximumError, Math.abs(value - current[index]));
          }
          report.maximumEncodingError = maximumError;
          report.encodingTolerance = (range[1] - range[0]) / 255 / 2 + 1e-4;
        }
        return report;
      }, field));
      assert.ok(results.at(-1).finite);
      if (field !== 'solar') assert.ok(results.at(-1).maximumEncodingError <= results.at(-1).encodingTolerance, JSON.stringify(results.at(-1)));
      if (field === 'wind') {
        await page.click('#l-part');
        await page.waitForFunction(() => viewer.scene.children.some(object => object.isLineSegments && object.renderOrder === 4 && object.visible && object.geometry.attributes.position.array.some(value => value !== 0)), {timeout: 15000});
        results.at(-1).particlesVisible = true;
      }
      await new Promise(resolve => setTimeout(resolve, 800));
      await page.screenshot({path: `${output}/${field}.png`});
    }
    await page.select('#solar-date', '20251221');
    await page.waitForFunction(() => !viewer.state.loading && document.querySelector('#time-label').textContent.includes('December'));
    await page.goto(new URL('src/visualization/viewer/?scene=thapar_university', base).href);
    await page.waitForFunction(() => window.urbanViewer?.widgets.length === 2 && document.querySelector('#status').textContent.includes('2 / 2'), {timeout: 120000});
    assert.equal(await page.$eval('#view', element => element.value), 'city');
    assert.ok(await page.$eval('#city-viewer-link', element => element.href.includes('viewer/3d/?scene=thapar_university')));
    await page.evaluate(() => urbanViewer.setTime(5000));
    await page.waitForFunction(() => urbanViewer.widgets.find(widget => widget.layer.id === 'wind').loadedTime === 5000, {timeout: 30000});
    await page.screenshot({path: output + '/protocol.png'});
    assert.ok(await page.evaluate(() => {urbanViewer.dispose();return urbanViewer.widgets.every(widget => widget.disposed);}));
    await page.goto(base);
    await page.waitForSelector('[data-scene="thapar_university"] a');
    assert.deepEqual(errors, []);
    assert.deepEqual(failures, []);
    const report = {results, errors, failures, scene: 'thapar_university', winterSwitch: true, protocolDefault: true, homeEntry: true, disposal: true};
    fs.writeFileSync(output + '/report.json', JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error); process.exit(1);});

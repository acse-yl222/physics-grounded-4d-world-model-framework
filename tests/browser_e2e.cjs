// Real CLI-retained GLB and binary fields, served from an independent data root.
(async () => {
  const { default: puppeteer } = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const assert = require('node:assert/strict');
  const fs = require('node:fs');
  const path = require('node:path');
  const output = process.env.UWM_BROWSER_OUTPUT;
  const expected = JSON.parse(fs.readFileSync(path.join(output, 'binary-expected.json')));
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  const page = await browser.newPage();
  const errors = [],
    ranges = [];
  const report = { passed: false };
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('response', (r) => {
    if (new URL(r.url()).pathname.endsWith('.npy')) {
      ranges.push({ url: r.url(), status: r.status(), range: r.headers()['content-range'] });
    } else if (r.status() >= 400 && !r.url().endsWith('/favicon.ico')) {
      errors.push(`HTTP ${r.status()}: ${r.url()}`);
    }
  });
  page.on('requestfailed', (r) => {
    if (r.failure().errorText !== 'net::ERR_ABORTED')
      errors.push(r.failure().errorText + ': ' + r.url());
  });
  async function loaded(count) {
    await page.waitForFunction(() => window.urbanViewer, { timeout: 15000 });
    assert.equal(
      await page.$eval('#status', (el) => el.textContent),
      `${count} / ${count} layers ready`,
    );
    assert.equal(
      await page.$eval('#layers', (el) => el.textContent.includes('Unavailable:')),
      false,
    );
  }
  function closeMatrix(actual, wanted) {
    assert.equal(actual.length, wanted.length);
    actual.forEach((row, i) => {
      assert.equal(row.length, wanted[i].length);
      row.forEach((value, j) =>
        assert.ok(
          Number.isFinite(value) && Math.abs(value - wanted[i][j]) < 1e-6,
          `Unexpected value at ${i}, ${j}: ${value} instead of ${wanted[i][j]}`,
        ),
      );
    });
  }
  try {
    await page.setViewport({ width: 1280, height: 900 });
    await page.goto(process.env.UWM_VIEWER_URL, { waitUntil: 'domcontentloaded' });
    await loaded(1);
    assert.equal(await page.$eval('#scene', (el) => el.value), 'south_ken');
    const point = await page.evaluate(() => {
      const camera = urbanViewer.widgets[0].context.camera;
      camera.updateMatrixWorld();
      const p = camera.position.clone().set(4, 3, -4).project(camera);
      const r = document.querySelector('#viewport > canvas').getBoundingClientRect();
      return { x: r.left + ((p.x + 1) * r.width) / 2, y: r.top + ((1 - p.y) * r.height) / 2 };
    });
    await page.mouse.click(point.x, point.y);
    const selection = JSON.parse(await page.$eval('#selection', (el) => el.textContent));
    assert.equal(selection.layer_id, 'geometry');
    assert.ok(Math.abs(selection.position[2] - 3) < 1e-5);
    await page.click('#layers input[type=checkbox]');
    assert.equal(await page.evaluate(() => urbanViewer.widgets[0].group.visible), false);
    await page.click('#layers input[type=checkbox]');
    assert.equal(await page.evaluate(() => urbanViewer.widgets[0].group.visible), true);
    await page.screenshot({ path: path.join(output, 'geometry.png') });
    report.geometry = selection;

    await Promise.all([page.waitForNavigation(), page.select('#view', 'binary_check')]);
    await loaded(2);
    await page.$eval('#time', (el) => {
      el.value = '0.5';
      el.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await page.waitForFunction(
      () =>
        urbanViewer.widgets.every((w) => w.loadedTime === 0.5) ||
        document.querySelector('#layers').textContent.includes('Unavailable:'),
      { timeout: 15000 },
    );
    await loaded(2);
    const values = await page.evaluate(() =>
      urbanViewer.widgets.map((w) => ({
        format: w.layer.format,
        indices: w.indices,
        positions: w.data.positions,
        values: w.current,
      })),
    );
    assert.deepEqual(
      values.map((w) => w.format),
      ['npy_frames', 'npy'],
    );
    for (const w of values) {
      assert.deepEqual(w.indices, expected.indices);
      closeMatrix(w.positions, expected.positions);
      closeMatrix(w.values, expected.values);
    }
    for (const asset of ['frame_0.npy', 'frame_1.npy', 'flow.npy', 'height.npy', 'mask.npy']) {
      assert.ok(
        ranges.some((r) => r.url.endsWith('/' + asset)),
        `Missing Range read: ${asset}`,
      );
    }
    assert.ok(ranges.every((r) => r.status === 206 && r.range?.startsWith('bytes ')));
    await page.screenshot({ path: path.join(output, 'binary.png') });
    await page.evaluate(() => urbanViewer.setTime(99));
    assert.equal(await page.evaluate(() => urbanViewer.widgets.some((w) => w.available)), false);
    assert.equal(
      await page.evaluate(() => {
        urbanViewer.dispose();
        urbanViewer.dispose();
        return urbanViewer.widgets.every((w) => w.disposed && w.group.parent === null);
      }),
      true,
    );
    assert.deepEqual(errors, []);
    report.binary = values;
    report.ranges = ranges;
    report.passed = true;
  } catch (error) {
    report.error = error.message;
    await page.screenshot({ path: path.join(output, 'failure.png') }).catch(() => {});
    throw error;
  } finally {
    report.errors = errors;
    fs.writeFileSync(path.join(output, 'browser-report.json'), JSON.stringify(report, null, 2));
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});

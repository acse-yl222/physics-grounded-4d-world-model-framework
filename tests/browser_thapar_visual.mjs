import assert from 'node:assert/strict';
import fs from 'node:fs';
const {default: puppeteer} = await import(process.env.PUPPETEER_MODULE || '../cache/stream/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js');
const base = process.env.UWM_VIEWER_URL || 'http://127.0.0.1:8773/';
const root = process.env.THAPAR_GEOMETRY_ROOT || 'project/thapar_university/geometry/visual_campus_20261007_v2';
const runId = process.env.THAPAR_RUN_ID || 'visual_campus_20261007_geometry';
const viewNames = process.env.THAPAR_VIEWS?.split(',') || ['visual_campus_library', 'visual_campus_hostel', 'visual_campus'];
const widgetCount = Number(process.env.THAPAR_WIDGET_COUNT || 1);
const coverage = JSON.parse(fs.readFileSync(root + '/coverage.json'));
const expectedIds = coverage.detailed_ids || coverage.campus_ids;
const modules = JSON.parse(fs.readFileSync(root + '/src/modules.json'));
const artisticIds = expectedIds.filter(identity => modules[identity] === 'visual_detail');
const browser = await puppeteer.launch({executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome', headless: true,
  args: ['--no-sandbox', '--enable-unsafe-swiftshader']});
try {
  const page = await browser.newPage();
  await page.setViewport({width: 1440, height: 960});
  const errors = [], failures = [], views = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => { if (response.status() >= 400 && !response.url().endsWith('favicon.ico')) failures.push(response.url()); });
  for (const view of viewNames) {
    await page.goto(new URL(`src/visualization/viewer/?scene=thapar_university&view=${view}`, base).href);
    await page.waitForFunction(count => window.urbanViewer?.widgets.length === count, {timeout: 240000}, widgetCount);
    const result = await page.evaluate(() => {
      const ids = new Set();
      const detailedIds = new Set();
      const roofIds = new Set();
      urbanViewer.widgets[0].group.traverse(object => {
        if (object.userData.building_id) ids.add(object.userData.building_id);
        if (object.userData.detail_basis && object.userData.building_id) detailedIds.add(object.userData.building_id);
      });
      for (const widget of urbanViewer.widgets) widget.group.traverse(object => {
        if (object.userData.source_building_id) roofIds.add(object.userData.source_building_id);
      });
      return {ids: [...ids], detailedIds: [...detailedIds], run: urbanViewer.manifest.run_id, note: document.querySelector('#source-note').textContent,
        roofCount: roofIds.size, expectedRoofs: urbanViewer.manifest.provenance.parameters.roof_overlay_buildings || 0,
        staticOnly: urbanViewer.widgets.every(widget => widget.layer.sampling === 'static')};
    });
    assert.equal(result.run, runId);
    assert.ok(result.staticOnly);
    assert.ok(result.note.includes('非实测'));
    assert.ok(expectedIds.every(identity => result.ids.includes(identity)));
    assert.ok(artisticIds.every(identity => result.detailedIds.includes(identity)));
    assert.equal(result.roofCount, result.expectedRoofs);
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.screenshot({path: root + '/' + view + '.png'});
    views.push({view, loadedDetailedBuildings: expectedIds.length, loadedRoofOverlays: result.roofCount, staticOnly: result.staticOnly});
  }
  const visibility = await page.evaluate(() => {
    return urbanViewer.widgets.every(widget => {
      widget.setVisible(false); const hidden = !widget.group.visible;
      widget.setVisible(true); return hidden && widget.group.visible;
    });
  });
  assert.ok(visibility);
  await page.evaluate(() => urbanViewer.dispose());
  assert.equal(errors.length, 0, JSON.stringify(errors));
  assert.equal(failures.length, 0, JSON.stringify(failures));
  const report = {errors, failures, views, visibility, disposal: true};
  fs.writeFileSync(root + '/browser_report.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
} finally {
  await browser.close();
}

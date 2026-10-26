#!/usr/bin/env node
// Headless driver for the image-to-three.js studio (Chromium via Playwright).
//
//   node render.cjs landmark <id> [--out DIR] [--views ne,sw,street_s] [--shadows]
//   node render.cjs region <x> <y> <r> [--out DIR] [--views ne,top]
//   --zoom F scales the camera distance (0.4 = close-up); views also take top.
//   node render.cjs gallery [--kind street|vehicle|vegetation] [--detail low] [--out DIR]            (all resources/ assets)
//   node render.cjs export --out DIR [--layers buildings,ground,trees,landmarks] [--tile M]
//
// Screenshots are written as <out>/<name>_<view>.png; exports as <out>/*.glb.
'use strict';
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '../../..');
const TYPES = {
  '.html': 'text/html',
  '.mjs': 'text/javascript',
  '.js': 'text/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.wasm': 'application/wasm',
};

function args() {
  const a = process.argv.slice(2),
    opts = { _: [] };
  for (let k = 0; k < a.length; k++) {
    if (a[k].startsWith('--')) {
      const key = a[k].slice(2);
      opts[key] = a[k + 1] && !a[k + 1].startsWith('--') ? a[++k] : true;
    } else opts._.push(a[k]);
  }
  return opts;
}

function serve(outDir) {
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent(req.url.split('?')[0]);
    if (req.method === 'PUT' && url.startsWith('/__out/')) {
      const file = path.join(outDir, path.basename(url));
      const part = Number(new URL(req.url, 'http://x').searchParams.get('part') ?? 0);
      const chunks = [];
      req.on('data', (c) => chunks.push(c));
      req.on('end', () => {
        (part ? fs.appendFileSync : fs.writeFileSync)(file, Buffer.concat(chunks));
        res.writeHead(200).end('ok');
      });
      return;
    }
    const file = path.join(ROOT, url);
    if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404).end();
      return;
    }
    res.writeHead(200, { 'content-type': TYPES[path.extname(file)] ?? 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((ok) => server.listen(0, '127.0.0.1', () => ok(server)));
}

async function main() {
  const o = args();
  const mode = o._[0];
  const outDir = path.resolve(
    o.out ?? path.join(ROOT, 'cache/imperial_corridor/image_to_threejs/renders'),
  );
  fs.mkdirSync(outDir, { recursive: true });
  const server = await serve(outDir);
  const base = `http://127.0.0.1:${server.address().port}/src/urban_geometry/image_to_threejs/studio.html`;
  const browser = await chromium.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
  });
  const page = await browser.newPage({
    viewport: { width: Number(o.width ?? 1280), height: Number(o.height ?? 800) },
  });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on(
    'console',
    (m) => (m.type() === 'error' || m.type() === 'warning') && errors.push(m.text()),
  );
  try {
    if (mode === 'export') {
      await page.goto(`${base}?mode=export${o.scene ? '&scene=' + o.scene : ''}`);
      await page.waitForFunction(() => window.studio);
      const layers = (o.layers ?? 'buildings,ground,trees,landmarks').split(',');
      const half = Number(o.half ?? 4000);
      const tile = Number(o.tile ?? 2 * half);
      const report = {};
      for (let y = -half; y < half; y += tile)
        for (let x = -half; x < half; x += tile) {
          const tiled = tile < 2 * half;
          const prefix = tiled ? `tile_${(x + half) / tile}_${(y + half) / tile}_` : '';
          const spec = {
            bounds: { x0: x, y0: y, x1: x + tile, y1: y + tile },
            prefix,
            layers: layers.filter((l) => l !== 'landmarks' || (x === -half && y === -half)),
          };
          console.log('export', prefix || 'domain', spec.layers.join(','));
          Object.assign(report, {
            [prefix || 'domain']: await page.evaluate((s) => window.studio.exportLayers(s), spec),
          });
        }
      fs.writeFileSync(path.join(outDir, 'export-report.json'), JSON.stringify(report, null, 2));
      console.log(JSON.stringify(report, null, 2));
    } else {
      let q, name;
      if (mode === 'landmark') {
        name = o._[1];
        q = `landmark=${name}${o.context ? '&context=' + o.context : ''}`;
      } else if (mode === 'region') {
        const [x, y, r] = o._.slice(1);
        name = `region_${x}_${y}_${r}`;
        q = `x=${x}&y=${y}&r=${r}`;
      } else if (mode === 'gallery') {
        name = 'gallery';
        q = `gallery=${o.kind ?? 1}&context=0${o.detail ? '&detail=' + o.detail : ''}`;
        if (o.kind) name = `gallery_${o.kind}`;
      } else throw new Error('mode must be landmark | region | gallery | export');
      if (o.shadows) q += '&shadows=1';
      if (o.zoom) q += `&zoom=${o.zoom}`;
      if (o.scene) q += `&scene=${o.scene}`;
      await page.goto(`${base}?${q}`);
      await page.waitForFunction(() => window.studio, null, { timeout: 60000 });
      await page.evaluate(() => window.studio.ready);
      for (const v of (o.views ?? 'ne,sw,street_s').split(',')) {
        await page.evaluate((vv) => window.studio.view(vv), v);
        const file = path.join(outDir, `${name}_${v}.png`);
        await page.screenshot({ path: file, timeout: 180000 });
        console.log(file);
      }
      console.log(JSON.stringify(await page.evaluate(() => window.studio.stats)));
    }
  } finally {
    if (errors.length)
      console.log('page messages:\n' + [...new Set(errors)].slice(0, 20).join('\n'));
    await browser.close();
    server.close();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

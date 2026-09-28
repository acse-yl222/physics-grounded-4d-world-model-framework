// Exercise real pointer/keyboard controls and navigation on the built public site.
(async () => {
  const {default: puppeteer} = await import(process.env.PUPPETEER_MODULE || 'puppeteer-core');
  const assert = require('node:assert/strict');
  const base = process.env.P4D_SITE_URL || 'http://127.0.0.1:8773/';
  const browser = await puppeteer.launch({executablePath: process.env.CHROME_PATH || '/opt/google/chrome/chrome', headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader']});
  try {
    const page = await browser.newPage(), errors = [];
    page.on('pageerror', e => { errors.push(e.message); console.error(e.message); });
    await page.setViewport({width: 1280, height: 900});
    await page.goto(new URL('viewer/3d/?scene=south_kensington&lite=1&expansion=0', base).href);
    await page.waitForFunction(() => document.querySelector('#loading')?.classList.contains('hide'), {timeout: 120000});
    console.log('Loaded South Kensington');
    async function reachable(selector) {
      assert.ok(await page.$eval(selector, e => {
        const r = e.getBoundingClientRect(), hit = document.elementFromPoint(r.x+r.width/2, r.y+r.height/2);
        return e === hit || e.contains(hit);
      }), `${selector} is obscured`);
    }
    await reachable('#scene-select'); await reachable('#scene-home');
    assert.deepEqual(await page.$$eval('#scene-select option', xs => xs.map(x => x.value)), ['south_ken','white_city','windfarm']);
    // Space must use the same replay pause control as the button.
    await page.click('#gl', {offset: {x: 500, y: 500}});
    const previous = await page.$eval('#play', e => e.textContent);
    await page.keyboard.press('Space');
    assert.notEqual(await page.$eval('#play', e => e.textContent), previous);
    const pausedShot = await page.evaluate(() => { viewer.replay.shotUntil = performance.now()+50; return viewer.replay.shot; });
    await new Promise(resolve => setTimeout(resolve,250));
    assert.equal(await page.evaluate(() => viewer.replay.playing), false, 'Paused replay must not auto-resume at a tour boundary');
    assert.equal(await page.evaluate(() => viewer.replay.shot), pausedShot);
    const replayTime = await page.$eval('#step', e => e.value);
    await page.keyboard.press('ArrowRight');
    assert.notEqual(await page.$eval('#step', e => e.value), replayTime, 'Replay keyboard seek must target replay time');
    await page.keyboard.press('Space');
    assert.equal(await page.$eval('#play', e => e.textContent), previous);
    for (const field of ['wind','temp','wind']) {
      const selector = `.tab[data-field="${field}"]`;
      await reachable(selector); await page.click(selector);
      await page.waitForFunction(s => document.querySelector(s).classList.contains('active'), {timeout: 1500}, selector);
    }
    await page.click('#play');
    const paused = await page.$eval('#step', e => e.value);
    await new Promise(resolve => setTimeout(resolve, 1100));
    assert.equal(await page.$eval('#step', e => e.value), paused, 'Pause must hold the selected frame');
    await page.focus('#step'); await page.keyboard.press('ArrowRight');
    assert.notEqual(await page.$eval('#step', e => e.value), paused, 'Time slider must respond to keyboard input');
    const checked = await page.$eval('#l-wind', e => e.checked);
    await reachable('#l-wind'); await page.click('#l-wind');
    assert.equal(await page.$eval('#l-wind', e => e.checked), !checked);
    console.log('Desktop controls passed');
    await page.setViewport({width: 390, height: 844});
    await reachable('#scene-select'); await reachable('#panel-toggle');
    await page.click('#panel-toggle');
    await page.waitForSelector('#layers.open'); await reachable('#l-wind'); await reachable('#play');
    const mobileChecked = await page.$eval('#l-wind', e => e.checked);
    await page.click('#l-wind');assert.equal(await page.$eval('#l-wind', e => e.checked), !mobileChecked);
    await page.click('#panel-toggle');
    assert.equal(await page.$eval('#layers', e => getComputedStyle(e).display), 'none');
    console.log('Mobile controls passed');
    await page.setViewport({width:1280,height:900});
    await Promise.all([page.waitForNavigation(), page.select('#scene-select','white_city')]);
    await page.waitForFunction(() => document.querySelector('#loading')?.classList.contains('hide'), {timeout:120000});
    console.log('Loaded White City');
    assert.ok(page.url().includes('scene=white_city'));await reachable('#scene-select');
    await Promise.all([page.waitForNavigation(),page.select('#scene-select','windfarm')]);
    await page.waitForFunction(() => window.movie?.ready, {timeout:120000});
    console.log('Loaded windfarm');
    await page.select('#model','mac_live'); await page.click('#play');
    const time = await page.$eval('#time', e => e.value);
    await new Promise(resolve => setTimeout(resolve,300));
    assert.equal(await page.$eval('#time', e => e.value),time);
    await page.focus('#time');await page.keyboard.press('ArrowRight');
    assert.notEqual(await page.$eval('#time', e => e.value),time);
    await page.setViewport({width:390,height:844});
    await page.waitForFunction(() => document.querySelector('#view').width === innerWidth && document.querySelector('#view').height === innerHeight);
    await reachable('#scene-select');
    await Promise.all([page.waitForNavigation(),page.select('#scene-select','south_ken')]);
    assert.equal(new URL(page.url()).searchParams.get('lite'), '1');
    await page.waitForFunction(() => !document.querySelector('#scene-select').disabled);
    await reachable('#scene-home');
    await Promise.all([page.waitForNavigation(),page.click('#scene-home')]);
    await page.waitForSelector('[data-scene="windfarm"] a');
    assert.deepEqual(errors, []);
    console.log('PASS: desktop/mobile hit targets, replay keyboard pause, field switching, time and layer controls, three-scene round trip, windfarm resize, home navigation');
  } finally { await browser.close(); }
})().catch(e => {console.error(e);process.exit(1);});

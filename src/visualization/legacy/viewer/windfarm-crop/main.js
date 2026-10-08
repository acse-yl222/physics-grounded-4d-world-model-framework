import { setDataBase, npy, getFrame, loadMask } from '../npy.js';
const base = '../../scenes/windfarm_crop/';
setDataBase(base);
const $ = (id) => document.getElementById(id),
  palette = [
    [38, 63, 131],
    [22, 139, 166],
    [103, 200, 164],
    [243, 220, 105],
    [237, 116, 69],
  ];
let g,
  a,
  b,
  mask,
  ground,
  coverage,
  nx,
  ny,
  ad,
  bd,
  view,
  playing = false,
  epoch = 0,
  request = 0;
async function json(p) {
  const r = await fetch(base + p, { cache: 'no-cache' });
  if (!r.ok) throw Error(p + ': ' + r.status);
  return r.json();
}
function color(v, diff) {
  if (diff) {
    const f = Math.min(1, Math.abs(v) / 6),
      to = v < 0 ? [56, 118, 191] : [228, 103, 66];
    return [233, 239, 243].map((c, k) => c + (to[k] - c) * f);
  }
  const t = Math.max(0, Math.min(4, (v / 20) * 4)),
    i = Math.min(3, Math.floor(t)),
    f = t - i;
  return palette[i].map((c, k) => c + (palette[i + 1][k] - c) * f);
}
function setView() {
  if ($('focus').value === 'all') view = [0, 0, nx, ny];
  else {
    const t = g.turbines[+$('focus').value],
      x = (t.hub_xyz_m[0] - g.origin_xyz_m[0]) / 4,
      y = (t.hub_xyz_m[1] - g.origin_xyz_m[1]) / 4;
    view = [
      Math.max(0, Math.min(nx - 160, Math.floor(x - 45))),
      Math.max(0, Math.min(ny - 160, Math.floor(y - 80))),
      160,
      160,
    ];
  }
  render();
}
function draw(id, data, diff = false) {
  const can = $(id),
    [x0, y0, w, h] = view;
  can.width = w;
  can.height = h;
  const ctx = can.getContext('2d'),
    im = ctx.createImageData(w, h);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const i = (y + y0) * nx + x + x0;
      let rgb = mask[i] ? [74, 91, 103] : color(data[i], diff);
      if (
        $('contours').checked &&
        x + x0 > 0 &&
        Math.floor(ground[i] / 20) !== Math.floor(ground[i - 1] / 20)
      )
        rgb = rgb.map((v) => v * 0.65);
      im.data.set([...rgb, 255], ((h - 1 - y) * w + x) * 4);
    }
  ctx.putImageData(im, 0, 0);
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = view[2] === nx ? 2 : 1;
  for (const t of g.turbines) {
    const x = (t.hub_xyz_m[0] - g.origin_xyz_m[0]) / 4 - x0,
      y = h - ((t.hub_xyz_m[1] - g.origin_xyz_m[1]) / 4 - y0),
      r = t.radius_m / 4;
    ctx.beginPath();
    ctx.moveTo(x, y - r);
    ctx.lineTo(x, y + r);
    ctx.stroke();
  }
}
function terrain() {
  const can = $('terrain'),
    ctx = can.getContext('2d');
  can.width = nx;
  can.height = ny;
  const im = ctx.createImageData(nx, ny),
    [lo, hi] = g.ground_range_m;
  for (let y = 0; y < ny; y++)
    for (let x = 0; x < nx; x++) {
      const i = y * nx + x,
        t = (ground[i] - lo) / (hi - lo);
      im.data.set([45 + t * 165, 70 + t * 140, 61 + t * 100, 255], ((ny - 1 - y) * nx + x) * 4);
    }
  ctx.putImageData(im, 0, 0);
  for (const t of g.turbines) {
    ctx.beginPath();
    ctx.arc(
      (t.hub_xyz_m[0] - g.origin_xyz_m[0]) / 4,
      ny - (t.hub_xyz_m[1] - g.origin_xyz_m[1]) / 4,
      4,
      0,
      7,
    );
    ctx.fillStyle = 'white';
    ctx.fill();
  }
  ctx.strokeStyle = '#7ce2e5';
  ctx.lineWidth = 2;
  ctx.strokeRect(view[0], ny - view[1] - view[3], view[2], view[3]);
  $('terrain-info').textContent =
    `Local datum elevation ${lo.toFixed(1)}–${hi.toFixed(1)} m; Source terrain coverage ${(g.terrain_coverage_fraction * 100).toFixed(1)}%; uncovered edges use boundary extension.`;
}
function render() {
  if (!ad) return;
  const n = nx * ny,
    d = Float32Array.from({ length: n }, (_, i) => ad[i] - bd[i]);
  draw('control', ad);
  draw('actuator', bd);
  draw('difference', d, true);
  terrain();
}
async function show() {
  const token = ++request,
    i = +$('time').value;
  try {
    const [x, y] = await Promise.all([getFrame(a.files[i], 0), getFrame(b.files[i], 0)]);
    if (token !== request) return;
    ad = x;
    bd = y;
    render();
    $('clock').textContent = `${i + 1}/${a.times.length} frames · ${a.times[i].toFixed(1)} s`;
    $('stats').textContent =
      `Terrain-following slice: AGL ${g.slice_agl_m} m(Sampling error ±2 m)· ${g.turbines.length} turbines · 4 m Native grid`;
    $('rows').replaceChildren(
      ...g.turbines.map((t, k) => {
        const row = document.createElement('tr');
        for (const value of [
          t.id.replace('node-', ''),
          a.metrics[i].disk_velocity_m_s[k].toFixed(2),
          b.metrics[i].disk_velocity_m_s[k].toFixed(2),
          (b.metrics[i].thrust_N[k] / 1000).toFixed(1),
        ]) {
          const cell = document.createElement('td');
          cell.textContent = value;
          row.append(cell);
        }
        return row;
      }),
    );
    $('status').textContent =
      `Each run:  ${a.completed_steps} steps · dt ${a.dt_s} s · Measured peak GPU memory ${b.metrics.at(-1).gpu_peak_gib.toFixed(2)} GiB · Displaying axial velocity, not speed magnitude.`;
  } catch (e) {
    $('status').textContent = 'Read failed: ' + e.message;
    stop();
  }
}
function stop() {
  playing = false;
  epoch++;
  $('play').textContent = 'Play';
}
async function tick(e) {
  if (!playing || e !== epoch) return;
  $('time').value = (+$('time').value + 1) % a.times.length;
  await show();
  if (playing && e === epoch) setTimeout(() => tick(e), 180);
}
$('play').onclick = () => {
  if (playing) stop();
  else {
    playing = true;
    $('play').textContent = 'Pause';
    tick(++epoch);
  }
};
$('time').oninput = () => {
  stop();
  show();
};
$('focus').onchange = setView;
$('contours').onchange = render;
for (const id of ['control', 'actuator', 'difference'])
  $(id).onmousemove = (e) => {
    if (!ad) return;
    const r = e.target.getBoundingClientRect(),
      x = Math.floor(((e.clientX - r.left) / r.width) * view[2]) + view[0],
      y = view[1] + view[3] - 1 - Math.floor(((e.clientY - r.top) / r.height) * view[3]),
      i = y * nx + x;
    if (i < 0 || i >= nx * ny) return;
    $('readout').textContent =
      `x ${(g.origin_xyz_m[0] + (x + 0.5) * 4).toFixed(0)} m / y ${(g.origin_xyz_m[1] + (y + 0.5) * 4).toFixed(0)} m · Control ${ad[i].toFixed(3)} / Actuator disk ${bd[i].toFixed(3)} / Difference ${(ad[i] - bd[i]).toFixed(3)} m/s`;
  };
try {
  [g, a, b] = await Promise.all([
    json('geometry.json'),
    json('control/result.json'),
    json('actuator/result.json'),
  ]);
  [mask, ground, coverage] = await Promise.all([
    loadMask('slice_mask.npy'),
    npy('ground.npy').readAll(),
    loadMask('terrain_valid.npy'),
  ]);
  [ny, nx] = g.shape_zyx.slice(1);
  $('summary').textContent =
    `${g.size_xyz_m.join(' × ')} m domain · ${(g.cell_count / 1e6).toFixed(1)} million cells · Two computed runs with matching initial conditions and terrain`;
  $('time').max = a.times.length - 1;
  $('time').value = a.times.length - 1;
  for (const [i, t] of g.turbines.entries())
    $('focus').append(
      Object.assign(document.createElement('option'), {
        value: i,
        textContent: 'Turbine ' + t.id.replace('node-', ''),
      }),
    );
  setView();
  await show();
} catch (e) {
  $('status').textContent = 'Initialization failed: ' + e.message;
}

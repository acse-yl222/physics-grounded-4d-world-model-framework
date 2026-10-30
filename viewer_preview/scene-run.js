/* Bridge a retained presentation run into the existing city viewer. */
export function recordedFrame(layer, seconds) {
  const times = layer.time_s;
  if (!times?.length || seconds < times[0] || seconds > times.at(-1)) return null;
  let index = 0;
  while (index + 1 < times.length && times[index + 1] <= seconds) index++;
  return index;
}

export async function loadRunScene(
  params,
  legacyRoot,
  readJSON = async (url) => {
    const response = await fetch(url, { cache: 'no-cache' });
    if (!response.ok) throw new Error(`Scene asset unavailable (${response.status}): ${url}`);
    return response.json();
  },
) {
  const id = params.get('scene'),
    run = params.get('run');
  if (!/^[a-z][a-z0-9_]*$/.test(id || '') || !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(run || ''))
    throw new Error('Use a canonical scene ID and a retained run ID');
  const site = new URL(
    legacyRoot.pathname.endsWith('/src/visualization/legacy/') ? '../../../' : './',
    legacyRoot,
  );
  const base = new URL(`project/${id}/runs/${run}/`, site);
  const manifest = await readJSON(new URL('manifest.json', base));
  if (
    manifest.schema_version !== '1.1.0' ||
    manifest.status !== 'complete' ||
    manifest.scene_id !== id ||
    manifest.run_id !== run
  )
    throw new Error('Incomplete or incompatible presentation run');
  const assets = new Set([
    ...(manifest.artifacts || []).map((a) => a.asset),
    ...manifest.layers.map((l) => l.asset),
  ]);
  const assetURL = (relative) => {
    if (!assets.has(relative) || relative.includes('\\'))
      throw new Error(`Undeclared scene asset: ${relative}`);
    const url = new URL(relative, base);
    if (!url.href.startsWith(base.href)) throw new Error('Scene asset escapes its retained run');
    return url;
  };
  const descriptor = manifest.artifacts.find((a) => a.id === 'city_scene');
  if (!descriptor) throw new Error('Run has no city presentation descriptor');
  const scene = await readJSON(assetURL(descriptor.asset));
  const dataBase = new URL('./', assetURL(descriptor.asset));
  const relativeToRun = (path, folder = '') =>
    new URL(folder + path, dataBase).href.slice(base.href.length);
  assetURL(relativeToRun(scene.model.url));
  for (const [kind, layer] of Object.entries(scene.layers)) {
    if (kind === 'solar') {
      for (const day of Object.values(layer.dates || {})) {
        assetURL(relativeToRun(day.ghi, 'physics/'));
        assetURL(relativeToRun(day.shadow, 'physics/'));
      }
      continue;
    }
    assetURL(relativeToRun(layer.file, 'physics/'));
    if (
      !layer.time_s?.length ||
      layer.time_s.length !== layer.frames ||
      !layer.time_s.every((t, i) => Number.isFinite(t) && (!i || t > layer.time_s[i - 1]))
    )
      throw new Error('Missing or invalid recorded field times');
  }
  for (const path of Object.values(scene.masks?.footprint || {}))
    assetURL(relativeToRun(path, 'physics/'));
  if (scene.masks?.solid_wind) assetURL(relativeToRun(scene.masks.solid_wind.file, 'physics/'));
  for (const key of ['footprint', 'roof'])
    if (scene.lite?.[key]) assetURL(relativeToRun(scene.lite[key], 'physics/'));
  scene.id = id;
  scene.base = dataBase.href;
  scene.physics = new URL('physics/', dataBase).href;
  scene.url = (relative) => assetURL(relativeToRun(relative)).href;
  scene.index = { default: id, scenes: [{ id, title: scene.title }] };
  scene.protocol_display = { strict_time: true, source_run: run, spatial: manifest.spatial };
  return scene;
}

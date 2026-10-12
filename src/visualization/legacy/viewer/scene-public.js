/* Explicitly selected website resources; source runs keep their original contract. */
export async function loadPublishedScene(
  params,
  legacyRoot,
  readJSON = async (url) => {
    const response = await fetch(url, { cache: 'no-cache' });
    if (!response.ok) throw new Error(`Published scene: HTTP ${response.status}`);
    return response.json();
  },
) {
  const site = new URL(
    legacyRoot.pathname.endsWith('/src/visualization/legacy/') ? '../../../' : './',
    legacyRoot,
  );
  const catalog = await readJSON(new URL('src/visualization/public-scenes.json', site));
  const entry = catalog.scenes.find(
    (item) =>
      item.scene_id === params.get('scene') &&
      item.presentation?.version === params.get('presentation'),
  );
  if (!entry) throw new Error('Unknown published presentation');
  const descriptor = new URL(
    entry.presentation.descriptor,
    catalog.resources_url.replace(/\/?$/, '/'),
  );
  const base = new URL('./', descriptor);
  const scene = await readJSON(descriptor);
  if (scene.id !== entry.scene_id) throw new Error('Published scene identity differs');
  const assetURL = (path) => {
    const url = new URL(path, base);
    if (!url.href.startsWith(base.href)) throw new Error('Published asset escapes its resource');
    return url.href;
  };
  const transport = await readJSON(assetURL('transport.json'));
  if (transport.schema_version !== '1.0.0') throw new Error('Unsupported resource transport');
  const source = await readJSON(assetURL('provenance/source_manifest.json'));
  if (
    source.status !== 'complete' ||
    source.scene_id !== scene.id ||
    source.run_id !== entry.presentation.version
  )
    throw new Error('Published source run differs');
  for (const [key, layer] of Object.entries(scene.layers)) {
    if (key === 'solar') {
      for (const day of Object.values(layer.dates))
        for (const file of [day.ghi, day.shadow])
          if (!transport.npy[file]) throw new Error('Missing solar transport');
    } else if (
      !transport.npy[layer.file] ||
      layer.time_s?.length !== layer.frames ||
      !layer.time_s.every((t, i) => Number.isFinite(t) && (!i || t > layer.time_s[i - 1]))
    )
      throw new Error('Missing field transport or recorded times');
  }
  scene.base = base.href;
  scene.physics = assetURL('physics/');
  scene.url = assetURL;
  scene.model.parts_manifest = assetURL(scene.model.parts_manifest);
  scene.index = { default: scene.id, scenes: [{ id: scene.id, title: scene.title }] };
  scene.protocol_display = {
    strict_time: true,
    published: true,
    source_run: source.run_id,
    spatial: source.spatial,
    npy_transport: transport.npy,
  };
  return scene;
}

#!/usr/bin/env node
// Index landmark modules (landmarks/index.json) and reusable assets
// (resources/index.json): {id, name, claims | file, references, ...}.
// Fails on duplicate claims or modules that break the contract.
// --check verifies the committed indexes instead of rewriting them.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const LANDMARKS = path.join(HERE, 'landmarks');
export const RESOURCES = path.join(HERE, 'resources');
const KINDS = ['street', 'vehicles', 'vegetation'];

function contract(id, source, def, problems) {
  if (/^\s*import\s/m.test(source)) problems.push(`${id}: modules must not import`);
  if (!def || def.id !== id || typeof def.build !== 'function') {
    problems.push(`${id}: default export must be { id: '${id}', build }`);
    return false;
  }
  const refs = def.references ?? [];
  if (!refs.length || refs.some((r) => !/^https?:\/\//.test(r.url ?? '')))
    problems.push(`${id}: needs references with http(s) URLs`);
  return true;
}

/** Reusable assets in resources/<kind>/<id>.mjs. */
export async function collectResources(dir = RESOURCES) {
  const assets = [],
    problems = [];
  for (const kind of KINDS)
    for (const file of fs
      .readdirSync(path.join(dir, kind))
      .filter((f) => f.endsWith('.mjs'))
      .sort()) {
      const id = file.slice(0, -4);
      const full = path.join(dir, kind, file);
      const def = (await import(pathToFileURL(full).href)).default;
      if (!contract(id, fs.readFileSync(full, 'utf8'), def, problems)) continue;
      if (assets.some((a) => a.id === id)) problems.push(`${id}: duplicate asset id`);
      if (!(def.size?.length === 3 && def.size.every((v) => v > 0)))
        problems.push(`${id}: size must be [width, depth, height] in metres`);
      assets.push({
        id,
        kind: def.kind,
        name: def.name,
        file: `${kind}/${file}`,
        size: def.size,
        references: def.references,
        notes: def.notes ?? '',
      });
    }
  return { index: { assets }, problems };
}

export async function collect(dir = LANDMARKS) {
  const index = [],
    owner = new Map(),
    problems = [];
  // Files starting with '_' are drafts and are not indexed.
  for (const file of fs
    .readdirSync(dir)
    .filter((f) => f.endsWith('.mjs') && !f.startsWith('_'))
    .sort()) {
    const id = file.slice(0, -4);
    const source = fs.readFileSync(path.join(dir, file), 'utf8');
    const def = (await import(pathToFileURL(path.join(dir, file)).href)).default;
    if (!contract(id, source, def, problems)) continue;
    const refs = def.references;
    for (const c of def.claims ?? []) {
      if (owner.has(c)) problems.push(`${id}: claim ${c} already claimed by ${owner.get(c)}`);
      owner.set(c, id);
    }
    index.push({
      id,
      name: def.name,
      claims: def.claims ?? [],
      references: refs,
      notes: def.notes ?? '',
    });
  }
  return { index, problems, claimed: owner.size };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const check = process.argv.includes('--check');
  const { index, problems, claimed } = await collect();
  const resources = await collectResources();
  problems.push(...resources.problems);
  for (const [target, data] of [
    [path.join(LANDMARKS, 'index.json'), index],
    [path.join(RESOURCES, 'index.json'), resources.index],
  ]) {
    const text = JSON.stringify(data, null, 2) + '\n';
    if (!check) fs.writeFileSync(target, text);
    else if (!fs.existsSync(target) || fs.readFileSync(target, 'utf8') !== text)
      problems.push(`${path.relative(HERE, target)} is out of date; run collect_landmarks.mjs`);
  }
  console.log(
    `${index.length} landmarks (${claimed} claimed footprints), ${resources.index.assets.length} assets`,
  );
  if (problems.length) {
    console.error(problems.join('\n'));
    process.exit(1);
  }
}

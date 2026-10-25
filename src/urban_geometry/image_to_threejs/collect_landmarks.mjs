#!/usr/bin/env node
// Index landmark modules into landmarks/index.json ({id, name, claims, references,
// notes}); fails on duplicate claims or modules that break the contract.
// --check verifies the committed index instead of rewriting it.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const LANDMARKS = path.join(path.dirname(fileURLToPath(import.meta.url)), 'landmarks');

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
    if (/^\s*import\s/m.test(source)) problems.push(`${id}: modules must not import`);
    const def = (await import(pathToFileURL(path.join(dir, file)).href)).default;
    if (!def || def.id !== id || typeof def.build !== 'function') {
      problems.push(`${id}: default export must be { id: '${id}', build }`);
      continue;
    }
    const refs = def.references ?? [];
    if (!refs.length || refs.some((r) => !/^https?:\/\//.test(r.url ?? '')))
      problems.push(`${id}: needs references with http(s) URLs`);
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
  const { index, problems, claimed } = await collect();
  const target = path.join(LANDMARKS, 'index.json');
  const text = JSON.stringify(index, null, 2) + '\n';
  if (process.argv.includes('--check')) {
    if (!fs.existsSync(target) || fs.readFileSync(target, 'utf8') !== text)
      problems.push('landmarks/index.json is out of date; run collect_landmarks.mjs');
  } else fs.writeFileSync(target, text);
  console.log(`${index.length} landmarks, ${claimed} claimed footprints`);
  if (problems.length) {
    console.error(problems.join('\n'));
    process.exit(1);
  }
}

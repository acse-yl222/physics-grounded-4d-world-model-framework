// panel.js -- schema-driven building parameter panel (view + edit + rebuild)

let SCHEMA = null;
async function schema() {
  if (!SCHEMA) SCHEMA = await (await fetch('/api/schema')).json();
  return SCHEMA;
}

// ---- dot-path helpers on the spec document
function pget(o, path) {
  let cur = o;
  for (const k of path.split('.')) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = cur[k];
  }
  return cur;
}
function pset(o, path, val) {
  const ks = path.split('.');
  let cur = o;
  for (const k of ks.slice(0, -1)) {
    if (cur[k] == null || typeof cur[k] !== 'object') cur[k] = {};
    cur = cur[k];
  }
  cur[ks[ks.length - 1]] = val;
}

// ---- linear rgb (spec) <-> sRGB hex (input type=color)
function lin2hex(rgb) {
  const f = c => {
    c = Math.max(0, Math.min(1, c));
    c = c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
    return Math.round(c * 255).toString(16).padStart(2, '0');
  };
  return '#' + f(rgb[0]) + f(rgb[1]) + f(rgb[2]);
}
function hex2lin(hex) {
  const f = h => {
    let c = parseInt(h, 16) / 255;
    return +(c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)).toFixed(4);
  };
  return [f(hex.slice(1, 3)), f(hex.slice(3, 5)), f(hex.slice(5, 7))];
}

const el = (tag, cls, html) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
};

// bilingual pickers (window.LANG from i18n.js)
const L = (o, k) => (window.LANG === 'en' && o[k + '_en']) ? o[k + '_en'] : o[k];

// ---- one scalar control; writes edits into work-spec, records touch
function control(field, value, onEdit, onLive) {
  const row = el('div', 'kv');
  const hint = L(field, 'hint');
  row.appendChild(el('span', 'k', L(field, 'label') + (hint ? ` <small>(${hint})</small>` : '')));
  const holder = el('span', 'v');
  let input;
  if (field.type === 'bool') {
    input = el('input');
    input.type = 'checkbox';
    input.checked = !!value;
    input.onchange = () => onEdit(input.checked);
  } else if (field.type === 'enum') {
    input = el('select');
    input.appendChild(el('option', null, '—'));
    for (const c of field.choices) {
      const o = el('option', null, c);
      o.value = c;
      input.appendChild(o);
    }
    if (value !== undefined) input.value = value;
    input.onchange = () => input.value && onEdit(input.value);
  } else if (field.type === 'color') {
    input = el('input');
    input.type = 'color';
    if (Array.isArray(value)) input.value = lin2hex(value);
    input.oninput = () => { if (onLive) onLive(hex2lin(input.value)); };
    input.onchange = () => onEdit(hex2lin(input.value));
  } else { // int / float -- slider + number pair; sliders stream onLive
    input = el('input');
    input.type = 'number';
    if (field.min !== undefined) input.min = field.min;
    if (field.max !== undefined) input.max = field.max;
    input.step = field.step || (field.type === 'int' ? 1 : 0.1);
    if (value !== undefined) input.value = value;
    input.placeholder = t('panel.unset');
    const parse = () => {
      const v = field.type === 'int' ? parseInt(input.value) : parseFloat(input.value);
      return isNaN(v) ? undefined : v;
    };
    input.onchange = () => { const v = parse(); if (v !== undefined) onEdit(v); };
    if (field.live && field.min !== undefined && field.max !== undefined) {
      const slider = el('input');
      slider.type = 'range';
      slider.min = field.min; slider.max = field.max;
      slider.step = field.step || (field.type === 'int' ? 1 : 0.1);
      if (value !== undefined) slider.value = value;
      slider.style.cssText = 'width:120px;vertical-align:middle;margin-right:6px';
      slider.oninput = () => {
        input.value = slider.value;
        const v = parse();
        if (v !== undefined && onLive) onLive(v);
      };
      slider.onchange = () => { const v = parse(); if (v !== undefined) onEdit(v); };
      input.oninput = () => { slider.value = input.value; const v = parse(); if (v !== undefined && onLive) onLive(v); };
      holder.appendChild(slider);
      input.style.maxWidth = '64px';
    }
  }
  input.style.maxWidth = '150px';
  holder.appendChild(input);
  row.appendChild(holder);
  return row;
}

// generic editor for one list item (roof entries, extra_parts, volumes)
function genericItem(item, mats, onDelete) {
  const box = el('div', 'group');
  const head = el('h4', null, item.type || '(item)');
  const del = el('button', 'ghost', t('panel.delete'));
  del.style.cssText = 'float:right;padding:2px 8px;font-size:11px';
  del.onclick = onDelete;
  head.appendChild(del);
  box.appendChild(head);
  for (const [k, v] of Object.entries(item)) {
    if (k === 'type') continue;
    if (typeof v === 'boolean') {
      box.appendChild(control({ label: k, type: 'bool' }, v, nv => item[k] = nv));
    } else if (typeof v === 'number') {
      box.appendChild(control({ label: k, type: 'float', step: 0.05 }, v, nv => item[k] = nv));
    } else if (typeof v === 'string') {
      const f = mats.includes(v) ? { label: k, type: 'enum', choices: mats } : null;
      if (f) box.appendChild(control(f, v, nv => item[k] = nv));
      else {
        const row = el('div', 'kv', `<span class="k">${k}</span><span class="v">${v}</span>`);
        box.appendChild(row);
      }
    } else {
      box.appendChild(el('div', 'kv',
        `<span class="k">${k}</span><span class="v" style="font-size:11px">${JSON.stringify(v)}</span>`));
    }
  }
  return box;
}

// dialect-part templates for "add part" (sizes from footprint)
function partTemplates(spec) {
  const fp = Array.isArray(spec.footprint) ? spec.footprint : [20, 12];
  const L = typeof fp[0] === 'number' ? fp[0] : 20;
  const W = typeof fp[1] === 'number' ? fp[1] : 12;
  const fh = spec.floor_h || 3.2;
  const fl = spec.floors || (spec.masses && spec.masses[0] && spec.masses[0].floors) || 4;
  // parameter meanings follow parts_learned.py, not the dialect prose:
  // `face` = signed wall-plane coordinate (-W/2 for the -y front), `along` =
  // centre along the facade (0 = middle), `levels` = slab heights in metres,
  // facade_band `span` = fraction (number) and `sides` = front/back/left/right.
  // The old templates passed a [0.05,0.95] range for along/span and no face,
  // so the part builder raised, the assembler skipped the part silently and
  // "add part" looked like it did nothing (09-08).
  const z = (k) => +(k * fh).toFixed(2);
  const face = +(-W / 2).toFixed(2);
  return {
    balcony_band: { type: 'balcony_band', side: '-y', face, length: +(L * 0.92).toFixed(1),
      along: 0, levels: fl >= 4 ? [z(1), z(fl - 1)] : [z(1)],
      depth: 0.85, rail_h: 1.0, slab_t: 0.18, spacing: 0.3,
      material: 'iron', slab_material: 'stone' },
    window_guards: { type: 'window_guards', side: '-y', face, span: +(L * 0.92).toFixed(1),
      along: 0, bays: Math.max(3, Math.round(L / 3.2)), width: 1.4,
      levels: Array.from({ length: Math.max(1, fl - 1) }, (_, k) => z(k + 1)),
      rail_h: 0.95, proj: 0.18, posts: 4, material: 'iron' },
    mansard_cap: { type: 'mansard_cap', length: L, width: W, base_z: +(fl * fh).toFixed(1),
      height: 3.2, inset: 1.1, overhang: 0.25, material: 'slate_dark',
      top_material: 'slate', cornice: true, cornice_material: 'stone',
      dormers: true, dormer_sides: ['-y'], dormer_width: 1.2, dormer_height: 1.5, dormer_frac: 0.6 },
    facade_band: { type: 'facade_band', length: L, width: W, z: z(1),
      depth: 0.25, thickness: 0.22, span: 1.0, sides: ['front'],
      railing: false, material: 'stone' },
  };
}

// live-preview dispatch: which spec fields can morph client-side, and how
function makeLive(f, work, hooks, info) {
  if (!hooks.live) return null;
  const baseFloors = () => Math.max(1,
    Array.isArray(work.masses) && work.masses.length
      ? Math.max(...work.masses.map(m => m.floors || 1))
      : (work.floors || 4));
  const baseFh = () => work.floor_h || 3.2;
  const orig = { floors: baseFloors(), fh: baseFh() };
  if (f.path === 'floors' || f.path === 'floor_h') {
    return v => {
      const fl = f.path === 'floors' ? v : baseFloors();
      const fh = f.path === 'floor_h' ? v : baseFh();
      hooks.live(info.osmid, 'heightRatio', (fl * fh) / (orig.floors * orig.fh));
    };
  }
  if (f.type === 'color' && f.path.startsWith('colors.')) {
    const channel = f.path.split('.')[1];
    if (channel === 'glass_look') return null;
    return rgb => hooks.live(info.osmid, 'tint', { channel, rgb });
  }
  return null;
}

export async function renderPanel(side, area, info, kind, hooks = {}) {
  const sc = await schema();
  side.innerHTML = '';
  const meta = info.meta || {};
  side.appendChild(el('h2', null, meta.name || `#${info.osmid}`));
  const bits = [`osmid ${info.osmid}`, meta.btype, meta.area_m2 ? `${meta.area_m2} m²` : null,
    info.typology && info.typology.card ? `typology: ${info.typology.card}` : null,
    info.refined ? `<span class="badge ok">${t('panel.refined')}</span>` : null,
    kind === 'lod1' ? '<span class="badge warn">LoD1</span>' : null]
    .filter(Boolean).join(' · ');
  side.appendChild(el('div', 'sub', bits));

  if (!info.spec) {
    side.appendChild(el('div', 'placeholder', t('panel.no_spec')));
    return;
  }

  const work = JSON.parse(JSON.stringify(
    (hooks.draft && hooks.draft.spec) || info.spec));
  let touched = false;
  let applyTimer = null;
  const markTouched = () => {
    touched = true;
    applyBtn.disabled = false;
    clearTimeout(applyTimer);
    applyTimer = setTimeout(() => doApply(), 400);   // auto preview-rebuild
  };

  // scalar groups
  for (const g of sc.groups) {
    const rows = [];
    for (const f of g.fields) {
      const hasMasses = Array.isArray(work.masses) && work.masses.length > 0;
      let cur = pget(work, f.path);
      if (f.masses_override && hasMasses) {
        // whole-building control: reads the tallest mass, writes ALL masses
        cur = f.path === 'floors'
          ? Math.max(...work.masses.map(m => m.floors || 0))
          : (work.masses[0][f.path] ?? cur);
      }
      const onLive = makeLive(f, work, hooks, info);
      const row = control(f, cur, v => {
        pset(work, f.path, v);
        if (f.masses_override && hasMasses) {
          for (const m of work.masses) m[f.path] = v;
        }
        markTouched();
      }, onLive);
      if (f.masses_override && hasMasses) {
        const k = row.querySelector('.k');
        if (k) k.innerHTML += ` <small>(${t('panel.masses_sync')})</small>`;
      }
      if (f.poly_drop && info.path === 'poly') {
        const input = row.querySelector('input,select');
        if (input) input.disabled = true;
        const k = row.querySelector('.k');
        if (k) k.innerHTML += ` <small>(${t('panel.poly_drop')})</small>`;
      }
      rows.push(row);
    }
    if (!rows.length) continue;
    const box = el('div', 'group');
    box.appendChild(el('h4', null, L(g, 'title')));
    rows.forEach(r => box.appendChild(r));
    side.appendChild(box);
  }

  // masses
  if (Array.isArray(work.masses) && work.masses.length) {
    const box = el('div', 'group');
    box.appendChild(el('h4', null, L(sc.lists.masses, 'title')));
    work.masses.forEach((m, i) => {
      box.appendChild(el('div', 'sub', `${t('panel.block')} ${i + 1} · x[${m.x}] y[${m.y}]`));
      for (const f of sc.lists.masses.fields) {
        box.appendChild(control(f, m[f.key], v => { m[f.key] = v; markTouched(); }));
      }
    });
    side.appendChild(box);
  }

  // generic lists: roof / volumes / extra_parts
  if (!Array.isArray(work.extra_parts)) work.extra_parts = [];
  for (const key of ['roof', 'volumes', 'extra_parts']) {
    const arr = work[key];
    if (!Array.isArray(arr) || (!arr.length && key !== 'extra_parts')) continue;
    const wrapBox = el('div', 'group');
    wrapBox.appendChild(el('h4', null, L(sc.lists[key], 'title')));
    let addSel = null;
    const renderList = () => {
      wrapBox.querySelectorAll('.group').forEach(n => n.remove());
      arr.forEach((item, i) => {
        const node = genericItem(item, sc.materials, () => {
          arr.splice(i, 1); markTouched(); renderList();
        });
        node.addEventListener('change', markTouched);
        wrapBox.appendChild(node);
      });
      if (addSel) wrapBox.appendChild(addSel);   // keep the selector last
    };
    if (key === 'extra_parts' && info.path === 'poly') {
      wrapBox.appendChild(el('div', 'sub', t('panel.poly_drop_parts')));
    }
    if (key === 'extra_parts') {
      addSel = el('select');
      addSel.appendChild(el('option', null, t('panel.add_part')));
      for (const t of Object.keys(partTemplates(work))) {
        const o = el('option', null, t); o.value = t; addSel.appendChild(o);
      }
      addSel.onchange = () => {
        if (!addSel.value) return;
        arr.push(JSON.parse(JSON.stringify(partTemplates(work)[addSel.value])));
        addSel.selectedIndex = 0;
        markTouched(); renderList();
      };
    }
    renderList();
    side.appendChild(wrapBox);
  }

  // actions: apply = in-view preview only; save = persist + history;
  // revert = drop unsaved (or walk the saved history back one step)
  const actions = el('div', 'group');
  const applyBtn = el('button', null, t('panel.apply'));
  const saveBtn = el('button', null, t('panel.save'));
  const revertBtn = el('button', 'ghost', t('panel.revert'));
  saveBtn.style.marginLeft = revertBtn.style.marginLeft = '8px';
  applyBtn.disabled = true;
  saveBtn.disabled = !(hooks.draft && hooks.draft.unsaved);
  let unsaved = !!(hooks.draft && hooks.draft.unsaved);
  let histDepth = info.history || 0;
  const syncButtons = () => {
    revertBtn.disabled = !unsaved && histDepth === 0;
    revertBtn.textContent = unsaved ? t('panel.revert')
      : `${t('panel.revert')}${histDepth ? ` (${histDepth})` : ''}`;
  };
  const status = el('div', 'sub', '');
  const rebuildUrl = hooks.rebuildUrl || `/api/areas/${area}/buildings/${info.osmid}/rebuild`;
  const post = async (url, body) => {
    const r = await fetch(url, { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  };
  let applying = false, applyAgain = false;
  async function doApply() {
    if (applying) { applyAgain = true; return; }
    applying = true;
    applyBtn.disabled = true;
    status.innerHTML = `<span class="spin"></span> ${t('panel.rebuilding')}`;
    try {
      const res = await post(rebuildUrl, { spec: work, persist: false });
      unsaved = true; saveBtn.disabled = false;
      if (hooks.setDraft) hooks.setDraft(work, true);
      status.textContent = t('panel.applied_unsaved');
      if (hooks.onRebuilt) await hooks.onRebuilt(info.osmid, res.glb);
    } catch (e) {
      status.textContent = t('panel.failed') + e.message;
      applyBtn.disabled = false;
    }
    applying = false;
    syncButtons();
    if (applyAgain) { applyAgain = false; doApply(); }   // coalesced latest spec
  }
  applyBtn.onclick = doApply;
  saveBtn.onclick = async () => {
    saveBtn.disabled = true;
    status.innerHTML = `<span class="spin"></span> ${t('panel.saving')}`;
    try {
      const res = await post(rebuildUrl, { spec: work, persist: true });
      unsaved = false;
      if (hooks.setDraft) hooks.setDraft(null);
      if (res.history !== undefined) histDepth = res.history;
      status.textContent = t('panel.saved');
      if (hooks.onRebuilt) await hooks.onRebuilt(info.osmid, res.glb);
    } catch (e) {
      status.textContent = t('panel.failed') + e.message;
      saveBtn.disabled = false;
    }
    syncButtons();
  };
  revertBtn.onclick = async () => {
    revertBtn.disabled = true;
    status.innerHTML = `<span class="spin"></span> ${t('panel.reverting')}`;
    try {
      if (unsaved) {
        const res = await post(rebuildUrl, { spec: info.spec, persist: false });
        if (hooks.setDraft) hooks.setDraft(null);
        if (hooks.onRebuilt) await hooks.onRebuilt(info.osmid, res.glb);
        renderPanel(side, area, info, kind, { ...hooks, draft: null });
        return;
      }
      const res = await post(`/api/areas/${area}/buildings/${info.osmid}/undo`);
      if (hooks.onRebuilt) await hooks.onRebuilt(info.osmid, res.glb);
      const fresh = { ...info, spec: res.spec, history: res.history };
      renderPanel(side, area, fresh, kind, hooks);
      return;
    } catch (e) {
      status.textContent = t('panel.failed') + e.message;
    }
    syncButtons();
  };
  syncButtons();
  actions.appendChild(applyBtn);
  if (!hooks.rebuildUrl) { actions.appendChild(saveBtn); actions.appendChild(revertBtn); }
  actions.appendChild(status);
  side.appendChild(actions);
}

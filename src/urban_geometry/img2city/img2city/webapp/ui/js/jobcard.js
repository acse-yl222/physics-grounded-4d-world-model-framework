// jobcard.js -- shared job card renderer (map page + jobs page). Plain script;
// needs i18n.js loaded first.

function jcEsc(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;'); }

function jcStage(label, on, detail = '') {
  return `<div class="stage"><span>${label} ${detail}</span><span class="${on ? 'ok' : 'off'}">${on ? '✓' : '…'}</span></div>`;
}

function jobCardHTML(j, opts = {}) {
  const p = j.progress || {};
  const disp = j.meta && j.meta.display ? `${jcEsc(j.meta.display)} · ` : '';
  const kind = t('kind.' + j.kind);
  const status = t('status.' + j.status);
  let html = `<div class="group"><h4>${kind === 'kind.' + j.kind ? j.kind : kind} · ${disp}${jcEsc(j.area)}
    <span class="badge ${j.status === 'done' ? 'ok' : (j.status === 'failed' || j.status === 'interrupted' ? 'warn' : '')}">${status}</span></h4>`;
  if (!j.maps_key) html += `<div class="sub" style="color:var(--warn)">${t('map.no_key')}</div>`;
  html += jcStage(t('stage.osm'), p.bootstrap, p.total ? `(${p.total})` : '');
  html += jcStage(t('stage.specs'), p.total > 0 && p.specs >= p.total, `${p.specs}/${p.total || '?'}`);
  html += jcStage(t('stage.refine'), p.refined > 0 && p.refined >= p.specs * 0.5, `${p.refined}`);
  html += jcStage(t('stage.assembly'), p.assembled);
  html += jcStage(t('stage.verify'), !!p.verdict, p.verdict || '');
  if ((j.status === 'running' || j.status === 'quoting') && j.stage) {
    html += `<div class="sub" style="margin-top:6px">${t('jobs.now')}<b>${t('stage.' + j.stage)}</b><br><code style="font-size:11px">${jcEsc(j.last_line)}</code></div>`;
  }
  if (j.status === 'awaiting_confirm') {
    const q = j.quote || {};
    html += `<div class="sub" style="margin-top:8px">${t('map.quote', { b: q.buildings ?? '?', s: q.specs_todo ?? '?', t: q.tokens_M_upper ?? '?' })}</div>
      ${j.blender_alive ? '' : `<div class="sub">${t('map.blender_off')}</div>`}
      ${j.meta && j.meta.preview ? `<div style="margin-top:6px"><button class="ghost" data-act="open" data-area="${jcEsc(j.area)}">${t('map.preview')}</button></div>` : ''}
      <div style="margin-top:8px"><button data-act="confirm">${t('map.confirm')}</button>
      <button class="ghost" data-act="cancel">${t('map.cancel')}</button></div>`;
  } else if (j.status === 'running' || j.status === 'quoting') {
    html += `<div style="margin-top:8px"><button class="ghost" data-act="cancel">${t('map.stop')}</button></div>`;
  } else if (j.status === 'done') {
    html += `<div style="margin-top:8px"><button data-act="open" data-area="${jcEsc(j.area)}">${t('map.open_viewer')}</button></div>`;
  } else if (j.status === 'failed' || j.status === 'interrupted' || j.status === 'cancelled') {
    if (j.error) html += `<div class="sub" style="color:var(--warn)">${t('map.failed')}${jcEsc(j.error)}</div>`;
    if (j.kind === 'generate') {
      html += `<div style="margin-top:8px"><button data-act="resume">${t('jobs.resume')}</button>`;
      if (j.meta && j.meta.preview || (j.progress && j.progress.assembled)) {
        html += ` <button class="ghost" data-act="open" data-area="${jcEsc(j.area)}">${t('map.open_viewer')}</button>`;
      }
      html += `</div>`;
    }
  }
  html += `</div>`;
  if (opts.log !== false && j.log_tail) {
    html += `<pre class="log">${jcEsc(j.log_tail)}</pre>`;
  }
  return html;
}

function bindJobActions(root, jid) {
  root.querySelectorAll('[data-act]').forEach(btn => {
    btn.onclick = async () => {
      const act = btn.dataset.act;
      if (act === 'open') {
        location.href = `/viewer.html?area=${btn.dataset.area}`;
        return;
      }
      btn.disabled = true;
      const r = await fetch(`/api/jobs/${jid}/${act}`, { method: 'POST' });
      if (!r.ok) { alert(await r.text()); btn.disabled = false; }
    };
  });
}

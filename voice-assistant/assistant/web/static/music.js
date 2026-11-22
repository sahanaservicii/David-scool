(() => {
  const statusEl = document.getElementById('status');
  const haHint = document.getElementById('haHint');
  const hint = document.getElementById('hint');
  const roomsEl = document.getElementById('rooms');
  const roomSelect = document.getElementById('roomSelect');
  const radioSelect = document.getElementById('radioSelect');
  const archiveSelect = document.getElementById('archiveSelect');
  const mediaInput = document.getElementById('mediaInput');
  const mediaType = document.getElementById('mediaType');
  const debugEl = document.getElementById('debug');
  const volInput = document.getElementById('volInput');

  let lastStatus = null;

  function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }

  function badge(text, cls){
    return `<span class="badge ${cls||''}">${esc(text)}</span>`;
  }

  function getRoomId(){ return roomSelect.value || ''; }

  function fillPresets(select, items, placeholder){
    const cur = select.value;
    select.innerHTML = `<option value="">${esc(placeholder)}</option>`;
    (items||[]).forEach(it => {
      const opt = document.createElement('option');
      opt.value = it.id || '';
      opt.textContent = it.name || it.id || 'Preset';
      opt.dataset.mcid = it.media_content_id || '';
      opt.dataset.mct = it.media_content_type || 'music';
      select.appendChild(opt);
    });
    if (cur) select.value = cur;
  }

  function presetToInput(select){
    const opt = select.options[select.selectedIndex];
    if (!opt || !opt.value) return;
    if (opt.dataset.mcid) mediaInput.value = opt.dataset.mcid;
    if (opt.dataset.mct) mediaType.value = opt.dataset.mct;
  }

  async function api(path, opts={}){
    const r = await fetch(path, Object.assign({headers:{'Content-Type':'application/json'}}, opts));
    let data = {};
    try { data = await r.json(); } catch(e) { data = {error:'invalid json'}; }
    return {ok: r.ok, status: r.status, data};
  }

  function renderRooms(status){
    const rooms = (status && status.rooms) || [];
    if (!rooms.length){
      roomsEl.innerHTML = '<div class="card muted">Комнаты не настроены. Добавьте rooms[] в config/config.local.json.</div>';
      return;
    }
    roomsEl.innerHTML = rooms.map(item => {
      const room = item.room || {};
      const ps = item.player_state || {};
      const mp = item.media_player || room.media_player || '';
      const st = ps.state || (mp ? 'unknown' : 'not configured');
      let cls = 'warn';
      if (!mp) cls = 'warn';
      else if (st === 'playing') cls = 'ok';
      else if (st === 'unavailable' || st === 'unknown') cls = 'warn';
      else if (item.error) cls = 'err';
      else cls = 'ok';
      const title = ps.media_title || '';
      const artist = ps.media_artist || '';
      const now = (title || artist) ? `<div class="small"><b>Сейчас:</b> ${esc([artist,title].filter(Boolean).join(' — '))}</div>` : '<div class="small muted">Нет данных о треке (ожидание плеера/MA).</div>';
      const vol = (typeof ps.volume_level === 'number') ? Math.round(ps.volume_level*100)+'%' : '—';
      return `
        <div class="card">
          <h3>${esc(room.name || room.id || 'Комната')}</h3>
          <div class="small muted">id: ${esc(room.id||'')} ${room.satellite_id ? '• satellite: '+esc(room.satellite_id) : ''}</div>
          <div style="margin:6px 0">${badge(st, cls)} ${mp ? badge(mp,'') : badge('нет media_player','warn')}</div>
          ${now}
          <div class="small muted">Громкость: ${esc(vol)} ${ps.source ? '• источник: '+esc(ps.source) : ''}</div>
          ${item.error ? `<div class="small" style="color:#ffb4b4;margin-top:6px">Ошибка: ${esc(item.error)}</div>` : ''}
          <div class="controls-grid" style="margin-top:10px">
            <button onclick="window.__musicCmd('play','${esc(room.id||'')}')">▶</button>
            <button onclick="window.__musicCmd('pause','${esc(room.id||'')}')">⏸</button>
            <button onclick="window.__musicCmd('stop','${esc(room.id||'')}')">⏹</button>
            <button onclick="window.__musicCmd('previous','${esc(room.id||'')}')">⏮</button>
            <button onclick="window.__musicCmd('next','${esc(room.id||'')}')">⏭</button>
          </div>
        </div>`;
    }).join('');
  }

  function renderRoomSelect(status){
    const rooms = (status && status.rooms) || [];
    const cur = roomSelect.value;
    roomSelect.innerHTML = '';
    rooms.forEach(item => {
      const r = item.room || {};
      const opt = document.createElement('option');
      opt.value = r.id || '';
      opt.textContent = (r.name || r.id || 'Комната') + (item.media_player ? ` (${item.media_player})` : '');
      roomSelect.appendChild(opt);
    });
    if (cur) roomSelect.value = cur;
  }

  async function refresh(){
    statusEl.textContent = 'Обновление…';
    const res = await api('/api/music');
    if (!res.ok){
      statusEl.textContent = 'Ошибка загрузки';
      hint.textContent = (res.data && (res.data.error||res.data.message)) || 'Не удалось получить состояние музыки.';
      debugEl.textContent = JSON.stringify(res, null, 2);
      return;
    }
    lastStatus = res.data;
    const ha = res.data.ha || {};
    statusEl.textContent = ha.reachable ? 'HA: подключён' : (ha.url ? 'HA: недоступен' : 'HA: не настроен');
    haHint.textContent = ha.reachable ? 'Можно управлять настроенными плеерами' : (ha.error || 'Настройте Home Assistant и media_player комнат');
    renderRoomSelect(res.data);
    renderRooms(res.data);
    const cfg = res.data.config || {};
    fillPresets(radioSelect, cfg.radio_presets || [], '— выбрать радио —');
    fillPresets(archiveSelect, cfg.archive_presets || [], '— выбрать из архива —');
    debugEl.textContent = JSON.stringify(res.data, null, 2);
  }

  async function sendControl(action, roomOverride){
    const room = roomOverride || getRoomId();
    const payload = {action, room};
    if (action === 'play_media' || action === 'start'){
      payload.media_content_id = mediaInput.value.trim();
      payload.media_content_type = mediaType.value || 'music';
      if (!payload.media_content_id){
        alert('Укажите URL/media_content_id или выберите пресет (радио/архив).');
        return;
      }
    }
    if (action === 'volume_set'){
      payload.volume = Number(volInput.value);
    }
    statusEl.textContent = 'Выполняю…';
    const res = await api('/api/music', {method:'POST', body: JSON.stringify(payload)});
    if (res.ok && res.data && res.data.ok){
      statusEl.textContent = 'Готово';
    } else {
      statusEl.textContent = 'Ошибка';
      const msg = (res.data && (res.data.message || res.data.error)) || 'Команда не выполнена';
      alert(msg);
    }
    await refresh();
  }

  window.__musicCmd = (action, room) => sendControl(action, room);

  document.getElementById('refreshBtn').addEventListener('click', refresh);
  document.getElementById('playBtn').addEventListener('click', () => sendControl('play_media'));
  document.getElementById('setVolBtn').addEventListener('click', () => sendControl('volume_set'));
  radioSelect.addEventListener('change', () => presetToInput(radioSelect));
  archiveSelect.addEventListener('change', () => presetToInput(archiveSelect));
  document.querySelectorAll('button[data-action]').forEach(btn => {
    btn.addEventListener('click', () => sendControl(btn.getAttribute('data-action')));
  });

  refresh();
})();

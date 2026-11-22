(() => {
  const chat = document.getElementById('chat');
  const statusEl = document.getElementById('status');
  const capsEl = document.getElementById('caps');
  const micBtn = document.getElementById('micBtn');
  const stopSpeakBtn = document.getElementById('stopSpeakBtn');
  const sendBtn = document.getElementById('sendBtn');
  const input = document.getElementById('textInput');
  const autoSpeak = document.getElementById('autoSpeak');
  const continuous = document.getElementById('continuous');
  const hint = document.getElementById('hint');
  const roomSelect = document.getElementById('roomSelect');
  const roomHint = document.getElementById('roomHint');

  const sessionId = 'web-' + Math.random().toString(36).slice(2, 10);
  let recognizing = false;
  let recognition = null;

  function getRoom() {
    return (roomSelect && roomSelect.value) || 'default';
  }

  function addMsg(role, text, meta) {
    const wrap = document.createElement('div');
    wrap.className = 'msg ' + (role === 'user' ? 'user' : 'bot');
    const b = document.createElement('div');
    b.className = 'bubble';
    b.textContent = text;
    wrap.appendChild(b);
    if (meta) {
      const m = document.createElement('div');
      m.className = 'meta';
      m.textContent = meta;
      b.appendChild(document.createElement('br'));
      b.appendChild(m);
    }
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;
  }

  function speak(text) {
    if (!autoSpeak.checked) return;
    if (!('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = (window.__assistantLang || 'ru-RU');
      u.rate = 1.0;
      const voices = window.speechSynthesis.getVoices ? window.speechSynthesis.getVoices() : [];
      const v = voices.find(x => (x.lang || '').toLowerCase().startsWith(u.lang.toLowerCase().slice(0,2)));
      if (v) u.voice = v;
      window.speechSynthesis.speak(u);
    } catch (e) { /* ignore */ }
  }

  let roomsCache = [];
  function roomLabel(room) {
    if (!room) return 'Дом';
    const bits = [room.name || room.id || 'Комната'];
    if (room.media_player) bits.push(`музыка: ${room.media_player}`);
    if (room.satellite_id) bits.push(`sat: ${room.satellite_id}`);
    return bits.join(' • ');
  }
  function updateRoomHint() {
    const room = roomsCache.find(r => r.id === getRoom()) || roomsCache[0];
    if (roomHint) roomHint.textContent = `Контекст: ${roomLabel(room)}`;
  }
  async function loadRooms() {
    if (!roomSelect) return;
    try {
      const r = await fetch('/api/rooms');
      const data = await r.json();
      const rooms = (data && data.rooms) || [];
      roomsCache = rooms;
      roomSelect.innerHTML = '';
      if (!rooms.length) {
        const opt = document.createElement('option');
        opt.value = 'default'; opt.textContent = 'Дом (по умолчанию)';
        roomSelect.appendChild(opt);
        roomsCache = [{id:'default', name:'Дом'}];
      } else {
        rooms.forEach(room => {
          const opt = document.createElement('option');
          opt.value = room.id || 'default';
          opt.textContent = room.name || room.id || 'Комната';
          opt.title = roomLabel(room);
          roomSelect.appendChild(opt);
        });
      }
      roomSelect.addEventListener('change', updateRoomHint);
      updateRoomHint();
    } catch (e) {
      if (roomSelect) {
        roomSelect.innerHTML = '<option value="default">Дом</option>';
      }
      roomsCache = [{id:'default', name:'Дом'}];
      updateRoomHint();
    }
  }

  async function loadStatus() {
    try {
      const r = await fetch('/api/status');
      const s = await r.json();
      window.__assistantLang = (s.language === 'ru' ? 'ru-RU' : (s.language || 'ru-RU'));
      const ha = s.home_assistant || {};
      const haTxt = ha.configured ? (ha.reachable ? `HA: ${ha.location_name || 'OK'}` : 'HA: недоступен') : 'HA: не настроен';
      const llmTxt = s.llm_configured ? `LLM: ${s.llm_provider || 'on'}` : 'LLM: выкл';
      statusEl.textContent = `v${s.version || ''} • навыки: ${(s.skills||[]).length} • ${haTxt} • ${llmTxt}`;
      capsEl.textContent = JSON.stringify(s, null, 2);
    } catch (e) {
      statusEl.textContent = 'Нет связи с сервером';
    }
  }

  async function sendText(text) {
    text = (text || '').trim();
    if (!text) return;
    const room = getRoom();
    addMsg('user', text, `комната: ${room}`);
    input.value = '';
    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ text, session_id: sessionId, room })
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Ошибка');
      const parts = [];
      if (data.intent) parts.push(`намерение: ${data.intent}`);
      if (data.room && data.room.name) parts.push(`комната: ${data.room.name}`);
      if (data.skill) parts.push(`skill: ${data.skill}`);
      if (data.data && data.data.target_player) parts.push(`player: ${data.data.target_player}`);
      else if (data.data && data.data.entity_id && (data.intent||'').startsWith('media')) parts.push(`player: ${data.data.entity_id}`);
      addMsg('bot', data.text || '(пустой ответ)', parts.join(' • '));
      speak(data.speak || data.text || '');
      if (data.intent === 'goodbye') stopRecognition();
    } catch (e) {
      addMsg('bot', 'Ошибка: ' + e.message);
    }
  }

  function setupRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      micBtn.disabled = true;
      micBtn.title = 'Распознавание речи не поддерживается браузером';
      hint.textContent += ' Голосовой ввод (STT) недоступен в этом браузере — используйте текст.';
      return null;
    }
    const rec = new SR();
    rec.lang = window.__assistantLang || 'ru-RU';
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.continuous = false;
    rec.onstart = () => { recognizing = true; micBtn.classList.add('active'); micBtn.textContent = '⏹ Слушаю…'; };
    rec.onend = () => {
      recognizing = false; micBtn.classList.remove('active'); micBtn.textContent = '🎤 Говорить';
      if (continuous.checked) { try { rec.start(); } catch(e){} }
    };
    rec.onerror = (e) => { console.warn('STT error', e.error); };
    rec.onresult = (ev) => {
      const t = ev.results[0][0].transcript;
      if (t) sendText(t);
    };
    return rec;
  }

  function stopRecognition() {
    continuous.checked = false;
    try { recognition && recognition.stop(); } catch(e){}
  }

  micBtn.addEventListener('click', () => {
    if (!recognition) recognition = setupRecognition();
    if (!recognition) return;
    if (recognizing) { stopRecognition(); return; }
    recognition.lang = window.__assistantLang || 'ru-RU';
    try { recognition.start(); } catch(e) { console.warn(e); }
  });
  stopSpeakBtn.addEventListener('click', () => { try { window.speechSynthesis.cancel(); } catch(e){} stopRecognition(); });
  sendBtn.addEventListener('click', () => sendText(input.value));
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendText(input.value); });

  Promise.all([loadRooms(), loadStatus()]).then(() => { recognition = setupRecognition(); });
  addMsg('bot', 'Здравствуйте! Я Свободный Голос — локальный помощник для чата и умного дома. Выберите комнату, нажмите «Говорить» или напишите запрос. Скажите «помощь» для списка возможностей.');
})();

// Интерактивная логика. Прогресс и журнал ошибок хранятся в localStorage браузера.
// Отчёт для папы кодируется компактно: S2|ru=вопрос:ответ,..|math=пример:ответ,..
// Вопросы и объяснения берутся из data.js на сайте — в QR только индексы.
const Store = {
  key: 'school-progress-v1',
  logKey: 'school-error-log-v2',
  load() { try { return JSON.parse(localStorage.getItem(this.key)) || {}; } catch (e) { return {}; } },
  save(data) { localStorage.setItem(this.key, JSON.stringify(data)); },
  stars() { const d = this.load(); return Object.values(d).reduce((s, v) => s + (v.stars || 0), 0); },
  starsFor(ids) { const d = this.load(); return ids.reduce((s, id) => s + ((d[id] && d[id].stars) || 0), 0); },
  done(id) { const d = this.load(); return !!(d[id] && d[id].done); },
  mark(id, stars) {
    const d = this.load();
    d[id] = { done: true, stars: Math.max((d[id] || {}).stars || 0, stars) };
    this.save(d);
  },
  log() { try { return JSON.parse(localStorage.getItem(this.logKey)) || {}; } catch (e) { return {}; } },
  addErrors(id, payload) { const d = this.log(); d[id] = payload; localStorage.setItem(this.logKey, JSON.stringify(d)); },
  clearLog() { localStorage.removeItem(this.logKey); localStorage.removeItem(this.key); },
  clearLogFor(ids) { const d = this.log(); ids.forEach(id => delete d[id]); localStorage.setItem(this.logKey, JSON.stringify(d)); }
};

const Report = {
  // Собрать компактный код из журнала ошибок
  encode() {
    const log = Store.log();
    const parts = ['S2'];
    Object.entries(log).forEach(([id, rec]) => {
      if (!rec || !rec.items || !rec.items.length) return;
      const encoded = rec.items.map(it => {
        if (rec.type === 'quiz') return `${it.i}:${it.given}`;
        if (rec.type === 'math') return `${it.q}:${it.given}`;
        return '';
      }).filter(Boolean).join(',');
      if (encoded) parts.push(`${id}=${encoded}`);
    });
    return parts.join('|');
  },
  // Разобрать компактный код и показать ошибки с объяснениями
  decode(code) {
    const parts = code.trim().split('|');
    if (parts[0] !== 'S2') throw new Error('Код должен начинаться с S2|');
    const out = [];
    parts.slice(1).forEach(seg => {
      const [id, data] = seg.split('=');
      if (!data) return;
      let subj = App.lesson.subjects.find(s => s.id === id);
      if (!subj) {
        const all = (window.SCHOOL_DATA && window.SCHOOL_DATA.lessons) || [];
        for (const l of all) { subj = l.subjects.find(s => s.id === id); if (subj) break; }
      }
      if (!subj) return;
      if (subj.game === 'quiz') {
        data.split(',').forEach(pair => {
          const [i, given] = pair.split(':');
          const q = subj.questions[Number(i)];
          if (!q) return;
          out.push({
            subject: subj.name, q: q.q, given: q.options[Number(given)] || '—',
            answer: q.options[q.answer], why: q.why
          });
        });
      } else if (subj.game === 'math') {
        data.split(',').forEach(pair => {
          const idx = pair.lastIndexOf(':');
          if (idx < 0) return;
          const expr = pair.slice(0, idx).replace(/\s/g, '');
          const given = pair.slice(idx + 1);
          let m = expr.match(/^(\d+)([+\-x×÷])(\d+)$/);
          if (!m) { out.push({ subject: subj.name, q: expr, given, answer: '?', why: 'Не удалось разобрать пример.' }); return; }
          const a = Number(m[1]), b = Number(m[3]);
          const op = m[2];
          const ans = op === '+' ? a + b : op === '-' ? a - b : (op === 'x' || op === '×') ? a * b : a / b;
          out.push({ subject: subj.name, q: `${a} ${op} ${b}`, given, answer: String(ans), why: 'Посчитай ещё раз внимательно.' });
        });
      }
    });
    return out;
  },
  drawQr(code) {
    const box = document.getElementById('qrBox');
    box.innerHTML = '';
    try {
      const qr = new window.QRCodeLib(0, 1); // тип 0 = авто, уровень L
      qr.addData(code);
      qr.make();
      const count = qr.getModuleCount();
      const scale = Math.max(4, Math.floor(240 / count));
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = count * scale;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#000';
      for (let r = 0; r < count; r++)
        for (let c = 0; c < count; c++)
          if (qr.isDark(r, c)) ctx.fillRect(c * scale, r * scale, scale, scale);
      box.appendChild(canvas);
    } catch (e) {
      box.textContent = 'Не удалось построить QR: ' + e.message;
    }
  }
};

const App = {
  lesson: null, role: null,
  init() {
    const data = window.SCHOOL_DATA;
    this.lesson = data.lessons[data.lessons.length - 1];
    document.getElementById('childName').textContent = data.child.name;
    document.getElementById('pinBtn').onclick = this.checkPin.bind(this);
    document.getElementById('pinInput').addEventListener('keydown', e => { if (e.key === 'Enter') this.checkPin(); });
    this.renderSubjects();
    this.renderLessonPanel();
    this.updateProgress();
    document.getElementById('totalStars').textContent = Store.starsFor(this.lesson.subjects.map(s => s.id));
    this.renderJournal();
    this.bindButtons();
  },
  enterChild() {
    this.role = 'child';
    document.getElementById('roleGate').classList.add('hidden');
    document.getElementById('pinGate').classList.add('hidden');
    document.getElementById('appRoot').classList.remove('hidden');
    document.getElementById('childView').classList.remove('hidden');
    document.getElementById('parentView').classList.add('hidden');
  },
  askPin() {
    document.getElementById('roleGate').classList.add('hidden');
    document.getElementById('pinGate').classList.remove('hidden');
    document.getElementById('pinInput').value = '';
    document.getElementById('pinError').textContent = '';
  },
  checkPin() {
    if (document.getElementById('pinInput').value === window.SCHOOL_DATA.parentPin) {
      this.role = 'parent';
      document.getElementById('pinGate').classList.add('hidden');
      document.getElementById('appRoot').classList.remove('hidden');
      document.getElementById('childView').classList.add('hidden');
      document.getElementById('parentView').classList.remove('hidden');
    } else {
      document.getElementById('pinError').textContent = 'Неверный PIN';
    }
  },
  backToGate() {
    document.getElementById('appRoot').classList.add('hidden');
    document.getElementById('pinGate').classList.add('hidden');
    document.getElementById('roleGate').classList.remove('hidden');
  },
  renderSubjects() {
    const box = document.getElementById('subjects');
    box.innerHTML = '';
    this.lesson.subjects.forEach(s => {
      const done = Store.done(s.id);
      const el = document.createElement('div');
      el.className = 'subject';
      el.style.setProperty('--color', s.color);
      el.innerHTML = `
        <div class="emoji">${s.emoji}</div>
        <h3>${s.name}</h3>
        <div class="task">${s.task}</div>
        <div class="status">${done ? '✅ Выполнено — можно повторить' : '▶ Начать задание'}</div>`;
      el.onclick = () => Game.open(s);
      box.appendChild(el);
    });
  },
  // Сводка заданий в левом нижнем углу: дата + предметы + что задали
  renderLessonPanel() {
    const l = this.lesson;
    if (!l) return;
    document.getElementById('lpDate').textContent = `${l.date} · ${l.weekday}`;
    const list = document.getElementById('lpList');
    list.innerHTML = '';
    l.subjects.forEach(s => {
      const done = Store.done(s.id);
      const el = document.createElement('div');
      el.className = 'lp-item' + (done ? ' lp-done' : '');
      el.innerHTML = `<div class="lp-name">${done ? '✅' : s.emoji} ${s.name}</div><div class="lp-task">${s.task}</div>`;
      list.appendChild(el);
    });
  },
  toggleLessonPanel() {
    const panel = document.getElementById('lessonPanel');
    const collapsed = panel.classList.toggle('collapsed');
    panel.querySelector('.lp-toggle').textContent = collapsed ? '+' : '−';
  },
  updateProgress() {
    const total = this.lesson.subjects.length;
    const done = this.lesson.subjects.filter(s => Store.done(s.id)).length;
    document.getElementById('progressText').textContent = `${done} / ${total}`;
    document.getElementById('progressFill').style.width = `${(done / total) * 100}%`;
  },
  finish(subject, stars, items, type, correct, total) {
    Store.mark(subject.id, stars);
    Store.addErrors(subject.id, { type, items, correct, total });
    document.getElementById('totalStars').textContent = Store.starsFor(this.lesson.subjects.map(s => s.id));
    this.renderSubjects();
    this.renderLessonPanel();
    this.updateProgress();
    this.renderJournal();
  },
  renderJournal() {
    const box = document.getElementById('journalBody');
    const log = Store.log();
    const ids = this.lesson.subjects.map(s => s.id);
    const entries = ids.filter(id => log[id]).map(id => [id, log[id]]);
    if (!entries.length) {
      box.innerHTML = '<p class="hint">Заданий пока нет. Начните выполнять — здесь появятся ошибки и подсказки.</p>';
      return;
    }
    box.innerHTML = '';
    entries.forEach(([id, rec]) => {
      const subj = this.lesson.subjects.find(s => s.id === id);
      const div = document.createElement('div');
      const errors = rec.items || [];
      div.className = 'report-subject' + (errors.length ? '' : ' clean');
      let html = `<h4>${subj ? subj.name : id} — ${rec.correct} из ${rec.total} верно</h4>`;
      if (!errors.length) html += '<div class="error-item"><span class="right">✅ Ошибок нет — отличная работа!</span></div>';
      errors.forEach(it => {
        let q, given, answer, why;
        if (rec.type === 'quiz' && subj && subj.questions[it.i]) {
          const question = subj.questions[it.i];
          q = question.q; given = question.options[it.given] || '—'; answer = question.options[question.answer]; why = question.why;
        } else if (rec.type === 'math') {
          q = it.q; given = it.given; answer = it.answer || 'см. проверку'; why = it.why || 'Проверь вычисление.';
        } else { q = it.q || 'Вопрос'; given = it.given || '—'; answer = it.answer || '—'; why = it.why || ''; }
        html += `<div class="error-item"><div>❓ ${q}</div>
          <div><span class="wrong">Твой ответ: ${given}</span> · <span class="right">Правильно: ${answer}</span></div>
          <div class="why">💡 ${why}</div></div>`;
      });
      div.innerHTML = html;
      box.appendChild(div);
    });
  },
  bindButtons() {
    document.getElementById('showQrBtn').onclick = () => {
      const code = Report.encode();
      document.getElementById('compactCode').textContent = code;
      Report.drawQr(code);
      document.getElementById('qrModal').classList.remove('hidden');
    };
    document.getElementById('clearReportBtn').onclick = () => {
      if (confirm('Очистить журнал ошибок по текущему уроку? Звёздочки останутся.')) {
        const ids = this.lesson.subjects.map(s => s.id);
        Store.clearLogFor(ids);
        this.renderJournal(); this.renderSubjects(); this.updateProgress();
        document.getElementById('totalStars').textContent = Store.starsFor(ids);
      }
    };
    document.getElementById('showReportBtn').onclick = () => {
      const out = document.getElementById('parentReport');
      try {
        const errors = Report.decode(document.getElementById('reportInput').value);
        let html = `<div class="report-subject"><h4>Найдено ошибок: ${errors.length}</h4>`;
        if (!errors.length) html += '<p class="hint">Ошибок нет — всё верно!</p>';
        errors.forEach(e => {
          html += `<div class="report-subject"><h4>${e.subject}</h4>
            <div class="error-item"><div>❓ ${e.q}</div>
            <div><span class="wrong">Ответ: ${e.given}</span> · <span class="right">Правильно: ${e.answer}</span></div>
            <div class="why">💡 ${e.why}</div></div></div>`;
        });
        out.innerHTML = html + '</div>';
      } catch (e) {
        out.innerHTML = `<div class="report-subject"><span class="wrong">Ошибка: ${e.message}</span></div>`;
      }
    };
  }
};

const Game = {
  subject: null, questions: [], index: 0, stars: 0, correctAnswers: 0, items: [],
  mathTotal: 0, mathIndex: 0, mathCurrent: null, mathExpr: '', wordIndex: 0,
  open(subject) {
    this.subject = subject;
    this.index = 0; this.stars = 0; this.correctAnswers = 0; this.items = [];
    document.getElementById('subjects').classList.add('hidden');
    document.querySelector('.hero').classList.add('hidden');
    document.getElementById('journal').classList.add('hidden');
    document.getElementById('game').classList.remove('hidden');
    document.getElementById('gameTitle').textContent = `${subject.emoji} ${subject.name}`;
    document.getElementById('gameHint').textContent = subject.hint;
    const body = document.getElementById('gameBody');
    body.innerHTML = '';
    if (subject.game === 'quiz') { this.questions = subject.questions.slice(); this.showQuizQuestion(); }
    else if (subject.game === 'math') { this.mathTotal = subject.rounds; this.mathIndex = 0; this.showMath(); }
    else if (subject.game === 'words') { this.wordIndex = 0; this.showWord(); }
  },
  close() {
    document.getElementById('game').classList.add('hidden');
    document.getElementById('subjects').classList.remove('hidden');
    document.querySelector('.hero').classList.remove('hidden');
    document.getElementById('journal').classList.remove('hidden');
  },
  showQuizQuestion() {
    const body = document.getElementById('gameBody');
    if (this.index >= this.questions.length) return this.showResult();
    const q = this.questions[this.index];
    body.innerHTML = `
      <div class="q-counter">Вопрос ${this.index + 1} из ${this.questions.length}</div>
      <div class="question">${q.q}</div>
      <div class="options" id="options"></div>
      <div id="feedback"></div>`;
    const box = document.getElementById('options');
    q.options.forEach((opt, i) => {
      const b = document.createElement('button');
      b.className = 'option'; b.textContent = opt;
      b.onclick = () => this.answerQuiz(i, q, b);
      box.appendChild(b);
    });
  },
  answerQuiz(i, q, button) {
    const correct = i === q.answer;
    document.querySelectorAll('.option').forEach(b => b.disabled = true);
    button.classList.add(correct ? 'correct' : 'wrong');
    const fb = document.getElementById('feedback');
    if (correct) { this.stars++; this.correctAnswers++; }
    else this.items.push({ i: this.index, given: i });
    fb.innerHTML = `<div class="explain">${correct ? '✅ Верно! ' : '❌ Неверно. '}${q.why}</div>
      <button class="next" id="nextBtn">${this.index + 1 >= this.questions.length ? 'Завершить' : 'Следующий вопрос →'}</button>`;
    document.getElementById('nextBtn').onclick = () => { this.index++; this.showQuizQuestion(); };
  },
  showMath() {
    const body = document.getElementById('gameBody');
    if (this.mathIndex >= this.mathTotal) return this.showResult();
    const ops = ['+', '-', '×', '÷'];
    const op = ops[Math.floor(Math.random() * ops.length)];
    let a, b, answer;
    if (op === '+') { a = 10 + Math.floor(Math.random() * 80); b = 5 + Math.floor(Math.random() * 30); answer = a + b; }
    if (op === '-') { a = 20 + Math.floor(Math.random() * 70); b = 5 + Math.floor(Math.random() * (a - 5)); answer = a - b; }
    if (op === '×') { a = 2 + Math.floor(Math.random() * 8); b = 2 + Math.floor(Math.random() * 8); answer = a * b; }
    if (op === '÷') { b = 2 + Math.floor(Math.random() * 8); answer = 2 + Math.floor(Math.random() * 8); a = b * answer; }
    this.mathCurrent = answer;
    const opCode = op === '×' ? 'x' : op;
    this.mathExpr = `${a}${opCode}${b}`;
    body.innerHTML = `
      <div class="q-counter">Пример ${this.mathIndex + 1} из ${this.mathTotal}</div>
      <div class="math-line">${a} ${op} ${b} = ?</div>
      <div style="text-align:center">
        <input class="answer-input" id="mathAnswer" type="number" inputmode="numeric" placeholder="?" autofocus>
        <button class="next" id="checkBtn">Проверить</button>
      </div>
      <div id="feedback"></div>`;
    const check = () => {
      const val = parseInt(document.getElementById('mathAnswer').value, 10);
      const ok = val === this.mathCurrent;
      if (ok) { this.stars++; this.correctAnswers++; }
      else this.items.push({ q: this.mathExpr, given: isNaN(val) ? '?' : String(val) });
      const fb = document.getElementById('feedback');
      fb.innerHTML = `<div class="explain">${ok ? '✅ Верно! Молодец!' : '❌ Неверно. Правильный ответ: ' + this.mathCurrent}</div>
        <button class="next" id="nextBtn">${this.mathIndex + 1 >= this.mathTotal ? 'Завершить' : 'Следующий пример →'}</button>`;
      document.getElementById('checkBtn').disabled = true;
      document.getElementById('mathAnswer').disabled = true;
      document.getElementById('nextBtn').onclick = () => { this.mathIndex++; this.showMath(); };
    };
    document.getElementById('checkBtn').onclick = check;
    document.getElementById('mathAnswer').addEventListener('keydown', e => { if (e.key === 'Enter') check(); });
  },
  showWord() {
    const body = document.getElementById('gameBody');
    const words = this.subject.words;
    const w = words[this.wordIndex % words.length];
    const showRu = this.wordIndex % 2 === 1;
    body.innerHTML = `
      <div class="q-counter">Карточка ${this.wordIndex + 1} из ${words.length * 2}</div>
      <div class="word-card">${showRu ? w.ru : w.en}</div>
      <div style="text-align:center;color:#666">${showRu ? 'Как это по-английски?' : 'Как это по-русски?'}</div>
      <div style="text-align:center;margin-top:16px">
        <button class="next" id="showBtn">Показать перевод</button>
      </div>
      <div id="feedback"></div>`;
    document.getElementById('showBtn').onclick = () => {
      const fb = document.getElementById('feedback');
      fb.innerHTML = `<div class="explain">📖 ${showRu ? w.en + ' = ' + w.ru : w.ru + ' = ' + w.en}</div>
        <button class="next" id="nextBtn">Я запомнил(а) →</button>`;
      this.stars++; this.correctAnswers++;
      document.getElementById('nextBtn').onclick = () => {
        this.wordIndex++;
        if (this.wordIndex >= words.length * 2) this.showResult();
        else this.showWord();
      };
    };
  },
  showResult() {
    const body = document.getElementById('gameBody');
    const total = this.subject.game === 'quiz' ? this.questions.length
      : this.subject.game === 'math' ? this.mathTotal : this.subject.words.length * 2;
    const stars = Math.min(5, Math.max(1, Math.round((this.stars / total) * 5)));
    App.finish(this.subject, stars, this.items, this.subject.game, this.correctAnswers, total);
    body.innerHTML = `
      <div class="result">
        <div class="big">🎉</div>
        <h2>Отлично поработал!</h2>
        <p>Правильных ответов: ${this.correctAnswers} из ${total}</p>
        <p>Звёздочек за задание: ${'⭐'.repeat(stars)}</p>
        ${this.items.length ? `<p class="hint">Ошибок: ${this.items.length}. Посмотри журнал ошибок.</p>` : ''}
        <button class="next" onclick="Game.close()">К другим предметам</button>
      </div>`;
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());

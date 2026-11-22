// Интерактивная логика. Прогресс и журнал ошибок хранятся в localStorage браузера.
const Store = {
  key: 'school-progress-v1',
  logKey: 'school-error-log-v1',
  load() { try { return JSON.parse(localStorage.getItem(this.key)) || {}; } catch (e) { return {}; } },
  save(data) { localStorage.setItem(this.key, JSON.stringify(data)); },
  stars() { const d = this.load(); return Object.values(d).reduce((s, v) => s + (v.stars || 0), 0); },
  done(id) { const d = this.load(); return !!(d[id] && d[id].done); },
  mark(id, stars) {
    const d = this.load();
    const prev = d[id] || { stars: 0 };
    d[id] = { done: true, stars: Math.max(prev.stars || 0, stars) };
    this.save(d);
  },
  log() { try { return JSON.parse(localStorage.getItem(this.logKey)) || {}; } catch (e) { return {}; } },
  addErrors(subjectId, errors, correct, total) {
    const d = this.log();
    d[subjectId] = { errors, correct, total, time: new Date().toISOString() };
    localStorage.setItem(this.logKey, JSON.stringify(d));
  },
  clearLog() { localStorage.removeItem(this.logKey); localStorage.removeItem(this.key); }
};

const App = {
  lesson: null,
  init() {
    const data = window.SCHOOL_DATA;
    this.lesson = data.lessons[data.lessons.length - 1];
    document.getElementById('childName').textContent = data.child.name;
    this.renderSubjects();
    this.updateProgress();
    document.getElementById('totalStars').textContent = Store.stars();
    this.renderJournal();
    this.bindJournalButtons();
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
  updateProgress() {
    const total = this.lesson.subjects.length;
    const done = this.lesson.subjects.filter(s => Store.done(s.id)).length;
    document.getElementById('progressText').textContent = `${done} / ${total}`;
    document.getElementById('progressFill').style.width = `${(done / total) * 100}%`;
  },
  finish(subject, stars, errors, correct, total) {
    Store.mark(subject.id, stars);
    Store.addErrors(subject.id, errors, correct, total);
    document.getElementById('totalStars').textContent = Store.stars();
    this.renderSubjects();
    this.updateProgress();
    this.renderJournal();
  },
  renderJournal() {
    const box = document.getElementById('journalBody');
    const log = Store.log();
    const entries = Object.entries(log);
    if (!entries.length) {
      box.innerHTML = '<p class="hint">Заданий пока нет. Начните выполнять — здесь появятся ошибки и подсказки.</p>';
      return;
    }
    box.innerHTML = '';
    entries.forEach(([id, rec]) => {
      const subj = this.lesson.subjects.find(s => s.id === id);
      const name = subj ? subj.name : id;
      const div = document.createElement('div');
      div.className = 'report-subject' + (rec.errors.length ? '' : ' clean');
      let html = `<h4>${name} — ${rec.correct} из ${rec.total} верно</h4>`;
      if (!rec.errors.length) html += '<div class="error-item"><span class="right">✅ Ошибок нет — отличная работа!</span></div>';
      rec.errors.forEach(e => {
        html += `<div class="error-item">
          <div>❓ ${e.q}</div>
          <div><span class="wrong">Твой ответ: ${e.given}</span> · <span class="right">Правильно: ${e.answer}</span></div>
          <div class="why">💡 ${e.why}</div>
        </div>`;
      });
      div.innerHTML = html;
      box.appendChild(div);
    });
  },
  bindJournalButtons() {
    document.getElementById('copyReportBtn').onclick = () => {
      const payload = { child: window.SCHOOL_DATA.child.name, date: this.lesson.date, log: Store.log() };
      const bytes = new TextEncoder().encode(JSON.stringify(payload));
      let bin = '';
      bytes.forEach(b => bin += String.fromCharCode(b));
      const code = 'SCHOOL1:' + btoa(bin);
      const ta = document.createElement('textarea');
      ta.value = code;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); document.getElementById('copyStatus').textContent = '✅ Код скопирован — отправьте его папе.'; }
      catch (e) { document.getElementById('copyStatus').textContent = 'Не удалось скопировать автоматически — выделите код вручную: ' + code; }
      document.body.removeChild(ta);
    };
    document.getElementById('clearReportBtn').onclick = () => {
      if (confirm('Очистить весь журнал ошибок и звёздочки?')) {
        Store.clearLog();
        this.renderJournal();
        this.renderSubjects();
        this.updateProgress();
        document.getElementById('totalStars').textContent = '0';
      }
    };
    document.getElementById('showReportBtn').onclick = () => {
      const raw = document.getElementById('reportInput').value.trim();
      const out = document.getElementById('parentReport');
      try {
        if (!raw.startsWith('SCHOOL1:')) throw new Error('Код должен начинаться с SCHOOL1:');
        const bin = atob(raw.slice(8));
        const bytes = Uint8Array.from(bin, c => c.charCodeAt(0));
        const payload = JSON.parse(new TextDecoder().decode(bytes));
        let html = `<div class="report-subject"><h4>Отчёт: ${payload.child} — ${payload.date}</h4>`;
        const entries = Object.entries(payload.log || {});
        if (!entries.length) html += '<p class="hint">В отчёте нет данных.</p>';
        entries.forEach(([id, rec]) => {
          const subj = App.lesson.subjects.find(s => s.id === id);
          const name = subj ? subj.name : id;
          html += `<div class="report-subject ${rec.errors.length ? '' : 'clean'}"><h4>${name} — ${rec.correct} из ${rec.total} верно</h4>`;
          if (!rec.errors.length) html += '<div class="error-item"><span class="right">✅ Ошибок нет</span></div>';
          rec.errors.forEach(e => {
            html += `<div class="error-item"><div>❓ ${e.q}</div>
              <div><span class="wrong">Ответ: ${e.given}</span> · <span class="right">Правильно: ${e.answer}</span></div>
              <div class="why">💡 ${e.why}</div></div>`;
          });
          html += '</div>';
        });
        html += '</div>';
        out.innerHTML = html;
      } catch (e) {
        out.innerHTML = `<div class="report-subject"><span class="wrong">Не удалось прочитать код: ${e.message}</span></div>`;
      }
    };
  }
};

const Game = {
  subject: null, questions: [], index: 0, stars: 0, correctAnswers: 0, errors: [],
  mathTotal: 0, mathIndex: 0, mathCurrent: null, wordIndex: 0,
  open(subject) {
    this.subject = subject;
    this.index = 0; this.stars = 0; this.correctAnswers = 0; this.errors = [];
    document.getElementById('subjects').classList.add('hidden');
    document.querySelector('.hero').classList.add('hidden');
    document.getElementById('journal').classList.add('hidden');
    document.querySelector('.journal.parent').classList.add('hidden');
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
    document.querySelector('.journal.parent').classList.remove('hidden');
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
      b.className = 'option';
      b.textContent = opt;
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
    else this.errors.push({ q: q.q, given: q.options[i], answer: q.options[q.answer], why: q.why });
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
    const prompt = `${a} ${op} ${b}`;
    body.innerHTML = `
      <div class="q-counter">Пример ${this.mathIndex + 1} из ${this.mathTotal}</div>
      <div class="math-line">${prompt} = ?</div>
      <div style="text-align:center">
        <input class="answer-input" id="mathAnswer" type="number" inputmode="numeric" placeholder="?" autofocus>
        <button class="next" id="checkBtn">Проверить</button>
      </div>
      <div id="feedback"></div>`;
    const check = () => {
      const val = parseInt(document.getElementById('mathAnswer').value, 10);
      const ok = val === this.mathCurrent;
      if (ok) { this.stars++; this.correctAnswers++; }
      else this.errors.push({ q: prompt, given: isNaN(val) ? 'нет ответа' : String(val), answer: String(this.mathCurrent), why: 'Посчитай ещё раз внимательно — проверь знак и перенос.' });
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
      this.stars++;
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
    App.finish(this.subject, stars, this.errors, this.correctAnswers, total);
    body.innerHTML = `
      <div class="result">
        <div class="big">🎉</div>
        <h2>Отлично поработал!</h2>
        <p>Правильных ответов: ${this.correctAnswers} из ${total}</p>
        <p>Звёздочек за задание: ${'⭐'.repeat(stars)}</p>
        ${this.errors.length ? `<p class="hint">Ошибок: ${this.errors.length}. Посмотри журнал ошибок ниже — там всё разобрано.</p>` : ''}
        <button class="next" onclick="Game.close()">К другим предметам</button>
      </div>`;
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());

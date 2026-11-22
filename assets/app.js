// Интерактивная логика. Состояние прогресса хранится в localStorage.
const Store = {
  key: 'school-progress-v1',
  load() { try { return JSON.parse(localStorage.getItem(this.key)) || {}; } catch (e) { return {}; } },
  save(data) { localStorage.setItem(this.key, JSON.stringify(data)); },
  stars() {
    const d = this.load();
    return Object.values(d).reduce((sum, v) => sum + (v.stars || 0), 0);
  },
  done(id) { return !!(this.load()[id] && this.load()[id].done); },
  mark(id, stars) {
    const d = this.load();
    const prev = d[id] || { stars: 0 };
    d[id] = { done: true, stars: Math.max(prev.stars || 0, stars) };
    this.save(d);
  }
};

const App = {
  lesson: null,
  subject: null,
  init() {
    const data = window.SCHOOL_DATA;
    this.lesson = data.lessons[data.lessons.length - 1];
    document.getElementById('childName').textContent = data.child.name;
    this.renderSubjects();
    this.updateProgress();
    document.getElementById('totalStars').textContent = Store.stars();
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
  finish(subject, stars) {
    Store.mark(subject.id, stars);
    document.getElementById('totalStars').textContent = Store.stars();
    this.renderSubjects();
    this.updateProgress();
  }
};

const Game = {
  subject: null,
  questions: [],
  index: 0,
  stars: 0,
  correctAnswers: 0,
  mathTotal: 0,
  mathIndex: 0,
  mathCurrent: null,
  wordIndex: 0,
  open(subject) {
    this.subject = subject;
    this.index = 0;
    this.stars = 0;
    this.correctAnswers = 0;
    document.getElementById('subjects').classList.add('hidden');
    document.querySelector('.hero').classList.add('hidden');
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
    fb.innerHTML = `<div class="explain">${correct ? '✅ Верно! ' : '❌ Правильный ответ: ' + q.options[q.answer] + '. '}${q.why}</div>
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
      const fb = document.getElementById('feedback');
      fb.innerHTML = `<div class="explain">${ok ? '✅ Верно! Молодец!' : '❌ Правильный ответ: ' + this.mathCurrent}</div>
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
      if (this.wordIndex >= words.length) this.correctAnswers++;
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
    App.finish(this.subject, stars);
    body.innerHTML = `
      <div class="result">
        <div class="big">🎉</div>
        <h2>Отлично поработал!</h2>
        <p>Правильных ответов: ${this.correctAnswers} из ${total}</p>
        <p>Звёздочек за задание: ${'⭐'.repeat(stars)}</p>
        <p class="hint">Не забудь записать задание в тетрадь — и можно закрывать домашку!</p>
        <button class="next" onclick="Game.close()">К другим предметам</button>
      </div>`;
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());

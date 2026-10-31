/* Zejściówki: losowanie pytań z wybranych wykładów, 15 minut, samoocena zapisywana w przeglądarce. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const STORE_KEY = 'bipol_quiz_v1';
  const SECONDS = 15 * 60;
  const LABELS = {known: 'Umiem', review: 'Do powtórki'};
  let timer = null, deadline = 0;

  function load() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE_KEY) || '{}');
      return saved && typeof saved === 'object' && saved.grades && typeof saved.grades === 'object' ? saved : {grades: {}};
    } catch (_) { return {grades: {}}; }
  }
  let state = load();
  const save = () => { try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch (_) { /* tryb prywatny */ } };

  const bank = () => [...document.querySelectorAll('#tab-quiz .quiz-question')].map(el => ({
    id: el.dataset.quizId, lecture: el.dataset.quizLecture,
    question: el.querySelector('.quiz-text').textContent,
    answer: el.querySelector('.quiz-answer > p').textContent,
    source: el.querySelector('.quiz-answer .studio-fine-print').textContent,
  }));

  function grade(id, value) {
    if (!id || !LABELS[value]) return;
    if (state.grades[id] === value) delete state.grades[id]; else state.grades[id] = value;
    save(); paint();
  }

  function paint() {
    const questions = bank();
    document.querySelectorAll('#tab-quiz [data-quiz-id]').forEach(el => {
      const value = state.grades[el.dataset.quizId] || '';
      el.dataset.quizState = value;
      el.querySelectorAll('[data-quiz-grade]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.quizGrade === value)));
      const mark = el.querySelector('.quiz-state');
      if (mark) mark.textContent = value === 'known' ? '✓' : value === 'review' ? '↻' : '•';
    });
    document.querySelectorAll('[data-quiz-progress]').forEach(el => {
      const own = questions.filter(q => q.lecture === el.dataset.quizProgress);
      el.textContent = `${own.filter(q => state.grades[q.id] === 'known').length}/${own.length}`;
    });
    const known = questions.filter(q => state.grades[q.id] === 'known').length;
    const review = questions.filter(q => state.grades[q.id] === 'review').length;
    $('quizSummary').textContent = `Umiesz ${known} z ${questions.length} pytań; do powtórki: ${review}; nieocenione: ${questions.length - known - review}.`;
  }

  // Najpierw „Do powtórki”, potem nieocenione, na końcu opanowane; w obrębie grupy losowo.
  function draw() {
    const chosen = new Set([...document.querySelectorAll('#quizLectures input:checked')].map(i => i.value));
    const pool = bank().filter(q => chosen.has(q.lecture));
    if (!pool.length) {
      stop();
      $('quizItems').innerHTML = '<li>Zaznacz przynajmniej jeden wykład.</li>';
      $('quizClock').textContent = '—';
      $('quizSession').hidden = false;
      return;
    }
    const rank = q => state.grades[q.id] === 'review' ? 0 : state.grades[q.id] === 'known' ? 2 : 1;
    const picked = pool.map(q => ({q, key: rank(q) + Math.random()})).sort((a, b) => a.key - b.key)
      .slice(0, Number($('quizCount').value)).map(item => item.q);
    $('quizItems').innerHTML = picked.map((q, i) => `<li class="quiz-item" data-quiz-id="${q.id}">
      <p class="quiz-item-question">${BipolStudio.escape(q.question)}</p>
      <label class="studio-field" for="quizAnswer${i}">Twoja odpowiedź<textarea id="quizAnswer${i}" rows="4"></textarea></label>
      <div class="quiz-model" hidden><p><strong>Odpowiedź wzorcowa:</strong> ${BipolStudio.escape(q.answer)}</p><p class="studio-fine-print">${BipolStudio.escape(q.source)}</p>
      <div class="quiz-grade" role="group" aria-label="Samoocena"><button type="button" class="btn btn-outline-sm" data-quiz-grade="known">Umiem</button><button type="button" class="btn btn-outline-sm" data-quiz-grade="review">Do powtórki</button></div></div></li>`).join('');
    $('quizSession').hidden = false;
    $('quizReveal').disabled = false;
    start();
    paint();
    $('quizAnswer0')?.focus();
  }

  function tick() {
    const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
    $('quizClock').textContent = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`;
    $('quizClock').classList.toggle('quiz-late', left <= 60);
    if (!left) { stop(); reveal(); }
  }
  function start() { stop(); deadline = Date.now() + SECONDS * 1000; tick(); timer = setInterval(tick, 1000); }
  function stop() { clearInterval(timer); timer = null; }
  function reveal() {
    stop();
    document.querySelectorAll('#quizItems .quiz-model').forEach(el => { el.hidden = false; });
    $('quizReveal').disabled = true;
  }

  // Arkusz do nauki offline: pytania z wybranych wykładów, odpowiedzi wzorcowe od nowej strony.
  function printSheet() {
    const chosen = new Set([...document.querySelectorAll('#quizLectures input:checked')].map(i => i.value));
    const titles = Object.fromEntries([...document.querySelectorAll('#tab-quiz .quiz-lecture')].map(el =>
      [el.dataset.quizLecture, el.querySelector('summary strong').textContent]));
    const questions = bank().filter(q => chosen.has(q.lecture));
    if (!questions.length) return;
    const esc = BipolStudio.escape;
    const section = withAnswers => [...chosen].filter(key => titles[key]).map(key => {
      const own = questions.filter(q => q.lecture === key);
      return `<h2>${esc(titles[key])}</h2><ol>${own.map(q => `<li><p><strong>${esc(q.question)}</strong></p>`
        + (withAnswers ? `<p>${esc(q.answer)}</p><p class="src">${esc(q.source)}</p>` : '<div class="space"></div>') + '</li>').join('')}</ol>`;
    }).join('');
    const win = window.open('', '_blank');
    if (!win) return;
    win.document.write('<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>BIPOL I — pytania do zejściówek</title>'
      + '<style>@page{size:A4;margin:16mm}body{font:11pt/1.4 sans-serif;color:#111}h1{font-size:15pt}h2{font-size:12pt;margin:14pt 0 4pt}'
      + 'li{margin:0 0 6pt;break-inside:avoid}.space{height:22mm;border-bottom:1px dotted #999}.src{color:#555;font-size:9pt}'
      + '.answers{break-before:page}</style></head><body>'
      + `<h1>BIPOL I — pytania do zejściówek (${questions.length})</h1>${section(false)}`
      + `<div class="answers"><h1>Odpowiedzi wzorcowe</h1>${section(true)}</div></body></html>`);
    win.document.close();
    win.focus();
    win.print();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const panel = $('tab-quiz');
    if (!panel) return;
    try {
      const chosen = JSON.parse(localStorage.getItem(STORE_KEY + '_lectures') || 'null');
      if (Array.isArray(chosen)) document.querySelectorAll('#quizLectures input').forEach(i => { i.checked = chosen.includes(i.value); });
    } catch (_) { /* brak zapisu */ }
    $('quizLectures').addEventListener('change', () => {
      const chosen = [...document.querySelectorAll('#quizLectures input:checked')].map(i => i.value);
      try { localStorage.setItem(STORE_KEY + '_lectures', JSON.stringify(chosen)); } catch (_) { /* tryb prywatny */ }
    });
    panel.addEventListener('click', event => {
      const range = event.target.closest('[data-quiz-range]')?.dataset.quizRange;
      if (range) {
        document.querySelectorAll('#quizLectures input').forEach(i => { i.checked = range === 'all'; });
        $('quizLectures').dispatchEvent(new Event('change'));
      }
      const button = event.target.closest('[data-quiz-grade]');
      if (button) grade(button.closest('[data-quiz-id]')?.dataset.quizId, button.dataset.quizGrade);
    });
    $('quizDraw').addEventListener('click', draw);
    $('quizPrint').addEventListener('click', printSheet);
    $('quizReveal').addEventListener('click', reveal);
    $('quizStop').addEventListener('click', () => { stop(); $('quizSession').hidden = true; });
    paint();
  });
})();

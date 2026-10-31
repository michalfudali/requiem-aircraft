/* Zadanie kolokwialne I: dane z liczby liter, sprawdzenie wyników i rozwiązanie krok po kroku. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const {escape: esc, format: fmt} = BipolStudio;
  const STORE_KEY = 'bipol_exam_v1';
  let result = null, sequence = 0;

  const letters = text => [...String(text || '')].filter(ch => /\p{L}/u.test(ch)).length;
  const tex = source => window.katex
    ? window.katex.renderToString(source, {throwOnError: false, strict: 'ignore', displayMode: true})
    : esc(source);
  const status = (message, error = false) => {
    const el = $('examStatus');
    el.textContent = message || '';
    el.hidden = !message;
    el.classList.toggle('error', error);
  };

  // Wartości do porównania z obliczeniami studenta: klucz, opis, jednostka, cyfry, tolerancja bezwzględna.
  const CHECKS = [
    ['S', 'Powierzchnia skrzydła S', 'm²', 2],
    ['b', 'Rozpiętość b', 'm', 3],
    ['c_r', 'Cięciwa u nasady c_r', 'm', 3],
    ['c_t', 'Cięciwa na końcówce c_k', 'm', 3],
    ['c_g', 'Średnia cięciwa geometryczna c_g', 'm', 3],
    ['c_a', 'Średnia cięciwa aerodynamiczna c_a', 'm', 3],
    ['n_max', 'Wymiarujące n_max', '', 2, 0.02],
    ['n_min', 'Wymiarujące n_min', '', 2, 0.02],
    ['VA_kmh', 'Prędkość manewrowa V_A', 'km/h', 1],
    ['VC_kmh', 'Prędkość przelotowa V_C', 'km/h', 1],
    ['VD_kmh', 'Prędkość nurkowania V_D', 'km/h', 1],
    ['T0', 'Siła tnąca u nasady T₀', 'N', 0],
    ['M0', 'Moment gnący u nasady M₀', 'N·m', 0],
  ];

  function remember(x, y) {
    try { localStorage.setItem(STORE_KEY, JSON.stringify({x, y})); } catch (_) { /* tryb prywatny */ }
  }

  function restore() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE_KEY) || 'null');
      if (Number.isInteger(saved?.x) && Number.isInteger(saved?.y)) { $('examX').value = saved.x; $('examY').value = saved.y; }
    } catch (_) { /* brak zapisu */ }
  }

  function readCount(id) {
    const value = Number($(id).value);
    return Number.isInteger(value) && value >= 1 && value <= 40 ? value : null;
  }

  async function solve(event) {
    event?.preventDefault();
    const x = readCount('examX'), y = readCount('examY');
    if (x == null || y == null) { status('Podaj X i Y jako liczby całkowite od 1 do 40 albo wpisz imię i nazwisko.', true); return; }
    const ticket = ++sequence;
    status('Obliczanie…');
    try {
      const response = await fetch('/api/exam/wing-loads', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({x, y})});
      const answer = await response.json();
      if (ticket !== sequence) return;
      if (!response.ok) throw new Error(answer.message || 'Nie udało się rozwiązać zadania.');
      result = answer;
      remember(x, y);
      status('');
      render();
    } catch (error) {
      if (ticket === sequence) status(error.message, true);
    }
  }

  function chip(label, value) {
    return `<div class="exam-chip"><span>${label}</span><strong>${value}</strong></div>`;
  }

  function renderData() {
    const step = key => result.sections.flatMap(s => s.entries).find(e => e.key === key)?.value;
    $('examData').innerHTML = [
      chip('X', result.x), chip('Y', result.y),
      chip('m<sub>TO</sub> = (X+Y)·100', `${fmt(step('m'), 0)} kg`),
      chip('Paliwo m<sub>TO</sub>/8 (0,25–0,75 rozpiętości)', `${fmt(step('m_f'), 1)} kg`),
      chip('Struktura płata m<sub>TO</sub>/6', `${fmt(step('m_s'), 1)} kg`),
      chip('Wydłużenie Λ = X', fmt(step('AR'), 0)),
      chip('Zbieżność λ = X/(X+Y)', fmt(step('lam'), 4)),
      chip(`Kategoria k = ${result.category_index}`, esc(result.category_label)),
      chip('V<sub>min</sub> wg JAR-23', '61 kt (V<sub>S0</sub>, z klapami)'),
      chip('C<sub>z max</sub> z klapami / gładka', '2,0 / 1,4'),
      chip('C<sub>z min</sub> / C<sub>x min</sub> / e', '−1,1 / 0,04 / 0,9'),
      chip('dC<sub>z</sub>/dα<sub>∞</sub>', '2π'),
    ].join('');
  }

  function renderCheck() {
    $('examCheck').innerHTML = CHECKS.map(([key, label, unit]) =>
      `<label class="studio-field" for="examCheck_${key}">${esc(label)}${unit ? ` [${esc(unit)}]` : ''}
        <input id="examCheck_${key}" data-exam-check="${key}" type="text" inputmode="decimal" autocomplete="off">
        <span class="exam-verdict" data-exam-verdict="${key}" aria-live="polite"></span></label>`).join('')
      + '<button type="submit" class="btn btn-primary">Sprawdź</button>';
    $('examCheckSummary').hidden = true;
  }

  function checkAnswers(event) {
    event.preventDefault();
    if (!result) return;
    let given = 0, good = 0;
    CHECKS.forEach(([key, , unit, digits, absolute]) => {
      const input = $(`examCheck_${key}`), verdict = document.querySelector(`[data-exam-verdict="${key}"]`);
      const raw = input.value.trim().replace(/\s/g, '').replace(',', '.');
      input.classList.remove('exam-ok', 'exam-bad');
      verdict.textContent = '';
      if (!raw) return;
      const value = Number(raw), expected = result.answers[key];
      if (!Number.isFinite(value)) { verdict.textContent = 'To nie jest liczba.'; input.classList.add('exam-bad'); return; }
      given += 1;
      const ok = absolute ? Math.abs(value - expected) <= absolute : Math.abs(value - expected) <= 0.02 * Math.abs(expected);
      if (ok) good += 1;
      input.classList.add(ok ? 'exam-ok' : 'exam-bad');
      verdict.textContent = ok ? '✓ zgodne' : `✗ rozwiązanie: ${fmt(expected, digits)}${unit ? ' ' + unit : ''}`;
    });
    const summary = $('examCheckSummary');
    summary.hidden = false;
    summary.textContent = given ? `Zgodnych wyników: ${good} z ${given}. Przy rozbieżności rozwiń odpowiedni krok poniżej.` : 'Wpisz przynajmniej jeden wynik.';
  }

  function renderSteps() {
    $('examSteps').innerHTML = result.sections.map(section => `<details class="exam-section">
      <summary><strong>${esc(section.title)}</strong>${section.source ? `<small>${esc(section.source)}</small>` : ''}</summary>
      <div class="exam-entries">${section.entries.map(entry => `<div class="exam-entry${entry.kind === 'given' ? ' exam-given' : ''}">
        <div class="exam-entry-label">${esc(entry.label)}${entry.source ? ` <small>${esc(entry.source)}</small>` : ''}</div>
        <div class="exam-math">${tex(entry.tex)}</div>
        ${entry.note ? `<p class="exam-entry-note">${esc(entry.note)}</p>` : ''}</div>`).join('')}</div></details>`).join('');
  }

  function table(head, rows) {
    return `<div class="exam-table-wrap"><table class="b-table exam-table"><thead><tr>${head.map(h => `<th>${h}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }

  // Wykres SVG: serie punktów [y, wartość]; „bars” rysuje słupki pasków.
  function svgPlot(target, {title, xLabel, yLabel, xMax, series, bars}) {
    const W = 460, H = 240, pad = {l: 62, r: 14, t: 28, b: 40};
    const values = series.flatMap(s => s.points.map(p => p[1])).concat(bars ? bars.map(b => b.value) : [], [0]);
    let yMin = Math.min(...values), yMax = Math.max(...values);
    const span = (yMax - yMin) || 1;
    yMin -= span * 0.06 * (yMin < 0); yMax += span * 0.1;
    const X = v => pad.l + v / xMax * (W - pad.l - pad.r);
    const Y = v => H - pad.b - (v - yMin) / (yMax - yMin) * (H - pad.t - pad.b);
    const ticks = 4, grid = [];
    for (let i = 0; i <= ticks; i++) {
      const v = yMin + (yMax - yMin) * i / ticks;
      grid.push(`<line x1="${pad.l}" x2="${W - pad.r}" y1="${Y(v)}" y2="${Y(v)}" class="exam-grid"/><text x="${pad.l - 6}" y="${Y(v) + 4}" text-anchor="end">${fmt(v, Math.abs(yMax - yMin) < 5 ? 2 : 0)}</text>`);
      const x = xMax * i / ticks;
      grid.push(`<text x="${X(x)}" y="${H - pad.b + 15}" text-anchor="middle">${fmt(x, 2)}</text>`);
    }
    const barSvg = (bars || []).map(b => `<rect x="${X(b.from)}" width="${X(b.to) - X(b.from) - 1}" y="${Math.min(Y(b.value), Y(0))}" height="${Math.abs(Y(b.value) - Y(0))}" class="exam-bar"/>
      <text x="${(X(b.from) + X(b.to)) / 2}" y="${Y(b.value) - 5}" text-anchor="middle" class="exam-bar-label">${fmt(b.value, 3)}</text>`).join('');
    const lines = series.map(s => `<polyline fill="none" stroke="${s.color}" stroke-width="2"${s.dash ? ' stroke-dasharray="5 4"' : ''} points="${s.points.map(p => `${X(p[0])},${Y(p[1])}`).join(' ')}"/>
      ${(s.marks || []).map(p => `<circle cx="${X(p[0])}" cy="${Y(p[1])}" r="3" fill="${s.color}"/>`).join('')}`).join('');
    const legend = series.filter(s => s.label).map((s, i) => `<g transform="translate(${pad.l + 8 + i * 170},${pad.t - 12})"><line x1="0" x2="18" y1="0" y2="0" stroke="${s.color}" stroke-width="2"${s.dash ? ' stroke-dasharray="5 4"' : ''}/><text x="23" y="4">${esc(s.label)}</text></g>`).join('');
    $(target).innerHTML = `<figure><figcaption>${esc(title)}</figcaption><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title)}">
      ${grid.join('')}<line x1="${pad.l}" x2="${W - pad.r}" y1="${Y(0)}" y2="${Y(0)}" class="exam-axis"/>
      ${barSvg}${lines}${legend}
      <text x="${(pad.l + W - pad.r) / 2}" y="${H - 6}" text-anchor="middle" class="exam-axis-label">${esc(xLabel)}</text>
      <text transform="translate(14 ${(pad.t + H - pad.b) / 2}) rotate(-90)" text-anchor="middle" class="exam-axis-label">${esc(yLabel)}</text></svg></figure>`;
  }

  // Siła tnąca i moment gnący od obciążeń skupionych w środkach pasków: dokładny przebieg schodkowy/łamany.
  function distribution(rows, key) {
    const half = rows[rows.length - 1].y_inner + (rows[1].y_inner - rows[0].y_inner);
    const loads = rows.map(r => ({y: r.y, p: r[key]}));
    const shearAt = y => loads.filter(l => l.y > y).reduce((a, l) => a + l.p, 0);
    const momentAt = y => loads.filter(l => l.y > y).reduce((a, l) => a + l.p * (l.y - y), 0);
    const shear = [[half, 0]];
    [...loads].reverse().forEach(l => { shear.push([l.y, shearAt(l.y)]); shear.push([l.y, shearAt(l.y - 1e-9)]); });
    shear.push([0, shearAt(0)]);
    const moment = [half, ...[...loads].reverse().map(l => l.y), 0].map(y => [y, momentAt(y)]);
    return {half, shear, moment};
  }

  function renderSchrenk() {
    const rows = result.rows, dy = rows[1].y_inner - rows[0].y_inner, half = rows[0].y_inner + dy * rows.length;
    svgPlot('examSchrenkChart', {
      title: 'Lokalny współczynnik c_z,i / C_z (słupki) i siła nośna paska przy n = 1',
      xLabel: 'y [m] od płaszczyzny symetrii', yLabel: 'c_z,i / C_z', xMax: half,
      bars: rows.map(r => ({from: r.y_inner, to: r.y_inner + dy, value: r.cz_ratio})),
      series: [{points: [[0, 1], [half, 1]], color: '#94a3b8', dash: true, label: 'C_z płata'}],
    });
    $('examSchrenkTable').innerHTML = table(
      ['i', 'y<sub>i</sub> [m]', 'c<sub>i</sub> [m]', 'S<sub>i</sub> [m²]', 'c<sub>e,i</sub> [m]', 'c<sub>z,i</sub>/C<sub>z</sub>', 'c<sub>z,i</sub> przy C<sub>z max</sub>', 'L<sub>t</sub> [N]', 'L<sub>e</sub> [N]', 'L<sub>i</sub> [N]'],
      rows.map(r => [r.i, fmt(r.y, 3), fmt(r.c, 3), fmt(r.area, 4), fmt(r.c_e, 3), fmt(r.cz_ratio, 3), fmt(r.cz_at_max, 3), fmt(r.lift_t, 1), fmt(r.lift_e, 1), fmt(r.lift, 1)]));
  }

  function renderLoads() {
    const rows = result.rows, limit = distribution(rows, 'p_unit'), zero = distribution(rows, 'p_unit_zf');
    const n = result.envelope.limits.n_max, nZero = result.zero_fuel.n_max;
    const scale = (pts, k) => pts.map(([y, v]) => [y, v * k]);
    const marks = (key, k) => rows.map(r => [r.y_inner, r[key] * k]);
    svgPlot('examShearChart', {title: 'Siła tnąca T(y), obciążenie dopuszczalne', xLabel: 'y [m]', yLabel: 'T [N]', xMax: limit.half,
      series: [{points: scale(limit.shear, n), color: '#0369a1', label: 'z paliwem', marks: marks('t_unit', n)},
               {points: scale(zero.shear, nZero), color: '#b45309', dash: true, label: `bez paliwa, n = ${fmt(nZero, 2)}`}]});
    svgPlot('examMomentChart', {title: 'Moment gnący M(y), obciążenie dopuszczalne', xLabel: 'y [m]', yLabel: 'M [N·m]', xMax: limit.half,
      series: [{points: scale(limit.moment, n), color: '#0369a1', label: 'z paliwem', marks: marks('m_unit', n)},
               {points: scale(zero.moment, nZero), color: '#b45309', dash: true, label: `bez paliwa, n = ${fmt(nZero, 2)}`}]});
    $('examLoadTable').innerHTML = table(
      ['i', 'krawędź y [m]', 'm<sub>str,i</sub> [kg]', 'm<sub>p,i</sub> [kg]', 'P<sub>i</sub> (n=1) [N]', 'T<sub>i</sub> (n=1) [N]', 'M<sub>i</sub> (n=1) [N·m]', `T<sub>i</sub> (n=${fmt(n, 2)}) [N]`, `M<sub>i</sub> (n=${fmt(n, 2)}) [N·m]`, 'M<sub>i</sub> obl. ×1,5 [N·m]', 'M<sub>i</sub> bez paliwa [N·m]'],
      rows.map(r => [r.i, fmt(r.y_inner, 3), fmt(r.m_struct, 2), fmt(r.m_fuel, 2), fmt(r.p_unit, 1), fmt(r.t_unit, 1), fmt(r.m_unit, 1), fmt(r.t_limit, 0), fmt(r.m_limit, 0), fmt(r.m_ult, 0), fmt(r.m_limit_zf, 0)]));
    const governing = result.governing === 'zero_fuel'
      ? 'Wymiarujący jest samolot bez paliwa. Paliwo wymaga większej siły nośnej, ale jego ciężar leży dalej od kadłuba (0,25–0,75 półrozpiętości) niż środek tej dodatkowej siły nośnej, więc w sumie odciąża płat.'
      : 'Wymiarujący jest samolot z pełnym paliwem.';
    $('examNotes').innerHTML = `<p><strong>${esc(governing)}</strong></p>${result.notes.map(s => `<p>${esc(s)}</p>`).join('')}`;
  }

  function renderEnvelope() {
    const env = result.envelope;
    if (typeof drawVnEnvelope === 'function') drawVnEnvelope('examEnvelopeCanvas', env);
    $('examPoints').innerHTML = table(['Punkt', 'V [km/h]', 'n'], env.points.map(p =>
      [esc(p.point), fmt(p.v_kmh, 1), p.n_neg == null ? fmt(p.n, 2) : `${fmt(p.n, 2)} / ${fmt(p.n_neg, 2)} (U = ${fmt(p.u_ms, 2)} m/s)`]));
  }

  function render() {
    if (!result) return;
    $('examResult').hidden = false;
    renderData(); renderCheck(); renderSteps(); renderSchrenk(); renderLoads();
    requestAnimationFrame(renderEnvelope);
  }

  function syncCount(source, target) {
    const count = letters($(source).value);
    if (count) $(target).value = Math.min(40, count);
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (!$('tab-exam')) return;
    restore();
    $('examFirst').addEventListener('input', () => syncCount('examFirst', 'examX'));
    $('examLast').addEventListener('input', () => syncCount('examLast', 'examY'));
    $('examForm').addEventListener('submit', solve);
    $('examCheck').addEventListener('submit', checkAnswers);
    $('tab-exam').addEventListener('click', event => {
      const mode = event.target.closest('[data-exam-expand]')?.dataset.examExpand;
      if (mode) document.querySelectorAll('#examSteps details').forEach(d => { d.open = mode === 'open'; });
    });
    // Płótno obwiedni ma szerokość kontenera; po pokazaniu zakładki lub zmianie okna rysujemy je ponownie.
    let resizeTimer;
    window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (result && $('tab-exam').classList.contains('active')) renderEnvelope(); }, 150); });
    document.querySelector('.bipol-tab[data-target="tab-exam"]')?.addEventListener('click', () => { if (result) requestAnimationFrame(renderEnvelope); });
  });
  window.BipolExam = {letters};
})();

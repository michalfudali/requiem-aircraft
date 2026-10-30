(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const {escape: esc, format: fmt} = BipolStudio;
  const labels = {blocked:'Wykryte braki', stale:'Sprawdź po zmianie wariantu', manual:'Własne opracowanie', review:'Do przeglądu'};
  let review, resultProject, fresh = false, iterating = false, gradeSequence = 0, gradeTimer, lastGradeKey = '', lastGradePlan = null, inflightGradeKey = '';
  const data = () => structuredClone(formBaseParams.coursework || {});

  function persist(value) {
    const active = getActiveProject();
    if (!active) return;
    formBaseParams.coursework = value;
    active.params.coursework = value;
    if (currentResults && resultProject === active.id) currentResults.params.coursework = value;
    saveProject(active);
  }

  function renderGrade(plan) {
    const grade = plan.grade == null ? 'Brak pełnych danych do oceny' : `Ocena według wpisanych punktów: ${fmt(plan.grade, 1)}`;
    const target = plan.quizzes_needed_for_five;
    const total = plan.total == null ? 'Uzupełnij brakujące oceny.' : `Łącznie: ${fmt(plan.total, 1)} / 200 pkt.`;
    $('courseworkGrade').innerHTML = `<p><strong>${esc(grade)}</strong></p><p>${esc(total)}</p>
      <p>Najwyższa suma przy maksymalnych brakujących ocenach: ${fmt(plan.maximum_possible, 1)} pkt.</p>
      <p>${plan.five_possible ? `Do progu 5,0 możesz jeszcze stracić ${fmt(Math.max(0, plan.remaining_loss_budget), 1)} pkt.` : '5,0 nie jest osiągalne przy wpisanych wynikach i warunkach zaliczenia.'}</p>
      ${target == null ? '' : `<p>Przy tych punktach projektowych potrzeba ${fmt(target, 1)} / 100 pkt z zejściówek.${target > 100 ? ' To przekracza ich maksymalną punktację.' : ''}</p>`}
      ${plan.projects_needed_for_five == null ? '' : `<p>Przy tym wyniku zejściówek potrzeba ${fmt(plan.projects_needed_for_five, 1)} / 100 pkt z projektów.</p>`}
      ${plan.blockers.length ? `<ul>${plan.blockers.map(s => `<li>${esc(s)}</li>`).join('')}</ul>` : ''}
      ${plan.complete ? '' : '<p>Wynik pozostaje warunkowy do wpisania wszystkich ocen i potwierdzenia zaliczenia wszystkich zejściówek.</p>'}`;
  }

  async function updateGrade(sequence, projectId) {
    const payload = JSON.stringify(data());
    const cacheKey = `${projectId}:${payload}`;
    if (cacheKey === lastGradeKey && lastGradePlan) {
      renderGrade(lastGradePlan);
      return;
    }
    inflightGradeKey = cacheKey;
    try {
      const response = await fetch('/api/coursework/grade', {method:'POST', headers:{'Content-Type':'application/json'}, body:payload});
      const plan = await response.json();
      if (sequence !== gradeSequence || projectId !== getActiveProjectId()) return;
      if (!response.ok) throw Error(plan.message || 'Nie udało się obliczyć punktacji.');
      lastGradeKey = cacheKey;
      lastGradePlan = plan;
      renderGrade(plan);
    } catch (error) {
      if (sequence === gradeSequence && projectId === getActiveProjectId()) $('courseworkGrade').textContent = error.message;
    } finally {
      if (inflightGradeKey === cacheKey) inflightGradeKey = '';
    }
  }

  function saveScores() {
    const sequence = ++gradeSequence;
    clearTimeout(gradeTimer);
    const controls = [...document.querySelectorAll('[data-coursework-score]'), $('courseworkQuizPoints')];
    if (controls.some(el => !el.checkValidity() || (el.value !== '' && !Number.isFinite(Number(el.value))))) {
      $('courseworkGrade').textContent = 'Sprawdź zakres punktów. Nieprawidłowe wartości nie zostały zapisane.';
      return;
    }
    const value = data();
    value.scores = Object.fromEntries(controls.filter(el => el.dataset.courseworkScore)
      .map(el => [el.dataset.courseworkScore, el.value === '' ? null : Number(el.value)]));
    value.quiz_points = $('courseworkQuizPoints').value === '' ? null : Number($('courseworkQuizPoints').value);
    const passed = $('courseworkQuizzesPassed').value;
    value.quizzes_passed = passed === '' ? null : passed === 'yes';
    persist(value);
    $('courseworkGrade').textContent = 'Przeliczanie punktacji…';
    gradeTimer = setTimeout(() => updateGrade(sequence, getActiveProjectId()), 180);
  }

  function syncScores() {
    const value = data();
    document.querySelectorAll('[data-coursework-score]').forEach(el => { el.value = value.scores?.[el.dataset.courseworkScore] ?? ''; });
    $('courseworkQuizPoints').value = value.quiz_points ?? '';
    $('courseworkQuizzesPassed').value = value.quizzes_passed == null ? '' : value.quizzes_passed ? 'yes' : 'no';
    clearTimeout(gradeTimer);
    const projectId = getActiveProjectId();
    const cacheKey = `${projectId}:${JSON.stringify(value)}`;
    if (cacheKey === inflightGradeKey) return;
    updateGrade(++gradeSequence, projectId);
  }

  function state(item) {
    const entry = data().evidence?.[item.key];
    return item.checks.some(c => !c.passed) ? 'blocked' : !entry?.note?.trim() ? 'manual'
      : entry.signature !== review.signature ? 'stale' : 'review';
  }

  function renderSummary() {
    if (!review) return;
    const ready = review.items.filter(item => state(item) === 'review').length;
    const blocked = review.items.filter(item => state(item) === 'blocked').length;
    $('courseworkReadiness').textContent = `${ready} / 21 podpunktów z odniesieniem do opracowania i bez wykrytych przeszkód; ${blocked} z wykrytymi brakami. To przegląd kompletności, nie zdobyte punkty.`;
    const pending = review.items.filter(item => state(item) !== 'review').sort((a, b) =>
      Number(b.mandatory)-Number(a.mandatory) || Number(state(b)==='blocked')-Number(state(a)==='blocked') || b.points-a.points);
    $('courseworkPriority').innerHTML = pending.slice(0, 5).map(item => `<article class="coursework-priority"><strong>${item.key.replace('_','.').toUpperCase()} · ${esc(item.label)}</strong><p>${esc(item.checks.find(c => !c.passed)?.detail || item.prompt)}</p><button type="button" class="studio-text-button" data-coursework-open="${item.key}">Pokaż zakres i opracowanie →</button></article>`).join('') || '<p>Wszystkie podpunkty są przygotowane do przeglądu przez prowadzącego.</p>';
    const filter = $('courseworkFilter').value;
    review.items.forEach(item => {
      const root = $(`courseworkItem_${item.key}`), status = state(item);
      if (!root) return;
      const badge = root.querySelector('.coursework-state');
      badge.dataset.state = status; badge.textContent = labels[status];
      root.hidden = filter === 'remaining' && status === 'review' && !root.contains(document.activeElement) || filter === 'mandatory' && !item.mandatory || filter === 'optional' && item.mandatory;
    });
  }

  function freshness() {
    $('courseworkFreshness').textContent = fresh ? '' : 'Wyniki wymagają przeliczenia. Odniesienia do opracowań można przypisać po obliczeniu aktualnego wariantu.';
    $('courseworkIterate').disabled = !fresh || iterating;
    document.querySelectorAll('[data-coursework-evidence], [data-coursework-confirm]').forEach(el => { el.disabled = !fresh; });
  }

  function renderEngineeringAudit(audit) {
    const listEl = $('courseworkAuditList');
    const badgeEl = $('courseworkAuditBadge');
    if (!listEl || !audit) return;

    if (badgeEl) {
      badgeEl.textContent = `${audit.passed_count} / ${audit.total_count} zaliczone (${audit.quality_score_pct}%)`;
      badgeEl.className = `badge ${audit.passed_count === audit.total_count ? 'badge-success' : 'badge-warning'}`;
    }

    listEl.innerHTML = audit.checks.map(c => `
      <div class="audit-item-card ${c.passed ? 'audit-passed' : 'audit-warning'}">
        <div class="audit-item-header">
          <div>
            <div class="audit-cat-tag">${esc(c.category)}</div>
            <div class="audit-item-title">${esc(c.title)}</div>
          </div>
          <span class="${c.passed ? 'audit-badge-ok' : 'audit-badge-warn'}">${c.passed ? '✓ Zgodny' : '⚠️ Sprawdź'}</span>
        </div>
        <div class="audit-values-row">
          <div class="audit-val-chip"><strong>Wartość:</strong> ${esc(c.value)}</div>
          <div class="audit-val-chip"><strong>Wymóg:</strong> ${esc(c.required)}</div>
        </div>
        <div class="audit-didactic-text">
          💡 <strong>Prosto mówiąc:</strong> ${esc(c.didactic_simple)}
        </div>
        <div class="audit-eng-note">
          ⚙️ <strong>Wskazówka inżynierska:</strong> ${esc(c.engineering_note)}
        </div>
      </div>
    `).join('');

    const qListEl = $('courseworkDefenseQuestionsList');
    if (qListEl && audit.defense_questions) {
      qListEl.innerHTML = audit.defense_questions.map((q, idx) => `
        <details class="defense-q-card" ${idx === 0 ? 'open' : ''}>
          <summary>
            <span class="audit-cat-tag" style="background:#eaf2f5; padding:2px 6px; border-radius:3px;">${esc(q.topic)}</span>
            <strong>Pytanie ${idx + 1}:</strong> ${esc(q.question)}
          </summary>
          <div class="defense-q-answer">
            🎓 <strong>Wzorcowa odpowiedź na obronie:</strong><br>
            ${esc(q.expected_answer)}
          </div>
          <div class="defense-q-tip">
            📌 <strong>Wskazówka prowadzącego:</strong> ${esc(q.faculty_tip)}
          </div>
        </details>
      `).join('');
    }
  }

  function render(result) {
    review = result.submission_review;
    if (!review) return;
    resultProject = getActiveProjectId(); fresh = true;
    syncScores();
    $('courseworkItems').innerHTML = review.items.map(item => `<details class="coursework-item" id="courseworkItem_${item.key}"><summary><strong>${item.key.replace('_','.').toUpperCase()} · ${esc(item.label)}</strong><small>${item.mandatory ? 'Obowiązkowe' : 'Opcjonalne'} · maks. ${item.points} pkt</small><span class="coursework-state"></span></summary>
      <p>${esc(item.prompt)}</p>${item.checks.length ? `<ul>${item.checks.map(c => `<li><strong>${c.passed ? 'Sprawdzone' : 'Do poprawy'}: ${esc(c.label)}</strong> — ${esc(c.detail)}</li>`).join('')}</ul>` : '<p class="studio-fine-print">Wymaga oceny własnego opracowania i danych źródłowych.</p>'}
      <button type="button" class="studio-text-button" data-studio-target="${item.target}">Otwórz odpowiednią analizę →</button>
      <label class="studio-field" for="courseworkEvidence_${item.key}">Odniesienie do własnego opracowania i uzasadnienie<textarea id="courseworkEvidence_${item.key}" data-coursework-evidence="${item.key}" maxlength="4000" rows="3" placeholder="Np. arkusz, rysunek, dokument i strona; Twoja interpretacja…">${esc(data().evidence?.[item.key]?.note || '')}</textarea></label>
      <button type="button" class="btn btn-outline-sm" data-coursework-confirm="${item.key}">Sprawdziłem opracowanie dla tego wariantu</button></details>`).join('');
    const polar = review.polar;
    $('courseworkPolar').innerHTML = `<table class="b-table"><thead><tr><th>Parametr</th><th>Założenie P2</th><th>Wynik P4</th></tr></thead><tbody>${[['Cx₀',polar.assumed_cx0,polar.calculated_cx0,4],['e',polar.assumed_e,polar.calculated_e,3],['Kmax',polar.assumed_kmax,polar.calculated_kmax,2]].map(([label,a,b,d]) => `<tr><th>${label}</th><td>${fmt(a,d)}</td><td>${fmt(b,d)}</td></tr>`).join('')}</tbody></table>${review.performance_findings.map(s => `<p>${esc(s)}</p>`).join('')}`;
    renderSummary(); freshness();
    if (result.engineering_audit) renderEngineeringAudit(result.engineering_audit);
  }

  function saveEvidence(key, confirm = false) {
    if (!fresh || resultProject !== getActiveProjectId()) return;
    const value = data(), input = $(`courseworkEvidence_${key}`);
    value.evidence ||= {};
    const previous = value.evidence[key];
    // Editing an old declaration does not silently confirm a changed design.
    const signature = confirm || !previous?.note?.trim() ? review.signature : previous.signature || '';
    value.evidence[key] = {note:input.value, signature};
    persist(value); renderSummary();
  }

  async function iterate() {
    const button = $('courseworkIterate'), origin = getActiveProject(), originId = origin?.id;
    if (!fresh || iterating || resultProject !== originId) return;
    iterating = true; button.disabled = true;
    $('courseworkIterationStatus').textContent = 'Przeliczanie nowego wariantu…';
    try {
      const params = collectFormData(), basis = JSON.stringify(params);
      const response = await fetch('/api/coursework/iterate-polar', {method:'POST', headers:{'Content-Type':'application/json'}, body:basis});
      const answer = await response.json();
      if (originId !== getActiveProjectId()) return;
      if (basis !== JSON.stringify(collectFormData())) {
        $('courseworkIterationStatus').textContent = 'Założenia zmieniły się podczas obliczeń. Przelicz projekt i ponów iterację.';
        return;
      }
      if (!response.ok) throw Error(answer.message || 'Nie udało się obliczyć wariantu.');
      const name = `${origin.name} · P2←P4`;
      const project = {...structuredClone(origin), id:BipolStudio.uniqueId('proj_'), name,
        params:{...answer.result.params, name}, createdAt:new Date().toISOString(), summary:{},
        semesterChecklist:{}, iteration:{source_project_id:originId, before:answer.before, after:answer.after}};
      // A different variant has not received the source project's grades.
      project.params.coursework = {evidence:project.params.coursework?.evidence || {}};
      saveProject(project); switchActiveProject(project.id);
      $('courseworkIterationStatus').textContent = `Utworzono „${name}”. MTOW: ${fmt(answer.mtow_before,1)} → ${fmt(answer.mtow_after,1)} kg po ${answer.iterations.length} krokach bilansu uściślonego. Sprawdź pozostałe wymagania i zaktualizuj odniesienia do opracowań.`;
    } catch (error) {
      if (originId === getActiveProjectId()) $('courseworkIterationStatus').textContent = error.message;
    } finally { iterating = false; freshness(); }
  }

  document.addEventListener('DOMContentLoaded', () => {
    $('courseworkScores').addEventListener('input', saveScores);
    $('courseworkFilter').addEventListener('change', renderSummary);
    $('courseworkItems').addEventListener('input', event => {
      if (event.target.dataset.courseworkEvidence) saveEvidence(event.target.dataset.courseworkEvidence);
    });
    $('tab-coursework').addEventListener('click', event => {
      const confirm = event.target.closest('[data-coursework-confirm]');
      if (confirm) saveEvidence(confirm.dataset.courseworkConfirm, true);
      const open = event.target.closest('[data-coursework-open]');
      if (open) { const root = $(`courseworkItem_${open.dataset.courseworkOpen}`); root.open = true; root.scrollIntoView({behavior:'smooth', block:'center'}); root.querySelector('textarea').focus({preventScroll:true}); }
    });
    $('courseworkIterate').addEventListener('click', iterate);
    const stale = () => { fresh = false; freshness(); };
    $('designForm').addEventListener('input', stale);
    $('designForm').addEventListener('change', stale);
    document.querySelectorAll('[data-analysis-param], [data-bipol1]').forEach(el => {
      el.addEventListener('input', stale); el.addEventListener('change', stale);
    });
    document.addEventListener('bipol:calculating', stale);
    document.addEventListener('bipol:project', () => {
      review = null; resultProject = null; stale(); syncScores();
      $('courseworkItems').textContent = ''; $('courseworkPriority').textContent = '';
      $('courseworkReadiness').textContent = 'Oczekiwanie na obliczenia aktywnego projektu.';
      $('courseworkPolar').textContent = ''; $('courseworkIterationStatus').textContent = '';
    });
    document.addEventListener('bipol:results', event => render(event.detail));
    if (currentResults) render(currentResults); else { syncScores(); freshness(); }
  });
})();

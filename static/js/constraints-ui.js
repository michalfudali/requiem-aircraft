/**
 * constraints-ui.js - Moduł blokowania parametrów, sugerowanych ograniczeń i obrysu skrzydła
 * Politechnika Warszawska MEiL PW - BIPOL I
 */

window.userLockedParams = new Set(['aircraft_type', 'category']);

const WING_PLANFORMS_INFO = {
  trapezoidal: {
    name_pl: 'Trapezowy (zbieżny klasyczny)',
    stall_summary: 'Sam obrys nie przesądza o przeciągnięciu. Potrzebne są profile, zwichrzenie i rozkład lokalnego Cz.',
    pros: 'Optymalny kompromis aerodynamiczno-wytrzymałościowy. Mniejsza masa dźwigarów w nasadzie niż w skrzydle prostokątnym.',
    cons: 'Wymaga zbieżnych żeber o zmiennej geometrii (wyższy koszt tłoczenia niż prostokątne).',
    aircraft: modelExample('wing_planform', 'trapezoidal')
  },
  rectangular: {
    name_pl: 'Prostokątny (stała cięciwa c = const)',
    stall_summary: 'Sam obrys nie przesądza o przeciągnięciu. Potrzebne są profile, zwichrzenie i rozkład lokalnego Cz.',
    pros: 'Maksymalna prostota technologiczna: wszystkie żebra są identyczne, proste poszycie bez skręcenia.',
    cons: 'Wyższy opór indukowany (współczynnik e ~ 0.70–0.78); cięższa nasada skrzydła ze względu na większą cięciwę przykadłubową.',
    aircraft: modelExample('wing_planform', 'rectangular')
  },
  compound_trapezoid: {
    name_pl: 'Prostokątno-trapezowy (centropłat prostokątny + końcówki trapezowe)',
    stall_summary: 'Sam obrys nie przesądza o przeciągnięciu. Potrzebne są profile, zwichrzenie i rozkład lokalnego Cz.',
    pros: 'Centropłat o stałej cięciwie ułatwia montaż klap, podwozia i zbiorników; trapezowe końcówki redukują opór indukowany.',
    cons: 'Punkt załamania krawędzi spływu wymaga dodatkowego węzła konstrukcyjnego.',
    aircraft: modelExample('wing_planform', 'compound_trapezoid')
  },
  elliptical: {
    name_pl: 'Eliptyczny (minimalny opór indukowany wg Prandtla)',
    stall_summary: 'Sam obrys nie przesądza o przeciągnięciu. Potrzebne są profile, zwichrzenie i rozkład lokalnego Cz.',
    pros: 'Teoretycznie minimalny możliwy opór indukowany (współczynnik Oswalda e = 1.0 dla skrzydła płaskiego).',
    cons: 'Bardzo wysoki koszt produkcji: każde żebro ma inne wymiary i krzywiznę, trudne wykonanie kesonu.',
    aircraft: modelExample('wing_planform', 'elliptical')
  },
  swept_trapezoidal: {
    name_pl: 'Skośny trapezowy (wysokie liczby Macha)',
    stall_summary: 'Sam obrys nie przesądza o przeciągnięciu. Potrzebne są profile, zwichrzenie i rozkład lokalnego Cz.',
    pros: 'Przesunięcie krytycznej liczby Macha Makr ku wyższym prędkościom przelotowym; mniejszy opór falowy.',
    cons: 'Spadek współczynnika siły nośnej cz_max; konieczność stosowania bardziej złożonej mechanizacji krawędzi natarcia (sloty).',
    aircraft: modelExample('wing_planform', 'swept_trapezoidal')
  }
};

function toggleParamLock(paramKey) {
  if (document.getElementById(paramKey)?.readOnly) return;
  const btn = document.getElementById(`lock_btn_${paramKey}`);
  const group = document.querySelector(`.input-group[data-param="${paramKey}"]`);
  const input = document.getElementById(paramKey);

  if (window.userLockedParams.has(paramKey)) {
    window.userLockedParams.delete(paramKey);
    if (paramKey === 'engine_power_kw') document.getElementById('power_input_mode').value = 'sized';
    if (paramKey === 'm_payload') document.getElementById('payload_input_mode').value = 'seats';
    if (btn) {
      btn.textContent = '🔓';
      btn.classList.remove('is-locked');
      btn.title = 'Parametr automatyczny. Kliknij 🔒 aby zablokować jako stałe założenie.';
    }
    if (group) group.classList.remove('is-locked');
  } else {
    window.userLockedParams.add(paramKey);
    if (btn) {
      btn.textContent = '🔒';
      btn.classList.add('is-locked');
      btn.title = 'Zablokowany przez Ciebie (Założenie wejściowe). Kliknij 🔓 aby odblokować.';
    }
    if (group) group.classList.add('is-locked');
  }

  if (btn) btn.setAttribute('aria-pressed', String(window.userLockedParams.has(paramKey)));
  // Wykonaj przeliczenie z nowym zbiorem blokad
  if (typeof performCalculation === 'function') {
    performCalculation();
  }
}

function applySuggestedConstraint(paramKey, value) {
  if (paramKey === 'wingspan_m') document.getElementById('wing_input_mode').value = 'span_aspect';
  if (paramKey === 'm_payload') document.getElementById('payload_input_mode').value = 'total';
  if (paramKey === 'engine_power_kw') document.getElementById('power_input_mode').value = 'fixed';
  const input = document.getElementById(paramKey);
  if (input) {
    input.value = value;
  }
  window.userLockedParams.add(paramKey);
  const btn = document.getElementById(`lock_btn_${paramKey}`);
  if (btn) {
    btn.setAttribute('aria-pressed', 'true');
    btn.textContent = '🔒';
    btn.classList.add('is-locked');
    btn.title = 'Zablokowany przez Ciebie (Założenie wejściowe)';
  }
  const group = document.querySelector(`.input-group[data-param="${paramKey}"]`);
  if (group) group.classList.add('is-locked');

  if (typeof performCalculation === 'function') {
    performCalculation();
  }
}

function updateDerivedUI(paramStates) {
  if (!paramStates) return;
  document.querySelectorAll('#designForm .is-derived').forEach(group => {
    group.classList.remove('is-derived');
    group.querySelectorAll('input').forEach(input=>input.readOnly=false);
    group.querySelectorAll('.derived-badge').forEach(badge=>badge.style.display='none');
    group.querySelectorAll('.param-lock-btn').forEach(button=>button.disabled=false);
  });

  for (const [key, info] of Object.entries(paramStates)) {
    const input = document.getElementById(key);
    const group = document.querySelector(`.input-group[data-param="${key}"]`);
    const btn = document.getElementById(`lock_btn_${key}`);
    const badge = document.getElementById(`derived_badge_${key}`);

    if (!input || !group) continue;

    if (btn) btn.disabled = info.state === 'derived';
    if (info.state === 'derived') {
      input.readOnly = true;
      if (info.value != null && !isNaN(info.value)) {
        const digits = Number.isInteger(info.display_digits) ? Math.max(0, Math.min(12, info.display_digits)) : 2;
        input.value = typeof info.value === 'number' ? (Number.isInteger(info.value) ? info.value : +info.value.toFixed(digits)) : info.value;
      }
      group.classList.add('is-derived');
      group.classList.remove('is-locked');
      if (btn) {
        btn.textContent = '⛓️';
        btn.classList.remove('is-locked');
        btn.title = `Parametr zależny, wyliczony ze wzoru: ${info.formula}`;
      }
      if (badge) {
        badge.style.display = 'flex';
        badge.innerHTML = `<span>⛓️</span> <span>Wyliczono z [${info.sources.join(', ')}]: <b>${info.formula}</b></span>`;
      }
    } else if (info.state === 'locked') {
      input.readOnly = false;
      group.classList.remove('is-derived');
      group.classList.add('is-locked');
      if (btn) {
        btn.textContent = '🔒';
        btn.classList.add('is-locked');
        btn.title = 'Zablokowany przez Ciebie (Założenie wejściowe)';
      }
      if (badge) {
        badge.style.display = 'none';
      }
    } else {
      input.readOnly = false;
      group.classList.remove('is-derived');
      group.classList.remove('is-locked');
      if (btn) {
        btn.textContent = '🔓';
        btn.classList.remove('is-locked');
        btn.title = 'Parametr automatyczny. Kliknij 🔒 aby przypiąć.';
      }
      if (badge) {
        badge.style.display = 'none';
      }
    }
  }
  window.BipolDesignBasis?.applyResult(currentResults);
}

async function renderInitialSuggestions() {
  const catEl = document.getElementById('category');
  const typeEl = document.getElementById('aircraft_type');
  const cat = catEl ? catEl.value : 'jar23_normal';
  const acType = typeEl ? typeEl.value : 'piston_ga';

  const container = document.getElementById('suggestionsCardsContainer');
  if (!container) return;

  try {
    // Same comparison sample as the P1 trend analysis of this project.
    const [cResp, tData] = await Promise.all([
      fetch(`/api/constraints/suggestions?category=${encodeURIComponent(cat)}&aircraft_type=${encodeURIComponent(acType)}`),
      window.BipolTrendProvenance.fetchSuggestions({aircraft_type: acType,
        engine_type: document.getElementById('engine_type')?.value || '',
        wing_configuration: document.getElementById('wing_config')?.value || ''}).catch(() => ({suggestions: {}}))
    ]);
    const cData = cResp.ok ? await cResp.json() : {suggestions: []};

    const noEngine = document.getElementById('engine_type')?.value === 'none';
    const suggestions = (cData.suggestions || []).filter(s=>!noEngine||!['engine_power_kw','takeoff_run_m'].includes(s.param));

    if (tData.suggestions) {
      const ar = tData.suggestions.ar;
      if (ar?.suggested_value != null) {
        suggestions.push({
          id: 'trend_ar',
          param: 'aspect_ratio',
          title: `Wydłużenie skrzydła Λ (${ar.suggested_value}) — analiza trendów`,
          value: ar.suggested_value,
          unit: '—',
          description: `${ar.provenance.method}: ${ar.equation}. Typowy zakres: ${ar.typical_range ? ar.typical_range.join(' – ') : '—'}; n = ${ar.n}.`,
          standard: 'BIPOL_1 / Analiza trendów',
          icon: '📈',
          trend: ar
        });
      }
      const dihedral = tData.suggestions.dihedral_deg;
      if (dihedral?.suggested_value != null) {
        suggestions.push({
          id: 'trend_dihedral',
          param: 'dihedral_deg',
          title: `Wznios skrzydła Γ (${dihedral.suggested_value}°) — średnia z bazy`,
          value: dihedral.suggested_value,
          unit: '°',
          description: `${dihedral.provenance.method}: ${dihedral.equation}; n = ${dihedral.n}.`,
          standard: 'BIPOL_1 / Średnie parametry',
          icon: '📐',
          trend: dihedral
        });
      }
    }

    if (suggestions.length === 0) {
      container.innerHTML = '<div style="font-size:0.75rem; color:#64748b;">Brak specyficznych ograniczeń dla wybranej konfiguracji.</div>';
      return;
    }

    container.innerHTML = suggestions.map(s => `
      <div class="suggestion-card">
        <div>
          <div class="suggestion-card-header">
            <span>${s.icon || '📌'}</span>
            <span>${s.title}</span>
          </div>
          <div class="suggestion-card-desc">${s.description}</div>
          ${s.trend ? `<details class="trend-provenance-box"><summary>Skąd ta wartość?</summary>${BipolTrendProvenance.render(s.trend)}</details>` : ''}
        </div>
        <div class="suggestion-card-footer">
          <span style="font-size:0.75rem; font-weight:700; color:#0284c7;">Wartość: ${s.value} ${s.unit}</span>
          <button type="button" class="btn-apply-suggestion" onclick="applySuggestedConstraint('${s.param}', ${s.value})">
            + Zastosuj i Zablokuj 🔒
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.warn('Nie udało się pobrać sugerowanych ograniczeń:', err);
  }
}

function toggleConstraintsDrawer() {
  const body = document.getElementById('constraintsDrawerBody');
  const chev = document.getElementById('constraintsDrawerChevron');
  if (!body) return;
  const isHidden = body.style.display === 'none';
  body.style.display = isHidden ? 'block' : 'none';
  if (chev) chev.textContent = isHidden ? '▼' : '▲';
}

function onWingPlanformChange() {
  const select = document.getElementById('wing_planform');
  const val = select ? select.value : 'trapezoidal';
  const breakGroup = document.getElementById('group_break_span_ratio');

  if (breakGroup) {
    breakGroup.style.display = (val === 'compound_trapezoid') ? 'flex' : 'none';
  }

  renderWingPlanformDidacticCard();

  if (typeof performCalculation === 'function') {
    performCalculation();
  }
}

function renderWingPlanformDidacticCard() {
  const select = document.getElementById('wing_planform');
  const val = select ? select.value : 'trapezoidal';
  const box = document.getElementById('wingPlanformDidacticBox');
  if (!box) return;

  const info = WING_PLANFORMS_INFO[val] || WING_PLANFORMS_INFO.trapezoidal;

  box.innerHTML = `
    <div style="font-size:0.82rem; font-weight:700; color:#0f172a; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
      <span>📐 Obrys: <strong>${info.name_pl}</strong></span>
      <span class="badge badge-info" style="font-size:0.72rem;">Projekt P3 &bull; Danilecki</span>
    </div>
    <div style="font-size:0.76rem; color:#334155; line-height:1.4; margin-bottom:4px;">
      <b>Charakterystyka przeciągnięcia:</b> ${info.stall_summary}
    </div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:0.74rem; margin-top:4px;">
      <div style="background:#ecfdf5; padding:4px 6px; border-radius:4px; border:1px solid #a7f3d0; color:#065f46;">
        <b>Zalety:</b> ${info.pros}
      </div>
      <div style="background:#fef2f2; padding:4px 6px; border-radius:4px; border:1px solid #fecaca; color:#991b1b;">
        <b>Wyzwania:</b> ${info.cons}
      </div>
    </div>
    <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">
      <b>Przykłady seryjne:</b> ${info.aircraft}
    </div>
  `;
}

function navigateToStep(stepId) {
  // Oznacz aktywny węzeł na pasku
  document.querySelectorAll('.step-node').forEach(node => {
    node.classList.remove('active');
  });
  const activeNode = document.getElementById(`step_node_${stepId}`);
  if (activeNode) activeNode.classList.add('active');

  // W trybie projektów semestralnych przełącz pigułkę
  if (typeof selectSemesterProject === 'function') {
    selectSemesterProject(stepId);
  }

  // W sidebarze rozwiń odpowiedni akordeon
  const modMap = {
    p1: 'mod1',
    p2: 'mod1',
    p3: 'mod2',
    p4: 'mod3',
    p5: 'mod4',
    p6: 'mod0'
  };
  const modId = modMap[stepId];
  if (modId && typeof toggleAccordion === 'function') {
    const body = document.getElementById(`body_${modId}`);
    if (body && body.style.display === 'none') {
      toggleAccordion(modId);
    }
    const acc = document.getElementById(`accordion_${modId}`);
    if (acc) {
      acc.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }
}

// Eksport do przestrzeni globalnej window
window.toggleParamLock = toggleParamLock;
window.applySuggestedConstraint = applySuggestedConstraint;
window.updateDerivedUI = updateDerivedUI;
window.renderInitialSuggestions = renderInitialSuggestions;
window.toggleConstraintsDrawer = toggleConstraintsDrawer;
window.onWingPlanformChange = onWingPlanformChange;
window.renderWingPlanformDidacticCard = renderWingPlanformDidacticCard;
window.navigateToStep = navigateToStep;

// Inicjalizacja przy załadowaniu DOM
document.addEventListener('DOMContentLoaded', () => {
  renderInitialSuggestions();
  renderWingPlanformDidacticCard();

  const catEl = document.getElementById('category');
  if (catEl) {
    catEl.addEventListener('change', renderInitialSuggestions);
  }
  const typeEl = document.getElementById('aircraft_type');
  if (typeEl) {
    typeEl.addEventListener('change', renderInitialSuggestions);
  }
});

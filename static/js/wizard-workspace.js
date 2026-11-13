/* The wizard is a persistent workspace. Drafts never update calculated projects. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const KEY = 'bipol_wizard_drafts_v1';
  const esc = BipolStudio.escape;
  const fmt = (n, digits = 2) => BipolStudio.format(n, digits);
  let ready = false, owner = null, dirty = false, applying = false, timer, controller, previewSequence = 0;
  let polar = null, requestedPreview = '';
  const stageNames = ['Temat i założenia', 'Misja i osiągi', 'Napęd i paliwo', 'Płat i aerodynamika', 'Sprawdź i oblicz'];

  function invalidFields(step) {
    return [...$(`wizardPane${step}`).querySelectorAll('input[type="number"]')].filter(input => {
      if (input.disabled || input.readOnly) return false;
      const v = input.validity;
      return (input.required && input.value.trim() === '') || v.badInput || v.rangeUnderflow || v.rangeOverflow;
    });
  }

  function readiness() {
    const issues = [1, 2, 3, 4].map(step => ({step, fields:invalidFields(step)}));
    const valid = issues.filter(issue => !issue.fields.length).length;
    $('projectWizardBackdrop').dataset.step = currentWizardStep;
    $('wizardStageLabel').textContent = `0${currentWizardStep} / 05 · ${stageNames[currentWizardStep - 1]}`;
    $('wizardReadinessProgress').value = valid;
    $('wizardReadinessLabel').textContent = `${valid} / 4 etapy z danymi liczbowymi w zakresie`;
    issues.forEach(({step, fields}) => {
      const badge = document.querySelector(`[data-step-status="${step}"]`);
      badge.textContent = fields.length ? `Do poprawy: ${fields.length}` : 'Dane w zakresie';
      badge.classList.toggle('needs-attention', fields.length > 0);
      badge.closest('button').setAttribute('aria-label', `${stageNames[step - 1]}: ${badge.textContent}`);
    });
    const bad = issues.flatMap(({step, fields}) => fields.map(input => ({step, input})));
    const review = $('wizardReviewIssues');
    review.hidden = !bad.length;
    review.innerHTML = bad.length ? `<strong>Uzupełnij lub popraw ${bad.length} pól przed obliczeniem.</strong><ul>${bad.map(({step, input}) => {
      const label = document.querySelector(`label[for="${input.id}"]`)?.textContent.trim() || input.id;
      return `<li><button type="button" data-invalid-field="${esc(input.id)}" data-invalid-step="${step}">Etap ${step} · ${esc(label)}</button></li>`;
    }).join('')}</ul>` : '';
    $('wizardFooterHint').textContent = bad.length ? `Do poprawy: ${bad.length} pól. Przejrzyj założenia w etapie 5.` : dirty ? 'Szkic zapisany lokalnie · oblicz, aby zastosować zmiany.' : 'Możesz edytować założenia w dowolnej kolejności.';
  }

  function clearPolar(message) {
    polar = null;
    $('wizardPolarBasis').textContent = message;
    for (const id of ['wizardPolarChart', 'wizardPolarMetrics', 'wizardPolarEquations']) $(id).replaceChildren();
    $('wizardPolarProbe').hidden = true;
    $('wizardDragFlow').replaceChildren();
    if (ready) renderReview(BipolDesignBasis.snapshot());
  }

  function equation(tex) {
    return window.katex ? katex.renderToString(tex, {throwOnError:false, trust:false}) : esc(tex);
  }

  function renderPolar(p) {
    polar = p;
    const k = 1 / (Math.PI * p.aspect_ratio * p.oswald_e);
    const clOpt = Math.sqrt(p.cx0 / k);
    const clMax = Math.ceil(Math.max(2, 1.15 * clOpt) * 10) / 10;
    $('wizPolarCl').max = clMax;
    $('wizardPolarProbe').hidden = false;
    $('wizardPolarBasis').textContent = p.mode === 'input' ? 'Wejście: opór zerowy całego samolotu C_D0.' : p.mode === 'reading' ? 'Wejście: S_wet/S i własny odczyt doskonałości K_max.' : 'Wejście: S_wet/S → wykres Raymera → C_D0.';
    $('wizardPolarMetrics').innerHTML = [
      ['C_D0', fmt(p.cx0, 5), p.mode === 'input' ? 'podany przez Ciebie' : 'wynik oszacowania'],
      ['K_max', fmt(p.kmax), p.mode === 'reading' ? 'własny odczyt' : 'maks. doskonałość modelu'],
      ['k', fmt(k, 5), 'współczynnik oporu indukowanego'],
      ['C_L przy K_max', fmt(clOpt, 3), 'bez ograniczenia przeciągnięciem']
    ].map(([name, value, note]) => `<div><span>${esc(name)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></div>`).join('');
    const formulas = [
      ...(p.swet_ratio ? [String.raw`\Lambda_{wet}=\frac{\Lambda}{S_{wet}/S}=\frac{${p.aspect_ratio.toFixed(3)}}{${p.swet_ratio.toFixed(3)}}=${p.wetted_aspect_ratio.toFixed(3)}`] : []),
      String.raw`k=\frac{1}{\pi\Lambda e}=${k.toFixed(6)}`,
      String.raw`C_D=${p.cx0.toFixed(5)}+${k.toFixed(5)}\,C_L^2`,
      String.raw`K_{max}=\frac{1}{2\sqrt{kC_{D0}}}=${p.kmax.toFixed(3)}`,
      String.raw`C_{L,opt}=\sqrt{\frac{C_{D0}}{k}}=${clOpt.toFixed(3)}`
    ];
    $('wizardPolarEquations').innerHTML = formulas.map(tex => `<div>${equation(tex)}</div>`).join('');
    const flow = p.mode === 'input' ? [
      ['Podajesz', `C_D0 = ${fmt(p.cx0, 5)}`, 'współczynnik całego samolotu'],
      ['Obliczamy', `k = ${fmt(k, 5)}`, `Λ = ${fmt(p.aspect_ratio)} · e = ${fmt(p.oswald_e)}`],
      ['Otrzymujesz', `K_max = ${fmt(p.kmax)}`, 'maksymalna doskonałość modelu']
    ] : [
      ['Podajesz', `S_wet/S = ${fmt(p.swet_ratio)}`, 'cały samolot / skrzydło'],
      ['Wyznaczamy', `Λ_wet = ${fmt(p.wetted_aspect_ratio)}`, p.mode === 'reading' ? `Twój odczyt K_max = ${fmt(p.kmax)}` : `Raymer: K_max = ${fmt(p.kmax)}`],
      ['Otrzymujesz', `C_D0 = ${fmt(p.cx0, 5)}`, `Λ = ${fmt(p.aspect_ratio)} · e = ${fmt(p.oswald_e)}`]
    ];
    $('wizardDragFlow').innerHTML = flow.map(([label, value, note], i) => `<li><span>${i+1}. ${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></li>`).join('');
    renderPolarPoint();
    renderReview(BipolDesignBasis.snapshot());
  }

  function modelScope(p) {
    return p.design_iteration_mode === 'preliminary'
      ? ['Bilans P1/P2 z wybraną biegunową', 'Bilans misji korzysta z biegunowej wstępnej wyznaczonej z podanego C_D0 albo S_wet/S.']
      : ['Domknięcie P2–P4 z oporem z geometrii', 'Wybrana metoda wyznacza biegunową wstępną. W bilansie misji P2–P4 opór jest następnie uściślany z geometrii; końcowy C_D0 może różnić się od podglądu.'];
  }

  function renderReview(p) {
    const direct = p.preliminary_polar_mode === 'input';
    const geometry = {
      loading:[`Λ = ${fmt(p.aspect_ratio)}`, 'Powierzchnia i rozpiętość zostaną wyznaczone z bilansu masy i ograniczenia VS0.'],
      span_aspect:[`b = ${fmt(p.wingspan_m)} m · Λ = ${fmt(p.aspect_ratio)}`, `Zależna powierzchnia S = ${fmt(p.wing_area_m2)} m²`],
      span_area:[`b = ${fmt(p.wingspan_m)} m · S = ${fmt(p.wing_area_m2)} m²`, `Zależne wydłużenie Λ = ${fmt(p.aspect_ratio)}`],
      area_aspect:[`S = ${fmt(p.wing_area_m2)} m² · Λ = ${fmt(p.aspect_ratio)}`, `Zależna rozpiętość b = ${fmt(p.wingspan_m)} m`]
    }[p.wing_input_mode || 'loading'];
    const propulsion = p.engine_type === 'none' ? ['Bez napędu', 'Szybowiec · bez bilansu paliwa silnikowego']
      : [p.engine_type === 'jet' ? 'Napęd odrzutowy' : 'Napęd śmigłowy',
        `${p.n_engines} siln. · ${p.engine_type === 'jet' ? 'Ciąg z diagramu doboru po obliczeniu' : $('wiz_power_input_mode').selectedOptions[0].textContent}`];
    const drag = direct ? `C_D0 = ${$('wiz_cx0').value.trim() ? fmt(p.cx0, 5) : '—'}`
      : p.wetted_example === 'sketch' ? `S_wet/S = ${$('wiz_sketch_swet_ratio').value.trim() ? fmt(p.sketch_swet_ratio) : '—'}`
      : 'S_wet/S z analogii';
    const cards = [
      [1, 'Skrzydło', ...geometry],
      [2, 'Misja', `${fmt(p.range_km, 0)} km · ${fmt(p.cruise_speed_kmh, 0)} km/h`, `Wysokość przelotu ${fmt(p.cruise_altitude_m, 0)} m`],
      [3, 'Napęd', ...propulsion],
      [4, 'Aerodynamika', drag, polar ? `Biegunowa wstępna: C_D0 = ${fmt(polar.cx0, 5)} · K_max = ${fmt(polar.kmax)}` : 'Podgląd biegunowej oczekuje na poprawne dane i odpowiedź obliczeń.']
    ];
    $('wizardReviewCards').innerHTML = cards.map(([step, title, value, note]) => `<button type="button" data-review-step="${step}" aria-controls="wizardPane${step}"><span class="wizard-review-card-title">0${step} · ${esc(title)} <span aria-hidden="true">↗</span></span><strong>${esc(value)}</strong><small>${esc(note)}</small></button>`).join('');
    const [title, text] = modelScope(p);
    $('wizardModelScopeTitle').textContent = title;
    $('wizardModelScopeText').textContent = text;
    $('wizardReviewScope').textContent = `${title}. ${text}`;
  }

  const normalize = text => text.toLowerCase().replace(/ł/g, 'l').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();

  function searchable(input) {
    if (input.disabled || input.type === 'hidden') return false;
    // Inactive stages are searchable; controls hidden by the selected method are not.
    for (let el = input; el && !el.classList.contains('wizard-form'); el = el.parentElement) {
      if (el.classList.contains('wizard-pane')) continue;
      if (el.hidden || getComputedStyle(el).display === 'none') return false;
    }
    return true;
  }

  function searchFields() {
    const query = normalize($('wizardFieldSearch').value);
    const list = $('wizardSearchResults');
    $('wizardSearchClear').hidden = !query;
    list.hidden = !query;
    if (!query) { list.replaceChildren(); $('wizardSearchStatus').textContent = ''; return; }
    const terms = query.split(' ');
    const matches = [...document.querySelectorAll('.wizard-pane input[id], .wizard-pane select[id], .wizard-pane textarea[id]')].filter(searchable).map(input => {
      const label = document.querySelector(`label[for="${input.id}"]`);
      if (!label) return null;
      const title = label.cloneNode(true);
      title.querySelectorAll('.param-info-icon, .param-didactic-hint, button').forEach(el => el.remove());
      const text = title.textContent.trim();
      const keywords = normalize(`${text} ${input.id} ${input.id === 'wiz_cx0' ? 'CD0 opór zerowy' : ''}`);
      if (!terms.every(term => keywords.includes(term))) return null;
      const value = input.tagName === 'SELECT' ? input.selectedOptions[0]?.textContent : input.value;
      return {id:input.id, text, value:value || 'Nie podano', step:Number(input.closest('.wizard-pane').id.replace('wizardPane', '')), derived:input.readOnly};
    }).filter(Boolean);
    $('wizardSearchStatus').textContent = matches.length ? `Znalezione parametry: ${matches.length}. Wybierz, aby przejść do pola.` : 'Brak parametrów dla tej frazy w aktualnej konfiguracji.';
    list.innerHTML = matches.slice(0, 12).map(item => `<li><button type="button" data-search-field="${esc(item.id)}" data-search-step="${item.step}"><span>${esc(item.text)}</span><small>Etap ${item.step} · ${esc(stageNames[item.step-1])}${item.derived ? ' · wynik zależny' : ''}</small><strong>${esc(item.value)}</strong></button></li>`).join('');
    if (matches.length > 12) list.insertAdjacentHTML('beforeend', '<li class="wizard-search-more">Pokazano pierwsze 12 wyników. Doprecyzuj wyszukiwanie.</li>');
  }

  function focusField(id, step) {
    goToWizardStep(step, {focus:false});
    const input = $(id);
    for (let el = input.parentElement; el; el = el.parentElement) {
      if (el.tagName === 'DETAILS') el.open = true;
    }
    input.style.scrollMarginTop = `${(document.querySelector('.bipol-navbar')?.getBoundingClientRect().height || 0) + 30}px`;
    input.focus({preventScroll:true}); input.scrollIntoView({block:'center', behavior:'instant'});
  }

  function renderPolarPoint() {
    if (!polar) return;
    const k = 1 / (Math.PI * polar.aspect_ratio * polar.oswald_e);
    const clOpt = Math.sqrt(polar.cx0 / k), clMax = Number($('wizPolarCl').max);
    const cl = Number($('wizPolarCl').value), cd = polar.cx0 + k * cl * cl;
    const maxCd = (polar.cx0 + k * clMax * clMax) * 1.1;
    const x = n => 44 + 230 * n / maxCd, y = n => 190 - 162 * n / clMax;
    const path = Array.from({length:81}, (_, i) => {
      const lift = clMax * i / 80;
      return `${i ? 'L' : 'M'}${x(polar.cx0 + k * lift * lift).toFixed(2)},${y(lift).toFixed(2)}`;
    }).join(' ');
    const grid = Array.from({length:5}, (_, i) => {
      const lift = clMax * i / 4, drag = maxCd * i / 4;
      return `<path class="polar-grid" d="M44 ${y(lift)}H274 M${x(drag)} 28V190"/><text x="37" y="${y(lift)+4}" text-anchor="end">${esc(fmt(lift, 1))}</text><text x="${x(drag)}" y="207" text-anchor="middle">${esc(fmt(drag, 3))}</text>`;
    }).join('');
    $('wizardPolarChart').innerHTML = `<svg viewBox="0 0 300 235" role="img" aria-label="Biegunowa paraboliczna. Dla C_L = ${esc(fmt(cl))}, C_D = ${esc(fmt(cd, 5))}. Punkt maksymalnej doskonałości zaznaczono obwódką."><title>Biegunowa wstępna szkicu</title>${grid}<path class="polar-axis" d="M44 25V190H280"/><text x="20" y="16">C_L</text><text x="265" y="229">C_D</text><path class="polar-curve" d="${path}"/><circle class="polar-optimum" cx="${x(2*polar.cx0)}" cy="${y(clOpt)}" r="5"/><circle class="polar-probe" cx="${x(cd)}" cy="${y(cl)}" r="4"/></svg><div class="wizard-chart-legend"><span>● Wybrany punkt</span><span>○ Maks. doskonałość</span></div>`;
    $('wizPolarClValue').textContent = fmt(cl);
    $('wizardPolarPoint').textContent = `C_D = ${fmt(cd, 5)} · K = C_L/C_D = ${fmt(cl / cd)}`;
  }

  function started() {
    ready = true; owner = getActiveProjectId(); dirty = false;
    requestedPreview = '';
    $('wizardFieldSearch').value = ''; searchFields();
    $('wizardDraftStatus').textContent = 'Szkic gotowy do edycji';
    refresh();
  }

  function syncRecalculate() {
    if (!ready || !$('tab-wizard').classList.contains('active')) return;
    if ($('wizRestoreSaved')) $('wizRestoreSaved').hidden = !dirty;
    const pill = $('navRecalcPill');
    pill.classList.toggle('synced', !dirty); pill.classList.toggle('stale', dirty);
    pill.innerHTML = `<span>${dirty ? 'Oblicz szkic' : 'Oblicz projekt'}</span> <kbd>Ctrl+Enter</kbd>`;
    pill.title = 'Oblicz i zapisz założenia z kreatora (Ctrl+Enter).';
  }

  function persist() {
    if (!ready || !dirty) return;
    const fields = {};
    $('projectWizardBackdrop').querySelectorAll('input[id], select[id], textarea[id]').forEach(el => {
      if (el.id.startsWith('wiz_')) fields[el.id] = el.type === 'checkbox' ? el.checked : el.value;
    });
    const drafts = projectStore.read(KEY, {});
    const safe = drafts && typeof drafts === 'object' && !Array.isArray(drafts) ? drafts : {};
    safe[owner] = {schema:1, mode:wizardProjectMode, step:currentWizardStep,
      params:BipolDesignBasis.snapshot(), fields};
    const saved = projectStore.write(KEY, safe);
    $('wizardDraftStatus').textContent = saved ? 'Szkic zapisany w tej przeglądarce' : 'Szkic zachowany w tej karcie — zapis przeglądarki niedostępny';
  }

  function ensure() {
    const id = getActiveProjectId();
    if (ready && owner === id) return;
    const draft = projectStore.read(KEY, {})?.[id];
    // Set readiness before navigation to avoid re-entering through the tab event.
    ready = true; owner = id;
    openWizard('edit');
    if (draft?.schema === 1 && draft.params && typeof draft.params === 'object') {
      wizardProjectMode = draft.mode === 'create' ? 'create' : 'edit';
      BipolDesignBasis.seed(draft.params);
      for (const [key, value] of Object.entries(draft.fields || {})) {
        const el = $(key); if (!key.startsWith('wiz_') || !el?.closest('#projectWizardBackdrop')) continue;
        if (el.type === 'checkbox') el.checked = Boolean(value); else el.value = String(value ?? '');
      }
      BipolDesignBasis.sync('wiz_');
      $('wizardWorkspaceTitle').textContent = wizardProjectMode === 'create' ? 'Nowy projekt' : 'Kreator projektu';
      dirty = true;
      goToWizardStep(Math.max(1, Math.min(5, Number(draft.step) || 1)), {focus:false});
      $('wizardDraftStatus').textContent = 'Przywrócono niezastosowany szkic';
    }
    refresh();
  }

  function refresh() {
    if (!ready) return;
    syncRecalculate();
    const p = BipolDesignBasis.snapshot();
    readiness();
    $('wizardDraftName').textContent = p.name;
    const direct = p.preliminary_polar_mode === 'input';
    $('wizardDragShortcutValue').textContent = direct ? `C_D0 = ${$('wiz_cx0').value.trim() ? fmt(p.cx0, 5) : '—'}` : p.wetted_example === 'sketch' ? `S_wet/S = ${$('wiz_sketch_swet_ratio').value.trim() ? fmt(p.sketch_swet_ratio) : '—'}` : 'Stosunek S_wet/S';
    document.querySelectorAll('[data-wizard-start]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.wizardStart === (direct ? 'input' : 'raymer'))));
    $('wizEnterOwnRatio').hidden = p.wetted_example === 'sketch';
    $('wizardLiveSummary').innerHTML = [
      ['Misja', `${p.range_km} km · ${p.cruise_speed_kmh} km/h`],
      ['Załoga i pasażerowie', `${Number(p.n_crew) + Number(p.n_pax)} os.`],
      ['Wydłużenie skrzydła', fmt(p.aspect_ratio)],
      ['Podstawa oporu', $('wizardDragShortcutValue').textContent]
    ].map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('');
    renderReview(p);
    if ($('wizardFieldSearch').value) searchFields();
    const signature = JSON.stringify(p);
    if (signature === requestedPreview) return;
    requestedPreview = signature;
    controller?.abort(); clearTimeout(timer);
    const sequence = ++previewSequence;
    const invalidPolar = ['wiz_aspect_ratio', 'wiz_oswald_e', 'wiz_cx0', 'wiz_sketch_swet_ratio', 'wiz_raymer_kmax'].some(id => {
      const input = $(id);
      if (input.disabled) return false;
      return input.value.trim() === '' || !Number.isFinite(Number(input.value)) || input.validity.rangeUnderflow || input.validity.rangeOverflow || Number(input.value) <= 0;
    });
    if (invalidPolar) {
      clearPolar('Uzupełnij poprawne dane biegunowej.');
      $('wizardPolarPreview').textContent = 'Sprawdź wydłużenie, współczynnik e i dane wybranej metody oporu.';
      return;
    }
    clearPolar('Aktualizowanie podglądu…');
    $('wizardPolarPreview').textContent = 'Przeliczanie biegunowej wstępnej…';
    timer = setTimeout(() => preview(p, sequence), 250);
  }

  async function preview(params, sequence) {
    controller = new AbortController();
    try {
      const response = await fetch('/api/preliminary-polar', {method:'POST',
        headers:{'Content-Type':'application/json'}, body:JSON.stringify(params), signal:controller.signal});
      const data = await response.json();
      if (sequence !== previewSequence) return;
      if (!response.ok) throw Error(data.message || 'Sprawdź założenia biegunowej.');
      const p = data.polar;
      renderPolar(p);
      const route = p.mode === 'input'
        ? `Podany C_D0 = ${fmt(p.cx0, 5)} → K_max = ½√(πΛe/C_D0) = ${fmt(p.kmax)}`
        : `S_wet/S = ${fmt(p.swet_ratio)} → Λ_wet = ${fmt(p.wetted_aspect_ratio)} → ${p.mode === 'reading' ? 'własny odczyt ' : ''}K_max = ${fmt(p.kmax)} → C_D0 = πΛe/(4K_max²) = ${fmt(p.cx0, 5)}`;
      const check = p.cx0_in_range ? 'W przedziale typowym dla wybranej klasy.' : 'Poza przedziałem typowym — sprawdź i uzasadnij przyjętą wartość.';
      $('wizardPolarPreview').innerHTML = `<strong>${esc(route)}</strong><p>C_D = C_D0 + C_L²/(πΛe). ${esc(check)}${p.extrapolated ? ' Odczyt Raymera poza zakresem narysowanej krzywej — ekstrapolacja do potwierdzenia.' : ''}</p>`;
    } catch (error) {
      if (error.name !== 'AbortError' && sequence === previewSequence) {
        clearPolar(error.message);
        $('wizardPolarPreview').textContent = error.message;
        requestedPreview = '';
      }
    }
  }

  function stepChanged() {
    document.querySelectorAll('.wizard-step-tab').forEach(tab => {
      tab.setAttribute('aria-controls', `wizardPane${tab.dataset.step}`);
    });
    refresh(); persist();
  }

  function suspend() {
    persist(); controller?.abort(); clearTimeout(timer); previewSequence++;
    requestedPreview = '';
  }

  function committed() {
    const drafts = projectStore.read(KEY, {});
    if (drafts && typeof drafts === 'object') { delete drafts[owner]; projectStore.write(KEY, drafts); }
    dirty = false; ready = false; owner = null;
  }

  window.BipolWizardWorkspace = {ensure, started, stepChanged, suspend, committed,
    beginApply:() => { applying = true; }, endApply:() => { applying = false; }};
  document.addEventListener('DOMContentLoaded', () => {
    const root = $('projectWizardBackdrop');
    const changed = event => {
      if (!ready || !event.target.matches('input, select, textarea') || event.target.closest('.wizard-tools, .wizard-trend-chart-box') || event.target.id === 'wizPolarCl') return;
      dirty = true; showWizardError(''); refresh(); persist();
    };
    root.addEventListener('input', changed); root.addEventListener('change', changed);
    $('wizardFieldSearch').addEventListener('input', searchFields);
    const clearSearch = () => { $('wizardFieldSearch').value = ''; searchFields(); $('wizardFieldSearch').focus(); };
    $('wizardSearchClear').addEventListener('click', clearSearch);
    root.querySelector('.wizard-field-search').addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); clearSearch(); return; }
      if (!['ArrowDown', 'ArrowUp'].includes(event.key)) return;
      const buttons = [...$('wizardSearchResults').querySelectorAll('button')];
      if (!buttons.length) return;
      const index = buttons.indexOf(document.activeElement);
      const next = index < 0 ? (event.key === 'ArrowDown' ? 0 : buttons.length-1)
        : (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length)%buttons.length;
      event.preventDefault(); buttons[next].focus();
    });
    $('wizardSearchResults').addEventListener('click', event => {
      const button = event.target.closest('[data-search-field]');
      if (!button) return;
      const {searchField, searchStep} = button.dataset;
      $('wizardFieldSearch').value = ''; searchFields();
      focusField(searchField, Number(searchStep));
    });
    $('wizardDragShortcut').addEventListener('click', () => {
      goToWizardStep(4);
      const input = document.querySelector('[name="wiz_drag_basis"]:checked');
      input.focus({preventScroll:true});
    });
    root.querySelectorAll('[data-wizard-start]').forEach(button => button.addEventListener('click', () => {
      const mode = button.dataset.wizardStart;
      if (mode === 'raymer') $('wiz_wetted_example').value = 'sketch';
      const input = root.querySelector(`[name="wiz_drag_basis"][value="${mode}"]`);
      input.checked = true;
      input.dispatchEvent(new Event('change', {bubbles:true}));
      focusField(mode === 'input' ? 'wiz_cx0' : 'wiz_sketch_swet_ratio', 4);
    }));
    $('wizardReviewCards').addEventListener('click', event => {
      const button = event.target.closest('[data-review-step]');
      if (button) goToWizardStep(Number(button.dataset.reviewStep));
    });
    $('wizardEditMissionModel').addEventListener('click', () => focusField('wiz_design_iteration_mode', 1));
    $('wizEnterOwnRatio').addEventListener('click', () => {
      $('wiz_wetted_example').value = 'sketch';
      $('wiz_wetted_example').dispatchEvent(new Event('change', {bubbles:true}));
      focusField('wiz_sketch_swet_ratio', 4);
    });
    $('wizPolarCl').addEventListener('input', renderPolarPoint);
    $('wizReviewBtn').addEventListener('click', () => goToWizardStep(5));
    $('wizardReviewIssues').addEventListener('click', event => {
      const button = event.target.closest('[data-invalid-field]');
      if (!button) return;
      goToWizardStep(Number(button.dataset.invalidStep));
      const input = $(button.dataset.invalidField);
      input.style.scrollMarginTop = `${(document.querySelector('.bipol-navbar')?.getBoundingClientRect().height || 0) + 30}px`;
      input.focus({preventScroll:true}); input.scrollIntoView({block:'center'});
    });
    // Keep the plot beside the form on large displays, beside its inputs on phones.
    const wide = window.matchMedia('(min-width:1400px)');
    const insights = root.querySelector('.wizard-insight-panel');
    const positionInsights = () => {
      if (wide.matches) root.querySelector('.wizard-body').append(insights);
      else $('wizardPolarPreview').after(insights);
    };
    wide.addEventListener('change', positionInsights); positionInsights();
    $('wizRestoreSaved')?.addEventListener('click', () => { committed(); ensure(); });
    $('wizExplanationToggle').addEventListener('click', event => {
      const show = $('tab-wizard').dataset.explanations !== 'true';
      $('tab-wizard').dataset.explanations = String(show);
      event.currentTarget.setAttribute('aria-pressed', String(show));
      event.currentTarget.textContent = show ? 'Ukryj objaśnienia' : 'Pokaż objaśnienia';
    });
    document.addEventListener('bipol:results', () => {
      // Other tabs can refine the same project. Refresh an untouched wizard;
      // retain an unapplied draft independently from newly calculated results.
      if (ready && !dirty && !applying) {
        const step = currentWizardStep;
        ready = false;
        if ($('tab-wizard').classList.contains('active')) { ensure(); goToWizardStep(step, {focus:false}); }
      }
      queueMicrotask(syncRecalculate);
    });
    document.addEventListener('bipol:tab', () => {
      syncRecalculate();
      if (ready && $('tab-wizard').classList.contains('active')) refresh();
    });
    document.addEventListener('bipol:project', () => {
      if (applying) return;
      if (ready && owner !== getActiveProjectId()) {
        suspend(); ready = false;
        if ($('tab-wizard').classList.contains('active')) ensure();
      }
    });
    window.addEventListener('pagehide', persist);
  });
})();

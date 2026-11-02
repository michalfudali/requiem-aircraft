/**
 * BiPOL Requiem — tryb „sterowanie ręczne” (niezależny od trybu dydaktycznego i konstrukcyjnego).
 *
 * W tym trybie żadna wartość domyślna nie trafia do obliczeń bez udziału użytkownika:
 *  - kreator nie wypełnia pól — pokazuje sugestię jako podpowiedź i nie pozwala przejść dalej,
 *    dopóki użytkownik nie wpisze danych bieżącego kroku;
 *  - po obliczeniu serwer zwraca dane domyślne bieżącego projektu (P1 → P6); okno akceptacji
 *    wymaga wpisania każdej z nich, a raport jest zablokowany do czasu wpisania wszystkich.
 * Wartości wpisane przez użytkownika (pola formularza i okno akceptacji) są zapisywane
 * w przeglądarce osobno dla każdego projektu i wysyłane z parametrami jako `manual_control`.
 */
(function () {
  'use strict';
  const MODE_KEY = 'bipol_manual_control';
  const STATE_KEY = 'bipol_manual_control_state_v1';
  const AUTHOR_FIELDS = new Set(['wiz_name', 'wiz_student_name', 'wiz_album_no', 'wiz_group_no', 'wiz_supervisor']);
  let enabled = false;
  let lastState = null;
  // Pola kreatora potwierdzone przez użytkownika w bieżącym otwarciu (po identyfikatorze — kreator przebudowuje pola).
  const confirmed = new Set();

  const escapeHtml = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const format = (value, digits) => (typeof value === 'number' && Number.isFinite(value))
    ? value.toFixed(Math.max(0, Math.min(6, digits ?? 2))).replace('.', ',') : '—';
  const parse = text => {
    const cleaned = String(text ?? '').trim().replace(/\s/g, '').replace(',', '.');
    if (!cleaned) return null;
    const value = Number(cleaned);
    return Number.isFinite(value) ? value : null;
  };

  function projectId() {
    try { return (typeof getActiveProjectId === 'function' && getActiveProjectId()) || 'default'; } catch (_) { return 'default'; }
  }
  function readAll() {
    try { return JSON.parse(localStorage.getItem(STATE_KEY) || '{}') || {}; } catch (_) { return {}; }
  }
  function own() {
    const all = readAll(), id = projectId();
    const state = all[id] && typeof all[id] === 'object' ? all[id] : {typed: [], accepted: {}};
    state.typed = Array.isArray(state.typed) ? state.typed : [];
    state.accepted = state.accepted && typeof state.accepted === 'object' ? state.accepted : {};
    return {all, id, state};
  }
  function persist(mutate) {
    const {all, id, state} = own();
    mutate(state);
    all[id] = state;
    try { localStorage.setItem(STATE_KEY, JSON.stringify(all)); } catch (_) { /* tryb prywatny: stan w bieżącej karcie */ }
  }
  function markTyped(param) {
    if (!param) return;
    persist(state => { if (!state.typed.includes(param)) state.typed.push(param); });
  }

  // --- wartości wpisane przez użytkownika ---
  function onUserEdit(event) {
    if (!enabled || !event.isTrusted) return;
    const el = event.target;
    if (!el || !el.id || !el.matches('input, select, textarea') || el.closest('#manualControlGate')) return;
    if (el.type === 'checkbox' || el.type === 'button') return;
    el.classList.remove('mc-needs-input');
    if (String(el.value).trim() === '') return;
    confirmed.add(el.id);
    markTyped(el.id.startsWith('wiz_') ? el.id.slice(4) : el.id);
  }
  document.addEventListener('input', onUserEdit, true);
  document.addEventListener('change', onUserEdit, true);

  // --- parametry wysyłane do obliczeń ---
  function wrapCollect() {
    if (typeof window.collectFormData !== 'function' || window.collectFormData.__manualControl) return;
    const original = window.collectFormData;
    const wrapped = function () {
      const data = original.apply(this, arguments);
      if (enabled) {
        const {state} = own();
        data.manual_control = {enabled: true, typed: state.typed.slice(), accepted: {...state.accepted}};
      } else {
        delete data.manual_control;
      }
      return data;
    };
    wrapped.__manualControl = true;
    window.collectFormData = wrapped;
  }

  function recalculate() {
    if (typeof window.performCalculation === 'function') window.performCalculation();
  }

  // --- okno akceptacji danych bieżącego projektu ---
  function gateElement() {
    let gate = document.getElementById('manualControlGate');
    if (!gate) {
      gate = document.createElement('div');
      gate.id = 'manualControlGate';
      gate.className = 'mc-backdrop';
      gate.setAttribute('role', 'dialog');
      gate.setAttribute('aria-modal', 'true');
      gate.setAttribute('aria-labelledby', 'mcTitle');
      gate.hidden = true;
      document.body.appendChild(gate);
    }
    return gate;
  }

  function hideGate() {
    const gate = document.getElementById('manualControlGate');
    if (gate) gate.hidden = true;
    document.body.classList.remove('mc-gate-open');
  }

  function showGate(state) {
    const gate = gateElement();
    const points = [...(state.conflicts || []), ...(state.pending || [])];
    const step = state.stage ? state.stage.slice(1) : '—';
    gate.innerHTML = `<form class="mc-modal" novalidate>
      <p class="mc-eyebrow">Sterowanie ręczne · projekt ${escapeHtml(step)} z 6</p>
      <h2 id="mcTitle">${escapeHtml(state.stage_title || 'Dane domyślne')}</h2>
      <p class="mc-lead">Wpisz wartości danych przyjmowanych w tym projekcie. Sugestia i jej uzasadnienie są tylko podpowiedzią.
        Dalsze obliczenia i raport odblokują się po wpisaniu wszystkich pól. Wpisano ${state.accepted} z ${state.total} danych.</p>
      <div class="mc-list">${points.map((point, index) => `
        <div class="mc-row${point.message ? ' mc-conflict' : ''}">
          <label class="mc-label" for="mcInput${index}">${escapeHtml(point.label)}<small>${escapeHtml(point.section)}</small></label>
          <div class="mc-field">
            <input id="mcInput${index}" data-key="${escapeHtml(point.key)}" data-index="${index}" inputmode="decimal" autocomplete="off"
              placeholder="sugestia: ${escapeHtml(format(point.suggested, point.digits))}" aria-describedby="mcOrigin${index}">
            <span class="mc-unit">${escapeHtml(point.unit || '')}</span>
          </div>
          <p class="mc-origin" id="mcOrigin${index}">${escapeHtml(point.origin)}${point.editable ? '' : ' Wartość wynika z przyjętej metody obliczeń.'}</p>
          ${point.message ? `<p class="mc-error" role="alert">Wpisano ${escapeHtml(format(point.entered, point.digits))}. ${escapeHtml(point.message)}</p>` : ''}
        </div>`).join('')}
      </div>
      <p class="mc-status" role="status" aria-live="polite"></p>
      <div class="mc-actions">
        <button type="button" class="btn btn-outline" data-mc-off>Wyłącz sterowanie ręczne</button>
        <button type="submit" class="btn btn-primary" data-mc-submit disabled>Zatwierdź i przelicz</button>
      </div>
    </form>`;
    const form = gate.querySelector('form');
    const inputs = [...form.querySelectorAll('input[data-key]')];
    const submit = form.querySelector('[data-mc-submit]');
    const status = form.querySelector('.mc-status');
    const refresh = () => {
      const missing = inputs.filter(input => parse(input.value) === null);
      inputs.forEach(input => input.classList.toggle('mc-invalid', input.value.trim() !== '' && parse(input.value) === null));
      submit.disabled = missing.length > 0;
      status.textContent = missing.length ? `Pozostało do wpisania: ${missing.length}.` : 'Wszystkie pola tego projektu są wypełnione.';
    };
    form.addEventListener('input', refresh);
    form.querySelector('[data-mc-off]').addEventListener('click', () => setEnabled(false));
    form.addEventListener('submit', event => {
      event.preventDefault();
      refresh();
      if (submit.disabled) return;
      const values = {};
      inputs.forEach(input => {
        const point = points[Number(input.dataset.index)];
        const value = parse(input.value);
        values[point.key] = value;
        // Wartość parametru projektu trafia też do formularza, aby był zgodny z obliczeniami.
        const field = point.editable && point.key !== 'P' ? document.getElementById(point.param) : null;
        if (field && field.matches('input')) {
          const previous = field.value;
          field.value = String(+(value * (point.scale || 1)).toPrecision(12));
          // Pole z ograniczeniem (krok, zakres) zachowuje poprzednią wartość; obliczenia i tak przyjmą wpis z okna.
          if (field.checkValidity()) markTyped(point.param); else field.value = previous;
        }
      });
      persist(state => Object.assign(state.accepted, values));
      hideGate();
      recalculate();
    });
    refresh();
    gate.hidden = false;
    document.body.classList.add('mc-gate-open');
    (inputs[0] || submit).focus();
  }

  // --- pasek stanu ---
  function updateBanner(state) {
    let banner = document.getElementById('manualControlBanner');
    if (!enabled) { banner?.remove(); return; }
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'manualControlBanner';
      banner.className = 'mc-banner';
      banner.setAttribute('role', 'status');
      document.body.appendChild(banner);
    }
    if (!state) {
      banner.innerHTML = '<span>✋ Sterowanie ręczne włączone — oblicz projekt, aby zobaczyć dane do wpisania.</span>';
      return;
    }
    if (!state.remaining) {
      banner.innerHTML = `<span>✋ Sterowanie ręczne: wszystkie dane (${state.total}) wpisane przez użytkownika.</span>`;
      return;
    }
    banner.innerHTML = `<span>✋ Sterowanie ręczne: pozostało ${state.remaining} danych — ${escapeHtml(state.stage_title)}.</span>
      <button type="button" class="btn btn-primary btn-sm" data-mc-open>Wpisz dane</button>`;
    banner.querySelector('[data-mc-open]').addEventListener('click', () => lastState && showGate(lastState));
  }

  document.addEventListener('bipol:results', event => {
    if (!enabled) return;
    lastState = event.detail && event.detail.manual_control || null;
    updateBanner(lastState);
    if (lastState && (lastState.pending.length || lastState.conflicts.length)) showGate(lastState);
    else hideGate();
  });

  // --- kreator: dane początkowe wpisuje użytkownik ---
  function suggestion(el) {
    if (el.tagName === 'SELECT') {
      const chosen = [...el.options].find(option => option.value === el.value && option.value !== '');
      return chosen ? chosen.textContent.trim() : '';
    }
    return String(el.value).trim().replace('.', ',');
  }

  function clearField(el) {
    const hint = suggestion(el);
    if (el.tagName === 'SELECT') {
      let empty = [...el.options].find(option => option.value === '' && option.dataset.mcEmpty);
      if (!empty) {
        empty = document.createElement('option');
        empty.value = '';
        empty.dataset.mcEmpty = '1';
        el.insertBefore(empty, el.firstChild);
      }
      if (hint) empty.textContent = `— wybierz (sugestia: ${hint}) —`;
      else if (!empty.textContent) empty.textContent = '— wybierz —';
      el.value = '';
    } else {
      if (hint) el.placeholder = `sugestia: ${hint}`;
      el.value = '';
    }
    el.classList.add('mc-needs-input');
  }

  // Pola kreatora nie są wypełniane za użytkownika. Wartość wstawiona przez kreator (np. przy
  // zmianie kroku) staje się sugestią, dopóki użytkownik sam nie wpisze lub nie wybierze danej.
  function prepareWizard() {
    if (!enabled) return;
    const {state} = own();
    document.querySelectorAll('#projectWizardBackdrop .wizard-pane input, #projectWizardBackdrop .wizard-pane select').forEach(el => {
      if (!el.id || AUTHOR_FIELDS.has(el.id) || el.type === 'checkbox' || el.type === 'hidden'
          || el.type === 'button' || el.disabled || el.readOnly || el.closest('.wizard-trend-chart-box') || confirmed.has(el.id)) return;
      if (!el.dataset.mcCleared && state.typed.includes(el.id.startsWith('wiz_') ? el.id.slice(4) : el.id)) return;
      if (!el.dataset.mcCleared || String(el.value).trim() !== '') clearField(el);
      el.dataset.mcCleared = '1';
    });
  }

  function guardWizard(event) {
    if (!enabled) return;
    prepareWizard();
    const pane = document.querySelector('#projectWizardBackdrop .wizard-pane.active');
    if (!pane) return;
    const missing = [...pane.querySelectorAll('[data-mc-cleared]')]
      .filter(el => el.offsetParent !== null && !el.disabled && !el.readOnly && !confirmed.has(el.id));
    if (!missing.length) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    missing.forEach(el => el.classList.add('mc-needs-input'));
    const message = `Tryb sterowania ręcznego: wpisz wszystkie dane tego kroku (brakuje ${missing.length}). Sugestie w polach są tylko podpowiedzią.`;
    if (typeof window.showWizardError === 'function') window.showWizardError(message);
    missing[0].focus();
  }

  function watchWizard() {
    const backdrop = document.getElementById('projectWizardBackdrop');
    if (!backdrop) return;
    const later = () => setTimeout(prepareWizard, 0);
    new MutationObserver(() => {
      if (backdrop.classList.contains('active')) later();
      else {
        confirmed.clear();
        backdrop.querySelectorAll('[data-mc-cleared]').forEach(el => { delete el.dataset.mcCleared; });
      }
    }).observe(backdrop, {attributes: true, attributeFilter: ['class']});
    backdrop.querySelectorAll('.wizard-pane').forEach(pane =>
      new MutationObserver(() => { if (pane.classList.contains('active') && backdrop.classList.contains('active')) later(); })
        .observe(pane, {attributes: true, attributeFilter: ['class']}));
    ['wizNextBtn', 'wizFinishBtn'].forEach(id => document.getElementById(id)?.addEventListener('click', guardWizard, true));
    // Po zmianie (np. rodzaju napędu) kreator przebudowuje pola i wstawia wartości domyślne — zamień je na sugestie.
    backdrop.addEventListener('change', () => { if (enabled && backdrop.classList.contains('active')) later(); });
  }

  // --- przełącznik trybu ---
  function setEnabled(value) {
    enabled = Boolean(value);
    document.body.classList.toggle('mode-manual-control', enabled);
    document.querySelectorAll('[data-manual-control]').forEach(button => {
      button.classList.toggle('active', enabled);
      button.setAttribute('aria-pressed', String(enabled));
    });
    try { localStorage.setItem(MODE_KEY, enabled ? '1' : '0'); } catch (_) { /* bez zapisu */ }
    if (!enabled) { hideGate(); lastState = null; }
    updateBanner(null);
    recalculate();
  }
  window.BipolManualControl = {setEnabled, isEnabled: () => enabled};

  function injectSwitch() {
    const bar = document.querySelector('.project-bar-right');
    if (!bar || bar.querySelector('[data-manual-control]')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'manual-control-switch';
    button.dataset.manualControl = '1';
    button.setAttribute('aria-pressed', 'false');
    button.title = 'Każdą wartość domyślną w obliczeniach wpisujesz sam; sugestie są tylko podpowiedzią. Kolejne projekty odblokowują się po wpisaniu danych poprzednich.';
    button.textContent = '✋ Sterowanie ręczne';
    button.addEventListener('click', () => setEnabled(!enabled));
    bar.insertBefore(button, bar.firstChild);
  }

  document.addEventListener('DOMContentLoaded', () => {
    wrapCollect();
    injectSwitch();
    watchWizard();
    let saved = null;
    try { saved = localStorage.getItem(MODE_KEY); } catch (_) { /* brak zapisu */ }
    enabled = saved === '1';
    document.body.classList.toggle('mode-manual-control', enabled);
    document.querySelectorAll('[data-manual-control]').forEach(button => {
      button.classList.toggle('active', enabled);
      button.setAttribute('aria-pressed', String(enabled));
    });
    if (enabled) updateBanner(null);
  });
})();

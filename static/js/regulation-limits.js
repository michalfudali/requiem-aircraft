/* Ograniczenia kreatora i formularza wynikające z przepisów wybranej kategorii.
   Katalog (window.BIPOL_REGULATIONS) pochodzi z calculations.polish_law.catalog_for_frontend():
   limity pól z paragrafami wyjątków z przepisów oraz elementy istniejące w danej klasie płatowca. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const catalog = () => window.BIPOL_REGULATIONS || {subcategories: {}, defaults: {}};
  const esc = text => String(text ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const LIMITED = ['n_pax', 'n_crew', 'm_crew_person', 'm_pax', 'v_stall_kmh', 'n_engines', 'engine_type', 'climb_rate_ms',
    'takeoff_distance_m'];

  function subcategory(prefix = '') {
    return catalog().subcategories[$(prefix + 'category')?.value] || null;
  }

  function features(prefix = '') {
    const sub = subcategory(prefix);
    const aircraft = $(prefix + 'aircraft_type')?.value || 'piston_ga';
    const all = sub?.features || {};
    return all[aircraft] || Object.values(all)[0] || null;
  }

  function defaultCategory(aircraftType) {
    return catalog().defaults?.[aircraftType] || 'jar23_normal';
  }

  function container(input) {
    return input?.closest('.input-group') || input?.parentElement;
  }

  function setVisible(input, visible) {
    const box = container(input);
    if (!box) return;
    box.hidden = !visible;
    box.style.display = visible ? '' : 'none';
  }

  function baseBound(input, name) {
    const key = 'regBase' + name;
    if (!(key in input.dataset)) input.dataset[key] = input.getAttribute(name.toLowerCase()) ?? '';
    return input.dataset[key];
  }

  function hint(prefix, input, limit, violated) {
    const box = container(input);
    if (!box) return;
    const node = document.createElement('p');
    node.className = 'param-didactic-hint regulation-hint' + (violated ? ' is-violated' : '');
    node.dataset.regHint = prefix;
    const link = limit.paragraph ? (limit.url ? `<a href="${esc(limit.url)}" target="_blank" rel="noopener">${esc(limit.paragraph)}</a>` : esc(limit.paragraph))
      : 'Założenie programu';
    node.innerHTML = limit.paragraph ? `${violated ? '⚠ ' : ''}Przepisy: ${link} — ${esc(limit.text || '')}`
      : `${violated ? '⚠ ' : ''}Założenie programu: ${esc(limit.text || '')}`;
    box.appendChild(node);
  }

  function applyLimits(prefix, sub) {
    document.querySelectorAll(`[data-reg-hint="${prefix}"]`).forEach(node => node.remove());
    const engines = Number($(prefix + 'n_engines')?.value || 1);
    for (const key of LIMITED) {
      const input = $(prefix + key);
      if (!input) continue;
      const configured = sub.limits?.[key];
      const occupants = Math.max(1, Number($(prefix + 'n_crew')?.value || 0) + Number($(prefix + 'n_pax')?.value || 0));
      const limit = configured?.min_by_occupants
        ? {...configured, min:configured.min_by_occupants[String(occupants)] ?? configured.min}
        : configured;
      if (input.tagName === 'SELECT') {
        for (const option of input.options) option.disabled = !!(limit?.allowed && !limit.allowed.includes(option.value));
        if (limit?.allowed && !limit.allowed.includes(input.value)) {
          input.value = limit.allowed[0];
          input.dispatchEvent(new Event('change', {bubbles: true}));
        }
        if (limit) hint(prefix, input, limit, false);
        continue;
      }
      const min = baseBound(input, 'Min'), max = baseBound(input, 'Max');
      input.min = min;
      input.max = max;
      if (!limit || (limit.single_engine_only && engines !== 1)) continue;
      if (limit.min != null) input.min = String(Math.max(Number(min || -Infinity), limit.min));
      if (limit.max != null) input.max = String(Math.min(Number(max || Infinity), limit.max));
      const value = Number(input.value);
      const violated = Number.isFinite(value) && input.value !== ''
        && ((limit.min != null && value < limit.min - 1e-9) || (limit.max != null && value > limit.max + 1e-9));
      input.classList.toggle('regulation-violation', violated);
      hint(prefix, input, limit, violated);
    }
  }

  function applyFeatures(prefix, f) {
    if (!f) return;
    const cargo = $(prefix + 'm_cargo');
    if (cargo) {
      setVisible(cargo, f.cargo);
      if (!f.cargo && Number(cargo.value) !== 0) {
        cargo.value = '0';
        cargo.dispatchEvent(new Event('input', {bubbles: true}));
      }
      const label = $(prefix ? 'label_wiz_m_cargo' : 'label_m_cargo_text');
      if (label && f.cargo) {
        const text = f.cargo_label === 'wyposażenie zadaniowe' ? 'Wyposażenie zadaniowe [kg]' : 'Ładunek handlowy [kg]';
        if (prefix) label.textContent = text + ':'; else if (label.firstChild) label.firstChild.textContent = text + ' ';
      }
    }
    // Ładownia istnieje tylko w płatowcu transportowym z ładunkiem.
    document.querySelectorAll(`[data-cargo-scope="${prefix}"]`).forEach(node => {
      node.hidden = !(f.cargo_bay && Number($(prefix + 'm_cargo')?.value || 0) > 0);
    });
    const mode = $(prefix + 'payload_input_mode');
    if (mode) {
      const total = mode.querySelector('option[value="total"]');
      if (total) { total.disabled = !f.payload_total_mode; total.hidden = !f.payload_total_mode; }
      if (!f.payload_total_mode && mode.value === 'total') {
        mode.value = 'seats';
        mode.dispatchEvent(new Event('change', {bubbles: true}));
      }
      setVisible(mode, f.payload_total_mode);
    }
    const surface = $(prefix + 'operating_surface');
    if (surface) {
      const water = surface.querySelector('option[value="water"]');
      if (water) { water.disabled = !f.water; water.hidden = !f.water; }
      if (!f.water && surface.value === 'water') {
        surface.value = 'land';
        surface.dispatchEvent(new Event('change', {bubbles: true}));
      }
    }
    const pax = $(prefix + 'n_pax');
    if (pax) setVisible(pax, f.passengers);
    const paxMass = $(prefix + 'm_pax');
    if (paxMass) {
      paxMass.disabled = !f.passengers || Number(pax?.value || 0) <= 0;
      setVisible(paxMass, !paxMass.disabled);
      const label = paxMass.closest('.input-group')?.querySelector('label');
      if (label && prefix) label.textContent = f.parachute ? 'Masa drugiej osoby ze spadochronem [kg]:' : 'Masa 1 osoby z bagażem [kg]:';
    }
  }

  function apply(prefix = '') {
    const sub = subcategory(prefix);
    if (!sub) return;
    const scope = $(prefix + 'category_scope');
    if (scope) {
      scope.innerHTML = sub.scope_paragraph
        ? `Zakres stosowania: ${sub.scope_url ? `<a href="${esc(sub.scope_url)}" target="_blank" rel="noopener">${esc(sub.scope_paragraph)}</a>` : esc(sub.scope_paragraph)} — ${esc(sub.scope_text)}`
        : '';
    }
    applyLimits(prefix, sub);
    applyFeatures(prefix, features(prefix));
  }

  document.addEventListener('input', event => {
    const id = event.target?.id || '';
    const prefix = id.startsWith('wiz_') ? 'wiz_' : '';
    const key = id.slice(prefix.length);
    if (LIMITED.includes(key) || key === 'm_cargo') apply(prefix);
  });
  document.addEventListener('change', event => {
    const id = event.target?.id || '';
    const prefix = id.startsWith('wiz_') ? 'wiz_' : '';
    if (['category', 'aircraft_type', 'engine_type', 'n_engines'].includes(id.slice(prefix.length))) apply(prefix);
  });
  document.addEventListener('DOMContentLoaded', () => { apply(''); apply('wiz_'); });

  window.BipolRegulations = {apply, features, subcategory, defaultCategory};
})();

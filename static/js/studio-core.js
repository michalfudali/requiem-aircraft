/* Wspólne narzędzia pracowni: bez zależności od DOM, także do testów Node. */
(function (root) {
  'use strict';
  const metrics = [
    ['mtow', 'Masa startowa', 'kg', r => r.mass.m0, 1],
    ['area', 'Powierzchnia skrzydła', 'm²', r => r.geometry.wing.S, 2],
    ['span', 'Rozpiętość', 'm', r => r.geometry.wing.b, 2],
    ['aspect', 'Wydłużenie', '−', r => r.geometry.wing.AR, 2],
    ['fuel', 'Masa paliwa', 'kg', r => r.mass.m_fuel, 1],
    ['power', 'Moc napędu', 'kW', r => r.sizing.design_point.power_kw, 1],
    ['thrust', 'Ciąg napędu', 'kN', r => r.sizing.design_point.thrust_kn, 2],
    ['ld', 'Doskonałość maksymalna', '−', r => r.aerodynamics.k_max, 2],
    ['stall', 'VS0, poziom morza', 'km/h', r => r.performance.speeds.vs_lnd_kmh, 1],
    ['vmax', 'Vmax TAS, poziom morza', 'km/h', r => r.params.engine_type === 'none' || r.performance.level_flight_available_sl === false ? null : r.performance.speeds.v_max_sl_kmh, 1],
    ['climb', 'Wznoszenie, poziom morza', 'm/s', r => r.performance.climb.wy_max_ms, 2],
    ['ceiling', 'Pułap praktyczny', 'm', r => r.performance.ceiling.service_ceiling_m, 0],
    ['margin', 'Zapas stateczności, tylne ŚM', '% ŚDA', r => r.balance.stability.static_margin_aft_pct, 1],
  ];
  const escape = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const format = (value, precision = 1) => Number.isFinite(value)
    ? value.toLocaleString('pl-PL', {minimumFractionDigits: precision, maximumFractionDigits: precision}) : '—';
  const filename = name => String(name || 'projekt-bipol').normalize('NFC').replace(/[^\p{L}\p{N}_-]+/gu, '-').replace(/^-|-$/g, '').slice(0, 80) || 'projekt-bipol';

  function createStore(storage, onState = () => {}) {
    const memory = new Map();
    const corrupt = new Set();
    const failures = new Set();
    let persistent = true;
    function state(ok) { persistent = ok; onState(ok); }
    return {
      read(key, fallback) {
        if (memory.has(key)) return JSON.parse(memory.get(key));
        try {
          const raw = storage?.getItem(key);
          if (raw == null) return fallback;
          const value = JSON.parse(raw);
          memory.set(key, raw);
          return value;
        } catch (_) { corrupt.add(key); failures.add(key); state(false); return fallback; }
      },
      write(key, value) {
        const raw = JSON.stringify(value);
        memory.set(key, raw);
        if (corrupt.has(key)) { state(false); return false; }
        try {
          if (!storage) throw new Error('Brak pamięci przeglądarki');
          storage.setItem(key, raw); failures.delete(key); state(failures.size === 0); return true;
        } catch (_) { failures.add(key); state(false); return false; }
      },
      get persistent() { return persistent; }
    };
  }

  function snapshot(result, name, now = new Date().toISOString()) {
    if (!result || result.status !== 'success') throw new Error('Najpierw oblicz poprawny projekt.');
    return {
      schema: 1, id: `variant-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: String(name || result.params.name || 'Wariant').slice(0, 160), date: now,
      params: JSON.parse(JSON.stringify(result.params)),
      metrics: Object.fromEntries(metrics.map(([key, , , get]) => [key, get(result) ?? null])),
      model: 'BiPOL Requiem / studio-1',
    };
  }

  function csv(rows) {
    function cell(value) {
      let text = value == null || (typeof value === 'number' && !Number.isFinite(value)) ? '' : String(value);
      if (typeof value === 'number') text = text.replace('.', ',');
      else if (/^[\s\uFEFF]*[=+@-]/u.test(text)) text = `'${text}`;
      return `"${text.replace(/"/g, '""')}"`;
    }
    return '\uFEFF' + rows.map(row => row.map(cell).join(';')).join('\r\n') + '\r\n';
  }

  function resultRows(result) {
    const rows = [['Sekcja', 'Wielkość', 'Wartość', 'Jednostka'], ['Projekt', 'Nazwa', result.params.name, '']];
    for (const [, label, unit, get] of metrics) rows.push(['Wyniki', label, get(result), unit]);
    for (const [name, value] of Object.entries(result.params)) {
      if (!name.startsWith('_') && (typeof value === 'string' || typeof value === 'number')) rows.push(['Parametry', name, value, '']);
    }
    for (const row of result.geometry.schrenk || []) rows.push(['Schrenk', 'y; c_schrenk', row.y, 'm'], ['Schrenk', 'c_schrenk', row.c_schrenk, 'm']);
    for (const row of result.aerodynamics.polar_points || []) rows.push(['Biegunowa', 'Cz', row.cz, '−'], ['Biegunowa', 'Cx, gładka', row.cx_clean, '−']);
    for (const row of result.balance.loading_states || []) rows.push(['Wyważenie', row.name, row.xcg_mac_pct, '% ŚDA']);
    for (const row of result.performance.glide?.points || []) rows.push(['Szybowanie', 'V TAS', row.v_kmh, 'km/h'], ['Szybowanie', 'Opadanie', row.sink_ms, 'm/s']);
    for (const row of result.compliance_checks || []) rows.push(['Weryfikacja', row.parameter, row.passed ? 'Spełnione' : row.severity === 'warning' ? 'Do oceny' : 'Niespełnione', row.actual]);
    return rows;
  }

  // crypto.randomUUID exists only in secure contexts (HTTPS, localhost), not on a LAN address over HTTP.
  function uniqueId(prefix) {
    const random = root.crypto?.randomUUID?.() || `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    return prefix + random;
  }

  const api = {metrics, escape, format, filename, createStore, snapshot, csv, resultRows, uniqueId};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.BipolStudio = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);

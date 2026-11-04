/* Where a BIPOL_1 trend suggestion comes from; shared by the P1 panel, the wizard and the input panel. */
(function (root) {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const num = (value, digits = 3) => Number.isFinite(value) ? value.toLocaleString('pl-PL', {maximumFractionDigits: digits}) : '—';
  const unit = s => s.unit && s.unit !== '−' ? ` ${esc(s.unit)}` : '';

  const CHART_SLOTS = [
    {
      detailsId: 'wizTrendChartDetailsBasis',
      selectId: 'wizTrendChartSelectBasis',
      stageId: 'wizTrendChartStageBasis',
      badgeId: 'wizTrendSampleBadgeBasis',
      keys: ['ar', 'me_m0', 'ws', 'pw', 'tw', 'ws_speed', 'rng_ar'],
      preferred: ['ar', 'me_m0'],
    },
    {
      detailsId: 'wizTrendChartDetailsMission',
      selectId: 'wizTrendChartSelectMission',
      stageId: 'wizTrendChartStageMission',
      badgeId: 'wizTrendSampleBadgeMission',
      keys: ['ws_speed', 'rng_ar', 'ws', 'ar'],
      preferred: ['ws_speed', 'ws'],
    },
    {
      detailsId: 'wizTrendChartDetailsPropulsion',
      selectId: 'wizTrendChartSelectPropulsion',
      stageId: 'wizTrendChartStagePropulsion',
      badgeId: 'wizTrendSampleBadgePropulsion',
      keys: ['pw', 'tw', 'ws_speed', 'me_m0'],
      preferred: ['pw', 'tw', 'me_m0'],
      hideWhenUnpowered: true,
    },
    {
      detailsId: 'wizTrendChartDetailsGeometry',
      selectId: 'wizTrendChartSelectGeometry',
      stageId: 'wizTrendChartStageGeometry',
      badgeId: 'wizTrendSampleBadgeGeometry',
      keys: ['vh', 'dihedral_deg', 'ar', 'b_ail_ratio', 'c_ail_ratio', 'c_e_ratio', 'c_r_ratio', 'v_v'],
      preferred: ['vh', 'ar'],
    },
  ];

  const PARAM_FIELD_FOR_CHART = {
    ar: ['aspect_ratio', 'AR', 2, ''],
    vh: ['v_h', 'V_H', 3, ''],
    v_v: ['v_v', 'V_V', 4, ''],
    dihedral_deg: ['dihedral_deg', 'Γ', 1, ' °'],
    b_ail_ratio: ['aileron_span_ratio', 'b_ail/(b/2)', 3, ''],
    c_ail_ratio: ['aileron_chord_ratio', 'c_ail/c', 3, ''],
    c_e_ratio: ['elevator_chord_ratio', 'c_e/c_H', 3, ''],
    c_r_ratio: ['rudder_chord_ratio', 'c_r/c_V', 3, ''],
  };

  let cachedQueryKey = null;
  let cachedPromise = null;
  let latestWizardData = null;

  function observations(p, s) {
    if (!p.observations?.length) return '';
    const rows = p.observations.map(o => `<tr><td>${esc(o.model)}</td>${p.x_label ? `<td>${o.x_label?.includes('Rok') || p.x_label?.includes('Rok') ? Math.round(o.x) : num(o.x, 0)}</td>` : ''}<td>${num(o.value, 4)}</td><td>${num(o.weight, 3)}</td><td>${esc(String(o.source || '').toUpperCase())}</td></tr>`).join('');
    return `<details class="trend-provenance-data"><summary>Dane wejściowe: ${p.observations.length} obserwacji</summary><div class="trend-table-scroll"><table class="b-table"><thead><tr><th>Konstrukcja</th>${p.x_label ? `<th>${esc(p.x_label)}</th>` : ''}<th>${esc(s.symbol)}${s.unit !== '−' ? ` [${esc(s.unit)}]` : ''}</th><th>Waga wᵢ</th><th>Źródło</th></tr></thead><tbody>${rows}</tbody></table></div></details>`;
  }

  function render(s, {alternatives = false} = {}) {
    const p = s?.provenance;
    if (!p) return '<div class="trend-provenance"><p>Ta wielkość nie dotyczy wybranego rodzaju napędu.</p></div>';
    const value = s.suggested_value != null ? ` → ${esc(s.symbol)} = <strong>${num(s.suggested_value, 4)}</strong>${unit(s)}` : '';
    const alt = (p.alternatives || []).map(a => `<p>Wartość alternatywna — ${esc(a.label)}: <strong>${num(a.value, 4)}</strong>${unit(s)}${alternatives ? ` <button type="button" class="btn btn-outline btn-sm" data-trend-alternative="${esc(s.key)}" data-value="${a.value}">Zastosuj tę wartość</button>` : ''}</p>`).join('');
    return `<div class="trend-provenance">
      <p><strong>${esc(p.method)}</strong>${value}</p>
      <p class="trend-provenance-basis">Podstawa: ${esc(p.basis)}</p>
      <p>Próba: ${esc(p.sample.description)} — ${p.sample.selected_n} wariantów, ${p.sample.families_n} rodzin.</p>
      ${p.formula ? `<p class="studio-equation">${esc(p.formula)}</p>` : ''}
      ${p.steps?.length ? `<ol>${p.steps.map(step => `<li>${esc(step)}</li>`).join('')}</ol>` : ''}
      ${alt}
      ${p.warnings?.length ? `<ul class="trend-provenance-warnings">${p.warnings.map(w => `<li>${esc(w)}</li>`).join('')}</ul>` : ''}
      ${observations(p, s)}
    </div>`;
  }

  // The comparison sample of the project: the wizard and the input panel must
  // propose values from the same aircraft as the P1 trend analysis.
  const SAMPLE_KEYS = ['trend_source', 'trend_nearest_count', 'trend_reference_mode', 'mass_initial_guess', 'trend_engine_count', 'trend_year_min',
    'trend_year_max', 'trend_weighting', 'trend_year_basis', 'trend_aircraft_ids', 'trend_observations', 'variable_sweep'];

  function sampleSettings(project, query) {
    const settings = {};
    for (const key of SAMPLE_KEYS) {
      const value = project?.[key];
      if (value != null && value !== '' && !Number.isNaN(value)) settings[key] = value;
    }
    // A manual aircraft selection belongs to one class and propulsion.
    if (project && (query.aircraft_type !== project.aircraft_type || (query.engine_type && query.engine_type !== project.engine_type))) {
      delete settings.trend_aircraft_ids;
    }
    return settings;
  }

  function projectSettings() {
    if (typeof formBaseParams === 'undefined') return {};
    return typeof collectFormData === 'function' ? collectFormData() : formBaseParams;
  }

  async function fetchSuggestions(query, project = projectSettings()) {
    const body = {};
    for (const [key, value] of Object.entries(query)) if (value) body[key] = value;
    Object.assign(body, sampleSettings(project, body));
    if (body.trend_reference_mode === 'design') {
      for (const [key,value] of Object.entries(project || {})) {
        if (!key.startsWith('_') && !(key in body) && value != null && value !== '') body[key] = value;
      }
    }
    const keyStr = JSON.stringify(body);
    if (cachedPromise && cachedQueryKey === keyStr) return cachedPromise;
    cachedQueryKey = keyStr;
    cachedPromise = (async () => {
      const response = await fetch('/api/trends/suggestions', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || 'Nie udało się pobrać analizy trendów.');
      return data;
    })().catch(err => {
      if (cachedQueryKey === keyStr) { cachedQueryKey = null; cachedPromise = null; }
      throw err;
    });
    return cachedPromise;
  }

  function readWizVal(paramKey) {
    if (root.BipolDesignBasis?.wizardValue) return root.BipolDesignBasis.wizardValue(paramKey);
    const el = typeof document !== 'undefined' ? document.getElementById('wiz_' + paramKey) : null;
    return el ? Number(el.value) : NaN;
  }

  function currentProjectMarker(chart) {
    if (!chart) return null;
    if (chart.key === 'rng_ar') {
      const ar = readWizVal('aspect_ratio');
      const rng = readWizVal('range_km');
      if (Number.isFinite(ar) && ar >= 2 && Number.isFinite(rng) && rng > 0) {
        return {x: ar, y: rng, label: `Kreator: AR=${num(ar, 1)}, R=${num(rng, 0)} km`};
      }
      return null;
    }
    if (chart.key === 'ws_speed' && chart.speed_metric === 'v_cruise_kmh') {
      const vcr = readWizVal('cruise_speed_kmh');
      if (Number.isFinite(vcr) && vcr > 0) {
        return {y: vcr, label: `Kreator: Vcr = ${num(vcr, 0)} km/h`};
      }
      return null;
    }
    const spec = PARAM_FIELD_FOR_CHART[chart.key];
    if (spec) {
      const [field, sym, digits, suffix] = spec;
      const val = readWizVal(field);
      if (Number.isFinite(val) && (field === 'dihedral_deg' ? val >= -15 && val <= 20 : val > 0)) {
        return {y: val, label: `Kreator: ${sym} = ${num(val, digits)}${suffix}`};
      }
    }
    return null;
  }

  function renderWizardChartSvg(chart, marker = null) {
    if (!chart || !chart.points?.length) {
      return '<p class="trend-empty" style="padding:14px 10px; margin:4px 0; border-radius:6px; font-size:0.78rem;">Brak udokumentowanych obserwacji tej zależności w próbie dla wybranej klasy.</p>';
    }
    const pts = chart.points;
    const xs = pts.map(p => p.x);
    const ys = pts.map(p => p.y);
    if (chart.forecast && Number.isFinite(chart.forecast.x) && Number.isFinite(chart.forecast.y)) {
      xs.push(chart.forecast.x);
      ys.push(chart.forecast.y);
    }
    if (Array.isArray(chart.typical_range) && chart.typical_range.length === 2) {
      ys.push(chart.typical_range[0], chart.typical_range[1]);
    }
    if (Number.isFinite(chart.suggested_value)) ys.push(chart.suggested_value);

    const rawYMin = Math.min(...ys), rawYMax = Math.max(...ys), rawSpanY = (rawYMax - rawYMin) || Math.abs(rawYMax) * 0.2 || 1;
    if (marker) {
      if (Number.isFinite(marker.x)) {
        const rawXMin = Math.min(...xs), rawXMax = Math.max(...xs), rawSpanX = (rawXMax - rawXMin) || 1;
        if (marker.x >= rawXMin - 1.5 * rawSpanX && marker.x <= rawXMax + 1.5 * rawSpanX) xs.push(marker.x);
      }
      if (Number.isFinite(marker.y) && marker.y >= rawYMin - 1.5 * rawSpanY && marker.y <= rawYMax + 1.5 * rawSpanY) {
        ys.push(marker.y);
      }
    }

    let xmin = Math.min(...xs), xmax = Math.max(...xs);
    let ymin = Math.min(...ys), ymax = Math.max(...ys);
    const padX = (xmax - xmin) * 0.06 || 1;
    const padY = (ymax - ymin) * 0.14 || 0.1;
    xmin -= padX; xmax += padX; ymin -= padY; ymax += padY;

    const W = 680, H = 198, l = 64, r = 20, t = 16, b = 40;
    const X = x => l + (x - xmin) / (xmax - xmin) * (W - l - r);
    const Y = y => H - b - (y - ymin) / (ymax - ymin) * (H - t - b);
    const clampY = y => Math.max(t + 2, Math.min(H - b - 2, Y(y)));
    const clampX = x => Math.max(l + 2, Math.min(W - r - 2, X(x)));
    const fmtX = x => chart.kind === 'time' ? String(Math.round(x)) : num(x, Math.abs(xmax - xmin) < 12 ? 1 : 0);
    const fmtY = y => num(y, Math.abs(ymax - ymin) < 0.2 ? 3 : Math.abs(ymax - ymin) < 12 ? 2 : 0);
    const unitSuffix = chart.unit && chart.unit !== '−' ? ` ${chart.unit}` : '';

    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(chart.title)}"><title>${esc(chart.title)}</title>`;

    if (Array.isArray(chart.typical_range) && chart.typical_range.length === 2) {
      const yTop = clampY(chart.typical_range[1]);
      const yBot = clampY(chart.typical_range[0]);
      if (yBot > yTop) {
        svg += `<rect x="${l}" y="${yTop.toFixed(1)}" width="${W - l - r}" height="${(yBot - yTop).toFixed(1)}" fill="#e0f2fe" fill-opacity="0.6"/>`;
      }
    }

    for (let i = 0; i <= 4; i++) {
      const xv = xmin + (xmax - xmin) * i / 4;
      const yv = ymin + (ymax - ymin) * i / 4;
      svg += `<path d="M${X(xv).toFixed(1)} ${t}V${H - b}M${l} ${Y(yv).toFixed(1)}H${W - r}" stroke="#dce7eb" stroke-dasharray="3 4"/>`;
      svg += `<text x="${X(xv).toFixed(1)}" y="${H - b + 17}" text-anchor="middle">${esc(fmtX(xv))}</text>`;
      svg += `<text x="${l - 7}" y="${(Y(yv) + 4).toFixed(1)}" text-anchor="end">${esc(fmtY(yv))}</text>`;
    }
    svg += `<rect x="${l}" y="${t}" width="${W - l - r}" height="${H - t - b}" fill="none" stroke="#cbd5e1"/>`;

    const fit = chart.fit;
    const predictFit = x => fit.kind === 'power' ? fit.A * Math.pow(x, fit.C) : fit.intercept + fit.slope * x;
    if (fit) {
      const d = Array.from({length: 57}, (_, i) => {
        const xv = fit.x_min + (fit.x_max - fit.x_min) * i / 56;
        return `${i ? 'L' : 'M'}${X(xv).toFixed(1)},${clampY(predictFit(xv)).toFixed(1)}`;
      }).join(' ');
      svg += `<path d="${d}" stroke="#147f76" stroke-width="2.4" fill="none"/>`;
      if (chart.forecast) {
        const yEnd = predictFit(fit.x_max);
        svg += `<path d="M${X(fit.x_max).toFixed(1)},${clampY(yEnd).toFixed(1)}L${X(chart.forecast.x).toFixed(1)},${clampY(chart.forecast.y).toFixed(1)}" stroke="#a86621" stroke-width="2" stroke-dasharray="5 4"/>`;
      }
    }
    if ((!fit || (chart.forecast && !chart.forecast.accepted)) && Number.isFinite(chart.suggested_value)) {
      const ym = clampY(chart.suggested_value);
      svg += `<line x1="${l}" y1="${ym.toFixed(1)}" x2="${W - r}" y2="${ym.toFixed(1)}" stroke="#147f76" stroke-width="2.2" ${fit ? 'stroke-dasharray="7 4"' : ''}/>`;
    }

    for (const p of pts) {
      svg += `<circle cx="${X(p.x).toFixed(1)}" cy="${clampY(p.y).toFixed(1)}" r="3.8" fill="#5478a9" fill-opacity="0.75"><title>${esc(p.model)}: ${esc(fmtX(p.x))} → ${esc(num(p.y, 3))}${esc(unitSuffix)}</title></circle>`;
    }

    if (chart.forecast) {
      svg += `<circle cx="${X(chart.forecast.x).toFixed(1)}" cy="${clampY(chart.forecast.y).toFixed(1)}" r="5.5" fill="#a86621" stroke="#ffffff" stroke-width="1.8"><title>Prognoza ${chart.forecast.x} r.: ${esc(num(chart.forecast.y, 3))}${esc(unitSuffix)}</title></circle>`;
    }

    if (marker) {
      if (Number.isFinite(marker.x) && Number.isFinite(marker.y)) {
        const mx = clampX(marker.x), my = clampY(marker.y);
        svg += `<circle cx="${mx.toFixed(1)}" cy="${my.toFixed(1)}" r="6" fill="#b5486a" stroke="#ffffff" stroke-width="2"><title>${esc(marker.label)}</title></circle>`;
        const anchor = mx > W - 180 ? 'end' : 'start';
        const tx = mx + (anchor === 'end' ? -9 : 9);
        const ty = my < t + 20 ? my + 14 : my - 8;
        svg += `<text x="${tx.toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="${anchor}" style="fill:#9d174d; font-weight:700; font-size:11px; paint-order:stroke; stroke:#ffffff; stroke-width:3px;">${esc(marker.label)}</text>`;
      } else if (Number.isFinite(marker.y)) {
        const my = clampY(marker.y);
        svg += `<line x1="${l}" y1="${my.toFixed(1)}" x2="${W - r}" y2="${my.toFixed(1)}" stroke="#b5486a" stroke-width="1.9" stroke-dasharray="6 4"/>`;
        const ty = my < t + 15 ? my + 12 : my - 5;
        svg += `<text x="${W - r - 4}" y="${ty.toFixed(1)}" text-anchor="end" style="fill:#9d174d; font-weight:700; font-size:11px; paint-order:stroke; stroke:#ffffff; stroke-width:3px;">${esc(marker.label)}</text>`;
      }
    }

    svg += `<text x="${((l + W - r) / 2).toFixed(1)}" y="${H - 6}" text-anchor="middle" style="font-weight:600;">${esc(chart.x_label)}</text>`;
    svg += `<text transform="translate(15 ${((t + H - b) / 2).toFixed(1)}) rotate(-90)" text-anchor="middle" style="font-weight:600;">${esc(chart.y_label)}</text>`;
    svg += '</svg>';

    const statsParts = [];
    if (fit) statsParts.push(`n = ${fit.n}${fit.r2 != null ? ` · R² = ${num(fit.r2, 3)}` : ''}`);
    else statsParts.push(`n = ${chart.n}`);
    if (Number.isFinite(chart.suggested_value)) {
      statsParts.push(`Sugestia BIPOL_1: <strong>${esc(chart.symbol)} = ${num(chart.suggested_value, chart.key === 'v_v' ? 4 : 3)}${esc(unitSuffix)}</strong>`);
    } else if (chart.equation) {
      statsParts.push(`<code>${esc(chart.equation)}</code>`);
    }

    return `${svg}<div class="wizard-trend-legend">
      <span><i class="wizard-trend-dot" style="background:#5478a9"></i>Konstrukcje (${chart.n})</span>
      <span><i class="wizard-trend-line-swatch" style="background:#147f76"></i>${fit ? 'Regresja z próby' : 'Średnia ważona BIPOL_1'}</span>
      ${chart.forecast ? `<span><i class="wizard-trend-dot" style="background:#a86621"></i>Prognoza ${chart.forecast.x} r.${chart.forecast.accepted ? '' : ' (odrzucona według kryteriów → średnia)'}</span>` : ''}
      ${Array.isArray(chart.typical_range) ? `<span><i class="wizard-trend-band-swatch"></i>Zakres lit. (${num(chart.typical_range[0], 2)}–${num(chart.typical_range[1], 2)}${esc(unitSuffix)})</span>` : ''}
      ${marker ? `<span><i class="wizard-trend-line-swatch" style="background:#b5486a"></i>Twój projekt w kreatorze</span>` : ''}
      <span style="margin-left:auto;">${statsParts.join(' · ')}</span>
    </div>`;
  }

  function refreshWizardCharts() {
    if (typeof document === 'undefined' || !latestWizardData?.charts) return;
    const data = latestWizardData;
    const sampleText = `${data.class_name} · próba n = ${data.sample?.selected_n ?? 0} (${data.sample?.families_n ?? 0} rodzin)`;
    for (const slot of CHART_SLOTS) {
      const details = document.getElementById(slot.detailsId);
      const select = document.getElementById(slot.selectId);
      const stage = document.getElementById(slot.stageId);
      const badge = document.getElementById(slot.badgeId);
      if (!select || !stage) continue;
      if (details && slot.hideWhenUnpowered) {
        details.hidden = data.engine_type === 'none';
        if (details.hidden) continue;
      }
      if (badge) badge.textContent = sampleText;
      const availableKeys = slot.keys.filter(k => data.charts[k]);
      const prevVal = select.value;
      const optionSig = availableKeys.map(k => `${k}:${data.charts[k].n}:${data.charts[k].title}`).join('|');
      if (select.dataset.optionSig !== optionSig) {
        select.innerHTML = availableKeys.map(k => {
          const c = data.charts[k];
          const cleanOptionTitle = c.title.replace(/\s+\S*_\S*(?=\s|$)/g, '');
          return `<option value="${esc(k)}">${esc(cleanOptionTitle)} (n=${c.n})</option>`;
        }).join('');
        select.dataset.optionSig = optionSig;
        if (availableKeys.includes(prevVal) && data.charts[prevVal].n > 0) {
          select.value = prevVal;
        } else {
          const best = slot.preferred.find(k => data.charts[k]?.n >= 3)
            || availableKeys.find(k => data.charts[k]?.n > 0)
            || availableKeys[0] || '';
          select.value = best;
        }
      }
      const chosen = data.charts[select.value] || data.charts[availableKeys[0]];
      stage.innerHTML = renderWizardChartSvg(chosen, currentProjectMarker(chosen));
    }
  }

  // The project the wizard is building carries its own comparison-sample settings.
  const wizardProject = () => root.BipolDesignBasis?.wizardBase?.() || projectSettings();

  // Wizard: apply the chosen suggestions and show where each value came from.
  async function applyInWizard(button, box, keys, assign) {
    const original = button.textContent;
    button.disabled = true; button.textContent = 'Ładowanie…';
    const field = id => document.getElementById(id)?.value;
    try {
      const data = await fetchSuggestions({aircraft_type: field('wiz_aircraft_type') || 'piston_ga',
        engine_type: field('wiz_engine_type'), wing_configuration: field('wiz_wing_config')}, wizardProject());
      latestWizardData = data;
      const used = keys.map(key => data.suggestions[key]).filter(s => s?.suggested_value != null);
      used.forEach(s => assign(s.key, s.suggested_value));
      refreshWizardCharts();
      const missing = keys.filter(key => data.suggestions[key]?.provenance && data.suggestions[key].suggested_value == null);
      box.hidden = false;
      box.innerHTML = (used.length ? `<p role="status">Zastosowano z analizy trendów (prognozy na ${data.forecast_year} r.): ${used.map(s => `${esc(s.symbol)} = ${num(s.suggested_value, 4)}${unit(s)}`).join(', ')}.</p>` : '<p role="status">Brak danych w bazie dla tej klasy; wartości nie zmieniono.</p>') +
        (missing.length ? `<p>Bez zmian (brak danych w próbie): ${missing.map(key => esc(data.suggestions[key].symbol)).join(', ')}.</p>` : '') +
        used.map(s => `<details><summary>Skąd ${esc(s.symbol)} = ${num(s.suggested_value, 4)}${unit(s)}?</summary>${render(s, {alternatives: true})}</details>`).join('');
      box.querySelectorAll('[data-trend-alternative]').forEach(alt => alt.addEventListener('click', () => {
        assign(alt.dataset.trendAlternative, Number(alt.dataset.value));
        alt.textContent = 'Zastosowano'; alt.disabled = true;
        refreshWizardCharts();
      }));
    } catch (error) {
      box.hidden = false; box.textContent = error.message;
    } finally {
      button.disabled = false; button.textContent = original;
    }
  }

  let previewSeq = 0;
  async function previewInWizard() {
    const basisEl = typeof document !== 'undefined' ? document.getElementById('wizTrendPreviewBasis') : null;
    const geomEl = typeof document !== 'undefined' ? document.getElementById('wizTrendPreviewGeometry') : null;
    const anyChart = typeof document !== 'undefined' && document.getElementById('wizTrendChartStageBasis');
    if (!basisEl && !geomEl && !anyChart) return;
    const seq = ++previewSeq;
    const field = id => document.getElementById(id)?.value;
    try {
      const data = await fetchSuggestions({
        aircraft_type: field('wiz_aircraft_type') || 'piston_ga',
        engine_type: field('wiz_engine_type'),
        wing_configuration: field('wiz_wing_config')
      }, wizardProject());
      if (seq !== previewSeq) return;
      latestWizardData = data;
      const ar = data.suggestions?.ar;
      if (basisEl) {
        basisEl.innerHTML = ar?.suggested_value != null
          ? ` — <strong>AR &approx; ${num(ar.suggested_value, 2)}</strong> (próba n = ${ar.provenance?.sample?.selected_n ?? '?'})`
          : '';
      }
      if (geomEl) {
        const parts = ['ar', 'vh', 'v_v', 'dihedral_deg']
          .map(k => data.suggestions?.[k])
          .filter(s => s?.suggested_value != null)
          .map(s => `${esc(s.symbol)} &approx; ${num(s.suggested_value, s.key === 'v_v' ? 3 : 2)}${unit(s)}`);
        geomEl.innerHTML = parts.length ? ` — <strong>${parts.join(' &middot; ')}</strong>` : '';
      }
      refreshWizardCharts();
    } catch (_) {
      if (seq !== previewSeq) return;
      if (basisEl) basisEl.textContent = '';
      if (geomEl) geomEl.textContent = '';
    }
  }

  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
      for (const slot of CHART_SLOTS) {
        document.getElementById(slot.selectId)?.addEventListener('change', refreshWizardCharts);
      }
      document.getElementById('wizSuggestSpeedsBtn')?.addEventListener('click', () => {
        setTimeout(refreshWizardCharts, 0);
      });
    });
    document.addEventListener('bipol:catalog-updated', () => {
      cachedQueryKey = null;
      cachedPromise = null;
      previewInWizard();
    });
  }

  const api = {render, fetchSuggestions, applyInWizard, previewInWizard, refreshWizardCharts, renderWizardChartSvg};
  root.BipolTrendProvenance = api;
  if (typeof module !== 'undefined') module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);

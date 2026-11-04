/* Source data are owned by Python. The browser selects a real engine and an operating point. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const keys = ['engine_fuel_mode','engine_model_id','engine_fuel_point','fuel_density_kg_l',
    'engine_custom_sfc','engine_custom_model','engine_custom_power_kw','engine_custom_thrust_kn','engine_fuel_source','engine_fuel_conditions',
    'engine_max_fuel_source','engine_max_fuel_conditions'];
  let engines = [], lastResult = null;
  let resolveReady;
  const ready = new Promise(resolve => { resolveReady = resolve; });
  const esc = s => window.BipolStudio?.escape ? window.BipolStudio.escape(String(s ?? '')) : String(s ?? '');
  const fmt = (v, d=3) => Number(v).toLocaleString('pl-PL',{maximumFractionDigits:d});
  const kind = () => $('engine_type')?.value || (window.formBaseParams && window.formBaseParams.engine_type) || 'prop';
  const chosen = () => engines.find(e=>e.id===$('engine_model_id')?.value);

  function points(preferred) {
    const record = chosen();
    const select = $('engine_fuel_point');
    if (!select) return;
    const old = preferred ?? select.value;
    select.innerHTML = (record?.points || []).map(p=>`<option value="${esc(p.id)}">${esc(p.conditions)} — ${fmt(p.value)} ${esc(p.unit)}</option>`).join('');
    if (record?.points?.some(p=>p.id===old)) select.value=old;
    visibility();
  }

  function visibility() {
    const mode = $('engine_fuel_mode')?.value || 'unselected';
    const jet = kind() === 'jet';
    const none = kind() === 'none';
    if ($('engineFuelPanel')) $('engineFuelPanel').hidden = none;
    const point = chosen()?.points?.find(p => p.id === $('engine_fuel_point')?.value);
    const isVol = point ? ['l/h','US gal/h'].includes(point.unit) : (engines.length === 0);
    for (const el of document.querySelectorAll('[data-engine-catalog]')) el.hidden = mode !== 'catalog';
    for (const el of document.querySelectorAll('[data-engine-custom]')) el.hidden = mode !== 'custom';
    for (const el of document.querySelectorAll('[data-engine-shaft]')) el.hidden = jet;
    for (const el of document.querySelectorAll('[data-engine-jet]')) el.hidden = !jet;
    for (const el of document.querySelectorAll('[data-engine-density]')) el.hidden = !isVol;
    for (const el of document.querySelectorAll('[data-engine-field]')) el.disabled = none || !!el.closest('[hidden]');

    // SINGLE AUTHORITATIVE SFC FIELD (#sfc):
    // ReadOnly ONLY in catalog mode (where value is driven by catalog point) or when no engine (glider)
    if ($('sfc')) {
      $('sfc').readOnly = none || mode === 'catalog';
      if ($('engine_custom_sfc')) $('engine_custom_sfc').value = $('sfc').value;
    }
    if ($('engineCustomSfcUnit')) $('engineCustomSfcUnit').textContent = jet ? 'cT·g [1/h]' : '[g/(kW·h)]';
    if ($('engine_power_kw')) {
      $('engine_power_kw').readOnly = none || mode === 'catalog';
      if ($('engine_custom_power_kw')) $('engine_custom_power_kw').value = $('engine_power_kw').value;
    }
  }

  function sync(params) {
    if (!params || Object.keys(params).length === 0) {
      params = typeof formBaseParams === 'object' ? formBaseParams : null;
      if (!params || Object.keys(params).length === 0) {
        try {
          if (typeof getActiveProject === 'function') {
            params = getActiveProject()?.params;
          }
        } catch (_) {}
      }
    }
    params = params || {};
    if (!$('engineFuelPanel')) return;
    if ($('engine_fuel_mode')) $('engine_fuel_mode').value = params.engine_fuel_mode || 'unselected';
    const previous = params.engine_model_id || '';
    if ($('engine_model_id')) {
      $('engine_model_id').innerHTML = '<option value="">Wybierz model z katalogu</option>' + engines.filter(e => e.engine_type === kind()).map(e => `<option value="${esc(e.id)}">${esc(e.model)}</option>`).join('');
      if (previous) $('engine_model_id').value = previous;
    }
    for (const key of keys.filter(k => !['engine_fuel_mode','engine_model_id','engine_fuel_point'].includes(k))) {
      const el = $(key);
      if (el && params[key] !== undefined) {
        el.value = params[key];
      } else if (el) {
        el.value = key === 'fuel_density_kg_l' ? 0.72 : key.includes('_power_') || key.includes('_thrust_') ? 0 : '';
      }
    }
    const curSfc = params.sfc ?? ($('sfc')?.value || (kind() === 'jet' ? 0.62 : 265));
    if ($('engine_custom_sfc')) $('engine_custom_sfc').value = curSfc;
    if ($('sfc') && params.sfc !== undefined) $('sfc').value = params.sfc;
    if (params.engine_custom_power_kw && $('engine_power_kw')) $('engine_power_kw').value = params.engine_custom_power_kw;
    points(params.engine_fuel_point || $('engine_fuel_point')?.value);
    visibility();
  }

  function collect(data) {
    if (!$('engineFuelPanel')) return data;
    delete data._engine_fuel;
    delete data.engine_static_thrust_kn;
    for (const key of keys) {
      const el = $(key);
      if (!el || el.disabled || !el.value.trim()) { delete data[key]; continue; }
      if (!el.checkValidity()) throw Error(`Dane silnika: ${el.closest('label')?.textContent.trim() || key}. ${el.validationMessage}`);
      data[key] = el.type === 'number' ? Number(el.value) : el.value;
    }
    if (data.engine_fuel_mode === 'custom') {
      const sVal = $('sfc') ? Number($('sfc').value) : data.engine_custom_sfc;
      data.sfc = sVal;
      if ($('engine_custom_sfc')) $('engine_custom_sfc').value = sVal;
      if ($('engine_power_kw') && kind() !== 'jet') {
        const pVal = Number($('engine_power_kw').value);
        if (pVal > 0) data.engine_custom_power_kw = pVal;
      }
    }
    delete data.engine_custom_sfc;
    return data;
  }

  function render(result) {
    lastResult = result;
    if (!$('engineFuelPanel')) return;
    sync(result.params);
    const ef = result.engine_selection;
    if (!ef) return;

    let htmlStatus = '';
    if (ef.supported && ef.status !== 'not_applicable') {
      if ($('sfc')) $('sfc').value = result.params.sfc;
      if ($('engine_custom_sfc')) $('engine_custom_sfc').value = result.params.sfc;
      if (result.params.engine_type === 'prop' && $('engine_power_kw')) $('engine_power_kw').value = result.params.engine_power_kw;
      if ($('power_input_mode') && result.params.engine_type === 'prop') $('power_input_mode').value = 'fixed';
      htmlStatus = `<p><strong>${ef.count} × ${esc(ef.model)}</strong>; SFC w obliczeniach: <strong>${fmt(ef.sfc,4)} ${esc(ef.unit)}</strong>.</p><p>Punkt źródłowy: <strong>${fmt(ef.point.value,4)} ${esc(ef.point.unit)}</strong>${ef.point.power_kw ? ` przy ${fmt(ef.point.power_kw)} kW na silnik` : ""}; ${esc(ef.point.conditions)}.</p><p>Dostępne łącznie: <strong>${fmt(ef.installed_total)} ${esc(ef.rating_unit)}</strong>; wymagane: ${fmt(ef.required_total)} ${esc(ef.rating_unit)}. ${esc(ef.rating_note)}</p><p>${esc(ef.source)} ${esc(ef.locator)}${ef.source_url ? ` · <a href="${esc(ef.source_url)}" target="_blank" rel="noopener">Dokument producenta</a>` : ''}</p><p>${esc(ef.notes.join(' '))}</p><p>${ef.adequate ? 'Moc/ciąg wystarcza według bieżącego doboru.' : 'Moc/ciąg nie wystarcza — wybierz inną propozycję.'}</p>`;
    } else {
      htmlStatus = ef.notes?.join(' ') || 'Lot bez napędu.';
    }

    if ($('engineFuelStatus')) $('engineFuelStatus').innerHTML = htmlStatus;
    if ($('engineSummaryStatus')) $('engineSummaryStatus').innerHTML = htmlStatus;

    const candHtml = ef.candidates?.length
      ? `<table class="b-table"><thead><tr><th>Silnik</th><th>Moc/ciąg łącznie</th><th>Źródłowy punkt paliwowy</th><th>Dobór</th></tr></thead><tbody>${ef.candidates.map(e => `<tr><td>${esc(e.model)}</td><td>${fmt(e.total_rating)} ${esc(ef.rating_unit)}</td><td>${fmt(e.points[0].value)} ${esc(e.points[0].unit)}<br>${esc(e.points[0].conditions)}</td><td><button type="button" class="btn btn-outline btn-sm" data-engine-pick="${esc(e.id)}">${e.adequate ? 'Przyjmij' : 'Sprawdź — za mała moc/ciąg'}</button></td></tr>`).join('')}</tbody></table>`
      : 'Brak udokumentowanej propozycji tej klasy w lokalnym katalogu. Podaj rzeczywisty model i źródło przez „Inny rzeczywisty silnik”.';

    if ($('engineFuelCandidates')) $('engineFuelCandidates').innerHTML = candHtml;
    if ($('engineFuelCandidatesTab')) $('engineFuelCandidatesTab').innerHTML = candHtml;
  }

  window.BipolEngineFuel = { collect, ready };
  window.focusPropulsionModule = function() {
    const body = document.getElementById('body_mod4');
    if (body && body.classList.contains('collapsed')) {
      if (typeof toggleAccordion === 'function') toggleAccordion('mod4');
    }
    const el = document.getElementById('accordion_mod4');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      el.classList.add('flash-highlight');
      setTimeout(() => el.classList.remove('flash-highlight'), 1500);
    }
  };
  if (window.BipolStudio) window.BipolStudio.focusPropulsionModule = window.focusPropulsionModule;

  document.addEventListener('DOMContentLoaded', async () => {
    $('engineFuelPanel')?.addEventListener('input', () => {
      const st = $('engineFuelStatus');
      if (st) st.textContent = 'Dane silnika zmienione — przyjmij je i przelicz projekt.';
    });

    $('sfc')?.addEventListener('input', () => {
      if ($('engine_custom_sfc')) $('engine_custom_sfc').value = $('sfc').value;
    });
    $('engine_custom_sfc')?.addEventListener('input', () => {
      if ($('sfc')) $('sfc').value = $('engine_custom_sfc').value;
    });
    $('engine_power_kw')?.addEventListener('input', () => {
      if ($('engine_custom_power_kw')) $('engine_custom_power_kw').value = $('engine_power_kw').value;
    });
    $('engine_custom_power_kw')?.addEventListener('input', () => {
      if ($('engine_power_kw')) $('engine_power_kw').value = $('engine_custom_power_kw').value;
    });

    $('engine_fuel_mode')?.addEventListener('change', visibility);
    $('engine_model_id')?.addEventListener('change', () => points(''));
    $('engine_fuel_point')?.addEventListener('change', visibility);
    $('applyEngineFuel')?.addEventListener('click', () => {
      if (typeof performCalculation === 'function') performCalculation();
    });

    const pickHandler = event => {
      const button = event.target.closest('[data-engine-pick]');
      if (!button) return;
      $('engine_fuel_mode').value = 'catalog';
      $('engine_model_id').value = button.dataset.enginePick;
      points('');
      visibility();
      if (typeof performCalculation === 'function') performCalculation();
    };
    $('engineFuelCandidates')?.addEventListener('click', pickHandler);
    $('engineFuelCandidatesTab')?.addEventListener('click', pickHandler);

    $('engine_type')?.addEventListener('change', () => {
      if (chosen()?.engine_type !== kind()) {
        $('engine_fuel_mode').value = 'unselected';
        $('engine_model_id').innerHTML = '<option value="">Wybierz model z katalogu</option>' + engines.filter(e => e.engine_type === kind()).map(e => `<option value="${esc(e.id)}">${esc(e.model)}</option>`).join('');
        points('');
      }
      visibility();
    });

    sync();
    try {
      const response = await fetch('/api/engines');
      if (!response.ok) throw Error('Brak katalogu silników.');
      engines = (await response.json()).engines;
      sync();
      if (lastResult) render(lastResult);
    } catch (error) {
      if ($('engineFuelStatus')) $('engineFuelStatus').textContent = error.message;
    } finally {
      resolveReady();
    }
  });

  document.addEventListener('bipol:project', () => sync());
  document.addEventListener('bipol:results', event => render(event.detail));
})();

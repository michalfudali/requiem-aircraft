(function () {
  'use strict';
  const $=id=>document.getElementById(id);
  const defaults={mass_method:'auto',empty_mass_model:'trend',empty_mass_closure:'trend',cx0_deviation_reason:'',
    payload_drop_kg:0,return_range_km:0,max_power_time_min:0,climb_fraction_mode:'auto',
    climb_start_altitude_m:0,preliminary_polar_mode:'raymer',wetted_example:'',sketch_swet_ratio:4,
    raymer_kmax:15,cx0_reference_class:'',
    mass_point_x1:1000,mass_point_x2:2000,
    mass_point_y1:.6,mass_point_y2:.55,
    corke_start_ordinate:.99,corke_end_ordinate:.98,trend_year_basis:'certification'};
  function visibility() {
    const model=$('empty_mass_model').value;
    document.querySelectorAll('[data-bipol1-group]').forEach(el=>el.hidden=el.dataset.bipol1Group!==model);
    document.querySelector('[data-bipol1-task]').hidden=!(Number($('max_power_time_min').value)>0);
    document.querySelector('[data-bipol1-corke-reading]').hidden=$('climb_fraction_mode').value!=='reading';
    document.querySelector('[data-bipol1-raymer-reading]').hidden=$('preliminary_polar_mode').value!=='reading';
    document.querySelector('[data-bipol1-sketch]').hidden=$('wetted_example').value!=='sketch';
    const jet=($('engine_type')?.value||formBaseParams.engine_type)==='jet';
    document.querySelector('[data-bipol1-prop]').hidden=jet;
    document.querySelector('[data-bipol1-jet]').hidden=!jet;
    $('bipol1SfcUnit').textContent=jet?'[1/h, cT·g]':'[g/(kW·h)]';
  }
  function sync(p=formBaseParams) {
    document.querySelectorAll('[data-bipol1]').forEach(el=>el.value=p[el.id]??defaults[el.id]??'');
    if(!['raymer','reading','input'].includes($('preliminary_polar_mode').value)) $('preliminary_polar_mode').value='raymer';
    if(!['trend','two_point'].includes($('empty_mass_model').value)) $('empty_mass_model').value='trend';
    if(!p.wetted_example&&['raymer','reading'].includes(p.preliminary_polar_mode)&&p.sketch_swet_ratio) $('wetted_example').value='sketch';
    visibility();
  }
  function collect(data) {
    visibility();
    for(const el of document.querySelectorAll('[data-bipol1]')) {
      if(el.closest('[hidden]')) continue;
      if(!el.value.trim()) {delete data[el.id];continue;}
      const val=el.validity; if(val&&(val.badInput||val.rangeUnderflow||val.rangeOverflow||val.valueMissing)) throw Error(`Sprawdź: ${el.closest('label')?.textContent.trim()||el.id}. ${el.validationMessage}`);
      data[el.id]=el.type==='number'?Number(el.value):el.value;
    }
    if(data.wetted_example!=='sketch') delete data.sketch_swet_ratio;
    if(data.preliminary_polar_mode==='input') data.preliminary_polar_includes_configuration=true;
    else delete data.preliminary_polar_includes_configuration;
    delete data.raymer_family;
    // BIPOL_1, wzór (1): A i C zawsze z linii trendu (programu albo własnego odczytu dwóch punktów).
    for(const key of ['empty_mass_trend_A','empty_mass_trend_C','empty_mass_fraction','empty_mass_a','empty_mass_c']) delete data[key];
    delete data.outbound_range_km;
    return data;
  }
  function render(res) {
    const esc = (window.BipolStudio && window.BipolStudio.escape) || (s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
    const fmt = (window.BipolStudio && window.BipolStudio.format) || ((n, d = 1) => Number(n).toFixed(d));
    const m = res.mass, r = res.bipol1_review;
    if (!r || !m) return;
    sync(res.params);

    const drop = m.m_payload_dropped || 0;
    const propApplicable = !drop;
    const method1Badge = propApplicable
      ? `<span class="method-badge ok">✓ Zastosowalna (brak zrzutu)</span>`
      : `<span class="method-badge disabled">⚠️ Niezastosowalna (zrzut ${fmt(drop, 1)} kg)</span>`;
    const method2Badge = `<span class="method-badge ok">✓ Zbieżna (${m.iterations.length} iteracji)</span>`;

    const dualCards = `
      <div class="dual-method-grid">
        <div class="method-card ${m.mass_method !== 'iterative' ? 'active' : ''}">
          <div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
              <strong>Metoda 1: Metoda proporcji</strong>
              ${method1Badge}
            </div>
            <p style="font-size:0.85rem;color:#475569;margin:0.25rem 0">
              Formuła analityczna: <code>m₀ = m_uż / (1 − m_f/m₀ − m_e/m₀)</code>
            </p>
            <p style="font-size:0.85rem;color:#64748b;margin:0.25rem 0">
              Mnożenie bezwymiarowych ułamków fazowych M_i. Prawidłowa wyłącznie gdy cała masa płatna ląduje na lotnisku docelowym.
            </p>
          </div>
          <div style="margin-top:0.5rem;font-weight:600;font-size:0.9rem">
            ${propApplicable ? `m₀: ${fmt(m.m0, 1)} kg · m_e: ${fmt(m.m_empty, 1)} kg` : `<span style="color:#b91c1c">Niedozwolona dla misji ze zrzutem</span>`}
          </div>
        </div>
        <div class="method-card ${m.mass_method === 'iterative' ? 'active' : ''}">
          <div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
              <strong>Metoda 2: Symulacja iteracyjna (12 kroków)</strong>
              ${method2Badge}
            </div>
            <p style="font-size:0.85rem;color:#475569;margin:0.25rem 0">
              Algorytm BIPOL 1 (punkty 1–12): śledzenie masy w każdej fazie z odliczeniem Δm_drop i korektą siecznych.
            </p>
            <p style="font-size:0.85rem;color:#64748b;margin:0.25rem 0">
              Domknięcie: m_e(wymagana z misji) = m_e(korelacja statystyczna) z błędem ${fmt(m.mission_assumptions.empty_mass_residual_relative * 100, 4)}%.
            </p>
          </div>
          <div style="margin-top:0.5rem;font-weight:600;font-size:0.9rem">
            m₀: ${fmt(m.m0, 1)} kg · m_e: ${fmt(m.m_empty, 1)} kg · paliwo: ${fmt(m.m_fuel, 1)} kg
          </div>
        </div>
      </div>
    `;

    const useful = (m.m_payload || 0) + (m.m_crew || 0);
    const mEmptyPct = (m.m_empty / m.m0) * 100;
    const usefulPct = (useful / m.m0) * 100;
    const burnPct = (m.fuel_burn_kg / m.m0) * 100;
    const resPct = (m.reserve_fuel_kg / m.m0) * 100;

    const waterfallHtml = `
      <div class="mass-waterfall-box">
        <div style="display:flex;justify-content:space-between;align-items:baseline">
          <h4 style="margin:0">Struktura masy startowej m₀ = ${fmt(m.m0, 1)} kg</h4>
          <span style="font-size:0.85rem;color:#64748b">Współczynnik rezerwy: 1.06</span>
        </div>
        <div class="mass-waterfall-bar" title="Podział masy startowej">
          <div class="mass-waterfall-seg" style="width:${mEmptyPct}%;background:#3b82f6" title="Masa pusta: ${fmt(m.m_empty, 1)} kg (${fmt(mEmptyPct, 1)}%)"></div>
          <div class="mass-waterfall-seg" style="width:${usefulPct}%;background:#10b981" title="Ładunek płatny + załoga: ${fmt(useful, 1)} kg (${fmt(usefulPct, 1)}%)"></div>
          <div class="mass-waterfall-seg" style="width:${burnPct}%;background:#f97316" title="Paliwo zużyte: ${fmt(m.fuel_burn_kg, 1)} kg (${fmt(burnPct, 1)}%)"></div>
          <div class="mass-waterfall-seg" style="width:${resPct}%;background:#eab308" title="Paliwo nienaruszalne i rezerwa 6%: ${fmt(m.reserve_fuel_kg, 1)} kg (${fmt(resPct, 1)}%)"></div>
        </div>
        <div class="mass-waterfall-legend">
          <div class="mass-waterfall-legend-item"><span class="mass-waterfall-dot" style="background:#3b82f6"></span><span>Masa pusta m_e (${fmt(m.m_empty, 1)} kg · ${fmt(mEmptyPct, 1)}%)</span></div>
          <div class="mass-waterfall-legend-item"><span class="mass-waterfall-dot" style="background:#10b981"></span><span>Ładunek użyteczny (${fmt(useful, 1)} kg · ${fmt(usefulPct, 1)}%)</span></div>
          <div class="mass-waterfall-legend-item"><span class="mass-waterfall-dot" style="background:#f97316"></span><span>Paliwo na trasę (${fmt(m.fuel_burn_kg, 1)} kg · ${fmt(burnPct, 1)}%)</span></div>
          <div class="mass-waterfall-legend-item"><span class="mass-waterfall-dot" style="background:#eab308"></span><span>Rezerwa 6% (${fmt(m.reserve_fuel_kg, 1)} kg · ${fmt(resPct, 1)}%)</span></div>
          ${drop > 0 ? `<div class="mass-waterfall-legend-item" style="color:#b91c1c;font-weight:600"><span>⚡ Zrzut ładunku w locie: ${fmt(drop, 1)} kg</span></div>` : ''}
        </div>
      </div>
    `;

    const traceRows = (m.iterations || []).map(it => `
      <tr>
        <td>${it.iter}</td>
        <td>${fmt(it.m0, 1)}</td>
        <td>${fmt(it.empty_fraction, 4)}</td>
        <td>${fmt(it.m_empty_correlation, 1)}</td>
        <td>${fmt(it.m_empty_from_mission, 1)}</td>
        <td>${fmt(it.diff, 4)}</td>
        <td>${fmt(it.relative_error * 100, 4)}%</td>
      </tr>
    `).join('');

    const traceHtml = `
      <details class="iteration-trace-box">
        <summary>Ślad zbieżności iteracyjnej (metoda siecznych — ${m.iterations.length} iteracji) ▾</summary>
        <div class="trend-table-scroll" style="margin-top:0.5rem">
          <table class="b-table">
            <thead>
              <tr><th>Krok k</th><th>m₀ [kg]</th><th>m_e/m₀</th><th>m_e(korelacja) [kg]</th><th>m_e(misja) [kg]</th><th>Różnica Δ [kg]</th><th>Błąd względny ε</th></tr>
            </thead>
            <tbody>${traceRows}</tbody>
          </table>
        </div>
      </details>
    `;

    const phaseRows = m.mission_phases.map(s => `
      <tr>
        <td>${esc(s.phase)}</td>
        <td>${fmt(s.mass_start_kg, 1)}</td>
        <td>${fmt(s.fuel_burn_kg, 2)}</td>
        <td>${fmt(s.payload_drop_kg, 1)}</td>
        <td>${fmt(s.mass_end_kg, 1)}</td>
        <td>${fmt(s.fuel_fraction, 4)}</td>
      </tr>
    `).join('');

    const phasesTable = `
      <div class="trend-table-scroll">
        <table class="b-table">
          <thead>
            <tr><th>Faza misji</th><th>Przed [kg]</th><th>Paliwo [kg]</th><th>Zrzut [kg]</th><th>Po [kg]</th><th>Ułamek M_i</th></tr>
          </thead>
          <tbody>${phaseRows}</tbody>
        </table>
      </div>
    `;

    const checksHtml = `
      <h3>Kompletność projektu wg wytycznych BIPOL 1: ${r.passed}/${r.total}</h3>
      <p style="font-size:0.85rem;color:#64748b">${esc(r.basis)}</p>
      <ul>${r.checks.map(c => `<li><strong>${c.passed ? '✓' : '⚠️'} ${esc(c.label)}</strong> — ${esc(c.detail)}</li>`).join('')}</ul>
    `;

    $('bipol1Results').innerHTML = `
      <h3>${m.mass_method === 'iterative' ? 'Metoda iteracyjna (BIPOL 1 s. 4)' : 'Metoda proporcji'}</h3>
      <p><strong>Masa startowa: ${fmt(m.m0, 1)} kg · Masa pusta: ${fmt(m.m_empty, 1)} kg · Paliwo całkowite: ${fmt(m.m_fuel, 1)} kg</strong></p>
      ${dualCards}
      ${waterfallHtml}
      ${traceHtml}
      <h4 style="margin:1rem 0 0.5rem 0">Tabela faz profilu misji</h4>
      ${phasesTable}
      ${checksHtml}
    `;
  }
  window.Bipol1={collect};
  document.addEventListener('DOMContentLoaded',()=>{
    sync();
    $('bipol1Panel').addEventListener('change',event=>{if(window.isDuplicateCalculatedChange?.(event))return;visibility();$('bipol1Results').textContent='Założenia zmienione — przelicz projekt.';});
    $('bipol1Calculate').addEventListener('click',()=>performCalculation());
    $('engine_type')?.addEventListener('change',visibility);
  });
  document.addEventListener('bipol:project',()=>sync());
  document.addEventListener('bipol:results',e=>render(e.detail));
})();

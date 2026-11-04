/* Descriptive P1 analyses; all fits, source selection, suggestions and CRUD come from Python. */
(function () {
  'use strict';
  const {escape: esc, format: fmt, csv, filename} = BipolStudio;
  const $ = id => document.getElementById(id);
  const defaults = {trend_source:'all', trend_nearest_count:50, trend_engine_count:0, trend_year_min:0, trend_year_max:0,
    trend_weighting:'family', mission_phase_model:'galinski', fuel_reserve_factor:1.06, mission_ld_factor:0.94};
  let result, catalog, catalogPromise, page = 0, selected = new Set(), visible = [];
  let latestSuggestions = null;
  const suggestionLabels = {ws:'Obciążenie powierzchni skrzydła', ar:'Wydłużenie skrzydła', me_m0:'Udział masy pustej',
    pw:'Obciążenie napędu', tw:'Stosunek ciągu do ciężaru', vh:'Objętość względna usterzenia poziomego',
    v_v:'Objętość względna usterzenia pionowego', dihedral_deg:'Wznios skrzydła', b_ail_ratio:'Względna rozpiętość lotek',
    c_ail_ratio:'Względna cięciwa lotek', c_e_ratio:'Względna cięciwa steru wysokości', c_r_ratio:'Względna cięciwa steru kierunku'};
  const size = 20;

  function download(name, content, type) {
    const url = URL.createObjectURL(new Blob([content], {type}));
    const a = document.createElement('a'); a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function syncControls() {
    for (const [key, fallback] of Object.entries(defaults)) if ($(key)) $(key).value = ['mission_phase_model','mission_ld_factor'].includes(key)?fallback:formBaseParams[key]??fallback;
    if ($('trend_variable_sweep')) $('trend_variable_sweep').value = formBaseParams.variable_sweep ? 'true' : 'false';
  }

  function status(message, error = false) {
    $('trendStatus').textContent = message; $('trendStatus').classList.toggle('trend-error', error);
  }

  const fitText = fit => fit ? `n = ${fit.n} · R² = ${fmt(fit.r2,3)}` : 'Za mało zróżnicowanych danych do regresji.';

  function plot(points, fit, {title, xLabel, yLabel, forecast, project} = {}) {
    if (!points.length) return '<p class="trend-empty">Brak kompletnych obserwacji dla tej zależności.</p>';
    const all = [...points]; if (project) all.push(project); if (forecast) all.push(forecast);
    let xmin=Math.min(...all.map(p=>p.x)), xmax=Math.max(...all.map(p=>p.x));
    let ymin=Math.min(...all.map(p=>p.y)), ymax=Math.max(...all.map(p=>p.y));
    const padX=(xmax-xmin)*.06||1, padY=(ymax-ymin)*.12||.1;
    xmin-=padX;xmax+=padX;ymin-=padY;ymax+=padY;
    const W=720,H=310,l=78,r=24,t=28,b=57, X=x=>l+(x-xmin)/(xmax-xmin)*(W-l-r), Y=y=>H-b-(y-ymin)/(ymax-ymin)*(H-t-b);
    let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title>`;
    for(let i=0;i<=4;i++) {
      const x=xmin+(xmax-xmin)*i/4,y=ymin+(ymax-ymin)*i/4;
      svg+=`<path d="M${X(x)} ${t}V${H-b}M${l} ${Y(y)}H${W-r}" stroke="#dce7eb" stroke-dasharray="3 4"/><text x="${X(x)}" y="${H-b+22}" text-anchor="middle">${fmt(x,Math.abs(x)<10?2:0)}</text><text x="${l-8}" y="${Y(y)+4}" text-anchor="end">${fmt(y,Math.abs(y)<10?2:0)}</text>`;
    }
    const predict=x=>fit.kind==='power'?fit.A*Math.pow(x,fit.C):fit.intercept+fit.slope*x;
    if(fit) {
      const path=Array.from({length:65},(_,i)=>{const x=fit.x_min+(fit.x_max-fit.x_min)*i/64;return `${i?'L':'M'}${X(x)},${Y(predict(x))}`;}).join(' ');
      svg+=`<path d="${path}" stroke="#147f76" stroke-width="2.5" fill="none"/>`;
      if(forecast)svg+=`<path d="M${X(fit.x_max)},${Y(predict(fit.x_max))}L${X(forecast.x)},${Y(forecast.y)}" stroke="#a86621" stroke-width="2" stroke-dasharray="5 4"/>`;
    }
    for(const p of points) svg+=`<circle cx="${X(p.x)}" cy="${Y(p.y)}" r="4" fill="#5478a9" fill-opacity=".72"><title>${esc(p.model)}: ${fmt(p.x,2)}; ${fmt(p.y,3)}</title></circle>`;
    for(const p of [project,forecast].filter(Boolean))svg+=`<circle cx="${X(p.x)}" cy="${Y(p.y)}" r="6" stroke="white" stroke-width="2" fill="${p===project?'#b5486a':'#a86621'}"><title>${esc(p.model)}: ${fmt(p.x,2)}; ${fmt(p.y,3)}</title></circle>`;
    svg+=`<text x="${(W+l-r)/2}" y="${H-8}" text-anchor="middle">${esc(xLabel)}</text><text transform="translate(17 ${(H+t-b)/2}) rotate(-90)" text-anchor="middle">${esc(yLabel)}</text></svg>`;
    return `<div class="trend-chart">${svg}</div><p class="studio-fine-print">Niebieskie punkty: konstrukcje · zielona linia: regresja${forecast?' · brązowy: prognoza +5 lat':''}${project?' · różowy: projekt':''}. ${fitText(fit)}</p>`;
  }

  function renderPlots() {
    const a=result?.bipol_projects?.p1?.trend_analysis; if(!a)return;
    const valid=a.similar_aircraft.filter(r=>r.empty_fraction>.15&&r.empty_fraction<.95);
    const t=a.time_trends.find(t=>t.key===$('trendTimeMetric').value);
    if(t) {
      const forecast=t.fit&&t.forecast_accepted?{x:t.forecast_year,y:t.forecast,model:'Prognoza +5 lat'}:null;
      $('trendTimeChart').innerHTML=plot(t.points,t.fit,{title:`${t.label} — trend czasowy`,xLabel:a.year_basis,yLabel:`${t.label} [${t.unit}]`,forecast})+
        `<p>${t.fit?`Prognoza na ${t.forecast_year} (rok opracowania + 5 lat; ${fmt(t.extrapolation_years,0)} lat po ostatniej obserwacji): <strong>${fmt(t.forecast,3)} ${esc(t.unit)}</strong>${!t.forecast_accepted?' — nie przyjęto do doboru: '+esc(t.forecast_rejection)+'.':''}${t.provisional?' · próba poniżej 20 obserwacji.':''}`:'Wymagane co najmniej 3 kompletne daty i rozpiętość czasu ≥5 lat.'}</p>`;
    }
    $('trendMassChart').innerHTML=plot(valid.map(r=>({x:r.m0,y:r.empty_fraction,model:r.model})),a.mass_fit,
      {title:'Udział masy pustej a MTOW',xLabel:'MTOW [kg]',yLabel:'OEW / MTOW [−]',project:{x:result.mass.m0,y:a.we_wo_actual,model:'Projekt'}});
    const x=$('trendRelationX').value==='propulsion'?(result.params.engine_type==='jet'?'thrust_to_weight':'power_loading_kg_kw'):$('trendRelationX').value;
    const relation=a.relationships.find(r=>r.x_key===x&&r.y_key===$('trendRelationY').value);
    $('trendRelationChart').innerHTML=relation?plot(relation.points,relation.fit,{title:`${relation.y_label} a ${relation.x_label}`,xLabel:`${relation.x_label} [${relation.x_unit}]`,yLabel:`${relation.y_label} [${relation.y_unit}]`}):'<p>Brak porównywalnego rodzaju napędu.</p>';
  }

  // Suggestions come from the same comparison sample as the P1 analysis (BIPOL_1, s. 1–2).
  function renderTrendSuggestions(a) {
    const tbody = $('trendSuggestionsRows');
    if (!tbody) return;
    latestSuggestions = a.suggestions || {};
    const rows = [];
    for (const k of ['ws', 'ar', 'me_m0', 'pw', 'tw', 'vh', 'v_v', 'dihedral_deg', 'b_ail_ratio', 'c_ail_ratio', 'c_e_ratio', 'c_r_ratio']) {
      const s = latestSuggestions[k];
      if (!s?.provenance) continue;
      const fitInfo = s.r2 != null ? `R² = ${fmt(s.r2, 3)} (n = ${s.n})` : `n = ${s.n}`;
      const typical = s.typical_range ? `${fmt(s.typical_range[0], 2)} – ${fmt(s.typical_range[1], 2)}${s.unit !== '−' ? ' ' + s.unit : ''}` : '—';
      const canApply = s.suggested_value != null && BipolTrendInputs.supports(k);
      rows.push(`<tr>
          <td><strong>${esc(suggestionLabels[k] || s.name)}</strong></td>
          <td><code>${esc(s.symbol)}</code></td>
          <td>${s.suggested_value != null ? `<strong class="trend-suggested-value">${esc(s.suggested_value.toLocaleString('pl-PL', {maximumFractionDigits: 4}))}</strong>${s.unit !== '−' ? ` <small>${esc(s.unit)}</small>` : ''}` : '—'}</td>
          <td>${esc(typical)}</td>
          <td>${esc(s.provenance.method)}${s.equation ? `<br><code>${esc(s.equation)}</code>` : ''}</td>
          <td>${esc(fitInfo)}</td>
          <td class="trend-suggestion-actions">
            <button type="button" class="btn btn-outline btn-sm trend-why-btn" data-sugg-key="${esc(k)}" aria-expanded="false">Skąd?</button>
            ${canApply ? `<button type="button" class="btn btn-outline btn-sm apply-single-trend-btn" data-sugg-key="${esc(k)}">+ Zastosuj</button>` : BipolTrendInputs.supports(k) ? '' : '<small>Do porównania</small>'}
          </td>
        </tr>
        <tr class="trend-provenance-row" data-provenance-for="${esc(k)}" hidden><td colspan="7">${BipolTrendProvenance.render(s, {alternatives: BipolTrendInputs.supports(k)})}</td></tr>`);
    }
    tbody.innerHTML = rows.join('') || '<tr><td colspan="7">Brak dostępnych sugestii dla tej klasy.</td></tr>';
    $('trendSuggestionsStatus').textContent = `Próba: ${a.sample.description}. Prognozy w czasie na ${a.forecast_year} r. (rok opracowania + 5 lat). Przycisk „Skąd?” pokazuje dane i obliczenie.`;
  }

  function applySuggestionValues(key, value) {
    const s=latestSuggestions?.[key];
    if(!s) return false;
    // The alternative (sample mean) of eq. (1) is a fixed fraction, not the trend equation.
    const patch=BipolTrendInputs.patch(key,value??s.suggested_value,collectFormData(),currentResults?.mass?.m0,value==null?s:null);
    const previous={};
    for(const [field,fieldValue] of Object.entries(patch)) {
      previous[field]={base:formBaseParams[field],input:$(field)?.value};
      if(fieldValue===null) { delete formBaseParams[field]; continue; }
      formBaseParams[field]=fieldValue;
      if($(field)) $(field).value=fieldValue;
    }
    window.BipolDesignBasis?.sync();
    return previous;
  }
  function restoreValues(previous) {
    for(const [field,{base,input}] of Object.entries(previous)) {
      if(base===undefined) delete formBaseParams[field]; else formBaseParams[field]=base;
      if($(field)&&input!==undefined) $(field).value=input;
    }
    window.BipolDesignBasis?.sync();
  }
  // A value that makes the project infeasible (e.g. eq. (1) with C > 0) is not kept.
  async function calculateOrRestore(previous, label) {
    const before=currentResults;
    await performCalculation();
    if(currentResults!==before) return true;
    const reason=$('calculationStatus')?.textContent||'';
    restoreValues(previous);
    await performCalculation();
    $('trendSuggestionsStatus').textContent=`Nie przeniesiono: ${label}. ${reason} Przywrócono poprzednie założenia.`;
    return false;
  }
  async function applySingleSuggestion(key, value) {
    try {
      const previous=applySuggestionValues(key, value);
      if(!previous) return;
      if(!await calculateOrRestore(previous, suggestionLabels[key]||key)) return;
      const trend=currentResults?.mass?.empty_mass_trend;
      const note=key==='ws'?' Przyjęto powierzchnię S z aktualnej masy i m₀/S; nowy bilans może zmienić obciążenie.':
        key==='me_m0'&&trend?` Do bilansu masy wstawiono równanie (1): mₑ/m₀ = ${fmt(trend.A,4)}·m₀^${fmt(trend.C,4)}·${fmt(trend.k_vs,2)}. Możesz wrócić do korelacji klasy przyciskiem poniżej.`:
        key==='me_m0'?' Przyjęto stały udział masy pustej. Możesz wrócić do korelacji klasy przyciskiem poniżej.':'';
      $('trendSuggestionsStatus').textContent=`Przeniesiono: ${suggestionLabels[key]||key}.${note} Sprawdź wyniki i warunki wykonalności.`;
    } catch(error) { $('trendSuggestionsStatus').textContent=error.message; }
  }
  async function applyAllKeySuggestions() {
    const applied=[], previous={};
    try {
      for(const key of ['ar','vh','v_v','dihedral_deg','b_ail_ratio','c_ail_ratio','c_e_ratio','c_r_ratio']) {
        if(latestSuggestions?.[key]?.suggested_value==null) continue;
        for(const [field,old] of Object.entries(applySuggestionValues(key))) previous[field]??=old;
        applied.push(latestSuggestions[key].symbol);
      }
      if(!await calculateOrRestore(previous, applied.join(', '))) return;
      $('trendSuggestionsStatus').textContent=`Przeniesiono: ${applied.join(', ')||'brak wartości'}. Sprawdź wyniki wyważenia i osiągów.`;
    } catch(error) { $('trendSuggestionsStatus').textContent=error.message; }
  }

  async function loadCatalog() {
    if(!catalogPromise)catalogPromise=fetch('/api/aircraft').then(async r=>{if(!r.ok)throw new Error('Nie udało się pobrać bazy. Odśwież stronę.');return r.json();}).then(data=>{catalog=data;return data;});
    try {await catalogPromise;renderCatalog();}catch(error){$('trendCatalogStatus').textContent=error.message;catalogPromise=null;}
  }

  function filteredCatalog() {
    if(!catalog||!result)return [];
    const query=$('trendSearch').value.trim().toLocaleLowerCase('pl');
    const ids=new Set(result.bipol_projects.p1.trend_analysis.similar_aircraft.map(r=>r.id));
    const scope=$('trendCatalogScope')?.value||'current';
    const rows=scope==='all'?catalog.aircraft:catalog.aircraft.filter(r=>r.aircraft_type===result.params.aircraft_type&&r.engine_type===result.params.engine_type)
      .filter(r=>result.params.trend_source==null||result.params.trend_source==='all'||r.source_id===result.params.trend_source)
      .filter(r=>!result.params.trend_engine_count||r.n_engines===result.params.trend_engine_count)
      .filter(r=>(!result.params.trend_year_min&&!result.params.trend_year_max)||r.year!=null&&(!result.params.trend_year_min||r.year>=result.params.trend_year_min)&&(!result.params.trend_year_max||r.year<=result.params.trend_year_max));
    return rows.filter(r=>!query||`${r.model} ${r.manufacturer} ${r.family}`.toLocaleLowerCase('pl').includes(query))
      .sort((a,b)=>Number(ids.has(b.id))-Number(ids.has(a.id))||a.model.localeCompare(b.model));
  }

  function renderCatalog() {
    const all=filteredCatalog();page=Math.max(0,Math.min(page,Math.ceil(all.length/size)-1));visible=all.slice(page*size,(page+1)*size);
    $('trendCatalogStatus').textContent=`${all.length} pozycji${$('trendCatalogScope')?.value==='all'?' w całej bazie':' w bieżącej klasie i źródle'}${$('trendSearch').value?' po wyszukaniu':''}. Otwórz „Parametry / edytuj”, aby sprawdzić dane. Dobór do próby obejmuje klasę i napęd projektu.`;
    $('trendAircraftRows').innerHTML=visible.map(r=>`<tr class="${selected.has(r.id)?'trend-selected':''}">
      <td><input type="checkbox" data-aircraft-id="${esc(r.id)}" aria-label="Dodaj ${esc(r.model)} do próby" ${selected.has(r.id)?'checked':''} ${r.aircraft_type!==result.params.aircraft_type||r.engine_type!==result.params.engine_type?'disabled title="Inna klasa lub napęd niż w projekcie"':''}></td>
      <td><strong>${esc(r.model)}</strong><small>${esc(r.family||'')} · <a href="${esc(catalog.sources[r.source_id]?.url||'#')}" target="_blank" rel="noopener">${esc((r.source_id||'').toUpperCase())}</a></small><details><summary>Pochodzenie</summary><p>${esc(r.source_locator||'')}<br>${esc(r.source_references||'')}<br>${esc(r.empty_mass_definition||'')}</p>${(r.quality_notes||[]).length?`<p>${esc(r.quality_notes.join(' '))}</p>`:''}</details></td>
      <td>${r.year??'—'}</td>
      <td>${fmt(r.m0,0)}</td>
      <td>${fmt(r.me,0)}</td>
      <td>${fmt(r.s,2)}</td>
      <td>${fmt(r.ar,2)}</td>
      <td>${r.engine_type==='jet'?`${fmt(r.t_kn,1)} kN`:`${fmt(r.p_kw,1)} kW`}</td>
      <td>${r.prop_diameter_m!=null?`${fmt(r.prop_diameter_m,2)} m`:'—'}</td>
      <td>${r.v_cruise_kmh!=null?`${fmt(r.v_cruise_kmh,0)} km/h`:r.cruise_mach!=null?`${fmt(r.cruise_mach,3)} Ma`:'—'}</td>
      <td style="white-space:nowrap;">
        <button type="button" class="btn btn-outline btn-sm edit-ac-btn" data-id="${esc(r.id)}" style="padding:7px 9px; font-size:0.78rem; margin-right:4px;">Parametry / edytuj</button>
        <button type="button" class="btn btn-outline btn-sm delete-ac-btn" data-id="${esc(r.id)}" style="padding:2px 7px; font-size:0.75rem; color:#ef4444; border-color:#fca5a5;">🗑️ Usuń</button>
      </td>
    </tr>`).join('')||'<tr><td colspan="11">Brak konstrukcji w tej klasie i źródle. Nie zastępujemy ich samolotami o innym przeznaczeniu.</td></tr>';
    $('trendPage').textContent=all.length?`${page+1} / ${Math.ceil(all.length/size)}`:'0 / 0';
    $('trendPrev').disabled=page===0;$('trendNext').disabled=(page+1)*size>=all.length;
    $('trendSelectionStatus').textContent=`Zaznaczono: ${selected.size}`;
  }

  async function deleteAircraft(id) {
    const ac = catalog?.aircraft?.find(r => r.id === id);
    const name = ac ? ac.model : id;
    if (!confirm(`Czy na pewno chcesz usunąć samolot „${name}” z bazy odniesienia? Zmiana jest trwała.`)) {
      return;
    }
    try {
      const resp = await fetch(`/api/aircraft/${encodeURIComponent(id)}`, {method: 'DELETE'});
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.message || 'Nie udało się usunąć samolotu.');
      catalogPromise = null;
      selected.delete(id);
      if(Array.isArray(formBaseParams.trend_aircraft_ids)){
        formBaseParams.trend_aircraft_ids=formBaseParams.trend_aircraft_ids.filter(key=>key!==id);
        if(!formBaseParams.trend_aircraft_ids.length)delete formBaseParams.trend_aircraft_ids;
      }
      await loadCatalog();
      if (typeof performCalculation === 'function') await performCalculation();
      status(`Usunięto samolot „${name}” z bazy.`);
    } catch (err) {
      alert(`Błąd usuwania: ${err.message}`);
    }
  }

  function render(res) {
    result=res;
    const a=res.bipol_projects.p1.trend_analysis,p=res.bipol_projects.p1.preliminary;
    selected=new Set(a.similar_aircraft.map(r=>r.id));
    status('Analiza aktualna.');
    const review=res.instructor_review;
    if(review&&$('instructorReview'))$('instructorReview').innerHTML=`<details><summary>Wytyczne prowadzącego: ${review.passed}/${review.total} sprawdzeń</summary><ul>${review.checks.map(c=>`<li><strong>${c.passed?'Spełnione':'Do uzupełnienia'}: ${esc(c.label)}</strong> — ${esc(c.detail)}</li>`).join('')}</ul><p>${review.manual.map(esc).join(' ')}</p></details>`;
    if($('trendReportPlan'))$('trendReportPlan').innerHTML=a.report_charts.map(c=>`<li>${esc(c.label)} — n=${c.n}${c.n<8?' · uzupełnij dane':''}</li>`).join('');
    $('p1_we_trend').textContent=fmt(a.we_wo_trend,3);$('p1_we_actual').textContent=fmt(a.we_wo_actual,3);
    $('p1_trend_summary').textContent=`Baza: ${a.database_total} pozycji · próba: ${a.selected_n} wariantów / ${a.families_n} rodzin · regresja masowa: n=${a.mass_fit?.n??0}. ${a.warnings[0]||''}`;
    $('trendClassDescription').textContent=`${a.class_label} · napęd ${res.params.engine_type==='jet'?'odrzutowy':res.params.engine_type==='none'?'bez napędu':'śmigłowy'} · masa projektu ${fmt(res.mass.m0,1)} kg.`;
    $('trendSummary').innerHTML=[['Konstrukcji w bazie',a.database_total],['Wariantów w próbie',a.selected_n],['Rodzin w próbie',a.families_n],['Pełnych par masowych',a.mass_fit?.n??0]].map(([label,value])=>`<div><small>${esc(label)}</small><strong>${value}</strong></div>`).join('');
    $('trendWarnings').innerHTML=a.warnings.map(w=>`<p>${esc(w)}</p>`).join('');
    const tp=a.two_point;
    $('trendMassStats').innerHTML=`<p class="studio-equation">OEW / MTOW = ${fmt(a.reg_A,4)} · m₀<sup>${fmt(a.reg_C,4)}</sup> · ${fmt(a.k_vs,2)}</p><p>${fitText(a.mass_fit)} · projekt ${fmt(a.we_wo_actual,3)} · trend ${fmt(a.we_wo_trend,3)}</p>${tp?`<p>Dwa punkty linii trendu: (${fmt(tp.x1,0)} kg; ${fmt(tp.y1,4)}) i (${fmt(tp.x2,0)} kg; ${fmt(tp.y2,4)}) → C = log(y₁/y₂)/log(x₁/x₂) = ${fmt(tp.C,4)}, A = y₁/x₁<sup>C</sup> = ${fmt(tp.A,4)}.</p>`:''}<p>${esc(a.method)} Model masy pustej w bilansie: ${res.mass.empty_mass_model==='trend'?'równanie (1) z aktualnej próby':res.mass.empty_mass_model==='bipol1_trend'?'współczynniki wskazane przez autora':res.mass.empty_mass_model==='fixed_fraction'?'stały udział':res.mass.empty_mass_model==='class_correlation'?'korelacja klasy':'własny model autora'}.</p>`;
    const metric=$('trendTimeMetric').value;
    // <option> nie składa indeksów: lista pomija końcowy symbol (V_H, c_e/c_H), wykres pokazuje go złożonego.
    $('trendTimeMetric').innerHTML=a.time_trends.map(t=>`<option value="${esc(t.key)}">${esc(t.label.replace(/\s+\S*_\S*$/,''))} [${esc(t.unit)}] · n=${t.available_n}</option>`).join('');
    $('trendTimeMetric').value=metric||'ar';
    const labels={empty_fraction:'OEW / MTOW [−]',ar:'Wydłużenie AR [−]',wing_loading_kg_m2:'Obciążenie powierzchni [kg/m²]',h_tail_area:'Powierzchnia usterzenia poziomego [m²]',v_tail_area:'Powierzchnia usterzenia pionowego [m²]'};
    const required=new Set(['v_h','v_v','empty_fraction','aileron_span_fraction','aileron_chord_ratio','elevator_chord_ratio','rudder_chord_ratio','dihedral_deg']);
    $('trendAverages').innerHTML='<div class="trend-table-scroll"><table class="b-table"><thead><tr><th>Parametr</th><th>Średnia</th><th>n</th></tr></thead><tbody>'+[...required].map(key=>{const value=a.averages[key];return `<tr><td>${esc(labels[key]||a.time_trends.find(t=>t.key===key)?.label||key)}</td><td>${value.n?fmt(value.mean,key==='v_v'?4:3):'brak danych'}</td><td>${value.n}</td></tr>`;}).join('')+'</tbody></table></div>';
    const turn=p.turn_45,mission=res.mass.mission_assumptions;
    $('trendPreliminary').innerHTML=`<p><strong>Kmax = ${fmt(p.k_max,2)}</strong> · Cx₀ z odwróconego wzoru = ${fmt(p.cx0_from_kmax,4)} · wydłużenie omywane AR/(Swet/S) = ${fmt(p.wetted_aspect_ratio,2)}.</p><div class="trend-table-scroll"><table class="b-table"><thead><tr><th>Warunek analityczny</th><th>Cz</th><th>K</th><th>V TAS [km/h]</th><th>Granica Czmax</th></tr></thead><tbody>${p.operating_points.map(v=>`<tr><td>${esc(v.label)}<small>${esc(v.formula)}</small></td><td>${fmt(v.cl,3)}</td><td>${fmt(v.ld,2)}</td><td>${fmt(v.v_tas_kmh,1)}</td><td>${v.below_stall_limit?'W zakresie':'Punkt nieosiągalny'}</td></tr>`).join('')}</tbody></table></div><p>Wznoszenie: <code>${esc(p.climb.formula)}</code> → minimum T/W = ${fmt(p.climb.tw_lower_bound,4)}.</p><p>Zakręt poziomy 45° przy prędkości przelotowej: n = ${fmt(turn.load_factor,3)}, r = ${fmt(turn.radius_m,0)} m, ω = ${fmt(turn.rate_deg_s,2)} °/s. Wymagany T/W = ${fmt(turn.tw_required,4)}, Cz = ${fmt(turn.cl_required,3)} ${turn.cl_required>res.aerodynamics.cz_max_clean?'— powyżej Czmax; zakręt nieosiągalny.':''}</p><p>Bilans misji: K przelotu = ${fmt(res.mass.ld_cruise_used,2)}, współczynnik rezerwy = ${fmt(mission.reserve_factor,2)}; względna reszta równania masowego = ${fmt(mission.mass_residual_relative*100,5)}% (cel PDF: ≤0,1%).</p><p class="studio-fine-print">${esc(p.limitations)}</p>`;
    $('trendSources').innerHTML=Object.entries(a.sources).map(([id,s])=>`<p>${s.url?`<a href="${esc(s.url)}" target="_blank" rel="noopener"><strong>${esc(s.name)}</strong></a>`:`<strong>${esc(s.name)}</strong>`}<br>${esc(s.citation)}<br>${s.attribution?esc(s.attribution)+'<br>':''}<a href="/download/aircraft/${id}/data">Dane JSON</a> · <a href="/download/aircraft/${id}/license">Licencja ${esc(s.license)}</a></p>`).join('')+`<p class="studio-fine-print">${esc(a.limitations)}</p>`;
    renderPlots();
    loadCatalog();
    renderTrendSuggestions(a);
  }

  function exportRows() {
    const a=result.bipol_projects.p1.trend_analysis;
    const rows=[['Model','Rodzina','Klasa',a.year_basis,'MTOW [kg]','OEW [kg]','S [m²]','b [m]','AR','Moc łączna [kW]','Ciąg łączny [kN]','V przelotowa [km/h]','Mach przelotu','Zasięg [km]','m₀/S [kg/m²]','m₀/P [kg/kW]','P/m₀ [kW/kg]','Wznoszenie [m/s]','Całkowity start wg źródła [m]','Całkowite lądowanie wg źródła [m]','Źródło','Lokalizacja danych','Licencja','Definicja masy','Atrybucja']];
    for(const r of a.similar_aircraft)rows.push([r.model,r.family,r.aircraft_type,r.year,r.m0,r.me,r.s,r.b,r.ar,r.p_kw,r.t_kn,r.v_cruise_kmh,r.cruise_mach,r.range_km,r.wing_loading_kg_m2,r.power_loading_kg_kw,r.specific_power_kw_kg,r.climb_rate_ms,r.takeoff_distance_m,r.landing_distance_m,a.sources[r.source_id].url,r.source_locator,a.sources[r.source_id].license,r.empty_mass_definition,a.sources[r.source_id].attribution||a.sources[r.source_id].citation]);
    return rows;
  }

  document.addEventListener('bipol:project',()=>{syncControls();status('Projekt zmieniony — oczekiwanie na nową analizę.');});
  document.addEventListener('bipol:calculating',()=>status('Dane wymagają przeliczenia lub trwają obliczenia.'));
  document.addEventListener('bipol:results',event=>render(event.detail));

  document.addEventListener('DOMContentLoaded',()=>{
    syncControls();if(currentResults)render(currentResults);
    document.querySelectorAll('[data-analysis-param]').forEach(input=>input.addEventListener('change',event=>{
      if(window.isDuplicateCalculatedChange?.(event))return;
      if(input.id.startsWith('trend_'))delete formBaseParams.trend_aircraft_ids;
      document.dispatchEvent(new CustomEvent('bipol:calculating'));status('Założenia zmienione — użyj „Przelicz analizę”.');
    }));
    for(const id of ['trendRecalculate','trendMissionApply'])$(id).addEventListener('click',()=>performCalculation());
    $('trendAutomatic').addEventListener('click',()=>{delete formBaseParams.trend_aircraft_ids;performCalculation();});
    $('trendApplySelection').addEventListener('click',()=>{
      // Search only affects visibility; keep all checked aircraft in this class.
      const ids=[...selected].filter(id=>catalog.aircraft.some(r=>r.id===id&&r.aircraft_type===result.params.aircraft_type&&r.engine_type===result.params.engine_type));
      if(!ids.length){status('Zaznacz przynajmniej jedną konstrukcję.',true);return;}
      formBaseParams.trend_aircraft_ids=ids;$('trend_nearest_count').value='0';performCalculation();
    });
    $('trendSearch').addEventListener('input',()=>{page=0;renderCatalog();});
    $('trendCatalogScope').addEventListener('change',()=>{page=0;renderCatalog();});
    $('trendOpenDatabase').addEventListener('click',()=>{
      $('trendSelectionPanel-tab')?.click();
      $('trendSearch').focus();$('trendSearch').scrollIntoView({block:'center'});
    });
    document.addEventListener('bipol:catalog-updated',async event=>{
      catalogPromise=null;await loadCatalog();
      await performCalculation();
      status(`Zapisano „${event.detail.model}” we wspólnej lokalnej bazie. Analiza została odświeżona.`);
    });
    
    // Obsługa tabeli katalogu i przycisków Edytuj / Usuń
    $('trendAircraftRows').addEventListener('change',event=>{
      const id=event.target.dataset.aircraftId;if(!id)return;
      if(event.target.checked)selected.add(id);else selected.delete(id);
      $('trendSelectionStatus').textContent=`Zaznaczono: ${selected.size}`;
    });
    $('trendAircraftRows').addEventListener('click',event=>{
      const editBtn = event.target.closest('.edit-ac-btn');
      if (editBtn) {
        const id = editBtn.dataset.id;
        const ac = catalog?.aircraft?.find(r => r.id === id);
        if (ac) BipolAircraftEditor.open(ac, catalog.sources);
        return;
      }
      const delBtn = event.target.closest('.delete-ac-btn');
      if (delBtn) {
        deleteAircraft(delBtn.dataset.id);
        return;
      }
    });

    // Obsługa panelu sugestii parametrów
    $('btnApplyAllTrendSuggestions')?.addEventListener('click', applyAllKeySuggestions);
    $('trendResetMassModel')?.addEventListener('click',async()=>{
      formBaseParams.empty_mass_model='trend';
      if($('empty_mass_model'))$('empty_mass_model').value='trend';
      await performCalculation();
      $('trendSuggestionsStatus').textContent='Masa pusta: równanie (1) z linii trendu próby porównawczej.';
    });
    $('trendSuggestionsRows')?.addEventListener('click', event => {
      const why = event.target.closest('.trend-why-btn');
      if (why) {
        const row = $('trendSuggestionsRows').querySelector(`[data-provenance-for="${why.dataset.suggKey}"]`);
        row.hidden = !row.hidden; why.setAttribute('aria-expanded', String(!row.hidden));
        return;
      }
      const alternative = event.target.closest('[data-trend-alternative]');
      if (alternative) { applySingleSuggestion(alternative.dataset.trendAlternative, Number(alternative.dataset.value)); return; }
      const btn = event.target.closest('.apply-single-trend-btn');
      if (btn) applySingleSuggestion(btn.dataset.suggKey);
    });
    $('trend_variable_sweep')?.addEventListener('change', event => {
      formBaseParams.variable_sweep = event.target.value === 'true';
      document.dispatchEvent(new CustomEvent('bipol:calculating'));
      status('Założenia zmienione — użyj „Przelicz analizę”.');
    });

    // Obsługa Modala dodawania/edycji samolotu
    $('btnAddAircraftBtn')?.addEventListener('click', () => BipolAircraftEditor.open(null, catalog?.sources));

    $('trendSelectVisible').addEventListener('click',()=>{visible.filter(r=>r.aircraft_type===result.params.aircraft_type&&r.engine_type===result.params.engine_type).forEach(r=>selected.add(r.id));renderCatalog();});
    $('trendClearSelection').addEventListener('click',()=>{selected.clear();renderCatalog();});
    $('trendPrev').addEventListener('click',()=>{page--;renderCatalog();});$('trendNext').addEventListener('click',()=>{page++;renderCatalog();});
    for(const id of ['trendTimeMetric','trendRelationX','trendRelationY'])$(id).addEventListener('change',renderPlots);
    
    $('trendObservationTemplate').addEventListener('click',()=>{
      if(!result)return;
      const saved=new Map((result.params.trend_observations||[]).map(r=>[r.id,r]));
      const fields=['id','model','climb_rate_ms','takeoff_distance_m','landing_distance_m','year','source'];
      const rows=[fields,...result.bipol_projects.p1.trend_analysis.similar_aircraft.map(r=>fields.map(k=>k==='id'||k==='model'?r[k]:saved.get(r.id)?.[k]??''))];
      download('uzupelnienia-proby.csv',csv(rows),'text/csv;charset=utf-8');
    });
    $('trendObservationFile').addEventListener('change',async event=>{
      const file=event.target.files[0];if(!file)return;
      const notice=$('trendObservationStatus');
      try {
        if(file.size>1000000)throw new Error('Plik może mieć maksymalnie 1 MB.');
        const body=new FormData();body.append('file',file);
        const response=await fetch('/api/trends/import',{method:'POST',body});
        const data=await response.json();if(!response.ok)throw new Error(data.error);
        const merged=new Map((formBaseParams.trend_observations||[]).map(r=>[r.id,r]));
        data.observations.forEach(r=>merged.set(r.id,{...merged.get(r.id),...r}));
        formBaseParams.trend_observations=[...merged.values()];
        await performCalculation();
        notice.textContent=`Wczytano ${data.observations.length} wierszy. Uzupełnienia zapisują się z projektem.`;
      } catch(error){notice.textContent=error.message;}
      event.target.value='';
    });
    $('trendObservationClear').addEventListener('click',()=>{
      delete formBaseParams.trend_observations;performCalculation();
      $('trendObservationStatus').textContent='Przywrócono dane katalogowe.';
    });
    $('trendExportCsv').addEventListener('click',async()=>{await performCalculation();if(currentResults&&$('openReportBtn').dataset.resultsStale==='false'){result=currentResults;download(`${filename(result.params.name)}-proba-trendow.csv`,csv(exportRows()),'text/csv;charset=utf-8');}});
    $('trendExportJson').addEventListener('click',async()=>{await performCalculation();if(currentResults&&$('openReportBtn').dataset.resultsStale==='false')download(`${filename(currentResults.params.name)}-analiza-trendow.json`,JSON.stringify({params:currentResults.params,analysis:currentResults.bipol_projects.p1},null,2),'application/json');});
  });
})();

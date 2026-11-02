(function () {
  'use strict';
  const $=id=>document.getElementById(id);
  const defaults={mass_method:'auto',empty_mass_model:'class_correlation',mass_initial_guess:5000,
    payload_drop_kg:0,return_range_km:0,max_power_time_min:0,climb_fraction_mode:'auto',
    climb_start_altitude_m:0,preliminary_polar_mode:'input',sketch_swet_ratio:4,
    raymer_family:'prop_fixed',raymer_kmax:15,cx0_reference_class:'single_fixed',
    empty_mass_a:.95,empty_mass_c:-.05,mass_point_x1:1000,mass_point_x2:2000,
    mass_point_y1:.6,mass_point_y2:.55,empty_mass_fraction:.55,
    corke_start_ordinate:.99,corke_end_ordinate:.98,trend_year_basis:'certification'};
  function visibility() {
    const model=$('empty_mass_model').value;
    document.querySelectorAll('[data-bipol1-group]').forEach(el=>el.hidden=el.dataset.bipol1Group!==model);
    document.querySelector('[data-bipol1-task]').hidden=!(Number($('max_power_time_min').value)>0);
    document.querySelector('[data-bipol1-corke-reading]').hidden=$('climb_fraction_mode').value!=='reading';
    document.querySelector('[data-bipol1-raymer-reading]').hidden=$('preliminary_polar_mode').value!=='reading';
    const jet=($('engine_type')?.value||formBaseParams.engine_type)==='jet';
    document.querySelector('[data-bipol1-prop]').hidden=jet;
    document.querySelector('[data-bipol1-jet]').hidden=!jet;
    $('bipol1SfcUnit').textContent=jet?'[1/h, cT·g]':'[g/(kW·h)]';
  }
  function sync(p=formBaseParams) {
    document.querySelectorAll('[data-bipol1]').forEach(el=>el.value=p[el.id]??defaults[el.id]??'');
    if(!p.raymer_family) $('raymer_family').value=p.engine_type==='none'?'glider':p.engine_type==='jet'?'jet':p.retractable_gear?'prop_retractable':'prop_fixed';
    if(!p.cx0_reference_class) $('cx0_reference_class').value=['glider','motoglider'].includes(p.aircraft_type)?'motoglider':p.aircraft_type==='jet_transport'?'transport':p.n_engines>=2?'small_twin':p.retractable_gear?'single_retractable':'single_fixed';
    visibility();
  }
  function collect(data) {
    visibility();
    for(const el of document.querySelectorAll('[data-bipol1]')) {
      if(el.closest('[hidden]')) continue;
      if(!el.value.trim()) {delete data[el.id];continue;}
      if(!el.checkValidity()) throw Error(`Sprawdź: ${el.closest('label')?.textContent.trim()||el.id}. ${el.validationMessage}`);
      data[el.id]=el.type==='number'?Number(el.value):el.value;
    }
    if(data.empty_mass_model!=='class_correlation') {
      delete data.empty_mass_trend_A;delete data.empty_mass_trend_C;
    }
    if(!['fixed_fraction','class_correlation'].includes(data.empty_mass_model)) delete data.empty_mass_fraction;
    delete data.outbound_range_km;
    return data;
  }
  function render(res) {
    const {escape:esc,format:fmt}=BipolStudio,m=res.mass,r=res.bipol1_review;
    if(!r)return;
    sync(res.params);
    const rows=m.mission_phases.map(s=>`<tr><td>${esc(s.phase)}</td><td>${fmt(s.mass_start_kg,1)}</td><td>${fmt(s.fuel_burn_kg,2)}</td><td>${fmt(s.payload_drop_kg,1)}</td><td>${fmt(s.mass_end_kg,1)}</td></tr>`).join('');
    $('bipol1Results').innerHTML=`<h3>${m.mass_method==='iterative'?'Metoda iteracyjna':'Metoda proporcji'}</h3><p><strong>Masa startowa ${fmt(m.m0,1)} kg · masa pusta ${fmt(m.m_empty,1)} kg</strong></p><p>Paliwo zużyte ${fmt(m.fuel_burn_kg,2)} kg; rezerwa i paliwo nieużywalne ${fmt(m.reserve_fuel_kg,2)} kg. ${m.iterations.length} iteracji; różnica ocen masy pustej ${fmt(m.mission_assumptions.empty_mass_residual_relative*100,6)}% (maks. 0,1%).</p><div class="trend-table-scroll"><table class="b-table"><thead><tr><th>Faza</th><th>Przed [kg]</th><th>Paliwo [kg]</th><th>Zrzut [kg]</th><th>Po [kg]</th></tr></thead><tbody>${rows}</tbody></table></div><h3>Kompletność projektu: ${r.passed}/${r.total}</h3><p>${esc(r.basis)}</p><ul>${r.checks.map(c=>`<li><strong>${c.passed?'Spełnione':'Do uzupełnienia'}: ${esc(c.label)}</strong> — ${esc(c.detail)}</li>`).join('')}</ul>`;
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

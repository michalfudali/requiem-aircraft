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
  const esc = s => window.BipolStudio.escape(String(s ?? ''));
  const fmt = (v, d=3) => Number(v).toLocaleString('pl-PL',{maximumFractionDigits:d});
  const kind = () => $('engine_type')?.value || formBaseParams.engine_type;
  const chosen = () => engines.find(e=>e.id===$('engine_model_id')?.value);
  function points(preferred) {
    const record = chosen();
    const select = $('engine_fuel_point');
    const old = preferred ?? select.value;
    select.innerHTML = (record?.points || []).map(p=>`<option value="${esc(p.id)}">${esc(p.conditions)} — ${fmt(p.value)} ${esc(p.unit)}</option>`).join('');
    if (record?.points.some(p=>p.id===old)) select.value=old;
    visibility();
  }
  function visibility() {
    const mode=$('engine_fuel_mode').value, jet=kind()==='jet', none=kind()==='none';
    $('engineFuelPanel').hidden=none;
    const point=chosen()?.points.find(p=>p.id===$('engine_fuel_point').value);
    for (const el of document.querySelectorAll('[data-engine-catalog]')) el.hidden=mode!=='catalog';
    for (const el of document.querySelectorAll('[data-engine-custom]')) el.hidden=mode!=='custom';
    for (const el of document.querySelectorAll('[data-engine-shaft]')) el.hidden=jet;
    for (const el of document.querySelectorAll('[data-engine-jet]')) el.hidden=!jet;
    for (const el of document.querySelectorAll('[data-engine-density]')) el.hidden=!['l/h','US gal/h'].includes(point?.unit);
    for(const el of document.querySelectorAll('[data-engine-field]')) el.disabled=none||!!el.closest('[hidden]');
    if($('sfc')) $('sfc').readOnly=none||mode==='catalog'||mode==='custom';
    $('engineCustomSfcUnit').textContent=jet?'cT·g [1/h]':'[g/(kW·h)]';
    if($('engine_power_kw')) $('engine_power_kw').readOnly=none||mode==='catalog'||mode==='custom';
  }
  function sync(params=formBaseParams) {
    if(!$('engineFuelPanel')) return;
    $('engine_fuel_mode').value=params.engine_fuel_mode||'unselected';
    const previous=params.engine_model_id||'';
    $('engine_model_id').innerHTML='<option value="">Wybierz model</option>'+engines.filter(e=>e.engine_type===kind()).map(e=>`<option value="${esc(e.id)}">${esc(e.model)}</option>`).join('');
    $('engine_model_id').value=previous;
    for(const key of keys.filter(k=>!['engine_fuel_mode','engine_model_id','engine_fuel_point'].includes(k))) {
      $(key).value=params[key]??(key==='fuel_density_kg_l' ? .72 : key.includes('_power_')||key.includes('_thrust_')?0:'');
    }
    $('engine_custom_sfc').value=params.sfc??(kind()==='jet' ? .62 : 265);
    points(params.engine_fuel_point);
    visibility();
  }
  function collect(data) {
    if(!$('engineFuelPanel'))return data;
    delete data._engine_fuel; delete data.engine_static_thrust_kn;
    for(const key of keys) {
      const el=$(key);
      if(el.disabled||!el.value.trim()) {delete data[key];continue;}
      if(!el.checkValidity()) throw Error(`Dane silnika: ${el.closest('label').textContent.trim()}. ${el.validationMessage}`);
      data[key]=el.type==='number'?Number(el.value):el.value;
    }
    if(data.engine_fuel_mode==='custom')data.sfc=data.engine_custom_sfc;
    delete data.engine_custom_sfc;
    return data;
  }
  function render(result) {
    lastResult=result;
    if(!$('engineFuelPanel'))return;
    sync(result.params);
    const ef=result.engine_selection;
    if(!ef)return;
    if(ef.supported&&ef.status!=='not_applicable') {
      $('sfc').value=result.params.sfc;
      if(result.params.engine_type==='prop')$('engine_power_kw').value=result.params.engine_power_kw;
      if($('power_input_mode')&&result.params.engine_type==='prop')$('power_input_mode').value='fixed';
      $('engineFuelStatus').innerHTML=`<p><strong>${ef.count} × ${esc(ef.model)}</strong>; SFC w obliczeniach: <strong>${fmt(ef.sfc,4)} ${esc(ef.unit)}</strong>.</p><p>Punkt źródłowy: <strong>${fmt(ef.point.value,4)} ${esc(ef.point.unit)}</strong>${ef.point.power_kw?` przy ${fmt(ef.point.power_kw)} kW na silnik`:""}; ${esc(ef.point.conditions)}.</p><p>Dostępne łącznie: <strong>${fmt(ef.installed_total)} ${esc(ef.rating_unit)}</strong>; wymagane: ${fmt(ef.required_total)} ${esc(ef.rating_unit)}. ${esc(ef.rating_note)}</p><p>${esc(ef.source)} ${esc(ef.locator)}${ef.source_url?` · <a href="${esc(ef.source_url)}" target="_blank" rel="noopener">Dokument producenta</a>`:''}</p><p>${esc(ef.notes.join(' '))}</p><p>${ef.adequate?'Moc/ciąg wystarcza według bieżącego doboru.':'Moc/ciąg nie wystarcza — wybierz inną propozycję.'}</p>`;
    } else $('engineFuelStatus').textContent=ef.notes?.join(' ')||'Lot bez napędu.';
    $('engineFuelCandidates').innerHTML=ef.candidates?.length?`<table class="b-table"><thead><tr><th>Silnik</th><th>Moc/ciąg łącznie</th><th>Źródłowy punkt paliwowy</th><th>Dobór</th></tr></thead><tbody>${ef.candidates.map(e=>`<tr><td>${esc(e.model)}</td><td>${fmt(e.total_rating)} ${esc(ef.rating_unit)}</td><td>${fmt(e.points[0].value)} ${esc(e.points[0].unit)}<br>${esc(e.points[0].conditions)}</td><td><button type="button" class="btn btn-outline btn-sm" data-engine-pick="${esc(e.id)}">${e.adequate?'Przyjmij':'Sprawdź — za mała moc/ciąg'}</button></td></tr>`).join('')}</tbody></table>`:'Brak udokumentowanej propozycji tej klasy w lokalnym katalogu. Podaj rzeczywisty model i źródło przez „Inny rzeczywisty silnik”.';
  }
  window.BipolEngineFuel={collect,ready};
  document.addEventListener('DOMContentLoaded',async()=>{
    $('engineFuelPanel').addEventListener('input',()=>{
      $('engineFuelStatus').textContent='Dane silnika zmienione — przyjmij je i przelicz projekt.';
    });
    $('engine_fuel_mode').addEventListener('change',visibility);
    $('engine_model_id').addEventListener('change',()=>points(''));
    $('engine_fuel_point').addEventListener('change',visibility);
    $('applyEngineFuel').addEventListener('click',()=>performCalculation());
    $('engineFuelCandidates').addEventListener('click',event=>{
      const button=event.target.closest('[data-engine-pick]');if(!button)return;
      $('engine_fuel_mode').value='catalog';$('engine_model_id').value=button.dataset.enginePick;points('');visibility();performCalculation();
    });
    $('engine_type')?.addEventListener('change',()=>{
      if(chosen()?.engine_type!==kind()) {
        $('engine_fuel_mode').value='unselected';
        $('engine_model_id').innerHTML='<option value="">Wybierz model</option>'+engines.filter(e=>e.engine_type===kind()).map(e=>`<option value="${esc(e.id)}">${esc(e.model)}</option>`).join('');
        points('');
      }
      visibility();
    });
    sync();
    try {const response=await fetch('/api/engines');if(!response.ok)throw Error('Brak katalogu silników.');engines=(await response.json()).engines;
      if(lastResult)render(lastResult);else sync();
    } catch(error){$('engineFuelStatus').textContent=error.message;}
    finally { resolveReady(); }
  });
  document.addEventListener('bipol:project',()=>sync());
  document.addEventListener('bipol:results',event=>render(event.detail));
})();

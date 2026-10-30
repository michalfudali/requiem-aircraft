/* Lokalny edytor wspólnego katalogu; brak danych pozostaje pustym polem. */
(function (root) {
  'use strict';
  const groups = ['Identyfikacja', 'Masy i skrzydło', 'Napęd', 'Osiągi', 'Usterzenie i stery', 'Źródło danych'];
  const field = (key,label,group,type='number',options={}) => ({key,label,group,type,...options});
  const distances = [['unknown','Nieokreślona'],['ground_roll','Rozbieg / dobieg'],['15m','Całkowita do / znad 15 m'],['50ft','Całkowita do / znad 50 ft'],['field_length','Długość pola wg źródła']];
  const fields = [
    field('model','Model *',0,'text',{required:true}), field('manufacturer','Producent *',0,'text'),
    field('family','Rodzina konstrukcji',0,'text'), field('year','Rok według źródła',0,'number',{min:1900,max:2100,step:1}),
    field('year_basis','Znaczenie daty',0,'select',{options:[['certification','Certyfikacja wariantu'],['production','Produkcja (BIPOL_1)']]}),
    field('aircraft_type','Klasa konstrukcyjna *',0,'select',{options:[['piston_ga','Tłokowy GA'],['turboprop_regional','Turbośmigłowy'],['jet_business','Odrzutowiec biznesowy'],['jet_transport','Odrzutowiec transportowy'],['glider','Szybowiec'],['motoglider','Motoszybowiec'],['uav','Bezzałogowy']]}),
    field('m0','Maksymalna masa startowa [kg] *',1,'number',{required:true,min:0.001}),
    field('me','Masa pusta OEW [kg]',1), field('s','Powierzchnia skrzydła [m²]',1), field('b','Rozpiętość [m]',1),
    field('engine_type','Rodzaj napędu *',2,'select',{options:[['prop','Śmigłowy (tłokowy / turbośmigłowy)'],['jet','Odrzutowy'],['none','Bez napędu']]}),
    field('n_engines','Liczba silników',2,'number',{min:0,max:8,step:1}),
    field('p_kw','Łączna moc silników [kW]',2), field('t_kn','Łączny ciąg silników [kN]',2), field('prop_diameter_m','Średnica śmigła [m]',2),
    field('v_cruise_kmh','Prędkość przelotowa [km/h]',3), field('cruise_mach','Liczba Macha przelotu',3),
    field('v_stall_kmh','Prędkość przeciągnięcia [km/h]',3), field('range_km','Zasięg [km]',3,'number',{min:0}),
    field('climb_rate_ms','Wznoszenie [m/s]',3,'number',{min:0,max:150}), field('ld_max','Doskonałość maksymalna',3),
    field('takeoff_m','Długość startu [m]',3), field('takeoff_basis','Definicja długości startu',3,'select',{options:distances}),
    field('landing_m','Długość lądowania [m]',3), field('landing_basis','Definicja długości lądowania',3,'select',{options:distances}),
    field('v_h','Cecha objętościowa V_H',4,'number',{max:2}), field('v_v','Cecha objętościowa V_V',4,'number',{max:0.5}),
    field('dihedral_deg','Wznios skrzydła [°]',4,'number',{min:-15,max:20}),
    field('aileron_span_fraction','Udział rozpiętości lotek',4,'number',{max:1}),
    field('aileron_chord_ratio','Względna cięciwa lotki',4,'number',{max:1}),
    field('elevator_chord_ratio','Względna cięciwa steru wysokości',4,'number',{max:1}),
    field('rudder_chord_ratio','Względna cięciwa steru kierunku',4,'number',{max:1}),
    field('source_locator','Dokument / strona / lokalizacja',5,'text'),
    field('source_references','Źródło i warunki pomiaru *',5,'textarea',{required:true}),
    field('empty_mass_definition','Definicja masy pustej',5,'textarea')
  ];

  function payload(values, original = {}) {
    const data = {};
    for (const spec of fields) {
      const raw = values[spec.key];
      if (spec.type === 'number') {
        if (raw === '' || raw == null) { data[spec.key] = null; continue; }
        const value = Number(raw);
        if (!Number.isFinite(value)) throw new Error(`${spec.label}: podaj skończoną liczbę.`);
        data[spec.key] = value;
      } else data[spec.key] = raw == null || String(raw).trim() === '' ? null : String(raw).trim();
    }
    for (const key of ['p_kw','prop_diameter_m']) if (data.engine_type !== 'prop') data[key] = null;
    if (data.engine_type !== 'jet') data.t_kn = null;
    if (data.engine_type === 'none') data.n_engines = 0;
    if (!data.family) data.family = data.model;
    data.source_id = original.source_id || 'user';
    return data;
  }

  function init() {
    const $ = id => document.getElementById(id), dialog = $('trendAircraftModal');
    if (!dialog) return;
    const {escape:esc,format:fmt} = root.BipolStudio;
    let original = null, opener = null, busy = false, baseline = '', openSequence = 0;
    const form = $('trendAircraftForm');
    const values = () => Object.fromEntries(fields.map(spec=>[spec.key,$('ac_'+spec.key).value]));
    const dirty = () => JSON.stringify(values()) !== baseline;
    const error = message => { $('trendModalError').textContent = message; $('trendModalError').hidden = !message; };
    function control(spec) {
      const attrs = `id="ac_${spec.key}" ${spec.required?'required':''}`;
      if (spec.type === 'select') return `<select ${attrs}>${spec.options.map(([v,t])=>`<option value="${v}">${esc(t)}</option>`).join('')}</select>`;
      if (spec.type === 'textarea') return `<textarea ${attrs} maxlength="4000"></textarea>`;
      return `<input ${attrs} type="${spec.type}" ${spec.type==='number'?`step="${spec.step||'any'}" min="${spec.min??0.000001}" ${spec.max!=null?`max="${spec.max}"`:''}`:'maxlength="2000"'}>`;
    }
    $('aircraftEditorFields').innerHTML = groups.map((title,index)=>`<details ${index<2?'open':''}><summary>${title}</summary><div class="aircraft-editor-fields">${fields.filter(s=>s.group===index).map(s=>`<label class="${s.type==='textarea'?'aircraft-wide-field':''}" for="ac_${s.key}">${esc(s.label)}${control(s)}</label>`).join('')}</div></details>`).join('');

    function fill(record) {
      for (const spec of fields) {
        const input = $('ac_'+spec.key), value = record[spec.key];
        if (spec.type === 'select') {
          // Preserve source-specific definitions instead of silently changing them.
          if (value && ![...input.options].some(o=>o.value===value)) input.add(new Option(value,value));
          input.value = value ?? ([...input.options].some(o=>o.value==='unknown')?'unknown':spec.options[0][0]);
        } else input.value = value ?? '';
      }
      $('ac_manufacturer').required = !original;
      baseline = JSON.stringify(values());
      preview();
    }
    function preview() {
      const v = values(), n = key => v[key] === '' ? null : Number(v[key]);
      const mass=n('m0'),empty=n('me'),area=n('s'),span=n('b'),power=n('p_kw'),thrust=n('t_kn');
      for (const key of ['p_kw','prop_diameter_m']) { const input=$('ac_'+key);input.disabled=v.engine_type!=='prop';input.closest('label').hidden=input.disabled; }
      $('ac_t_kn').disabled=v.engine_type!=='jet';$('ac_t_kn').closest('label').hidden=v.engine_type!=='jet';
      $('ac_n_engines').readOnly=v.engine_type==='none';
      if(v.engine_type==='none')$('ac_n_engines').value='0';
      else if(Number($('ac_n_engines').value)<=0)$('ac_n_engines').value='1';
      const rows=[['Wydłużenie b²/S',span>0&&area>0?span*span/area:null,''],['OEW / MTOW',mass>0&&empty>0?empty/mass:null,''],['Obciążenie m₀/S',mass>0&&area>0?mass/area:null,'kg/m²']];
      if(v.engine_type==='prop')rows.push(['Obciążenie m₀/P',mass>0&&power>0?mass/power:null,'kg/kW']);
      if(v.engine_type==='jet')rows.push(['Stosunek T/W',mass>0&&thrust>0?thrust*1000/(mass*9.80665):null,'']);
      $('aircraftEditorDerived').innerHTML=rows.map(([label,val,unit])=>`<div><dt>${esc(label)}</dt><dd>${fmt(val,3)} ${unit}</dd></div>`).join('');
      const invalid=mass>0&&empty!=null&&empty>=mass;
      $('ac_me').setCustomValidity(invalid?'Masa pusta musi być mniejsza od masy startowej.':'');
      $('aircraftEditorChecks').textContent=invalid?'Masa pusta musi być mniejsza od MTOW.':'Podgląd aktualizuje się podczas edycji. „Sprawdź dane” weryfikuje cały rekord bez zapisu.';
      $('aircraftEditorChecks').classList.toggle('is-invalid',invalid);
      $('aircraftEditorProject').disabled=!original||dirty();
      $('aircraftEditorProjectNote').textContent=original?(dirty()?'Zapisz zmiany lub cofnij edycję, aby użyć zapisanych danych w projekcie.':'Kreator przejmie dostępne dane katalogowe. Pozostałe założenia sprawdzisz przed utworzeniem projektu.'):'Najpierw zapisz nowy samolot w bazie.';
    }
    function validForm() {
      preview();
      const invalid=[...form.querySelectorAll('input,select,textarea')].find(input=>!input.disabled&&!input.checkValidity());
      if(invalid){invalid.closest('details').open=true;invalid.reportValidity();return false;}
      return true;
    }
    function setBusy(value) {
      busy=value;
      for(const button of dialog.querySelectorAll('button'))button.disabled=value;
      for(const input of form.querySelectorAll('input,select,textarea'))input.disabled=value;
      if(!value)preview();
    }
    async function request(checkOnly) {
      if(busy||!validForm())return;
      error('');
      const data=payload(values(),original||{}), id=original?.id||BipolStudio.uniqueId('user-');
      const body=checkOnly?{id:original?.id||null,record:{...data,id}}:original?data:{...data,id};
      setBusy(true);
      let checkedMessage='';
      try {
        const response=await fetch(checkOnly?'/api/aircraft/preview':original?`/api/aircraft/${encodeURIComponent(id)}`:'/api/aircraft',{
          method:checkOnly||!original?'POST':'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const answer=await response.json();if(!response.ok)throw Error(answer.message||'Nie udało się sprawdzić danych.');
        if(checkOnly){checkedMessage='Dane poprawne. '+(answer.aircraft.quality_notes||[]).join(' ');}
        else {dialog.close();document.dispatchEvent(new CustomEvent('bipol:catalog-updated',{detail:answer.aircraft}));}
      }catch(err){error(err.message);}finally{setBusy(false);if(checkedMessage)$('aircraftEditorChecks').textContent=checkedMessage;}
    }
    async function open(record = null, sources = {}) {
      if(busy)return;
      const sequence=++openSequence;
      opener=document.activeElement;
      if(record){
        try {
          const response=await fetch(`/api/aircraft/${encodeURIComponent(record.id)}`);
          const answer=await response.json();if(!response.ok)throw Error(answer.message||'Nie udało się pobrać danych.');
          if(sequence!==openSequence)return;
          record=answer.aircraft;
        }catch(err){$('trendStatus').textContent=err.message;return;}
      }
      original=record?structuredClone(record):null;error('');
      $('trendModalTitle').textContent=original?`Parametry: ${original.model}`:'Dodaj statek powietrzny';
      fill(record||{aircraft_type:'piston_ga',engine_type:'prop',n_engines:1});
      const source=sources[record?.source_id];
      $('aircraftEditorSource').textContent=source?`Baza źródłowa: ${source.name}. ID: ${record.id}`:'Nowy wpis użytkownika';
      if(!dialog.open)dialog.showModal();
      $('ac_model').focus();
    }
    async function startProject() {
      if(!original||dirty())return;
      error('');setBusy(true);
      try {
        const mapped=root.BipolAircraftProject.fromRecord(original);
        const [presets,topics]=await Promise.all([fetch('/api/presets').then(r=>r.json()),fetch('/api/topics').then(r=>r.json())]);
        const profiles={piston_ga:'ga_trainer',turboprop_regional:'twin_turboprop',jet_business:'vlj_jet',glider:'glider_pw5',motoglider:'motoglider_aos',uav:'uav_tactical'};
        const base=mapped.aircraft_type==='jet_transport'?topics.topics.find(t=>t.id==='topic_78')?.parameters:presets[profiles[mapped.aircraft_type]];
        if(!base)throw Error('Brak profilu startowego dla tej klasy.');
        const params={...base,locked_params:[],wing_input_mode:'loading',payload_input_mode:'seats',power_input_mode:'sized',wingspan_m:0,wing_area_m2:0,engine_power_kw:0,...mapped.params,reference_aircraft:mapped.reference_aircraft};
        delete params.topic_id;delete params.topic_origin;delete params.id;
        opener=null;dialog.close();openWizard('create');root.BipolDesignBasis.seed(params);
      }catch(err){error(err.message);}finally{setBusy(false);}
    }
    form.addEventListener('input',()=>{error('');preview();});
    form.addEventListener('change',event=>{
      if(event.target.id==='ac_engine_type'&&event.target.value!=='none'&&$('ac_n_engines').value==='0')$('ac_n_engines').value='1';
      preview();
    });
    form.addEventListener('submit',event=>{event.preventDefault();request(false);});
    $('aircraftEditorCheck').addEventListener('click',()=>request(true));
    $('aircraftEditorReset').addEventListener('click',()=>{fill(original||{aircraft_type:'piston_ga',engine_type:'prop',n_engines:1});error('');});
    $('aircraftEditorProject').addEventListener('click',startProject);
    for(const id of ['closeTrendModalBtn','cancelTrendModalBtn'])$(id).addEventListener('click',()=>{if(!busy)dialog.close();});
    dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});
    dialog.addEventListener('close',()=>{if(opener?.isConnected)opener.focus({preventScroll:true});});
    root.BipolAircraftEditor.open=open;
  }
  const api={fields,payload,init};
  if(typeof module==='object'&&module.exports)module.exports=api;else root.BipolAircraftEditor=api;
  if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',init);
})(typeof globalThis!=='undefined'?globalThis:this);

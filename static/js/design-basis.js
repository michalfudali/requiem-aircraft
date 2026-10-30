/* Select independent assumptions explicitly; dependent controls are outputs. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const extraKeys = ['gear_attachment','gear_retraction','wing_input_mode','payload_input_mode','power_input_mode','wingspan_m',
    'takeoff_distance_m','landing_distance_m','wing_area_m2','m_payload','engine_power_kw','n_engines','wing_planform','dihedral_deg','aileron_type',
    'operating_surface','design_iteration_mode','water_displacement_volume_m3',
    'cargo_bay_length_m','cargo_bay_width_m','cargo_bay_height_m'];
  const wingSources = {loading:['aspect_ratio'],span_aspect:['wingspan_m','aspect_ratio'],
    span_area:['wingspan_m','wing_area_m2'],area_aspect:['wing_area_m2','aspect_ratio']};
  let wizardBase = {};
  let classPresets = {};
  const value = (prefix, key) => $(prefix+key)?.value;
  const number = (prefix, key) => Number(value(prefix,key) || 0);
  const set = (prefix, key, val) => { if ($(prefix+key) && val != null) $(prefix+key).value = val; };
  const defaultEngines = (prefix='') => value(prefix,'engine_type')==='none' ? 0 : (value(prefix,'engine_location')==='wing' || value(prefix,'engine_type')==='jet' ? 2 : 1);
  function derived(prefix, key, isDerived, formula='', result) {
    const input=$(prefix+key); if (!input) return;
    input.readOnly=isDerived;
    input.setAttribute('aria-readonly',String(isDerived));
    input.closest('.input-group')?.classList.toggle('is-derived',isDerived);
    if (isDerived && Number.isFinite(result)) input.value=+result.toFixed(6);
    const badge=$(prefix+'derived_badge_'+key);
    if (badge) {badge.hidden=!isDerived;badge.style.display=isDerived?'block':'none';badge.textContent=formula;}
    const button=$('lock_btn_'+key);
    if (!prefix && button) {button.disabled=isDerived;button.title=isDerived?formula:'Przypnij jako założenie';}
  }
  function sync(prefix='') {
    document.querySelectorAll(`[data-water-scope="${prefix}"]`).forEach(el=>el.hidden=value(prefix,'operating_surface')!=='water');
    document.querySelectorAll(`[data-cargo-scope="${prefix}"]`).forEach(el=>el.hidden=number(prefix,'m_cargo')<=0);
    const mode=value(prefix,'wing_input_mode') || 'loading';
    const b=number(prefix,'wingspan_m'), s=number(prefix,'wing_area_m2'), ar=number(prefix,'aspect_ratio');
    if (mode==='span_aspect') {
      derived(prefix,'wingspan_m',false);derived(prefix,'aspect_ratio',false);
      derived(prefix,'wing_area_m2',true,'S = b² / Λ', ar>0?b*b/ar:undefined);
    } else if (mode==='span_area') {
      derived(prefix,'wingspan_m',false);derived(prefix,'wing_area_m2',false);
      derived(prefix,'aspect_ratio',true,'Λ = b² / S',s>0?b*b/s:undefined);
    } else if (mode==='area_aspect') {
      derived(prefix,'wing_area_m2',false);derived(prefix,'aspect_ratio',false);
      derived(prefix,'wingspan_m',true,'b = √(S · Λ)',s>0&&ar>0?Math.sqrt(s*ar):undefined);
    } else {
      derived(prefix,'aspect_ratio',false);
      derived(prefix,'wing_area_m2',true,'Powierzchnia z bilansu masy i wymagania VS0 — po przeliczeniu.');
      derived(prefix,'wingspan_m',true,'Rozpiętość z powierzchni i wydłużenia — po przeliczeniu.');
    }
    const payload=number(prefix,'n_pax')*(number(prefix,'m_pax')+(prefix?Number(wizardBase.m_bag||0):Number(formBaseParams.m_bag||0)));
    if (value(prefix,'payload_input_mode')==='total') {
      derived(prefix,'m_payload',false);
      derived(prefix,'m_cargo',true,'Cargo = masa płatna − masa pasażerów z bagażem.',number(prefix,'m_payload')-payload);
    } else {
      derived(prefix,'m_cargo',false);
      derived(prefix,'m_payload',true,'Masa płatna = pasażerowie z bagażem + cargo (bez załogi).',payload+number(prefix,'m_cargo'));
    }
    const planform=value(prefix,'wing_planform');
    derived(prefix,'taper_ratio',planform==='rectangular'||planform==='elliptical',
      'Zbieżność wynika z wybranego obrysu.',planform==='rectangular'?1:planform==='elliptical'?0:undefined);
    const unpowered=value(prefix,'engine_type')==='none';
    const fixedPower=value(prefix,'power_input_mode')==='fixed'&&!unpowered;
    derived(prefix,'engine_power_kw',!fixedPower,unpowered?'Nie dotyczy lotu bez napędu.':'Moc z diagramu doboru — po przeliczeniu.',unpowered?0:undefined);
    const uas=value(prefix,'aircraft_type')==='uav';
    derived(prefix,'n_pax',uas,'Statek bezzałogowy — brak osób na pokładzie.',uas?0:undefined);
    derived(prefix,'n_crew',uas,'Statek bezzałogowy — brak osób na pokładzie.',uas?0:undefined);
    const note=$(prefix+'basis_note');
    if (note) note.textContent=mode==='loading'
      ? 'Powierzchnia i rozpiętość wynikają z masy, wymagania VS0 i przyjętego wydłużenia.'
      : 'Dwa wymiary są założeniami, trzeci wynika z b² = S · Λ. Wymaganie VS0 jest sprawdzane dla tej geometrii.';
  }
  function propulsion(prefix='') {
    const engine=value(prefix,'engine_type'), none=engine==='none', prop=engine==='prop';
    if (!prop) set(prefix,'power_input_mode','sized');
    for (const key of ['engine_location','sfc','prop_efficiency','engine_power_kw','power_input_mode','loiter_time_min','prop_eff_to','takeoff_run_m','takeoff_distance_m','climb_rate_ms']) {
      const input=$(prefix+key);if(!input)continue;
      if(key==='takeoff_run_m')input.closest('.legacy-runway')?.toggleAttribute('hidden',none);
      const hide=none||(!prop&&['prop_efficiency','engine_power_kw','power_input_mode','prop_eff_to'].includes(key));
      const group=input.closest('.input-group'); if(group){group.hidden=hide;group.style.display=hide?'none':'';}
      input.disabled=hide;
      if(['sfc','takeoff_run_m','takeoff_distance_m','climb_rate_ms'].includes(key))input.readOnly=none;
      if (none&&['sfc','engine_power_kw','takeoff_run_m','takeoff_distance_m','climb_rate_ms'].includes(key))input.value=0;
    }
    const loc=$(prefix+'engine_location');
    if (loc) {
      const noLocation=loc.querySelector('option[value="none"]');if(noLocation){noLocation.hidden=!none;noLocation.disabled=!none;}
      if(none) {if(loc.value!=='none')loc.dataset.poweredLocation=loc.value;loc.value='none';}
      else if(loc.value==='none'||!loc.value)loc.value=loc.dataset.poweredLocation||((engine==='jet')?'rear':'nose');
    }
    const nEng=$(prefix+'n_engines'), base=prefix?wizardBase:(typeof formBaseParams!=='undefined'?formBaseParams:null);
    if (nEng) {
      const grp=nEng.closest('.input-group'); if(grp){grp.hidden=none;grp.style.display=none?'none':'';}
      nEng.disabled=none; nEng.readOnly=none; nEng.min=none?'0':'1';
      if (none) { nEng.value='0'; if(base)base.n_engines=0; }
      else if (!Number.isFinite(Number(nEng.value)) || Number(nEng.value)<1) { const defN=defaultEngines(prefix); nEng.value=String(defN); if(base&&!(Number(base.n_engines)>=1))base.n_engines=defN; }
    } else if (base) { if(none)base.n_engines=0; else if(!(Number(base.n_engines)>=1))base.n_engines=defaultEngines(prefix); }
    const title=$('wiz_pane3_title');
    if(prefix&&title)title.textContent=none?'Krok 3: Lot bez napędu':'Krok 3: Zespół napędowy';
    const description=prefix?$('wizardPane3')?.querySelector('.wizard-pane-header p'):null;
    if(description)description.textContent=none?'Szybowiec nie wymaga lokalizacji silnika, mocy ani zużycia paliwa. Przejdź do konfiguracji płata.':'Określ rodzaj i lokalizację napędu. Możesz podać dostępną moc albo pozostawić jej dobór obliczeniom.';
    if(prefix)document.querySelectorAll('#wizardPane3 .formula-box').forEach(el=>el.hidden=none);
    sync(prefix);
  }
  function infer(params) {
    return {...params, wing_input_mode:params.wing_input_mode||((params.wingspan_m||params.span_limit)?'span_aspect':params.wing_area_m2?'area_aspect':'loading'),
      payload_input_mode:params.payload_input_mode||(params.locked_params?.includes('m_payload')?'total':'seats'),
      power_input_mode:params.power_input_mode||(params.locked_params?.includes('engine_power_kw')?'fixed':'sized')};
  }
  function restore(params) {
    const p=infer(params);window.userLockedParams=new Set(p.locked_params||[]);
    set('','operating_surface',p.operating_surface||'land');
    set('','design_iteration_mode',p.design_iteration_mode||'preliminary');
    set('','water_displacement_volume_m3',p.water_displacement_volume_m3||0);
    for(const key of ['cargo_bay_length_m','cargo_bay_width_m','cargo_bay_height_m'])set('',key,p[key]||0);
    for (const key of extraKeys) if(key in p)set('',key,p[key]);
    if(!('wing_area_m2' in p))set('','wing_area_m2',0);
    if(!('wingspan_m' in p))set('','wingspan_m',p.span_limit||0);
    if(!('engine_power_kw' in p))set('','engine_power_kw',0);
    for(const key of ['takeoff_distance_m','landing_distance_m'])set('',key,p[key]||0);
    set('','gear_attachment',p.gear_attachment||'fuselage');
    set('','gear_retraction',p.gear_retraction||'auto');
    set('','n_engines',p.engine_type==='none'?0:(Number(p.n_engines)>=1?p.n_engines:defaultEngines('')));
    sync();propulsion();
  }
  function openWizard() {
    if ($('wizardCatalogSource')) $('wizardCatalogSource').hidden = true;
    wizardBase=infer(collectFormData());
    for(const [key,val] of Object.entries(wizardBase))set('wiz_',key,val);
    const topic=topicsData.find(t=>t.num===Number(wizardBase.topic_id));
    set('wiz_','topic',wizardBase.topic_origin==='official'&&topic?topic.id:'');
    document.querySelectorAll('[data-wizard-assumption]').forEach(input=>input.checked=window.userLockedParams.has(input.dataset.wizardAssumption));
    set('wiz_basis_','range_km', value('wiz_','range_km'));
    set('wiz_basis_','cruise_speed_kmh', value('wiz_','cruise_speed_kmh'));
    set('wiz_basis_','v_stall_kmh', value('wiz_','v_stall_kmh'));
    if($('wizTrendProvenanceBasis'))$('wizTrendProvenanceBasis').hidden=true; if($('wizTrendProvenanceGeometry'))$('wizTrendProvenanceGeometry').hidden=true; sync('wiz_');propulsion('wiz_');topicNote(); window.BipolTrendProvenance?.previewInWizard?.();
  }
  function seed(params) {
    // Reset the new project wizard before applying a catalogue observation.
    wizardBase=infer(structuredClone(params));
    for (const input of document.querySelectorAll('#projectWizardBackdrop input, #projectWizardBackdrop select')) {
      if (!input.id.startsWith('wiz_')) continue;
      if (input.type==='checkbox') { input.checked=false; continue; }
      if (input.tagName==='SELECT') input.value=[...input.options].find(o=>o.defaultSelected)?.value||input.options[0]?.value||'';
      else input.value=input.defaultValue;
    }
    for(const [key,val] of Object.entries(wizardBase))set('wiz_',key,val);
    set('wiz_','topic','');
    document.querySelectorAll('[data-wizard-assumption]').forEach(input=>input.checked=(wizardBase.locked_params||[]).includes(input.dataset.wizardAssumption));
    syncAircraftClassAndEASAUI(true);propulsion('wiz_');renderWizardStep4Mechanics();
    for(const [key,val] of Object.entries(wizardBase))set('wiz_',key,val);
    for(const key of ['range_km','cruise_speed_kmh','v_stall_kmh'])set('wiz_basis_',key,wizardBase[key]);
    sync('wiz_');topicNote();
    window.BipolTrendProvenance?.previewInWizard?.();
    const note=$('wizardCatalogSource');
    if(note){note.hidden=false;note.textContent=`Dane początkowe: ${params.reference_aircraft.model}. Przeniesiono dostępne parametry katalogowe. Pozostałe pola pochodzą z profilu klasy — sprawdź misję, załogę i ładunek przed zapisaniem projektu. Katalogowe MTOW i OEW służą do porównania.`;}
  }
  function topicNote() {
    const topic=topicsData.find(t=>t.id===value('wiz_','topic'));
    const note=$('wiz_topic_note');
    if(note)note.textContent=topic?[7,8].includes(topic.num)?'Ten temat wymaga rozpiętości większej niż 20 m. Przyjęto roboczo 21 m; możesz podać inną wartość powyżej 20 m.':'Wartości startowe odpowiadają wybranemu tematowi. Możesz zmienić niezależne założenia.':'Własny projekt: wybierz wielkości wejściowe i ich wartości.';
    const b=$('wiz_wingspan_m');if(b)b.min=topic&&[7,8].includes(topic.num)?'20.001':'0';
  }
  function chooseTopic() {
    const topic=topicsData.find(t=>t.id===value('wiz_','topic'));
    if(!topic){delete wizardBase.topic_id;delete wizardBase.topic_origin;topicNote();return;}
    if($('wizardCatalogSource'))$('wizardCatalogSource').hidden=true;
    wizardBase=structuredClone(topic.parameters);
    set('wiz_','water_displacement_volume_m3',0);
    for(const key of ['cargo_bay_length_m','cargo_bay_width_m','cargo_bay_height_m'])set('wiz_',key,0);
    for(const [key,val] of Object.entries(wizardBase))set('wiz_',key,val);
    set('wiz_','n_engines',wizardBase.engine_type==='none'?0:(wizardBase.n_engines ?? defaultEngines('wiz_')));
    document.querySelectorAll('[data-wizard-assumption]').forEach(input=>input.checked=wizardBase.locked_params.includes(input.dataset.wizardAssumption));
    set('wiz_basis_','range_km', wizardBase.range_km || value('wiz_','range_km'));
    set('wiz_basis_','cruise_speed_kmh', wizardBase.cruise_speed_kmh || value('wiz_','cruise_speed_kmh'));
    set('wiz_basis_','v_stall_kmh', wizardBase.v_stall_kmh || value('wiz_','v_stall_kmh'));
    syncAircraftClassAndEASAUI(true);syncWizardPropulsionUI(false);renderWizardStep4Mechanics();window.BipolTrendProvenance?.previewInWizard?.();
    sync('wiz_');topicNote();
  }
  // Fields without a wizard input still travel with the wizard snapshot.
  function applyWizardTrend(key, val) {
    const patch = BipolTrendInputs.patch(key, val, {wing_input_mode: value('wiz_', 'wing_input_mode')}, 0);
    for (const [field, fieldValue] of Object.entries(patch)) {
      wizardBase[field] = fieldValue;
      if ($('wiz_' + field)) set('wiz_', field, fieldValue);
    }
    sync('wiz_');
  }
  function snapshot() {
    sync('wiz_');
    const p={...wizardBase};
    const keys=new Set([...Object.keys(collectFormData()),...extraKeys]);
    keys.forEach(key=>{const input=$('wiz_'+key);if(!input)return;p[key]=input.type==='number'?Number(input.value):input.value;});
    if($('wiz_basis_range_km')){const bR=Number($('wiz_basis_range_km').value);if(!isNaN(bR)&&bR>=0)p['range_km']=bR;}
    if($('wiz_basis_cruise_speed_kmh')){const bV=Number($('wiz_basis_cruise_speed_kmh').value);if(!isNaN(bV)&&bV>0)p['cruise_speed_kmh']=bV;}
    if($('wiz_basis_v_stall_kmh')){const bVs=Number($('wiz_basis_v_stall_kmh').value);if(!isNaN(bVs)&&bVs>0)p['v_stall_kmh']=bVs;}
    p.name=$('wiz_name').value.trim()||'Mój projekt BIPOL';
    if(p.engine_type==='none')p.n_engines=0; else if(!(Number(p.n_engines)>=1))p.n_engines=defaultEngines('wiz_');
    const locked=new Set(wizardBase.locked_params||[]);
    for(const key of ['wingspan_m','wing_area_m2','aspect_ratio','m_payload','m_cargo','engine_power_kw'])locked.delete(key);
    for(const key of wingSources[p.wing_input_mode])locked.add(key);
    if(p.payload_input_mode==='total')locked.add('m_payload');
    if(p.power_input_mode==='fixed'&&p.engine_type==='prop')locked.add('engine_power_kw');
    document.querySelectorAll('[data-wizard-assumption]').forEach(input=>{
      if(input.checked)locked.add(input.dataset.wizardAssumption);else locked.delete(input.dataset.wizardAssumption);
    });
    p.locked_params=[...locked];
    return p;
  }
  function collect(data) {
    // Read-only numbers shown to the user are outputs; modes are authoritative.
    data.wing_input_mode=value('','wing_input_mode');
    data.payload_input_mode=value('','payload_input_mode');
    data.power_input_mode=value('','power_input_mode');
    return data;
  }
  function loadTopic(topic) {
    formBaseParams=structuredClone(topic.parameters);
    for(const [key,val] of Object.entries(formBaseParams))set('',key,val);
    restore(formBaseParams);
    const active=getActiveProject();
    if(active){active.name=topic.title;active.params={...formBaseParams};saveProject(active);}
    if($('projectNameDisplay'))$('projectNameDisplay').textContent=topic.title;
    syncAircraftClassAndEASAUI(false);syncFormPropulsionUI(false);renderWingConfigDidacticCard();renderFlapDidacticCard(true);
    sync();updateAccordionPills();performCalculation();
  }
  function applyResult(result) {
    window.userLockedParams=new Set(result.params.locked_params||[]);
    for(const key of ['wing_input_mode','payload_input_mode','power_input_mode'])set('',key,result.params[key]);
    sync();
  }
  function classDefaults(prefix='') {
    const base=prefix?wizardBase:formBaseParams;
    delete base.preliminary_polar_includes_configuration;
    delete base.topic_id;delete base.topic_origin;
    if(prefix){set('wiz_','topic','');topicNote();}
    if(prefix){if($('wizTrendProvenanceBasis'))$('wizTrendProvenanceBasis').hidden=true;if($('wizTrendProvenanceGeometry'))$('wizTrendProvenanceGeometry').hidden=true;window.BipolTrendProvenance?.previewInWizard?.();}
    const defN=defaultEngines(prefix); base.n_engines=defN; set(prefix,'n_engines',defN);
    const preset=classPresets[value(prefix,'aircraft_type')];if(!preset){sync(prefix);return;}
    if(preset.n_engines!=null){base.n_engines=preset.n_engines;set(prefix,'n_engines',preset.n_engines);}
    for(const key of ['aspect_ratio','cx0','oswald_e','sfc','v_h','v_v','ar_h','ar_v','loiter_time_min']){
      if (key==='aspect_ratio'&&(value(prefix,'wing_input_mode')!=='loading'||(prefix?(base.locked_params||[]):[...window.userLockedParams]).includes(key)))continue;
      base[key]=preset[key];set(prefix,key,preset[key]);
    }
    sync(prefix);
  }
  const wizardValue=key=>$('wiz_'+key)?Number($('wiz_'+key).value):wizardBase[key]!=null?Number(wizardBase[key]):formBaseParams[key]!=null?Number(formBaseParams[key]):$(key)?Number($(key).value):Number(window.currentResults?.params?.[key]??classPresets[value('wiz_','aircraft_type')]?.[key]);
  window.BipolDesignBasis={sync,propulsion,restore,openWizard,seed,snapshot,collect,loadTopic,applyResult,classDefaults,wizardValue};
  document.addEventListener('DOMContentLoaded',async()=>{
    $('wiz_topic')?.addEventListener('change',chooseTopic);
    const syncAssumption = (basisId, step2Id, assumptionKey) => {
      const bEl = $(basisId), s2El = $(step2Id);
      const chk = document.querySelector(`[data-wizard-assumption="${assumptionKey}"]`);
      if(bEl && s2El) {
        bEl.addEventListener('input', () => {
          s2El.value = bEl.value;
          if(chk) chk.checked = true;
          wizardBase[assumptionKey] = Number(bEl.value);
        });
        s2El.addEventListener('input', () => {
          bEl.value = s2El.value;
          if(chk) chk.checked = true;
          wizardBase[assumptionKey] = Number(s2El.value);
        });
      }
    };
    syncAssumption('wiz_basis_range_km', 'wiz_range_km', 'range_km');
    syncAssumption('wiz_basis_cruise_speed_kmh', 'wiz_cruise_speed_kmh', 'cruise_speed_kmh');
    syncAssumption('wiz_basis_v_stall_kmh', 'wiz_v_stall_kmh', 'v_stall_kmh');
    $('wizApplyTrendGeometryBtn')?.addEventListener('click', () => BipolTrendProvenance.applyInWizard(
      $('wizApplyTrendGeometryBtn'), $('wizTrendProvenanceBasis'), ['ar'], applyWizardTrend));
    $('wizSuggestTrendsBtn')?.addEventListener('click', () => BipolTrendProvenance.applyInWizard(
      $('wizSuggestTrendsBtn'), $('wizTrendProvenanceGeometry'),
      ['ar', 'vh', 'v_v', 'b_ail_ratio', 'c_ail_ratio', 'c_e_ratio', 'c_r_ratio', 'dihedral_deg'], applyWizardTrend));
    document.addEventListener('input',event=>{
      const input=event.target;if(!input.matches('#designForm input, #projectWizardBackdrop input'))return;
      const prefix=input.id.startsWith('wiz_')?'wiz_':'';sync(prefix);if(prefix)window.BipolTrendProvenance?.refreshWizardCharts?.();
    });
    document.addEventListener('change',event=>{
      const input=event.target;if(!input.matches('#designForm select, #projectWizardBackdrop select'))return;
      const prefix=input.id.startsWith('wiz_')?'wiz_':'';
      if(input.dataset.basisSelector!==undefined && value(prefix,'power_input_mode')==='fixed'&&number(prefix,'engine_power_kw')<=0)set(prefix,'engine_power_kw',73.5);
      if(prefix==='wiz_'&&['wiz_engine_type','wiz_wing_config'].includes(input.id))window.BipolTrendProvenance?.previewInWizard?.();
      if(input.id===prefix+'engine_location'&&value(prefix,'engine_type')!=='none'&&input.value==='wing'&&number(prefix,'n_engines')===1)set(prefix,'n_engines',2);
      sync(prefix);if(prefix)window.BipolTrendProvenance?.refreshWizardCharts?.();
    });
    try {const response=await fetch('/api/presets');const presets=await response.json();for(const preset of Object.values(presets))classPresets[preset.aircraft_type]??=preset;} catch(_){}
  });
})();

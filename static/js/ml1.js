/* ML1 fixed-aircraft workbook. Source data stay in this browser until submitted. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const KEY = 'requiem.ml1.v1';
  const labels = {
    aircraft:'P1 · Dane znanego samolotu', geometry:'P2 · Obrys płata', profile:'P2 · Badania profilu',
    aircraft_aerodynamics:'P3 · Charakterystyki całego samolotu', glide_cases:'P4 · Trzy przypadki lotu szybowego',
    propulsion:'P5 · Zespół napędowy', propeller_design:'P5 · Warunki doboru śmigła', performance:'P6 · Osiągi podstawowe',
    cruise:'P6 · Zasięg i długotrwałość', example_basis:'Oznaczenie danych',
    mass_kg:'Masa w locie [kg]',mass_initial_kg:'Początkowa masa przelotu [kg]',mass_final_kg:'Końcowa masa przelotu [kg]',
    area_m2:'Powierzchnia odniesienia płata [m²]',span_m:'Rozpiętość [m]',mac_m:'MAC [m]',length_m:'Długość [m]',height_m:'Wysokość samolotu [m]',
    altitude_m:'Wysokość lotu [m]',heights_m:'Wysokości lotu [m]',altitudes_m:'Wysokości lotu [m]',
    empty_mass_kg:'Masa pusta [kg]',mtow_kg:'Maksymalna masa startowa [kg]',flight_mass_kg:'Masa w locie [kg]',
    fuel_mass_kg:'Całkowity zapas paliwa [kg]',payload_mass_kg:'Masa ładunku [kg]',fuel_kg:'Zapas paliwa [kg]',
    name:'Nazwa i wariant',sources:'Źródła danych',source:'Źródło danych: autor, strona / wykres / adres',notes:'Uwagi',
    profile_data:'Informacje źródłowe o profilach',engine_data:'Dane źródłowe silnika',reported_performance:'Osiągi według źródeł',
    drawing:'Podziałka rysunku',reference_length_m:'Wymiar rzeczywisty [m]',measured_length_mm:'Wymiar zmierzony na rysunku [mm]',target_denominator:'Docelowa podziałka 1 :',
    stations:'Stacje obrysu półskrzydła: y_m, x_le_m, chord_m',datasets:'Trzy lub więcej charakterystyk: re i rows',
    rows:'Punkty charakterystyki',polar:'Biegunowa: cl, cd',wing_rows:'Biegunowa płata: cl, cd_wing, alpha_wing_deg',
    lift_rows:'Charakterystyka siły nośnej: cl, alpha_deg',drag_rows:'Charakterystyka oporu: cl, cd',
    cm_ac:'Cm względem środka aerodynamicznego',x_ac_mac:'Położenie S.A. / MAC',z_ac_mac:'Pionowe położenie S.A. / MAC',
    x_cg_mac:'Położenie środka masy / MAC',a_inf_rad:'dCz/dα profilu [1/rad]',a_wing_rad:'dCz/dα płata [1/rad]',theoretical_a_rad:'Pochodna płata według (2.27) [1/rad]',
    aspect_ratio:'Wydłużenie płata',taper_ratio:'Zbieżność ck/c0',sweep_quarter_deg:'Skos linii ćwiartek cięciw [°]',
    re_from:'Liczba Re danych źródłowych',re_to:'Docelowa liczba Re',target_re:'Docelowa liczba Re',
    material:'Materiał / wariant oporu technicznego',data_kind:'Rodzaj danych tunelowych',
    cl:'Cz / CL',cd:'Cx / CD',cl_min:'Dolna granica Cz',cl_max:'Górna granica Cz',cl_values:'Wartości Cz tabeli',cd0:'Cx0 / CD0',k:'k w biegunowej Cx = Cx0 + k·Cz²',
    cl_critical_positive:'Cz krytyczne dodatnie',cl_critical_negative:'Cz krytyczne ujemne',cd_min_reference:'Minimalny Cx źródłowy',
    cl_fit_min:'Dolna granica Cz aproksymacji',cl_fit_max:'Górna granica Cz aproksymacji',
    alpha_min_deg:'Dolna granica α regresji [°]',alpha_max_deg:'Górna granica α regresji [°]',
    measured_stall_speed_ms:'Zmierzona prędkość przeciągnięcia [m/s]',stall_speed_ms:'Zmierzona prędkość przeciągnięcia [m/s]',
    tail:'Usterzenie poziome',arm_m:'Ramię usterzenia od środka masy [m]',oswald_e:'Współczynnik Oswalda e',position:'Położenie usterzenia',
    pressure_ratio:'Stosunek qH/q',profile_cd_min:'Minimalny Cx profilu usterzenia',gap_cd:'Przyrost Cx od szczelin',
    components:'Podzespoły: name, cd, reference_area_m2, source',component:'Dane jednego podzespołu',zeta:'Zeta (3–6)',interference:'Współczynnik interferencji',
    points:'Punkty wykresu: [argument, wartość]',argument:'Argument odczytu',logarithmic_x:'Oś argumentu logarytmiczna',
    frontal_area_m2:'Maksymalny przekrój czołowy kadłuba [m²]',nose_length_m:'Długość nosowej części [m]',
    wetted_area_m2:'Zmierzona powierzchnia omywana [m²] (null = wzór przybliżony)',cf:'Cf z wykresu',eta_shape:'ηk z wykresu',eta_mach:'ηMa z wykresu',
    velocity_ms:'Prędkość lotu [m/s]',maximum_speed_ms:'Maksymalna prędkość pozioma [m/s]',mach:'Liczba Macha',
    diameter_m:'Średnica śmigła [m]',power_w:'Moc na wale śmigła [W]',power_at_max_w:'Moc przy obrotach maksymalnych [W]',
    revolutions_s:'Obroty śmigła [obr/s]',rpm:'Obroty śmigła [obr/min]',rpm_limit:'Ograniczenie obrotów śmigła [obr/min]',rpm_max:'Obroty maksymalne [obr/min]',
    pitch:'Sposób zmiany skoku śmigła',beta_deg:'Kąt ustawienia łopaty [°]',propeller:'Mapa śmigła',candidates:'Mapy porównywanych śmigieł',
    curves:'Krzywe mapy: beta_deg, rows[{j,cn,eta}]',engine:'Charakterystyka silnika',model:'Model charakterystyki silnika',
    engine_curve:'Moc [W] w funkcji obr/min wału śmigła na danej wysokości',engine_rpm_power:'Moc [W] w funkcji obr/min wału śmigła przy ziemi',
    engine_count:'Liczba silników',kind:'Rodzaj napędu',propulsion_config:'Dane zespołu napędowego',
    power_sl_w:'Moc silnika przy ziemi [W]',static_thrust_n:'Ciąg statyczny jednego silnika [N]',lapse_k:'Współczynnik k spadku mocy',
    min_diameter_m:'Minimalna średnica z warunków zabudowy [m]',max_diameter_m:'Maksymalna średnica z warunków zabudowy [m]',
    j_values:'Wartości posuwu J',eta:'Sprawność śmigła do obliczeń zasięgu',sfc:'qe: śmigło kg/(kW·h), odrzut kg/(daN·h)',
    nominal_per_engine:'Nastawa nominalna jednego silnika: śmigło [kW], odrzut [N]',maneuver_minutes:'Łączny czas startu i lądowania [min]',reserve_minutes:'Rezerwa nawigacyjna [min]',
    prandtl:'Korekta Prandtla dla odrzutowca (Ma < 1)',schedule:'Program lotu',steps:'Liczba przedziałów całkowania (parzysta)',
    reserve_fuel_flow_kgh:'Ekonomiczne zużycie rezerwowe całego napędu [kg/h] (null = nominalne)',
    samples:'Liczba punktów charakterystyki osiągów',climb_steps:'Przedziały całkowania wznoszenia (parzysta)',
    height_m:'Wysokość docelowa [m]',theoretical_ceiling_m:'Pułap teoretyczny [m]',sea_level_roc_ms:'Maksymalne wznoszenie przy ziemi [m/s]',
    target_height_m:'Wysokość docelowa [m]',allow_critical_extrapolation:'Zezwól na liniowe uzupełnienie Cx przy kątach krytycznych',
    source_aspect_ratio:'Wydłużenie płata tunelowego',target_aspect_ratio:'Wydłużenie płata docelowego',source_taper:'Zbieżność płata tunelowego',target_taper:'Zbieżność docelowa',
    point_a:'Pierwszy punkt prostej Cx(Cz²)',point_b:'Drugi punkt prostej Cx(Cz²)',elliptical:'Idealny nieskoszony płat eliptyczny',
    efficiency_curve:'Tabela η(V) lub null',sfc_curve:'Tabela qe(V) lub null',cd_incompressible:'Cx bez korekty ściśliwości',cases:'Trzy pary mass_kg, altitude_m'
  };
  const choices = {
    schedule:['constant_cl','constant_speed'], material:['metal_composite','wood_fabric_mixed','metal','wood_composite'],
    data_kind:['section','finite_wing'],position:['t_tail','below_fuselage','fuselage_axis'],kind:['propeller','jet'],
    propulsion:['propeller','jet','glider'],pitch:['variable','fixed','power_table'],
    model:['piston_unboosted','turbocharged','two_speed_supercharger','turboprop','turbojet','turbofan','table'],
    example_basis:['synthetic_educational_data','user_data']
  };
  const engineTemplates = {
    piston_unboosted:{model:'piston_unboosted',power_sl_w:120000,lapse_k:.14},
    turbocharged:{model:'turbocharged',power_sl_w:120000,critical_height_m:6000,lapse_k:.14},
    two_speed_supercharger:{model:'two_speed_supercharger',power_sl_w:100000,critical_1_m:2000,shift_height_m:3000,critical_2_m:4000,power_critical_1_w:110000,power_shift_2_w:105000,power_critical_2_w:115000,lapse_k:.14},
    turboprop:{model:'turboprop',power_sl_w:500000},turbojet:{model:'turbojet',static_thrust_n:10000},
    turbofan:{model:'turbofan',static_thrust_n:10000,kp:.5},
    table_power:{model:'table',altitude_power:[[0,120000],[4000,80000],[8000,40000]]},
    table_thrust:{model:'table',altitude_slices:[{altitude_m:0,mach_thrust:[[0,10000],[1,8000]]},{altitude_m:8000,mach_thrust:[[0,4000],[1,3000]]}]}
  };
  const state = {catalog:[],workbook:null,method:null,last:null,revision:0,controller:null,drafts:{},view:'workbook'};
  function node(tag,text,cls) { const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e; }
  function message(text,cls='') { $('calculationMessage').textContent=text;$('calculationMessage').className=cls; }
  function invalidate() {
    state.revision++;state.last=null;$('resultsSection').hidden=true;
    $('downloadResults').disabled=true;$('downloadReport').disabled=true;
    if(state.controller){state.controller.abort();state.controller=null;message('Dane zmieniły się. Uruchom obliczenia ponownie.');}
  }
  function rawForm(container) {
    return Object.fromEntries([...container.querySelectorAll('[data-path]')].map(e=>[e.dataset.path,e.type==='checkbox'?e.checked:e.value]));
  }
  function save() {
    try {
      const draft=rawForm($(state.view==='methods'?'methodFields':'workbookFields'));
      if(state.view==='methods')state.drafts[state.method]=draft;
      const old=JSON.parse(localStorage.getItem(KEY)||'{}');
      localStorage.setItem(KEY,JSON.stringify({workbook:state.workbook,workbookDraft:state.view==='workbook'?draft:old.workbookDraft,
        drafts:state.drafts,method:state.method,view:state.view}));
      $('saveStatus').textContent='Dane zapisane w tej przeglądarce';
    } catch { $('saveStatus').textContent='Zapis lokalny niedostępny — użyj eksportu JSON'; }
  }
  function setPath(root,path,value) {
    const keys=path.split('.');let current=root;
    keys.slice(0,-1).forEach(key=>{current[key]??={};current=current[key];});current[keys.at(-1)]=value;
  }
  function readForm(container,base) {
    const result=structuredClone(base);
    for(const e of container.querySelectorAll('[data-path]')) {
      e.classList.remove('invalid');let value;
      try {
        if(e.type==='checkbox')value=e.checked;
        else if(e.dataset.kind==='json')value=JSON.parse(e.value);
        else if(e.type==='number') {value=e.value===''?null:Number(e.value);if(value!==null&&!Number.isFinite(value))throw Error('Podaj skończoną liczbę.');}
        else value=e.value;
      } catch(error) { e.classList.add('invalid');e.focus();throw Error(`${e.dataset.label}: ${error.message}`); }
      setPath(result,e.dataset.path,value);
    }
    return result;
  }
  function restoreDraft(container,draft) {
    if(!draft)return;
    for(const e of container.querySelectorAll('[data-path]'))if(Object.hasOwn(draft,e.dataset.path)) {
      if(e.type==='checkbox')e.checked=!!draft[e.dataset.path];else e.value=draft[e.dataset.path];
    }
  }
  function parseCSV(text) {
    text=text.replace(/^\uFEFF/,'');const first=text.split(/\r?\n/)[0];
    const delimiter=first.includes(';')?';':first.includes('\t')?'\t':',';
    const rows=[];let row=[],value='',quoted=false;
    for(let i=0;i<text.length;i++) {
      const c=text[i];
      if(c==='"'){if(quoted&&text[i+1]==='"'){value+='"';i++;}else quoted=!quoted;}
      else if(!quoted&&c===delimiter){row.push(value);value='';}
      else if(!quoted&&(c==='\n'||c==='\r')){if(c==='\r'&&text[i+1]==='\n')i++;row.push(value);if(row.some(x=>x.trim()))rows.push(row);row=[];value='';}
      else value+=c;
    }
    if(quoted)throw Error('Niezamknięty cudzysłów CSV.');
    row.push(value);if(row.some(x=>x.trim()))rows.push(row);
    if(rows.length<2)throw Error('CSV wymaga nagłówka i co najmniej jednego wiersza.');
    const headers=rows.shift().map(x=>x.trim());
    if(new Set(headers).size!==headers.length||headers.some(x=>!x))throw Error('Nagłówki CSV muszą być niepuste i różne.');
    const numeric=new Set(['re','cl','cd','alpha_deg','beta_deg','j','cn','eta','y_m','x_le_m','chord_m','mass_kg','altitude_m','reference_area_m2','drag_n','dynamic_pressure_pa','rho_kgm3','velocity_ms','cd_wing','alpha_wing_deg']);
    return rows.map((cells,index)=>{
      if(cells.length!==headers.length)throw Error(`Wiersz ${index+2}: liczba kolumn nie odpowiada nagłówkom.`);
      return Object.fromEntries(headers.map((h,i)=>{
        let v=cells[i].trim();if(numeric.has(h)){v=Number(delimiter===';'?v.replace(',','.'):v);if(cells[i].trim()===''||!Number.isFinite(v))throw Error(`Wiersz ${index+2}, ${h}: wymagana liczba.`);}return [h,v];
      }));
    });
  }
  function groupCSV(rows,key) {
    const groups=new Map();
    for(const row of rows){if(!Object.hasOwn(row,key))throw Error(`CSV wymaga kolumny ${key}.`);const {[key]:value,...rest}=row;if(!groups.has(value))groups.set(value,[]);groups.get(value).push(rest);}
    return [...groups].map(([value,values])=>({[key]:value,rows:values}));
  }
  function field(parent,key,value,path,depth=0) {
    const title=labels[key]||key.replaceAll('_',' ');
    if(value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).length&&depth<3&&!['engine','propulsion_config'].includes(key)) {
      const fs=node('fieldset');fs.append(node('legend',title));const grid=node('div',undefined,'field-grid');
      for(const [k,v] of Object.entries(value))field(grid,k,v,path?`${path}.${k}`:k,depth+1);
      fs.append(grid);fs.className='wide';parent.append(fs);return;
    }
    const label=node('label');label.append(node('span',title));let input;
    if(typeof value==='boolean'){input=node('input');input.type='checkbox';input.checked=value;}
    else if(typeof value==='number'){input=node('input');input.type='number';input.step='any';input.value=value;}
    else if(typeof value==='string'&&choices[key]){input=node('select');for(const choice of choices[key])input.append(new Option(choice,choice));if(!choices[key].includes(value))input.append(new Option(value,value));input.value=value;}
    else if(typeof value==='string'){input=node('input');input.type='text';input.value=value;}
    else {input=node('textarea');input.dataset.kind='json';input.value=JSON.stringify(value,null,2);input.spellcheck=false;label.className='wide';if(Array.isArray(value))input.className='data';}
    input.dataset.path=path;input.dataset.label=title;
    input.id='ml1-'+path.replaceAll('.','-');label.htmlFor=input.id;label.append(input);parent.append(label);
    if(input.dataset.kind==='json') {
      label.append(node('small','JSON; null pozostawia opcję domyślną.','hint'));
      if(key==='engine') {
        const tools=node('div',undefined,'field-tools');const select=node('select');select.setAttribute('aria-label','Przykładowa struktura charakterystyki silnika');
        Object.keys(engineTemplates).forEach(name=>select.append(new Option(name,name)));
        const button=node('button','Wstaw strukturę przykładową');button.type='button';
        button.addEventListener('click',()=>{input.value=JSON.stringify(engineTemplates[select.value],null,2);invalidate();save();message('Wstawiono syntetyczny wzór danych silnika. Uzupełnij go własnymi danymi źródłowymi.');});
        tools.append(select,button);label.append(tools);
      }
      if(Array.isArray(value)&&value.every(x=>x&&typeof x==='object'&&!Array.isArray(x))) {
        const tools=node('div',undefined,'field-tools');const file=node('input');file.type='file';file.accept='.csv,text/csv';file.hidden=true;
        const button=node('button','Wczytaj tabelę CSV');button.type='button';button.addEventListener('click',()=>file.click());
        const hint=node('small',key==='datasets'?'Kolumny: re,cl,cd,alpha_deg':key==='curves'?'Kolumny: beta_deg,j,cn,eta':'Nagłówki zgodne z kluczami JSON.','hint');
        file.addEventListener('change',async()=>{try{if(file.files[0].size>4*1024*1024)throw Error('Plik przekracza 4 MB.');let rows=parseCSV(await file.files[0].text());if(key==='datasets')rows=groupCSV(rows,'re');if(key==='curves')rows=groupCSV(rows,'beta_deg');input.value=JSON.stringify(rows,null,2);invalidate();save();message('Wczytano tabelę CSV.');}catch(error){message(error.message,'error');}finally{file.value='';}});
        tools.append(button,file,hint);label.append(tools);
      }
    }
  }
  function workbookFields(draft) {
    $('workbookFields').replaceChildren();for(const [key,value] of Object.entries(state.workbook))field($('workbookFields'),key,value,key);
    restoreDraft($('workbookFields'),draft);
    $('exampleNotice').hidden=state.workbook.example_basis!=='synthetic_educational_data';
  }
  function selectedMethod() {return state.catalog.find(m=>m.id===state.method);}
  function methodFields() {
    const method=selectedMethod();if(!method)return;
    $('methodFields').replaceChildren();const grid=node('div',undefined,'field-grid');
    for(const [key,value] of Object.entries(method.inputs))field(grid,key,value,key);
    $('methodFields').append(grid);restoreDraft($('methodFields'),state.drafts[state.method]);
    const link=node('a',`P${method.project} · Materiał źródłowy`);link.href=method.source_url;link.target='_blank';link.rel='noopener';$('methodSource').replaceChildren(link);
  }
  function filterMethods() {
    const project=Number($('projectFilter').value);$('methodSelect').replaceChildren();
    for(const m of state.catalog.filter(m=>!project||m.project===project))$('methodSelect').append(new Option(`P${m.project} · ${m.title}`,m.id));
    if([...$('methodSelect').options].some(o=>o.value===state.method))$('methodSelect').value=state.method;
    state.method=$('methodSelect').value;methodFields();
  }
  function fmt(value) {
    if(value===null||value===undefined)return '—';if(typeof value==='boolean')return value?'tak':'nie';
    if(typeof value==='number')return Number.isFinite(value)?new Intl.NumberFormat('pl-PL',{maximumSignificantDigits:7}).format(value):'—';
    return typeof value==='object'?JSON.stringify(value):String(value);
  }
  function metrics(parent,pairs) {
    const grid=node('div',undefined,'metrics');for(const [label,value] of pairs){const card=node('div',undefined,'metric');card.append(node('strong',fmt(value)),node('span',label));grid.append(card);}parent.append(grid);
  }
  function download(name,text,type='application/json') {
    const url=URL.createObjectURL(new Blob([text],{type}));const a=node('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function csvRows(rows) {
    const keys=[...new Set(rows.flatMap(r=>Object.keys(r)))];const quote=v=>'"'+fmt(v).replaceAll('"','""')+'"';
    // Use raw decimal points in CSV, independent of on-screen Polish formatting.
    const raw=v=>'"'+(v===null||v===undefined?'':typeof v==='object'?JSON.stringify(v):String(v)).replaceAll('"','""')+'"';
    return '\uFEFF'+keys.map(quote).join(';')+'\r\n'+rows.map(row=>keys.map(k=>raw(row[k])).join(';')).join('\r\n');
  }
  function resultTree(parent,value,label='Pełne wyniki') {
    const details=node('details');details.append(node('summary',label));
    if(Array.isArray(value)&&value.length&&value.every(r=>r&&typeof r==='object'&&!Array.isArray(r))&&value.every(r=>Object.values(r).every(v=>v===null||typeof v!=='object'))) {
      const keys=[...new Set(value.flatMap(r=>Object.keys(r)))];const wrap=node('div',undefined,'table-wrap');const table=node('table');const head=node('tr');keys.forEach(k=>head.append(node('th',k)));const thead=node('thead');thead.append(head);table.append(thead);const body=node('tbody');
      for(const row of value.slice(0,60)){const tr=node('tr');keys.forEach(k=>tr.append(node('td',fmt(row[k]))));body.append(tr);}table.append(body);wrap.append(table);
      const button=node('button',`Pobierz wszystkie ${value.length} wierszy CSV`);button.type='button';button.addEventListener('click',()=>download('ml1-table.csv',csvRows(value),'text/csv;charset=utf-8'));
      details.append(button,wrap);if(value.length>60)details.append(node('p','Podgląd: pierwszych 60 wierszy. Eksport CSV zawiera całą tabelę.'));
    } else if(value&&typeof value==='object'&&!Array.isArray(value)) {
      const simple=Object.entries(value).filter(([,v])=>v===null||typeof v!=='object');
      if(simple.length){const dl=node('dl');for(const [k,v] of simple){dl.append(node('dt',labels[k]||k),node('dd',fmt(v)));}details.append(dl);}
      for(const [key,item] of Object.entries(value))if(item&&typeof item==='object')resultTree(details,item,key);
    } else details.append(node('pre',JSON.stringify(value,null,2)));
    parent.append(details);
  }
  function chart(parent,title,series,xkey,ykey,xlabel,ylabel) {
    const colors=['#075879','#b75611','#47863d','#8a469a','#bc3131','#526cca'];
    const clean=series.map(s=>({name:s.name,rows:s.rows.filter(r=>Number.isFinite(r[xkey])&&Number.isFinite(r[ykey]))})).filter(s=>s.rows.length>1);
    if(!clean.length)return;
    const all=clean.flatMap(s=>s.rows);let xmin=Math.min(...all.map(r=>r[xkey])),xmax=Math.max(...all.map(r=>r[xkey])),ymin=Math.min(...all.map(r=>r[ykey])),ymax=Math.max(...all.map(r=>r[ykey]));
    if(xmin===xmax)xmax=xmin+1;if(ymin===ymax)ymax=ymin+1;
    const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 900 400');svg.setAttribute('role','img');svg.setAttribute('aria-label',title);svg.classList.add('chart');
    const elem=(tag,attrs,text)=>{const e=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;svg.append(e);return e;};
    elem('title',{},title);const x=v=>85+(v-xmin)/(xmax-xmin)*780,y=v=>340-(v-ymin)/(ymax-ymin)*290;
    elem('text',{x:85,y:25,'font-size':17},title);
    for(let i=0;i<=5;i++){let xv=xmin+(xmax-xmin)*i/5,yv=ymin+(ymax-ymin)*i/5;elem('line',{x1:x(xv),y1:50,x2:x(xv),y2:340,stroke:'#dce3e9'});elem('line',{x1:85,y1:y(yv),x2:865,y2:y(yv),stroke:'#dce3e9'});elem('text',{x:x(xv),y:360,'text-anchor':'middle','font-size':12},fmt(xv));elem('text',{x:77,y:y(yv)+4,'text-anchor':'end','font-size':12},fmt(yv));}
    elem('text',{x:475,y:389,'text-anchor':'middle','font-size':13},xlabel);elem('text',{x:90,y:45,'font-size':13},ylabel);
    const legend=node('div',undefined,'legend');clean.forEach((s,index)=>{const color=colors[index%colors.length];elem('polyline',{points:s.rows.map(r=>`${x(r[xkey])},${y(r[ykey])}`).join(' '),fill:'none',stroke:color,'stroke-width':2});for(const r of s.rows){const c=elem('circle',{cx:x(r[xkey]),cy:y(r[ykey]),r:3,fill:color});const t=document.createElementNS(ns,'title');t.textContent=`${s.name}: ${xlabel} ${fmt(r[xkey])}; ${ylabel} ${fmt(r[ykey])}`;c.append(t);}const text=node('span',s.name);text.style.color=color;legend.append(text);});parent.append(svg,legend);
  }
  function renderResult(result,method) {
    const root=$('results');root.replaceChildren();
    if(method==='workbook') {
      if(result.example_basis==='synthetic_educational_data')root.append(node('p','Dane syntetyczne. Wyniki służą do sprawdzenia metod ML1.','notice'));
      root.append(node('h3',result.p1.name));metrics(root,[['Masa w locie [kg]',result.p1.flight_mass_kg],['Pole z obrysu [m²]',result.p2.geometry.area_m2],['MAC [m]',result.p2.geometry.mac_m],['Oswald e',result.p3.least_squares.oswald_e]]);
      if(!result.p3.least_squares.oswald_in_course_range)root.append(node('p','Współczynnik Oswalda poza zakresem kontrolnym ML1 0,7–0,98. Sprawdź dane i aproksymację.','notice'));
      chart(root,'P3 · Biegunowa całego samolotu',[{name:'P3',rows:result.p3.polar.rows}],'cl','cd','Cz','Cx');
      chart(root,'P4 · Biegunowe prędkości',result.p4.cases.map(c=>({name:`${c.mass_kg} kg / ${c.altitude_m} m`,rows:c.rows})),'velocity_ms','sink_ms','V [m/s]','Opadanie [m/s]');
      if(result.p5)chart(root,'P5 · Zespół napędowy',result.p5.tables.map(t=>({name:`${t.altitude_m} m`,rows:t.rows.filter(r=>r.available)})),'velocity_ms',result.p1.propulsion==='jet'?'thrust_n':'useful_power_w','V [m/s]',result.p1.propulsion==='jet'?'Ciąg [N]':'Moc użyteczna [W]');
      if(result.p6) {
        const p=result.p6;metrics(root,[['Pułap teoretyczny [m]',p.offer.theoretical_ceiling_m],['Pułap praktyczny [m]',p.offer.practical_ceiling_m],['Czas do pułapu praktycznego [s]',p.offer.climb_to_practical_s],['Paliwo przelotowe [kg]',p.fuel_budget.cruise_fuel_kg]]);
        if(p.exact_force_tables?.length){const exact=p.exact_force_tables[0];chart(root,'P6 · Metoda mocy i dokładna równowaga sił',[
          {name:'Metoda mocy ML1',rows:p.offer.tables[0].rows.filter(r=>r.available)},
          {name:'Dokładna równowaga',rows:exact.rows.filter(r=>r.available).map(r=>({velocity_ms:r.velocity_ms,roc_ms:r.best_rate.roc_ms}))}
        ],'velocity_ms','roc_ms','V [m/s]','w [m/s]');}
        if(p.method_eligibility?.within_course_power_method_loading===false)root.append(node('p','Wskaźnik obciążenia mocy lub ciągu wymaga dokładniejszej metody niż metoda mocy ML1. Wyniki mają charakter przybliżony.','notice'));
        if(p.offer.tables.some(t=>!t.best_rate.within_small_angle_scope||!t.best_gradient.within_small_angle_scope))root.append(node('p','Część punktów najlepszego wznoszenia przekracza założenie małego kąta toru lotu (20°). Szczegóły zakresu znajdują się w tabelach.','notice'));
        chart(root,'P6 · Wykres ofertowy — wznoszenie',[{name:'wmax(h)',rows:p.offer.rows}],'altitude_m','maximum_roc_ms','h [m]','wmax [m/s]');
        chart(root,'P6 · Wykres ofertowy — prędkości',[{name:'Vmin(h)',rows:p.offer.rows.map(r=>({h:r.altitude_m,v:r.minimum_speed_ms}))},{name:'Vmax(h)',rows:p.offer.rows.map(r=>({h:r.altitude_m,v:r.maximum_speed_ms}))}],'h','v','h [m]','V [m/s]');
        const series=p.ranges.schedules.map(s=>({name:s.schedule,rows:s.rows.filter(r=>r.available)}));
        chart(root,'P6 · Zasięg — oba programy lotu',series,'reference_velocity_ms','range_km','V przy masie średniej [m/s]','Zasięg [km]');
        chart(root,'P6 · Długotrwałość — oba programy lotu',series,'reference_velocity_ms','time_h','V przy masie średniej [m/s]','Czas [h]');
        for(const s of p.ranges.schedules)metrics(root,[[`${s.schedule}: maks. zasięg [km]`,s.maximum_range?.range_km],[`${s.schedule}: maks. czas [h]`,s.maximum_endurance?.time_h]]);
        if(p.ranges.schedules.some(s=>s.rows.some(r=>!r.available)))root.append(node('p','Część warunków przelotu jest niedostępna. Tabele zawierają przyczyny: zakres danych, przeciągnięcie lub niedostateczny napęd.','notice'));
      } else root.append(node('p',result.propulsion_scope));
    } else if(result&&typeof result==='object') {
      if(result.rows) {
        const rows=result.rows.filter(r=>r&&r.available!==false);
        if(rows.some(r=>r.velocity_ms!==undefined&&r.roc_ms!==undefined))chart(root,'Wznoszenie', [{name:'w(V)',rows}],'velocity_ms','roc_ms','V [m/s]','w [m/s]');
        else if(rows.some(r=>r.cd_wing!==undefined))chart(root,'Biegunowa płata',[{name:'Płat',rows}],'cl','cd_wing','Cz','Cx');
        else if(rows.some(r=>r.cd!==undefined))chart(root,'Biegunowa',[{name:'Cx(Cz)',rows}],'cl','cd','Cz','Cx');
      }
      if(typeof result==='object'&&!Array.isArray(result))metrics(root,Object.entries(result).filter(([,v])=>typeof v==='number').slice(0,10));
    } else metrics(root,[['Wynik',result]]);
    resultTree(root,result);$('resultsSection').hidden=false;$('downloadResults').disabled=false;$('downloadReport').disabled=false;
  }
  async function run(event) {
    event.preventDefault();const form=event.currentTarget;let payload;
    try{payload=state.view==='workbook'?{method:'workbook',inputs:readForm($('workbookFields'),state.workbook)}:{method:state.method,inputs:readForm($('methodFields'),selectedMethod().inputs)};}catch(error){message(error.message,'error');return;}
    invalidate();save();const revision=state.revision,controller=new AbortController();state.controller=controller;
    message('Trwają obliczenia. Pełny zeszyt ze śmigłem stałym może potrwać około minuty.','pending');form.querySelector('button[type=submit]').disabled=true;
    try {
      const response=await fetch('/api/ml1/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal});const data=await response.json();
      if(!response.ok)throw Error(data.message||'Nie udało się wykonać obliczeń.');
      if(state.revision!==revision)return;
      state.last={payload,result:data.result};renderResult(data.result,payload.method);message('Obliczenia zakończone. Tabele, wykresy i eksport odnoszą się do bieżących danych.','success');
      $('resultsSection').scrollIntoView({behavior:'smooth',block:'start'});
    } catch(error) {if(error.name!=='AbortError'&&state.revision===revision)message(error.message,'error');}
    finally {form.querySelector('button[type=submit]').disabled=false;if(state.controller===controller)state.controller=null;}
  }
  function setView(view) {
    if(state.view!==view){save();invalidate();}state.view=view;
    for(const name of ['workbook','methods','sources'])$(name+'View').hidden=name!==view;
    document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===view)));
    save();
  }
  async function loadExample(kind) {
    const response=await fetch('/api/ml1/example/'+kind);if(!response.ok)throw Error('Nie udało się pobrać przykładu.');
    state.workbook=await response.json();invalidate();workbookFields();save();message('Wczytano przykład z danymi syntetycznymi.');
  }
  async function initialize() {
    const response=await fetch('/api/ml1/catalog');if(!response.ok)throw Error('Nie udało się pobrać katalogu ML1.');const data=await response.json();state.catalog=data.methods;
    let saved={};try{saved=JSON.parse(localStorage.getItem(KEY)||'{}');}catch{/* a damaged local draft does not disable the page */}
    state.drafts=saved.drafts||{};state.method=saved.method||data.methods[0].id;
    if(saved.workbook&&typeof saved.workbook==='object'){state.workbook=saved.workbook;workbookFields(saved.workbookDraft);}else await loadExample('propeller');
    filterMethods();for(const source of data.sources){const item=node('li');const link=node('a',source.file.replace(/^\d+-/,''));link.href=source.url;link.target='_blank';link.rel='noopener';item.append(link,node('small',source.pages?` · ${source.pages} stron`:''));$('sourceList').append(item);}
    document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
    $('projectFilter').addEventListener('change',()=>{save();invalidate();filterMethods();save();});
    $('methodSelect').addEventListener('change',()=>{save();invalidate();state.method=$('methodSelect').value;methodFields();save();});
    for(const name of ['workbookForm','methodForm']){$(name).addEventListener('submit',run);$(name).addEventListener('input',()=>{invalidate();save();});}
    $('loadExample').addEventListener('click',()=>loadExample($('exampleKind').value).catch(e=>message(e.message,'error')));
    $('importWorkbook').addEventListener('click',()=>$('workbookFile').click());
    $('workbookFile').addEventListener('change',async()=>{try{const file=$('workbookFile').files[0];if(file.size>4*1024*1024)throw Error('Plik przekracza 4 MB.');const parsed=JSON.parse(await file.text());const input=parsed.method==='workbook'?parsed.inputs:parsed;if(!input?.aircraft||!input?.geometry||!input?.profile)throw Error('Plik musi zawierać zeszyt ML1: aircraft, geometry, profile.');state.workbook=input;invalidate();workbookFields();save();message('Wczytano zeszyt.');}catch(e){message(e.message,'error');}finally{$('workbookFile').value='';}});
    $('exportWorkbook').addEventListener('click',()=>{try{download('ml1-inputs.json',JSON.stringify(readForm($('workbookFields'),state.workbook),null,2));}catch(e){message(e.message,'error');}});
    $('downloadResults').addEventListener('click',()=>{if(state.last)download('ml1-results.json',JSON.stringify({...state.last.payload,result:state.last.result},null,2));});
    $('downloadReport').addEventListener('click',async()=>{if(!state.last)return;const snapshot=state.last,revision=state.revision;const button=$('downloadReport');button.disabled=true;try{message('Przygotowuję raport z ponownym przeliczeniem danych.','pending');const response=await fetch('/ml1/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(snapshot.payload)});if(!response.ok){const error=await response.json();throw Error(error.message||'Błąd raportu.');}const text=await response.text();if(revision!==state.revision||state.last!==snapshot)return;download('ml1-report.html',text,'text/html;charset=utf-8');message('Pobrano samodzielny raport HTML. Można wydrukować go do PDF.','success');}catch(e){if(revision===state.revision)message(e.message,'error');}finally{button.disabled=!state.last;}});
    setView(['workbook','methods','sources'].includes(saved.view)?saved.view:'workbook');
    $('saveStatus').textContent='Dane zapisane w tej przeglądarce';
  }
  window.ML1Data={parseCSV,groupCSV};
  initialize().catch(error=>message(error.message,'error'));
})();

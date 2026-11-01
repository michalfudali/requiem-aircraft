/* Interactive trim-ballast design aid; it never silently changes aircraft mass. */
(function(){
  'use strict';
  const $=id=>document.getElementById(id),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=(v,d=3)=>Number(v).toLocaleString('pl-PL',{minimumFractionDigits:d,maximumFractionDigits:d}),tex=v=>String(Number(v.toPrecision(10)));
  let model=null,projectName='',optimal=null,chosen=null;
  const fail=r=>r.reason==='mass'?'Przekroczona masa projektowa; dodanie balastu jej nie zmniejszy.':'Brak wspólnego rozwiązania dla wszystkich stanów przy zadanych kryteriach i zapasie masy.';
  function equations(result){
    const lines=[{label:'Wybrana masa każdej osoby załogi',tex:`m_{os}=${tex(result.person_kg)}\\;\\mathrm{kg}`},
      {label:'Masa i moment balastu',tex:'Z=w x_B,\\qquad x_{SM,i}^{nowy}=\\frac{M_i+Z}{m_i+w},\\qquad w\\geq0'},
      {label:'Badany zakres położeń',tex:`${tex(model.station_domain_m[0])}w\\leq Z\\leq${tex(model.station_domain_m[1])}w`}];
    if(result.feasible){lines.push({label:'Minimalna masa w wybranym położeniu',tex:`w=${tex(result.mass_kg)}\\;\\mathrm{kg},\\quad Z=${tex(result.moment_kg_m)}\\;\\mathrm{kg\\,m}`});
      if(result.station_m!==null)lines.push({label:'Położenie balastu',tex:`x_B=${tex(result.station_m)}\\;\\mathrm{m}`});
      for(const row of result.after){const before=result.before.find(x=>x.key===row.key);lines.push({label:row.name+' — wyważenie po dodaniu balastu',tex:`x_{SM}=\\frac{${tex(before.moment_kg_m)}+${tex(result.moment_kg_m)}}{${tex(before.mass_kg)}+${tex(result.mass_kg)}}=${tex(row.xcg_m)}\\;\\mathrm{m}`});}
    }else lines.push({label:fail(result),tex:'\\mathcal F=\\varnothing'});
    return lines;
  }
  function render(){
    if(!model)return;
    const p=Number($('pilotLoadingMass').value),station=Number($('ballastStation').value);
    optimal=BipolBallast.solve(model,p);chosen=BipolBallast.solve(model,p,station);
    $('ballastStationValue').textContent=fmt(station)+' m';
    $('ballastOptimal').textContent=optimal.status==='unnecessary'?'Balast niepotrzebny dla tej masy załogi.':optimal.feasible
      ?`Minimum w całym badanym zakresie: ${fmt(optimal.mass_kg)} kg przy x = ${fmt(optimal.station_m)} m od nosa.`:fail(optimal);
    $('ballastUseOptimal').disabled=!$('pilotLoadingStale').hidden||!optimal.feasible||optimal.mass_kg===0;
    $('ballastResult').textContent=chosen.feasible?`Wybrane miejsce: ${fmt(station)} m. Minimalny wspólny balast: ${fmt(chosen.mass_kg)} kg. Zapas masy przed korektą: ${fmt(chosen.mass_headroom_kg)} kg.`:fail(chosen);
    $('ballastResult').dataset.feasible=String(chosen.feasible);$('ballastResult').dataset.mass=String(chosen.mass_kg);
    $('ballastStates').innerHTML=chosen.before.map(before=>{const after=chosen.after.find(v=>v.key===before.key);return `<tr><td>${esc(before.name)}</td><td>${fmt(before.xcg_mac_pct,2)}</td><td>${after?fmt(after.xcg_mac_pct,2):'—'}</td><td>${after?fmt(after.mass_kg,2):'—'}</td><td>${after?fmt(after.static_margin_pct,2):'—'}</td><td>${after?(after.passed?'Spełnione':esc(after.failed.join(', '))):'Brak korekty'}</td></tr>`;}).join('');
    const math=$('ballastMath');math.replaceChildren();
    for(const row of equations(chosen).slice(1,5)){const el=document.createElement('div');math.append(el);katex.render(row.tex,el,{displayMode:true,throwOnError:false});}
    const W=Math.max(340,$('ballastAxis').clientWidth||720),L=28,R=W-28,H=94,[lo,hi]=model.station_domain_m,x=v=>L+(v-lo)/(hi-lo)*(R-L);
    let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Położenie balastu na osi kadłuba"><path d="M${L} 36H${R}" stroke="#8199a7" stroke-width="2"/>`;
    for(let i=0;i<=4;i++){const pos=lo+(hi-lo)*i/4;svg+=`<path d="M${x(pos)} 31V41" stroke="#8199a7"/><text x="${x(pos)}" y="62" text-anchor="middle">${fmt(pos,1)} m</text>`;}
    if(optimal.feasible&&optimal.mass_kg>0)svg+=`<path d="M${x(optimal.station_m)-5} 22l5 -8l5 8Z" fill="#087f77"/>`;
    svg+=`<circle cx="${x(station)}" cy="36" r="6" fill="#2175a1"/><text x="${L}" y="86">Nos</text><text x="${R}" y="86" text-anchor="end">Tył kadłuba</text></svg>`;
    $('ballastAxis').innerHTML=svg;
  }
  document.addEventListener('DOMContentLoaded',()=>{
    if(!$('ballastPanel'))return;
    $('ballastStation').addEventListener('input',render);$('pilotLoadingMass').addEventListener('input',render);
    $('ballastPanel').addEventListener('toggle',()=>{if($('ballastPanel').open)render();});
    $('ballastUseOptimal').addEventListener('click',()=>{if(optimal?.feasible&&optimal.station_m!==null){$('ballastStation').value=optimal.station_m;render();}});
    $('ballastGraph').addEventListener('click',()=>{document.querySelector('[data-studio-nav="tab-calculation-tree"]')?.click();const tree=window.BipolCalculationTree,key=tree?.state.model?.byId.has('ballast_light_mass')?'ballast_light_mass':'ballast_light_problem';tree?.selectEntry(key,true);});
    $('ballastExport').addEventListener('click',()=>{
      if(!model||!chosen||!$('pilotLoadingStale').hidden)return;
      const rows=equations(chosen);
      for(const c of chosen.constraints)rows.push({label:c.state_name+' — '+c.label,tex:`(${tex(c.a)})w+(${tex(c.b)})Z+(${tex(c.c)})\\geq0`});
      const data={version:1,project_name:projectName+' / analiza balastu',nodes:rows.map((v,i)=>({...v,id:'ballast-'+i,source:'FAA-H-8083-1B, rozdz. 7; kryteria P3',note:i===0?model.note:''})),edges:[]};
      const content=BipolCalculationGraph.latex(BipolCalculationGraph.build(data),data.nodes.map(n=>n.id),false);
      const url=URL.createObjectURL(new Blob([content],{type:'application/x-tex;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='analiza_balastu_'+chosen.person_kg+'kg.tex';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    });
    document.addEventListener('bipol:project',()=>{model=null;});
    document.addEventListener('bipol:results',e=>{
      model=e.detail?.balance?.pilot_loading?.ballast?.model;projectName=e.detail?.params?.name||'Projekt';if(!model)return;
      $('ballastNote').textContent=model.note;
      const p=Number($('pilotLoadingMass').value),solution=BipolBallast.solve(model,p),slider=$('ballastStation');
      slider.min=model.station_domain_m[0];slider.max=model.station_domain_m[1];slider.value=solution.station_m??model.crew_arm_m;render();
    });
    rootExpose();
  });
  function rootExpose(){window.BipolBallastUI={get model(){return model;},get optimal(){return optimal;},get chosen(){return chosen;}};}
})();

/* Fixed-airframe loading exploration; actual mass moments come from P3. */
(function(){
  'use strict';
  const $=id=>document.getElementById(id),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=(n,d=2)=>Number(n).toLocaleString('pl-PL',{minimumFractionDigits:d,maximumFractionDigits:d});
  const interval=v=>v?`${fmt(v.min_kg)}–${fmt(v.max_kg)} kg/os`:'Brak wspólnego przedziału';
  let study=null,geom=null,bal=null;
  function point(c,p){const m=c.base_mass_kg+study.n_crew*p,q=c.base_moment_kg_m+study.n_crew*p*study.crew_arm_m,x=q/m;
    return {mass:m,moment:q,x,pct:100*(x-bal.x_lemac_m)/geom.wing.mac,failed:c.constraints.filter(v=>v.a*p+v.b < -1e-9)};}
  function draw(){
    if(!study?.available)return;
    const c=study.cases.find(v=>v.key===$('pilotLoadingCase').value)||study.cases[0],p=Number($('pilotLoadingMass').value),v=point(c,p),kn=bal.neutral_point.x_n_mac_pct-v.pct;
    $('pilotLoadingMassValue').textContent=fmt(p,1)+' kg/os.';
    const read=$('pilotLoadingReadout');read.dataset.failed=String(v.failed.length>0);
    read.textContent=`Masa: ${fmt(v.mass)} kg · ŚC: ${fmt(v.pct)}% ŚDA · zapas stateczności: ${fmt(kn)}% ŚDA. `+
      (v.failed.length?'Niespełnione: '+v.failed.map(x=>x.label).join(', ')+'.':'Spełnione kryteria modelu dla tego stanu.')+
      (v.mass>study.limits.maximum_mass_kg+1e-9?` Przekroczenie masy projektowej: ${fmt(v.mass-study.limits.maximum_mass_kg)} kg.`:'');
    read.dataset.mass=String(v.mass);read.dataset.cg=String(v.pct);read.dataset.margin=String(kn);
    const limits=[{v:study.limits.aft_pct,label:'Tylne ŚC P3',color:'#9b6a23'},
      {v:study.limits.stability_aft_pct,label:'Zapas 5% ŚDA',color:'#925046'}];
    if(study.limits.forward_pct!==null)limits.push({v:study.limits.forward_pct,label:'Przednie ŚC P3',color:'#9b6a23'});
    const ymin=Math.min(...c.samples.map(x=>x.xcg_mac_pct),...limits.map(x=>x.v))-3,ymax=Math.max(...c.samples.map(x=>x.xcg_mac_pct),...limits.map(x=>x.v))+3;
    const W=Math.max(340,$('pilotLoadingChart').clientWidth||760),H=300,L=65,R=22,T=24,B=48,[lo,hi]=study.domain_kg;
    const x=a=>L+(a-lo)/(hi-lo)*(W-L-R),y=a=>H-B-(a-ymin)/(ymax-ymin)*(H-T-B);
    let svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Wpływ masy osoby na ŚC w stanie: ${esc(c.name)}"><title>Środek ciężkości od masy każdej osoby załogi</title><rect width="${W}" height="${H}" fill="#f8fafc"/>`;
    if(c.interval)svg+=`<rect x="${x(c.interval.min_kg)}" y="${T}" width="${Math.max(0,x(c.interval.max_kg)-x(c.interval.min_kg))}" height="${H-T-B}" fill="#087f7712"/>`;
    for(let i=0;i<=4;i++){const a=lo+(hi-lo)*i/4,b=ymin+(ymax-ymin)*i/4;svg+=`<path d="M${L} ${y(b)}H${W-R}" stroke="#dce6eb"/><text x="${L-8}" y="${y(b)+4}" text-anchor="end">${fmt(b,1)}</text><text x="${x(a)}" y="${H-B+22}" text-anchor="middle">${fmt(a,1)}</text>`;}
    for(const l of limits)svg+=`<path d="M${L} ${y(l.v)}H${W-R}" stroke="${l.color}" stroke-dasharray="5 4"/>`;
    $('pilotLoadingLegend').innerHTML=limits.map(l=>`<span style="color:${l.color}">${esc(l.label)}: ${fmt(l.v)}%</span>`).join('');
    svg+=`<polyline points="${c.samples.map(a=>`${x(a.person_kg)},${y(a.xcg_mac_pct)}`).join(' ')}" fill="none" stroke="#087f77" stroke-width="2.5"/>`;
    for(const a of c.samples.filter(a=>!a.passed))svg+=`<circle cx="${x(a.person_kg)}" cy="${y(a.xcg_mac_pct)}" r="2.2" fill="#be4646"/>`;
    svg+=`<path d="M${x(p)} ${T}V${H-B}" stroke="#2175a1" stroke-dasharray="3 3"/><circle cx="${x(p)}" cy="${y(v.pct)}" r="5" fill="#2175a1" stroke="#fff" stroke-width="2"/><text x="${(L+W-R)/2}" y="${H-5}" text-anchor="middle">Masa każdej osoby załogi z wyposażeniem [kg]</text><text transform="translate(17 ${(T+H-B)/2}) rotate(-90)" text-anchor="middle">ŚC [% ŚDA]</text></svg>`;
    $('pilotLoadingChart').innerHTML=svg;
    $('pilotLoadingChart').querySelector('svg').style.cssText='font:12px system-ui,sans-serif;fill:#526a7a';
    const math=$('pilotLoadingMath');math.replaceChildren();
    const tex=n=>String(Number(n.toPrecision(8)));
    for(const formula of [
      `x_{SM}=\\frac{M_b+n_{zał}m_{os}x_{zał}}{m_b+n_{zał}m_{os}}=\\frac{${tex(c.base_moment_kg_m)}+${study.n_crew}\\cdot${tex(p)}\\cdot${tex(study.crew_arm_m)}}{${tex(c.base_mass_kg)}+${study.n_crew}\\cdot${tex(p)}}=${tex(v.x)}\\;\\mathrm{m}`,
      `\\bar x_{SM}=100\\frac{x_{SM}-x_{N,\\bar c}}{\\bar c}=100\\frac{${tex(v.x)}-${tex(bal.x_lemac_m)}}{${tex(geom.wing.mac)}}=${tex(v.pct)}\\%`,
      `K_n=\\bar x_N-\\bar x_{SM}=${tex(bal.neutral_point.x_n_mac_pct)}-${tex(v.pct)}=${tex(kn)}\\%`
    ]){const el=document.createElement('div');math.append(el);if(window.katex)katex.render(formula,el,{displayMode:true,throwOnError:false});else el.textContent=formula;}
  }
  document.addEventListener('DOMContentLoaded',()=>{
    if(!$('pilotLoading'))return;
    function stale(value=true){if(!study?.available)return;$('pilotLoadingStale').hidden=!value;for(const id of ['pilotLoadingCase','pilotLoadingMass','pilotLoadingGraph'])$(id).disabled=value;}
    document.addEventListener('bipol:project',()=>{study=null;$('pilotLoading').hidden=true;});
    document.addEventListener('bipol:calculating',()=>stale());
    $('designForm')?.addEventListener('input',()=>stale(),true);$('designForm')?.addEventListener('change',()=>stale(),true);
    new ResizeObserver(()=>{if($('pilotLoadingChart').clientWidth)draw();}).observe($('pilotLoadingChart'));
    $('pilotLoadingCase').addEventListener('change',draw);$('pilotLoadingMass').addEventListener('input',draw);
    $('pilotLoadingGraph').addEventListener('click',()=>{document.querySelector('[data-studio-nav="tab-calculation-tree"]')?.click();window.BipolCalculationTree?.selectEntry('pilot_'+$('pilotLoadingCase').value+'_heavy_pct',true);});
    document.addEventListener('bipol:results',e=>{
      const r=e.detail;study=r?.balance?.pilot_loading;geom=r?.geometry;bal=r?.balance;
      $('pilotLoading').hidden=!study?.available;if(!study?.available)return;
      stale(false);
      $('pilotLoadingNote').textContent=study.note;
      $('pilotLoadingCS22').textContent=['cs22_glider','cs22_motoglider'].includes(r.params.category)?study.cs22_note:'';
      $('pilotLoadingInterval').textContent='Wspólny przedział dla wszystkich stanów w badanym zakresie: '+interval(study.common_interval)+'.';
      $('pilotLoadingCase').innerHTML=study.cases.map(c=>`<option value="${esc(c.key)}">${esc(c.name)}</option>`).join('');$('pilotLoadingCase').value='mtow';
      const slider=$('pilotLoadingMass');slider.min=study.domain_kg[0];slider.max=study.domain_kg[1];slider.value=study.nominal_person_kg;
      $('pilotLoadingRows').innerHTML=study.cases.map(c=>`<tr><td>${esc(c.name)}</td><td>${fmt(c.light.xcg_mac_pct)}</td><td>${fmt(c.heavy.xcg_mac_pct)}</td><td>${fmt(c.heavy.mass_excess_kg)}</td><td>${interval(c.interval)}</td></tr>`).join('');
      $('pilotLoadingConstraints').innerHTML=study.cases.flatMap(c=>c.constraints.map(v=>`<tr><td>${esc(c.name)}</td><td>${esc(v.label)}</td><td>${fmt(v.a,6)}</td><td>${fmt(v.b,6)}</td></tr>`)).join('');draw();
    });
  });
})();

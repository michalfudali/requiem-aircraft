/* Interactive calculation graph. Numbers and worked LaTeX come from the API sheet. */
(function(root){
  'use strict';
  const colors={const:'#8198a7',p1:'#268e96',p2:'#268b69',p3:'#8061b2',p4:'#4d83b5',p5:'#bb8542',p6:'#ba6174'};
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const kindLabel={given:'Dana / model',calc:'Obliczenie',solve:'Rozwiązanie numeryczne',table:'Wzór tabelaryczny',procedure:'Procedura iteracyjna'};
  function math(source,display=false){
    if(!source)return '';
    if(!root.katex)return esc(source);
    return root.katex.renderToString(source,{displayMode:display,throwOnError:false,strict:'ignore',trust:false,maxExpand:1000});
  }
  function number(value){return typeof value==='number'&&Number.isFinite(value)?value.toLocaleString('pl-PL',{maximumFractionDigits:3}):'—';}
  function value(n){return n.value_tex?math(n.sym?`${n.sym}=${n.value_tex}`:n.value_tex):n.kind==='table'?'Zależność tabelaryczna':number(n.value);}
  function element(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
  function init(){
    const $=id=>document.getElementById(id),panel=$('tab-calculation-tree'),vp=$('calculationTreeRoot');if(!panel||!vp)return;
    const G=root.BipolCalculationGraph;
    const state={model:null,view:null,camera:{x:0,y:0,scale:1},scope:'overview',selected:null,selectedGroup:null,
      stale:false,world:null,buttons:new Map(),paths:[],dimensions:{width:0,height:0},needsFit:true,suppressClickUntil:0};
    let frame=0,lastPointer=0;const pointers=new Map();let gesture=null;
    const active=()=>panel.classList.contains('active');
    function dims(){state.dimensions={width:vp.clientWidth,height:vp.clientHeight};return state.dimensions;}
    function status(text){$('calculationTreeStatus').textContent=text;$('calculationTreeStatus').classList.toggle('is-stale',state.stale);}
    function updateStatus(){
      if(!state.model)return;
      const displayed=state.view?.nodes.length||0;
      status(`${state.stale?'Wyniki wymagają przeliczenia. ':''}${state.model.data.project_name} · ${state.model.data.nodes.length} wielkości · ${displayed} kart w tym widoku.`);
      $('calculationGraphStale').hidden=!state.stale;
      panel.querySelector('[data-graph-action=latex]').disabled=state.stale||!state.view;
    }
    function camera(){
      if(!state.world)return;
      const c=state.camera;state.world.style.transform=`translate(${c.x}px,${c.y}px) scale(${c.scale})`;
      $('calculationGraphZoom').textContent=Math.round(c.scale*100)+'%';
      const rect=$('calculationGraphMinimap').querySelector('[data-camera]');
      if(rect){rect.setAttribute('x',-c.x/c.scale);rect.setAttribute('y',-c.y/c.scale);rect.setAttribute('width',vp.clientWidth/c.scale);rect.setAttribute('height',vp.clientHeight/c.scale);}
    }
    function scheduleCamera(){if(!frame)frame=requestAnimationFrame(()=>{frame=0;camera();});}
    function fit(){if(!state.view||!vp.clientWidth)return;const d=dims();state.camera=G.fit(state.view.bounds,d.width,d.height,48);state.needsFit=false;camera();}
    function focus(id,readable=false){
      if(!state.view)return;const visual=state.view.byId.get(state.view.map.get(id)||id);if(!visual)return;
      const d=dims();state.camera=G.center(state.camera,visual,d.width,d.height,readable?Math.min(1.1,Math.max(.85,state.camera.scale)):state.camera.scale);state.needsFit=false;camera();
    }
    function close(clear=false){
      $('calculationGraphInspector').hidden=true;delete $('calculationGraphWorkspace').dataset.inspecting;
      if(clear){state.selected=null;state.selectedGroup=null;}highlight();
    }
    function minimap(){
      const v=state.view,b=v.bounds;
      $('calculationGraphMinimap').innerHTML=`<svg viewBox="0 0 ${b.width} ${b.height}" aria-hidden="true">${v.nodes.map(n=>`<rect x="${n.x}" y="${n.y}" width="${n.width}" height="${n.height}" rx="8" fill="${colors[n.project]||'#91a8b4'}" opacity=".6"/>`).join('')}<rect data-camera fill="#168c8315" stroke="#087f77" stroke-width="${Math.max(2,b.width/180)}"/></svg>`;
      $('calculationGraphMinimap').hidden=false;
    }
    function nodeHTML(n){
      const samples=n.samples.map(id=>state.model.byId.get(id));
      if(n.kind==='project')return `<span class="calc-graph-node-header"><span>${n.project==='const'?'ISA / DANE':esc(n.project.toUpperCase())}</span><span>${n.members.length} wielkości</span></span><strong class="calc-graph-node-title">${esc(n.label)}</strong><span class="calc-graph-node-preview">${samples.map(s=>`<span>${value(s)}</span>`).join('')}</span><small>Wybierz etap, aby zobaczyć obliczenia →</small>`;
      const grouped=['data','portal','cycle'].includes(n.kind),primary=samples[0];
      return `<span class="calc-graph-node-header"><span>${esc(n.project==='const'?'ISA':n.project.toUpperCase())} · ${n.kind==='cycle'?'SPRZĘŻENIE':n.kind==='data'?'DANE / MODEL':n.kind==='portal'?'POPRZEDNI ETAP':esc(kindLabel[n.kind]||'WYNIK')}</span><span>${grouped?n.members.length:''}</span></span><strong class="calc-graph-node-title">${esc(n.label)}</strong><span class="calc-graph-node-value">${primary?value(primary):''}</span><small>${grouped?(n.kind==='cycle'?'Wzajemne zależności · rozwiń szczegóły':'Wybierz, aby zobaczyć wszystkie wartości'):'Wzór · podstawienie · wynik'}</small>`;
    }
    function draw(reset=true){
      if(!state.model||!active())return;
      try{state.view=G.project(state.model,state.scope,state.selected);}
      catch(error){status(error.message);return;}
      const view=state.view;state.buttons.clear();state.paths=[];
      const world=element('div',undefined,'calc-graph-world');world.style.width=view.bounds.width+'px';world.style.height=view.bounds.height+'px';
      const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.classList.add('calc-graph-edges');svg.setAttribute('width',view.bounds.width);svg.setAttribute('height',view.bounds.height);svg.setAttribute('aria-hidden','true');
      svg.innerHTML='<defs><marker id="calcGraphArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="context-stroke"/></marker></defs>';
      for(const edge of view.edges){const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',G.edgePath(edge,view));path.setAttribute('marker-end','url(#calcGraphArrow)');path.classList.add('calc-graph-edge');const stages=['const','p1','p2','p3','p4','p5','p6'];if(view.isOverview&&stages.indexOf(view.byId.get(edge.source).project)>stages.indexOf(view.byId.get(edge.target).project))path.classList.add('is-feedback');svg.append(path);state.paths.push({path,edge});}
      world.append(svg);
      for(const node of view.nodes){
        const button=element('button',undefined,`calc-graph-node is-${node.kind}`);button.type='button';button.dataset.graphId=node.id;
        button.style.cssText=`left:${node.x}px;top:${node.y}px;width:${node.width}px;height:${node.height}px;--phase-color:${colors[node.project]||'#168c83'}`;
        button.innerHTML=nodeHTML(node);button.setAttribute('aria-label',node.label+(node.members.length>1?`, ${node.members.length} wielkości`:''));
        button.addEventListener('click',()=>{if(performance.now()<state.suppressClickUntil)return;selectGroup(node);});
        button.addEventListener('focus',()=>{if(performance.now()-lastPointer<500)return;const r=button.getBoundingClientRect(),p=vp.getBoundingClientRect();if(r.left<p.left||r.right>p.right||r.top<p.top||r.bottom>p.bottom)focus(node.id,true);});
        world.append(button);state.buttons.set(node.id,button);
      }
      vp.replaceChildren(world);state.world=world;minimap();highlight();updateStatus();
      if(reset||state.needsFit){
        if(!['overview','all','path'].includes(state.scope)){
          const preferred={p1:'m_lad',p2:'m0',p3:'S',p4:'Cx0',p5:'V_S',p6:'V_D',const:'g'}[state.scope];
          if(preferred&&view.map.has(preferred)){state.camera.scale=.9;focus(preferred);}
          else fit();
        }else fit();
      }else camera();
    }
    function highlight(){
      if(!state.view||!state.model)return;
      const selected=state.selected?state.view.map.get(state.selected):state.selectedGroup;
      const roots=state.selected?[state.selected]:state.view.byId.get(state.selectedGroup)?.members||[];
      const related=G.ancestors(state.model,roots);
      const relatedVisual=new Set([...related].map(id=>state.view.map.get(id)));
      for(const [id,button] of state.buttons){button.classList.toggle('is-selected',id===selected);button.classList.toggle('is-related',id!==selected&&relatedVisual.has(id));button.classList.toggle('is-muted',!!selected&&id!==selected&&!relatedVisual.has(id));button.setAttribute('aria-pressed',String(id===selected));}
      for(const {path,edge} of state.paths){const on=relatedVisual.has(edge.source)&&relatedVisual.has(edge.target);path.classList.toggle('is-active',on);path.classList.toggle('is-muted',!!selected&&!on&&edge.target!==selected&&edge.source!==selected);}
    }
    function openInspector(title,kicker){
      $('calculationGraphDetailTitle').textContent=title;$('calculationGraphDetailKicker').textContent=kicker;
      $('calculationGraphInspector').hidden=false;$('calculationGraphWorkspace').dataset.inspecting='true';$('calculationGraphDetail').replaceChildren();
      $('calculationGraphInspector').scrollTop=0;
    }
    function jumpButton(id){const n=state.model.byId.get(id),b=element('button',n.label);b.type='button';b.dataset.graphEntry=id;b.addEventListener('click',()=>selectEntry(id,true));return b;}
    function groupedList(parent,ids){
      const box=element('div',undefined,'calc-graph-group'),sections=new Map();
      for(const id of ids){const n=state.model.byId.get(id);if(!sections.has(n.section))sections.set(n.section,[]);sections.get(n.section).push(n);}
      let index=0;
      for(const [key,nodes] of sections){const details=element('details');details.open=index++===0;details.append(element('summary',(state.model.data.sections.find(s=>s.key===key)?.title||'Procedura iteracyjna')+` · ${nodes.length}`));for(const n of nodes){const b=jumpButton(n.id),v=element('span');v.innerHTML=n.value_tex?math(n.value_tex):number(n.value);b.append(v);details.append(b);}box.append(details);}parent.append(box);
    }
    function selectGroup(group){
      if(!state.model)return;
      if(!['project','cycle','data','portal'].includes(group.kind))return selectEntry(group.members[0]);
      state.selected=null;state.selectedGroup=group.id;
      openInspector(group.label,group.kind==='cycle'?'Sprzężenie obliczeń':group.project==='const'?'Stałe i atmosfera':group.project.toUpperCase());
      const detail=$('calculationGraphDetail');
      if(group.kind==='cycle')detail.append(element('p','Te wielkości zależą od siebie. Wyznacza je wspólne rozwiązanie iteracyjne; kolejność kart nie oznacza niezależnych kroków.','calc-graph-detail-note'));
      if(group.kind==='project'||group.kind==='portal'){
        const button=element('button','Rozwiń etap na wielkości →','calc-graph-detail-action');button.type='button';button.addEventListener('click',()=>{state.scope=group.project;$('calculationGraphScope').value=state.scope;draw();});detail.append(button);
      }
      detail.append(element('p',`${group.members.length} wielkości. Wybierz pozycję, aby przejść do jej wzoru i podstawienia.`));groupedList(detail,group.members);highlight();focus(group.id);
    }
    function equation(parent,source,cls=''){if(!source)return;const p=element('div',undefined,'calc-graph-equation '+cls);p.innerHTML=math(source,true);parent.append(p);}
    function dependencyList(parent,ids,title){if(!ids.length)return;parent.append(element('h3',title));const box=element('div',undefined,'calc-graph-dependencies');ids.forEach(id=>box.append(jumpButton(id)));parent.append(box);}
    function iterationList(parent,node){
      if(!(node.iterations||[]).length)return;
      parent.append(element('h3',`Pełne obliczenia · ${node.iterations.length} iteracji`));
      for(const row of node.iterations){
        const details=element('details',undefined,'calc-graph-iteration');details.dataset.graphIteration=String(row.number);
        details.append(element('summary',`Iteracja ${row.number} · m₀ = ${number(row.mass_kg)} kg`));
        details.addEventListener('toggle',()=>{if(!details.open||details.dataset.rendered)return;details.dataset.rendered='true';for(const step of row.steps){details.append(element('p',`${step.point}. ${step.label}`));equation(details,step.tex,'is-worked');}});
        parent.append(details);
      }
    }
    function selectEntry(id,navigate=false){
      if(!state.model?.byId.has(id))return;
      state.selected=id;state.selectedGroup=null;const n=state.model.byId.get(id);
      const pathOption=$('calculationGraphScope').querySelector('[value=path]');pathOption.disabled=false;
      if(navigate||state.view?.isOverview||!state.view?.map.has(id)){state.scope='path';$('calculationGraphScope').value='path';draw(false);}
      openInspector(n.label,`${n.project==='const'?'Stałe / ISA':n.project.toUpperCase()} · ${kindLabel[n.kind]||n.kind}`);
      const detail=$('calculationGraphDetail');
      if(state.stale)detail.append(element('p','Dane z poprzedniego obliczenia. Przelicz projekt, aby zaktualizować wynik i pobrać obliczenia.','calc-graph-detail-note'));
      if(n.value_tex)equation(detail,n.sym?`${n.sym}=${n.value_tex}`:n.value_tex,'is-result');
      if(n.formula){detail.append(element('h3',n.kind==='solve'?'Warunek rozwiązania':'Wzór ogólny'));equation(detail,n.sym&&n.kind!=='solve'?`${n.sym}=${n.formula}`:n.formula);}
      if(n.substitution_tex){detail.append(element('h3','Podstawienie liczb'));equation(detail,`${n.sym}=${n.substitution_tex}`);}
      if(n.tex){detail.append(element('h3',n.kind==='given'?'Wartość przyjęta w modelu':'Pełny zapis obliczenia'));equation(detail,n.tex,'is-worked');}
      if(n.consistent!==null&&n.consistent!==undefined)detail.append(element('p',n.consistent?'Podstawienie zgodne z wynikiem programu.':'Kontrola podstawienia wskazuje różnicę — sprawdź model i dokładność.','calc-graph-check'+(n.consistent?'':' is-warning')));
      if(n.note)detail.append(element('p',n.note,'calc-graph-detail-note'));
      if(n.source)detail.append(element('p','Źródło: '+n.source,'calc-graph-source'));
      const component=state.model.componentById.get(id);
      if(component.cyclic){const note=element('div',undefined,'calc-graph-detail-note');note.append(element('strong',`Grupa sprzężeń · ${component.members.length} wielkości`));const more=element('details');more.append(element('summary','Pokaż wielkości we wspólnym rozwiązaniu'));groupedList(more,component.members);note.append(more);detail.append(note);}
      dependencyList(detail,state.model.parents.get(id),'Użyte do obliczenia');
      dependencyList(detail,state.model.children.get(id),'Wykorzystywane dalej');
      iterationList(detail,n);highlight();focus(id,true);updateStatus();
    }
    function search(){
      const q=$('calculationGraphSearch').value,box=$('calculationGraphMatches');box.replaceChildren();
      const matches=state.model?G.search(state.model,q):[];box.hidden=!q.trim();$('calculationGraphSearch').setAttribute('aria-expanded',String(!box.hidden));
      if(!matches.length&&q.trim())box.append(element('p','Brak pasujących wielkości.'));
      for(const n of matches){const b=element('button',n.label);b.type='button';b.dataset.graphMatch=n.id;b.append(element('small',`${n.project.toUpperCase()} · ${n.id}`));b.addEventListener('click',()=>{box.hidden=true;$('calculationGraphSearch').setAttribute('aria-expanded','false');selectEntry(n.id,true);});box.append(b);}
    }
    function latex(){
      if(!state.model||state.stale||!state.view)return;
      let ids=state.selected?[state.selected]:state.selectedGroup?state.view.byId.get(state.selectedGroup)?.members:null;
      ids??=[...state.view.map.keys()];const text=G.latex(state.model,ids,true);
      const url=URL.createObjectURL(new Blob([text],{type:'application/x-tex;charset=utf-8'}));const link=element('a');link.href=url;link.download='tok-obliczen.tex';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
    panel.addEventListener('click',event=>{
      const action=event.target.closest('[data-graph-action]')?.dataset.graphAction;if(!action)return;
      if(action==='close'){close();return;}if(action==='latex'){latex();return;}if(!state.view)return;
      if(action==='fit'){fit();return;}
      const d=dims();if(action==='actual')state.camera=G.zoom(state.camera,1/state.camera.scale,d.width/2,d.height/2);
      else state.camera=G.zoom(state.camera,action==='in'?1.25:.8,d.width/2,d.height/2);camera();
    });
    $('calculationGraphScope').addEventListener('change',()=>{state.scope=$('calculationGraphScope').value;state.selectedGroup=null;if(state.scope!=='path')state.selected=null;close();draw();});
    $('calculationGraphSearch').addEventListener('input',search);
    $('calculationGraphSearch').addEventListener('keydown',event=>{if(event.key==='ArrowDown'){$('calculationGraphMatches').querySelector('button')?.focus();event.preventDefault();}if(event.key==='Escape'){$('calculationGraphMatches').hidden=true;$('calculationGraphSearch').setAttribute('aria-expanded','false');}});
    document.addEventListener('click',event=>{if(!event.target.closest('.calc-graph-search')){$('calculationGraphMatches').hidden=true;$('calculationGraphSearch').setAttribute('aria-expanded','false');}});
    vp.addEventListener('wheel',event=>{if(!state.view)return;event.preventDefault();const r=vp.getBoundingClientRect();state.camera=G.zoom(state.camera,Math.exp(-event.deltaY*.0015),event.clientX-r.left,event.clientY-r.top);scheduleCamera();},{passive:false});
    function begin(){
      if(!pointers.size){gesture=null;return;}
      const ps=[...pointers.values()];gesture={camera:{...state.camera},start:ps[0],dragged:false};
      if(ps.length>1){gesture.mid={x:(ps[0].x+ps[1].x)/2,y:(ps[0].y+ps[1].y)/2};gesture.distance=Math.hypot(ps[0].x-ps[1].x,ps[0].y-ps[1].y);}
    }
    vp.addEventListener('pointerdown',event=>{if(event.button!==0&&event.pointerType==='mouse')return;if(!state.view)return;lastPointer=performance.now();pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});begin();});
    vp.addEventListener('pointermove',event=>{
      if(!pointers.has(event.pointerId)||!gesture)return;
      pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});const ps=[...pointers.values()];
      if(ps.length>1&&gesture.mid&&gesture.distance>0){const r=vp.getBoundingClientRect(),mid={x:(ps[0].x+ps[1].x)/2,y:(ps[0].y+ps[1].y)/2},distance=Math.hypot(ps[0].x-ps[1].x,ps[0].y-ps[1].y);state.camera=G.zoom(gesture.camera,distance/gesture.distance,gesture.mid.x-r.left,gesture.mid.y-r.top);state.camera.x+=mid.x-gesture.mid.x;state.camera.y+=mid.y-gesture.mid.y;gesture.dragged=true;}
      else{const dx=ps[0].x-gesture.start.x,dy=ps[0].y-gesture.start.y;if(!gesture.dragged&&Math.hypot(dx,dy)<5)return;gesture.dragged=true;state.camera={...gesture.camera,x:gesture.camera.x+dx,y:gesture.camera.y+dy};}
      event.preventDefault();vp.setPointerCapture(event.pointerId);vp.classList.add('is-dragging');scheduleCamera();
    });
    function end(event){
      if(!pointers.has(event.pointerId))return;
      if(gesture?.dragged)state.suppressClickUntil=performance.now()+300;
      pointers.delete(event.pointerId);if(vp.hasPointerCapture(event.pointerId))vp.releasePointerCapture(event.pointerId);
      vp.classList.remove('is-dragging');begin();
    }
    vp.addEventListener('pointerup',end);vp.addEventListener('pointercancel',end);
    vp.addEventListener('lostpointercapture',event=>{pointers.delete(event.pointerId);if(!pointers.size){vp.classList.remove('is-dragging');gesture=null;}});
    vp.addEventListener('keydown',event=>{
      if(event.target!==vp||!state.view)return;
      const shifts={ArrowLeft:[60,0],ArrowRight:[-60,0],ArrowUp:[0,60],ArrowDown:[0,-60]};
      if(shifts[event.key]){event.preventDefault();state.camera.x+=shifts[event.key][0];state.camera.y+=shifts[event.key][1];camera();}
      if(event.key==='Home'){event.preventDefault();fit();}
      if(['+','=','-'].includes(event.key)){event.preventDefault();const d=dims();state.camera=G.zoom(state.camera,event.key==='-'?.8:1.25,d.width/2,d.height/2);camera();}
      if(event.key==='Escape')close();
    });
    $('calculationGraphMinimap').addEventListener('click',event=>{
      if(!state.view)return;if(!event.detail){fit();return;}const r=$('calculationGraphMinimap').querySelector('svg').getBoundingClientRect(),b=state.view.bounds,s=Math.min(r.width/b.width,r.height/b.height),ox=(r.width-b.width*s)/2,oy=(r.height-b.height*s)/2;
      const x=Math.max(0,Math.min(b.width,(event.clientX-r.left-ox)/s)),y=Math.max(0,Math.min(b.height,(event.clientY-r.top-oy)/s));const d=dims();state.camera.x=d.width/2-x*state.camera.scale;state.camera.y=d.height/2-y*state.camera.scale;camera();
    });
    new ResizeObserver(()=>{if(!state.view||!active())return;const old=state.dimensions,d=dims();if(!d.width||!d.height)return;if(state.needsFit){fit();return;}state.camera.x+=(d.width-old.width)/2;state.camera.y+=(d.height-old.height)/2;camera();}).observe(vp);
    function stale(){if(!state.model)return;state.stale=true;updateStatus();if(state.selected&&!$('calculationGraphInspector').hidden)selectEntry(state.selected);}
    function results(result){
      try{const wasOpen=!$('calculationGraphInspector').hidden;state.model=G.build(result.calculation_graph);state.stale=false;state.view=null;state.needsFit=true;if(state.selected&&!state.model.byId.has(state.selected))state.selected=null;draw();if(active()&&wasOpen){if(state.selected)selectEntry(state.selected);else if(state.selectedGroup&&state.view?.byId.has(state.selectedGroup))selectGroup(state.view.byId.get(state.selectedGroup));}updateStatus();}
      catch(error){state.model=null;state.view=null;vp.replaceChildren(element('div',error.message,'calc-graph-empty'));status(error.message);panel.querySelector('[data-graph-action=latex]').disabled=true;}
    }
    document.addEventListener('bipol:results',event=>results(event.detail));
    document.addEventListener('bipol:project',()=>{state.model=null;state.view=null;state.scope='overview';$('calculationGraphScope').value='overview';close(true);vp.replaceChildren(element('div','Oczekiwanie na obliczenia nowego projektu.','calc-graph-empty'));$('calculationGraphMinimap').hidden=true;panel.querySelector('[data-graph-action=latex]').disabled=true;status('Oczekiwanie na obliczenia.');});
    document.addEventListener('bipol:tab',()=>{if(active()&&state.model&&!state.view)draw();});
    document.addEventListener('bipol:calculating',stale);
    document.getElementById('designForm')?.addEventListener('input',stale,true);document.getElementById('designForm')?.addEventListener('change',stale,true);
    if(typeof currentResults!=='undefined'&&currentResults)results(currentResults);
    root.BipolCalculationTree={state,selectEntry,fit,draw};
  }
  if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',init);
})(typeof globalThis!=='undefined'?globalThis:this);

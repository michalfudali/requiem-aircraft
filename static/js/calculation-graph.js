/* Pure graph model, readable projections, layout and camera; no DOM dependency. */
(function(root){
  'use strict';
  const ORDER=['const','p1','p2','p3','p4','p5','p6'];
  const PRIMARY={const:['g','rho0'],p1:['m_lad','m_zal','Kmax_1'],p2:['m0','m_f','P_req'],p3:['S','b','mac'],p4:['Cx0','Kmax','k'],p5:['V_S','w_max','V_max'],p6:['V_D','n_ult_p','n_ult_m']};
  const finite=x=>typeof x==='number'&&Number.isFinite(x);
  const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ł/g,'l').replace(/Ł/g,'L').toLowerCase();
  function build(data){
    if(!data||data.version!==1||!Array.isArray(data.nodes)||!Array.isArray(data.edges))throw Error('Brak arkusza obliczeń. Przelicz projekt.');
    const byId=new Map(),parents=new Map(),children=new Map();
    for(const node of data.nodes){if(byId.has(node.id))throw Error('Powtórzony identyfikator w grafie.');byId.set(node.id,node);parents.set(node.id,[]);children.set(node.id,[]);}
    for(const edge of data.edges){if(!byId.has(edge.source)||!byId.has(edge.target))throw Error('Niepełna zależność w arkuszu.');parents.get(edge.target).push(edge.source);children.get(edge.source).push(edge.target);}
    const componentById=new Map();
    for(const c of data.components||[])for(const id of c.members){if(!byId.has(id)||componentById.has(id))throw Error('Nieprawidłowa grupa sprzężeń.');componentById.set(id,c);}
    for(const node of data.nodes)if(!componentById.has(node.id))componentById.set(node.id,{id:'single:'+node.id,members:[node.id],cyclic:false});
    return {data,byId,parents,children,componentById};
  }
  function ancestors(model,ids){
    const seen=new Set(),queue=[...ids];
    while(queue.length){const key=queue.pop();if(seen.has(key)||!model.byId.has(key))continue;seen.add(key);queue.push(...model.parents.get(key));}
    return seen;
  }
  function search(model,query,limit=12){
    const q=normalize(query.trim());if(!q)return [];
    return model.data.nodes.map(n=>({node:n,key:normalize(n.id),label:normalize(n.label)}))
      .filter(x=>`${x.key} ${x.label} ${normalize(x.node.sym)}`.includes(q))
      .sort((a,b)=>(a.key===q?-2:a.key.startsWith(q)?-1:0)-(b.key===q?-2:b.key.startsWith(q)?-1:0)||a.label.localeCompare(b.label,'pl'))
      .slice(0,limit).map(x=>x.node);
  }
  function overview(model){
    const spots=[[0,0],[330,0],[660,0],[660,220],[330,220],[0,220],[0,440]];
    const nodes=ORDER.filter(p=>model.data.nodes.some(n=>n.project===p)).map(project=>{
      const members=model.data.nodes.filter(n=>n.project===project).map(n=>n.id);
      let samples=(PRIMARY[project]||[]).filter(id=>model.byId.has(id));
      if(samples.length<2)samples=[...new Set([...samples,...members.filter(id=>finite(model.byId.get(id).value)&&model.byId.get(id).kind!=='given')])].slice(0,3);
      return {id:'project:'+project,label:model.data.projects[project],project,kind:'project',members,samples,
        x:spots[ORDER.indexOf(project)][0]+30,y:spots[ORDER.indexOf(project)][1]+30,width:280,height:172};
    });
    const map=new Map(nodes.flatMap(n=>n.members.map(id=>[id,n.id])));
    return finishProjection(model,nodes,map,model.data.edges,true);
  }
  function project(model,scope='overview',selected=null){
    if(scope==='overview')return overview(model);
    let active;
    if(scope==='path')active=ancestors(model,selected?[selected]:[]);
    else if(scope==='all')active=new Set(model.byId.keys());
    else active=new Set(model.data.nodes.filter(n=>n.project===scope).map(n=>n.id));
    // A feedback group remains intact even when it crosses project boundaries.
    for(const id of [...active]){const c=model.componentById.get(id);if(c.cyclic)c.members.forEach(k=>active.add(k));}
    const groups=new Map(),map=new Map();
    function group(id,key,kind,label,project){
      if(!groups.has(key))groups.set(key,{id:key,kind,label,project,members:[],samples:[],width:258,height:138});
      groups.get(key).members.push(id);map.set(id,key);
    }
    for(const node of model.data.nodes){
      if(!active.has(node.id))continue;
      const c=model.componentById.get(node.id);
      if(c.cyclic)group(node.id,c.id,'cycle',c.members.includes('m0')?'Bilans masy':'Geometria ↔ aerodynamika',ORDER.includes(scope)?scope:node.project);
      else if(node.kind==='given')group(node.id,'data:'+node.section,'data',model.data.sections.find(s=>s.key===node.section)?.title||'Dane i parametry modelu',node.project);
      else group(node.id,node.id,node.kind,node.label,node.project);
    }
    if(scope!=='all'&&scope!=='path'){
      const external=new Set();for(const id of active)for(const parent of model.parents.get(id))if(!active.has(parent))external.add(parent);
      for(const id of external){const n=model.byId.get(id);group(id,'external:'+n.project,'portal','Z '+(n.project==='const'?'danych ISA':n.project.toUpperCase()),n.project);}
    }
    const nodes=[...groups.values()];
    for(const n of nodes){
      n.samples=n.kind==='cycle'?['m0','S','Cx0'].filter(k=>n.members.includes(k)):n.members.slice(0,n.kind==='data'||n.kind==='portal'?2:1);
      if(!n.samples.length)n.samples=n.members.slice(0,1);
    }
    const edges=model.data.edges.filter(e=>map.has(e.source)&&map.has(e.target)&&(active.has(e.target)||scope==='all'||scope==='path'));
    const view=finishProjection(model,nodes,map,edges,false);layout(view);return view;
  }
  function finishProjection(model,nodes,map,originalEdges,isOverview){
    const grouped=new Map();
    for(const e of originalEdges){const source=map.get(e.source),target=map.get(e.target);if(!source||!target||source===target)continue;const key=source+'\0'+target;if(!grouped.has(key))grouped.set(key,{id:key,source,target,count:0,original:[]});const edge=grouped.get(key);edge.count++;edge.original.push(e);}
    const byId=new Map(nodes.map(n=>[n.id,n]));
    return {nodes,edges:[...grouped.values()],byId,map,isOverview,bounds:bounds(nodes)};
  }
  function layout(view){
    const indegree=new Map(view.nodes.map(n=>[n.id,0])),children=new Map(view.nodes.map(n=>[n.id,[]])),parents=new Map(view.nodes.map(n=>[n.id,[]]));
    for(const e of view.edges){indegree.set(e.target,indegree.get(e.target)+1);children.get(e.source).push(e.target);parents.get(e.target).push(e.source);}
    const queue=view.nodes.filter(n=>!indegree.get(n.id)).map(n=>n.id),depth=new Map(queue.map(id=>[id,0]));
    for(let i=0;i<queue.length;i++){const id=queue[i];for(const next of children.get(id)){depth.set(next,Math.max(depth.get(next)||0,(depth.get(id)||0)+1));indegree.set(next,indegree.get(next)-1);if(!indegree.get(next))queue.push(next);}}
    if(queue.length!==view.nodes.length)throw Error('Nierozwiązany cykl w układzie grafu.');
    const layers=[];for(const id of queue){const d=depth.get(id);(layers[d]??=[]).push(view.byId.get(id));}
    const slots=new Map();
    layers.forEach((layer,d)=>{
      if(d)layer.sort((a,b)=>{
        const mean=n=>{const ps=parents.get(n.id);return ps.length?ps.reduce((sum,id)=>sum+(slots.get(id)||0),0)/ps.length:0;};
        return mean(a)-mean(b)||a.label.localeCompare(b.label,'pl');
      });
      layer.forEach((n,i)=>{n.x=30+d*332;n.y=30+i*178;slots.set(n.id,i);});
    });
    view.bounds=bounds(view.nodes);return view;
  }
  function bounds(nodes){return {x:0,y:0,width:Math.max(360,...nodes.map(n=>n.x+n.width+30)),height:Math.max(260,...nodes.map(n=>n.y+n.height+30))};}
  const clampScale=s=>Math.max(.025,Math.min(2.5,s));
  function fit(box,width,height,padding=28){const scale=clampScale(Math.min((width-2*padding)/box.width,(height-2*padding)/box.height,1.15));return {x:(width-box.width*scale)/2,y:(height-box.height*scale)/2,scale};}
  function zoom(camera,factor,x,y){const scale=clampScale(camera.scale*factor),ratio=scale/camera.scale;return {x:x-(x-camera.x)*ratio,y:y-(y-camera.y)*ratio,scale};}
  function center(camera,node,width,height,scale=camera.scale){scale=clampScale(scale);return {x:width/2-(node.x+node.width/2)*scale,y:height/2-(node.y+node.height/2)*scale,scale};}
  function edgePath(edge,view){
    const a=view.byId.get(edge.source),b=view.byId.get(edge.target);
    let x1=a.x+a.width,y1=a.y+a.height/2,x2=b.x,y2=b.y+b.height/2;
    if(view.isOverview&&Math.abs(a.y-b.y)>150){x1=a.x+a.width/2;y1=a.y+(b.y>a.y?a.height:0);x2=b.x+b.width/2;y2=b.y+(a.y>b.y?b.height:0);const mid=(y1+y2)/2;return `M${x1},${y1} C${x1},${mid} ${x2},${mid} ${x2},${y2}`;}
    if(x2<x1){x1=a.x;x2=b.x+b.width;}
    const mid=(x1+x2)/2;return `M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}`;
  }
  function texEscape(value){
    const escaped={'\\':'\\textbackslash{}','{':'\\{','}':'\\}','#':'\\#','$':'\\$','%':'\\%','&':'\\&','_':'\\_','~':'\\textasciitilde{}','^':'\\textasciicircum{}','–':'--','—':'---','−':'\\ensuremath{-}','’':"'",'‘':"'",'“':'``','”':"''"};
    const math={'≥':'\\geq','≤':'\\leq','≈':'\\approx','∞':'\\infty','∛':'\\sqrt[3]{}','√':'\\sqrt{}','↔':'\\leftrightarrow','→':'\\rightarrow','α':'\\alpha','β':'\\beta','γ':'\\gamma','δ':'\\delta','ε':'\\varepsilon','η':'\\eta','κ':'\\kappa','λ':'\\lambda','μ':'\\mu','π':'\\pi','ρ':'\\rho','τ':'\\tau','χ':'\\chi','Δ':'\\Delta','Λ':'\\Lambda','Σ':'\\Sigma'};
    for(const [i,c] of Array.from('₀₁₂₃₄₅₆₇₈₉').entries())math[c]='{}_{'+i+'}';
    for(const [i,c] of Array.from('⁰¹²³⁴⁵⁶⁷⁸⁹').entries())math[c]='{}^{'+i+'}';
    for(const [c,v] of Object.entries({'ᵢ':'i','ⱼ':'j','ₑ':'e','ₖ':'k','ₓ':'x'}))math[c]='{}_{'+v+'}';
    const chars=Array.from(String(value??''));let out='';
    for(let i=0;i<chars.length;i++){const c=chars[i];
      if(chars[i+1]==='\u0304'&&/[a-zA-Z]/.test(c)){out+='\\ensuremath{\\bar{'+c+'}}';i++;}
      else out+=escaped[c]??(math[c]?'\\ensuremath{'+math[c]+'}':c);
    }return out;
  }
  function latex(model,ids,follow=true){
    const chosen=follow?ancestors(model,ids):new Set(ids);
    const lines=['\\documentclass[11pt,a4paper]{article}','\\usepackage[T1]{fontenc}','\\usepackage[utf8]{inputenc}','\\usepackage[polish]{babel}','\\usepackage{amsmath,amssymb,geometry}','\\geometry{margin=20mm}','\\allowdisplaybreaks','\\begin{document}',`\\section*{Tok obliczeń: ${texEscape(model.data.project_name)}}`];
    const selected=model.data.nodes.filter(n=>chosen.has(n.id));
    for(const n of selected){
      lines.push(`\\subsection*{${texEscape(n.label)}}`);
      if(n.source)lines.push(texEscape(n.source)+'\\par');
      if(n.tex)lines.push('\\[',n.tex,'\\]');
      if(n.note)lines.push(texEscape(n.note)+'\\par');
      for(const iteration of n.iterations||[]){lines.push(`\\subsubsection*{Iteracja ${iteration.number}}`);for(const step of iteration.steps)lines.push(texEscape(step.label)+'\\par','\\[',step.tex,'\\]');}
    }
    lines.push('\\end{document}');return lines.join('\n');
  }
  const api={build,project,ancestors,search,layout,fit,zoom,center,edgePath,latex,normalize};
  if(typeof module==='object'&&module.exports)module.exports=api;else root.BipolCalculationGraph=api;
})(typeof globalThis!=='undefined'?globalThis:this);

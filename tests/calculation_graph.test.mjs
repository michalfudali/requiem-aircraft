import test from 'node:test';
import assert from 'node:assert/strict';
import G from '../static/js/calculation-graph.js';

function fixture(){return {
  version:1,project_name:'Test \\input{bad} & <samolot>',projects:{const:'Stałe',p1:'Założenia',p2:'Masy',p3:'Geometria'},
  sections:[{key:'const',title:'Stałe'},{key:'p1.data',title:'Założenia'},{key:'p2.mass',title:'Masa'},{key:'p3.wing',title:'Płat'}],
  nodes:[
    {id:'g',kind:'given',project:'const',section:'const',label:'Grawitacja',sym:'g',value:9.81,value_tex:'9.81',tex:'g=9.81',deps:[]},
    {id:'WS',kind:'given',project:'p1',section:'p1.data',label:'Obciążenie płata',sym:'W/S',value:100,tex:'W/S=100',deps:[]},
    {id:'m0',kind:'solve',project:'p2',section:'p2.mass',label:'Masa startowa',value:1000,tex:'m_0=1000',deps:['S']},
    {id:'S',kind:'calc',project:'p3',section:'p3.wing',label:'Powierzchnia płata',value:98.1,tex:'S=1000\\cdot9.81/100=98.1',deps:['g','m0','WS']},
    {id:'b',kind:'calc',project:'p3',section:'p3.wing',label:'Rozpiętość',value:20,tex:'b=20',deps:['S']},
    {id:'@iteration',kind:'procedure',project:'p2',section:'p2.mass',label:'Iteracja',deps:['WS'],iterations:[{number:1,steps:[{label:'Podstawienie',tex:'m_0=1000'}]}]}
  ],edges:[{source:'g',target:'S'},{source:'WS',target:'S'},{source:'m0',target:'S'},{source:'S',target:'m0'},{source:'S',target:'b'},{source:'WS',target:'@iteration'}],
  components:[{id:'c0',members:['g'],cyclic:false},{id:'c1',members:['WS'],cyclic:false},{id:'cycle',members:['m0','S'],cyclic:true},{id:'c3',members:['b'],cyclic:false},{id:'c4',members:['@iteration'],cyclic:false}]
};}

test('a real feedback group stays intact across project and dependency views',()=>{
  const model=G.build(fixture());
  for(const scope of ['all','p2','p3','path']){
    const view=G.project(model,scope,'S');
    assert.equal(view.map.get('S'),view.map.get('m0'));
    assert.equal(view.byId.get(view.map.get('S')).kind,'cycle');
    for(const edge of view.edges)assert.ok(view.byId.get(edge.target).x>view.byId.get(edge.source).x);
  }
});
test('every projected edge corresponds to actual dependencies, with complete member coverage',()=>{
  const model=G.build(fixture()),view=G.project(model,'all');
  for(const node of model.data.nodes)assert.ok(view.map.has(node.id));
  for(const edge of view.edges){assert.equal(edge.count,edge.original.length);for(const raw of edge.original){assert.ok(model.data.edges.includes(raw));assert.equal(edge.source,view.map.get(raw.source));assert.equal(edge.target,view.map.get(raw.target));}}
});
test('camera zoom keeps the world point below the cursor fixed and clamps extreme scales',()=>{
  const before={x:100,y:-30,scale:.8},point={x:270,y:160};
  for(const factor of [1.25,.1,1000,.00001]){const after=G.zoom(before,factor,point.x,point.y);assert.ok(after.scale>=.025&&after.scale<=2.5);assert.ok(Math.abs((point.x-before.x)/before.scale-(point.x-after.x)/after.scale)<1e-8);assert.ok(Math.abs((point.y-before.y)/before.scale-(point.y-after.y)/after.scale)<1e-8);}
});
test('fit and focus center a diagram and quantity even at the scale limits',()=>{
  const c=G.fit({width:1000,height:600},900,700),node={x:200,y:100,width:260,height:138};
  assert.ok(c.scale<1&&c.x>=0&&c.y>=0);
  const focused=G.center(c,node,900,700,9);
  assert.equal(focused.scale,2.5);assert.equal(focused.x+(node.x+node.width/2)*focused.scale,450);assert.equal(focused.y+(node.y+node.height/2)*focused.scale,350);
});
test('search prioritizes an exact symbol and tolerates missing Polish accents',()=>{
  const model=G.build(fixture());assert.equal(G.search(model,'S')[0].id,'S');assert.equal(G.search(model,'rozpietosc')[0].id,'b');
});
test('LaTeX export contains true predecessors, full substitutions and safely escaped editorial text',()=>{
  const model=G.build(fixture()),tex=G.latex(model,['S','@iteration']);
  assert.ok(tex.includes('S=1000\\cdot9.81/100=98.1'));
  assert.ok(tex.includes('g=9.81')&&tex.includes('W/S=100')&&tex.includes('Iteracja 1'));
  assert.ok(!tex.includes('\\input{bad}'));assert.ok(tex.includes('\\textbackslash{}input\\{bad\\} \\&'));
  assert.equal((tex.match(/\\subsection\*\{Masa startowa\}/g)||[]).length,1);
});
test('broken edges and duplicate identifiers fail explicitly',()=>{
  const data=fixture();data.edges.push({source:'missing',target:'S'});assert.throws(()=>G.build(data));
  const duplicate=fixture();duplicate.nodes.push(duplicate.nodes[0]);assert.throws(()=>G.build(duplicate));
});
test('LaTeX text converts technical Unicode without exposing TeX commands',()=>{
  const data=fixture();data.project_name='ŚC ≥ 5% · m₀, Λ, c̄, Re 10⁷';data.nodes[0].note='∛ √ μ δ τ λ χ κ';
  const tex=G.latex(G.build(data),['g']);
  assert.ok(tex.includes('ŚC \\ensuremath{\\geq} 5\\%'));
  for(const ch of '≥₀Λ̄⁷∛√μδτλχκ')assert.ok(!tex.includes(ch),ch);
  assert.ok(tex.includes('\\ensuremath{\\bar{c}}'));
});

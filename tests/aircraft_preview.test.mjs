import test from 'node:test';
import assert from 'node:assert/strict';
import preview from '../static/js/aircraft-preview.js';

function result(overrides = {}) {
  return {params:{name:'Samolot testowy',engine_type:'prop',engine_location:'nose',flap_type:'single_slotted',aileron_type:'differential',slat_type:'none',...overrides},
    geometry:{wing:{S:16,b:12,cr:1.8,ct:.9,sweep_deg:4,dihedral_deg:3,wing_config:'low',wing_planform:'trapezoidal',tc_ratio:.12},
      fuselage:{length:8,diameter:1.25},horizontal_tail:{S_h:3,b_h:3.5,cr_h:1.1,ct_h:.66},vertical_tail:{h_v:1.6,cr_v:1.2,ct_v:.6},
      control_surfaces:{flaps:{y_in_m:.8,y_out_m:3.8,cf_over_c:.3,name:'Klapa jednoszczelinowa'},
        ailerons:{y_in_m:4,y_out_m:5.7,ca_over_c:.2,name:'Lotka różnicowa'}}},
    balance:{x_le_wing_m:2.5,loading_states:[{xcg_m:3}]},
    bipol_projects:{p4:{paturski_propulsion:{propeller_selection:{diameter_m:2.1}}}}};
}
const points = (model, part) => model.faces.filter(face=>face.part===part).flatMap(face=>face.points);

test('rendered propulsion honours one, two and four engines in every mounting location', () => {
  for (const engine_type of ['prop','jet']) for (const engine_location of ['nose','wing','rear','retractable']) {
    const one=preview.model(result({engine_type,engine_location,n_engines:1}));
    const label=engine_type==='jet'?'Gondola silnika odrzutowego':'Osłona silnika śmigłowego';
    const single=one.faces.filter(face=>face.label===label).length;
    assert.ok(single>0);
    for(const n_engines of [2,4]){
      const multiple=preview.model(result({engine_type,engine_location,n_engines}));
      assert.equal(multiple.faces.filter(face=>face.label===label).length,single*n_engines);
      assert.ok(new Set(points(multiple,'engine').map(p=>p[1])).size>new Set(points(one,'engine').map(p=>p[1])).size);
    }
  }
});

test('a water-only aircraft is not shown with a wheel undercarriage', () => {
  assert.equal(points(preview.model(result({operating_surface:'water'})),'gear').length,0);
  assert.ok(points(preview.model(result({operating_surface:'land'})),'gear').length>0);
});

test('propulsion follows engine type and location, without inventing a glider engine', () => {
  for (const loc of ['nose','wing','rear','retractable']) {
    const prop=preview.model(result({engine_location:loc}));
    assert.ok(points(prop,'engine').length);
    assert.ok(points(prop,'propeller').length);
    if (loc==='wing') {
      assert.ok(points(prop,'engine').some(p=>p[1]>1.5));
      assert.ok(points(prop,'engine').some(p=>p[1]<-1.5));
    }
    const jet=preview.model(result({engine_type:'jet',engine_location:loc}));
    assert.ok(points(jet,'engine').length); assert.equal(points(jet,'propeller').length,0);
    assert.ok(jet.faces.some(face=>face.label==='Wlot silnika odrzutowego'));
  }
  const glider=preview.model(result({engine_type:'none',engine_location:'none'}));
  assert.equal(points(glider,'engine').length,0); assert.equal(points(glider,'propeller').length,0);
});

test('aileron and flap spans and hinge chords come from calculated control surfaces', () => {
  const r=result(), model=preview.model(r);
  for (const [part,start,end,ratio] of [['flap',.8,3.8,.3],['aileron',4,5.7,.2]]) {
    const ps=points(model,part), ys=ps.map(p=>Math.abs(p[1]));
    assert.equal(Math.min(...ys),start); assert.equal(Math.max(...ys),end);
    for (const [x,y] of ps) {
      const chord=1.8+(.9-1.8)*Math.abs(y)/6;
      const leading=2.5+Math.abs(y)*Math.tan(4*Math.PI/180)+(1.8-chord)*.25;
      assert.ok(x>=leading+chord*(1-ratio)-1e-8);
      assert.ok(x<=leading+chord+1e-8);
    }
  }
});

test('selected leading edge device appears on both wings; a clean wing has none', () => {
  assert.equal(points(preview.model(result()),'slat').length,0);
  for (const slat_type of ['fixed_slot','slats_auto','krueger']) {
    const model=preview.model(result({slat_type})), ps=points(model,'slat');
    assert.ok(ps.some(p=>p[1]>0)); assert.ok(ps.some(p=>p[1]<0));
    assert.ok(model.parts.find(part=>part.id==='slat').label.length);
  }
});

test('combined flaperons form one surface instead of overlapping flaps and ailerons', () => {
  const r=result({flap_type:'flaperon',aileron_type:'flaperon'});
  r.geometry.control_surfaces.is_flaperon=true;
  const model=preview.model(r);
  assert.ok(points(model,'flaperon').length);
  assert.equal(points(model,'flap').length,0); assert.equal(points(model,'aileron').length,0);
  const clean=preview.model(result({flap_type:'none'}));
  assert.equal(points(clean,'flap').length,0); assert.ok(points(clean,'aileron').length);
});

test('camera presets retain orthographic top, side and front conventions', () => {
  const near=(actual,want)=>actual.forEach((v,i)=>assert.ok(Math.abs(v-want[i])<1e-8));
  near(preview.project([3,4,5],preview.camera('top')).slice(0,2),[4,-3]);
  near(preview.project([3,4,5],preview.camera('side')).slice(0,2),[3,-5]);
  near(preview.project([3,4,5],preview.camera('front')).slice(0,2),[4,-5]);
  assert.deepEqual(preview.camera('iso',{yaw:400,elevation:-150}),{yaw:40,elevation:-90});
});

test('export fits the complete model, including propulsion, through full rotations', () => {
  const r=result({slat_type:'slats_auto',engine_location:'retractable'}), original=structuredClone(r);
  const model=preview.model(r);
  for (const yaw of [-180,-90,0,90,179]) for (const elevation of [-90,-45,0,45,90]) {
    const svg=preview.render(model,'custom',{yaw,elevation});
    assert.ok(!/NaN|Infinity|undefined/.test(svg));
    assert.ok(svg.includes('xmlns="http://www.w3.org/2000/svg"'));
    assert.ok(svg.includes('data-aircraft-part="propeller"'));
    for (const match of svg.matchAll(/points="([^"]+)"/g)) for (const pair of match[1].split(' ')) {
      const [x,y]=pair.split(',').map(Number);
      assert.ok(x>=54.9&&x<=705.1&&y>=62.4&&y<=347.6,`${yaw}/${elevation}: ${x},${y}`);
    }
  }
  assert.deepEqual(r,original);
  assert.ok(preview.render(model,'top').includes('RZUT Z GÓRY'));
});

test('all supported wing planforms render valid solids with their calculated tip chords', () => {
  for (const planform of ['trapezoidal','rectangular','compound_trapezoid','elliptical','swept_trapezoidal']) {
    const r=result(); r.geometry.wing.wing_planform=planform; r.geometry.wing.break_station_m=2;
    if (planform==='elliptical') r.geometry.wing.ct=0;
    const model=preview.model(r), svg=preview.render(model);
    assert.ok(!/NaN|Infinity/.test(svg));
    if (planform==='elliptical') {
      const tip=points(model,'wing').filter(p=>Math.abs(p[1])===6);
      assert.ok(tip.length); assert.ok(tip.every(p=>Math.abs(p[0]-(2.5+6*Math.tan(4*Math.PI/180)+1.8*.25))<1e-8));
    }
  }
});

test('aircraft names and labels are escaped in standalone SVG', () => {
  const svg=preview.render(preview.model(result({name:'<script>"& test'})));
  assert.ok(!svg.includes('<script>')); assert.ok(svg.includes('&lt;script&gt;&quot;&amp; test'));
});

test('concept proportions clarify the extreme regional profile without mutating calculated geometry', () => {
  const r=result({aircraft_type:'turboprop_regional',n_pax:70,engine_location:'wing'});
  Object.assign(r.geometry.wing,{b:80.2,S:584.71,cr:10,ct:4,wing_config:'high'});
  Object.assign(r.geometry.fuselage,{length:68.17,diameter:2.4});
  const original=structuredClone(r), exact=preview.model(r,{proportions:'calculated'}), concept=preview.model(r,{proportions:'concept'});
  assert.equal(exact.dimensions.diameter,2.4);
  assert.equal(concept.dimensions.sourceDiameter,2.4);
  assert.ok(concept.dimensions.diameter>=68.17*.08);
  assert.equal(exact.dimensions.length,concept.dimensions.length);
  assert.equal(exact.span,concept.span); assert.equal(exact.area,concept.area);
  assert.ok(concept.faces.some(face=>face.label==='Okno kabiny pasażerskiej'));
  const svg=preview.render(concept);
  assert.ok(svg.includes('KONCEPCJA · PROPORCJE UPROSZCZONE'));
  assert.ok(svg.includes('S = 584,71 m² · b = 80,2 m'));
  assert.deepEqual(r,original);
});

test('solid faces have finite outward unit normals and no collapsed panels', () => {
  for (const aircraft_type of ['piston_ga','turboprop_regional','glider','jet_business']) {
    const r=result({aircraft_type,n_pax:70});
    const model=preview.model(r,{proportions:'concept'});
    for (const face of model.faces.filter(face=>!face.line)) {
      assert.ok(face.normal,`${aircraft_type}: ${face.part}`);
      assert.ok(face.normal.every(Number.isFinite));
      assert.ok(Math.abs(Math.hypot(...face.normal)-1)<1e-7);
    }
  }
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),{solve}=require('../static/js/ballast.js');
function fixture(maximum=1000){return {station_domain_m:[0,5],n_crew:0,crew_arm_m:0,lemac_m:0,mac_m:1,neutral_point_pct:265,
  cases:[{key:'a',name:'A',base_mass_kg:100,base_moment_kg_m:200},{key:'b',name:'B',base_mass_kg:200,base_moment_kg_m:600}],
  constraints:[{state_key:'a',kind:'mass',label:'Masa',a:-1,b:0,c0:maximum-100,cp:0},
    {state_key:'b',kind:'mass',label:'Masa',a:-1,b:0,c0:maximum-200,cp:0},
    {state_key:'a',kind:'forward',label:'Przednie',a:-2.4,b:1,c0:-40,cp:0},
    {state_key:'a',kind:'aft',label:'Tylne',a:2.6,b:-1,c0:60,cp:0},
    {state_key:'b',kind:'forward',label:'Przednie',a:-2.4,b:1,c0:120,cp:0},
    {state_key:'b',kind:'aft',label:'Tylne',a:2.6,b:-1,c0:-80,cp:0}]};}
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
test('joint minimum is inside the fuselage, not at either end',()=>{
  const r=solve(fixture(),0);assert.equal(r.feasible,true);close(r.mass_kg,600);close(r.station_m,1480/600);
  close(r.after[0].xcg_m,2.4);close(r.after[1].xcg_m,2.6);assert.ok(r.after.every(v=>v.passed));
  assert.equal(solve(fixture(),0,0).feasible,false);assert.equal(solve(fixture(),0,5).feasible,false);
});
test('a single feasible point at the mass ceiling is preserved',()=>{
  const r=solve(fixture(800),0);assert.ok(r.feasible);close(r.mass_kg,600);close(r.after[1].mass_kg,800);
  assert.equal(solve(fixture(799),0).feasible,false);
});
test('fixed optimal station reproduces the global minimum',()=>{
  const global=solve(fixture(),0),fixed=solve(fixture(),0,global.station_m);
  close(fixed.mass_kg,global.mass_kg);assert.ok(fixed.after.every(v=>v.passed));
});
test('overweight has no positive-ballast solution',()=>{
  const r=solve(fixture(199),0);assert.equal(r.reason,'mass');assert.equal(r.mass_kg,null);assert.deepEqual(r.after,[]);
});
test('invalid person or station is rejected',()=>{
  for(const [p,x] of [[NaN,null],[-1,null],[55,Infinity],[55,-1],[55,6]])assert.throws(()=>solve(fixture(),p,x));
});
test('solver does not mutate physical coefficients or input ordering',()=>{
  const m=fixture(),copy=structuredClone(m);solve(m,0);assert.deepEqual(m,copy);
});

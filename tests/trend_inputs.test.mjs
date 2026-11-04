import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const {patch,supports}=createRequire(import.meta.url)('../static/js/trend-inputs.js');
test('mass wing loading uses kg/m² without another gravity conversion',()=>{
  assert.deepEqual(patch('ws',80,{engine_type:'prop'},1200),{wing_input_mode:'area_aspect',wing_area_m2:15});
});
test('power loading uses total installed power and activates fixed-power mode',()=>{
  assert.deepEqual(patch('pw',8,{engine_type:'prop'},1200),{power_input_mode:'fixed',engine_power_kw:150});
});
test('geometry suggestions change the actual model inputs',()=>{
  assert.deepEqual(patch('vh',.8,{},1000),{v_h:.8});
  assert.deepEqual(patch('ar',12,{wing_input_mode:'span_area'},1000),{aspect_ratio:12,wing_input_mode:'span_aspect'});
  assert.deepEqual(patch('c_r_ratio',.3,{},1000),{rudder_chord_ratio:.3});
});
test('empty mass always comes from BIPOL_1 eq. (1) of the trend line, never a typed fraction',()=>{
  assert.deepEqual(patch('me_m0',.61,{},1000,{apply:{empty_mass_trend_A:.9,empty_mass_trend_C:-.05}}),{empty_mass_model:'trend'});
  assert.deepEqual(patch('me_m0',.6,{},1000),{empty_mass_model:'trend'});
  assert.equal(supports('me_m0'),false);
});

test('a sample mass law follows later sample edits instead of freezing old coefficients',()=>{
  const apply={empty_mass_model:'trend',empty_mass_trend_A:.9,empty_mass_trend_C:-.05,empty_mass_fraction:null};
  assert.deepEqual(patch('me_m0',.61,{},1000,{apply}),
    {empty_mass_model:'trend',empty_mass_trend_A:null,empty_mass_trend_C:null,empty_mass_fraction:null});
  assert.equal(apply.empty_mass_trend_A,.9);
});
test('unsupported or missing values cannot claim to have been applied',()=>{
  assert.equal(supports('tw'),false);
  assert.throws(()=>patch('tw',.4,{},1200));
  assert.throws(()=>patch('ws',80,{},0));
  assert.throws(()=>patch('ar',NaN,{},1000));
});

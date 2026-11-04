import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const {scatterXPositions, scatterNote, renderWizardChartSvg} =
  createRequire(import.meta.url)('../static/js/trend-provenance.js');

test('duplicate abscissae spread symmetrically and stay between nearby observations', () => {
  const points = [{x:10,y:.6,model:'Left'}, {x:20,y:.7,model:'B'},
    {x:20,y:.5,model:'A'}, {x:20,y:.6,model:'C'}, {x:21,y:.6,model:'Right'}];
  const original = structuredClone(points);
  const positions = scatterXPositions(points, x => x, 0, 100);
  assert.deepEqual(points, original);
  assert.equal(positions[0], 10);
  assert.equal(positions[4], 21);
  assert.equal(new Set(positions.slice(1, 4)).size, 3);
  assert.ok(Math.abs(positions.slice(1, 4).reduce((a,b) => a+b) / 3 - 20) < 1e-9);
  assert.ok(positions.slice(1, 4).every(x => x > 10 && x < 21 && Math.abs(x-20) <= 12));
  assert.deepEqual(scatterXPositions([...points].reverse(), x => x, 0, 100).reverse(), positions);
  assert.deepEqual(scatterXPositions([], x => x, 0, 100), []);
});

test('a large group stays inside chart bounds and the maximum display offset', () => {
  const points = Array.from({length:50}, (_,i) => ({x:600,y:i,model:`Aircraft ${i}`}));
  const positions = scatterXPositions(points, () => 100, 0, 200);
  assert.equal(new Set(positions).size, points.length);
  assert.ok(positions.every(x => x >= 88 && x <= 112));
  assert.deepEqual(scatterXPositions(points, () => 4, 0, 200), Array(50).fill(4));
});

test('wizard keeps original data and forecast while spreading a repeated mass', () => {
  const chart = {key:'me_m0',kind:'mass',title:'Mass',symbol:'mₑ/m₀',unit:'−',
    x_label:'MTOW [kg]',y_label:'OEW / MTOW',n:4,
    points:[{x:600,y:.5,model:'B'}, {x:600,y:.6,model:'A'},
      {x:575,y:.55,model:'Left'}, {x:780,y:.65,model:'Right'}],
    fit:{kind:'linear',slope:.001,intercept:0,x_min:575,x_max:780,n:4,r2:.8},
    forecast:{x:800,y:.8,accepted:true}};
  const original = structuredClone(chart);
  const html = renderWizardChartSvg(chart);
  const circles = [...html.matchAll(/<circle cx="([^"]+)" cy="([^"]+)"[^>]*><title>([^<]*)<\/title>/g)];
  assert.notEqual(circles[0][1], circles[1][1]);
  assert.ok(circles[0][3].includes('B: 600'));
  assert.ok(circles[1][3].includes('A: 600'));
  assert.ok(circles[4][3].includes('Prognoza 800'));
  assert.ok(html.includes(scatterNote));
  assert.deepEqual(chart, original);
  chart.points = chart.points.slice(2);
  assert.ok(!renderWizardChartSvg(chart).includes(scatterNote));
});

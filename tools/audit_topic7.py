"""Reproduce the topic 7 study and all six BIPOL reports in isolated databases.

Exit 0 only if the numerical invariants and the exposed design checks all pass.
An exit code of 1 still produces reports, with the outstanding items preserved.
"""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))


def numerical_invariants(result):
    p, m, wing = result['params'], result['mass'], result['geometry']['wing']
    checks = []

    def check(name, passed, actual):
        checks.append(dict(name=name, passed=bool(passed), actual=actual))

    # Requirements read from BIPOL1_samoloty.pdf, topic 7, independent of the app checker.
    configuration = dict(occupants=p['n_crew']+p['n_pax'], span=wing['b'],
                         engine=p['engine_type'], location=p['engine_location'], count=p['n_engines'])
    check('Topic 7: one seat, span >20 m, one fixed tractor piston engine',
          configuration['occupants']==1 and wing['b']>20 and p['engine_type']=='prop'
          and p['engine_location']=='nose' and p['n_engines']==1, configuration)
    total = sum(m[key] for key in ('m_empty','m_crew','m_payload','m_fuel'))
    check('Take-off mass closure to 0.1%', abs(total-m['m0']) <= .001*m['m0'],
          dict(mtow_kg=m['m0'], component_sum_kg=total))
    check('Wing geometry: AR = b^2/S', math.isclose(wing['AR'],wing['b']**2/wing['S'],rel_tol=1e-8), wing)
    phases=m['mission_phases']
    continuous=all(math.isclose(a['mass_end_kg'],b['mass_start_kg'],abs_tol=.001)
                   for a,b in zip(phases,phases[1:]))
    decreasing=all(v['mass_end_kg']<=v['mass_start_kg']+.001 for v in phases)
    check('Mission mass continuity and fuel burn',continuous and decreasing,
          [dict(phase=v['key'],start_kg=v['mass_start_kg'],end_kg=v['mass_end_kg']) for v in phases])
    cg=result['balance']
    independently=(cg['neutral_point']['x_n_mac_pct']-cg['cg_range']['aft_pct'])
    check('Static margin = neutral point - aft CG',
          math.isclose(independently,cg['stability']['static_margin_aft_pct'],abs_tol=.001),independently)
    noise=result['acoustics']
    expected=math.hypot(math.pi*noise['propeller_diameter_m']*noise['propeller_rpm']/60,
                        noise['evaluation_speed_ms'])/noise['evaluation_speed_of_sound_ms']
    check('Helical propeller tip Mach from shaft RPM, diameter and forward speed',
          abs(expected-noise['propeller_tip_mach'])<=.0005,dict(calculated=expected,reported=noise['propeller_tip_mach']))
    # Manufacturer's maximum-continuous point, not a claim about low-load operation.
    engine=result['engine_selection']
    # OM-912 section 5.2: independently converted operating-point observations.
    density=p.get('fuel_density_kg_l',.72)
    expected_sfc={'continuous':285,'cruise75':16.2*density*1000/(.75*58),
                  'takeoff':24*density*1000/59.6}.get((engine.get('point') or {}).get('id'))
    check('Rotax 912 UL: 58 kW and SFC independently checked against the source operating point',
          engine.get('model')=='Rotax 912 UL' and engine.get('installed_total')==58 and
          expected_sfc is not None and math.isclose(p['sfc'],expected_sfc,rel_tol=1e-10),
          dict(model=engine.get('model'),installed_kw=engine.get('installed_total'),sfc_g_kwh=p['sfc'],expected_sfc_g_kwh=expected_sfc))
    # OM-912, section 7.6: standard nominal reduction ratio 2.27:1.
    check('Reference shaft RPM: 5500 engine RPM / nominal 2.27 reduction',
          math.isclose(noise['propeller_rpm']*2.27,5500,abs_tol=.5),
          dict(propeller_rpm=noise['propeller_rpm'],nominal_reduction=2.27))
    estimate=m['component_masses']
    used=estimate['inputs']
    geometry=result['geometry']
    expected_inputs=dict(wing_area_m2=wing['S'],aspect_ratio=wing['AR'],tc_ratio=wing['tc_ratio'],
        sweep_quarter_rad=math.radians(wing['sweep_deg']),taper_ratio=wing['eta'],
        fuselage_length_m=geometry['fuselage']['length'],
        fuselage_wetted_area_m2=geometry['fuselage']['S_wet'],
        horizontal_tail_arm_m=geometry['horizontal_tail']['l_h'],mission_fuel_mass_kg=m['m_fuel'],
        engine_total_power_kw=result['sizing']['design_point']['power_kw'])
    check('Component estimate uses the solved geometry, mission fuel and installed power',
          all(math.isclose(used[k],v,rel_tol=1e-8,abs_tol=1e-8) for k,v in expected_inputs.items()),
          dict(used={k:used[k] for k in expected_inputs},expected=expected_inputs))
    limits=result['envelope']['limits']
    ultimate=max(abs(limits['n_ult_pos']),abs(limits['n_ult_neg']))
    check('Component ultimate load comes from the final envelope without a second safety factor',
          math.isclose(used['ultimate_load_factor'],ultimate,rel_tol=1e-8),
          dict(used=used['ultimate_load_factor'],envelope=ultimate))
    independent_total=math.fsum(estimate['breakdown'].values())
    check('Independent component masses sum to their unscaled empty-mass estimate',
          math.isclose(independent_total,estimate['m_empty'],abs_tol=1e-8),
          dict(component_sum_kg=independent_total,independent_empty_kg=estimate['m_empty']))
    allocation=m['component_allocation']
    rows=result['bipol_projects']['p3']['component_mass_estimation']['rows']
    assigned=math.fsum(row['assigned_mass_kg'] for row in rows)
    fixed=allocation.get('fixed_masses_kg',{})
    allocation_ok=all(math.isclose(row['assigned_mass_kg'],fixed.get(row['component'],0)+
        (row['estimated_mass_kg']-fixed.get(row['component'],0))*allocation['normalization_factor'],abs_tol=1e-8) for row in rows)
    check('Conditional CG allocation preserves known hardware masses and scales only estimates',
          allocation_ok and math.isclose(assigned,m['m_empty'],abs_tol=1e-8),
          dict(assigned_sum_kg=assigned,adopted_empty_kg=m['m_empty'],
               normalization_factor=allocation['normalization_factor']))
    engine_mass=engine.get('mass') or {}
    check('Rotax 912 UL manufacturer base mass: 55.4 kg; allocated propulsion cannot be lighter',
          engine_mass.get('base_mass_each_kg')==55.4 and
          allocation['assigned_masses_kg']['propulsion']>=55.4*p['n_engines'],
          dict(base_mass_each_kg=engine_mass.get('base_mass_each_kg'),
               allocated_propulsion_kg=allocation['assigned_masses_kg']['propulsion']))
    return checks


def open_checks(result):
    found=[]

    def walk(value,path):
        if isinstance(value,dict):
            if value.get('passed') is False or value.get('ok') is False:
                found.append(dict(path=path,check=value))
            for key,item in value.items():
                walk(item,f'{path}.{key}')
        elif isinstance(value,list):
            for i,item in enumerate(value):walk(item,f'{path}[{i}]')

    for key in ('compliance_checks','bipol1_review','submission_review','engineering_audit'):
        walk(result.get(key),key)
    return found


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'data/design_cases/topic7_source_engine.json')
    parser.add_argument('--output',type=Path,default=ROOT/'work/topic7-audit')
    parser.add_argument('--no-reports',action='store_true',help='Skip HTML generation; preserve numerical and design checks.')
    args=parser.parse_args()
    from database_sandbox import DatabaseSandbox
    sandbox=DatabaseSandbox()
    try:
        from app import app
        from calculations import run_bipol_project
        params=json.loads(args.input.read_text(encoding='utf-8'))
        result=run_bipol_project(params)
        output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
        def save(name,value):
            (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        save('inputs.json',result['params'])
        save('results.json',result)
        invariants=numerical_invariants(result)
        outstanding=open_checks(result)
        reports=[]
        if not args.no_reports:
            with app.test_client() as client:
                for part in range(1,7):
                    response=client.post(f'/report/project/p{part}',json=result['params'])
                    if response.status_code!=200:
                        raise RuntimeError(f'P{part}: report response {response.status_code}: {response.get_data(as_text=True)[:300]}')
                    name=f'P{part}.html'
                    (output/name).write_bytes(response.data)
                    reports.append(dict(project=part,file=name,bytes=len(response.data)))
        passed=all(v['passed'] for v in invariants) and not outstanding
        summary=dict(topic=7,input=str(args.input.resolve()),numerical_invariants=invariants,
                     open_design_checks=outstanding,reports=reports,all_exposed_checks_passed=passed,
                     scope='Preliminary coursework study. Passing exposed checks is not proof of certification, structural substantiation or experimental aerodynamic accuracy.')
        save('audit.json',summary)
        print(json.dumps(dict(output=str(output),invariants_passed=sum(v['passed'] for v in invariants),
                              invariants_total=len(invariants),open_design_checks=len(outstanding),reports=len(reports)),ensure_ascii=False))
        return 0 if passed else 1
    finally:
        sandbox.close()


if __name__=='__main__':
    raise SystemExit(main())

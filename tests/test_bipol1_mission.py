"""Independent balances and graph anchors for BIPOL_1, not snapshots of outputs."""
import math
import pytest
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.mass import calculate_mass_sizing
from calculations.bipol1 import interpolate, RAYMER, CORKE, preliminary_polar, empty_mass_law
from calculations.validation import validate_parameters
from calculations.atmosphere import G0, isa_atmosphere


def base(**changes):
    return validate_parameters(dict(AIRCRAFT_PRESETS['ga_trainer'], **changes))


@pytest.mark.parametrize('drop',[0,100,300])
@pytest.mark.parametrize('method',['auto','iterative'])
def test_closed_form_mission_with_absolute_burn_and_drop(drop,method):
    # Eq. (1) read at two points of equal ordinate: m_e/m_0 = 0,5 for every m_0.
    p=base(m_cargo=300,mass_method=method,payload_drop_kg=drop,range_km=1000,
        return_range_km=400,empty_mass_model='two_point',mass_point_x1=1000,mass_point_y1=.5,
        mass_point_x2=2000,mass_point_y2=.5,
        climb_fraction_mode='reading',corke_start_ordinate=.99,corke_end_ordinate=.98,
        max_power_time_min=10,max_power_kw=200,max_power_sfc=300,loiter_speed_kmh=140)
    r=calculate_mass_sizing(p)
    # BIPOL_1, s. 2–3: K_max of project 1 is read from Fig. 2 (checked in test_raymer_graph_anchor...).
    k=preliminary_polar(p)['kmax']
    cp=p['sfc']/3.6e9
    qout=math.exp(-600000*cp*G0/(p['prop_efficiency']*.94*k))
    qback=math.exp(-400000*cp*G0/(p['prop_efficiency']*.94*k))
    qloiter=math.exp(-p['loiter_time_min']*60*(140/3.6)*cp*G0/(p['prop_efficiency']*.8*k))
    a=.975*(.98/.99)*qout
    b=qback*qloiter*.975
    task=300/1000*200*(10/60)
    useful=r['m_payload']+r['m_crew']
    expected=(useful+1.06*(b*task+(b-1)*drop))/(1-.5-1.06*(1-a*b))
    assert r['m0']==pytest.approx(expected,abs=.051)
    phases=r['mission_phases']
    assert sum(s['fuel_burn_kg'] for s in phases)==pytest.approx(r['fuel_burn_kg'])
    assert phases[-1]['mass_end_kg']==pytest.approx(a*b*expected-b*(drop+task),abs=.001)
    assert r['reserve_fuel_kg']==pytest.approx(.06*r['fuel_burn_kg'])
    assert r['mission_assumptions']['empty_mass_residual_relative']<.001
    assert len(r['iterations'])>=5
    assert r['m0']==pytest.approx(r['m_empty']+r['m_fuel']+useful,abs=.11)
    assert next(s for s in phases if s['key']=='task')['fuel_burn_kg']==pytest.approx(10)
    if drop:
        assert next(s for s in phases if s['key']=='drop')['fuel_burn_kg']==0
        assert not r['sizing_methods']['proportion']['applicable']


def test_methods_agree_without_drop():
    r=calculate_mass_sizing(base())
    assert r['sizing_methods']['proportion']['m0']==pytest.approx(r['sizing_methods']['iterative']['m0'],abs=.001)


def test_selected_trend_cohort_is_used_and_preserved_in_report():
    p=dict(AIRCRAFT_PRESETS['regional_turboprop'],empty_mass_model='trend',mass_initial_guess=25000,trend_nearest_count=20)
    r=run_bipol_project(p)
    law=r['mass']['empty_mass_law']
    assert law['mode']=='trend' and law['n']>=3
    rows=r['bipol_projects']['p1']['trend_analysis']['similar_aircraft']
    # One sample: the law uses every aircraft of the P1 sample that has a usable empty-mass fraction.
    assert len(rows)==20
    assert set(law['aircraft_ids'])=={row['id'] for row in rows if row.get('empty_fraction') and .15<row['empty_fraction']<.95}
    assert r['mass']['m_empty']==pytest.approx(law['A']*r['mass']['m0']**(law['C']+1)*law['k_vs'])


def test_maximum_jet_thrust_uses_total_thrust_and_mass_units():
    p=validate_parameters(dict(AIRCRAFT_PRESETS['vlj_jet'],max_power_time_min=1,
                              max_thrust_kn=20,max_power_sfc=.6))
    r=calculate_mass_sizing(p)
    task=next(s for s in r['mission_phases'] if s['key']=='task')
    assert task['fuel_burn_kg']==pytest.approx(.6*20000/G0/60)


def test_corke_is_ratio_of_graph_ordinates_at_two_isa_mach_numbers():
    # Exact graph anchors M=.5 and M=1, not a fitted altitude penalty.
    p=base(cruise_altitude_m=10000,cruise_speed_kmh=isa_atmosphere(10000)['a']*3.6,
           climb_start_speed_kmh=.5*isa_atmosphere(0)['a']*3.6,climb_fraction_mode='corke')
    r=calculate_mass_sizing(p)
    assert r['fuel_fractions_detail']['climb']==pytest.approx(.960/.984)
    assert interpolate(CORKE,math.sqrt(.5*.7),True)==pytest.approx((.984+.975)/2)


def test_raymer_graph_anchor_and_equation_three():
    p=base(preliminary_polar_mode='raymer',sketch_swet_ratio=4,aspect_ratio=8,gear_retraction='fixed')
    polar=preliminary_polar(p)
    assert polar['wetted_example']=='sketch' and polar['raymer_family']=='prop_fixed'
    assert polar['kmax']==12.5 and not polar['extrapolated']
    assert polar['cx0']==pytest.approx(math.pi*8*.8/(4*12.5**2))
    r=run_bipol_project(p)
    assert r['params']['cx0']==pytest.approx(polar['cx0'])
    assert r['mass']['mission_assumptions']['k_max_preliminary']==12.5
    with pytest.raises(ValueError,match='zakresem'):
        interpolate(RAYMER['prop_fixed'],20)


def test_cx0_of_project_one_follows_the_handout_chain_by_default():
    # Fig. 1: light single (Cessna 150) S_wet/S = 3,9; Fig. 2: retractable-gear propeller curve; eq. (3).
    p=base()
    polar=preliminary_polar(p)
    assert p['preliminary_polar_mode']=='raymer'
    assert polar['wetted_example']=='light_single' and polar['swet_ratio']==3.9
    assert polar['wetted_aspect_ratio']==pytest.approx(p['aspect_ratio']/3.9)
    assert polar['kmax']==pytest.approx(interpolate(RAYMER[polar['raymer_family']],p['aspect_ratio']/3.9))
    assert polar['cx0']==pytest.approx(math.pi*p['aspect_ratio']*p['oswald_e']/(4*polar['kmax']**2))
    low,high=polar['cx0_bounds']
    assert polar['cx0_in_range']==(low<=polar['cx0']<=high)
    # The graph remains the default; an explicitly selected aircraft C_D0 is respected.
    direct=validate_parameters(dict(AIRCRAFT_PRESETS['ga_trainer'],preliminary_polar_mode='input',cx0=.03))
    assert direct['preliminary_polar_mode']=='input'
    assert preliminary_polar(direct)['cx0']==.03


def test_reading_beyond_the_printed_curve_follows_its_square_root_shape():
    from calculations.bipol1 import read_raymer
    kmax,extrapolated=read_raymer('prop_fixed',4.6)
    assert extrapolated and kmax==pytest.approx(13.5*math.sqrt(2))
    assert read_raymer('prop_fixed',2)==(12.5,False)
    p=base(aspect_ratio=14,gear_retraction='fixed')
    polar=preliminary_polar(p)
    assert polar['extrapolated'] and polar['kmax']==pytest.approx(13.5*math.sqrt(14/3.9/2.3))


def test_two_point_mass_law_preserves_endpoints_and_kvs():
    p=base(empty_mass_model='two_point',mass_point_x1=1000,mass_point_y1=.6,
           mass_point_x2=2000,mass_point_y2=.55,variable_sweep=True)
    share,meta=empty_mass_law(p)
    assert share(1000)==pytest.approx(.6*1.04)
    assert share(2000)==pytest.approx(.55*1.04)
    r=calculate_mass_sizing(p)
    assert r['m_empty']==pytest.approx(meta['A']*r['m0']**(meta['C']+1)*1.04,abs=.1)


@pytest.mark.parametrize('changes',[
    dict(payload_drop_kg=100,m_cargo=0),
    dict(payload_drop_kg=100,m_cargo=100,mass_method='proportion'),
    dict(return_range_km=3000),
    dict(max_power_time_min=5),
    dict(climb_fraction_mode='reading',corke_start_ordinate=.9,corke_end_ordinate=.99),
    dict(empty_mass_model='two_point',mass_point_x1=1000,mass_point_x2=1000,mass_point_y1=.6,mass_point_y2=.5),
])
def test_inconsistent_missions_rejected(changes):
    with pytest.raises(ValueError):
        calculate_mass_sizing(base(**changes))


def test_drop_flows_to_landing_performance_and_balance():
    p=base(payload_drop_kg=200,m_cargo=300,return_range_km=500)
    r=run_bipol_project(p)
    start=next(s for s in r['mass']['mission_phases'] if s['key']=='landing')['mass_start_kg']
    assert r['sizing']['assumptions']['m_landing_kg']==pytest.approx(start,abs=.11)
    mlw=next(s for s in r['balance']['loading_states'] if s['key']=='mlw')
    assert mlw['mass_kg']==pytest.approx(start,abs=.21)
    assert r['bipol_projects']['p2']['mission_profile']==r['mass']['mission_phases']


def test_project_review_does_not_invent_manual_work_or_missing_data():
    r=run_bipol_project(base(empty_mass_model='trend', trend_reference_mode='design', trend_nearest_count=50))
    c={x['key']:x for x in r['bipol1_review']['checks']}
    assert not c['sketch']['passed'] and not c['mission']['passed']
    # Eq. (1) comes from the program's own trend line of the sample: nothing to write by hand.
    assert c['mass_law']['passed']
    assert not r['bipol1_review']['complete']


def test_production_years_are_not_inferred_from_certification():
    from calculations.trends import dated_rows
    # The database dates variants by certification: the trends say so instead of inventing production years.
    r=run_bipol_project(base())
    ta=r['bipol_projects']['p1']['trend_analysis']
    assert ta['year_basis']=='Rok certyfikacji wariantu (nie rok produkcji)'
    allowed={x['model'] for x in ta['similar_aircraft'] if (x.get('year_basis') or 'certification')=='certification'}
    assert all(point['model'] in allowed for t in ta['time_trends'] for point in t['points'])
    # BIPOL_1 asks for the production year: it is used once the sample has at least as many such dates.
    rows=[dict(id=str(i),year=1990+i,year_basis='production' if i<2 else 'certification') for i in range(5)]
    assert dated_rows(rows)[0]=='certification'
    rows=[dict(row,year_basis='production') if i<4 else row for i,row in enumerate(rows)]
    basis,dated=dated_rows(rows)
    assert basis=='production' and [r['id'] for r in dated]==['0','1','2','3']


def test_report_includes_drop_and_completeness(client):
    p=base(payload_drop_kg=100,m_cargo=100,return_range_km=400)
    response=client.post('/report?sections=p1,p2',json=p)
    assert response.status_code==200
    html=response.get_data(as_text=True)
    assert 'Paliwo i zrzut ładunku w poszczególnych fazach' in html
    # Sprawozdanie nie zawiera list kontrolnych dla autora.
    assert 'Kompletność danych i uzgodnień' not in html
    assert 'nie zakłada się zrzutu' not in html

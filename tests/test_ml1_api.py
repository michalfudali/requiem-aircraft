"""Exercise the actual published method catalog, all linked branches and reports."""
import json

import pytest

from app import app
from calculations.ml1.catalog import catalog
from calculations.ml1.examples import example_workbook
from calculations.ml1.reference import drawing_scale,known_aircraft
from calculations.ml1.wing import assemble_tunnel_polar


@pytest.fixture
def client():return app.test_client()


@pytest.mark.parametrize('method',catalog(),ids=lambda m:m['id'])
def test_every_published_method_example_is_executable_through_the_api(client,method):
    response=client.post('/api/ml1/calculate',json=dict(method=method['id'],inputs=method['inputs']))
    assert response.status_code==200,response.get_json()
    data=json.loads(response.data,parse_constant=lambda v:pytest.fail('Non-finite JSON: '+v))
    assert data['status']=='ok'
    assert data['inputs']==method['inputs']


@pytest.mark.parametrize('kind,pitch',[('glider','variable'),('propeller','variable'),('propeller','fixed'),('jet','variable')])
def test_all_linked_workbook_branches_preserve_p1_mass_and_p3_to_p6_polar(client,kind,pitch):
    inputs=example_workbook(kind,pitch)
    response=client.post('/api/ml1/calculate',json=dict(method='workbook',inputs=inputs))
    assert response.status_code==200,response.get_json()
    result=response.get_json()['result']
    assert result['p1']['flight_mass_kg']==inputs['aircraft']['flight_mass_kg']
    assert result['p1']['mass_basis']=='known_aircraft_fixed_measurements'
    assert len(result['p4']['cases'])==3
    assert result['p3']['least_squares']['oswald_in_course_range']
    if kind=='glider':
        assert result['p5'] is result['p6'] is None
    else:
        for table in result['p6']['offer']['tables']:
            assert table['prandtl']==(kind=='jet')
            assert table['mass_kg']==inputs['aircraft']['flight_mass_kg']
        for schedule in result['p6']['ranges']['schedules']:
            assert schedule['maximum_range'] and schedule['maximum_endurance']
            assert schedule['maximum_range']['prandtl']==(kind=='jet')
        assert result['p6']['offer']['climb_to_theoretical_s'] is None


@pytest.mark.parametrize('kind',['glider','jet'])
def test_workbook_report_contains_offline_charts_and_reproducible_inputs(client,kind):
    inputs=example_workbook(kind)
    inputs['aircraft']['name']='<script>alert("bad")</script>'
    response=client.post('/ml1/report',json=dict(method='workbook',inputs=inputs))
    assert response.status_code==200
    html=response.get_data(as_text=True)
    assert '<svg ' in html
    assert '<script>alert' not in html
    assert 'Dane syntetyczne' in html
    assert 'mass_basis' in html
    assert '<script src=' not in html and '<link rel="stylesheet"' not in html


@pytest.mark.parametrize('payload',[None,[],dict(method='missing',inputs={}),
    dict(method='prandtl',inputs=dict(cd_incompressible=.02,mach=float('nan'))),
    dict(method='planform_integrals',inputs=dict(stations=[None,None])),
    dict(method='jet_thrust',inputs=dict(engine=[],mach=.5,altitude_m=0)),
    dict(method='workbook',inputs=dict(aircraft=None)),
    dict(method='prandtl',inputs=dict(cd_incompressible=.02,mach=1)),
    dict(method='prandtl',inputs=dict(cd_incompressible=.02,mach=True))])
def test_bad_input_returns_a_readable_validation_error_instead_of_500(client,payload):
    r=client.post('/api/ml1/calculate',json=payload)
    assert r.status_code in (400,415)


def test_course_catalog_has_all_six_projects_and_39_source_files(client):
    data=client.get('/api/ml1/catalog').get_json()
    assert {m['project'] for m in data['methods']}==set(range(1,7))
    assert len(data['sources'])==39
    assert all('Login' not in str(s) and 'Password' not in str(s) for s in data['sources'])
    assert client.get('/ml1').status_code==200


def test_drawing_scaling_and_fixed_aircraft_mass_validation():
    scale=drawing_scale(10,100,target_denominator=50)
    assert scale['current_denominator']==100
    assert scale['print_size_percent']==200
    assert scale['target_length_mm']==200
    bad=example_workbook()['aircraft'];bad['flight_mass_kg']=1100
    with pytest.raises(ValueError):known_aircraft(bad)


def test_critical_drag_extrapolation_requires_opt_in_and_marks_each_completed_point():
    lift=[dict(cl=c,alpha_deg=c*10) for c in (-1,-.5,0,.5,1)]
    drag=[dict(cl=c,cd=.01+.01*abs(c)) for c in (-.5,0,.5)]
    with pytest.raises(ValueError):assemble_tunnel_polar(lift,drag)
    result=assemble_tunnel_polar(lift,drag,allow_critical_extrapolation=True)
    assert result['extrapolated_count']==2
    assert result['rows'][0]['cd']==pytest.approx(.02)
    assert result['rows'][-1]['cd_extrapolated']

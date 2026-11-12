"""Real native geometry must retain the engine and propeller inputs of P3/P4."""
import pytest

from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.openvsp_bridge import vsp, build_model_from_bipol
from calculations.openvsp_integration import build_vsp_aircraft_model


@pytest.mark.skipif(vsp is None, reason='Native OpenVSP API requires a compatible interpreter')
@pytest.mark.parametrize('builder', ['studio', 'analysis'])
@pytest.mark.parametrize('preset', ['ga_trainer', 'regional_turboprop', 'vlj_jet', 'motoglider_aos',
                                   'glider_pw5', 'uav_tactical', 'transport'])
def test_native_engine_count_type_diameter_and_blades_match_the_project(builder, preset):
    params = dict(AIRCRAFT_PRESETS['vlj_jet' if preset == 'transport' else preset], blade_count=4,
                  engine_count=1, propeller_blades=2)  # legacy fields must not override canonical inputs
    if preset == 'transport':
        params.update(aircraft_type='jet_transport', category='cs25_transport', n_pax=120,
                      range_km=3500, cruise_speed_kmh=750, cruise_altitude_m=10000, v_stall_kmh=200)
    result = run_bipol_project(params)
    p = result['params']
    if builder == 'studio':
        build_model_from_bipol(result)
    else:
        build_vsp_aircraft_model(result, vsp_module=vsp)
    geoms = list(vsp.FindGeoms())
    propellers = [g for g in geoms if vsp.GetGeomTypeName(g) == 'Propeller']
    jets = [g for g in geoms if vsp.GetGeomName(g).startswith('Gondola')]
    def copies(geom):
        return 2 if int(vsp.GetParmVal(geom, 'Sym_Planar_Flag', 'Sym')) == vsp.SYM_XZ else 1
    if p['engine_type'] == 'prop':
        assert sum(map(copies, propellers)) == p['n_engines']
        for propeller in propellers:
            assert vsp.GetParmVal(propeller, 'Diameter', 'Design') == pytest.approx(result['geometry']['propeller']['diameter_m'])
            assert vsp.GetParmVal(propeller, 'NumBlade', 'Design') == p['blade_count']
    elif p['engine_type'] == 'jet':
        assert not propellers
        assert sum(map(copies, jets)) == p['n_engines']
    else:
        assert not propellers and not jets


@pytest.mark.skipif(vsp is None, reason='Native OpenVSP API requires a compatible interpreter')
@pytest.mark.parametrize('builder', ['studio', 'analysis'])
@pytest.mark.parametrize('preset,expected', [('ga_trainer', 2), ('regional_turboprop', 4)])
def test_unselected_blade_count_matches_the_preliminary_clearance_model(builder, preset, expected):
    params = dict(AIRCRAFT_PRESETS[preset])
    params.pop('blade_count', None)
    params.pop('propeller_blades', None)
    result = run_bipol_project(params)
    if builder == 'studio':
        build_model_from_bipol(result)
    else:
        build_vsp_aircraft_model(result, vsp_module=vsp)
    props = [g for g in vsp.FindGeoms() if vsp.GetGeomTypeName(g) == 'Propeller']
    assert props
    assert all(vsp.GetParmVal(g, 'NumBlade', 'Design') == expected for g in props)

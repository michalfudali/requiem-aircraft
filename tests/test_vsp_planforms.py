"""Independent planform invariants read back from the real OpenVSP model."""
import math

import pytest

from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.openvsp_bridge import vsp, build_model_from_bipol
from calculations.openvsp_integration import build_vsp_aircraft_model


@pytest.mark.skipif(vsp is None, reason='Native OpenVSP API requires a compatible interpreter')
@pytest.mark.parametrize('builder', ['studio', 'analysis'])
@pytest.mark.parametrize('dihedral', [0., 12., -6.])
@pytest.mark.parametrize('planform', ['trapezoidal', 'rectangular', 'compound_trapezoid', 'elliptical', 'swept_trapezoidal'])
def test_native_projected_planform_matches_p3(builder, dihedral, planform):
    # Non-round dimensions also expose rounding at the compound-wing break.
    p = dict(AIRCRAFT_PRESETS['ga_trainer'], wingspan_m=13.73, wing_area_m2=23.13,
             wing_planform=planform, dihedral_deg=dihedral, break_span_ratio=.371,
             sweep_quarter_deg=12., wing_twist_deg=0., wing_incidence_deg=0.,
             airfoil='NACA 0012', airfoil_coordinates='')
    result = run_bipol_project(p)
    wing = result['geometry']['wing']
    if builder == 'studio':
        build_model_from_bipol(result)
        gid = next(g for g in vsp.FindGeoms() if vsp.GetGeomName(g) == 'Skrzydlo_Glowne')
    else:
        gid = build_vsp_aircraft_model(result, vsp_module=vsp)['wing']['geom_id']
    # P3 and the application's 3D preview use the horizontal projection.
    c = math.cos(math.radians(dihedral))
    assert vsp.GetParmVal(gid, 'TotalProjectedSpan', 'WingGeom') == pytest.approx(wing['b'], abs=1e-7)
    assert vsp.GetParmVal(gid, 'TotalArea', 'WingGeom')*c == pytest.approx(wing['S'], abs=1e-7)
    # Integrate the actual native surface outline, independently of section Area.
    # CurvedArea in SDK 3.55 has a quadrature error for unequally spaced sections.
    us = [i/2048 for i in range(2049)]
    le = list(vsp.CompVecPnt01(gid, 0, us, [.5]*len(us)))
    te = list(vsp.CompVecPnt01(gid, 0, us, [0.]*len(us)))
    outline = le+list(reversed(te))
    mesh_area = abs(sum(a.x()*b.y()-b.x()*a.y() for a, b in zip(outline, outline[1:]+outline[:1])))
    assert mesh_area == pytest.approx(wing['S'], rel=1e-5)
    n = vsp.GetNumXSec(vsp.GetXSecSurf(gid, 0))-1
    y = qx = area = chord_squared = 0.
    for i in range(1, n+1):
        group = f'XSec_{i}'
        dy = vsp.GetParmVal(gid, 'Span', group)*c
        cr = vsp.GetParmVal(gid, 'Root_Chord', group)
        ct = vsp.GetParmVal(gid, 'Tip_Chord', group)
        sweep = vsp.GetParmVal(gid, 'Sweep', group)
        y += dy
        qx += dy/c*math.tan(math.radians(sweep))
        area += dy*(cr+ct)  # both halves
        chord_squared += 2*dy*(cr*cr+cr*ct+ct*ct)/3
        assert qx == pytest.approx(y*math.tan(math.radians(12)), abs=1e-7)
        if planform == 'elliptical':
            expected = wing['cr']*math.sqrt(max(0., 1-(2*y/wing['b'])**2))
            assert abs(ct-expected) < .0005*wing['cr']
    assert area == pytest.approx(wing['S'], abs=1e-7)
    assert chord_squared/area == pytest.approx(wing['mac'], rel=.001 if planform == 'elliptical' else 1e-7)
    assert vsp.GetParmVal(gid, 'Root_Chord', 'XSec_1') == pytest.approx(wing['cr'], abs=1e-8)
    assert vsp.GetParmVal(gid, 'Tip_Chord', f'XSec_{n}') == pytest.approx(wing['ct'], abs=1e-8)


@pytest.mark.skipif(vsp is None, reason='Native OpenVSP API requires a compatible interpreter')
@pytest.mark.parametrize('builder', ['studio', 'analysis'])
def test_invalid_planform_does_not_erase_existing_native_geometry(builder):
    from copy import deepcopy
    result = run_bipol_project(dict(AIRCRAFT_PRESETS['ga_trainer']))
    build_model_from_bipol(result)
    original = list(vsp.FindGeoms())
    bad = deepcopy(result)
    bad['geometry']['wing']['S'] *= 1.1
    with pytest.raises(ValueError, match='Przelicz'):
        if builder == 'studio':
            build_model_from_bipol(bad)
        else:
            build_vsp_aircraft_model(bad, vsp_module=vsp)
    assert list(vsp.FindGeoms()) == original


@pytest.mark.skipif(vsp is None, reason='Native OpenVSP API requires a compatible interpreter')
def test_native_error_stack_is_drained_even_when_last_call_flag_stays_true():
    # A native last-call flag is sticky after PopLastError; it is not queue length.
    # A child timeout makes regression fail rather than hang the entire test run.
    import subprocess
    import sys
    code = '''
from calculations.openvsp_bridge import vsp
from calculations.openvsp_integration import _check_vsp_errors
vsp.VSPRenew()
vsp.SetParmVal('MISSING_ID', 'Span', 'XSec_1', 1.)
errors = _check_vsp_errors(vsp, 'regression')
assert errors and all('MISSING_ID' in error for error in errors)
assert not _check_vsp_errors(vsp)
assert vsp.ErrorMgrSingleton.getInstance().GetNumTotalErrors() == 0
print('queue_ok')
'''
    result = subprocess.run([sys.executable, '-c', code], timeout=10, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'queue_ok' in result.stdout

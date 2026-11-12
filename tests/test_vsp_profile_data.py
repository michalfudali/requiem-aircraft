"""Airfoil fidelity and failure atomicity also run when the native SDK is absent."""
import pytest

from calculations.openvsp_integration import _configure_wing_airfoils, build_vsp_aircraft_model
from calculations.vsp_airfoils import resolve_wing_airfoil
from test_openvsp_integration import MockOpenVSP


COORDINATES = 'CUSTOM REFLEX\n1 .002\n.75 .04\n.5 .08\n.25 .06\n.1 .03\n0 0\n.1 -.01\n.25 -.02\n.5 -.01\n1 .002\n'


def test_custom_profile_is_not_replaced_by_a_nearby_naca_shape():
    sdk = MockOpenVSP()
    wing = sdk.AddGeom('WING')
    result = _configure_wing_airfoils(sdk, wing, 'CUSTOM REFLEX', .12, coordinates=COORDINATES,
                                     profile_source='Rzędne testowe autora')
    assert result['mode'] == 'FILE_AIRFOIL' and not result['assumed']
    assert result['source'] == 'Rzędne testowe autora' and result['thickness_mismatch']
    assert result['tc_ratio'] == pytest.approx(.09)
    assert len(sdk.airfoil_points) == 2
    for surfaces in sdk.airfoil_points.values():
        assert surfaces['upper'][3] == pytest.approx((.5, .08, 0))
        assert surfaces['lower'][3] == pytest.approx((.5, -.01, 0))


@pytest.mark.parametrize('invalid', ['named_profile', 'missing_file'])
def test_invalid_profile_cannot_clear_the_current_analysis_model(invalid, tmp_path):
    sdk = MockOpenVSP()
    existing = sdk.AddGeom('POD')
    args = dict(vsp_module=sdk)
    params = {'airfoil':'UNKNOWN WITHOUT COORDINATES'} if invalid == 'named_profile' else {}
    if invalid == 'missing_file':
        args['airfoil_file_path'] = str(tmp_path/'missing.dat')
    with pytest.raises(ValueError):
        build_vsp_aircraft_model({'params':params, 'geometry':{'wing':{'tc_ratio':.12}}}, **args)
    assert list(sdk.geoms) == [existing]


def test_no_profile_choice_remains_an_explicit_assumption():
    profile, metadata = resolve_wing_airfoil({}, .14)
    assert profile is None
    assert metadata['assumed'] and metadata['profile_name'] is None and metadata['warnings']


def test_native_rejection_of_profile_points_cannot_be_reported_as_a_success(monkeypatch):
    sdk = MockOpenVSP()
    wing = sdk.AddGeom('WING')
    def reject(*_):
        sdk.error_mgr.push_error('SetAirfoilPnts', 'Rejected airfoil points')
    monkeypatch.setattr(sdk, 'SetAirfoilPnts', reject)
    with pytest.raises(ValueError, match='Rejected airfoil points'):
        _configure_wing_airfoils(sdk, wing, 'CUSTOM REFLEX', .12, coordinates=COORDINATES)


def test_native_rejection_of_an_airfoil_file_is_not_discarded(monkeypatch, tmp_path):
    from calculations.openvsp_integration import OpenVSPAPIError
    sdk = MockOpenVSP()
    wing = sdk.AddGeom('WING')
    source = tmp_path/'profile.dat';source.write_text(COORDINATES, encoding='utf8')
    def reject(*_):
        sdk.error_mgr.push_error('ReadFileAirfoil', 'Rejected airfoil file')
    monkeypatch.setattr(sdk, 'ReadFileAirfoil', reject)
    with pytest.raises(OpenVSPAPIError, match='Rejected airfoil file'):
        _configure_wing_airfoils(sdk, wing, '', .12, airfoil_file_path=str(source))

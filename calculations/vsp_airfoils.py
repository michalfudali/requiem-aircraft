"""Use the selected 2D profile in both OpenVSP builders, without shape substitution.

Official API: https://openvsp.org/api_docs/3.55.0/group___x_sec.html
SetAirfoilPnts expects upper/lower vectors from leading to trailing edge.
"""
import math

from calculations.airfoils import airfoil_200mm


def resolve_wing_airfoil(params, tc_ratio):
    name = str(params.get('airfoil') or '').strip()
    coordinates = str(params.get('airfoil_coordinates') or '').strip()
    if not name and not coordinates:
        return None, dict(mode='FOUR_SERIES', assumed=True, profile_name=None, tc_ratio=tc_ratio,
                          warnings=['Nie wybrano profilu skrzydła: model 3D używa założonego profilu '
                                    '4-cyfrowego o strzałce 2% w 40% cięciwy.'])
    try:
        profile = airfoil_200mm(name, coordinates)
    except ValueError as exc:
        raise ValueError('OpenVSP: nie można odtworzyć wybranego profilu skrzydła. '
                         'Uzupełnij poprawne rzędne lub wybierz obsługiwane oznaczenie NACA. ' + str(exc)) from exc
    thickness = profile.get('nominal_thickness_ratio', profile['thickness_ratio'])
    mismatch = not math.isclose(thickness, tc_ratio, abs_tol=1e-4)
    warnings = (['Geometria 3D zachowuje wybrany profil; jego t/c różni się od ręcznego '
                 'założenia t/c w obliczeniach. Uzgodnij profil i założenie grubości.'] if mismatch else [])
    return profile, dict(mode='FILE_AIRFOIL', assumed=False, profile_name=profile['name'],
                         source_kind=profile['kind'], source=params.get('airfoil_source') or profile['note'],
                         tc_ratio=thickness, calculation_tc_ratio=tc_ratio, thickness_mismatch=mismatch,
                         point_count=len(profile['upper'])+len(profile['lower']), warnings=warnings)


def set_coordinate_airfoil(vsp, xsec_surf, xsec_index, profile):
    """Pass dimensionless ordinates directly; no temporary path or t/c rescaling."""
    vsp.ChangeXSecShape(xsec_surf, xsec_index, vsp.XS_FILE_AIRFOIL)
    xsec = vsp.GetXSec(xsec_surf, xsec_index)
    chord = profile['chord_mm']
    upper = [vsp.vec3d(x/chord, y/chord, 0.) for x, y in profile['upper']]
    lower = [vsp.vec3d(x/chord, y/chord, 0.) for x, y in profile['lower']]
    vsp.SetAirfoilPnts(xsec, upper, lower)
    manager = vsp.ErrorMgrSingleton.getInstance()
    errors = []
    while manager.GetErrorLastCallFlag():
        errors.append(manager.PopLastError().GetErrorString())
    if errors:
        raise ValueError('OpenVSP nie przyjął rzędnych profilu: ' + '; '.join(errors))
    return xsec

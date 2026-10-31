"""Preliminary section increments at 20°/40°, scaled to the equipped wing area.

BIPOL_2 p. 4: a section lift increment applies only to the equipped wing area.
The table remains an estimate, not measured data for the selected airfoil.
"""
import math


FLAPS = {
    'none': (0., 0., 0., 0., None, None),
    'plain': (.30, .60, .010, .035, .74, .68),
    'split': (.30, .65, .018, .060, .74, .68),
    'single_slotted': (.40, .85, .012, .045, .76, .70),
    'flaperon': (.30, .60, .010, .035, .74, .68),
    'fowler': (.55, 1.15, .015, .055, .78, .72),
    'double_slotted': (.50, 1.05, .018, .065, .75, .68),
    'junkers': (.45, .90, .020, .060, .72, .66),
}


def high_lift(params, clean_e=.8, geometry=None):
    lift_to, lift_lnd, drag_to, drag_lnd, e_to, e_lnd = FLAPS[params.get('flap_type', 'single_slotted')]
    slat_lift, slat_drag = {'none': (0, 0), 'slats_auto': (.35, .008),
        'fixed_slot': (.30, .012), 'krueger': (.25, .010)}[params.get('slat_type', 'none')]
    # Unit coverage is used only to seed the coupled geometry/sizing iteration.
    flap_area = slat_area = 1.0
    if geometry is not None:
        devices = geometry['control_surfaces']
        flap_area = devices['flaps']['s_flapped_over_s']
        slat_area = devices['slats']['s_equipped_over_s']
    lift_to, lift_lnd = lift_to * flap_area, lift_lnd * flap_area
    drag_to, drag_lnd = drag_to * flap_area, drag_lnd * flap_area
    slat_lift, slat_drag = slat_lift * slat_area, slat_drag * slat_area
    cl = float(params.get('cz_max_clean', 1.45))
    return dict(delta_cz_to=lift_to, delta_cz_lnd=lift_lnd, delta_cx0_to=drag_to,
        delta_cx0_lnd=drag_lnd, e_to=e_to or clean_e, e_lnd=e_lnd or clean_e,
        slat_lift=slat_lift, slat_drag=slat_drag,
        flap_area_fraction=flap_area, slat_area_fraction=slat_area,
        cz_max_to=cl+lift_to+.5*slat_lift, cz_max_lnd=cl+lift_lnd+slat_lift)


def stall_requirement(params, performance):
    """Project VS0 limit at MTOW, using the unrounded sea-level lift balance.

    This is a preliminary project check, not a CS-23 certification finding.
    Keep legacy performance inputs usable when only the speed table is supplied.
    """
    raw_ms = performance.get('terms', {}).get('vs_lnd')
    actual = float(raw_ms) * 3.6 if raw_ms is not None else float(performance['speeds']['vs_lnd_kmh'])
    limit = float(params['v_stall_kmh'])
    if not all(math.isfinite(v) and v > 0 for v in (actual, limit)):
        raise ValueError('Ocena przeciągnięcia wymaga dodatnich, skończonych prędkości.')
    return dict(limit_kmh=limit, actual_kmh=actual, margin_kmh=limit - actual,
                passed=actual <= limit, basis='project', mass_basis='MTOW',
                speed_basis='EAS', reference_altitude_m=0,
                certification_verified=False,
                note='Wymaganie projektu dla konfiguracji do lądowania przy MTOW. '
                     'Ocena z pełnej precyzji równowagi siły nośnej; bez dodatkowej tolerancji prędkości. '
                     'Nie stanowi wykazania zgodności certyfikacyjnej ani oceny zachowania po przeciągnięciu.')

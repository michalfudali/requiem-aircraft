import pytest
from calculations import run_bipol_project
from calculations.flying_qualities import evaluate_flying_qualities
from calculations.presets import AIRCRAFT_PRESETS


def test_flying_qualities_evaluation_ga_trainer():
    r = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    fq = evaluate_flying_qualities(
        r['params'], r['geometry'], r['aerodynamics'], r['mass'], r['balance'], r['performance']
    )
    assert fq is not None
    # Short period checks
    sp = fq['short_period']
    assert 0.5 <= sp['omega_n_rad_s'] <= 12.0
    assert 0.2 <= sp['damping_ratio_zeta'] <= 2.0
    assert sp['cap_rad_s2_per_g'] > 0.02
    assert sp['cap_level'] in (1, 2)

    # Phugoid checks
    ph = fq['phugoid']
    assert ph['period_s'] > 10.0
    assert ph['damping_ratio_zeta'] >= 0.0

    # Roll mode checks
    rm = fq['roll_mode']
    assert 0.05 <= rm['time_constant_T_R_s'] <= 3.0
    assert rm['time_to_bank_60deg_s'] > 0.0

    # Dutch roll checks
    dr = fq['dutch_roll']
    assert dr['omega_n_rad_s'] > 0.1
    assert dr['damping_criterion_ratio'] >= 0.0523  # JAR-23 compliance
    assert dr['cs23_criterion_passed'] is True


def test_cap_scales_with_static_margin():
    """CAP should increase when static stability margin is increased."""
    r = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    bal1 = dict(r['balance'], stability=dict(r['balance']['stability'], static_margin_aft_pct=5.0))
    bal2 = dict(r['balance'], stability=dict(r['balance']['stability'], static_margin_aft_pct=15.0))
    
    fq1 = evaluate_flying_qualities(r['params'], r['geometry'], r['aerodynamics'], r['mass'], bal1, r['performance'])
    fq2 = evaluate_flying_qualities(r['params'], r['geometry'], r['aerodynamics'], r['mass'], bal2, r['performance'])

    assert fq2['short_period']['cap_rad_s2_per_g'] > fq1['short_period']['cap_rad_s2_per_g']
    assert fq2['short_period']['omega_n_rad_s'] > fq1['short_period']['omega_n_rad_s']


def test_jet_transport_flying_qualities():
    r = run_bipol_project(AIRCRAFT_PRESETS['vlj_jet'])
    fq = evaluate_flying_qualities(
        r['params'], r['geometry'], r['aerodynamics'], r['mass'], r['balance'], r['performance']
    )
    assert fq['overall_summary']['mil_std_overall_level'] in (1, 2, 3)
    assert fq['flight_condition']['mach'] > 0.3


def test_spiral_mode_becomes_stable_with_dihedral():
    """Spirala stateczna, gdy C_lβ·C_nr > C_lr·C_nβ (Nelson, Cook): więcej wzniosu → mniejsze λ_s.

    Wcześniej znak λ_s był odwrócony, a efekt wzniosu (−0,15·Γ) ok. 8 razy za mały.
    """
    r = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
    spiral = lambda dihedral: evaluate_flying_qualities(  # noqa: E731
        dict(r['params'], dihedral_deg=dihedral), r['geometry'], r['aerodynamics'], r['mass'], r['balance'], r['performance']
    )['spiral_mode']
    flat, moderate, steep = spiral(0.0), spiral(4.0), spiral(12.0)
    assert flat['lambda_s'] > moderate['lambda_s'] > steep['lambda_s']
    assert not flat['is_stable'] and steep['is_stable']

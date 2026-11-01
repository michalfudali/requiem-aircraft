"""All ML1 P2 polar-conversion branches and the two P3 approximation methods."""
import math

import pytest

from calculations.ml1.wing import (normalize_polar,fit_lift_slope,glauert_coefficients,
    reynolds_drag_correction,wing_from_section,infer_section_slope,transfer_finite_wing,
    select_reynolds_data,sample_lift_coefficients,fit_parabolic_polar,parabolic_polar_from_chart,
    compare_wing_slope)


POLAR = [dict(cl=cl,cd=.008+.006*cl*cl,alpha_deg=math.degrees(cl/6.18))
         for cl in (-.8,-.6,-.3,0,.3,.6,1.2)]


def test_measured_profile_slope_is_fitted_in_degrees_and_converted_to_per_radian():
    result=fit_lift_slope(POLAR)
    assert result['a_per_rad']==pytest.approx(6.18,rel=1e-13)
    assert result['alpha_zero_lift_deg']==pytest.approx(0,abs=1e-12)
    assert result['count']==5 and result['r_squared']==pytest.approx(1)


def test_glauert_polynomials_match_a_hand_evaluated_reference_case():
    result=glauert_coefficients(6.18,1,6.18)
    assert result['tau']==pytest.approx(.17,abs=1e-13)
    assert result['delta']==pytest.approx(.0487,abs=1e-13)
    ellipse=glauert_coefficients(10,0,6.18,elliptical=True)
    assert ellipse['tau']==ellipse['delta']==0


def test_reynolds_correction_reaches_zero_at_each_asymmetric_critical_lift():
    for cl in (-.8,1.2):
        r=reynolds_drag_correction(cl,.02,1.2,-.8,.008,3e6)
        assert r['delta_cd']==0 and r['cd']==.02
    zero=reynolds_drag_correction(0,.008,1.2,-.8,.008,3e6)
    assert zero['cd']==pytest.approx(.008*.3**.11,rel=1e-13)
    for cl in (-.4,.6):
        half=reynolds_drag_correction(cl,.015,1.2,-.8,.008,3e6)
        assert half['delta_cd']==pytest.approx(zero['delta_cd']/2,rel=1e-13)
    reverse=reynolds_drag_correction(0,.008,1.2,-.8,.008,1e7,3e6)
    assert reverse['delta_cd']>0


def test_wing_conversion_adds_the_actual_material_technical_drag_and_induced_angle():
    smooth=wing_from_section(POLAR,8,.5,a_inf_rad=6.18,elliptical=False)
    wooden=wing_from_section(POLAR,8,.5,a_inf_rad=6.18,material='wood_fabric_mixed')
    assert wooden['cd_technical']/smooth['cd_technical']==pytest.approx(.5/.15,rel=1e-13)
    for original,metal,wood in zip(POLAR,smooth['rows'],wooden['rows']):
        assert wood['cd_wing']-metal['cd_wing']==pytest.approx(.35*smooth['cd_min_corrected'],rel=1e-12)
        assert metal['alpha_wing_deg']==pytest.approx(original['alpha_deg']+
            math.degrees(original['cl']*(1+smooth['corrections']['tau'])/(8*math.pi)),rel=1e-12,abs=1e-12)
    as_polar=[dict(cl=row['cl'],cd=row['cd_wing'],alpha_deg=row['alpha_wing_deg']) for row in smooth['rows']]
    comparison=compare_wing_slope(as_polar,smooth['a_wing_rad'])
    assert comparison['within_ten_percent']
    assert comparison['relative_difference_pct']==pytest.approx(0,abs=1e-11)


def test_inverse_lifting_line_relation_recovers_the_measured_section_slope():
    correction=glauert_coefficients(8,1,6.18)
    aw=6.18/(1+6.18*(1+correction['tau'])/(math.pi*8))
    assert infer_section_slope(aw,8)==pytest.approx(6.18,rel=1e-10)
    ellipse_aw=6.18/(1+6.18/(8*math.pi))
    assert infer_section_slope(ellipse_aw,8,elliptical=True)==pytest.approx(6.18,rel=1e-13)


def test_finite_wing_transfer_is_identity_before_new_technical_drag_at_equal_re_and_geometry():
    result=transfer_finite_wing(POLAR,8,8,a_inf_rad=6.18)
    for original,converted in zip(POLAR,result['rows']):
        assert converted['alpha_wing_deg']==original['alpha_deg']
        assert converted['cd_before_technical']==original['cd']
        assert converted['delta_cd_reynolds']==converted['delta_cd_induced']==0


def test_transfer_to_higher_aspect_ratio_reduces_induced_drag_and_angle():
    measured=wing_from_section(POLAR,6,1,a_inf_rad=6.18,re_from=3e6,re_to=3e6)
    finite_polar=[dict(cl=r['cl'],cd=r['cd_wing'],alpha_deg=r['alpha_wing_deg'])
                  for r in measured['rows']]
    result=transfer_finite_wing(finite_polar,6,10,a_inf_rad=6.18,re_from=3e6,re_to=6e6)
    positive=next(r for r in result['rows'] if r['cl']==.6)
    assert positive['delta_cd_induced']<0 and positive['alpha_delta_rad']<0
    assert positive['delta_cd_reynolds']<0


def test_dataset_selection_uses_the_lowest_re_only_for_missing_stall_measurement():
    datasets=[dict(re=re,rows=POLAR) for re in (1e6,3e6,6e6)]
    result=select_reynolds_data(datasets,500,10,1.5)
    assert result['stall_speed_source']=='estimate_lowest_re'
    assert result['stall_estimate_dataset_re']==1e6
    assert result['selected']['re']==3e6
    measured=select_reynolds_data(datasets,500,10,1.5,45)
    assert measured['stall_speed_ms']==45 and measured['stall_speed_source']=='measured'
    assert measured['selected']['re']==6e6
    exception=select_reynolds_data(datasets[:1],500,10,1.5,finite_wing_data=True)
    assert exception['dataset_count']==1
    assert not exception['has_three_reynolds_datasets']
    with pytest.raises(ValueError):select_reynolds_data(datasets[:1],500,10,1.5)


def test_lift_sampling_keeps_the_table_2_0_endpoints_and_dense_low_lift_values():
    grid=sample_lift_coefficients(1.2)
    assert grid[0]==1.2 and grid[-1]==0
    assert all(a>b for a,b in zip(grid,grid[1:]))
    for point in (.02,.04,.06,.08,.1,.3,.6,.96):
        assert any(abs(point-x)<1e-12 for x in grid)


def test_least_squares_and_graphical_parabolic_methods_agree_on_a_known_polar():
    rows=[dict(cl=cl,cd=.02+.05*cl*cl) for cl in (0,.2,.4,.6,.8,1,1.2)]
    fit=fit_parabolic_polar(rows,8)
    chart=parabolic_polar_from_chart(dict(cl_squared=0,cd=.02),dict(cl_squared=1,cd=.07),8)
    for r in (fit,chart):
        assert r['cd0']==pytest.approx(.02,rel=1e-13)
        assert r['k']==pytest.approx(.05,rel=1e-13)
        assert r['oswald_e']==pytest.approx(1/(.4*math.pi),rel=1e-13)
        assert r['oswald_in_course_range']


def test_a_polar_outside_the_course_oswald_range_is_reported_without_clamping():
    rows=[dict(cl=cl,cd=.02+.02*cl*cl) for cl in (0,.2,.4,.6,.8,1,1.2)]
    fit=fit_parabolic_polar(rows,8)
    assert fit['k']==pytest.approx(.02)
    assert fit['oswald_e']>1 and not fit['oswald_in_course_range']


@pytest.mark.parametrize('data',[[],[dict(cl=0,cd=.02,alpha_deg=0)]*3,
    [dict(cl=cl,cd=.02,alpha_deg=0) for cl in (-1,0,1)]])
def test_invalid_polar_data_are_rejected(data):
    with pytest.raises(ValueError):normalize_polar(data)

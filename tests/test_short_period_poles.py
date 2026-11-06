"""Independent analytical second-order solutions, especially zeta > 1 in topic 7."""
import math

import pytest

from calculations.flying_qualities import short_period_poles


@pytest.mark.parametrize('omega,zeta',[(3,.4),(2,1),(2,2),(1,10**8)])
def test_poles_obey_the_characteristic_polynomial_and_modal_half_time(omega,zeta):
    p=short_period_poles(omega,zeta)
    real=p['dominant_pole_real_s1']
    pole=complex(real,p['pole_imaginary_rad_s'])
    assert abs(pole*pole+2*zeta*omega*pole+omega*omega)<1e-10
    assert math.exp(real*p['modal_half_time_s'])==pytest.approx(.5)
    if zeta>=1:
        assert p['pole_imaginary_rad_s']==0
        assert p['dominant_pole_real_s1']>=p['fast_pole_real_s1']
    else:
        assert p['pole_imaginary_rad_s']>0


def test_overdamped_half_time_uses_the_slow_root_instead_of_the_poles_mean():
    p=short_period_poles(2,2)
    slow=-4+math.sqrt(12)
    assert p['regime']=='overdamped'
    assert p['dominant_pole_real_s1']==pytest.approx(slow)
    assert p['modal_half_time_s']==pytest.approx(math.log(2)/-slow)
    assert p['modal_half_time_s']>5*math.log(2)/4


def test_undamped_mode_has_no_finite_amplitude_half_time():
    p=short_period_poles(3,0)
    assert p['modal_half_time_s'] is None
    assert p['pole_imaginary_rad_s']==3

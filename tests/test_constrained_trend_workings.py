"""A constrained mass model must not be presented as the unconstrained regression."""
import math

import pytest

from calculations.trend_workings import regression_working
from calculations import run_bipol_project
from calculations.bipol1 import run_mission_mass_sizing
from calculations.presets import AIRCRAFT_PRESETS


def test_report_separates_adopted_and_unconstrained_slopes_and_retains_negative_r2():
    # y=x gives OLS slope +1 in log space; adopt -1 through the same centroid.
    # Predictions are 4, 2, 1; the weighted log-space R² is exactly -3.
    fit = dict(kind='power', slope=-1, intercept=math.log(4), A=4, C=-1,
               r2=-3, physically_constrained=True)
    working = regression_working([(1,1),(2,2),(4,4)], [1,1,1], fit)
    assert working['slope'] == -1
    assert working['intercept'] == math.log(4)
    assert working['unconstrained_slope'] == pytest.approx(1)
    assert working['constrained']
    assert 'a_{MNK}' in ' '.join(working['lines'])
    assert 'C_{przyj}' in ' '.join(working['lines'])
    assert working['lines'][-2].endswith('-3{,}0000')


def test_extreme_ga_range_cannot_be_closed_by_extrapolating_to_tens_of_millions_of_kg():
    params = dict(AIRCRAFT_PRESETS['ga_trainer'], range_km=15000)
    with pytest.raises(ValueError, match='dziesięciokrotności górnej masy próby'):
        run_mission_mass_sizing(params)


@pytest.mark.parametrize('preset', ['ga_trainer','motoglider_aos','regional_turboprop'])
def test_representative_projects_remain_inside_the_declared_search_domain(preset):
    result = run_bipol_project(AIRCRAFT_PRESETS[preset])
    law = result['mass']['empty_mass_law']
    assert result['mass']['m0'] <= 10*law['valid_range'][1]

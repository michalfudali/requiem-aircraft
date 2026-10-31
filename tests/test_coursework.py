"""Grade boundaries, real eligibility, evidence freshness and design iteration."""
from copy import deepcopy

import pytest

from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.coursework import PROJECT_MAX, RUBRIC, grade_plan, review_submission


@pytest.fixture(scope='module')
def result():
    return run_bipol_project(dict(AIRCRAFT_PRESETS['pzl_kos']))


def scores(quiz=100):
    return dict(scores=dict(PROJECT_MAX), quiz_points=quiz, quizzes_passed=True)


@pytest.mark.parametrize('total, grade', [(99, 2), (100, 3), (128, 3), (129, 3.5),
    (150, 3.5), (151, 4), (170, 4), (171, 4.5), (190, 4.5), (191, 5), (200, 5)])
def test_regulation_grade_boundaries(total, grade):
    value = scores()
    if total >= 150:
        value['quiz_points'] = total - 100
    else:
        value['quiz_points'] = 50
        # Keep every project positive; total=99 fails the separate project gate.
        points = total - 50
        value['scores'] = {key: maximum * points / 100 for key, maximum in PROJECT_MAX.items()}
    assert grade_plan(value)['grade'] == grade


def test_five_needs_both_parts_and_all_individual_passes():
    value = scores(91)
    assert grade_plan(value)['grade'] == 5
    value['quizzes_passed'] = None
    assert grade_plan(value)['grade'] is None
    value['quizzes_passed'] = False
    assert grade_plan(value)['grade'] == 2
    value = scores()
    value['scores']['p1'] = 0
    # 195/200 still fails the all-projects condition.
    plan = grade_plan(value)
    assert plan['total'] == 195 and plan['grade'] == 2 and not plan['five_possible']
    assert grade_plan(scores(49))['grade'] == 2


def test_missing_scores_are_not_zero_or_earned_checklist_points():
    plan = grade_plan({})
    assert plan['grade'] is None and plan['total'] is None and plan['maximum_possible'] == 200
    assert plan['five_possible']
    plan = grade_plan({'scores': {'p1': 1}})
    assert plan['maximum_possible'] == 196 and plan['remaining_loss_budget'] == 5
    assert plan['grade'] is None
    plan = grade_plan({'scores': {'p3': 10}})
    assert plan['maximum_possible'] == 183 and not plan['five_possible']
    value = scores(97)
    value['scores']['p3'] -= 6
    assert grade_plan(value)['quizzes_needed_for_five'] == 97
    assert grade_plan(value)['grade'] == 5


def test_every_rubric_item_matches_regulation_table_and_existing_ui(client):
    assert len(RUBRIC) == 21
    assert sum(r[2] for r in RUBRIC if r[3]) == 60
    assert sum(r[2] for r in RUBRIC if not r[3]) == 40
    assert list(PROJECT_MAX.values()) == [5, 18, 27, 15, 15, 20]
    import re
    from pathlib import Path
    text = Path('static/js/app.js').read_text(encoding='utf-8')
    for key, _, points, mandatory, *_ in RUBRIC:
        assert re.search(r"id: 'chk_" + key + r"', pts: " + str(points) +
                         r", type: '" + ('obow' if mandatory else 'opcj') + r"'", text)


@pytest.mark.parametrize('value', [None, [], {'scores': []}, {'scores': {'p7': 1}},
    {'scores': {'p1': 6}}, {'scores': {'p1': -1}}, {'scores': {'p1': True}},
    {'scores': {'p1': float('nan')}}, {'quiz_points': float('inf')},
    {'quiz_points': '91'}, {'quizzes_passed': 'yes'}, {'evidence': {'p0_1': {}}},
    {'evidence': {'p1_1': {'note': 'x' * 4001}}},
    {'evidence': {'p1_1': {'note': 'x', 'signature': '<script>'}}}])
def test_bad_grade_inputs_are_rejected_by_both_apis(client, value):
    assert client.post('/api/coursework/grade', json=value).status_code == 400
    assert client.post('/api/calculate', json={**AIRCRAFT_PRESETS['pzl_kos'], 'coursework': value}).status_code == 400


def test_evidence_does_not_erase_failed_checks_and_is_tied_to_actual_results(result):
    changed = deepcopy(result)
    review = changed['submission_review']
    changed['params']['coursework'] = {'evidence': {
        r[0]: {'note': 'Źródło i moje obliczenia.', 'signature': review['signature']} for r in RUBRIC}}
    reviewed = review_submission(changed)
    assert next(i for i in reviewed['items'] if i['key'] == 'p3_1')['status'] == 'review'
    assert next(i for i in reviewed['items'] if i['key'] == 'p1_2')['status'] == 'blocked'
    assert reviewed['grade']['grade'] is None
    changed['params']['student_name'] = 'Anna'
    assert review_submission(changed)['signature'] == review['signature']
    changed['aerodynamics']['cx0_clean'] += .001
    stale = review_submission(changed)
    assert stale['signature'] != review['signature']
    assert next(i for i in stale['items'] if i['key'] == 'p3_1')['status'] == 'stale'


def test_signature_survives_recalculation_and_report_notes(result):
    params = {**result['params'], 'report_notes': 'Moja interpretacja', 'source_notes': 'Moje źródła'}
    again = run_bipol_project(params)
    assert again['submission_review']['signature'] == result['submission_review']['signature']


def test_iteration_resolves_actual_mass_with_p4_polar_and_preserves_inputs(client, result):
    params = deepcopy(result['params'])
    original = deepcopy(params)
    response = client.post('/api/coursework/iterate-polar', json=params)
    assert response.status_code == 200
    answer = response.get_json()
    updated = answer['result']
    assert params == original
    assert updated['params']['cx0'] == result['aerodynamics']['cx0_clean']
    assert updated['params']['oswald_e'] == result['aerodynamics']['oswald_e']
    assert updated['params']['preliminary_polar_mode'] == 'input'
    assert updated['mass']['m0'] != result['mass']['m0']
    assert updated['mass']['mission_assumptions']['mass_residual_relative'] <= .001
    assert updated['submission_review']['signature'] != result['submission_review']['signature']


def test_report_scopes_evidence_escapes_text_and_keeps_grades_private(client, result):
    value = {**scores(91), 'evidence': {
        'p3_1': {'note': '<script>unsafe()</script> Arkusz 3', 'signature': result['submission_review']['signature']},
        'p6_1': {'note': 'TYLKO-P6', 'signature': result['submission_review']['signature']}}}
    response = client.post('/report?sections=p3', json={**result['params'], 'coursework': value})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="submission-review"' in html
    assert '&lt;script&gt;unsafe()&lt;/script&gt; Arkusz 3' in html
    assert '<script>unsafe()</script>' not in html and 'TYLKO-P6' not in html
    assert 'Punkty przyznane' not in html and 'Ocena według wpisanych punktów' not in html


def test_schedule_follows_regulation_calendar():
    """Regulamin 2026/27, slajd 8: tygodnie 1–12 od 5.10.2026, po przerwie tydzień 13 od 11.01.2027."""
    from datetime import date, timedelta
    from calculations.coursework import SCHEDULE, GROUP_DAYS

    def monday(week):
        return date(2026, 10, 5) + timedelta(weeks=week - 1) if week <= 12 else date(2027, 1, 11) + timedelta(weeks=week - 13)
    assert [item['key'] for item in SCHEDULE] == list(PROJECT_MAX)
    assert [item['week'] for item in SCHEDULE] == [3, 5, 8, 10, 11, 14]
    for item in SCHEDULE:
        assert date.fromisoformat(item['wednesday']) == monday(item['week']) + timedelta(days=2)
        assert date.fromisoformat(item['friday']) == monday(item['week']) + timedelta(days=4)
    assert sorted(g for g, day in GROUP_DAYS.items() if day == 'wednesday') == [1, 7, 8]
    assert sorted(g for g, day in GROUP_DAYS.items() if day == 'friday') == [2, 3, 4, 5, 6]


def test_schedule_card_is_rendered_for_every_project():
    from app import app
    html = app.test_client().get('/').get_data(as_text=True)
    assert html.count('data-schedule="p') == 6
    assert 'data-wednesday="2026-11-04" data-friday="2026-11-06"' in html
    assert html.count('data-day="wednesday"') == 3 and html.count('data-day="friday"') == 5

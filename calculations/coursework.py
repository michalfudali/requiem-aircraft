"""Submission review and grade arithmetic from BIPOL I regulations 2026/27.

Readiness never awards points. Scores are entered separately as points awarded
by the instructor. Evidence is an author's declaration, tied to a design basis.
"""
import hashlib
import json
import math

REGULATION = 'BIPOL1_regulamin.pdf, 2026/27, slajdy 7, 9–12 i 17'
TARGET = 191
# The table totals 60 mandatory + 40 optional points. The prose says 68;
# use the explicit table, as in the existing semester rubric.
RUBRIC = (
    ('p1_1', 'Konfiguracja i odręczny szkic', 3, True, 'tab-cad',
     'Wskaż własny szkic A4 w trzech rzutach i uzasadnij konfigurację oraz przewagę nad konstrukcjami porównawczymi.'),
    ('p1_2', 'Analiza trendów', 2, False, 'tab-trends',
     'Podaj arkusz, strony źródeł, warunki danych oraz uzasadnienie doboru próby i parametrów. Omów jakość regresji.'),
    ('p2_1', 'Profil misji i bilans masy', 5, True, 'tab-trends',
     'Wskaż uzgodnienie misji, masę pustą, odczyty wykresów i sprawdzenie bilansu paliwa wszystkich faz.'),
    ('p2_2', 'Dobór profilu', 3, False, 'tab-p1-p2',
     'Porównaj co najmniej trzy profile dla właściwych Re i Macha. Wskaż biegunowe źródłowe i uzasadnij wybór.'),
    ('p2_3', 'Analiza wrażliwości', 2, False, 'tab-p1-p2',
     'Wyjaśnij wpływ masy płatnej i paliwa na MTOW oraz wybór najważniejszego parametru do poprawy.'),
    ('p2_4', 'Wykres doboru skrzydła i napędu', 5, True, 'tab-p1-p2',
     'Wskaż ograniczenie aktywne, punkt projektowy oraz uzasadnienie powierzchni skrzydła i mocy lub ciągu.'),
    ('p2_5', 'Analiza kosztów', 3, True, 'tab-p1-p2',
     'Uzasadnij serię, amortyzację i cenę napędu. Porównaj wynik z konstrukcją podobną; omów ekstrapolację kosztów.'),
    ('p3_1', 'Rysunek samolotu i profilu 200 mm', 15, True, 'tab-cad',
     'Wskaż własny arkusz na papierze milimetrowym: trzy rzuty, skala, wymiary, mocowanie podwozia i profil o cięciwie 200 mm ze zweryfikowanych rzędnych. Format uzgodnij z prowadzącym.'),
    ('p3_2', 'Analiza masowa i skrajne ŚC', 5, True, 'tab-p3',
     'Wskaż źródła mas i ramion oraz analizę załadunku, zużycia paliwa i wariantów pilota. Opisz korektę rozmieszczenia zespołów.'),
    ('p3_3', 'Charakterystyki aerodynamiczne płata', 2, True, 'tab-p3',
     'Podaj źródło charakterystyk profilu i warunki Re/M. Omów Cz(α), Cm(α), Cx(Cz) oraz punkt odniesienia momentu.'),
    ('p3_4', 'Rozkład Schrenka', 5, False, 'tab-p3',
     'Omów rozkład przy Cz=1, całkę siły nośnej, miejsce początku przeciągnięcia i oszacowanie Cz,max płata.'),
    ('p4_1', 'Charakterystyki aerodynamiczne samolotu', 5, True, 'tab-p4',
     'Omów Cz(α), Cm(α), Cz(Cx), K i E w funkcji α i Cz. Uzasadnij opory zespołów i zakres użycia modelu.'),
    ('p4_2', 'Biegunowa prędkości dla skrajnych ŚC', 3, False, 'tab-p4',
     'Porównaj biegunowe dla przedniego i tylnego ŚC, prędkości ekonomiczne i optymalne oraz opór wyważenia.'),
    ('p4_3', 'Mechanizacja płata', 5, False, 'tab-p4',
     'Uzasadnij typ klap, pokrycie rozpiętości i przyrosty Cz/Cx w konfiguracjach 0°/20°/40°.'),
    ('p4_4', 'Charakterystyki zespołu napędowego', 2, False, 'tab-p4',
     'Wskaż rzeczywisty silnik, charakterystyki prędkościowe i wysokościowe, zużycie paliwa oraz dobór śmigła. Dla szybowca uzgodnij zakres z prowadzącym.'),
    ('p5_1', 'Wykres ofertowy', 5, False, 'tab-p5',
     'Omów prędkości charakterystyczne, kąt i prędkość wznoszenia oraz pułap teoretyczny i praktyczny.'),
    ('p5_2', 'Zasięg i długotrwałość', 4, False, 'tab-p5',
     'Porównaj wyniki na wymaganych wysokościach i przy zadanej prędkości; opisz paliwo przelotowe, rezerwę i ograniczenia napędu.'),
    ('p5_3', 'Start i lądowanie', 4, False, 'tab-p5',
     'Omów całkowitą długość i czas startu do 15 m oraz lądowanie znad 15 m, warunki atmosferyczne i nawierzchnię.'),
    ('p5_4', 'Krytyczna ocena osiągów', 2, True, 'tab-compliance',
     'Porównaj wymaganie z wynikiem i zaproponuj liczbowo uzasadnione zmiany. Wyjaśnij każdy niespełniony warunek.'),
    ('p6_1', 'Obwiednia obciążeń dopuszczalnych', 15, True, 'tab-p6',
     'Uzasadnij podstawę metody, EAS/TAS, prędkości i punkty charakterystyczne oraz podmuchy. Oddziel obciążenia dopuszczalne od niszczących.'),
    ('p6_2', 'Obwiednia od mechanizacji', 5, False, 'tab-p6',
     'Omów pętlę klapową, VF i nF na tle obwiedni głównej oraz warunki użycia mechanizacji.'),
)
PROJECT_MAX = {f'p{i}': sum(r[2] for r in RUBRIC if r[0].startswith(f'p{i}_')) for i in range(1, 7)}

# Regulamin, slajd 8: tydzień oddania każdego projektu; oddaje się na własnych zajęciach projektowych.
# Grupy 1, 7 i 8 mają zajęcia w środę, grupy 2–6 w piątek (slajd 4). Tygodnie 1–12 zaczynają się
# 5.10.2026, a po przerwie świątecznej tydzień 13 zaczyna się 11.01.2027.
SCHEDULE = (
    dict(key='p1', title='Projekt koncepcyjny', week=3, wednesday='2026-10-21', friday='2026-10-23'),
    dict(key='p2', title='Studium wykonalności', week=5, wednesday='2026-11-04', friday='2026-11-06'),
    dict(key='p3', title='Projekt wstępny i analiza masowa', week=8, wednesday='2026-11-25', friday='2026-11-27'),
    dict(key='p4', title='Charakterystyki aerodynamiczne', week=10, wednesday='2026-12-09', friday='2026-12-11'),
    dict(key='p5', title='Osiągi samolotu', week=11, wednesday='2026-12-16', friday='2026-12-18'),
    dict(key='p6', title='Obwiednia obciążeń dopuszczalnych', week=14, wednesday='2027-01-20', friday='2027-01-22'),
)
GROUP_DAYS = {1: 'wednesday', 2: 'friday', 3: 'friday', 4: 'friday', 5: 'friday', 6: 'friday', 7: 'wednesday', 8: 'wednesday'}
GROUP_HOURS = {1: '8:15', 2: '10:15', 3: '10:15', 4: '11:15', 5: '12:15', 6: '13:15', 7: '9:15', 8: '8:15'}


def validate_coursework(value):
    if not isinstance(value, dict) or set(value) - {'scores', 'quiz_points', 'quizzes_passed', 'evidence'}:
        raise ValueError('Plan zaliczenia: nieprawidłowa struktura danych.')
    scores = value.get('scores', {})
    if not isinstance(scores, dict) or set(scores) - PROJECT_MAX.keys():
        raise ValueError('Punktacja: podaj wyłącznie projekty P1–P6.')
    for key, maximum in {**PROJECT_MAX, 'quiz_points': 100}.items():
        number = value.get(key) if key == 'quiz_points' else scores.get(key)
        if number is not None and (type(number) not in (int, float) or not math.isfinite(number) or not 0 <= number <= maximum):
            raise ValueError(f'Punktacja {key}: podaj liczbę od 0 do {maximum} albo pozostaw puste.')
    if value.get('quizzes_passed') is not None and type(value['quizzes_passed']) is not bool:
        raise ValueError('Zaliczenie wszystkich zejściówek: wybierz tak, nie albo brak danych.')
    evidence = value.get('evidence', {})
    if not isinstance(evidence, dict) or set(evidence) - {r[0] for r in RUBRIC}:
        raise ValueError('Odniesienia do opracowań: nieznany podpunkt projektu.')
    for entry in evidence.values():
        if not isinstance(entry, dict) or set(entry) - {'note', 'signature'}:
            raise ValueError('Odniesienie do opracowania: nieprawidłowa struktura.')
        if not isinstance(entry.get('note', ''), str) or len(entry.get('note', '')) > 4000:
            raise ValueError('Odniesienie do opracowania: maksymalnie 4000 znaków.')
        signature = entry.get('signature', '')
        if not isinstance(signature, str) or (signature and (len(signature) != 64 or any(c not in '0123456789abcdef' for c in signature))):
            raise ValueError('Odniesienie do opracowania: nieprawidłowy identyfikator wariantu.')
    return value


def grade_plan(value):
    value = validate_coursework(value)
    scores, quiz = value.get('scores', {}), value.get('quiz_points')
    projects = sum(v for v in scores.values() if v is not None)
    projects_complete = all(scores.get(key) is not None for key in PROJECT_MAX)
    known_losses = sum(maximum - scores[key] for key, maximum in PROJECT_MAX.items() if scores.get(key) is not None)
    known_losses += 100 - quiz if quiz is not None else 0
    maximum = 200 - known_losses
    blockers = []
    if any(v == 0 for v in scores.values()):
        blockers.append('Każdy z sześciu projektów musi być oddany i oceniony powyżej 0 pkt.')
    if projects_complete and projects < 50:
        blockers.append('Suma punktów z projektów musi wynosić co najmniej 50.')
    if quiz is not None and quiz < 50:
        blockers.append('Suma punktów z zejściówek musi wynosić co najmniej 50.')
    if value.get('quizzes_passed') is False:
        blockers.append('Wymagane jest zaliczenie wszystkich zejściówek.')
    complete = projects_complete and quiz is not None and value.get('quizzes_passed') is not None
    total = projects + quiz if projects_complete and quiz is not None else None
    grade = None
    if blockers:
        grade = 2.0
    elif complete:
        grade = next(g for threshold, g in ((191, 5.0), (171, 4.5), (151, 4.0), (129, 3.5), (100, 3.0), (0, 2.0)) if total >= threshold)
    return dict(target=TARGET, projects_points=projects, projects_complete=projects_complete,
                quiz_points=quiz, total=total, grade=grade, complete=complete, blockers=blockers,
                maximum_possible=maximum, five_possible=maximum >= TARGET and not blockers,
                points_to_five=max(0, TARGET-total) if total is not None else None,
                quizzes_needed_for_five=max(0, TARGET-projects) if projects_complete else None,
                projects_needed_for_five=max(0, TARGET-quiz) if quiz is not None else None,
                remaining_loss_budget=9-known_losses,
                basis=REGULATION)


def canonical_json(value):
    """JSON round-trips may turn 5 into 5.0; these represent the same basis."""
    def normalize(v):
        if isinstance(v, dict):
            return {k: normalize(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [normalize(x) for x in v]
        if type(v) in (int, float):
            return float(v) or 0.0
        return v
    return json.dumps(normalize(value), sort_keys=True, ensure_ascii=False, allow_nan=False)


def design_signature(params):
    editorial = {'coursework', 'name', 'report_notes', 'source_notes', 'student_name', 'album_no',
                 'group_no', 'supervisor', 'submission_date', 'academic_year'}
    basis = {k: v for k, v in params.items() if k not in editorial and not k.startswith('_')}
    return hashlib.sha256(canonical_json(basis).encode('utf-8')).hexdigest()


def review_submission(result):
    """Map all 21 graded items to available checks and explicit author work."""
    params, bp = result['params'], result['bipol_projects']
    data = params.get('coursework', {})
    # Include outputs and the actual catalogue cohort: changing a source record
    # can invalidate an argument even when the user's input fields stay equal.
    basis = {key: result[key] for key in ('mass', 'geometry', 'aerodynamics', 'performance', 'balance', 'envelope')}
    basis['trends'] = bp['p1']['trend_analysis']
    signature = hashlib.sha256(('submission-v1:' + design_signature(params) +
        canonical_json(basis)).encode('utf-8')).hexdigest()
    instructor = {c['key']: c for c in result['instructor_review']['checks']}
    bipol1 = {c['key']: c for c in result['bipol1_review']['checks']}

    def course(*keys):
        return [dict(label=instructor[k]['label'], passed=instructor[k]['passed'], detail=instructor[k]['detail'])
                for k in keys if k in instructor]

    def b1(*keys):
        return [dict(label=bipol1[k]['label'], passed=bipol1[k]['passed'], detail=bipol1[k]['detail'])
                for k in keys if k in bipol1]

    def check(label, passed, detail):
        return dict(label=label, passed=bool(passed), detail=detail)

    powered = params['engine_type'] != 'none'
    aero = result['aerodynamics']
    performance_checks = [dict(label=c['parameter'], passed=c['passed'], detail=f"{c['required']}; {c['actual']}")
                          for c in result['compliance_checks'] if not c['parameter'].startswith('[')
                          and 'stateczności' not in c['parameter'] and 'ŚC' not in c['parameter']]
    balance = result['balance']
    automatic = {
        'p1_1': b1('sketch', 'mission'),
        'p1_2': course('sample', 'charts', 'mass_trend', 'climb_data') + b1('dates', 'averages'),
        'p2_1': course('iteration', 'cruise', 'start_fraction') + b1('mass_law', 'mass', 'reserve', 'corke', 'mission'),
        'p2_2': [],  # Source polars are external work; catalogue placeholders are not a verified selection.
        'p2_3': [check('Zbieżność wariantów wrażliwości', all(row['d_mtow_kg'] is not None for row in bp['p2']['sensitivity']['table']),
                       'Każdy wariant wymaga rozwiązania bilansu; brak rozwiązania należy omówić.')],
        'p2_4': course('takeoff', 'landing', 'polar_consistency'),
        'p2_5': [],
        'p3_1': [],
        'p3_2': [check('Zakres ŚC', balance['cg_check']['passed'], balance['cg_check']['required']),
                 check('Zapas stateczności ≥5% ŚDA', balance['stability']['static_margin_aft_pct'] >= 5,
                       f"Wynik: {balance['stability']['static_margin_aft_pct']}% ŚDA.")],
        'p3_3': [],
        'p3_4': [],
        'p4_1': course('polar_consistency'),
        'p4_2': [],
        'p4_3': course('flaps'),
        'p4_4': [],
        'p5_1': [],
        'p5_2': [c for c in performance_checks if 'Zasięg' in c['label'] or 'Lot poziomy' in c['label']],
        'p5_3': [c for c in performance_checks if 'długość startu' in c['label'] or 'długość lądowania' in c['label']],
        'p5_4': [],  # A failed target is material to the required critical evaluation, not proof it is absent.
        'p6_1': [],
        'p6_2': [],
    }
    items = []
    for key, label, points, mandatory, target, prompt in RUBRIC:
        evidence = data.get('evidence', {}).get(key, {})
        note = evidence.get('note', '').strip()
        failures = [c for c in automatic[key] if not c['passed']]
        stale = bool(note) and evidence.get('signature') != signature
        status = 'blocked' if failures else 'stale' if stale else 'review' if note else 'manual'
        items.append(dict(key=key, project=key[:2], label=label, points=points, mandatory=mandatory,
                          target=target, prompt=prompt, checks=automatic[key], evidence=note,
                          evidence_stale=stale, status=status))
    polar = dict(assumed_cx0=params['cx0'], calculated_cx0=aero['cx0_clean'],
                 assumed_e=params['oswald_e'], calculated_e=aero['oswald_e'],
                 assumed_kmax=result['mass']['mission_assumptions']['k_max_preliminary'],
                 calculated_kmax=aero['k_max'])
    # The full model and its input cohort identify the basis of this review.
    return dict(basis=REGULATION, signature=signature, items=items, polar=polar,
                grade=grade_plan(data), project_max=PROJECT_MAX,
                blocked=sum(i['status'] == 'blocked' for i in items),
                ready_for_review=sum(i['status'] == 'review' for i in items),
                remaining=sum(i['status'] != 'review' for i in items),
                performance_findings=bp['p5']['performance_findings'],
                powered=powered,
                priority=sorted([i for i in items if i['status'] != 'review'],
                                key=lambda i: (not i['mandatory'], i['status'] != 'blocked', -i['points'])))

"""
Testy weryfikujące 100% zgodności implementacji z wytycznymi BIPOL_1.pdf,
BIPOL_1_wzory.pdf oraz notatkami prowadzącego (docs/WYTYCZNE_PROWADZACEGO.md).
"""

import pytest
import math
from calculations.mass import calculate_mass_sizing, corke_climb_fuel_fraction
from calculations.trends import two_point_coefficients, BIPOL_1_AVERAGES, analyze_trends
from calculations.preliminary import (
    preliminary_insights,
    classify_bipol_cx0,
    BIPOL_1_CX0_TABLE
)
from calculations.presets import AIRCRAFT_PRESETS
from calculations.validation import validate_parameters
from calculations import run_bipol_project


class TestBipol1MassSizing:
    """Weryfikacja metod wyznaczania masy startowej i pustej."""

    def test_proportion_method_balances_equation_five(self):
        """Metoda proporcji (BIPOL_1 s. 4, wzory 4–5) spełnia równanie bilansu masy."""
        params = dict(AIRCRAFT_PRESETS['ga_trainer'])
        params['mass_method'] = 'proportion'
        res = calculate_mass_sizing(params)

        assert res['primary_method'] == 'proportion'
        sizing = res['sizing_methods']['proportion']
        assert sizing['m0'] > 0
        assert sizing['m_empty'] > 0
        assert sizing['m_fuel'] > 0

        # Wzór 5: m0 = (m_pay + m_crew) / (1 - m_f/m0 - m_e/m0)
        m0 = sizing['m0']
        m_useful = res['m_payload'] + res['m_crew']
        f_ratio = sizing['fuel_fraction']
        e_ratio = sizing['empty_fraction']
        expected_m0 = m_useful / (1.0 - f_ratio - e_ratio)
        assert abs(m0 - expected_m0) < 0.5
        assert sizing['residual'] < 0.001

    def test_iterative_method_12_steps_with_payload_drop(self):
        """
        Metoda iteracyjna (BIPOL_1 s. 4, 12 kroków):
        - zrzut ładunku w trakcie misji (m_drop > 0)
        - odrębny dolot (outbound) i powrót (return)
        - zgodność dwóch ocen masy pustej do 0,1% (|Δme| / me,trend < 0.001)
        - zachowanie dokładnego bilansu masy w całym cyklu misji
        """
        params = dict(AIRCRAFT_PRESETS['ga_trainer'])
        params['mass_method'] = 'iterative'
        params['payload_drop_kg'] = 150.0  # zrzut 150 kg
        params['m_cargo'] = 150.0  # zrzucany ładunek musi być na pokładzie
        params['outbound_range_km'] = 600.0
        params['return_range_km'] = 600.0

        res = calculate_mass_sizing(params)

        assert res['primary_method'] == 'iterative'
        sizing = res['sizing_methods']['iterative']
        assert sizing['m_drop'] == 150.0
        assert res['payload_remaining_kg'] == res['m_payload'] - 150.0

        # Zgodność do 0,1%
        assert sizing['residual_relative'] < 0.001

        # Sprawdzenie kroków misji: masa maleje na każdym etapie
        phases = sizing['phases']
        assert phases['m0'] > phases['m1_takeoff']
        assert phases['m1_takeoff'] > phases['m2_climb']
        assert phases['m2_climb'] > phases['m3_outbound']
        assert phases['m3_outbound'] >= phases['m3_post_task']
        assert phases['m3_post_task'] > phases['m4_post_drop']
        assert phases['m4_post_drop'] > phases['m5_return']
        assert phases['m5_return'] > phases['m6_loiter']
        assert phases['m6_loiter'] > phases['m7_landing']

        # O ile lżejszy jest powrót niż dolot z powodu zrzutu:
        # masa na początku dolotu m2 vs masa na początku powrotu m4
        assert phases['m4_post_drop'] < phases['m2_climb'] - 150.0

        # Bilans masy w całym cyklu
        m0 = res['m0']
        m_e = res['m_empty']
        m_f = res['m_fuel']
        m_pay = res['m_payload']
        m_crew = res['m_crew']
        assert abs(m0 - (m_e + m_f + m_pay + m_crew)) < 0.1

    def test_both_sizing_methods_available_simultaneously(self):
        """Obie metody (proporcji i iteracyjna) są liczone i zwracane w sizing_methods."""
        params = dict(AIRCRAFT_PRESETS['regional_turboprop'])
        res = calculate_mass_sizing(params)

        assert 'sizing_methods' in res
        assert 'proportion' in res['sizing_methods']
        assert 'iterative' in res['sizing_methods']

        prop = res['sizing_methods']['proportion']
        it = res['sizing_methods']['iterative']

        assert prop['m0'] > 0
        assert it['m0'] > 0
        assert prop['residual'] < 0.001
        assert it['residual_relative'] < 0.001

    def test_trend_regression_coefficients_feed_mass_solver(self):
        """Współczynniki A, C (dwa punkty linii trendu próby) i Kvs (BIPOL_1 wzór 1) zasilają bilans masy."""
        from calculations.trends import empty_mass_trend
        params = validate_parameters(dict(AIRCRAFT_PRESETS['ga_trainer'], variable_sweep=True,
                                          empty_mass_model='trend', trend_reference_mode='design', trend_nearest_count=50,
                                          empty_mass_trend_A=0.95, empty_mass_trend_C=-0.055))
        res = calculate_mass_sizing(params)
        _, _, points = empty_mass_trend(params)

        assert res['empty_mass_model'] == 'trend'
        assert res['empty_mass_trend'] == {'A': points['A'], 'C': points['C'], 'k_vs': 1.04}
        m0 = res['m0']
        assert res['empty_fraction'] == pytest.approx(points['A'] * m0 ** points['C'] * 1.04, abs=1e-4)


class TestBipol1CorkeClimb:
    """Weryfikacja modelu wznoszenia Corke'a (BIPOL_1 s. 4–5, Rys. 3)."""

    def test_corke_climb_varies_with_altitude_and_mach(self):
        """Udział paliwa wznoszenia maleje (zużycie rośnie) przy wyższym pułapie i prędkości."""
        ff_low = corke_climb_fuel_fraction("prop", h_cr_m=2500.0, v_cr_ms=65.0)
        ff_high = corke_climb_fuel_fraction("prop", h_cr_m=6000.0, v_cr_ms=65.0)

        # Na wyższy pułap potrzeba więcej paliwa, więc m2/m1 jest mniejsze
        assert ff_high < ff_low
        assert 0.94 < ff_high < 1.0
        assert 0.94 < ff_low < 1.0

    def test_corke_climb_jet_vs_prop(self):
        """Wznoszenie odrzutowca i samolotu śmigłowego w modelu Corke'a."""
        ff_prop = corke_climb_fuel_fraction("prop", h_cr_m=8000.0, v_cr_ms=120.0)
        ff_jet = corke_climb_fuel_fraction("jet", h_cr_m=11000.0, v_cr_ms=230.0)

        # The original graph has no separate engine-type penalty. At these
        # subsonic Mach numbers its ratios are much closer to 1 than 0.99.
        assert 0.99 < ff_prop < 1.0
        assert 0.99 < ff_jet < 1.0
        assert ff_jet < ff_prop


class TestBipol1TrendsAndAverages:
    """Weryfikacja modułu analizy trendów i 8 średnich z BIPOL_1 s. 1."""

    def test_eight_bipol1_averages_defined_and_computed(self):
        """Wszystkie 8 średnich parametrów z BIPOL_1 s. 1 (w tym V_V) są obecne."""
        assert len(BIPOL_1_AVERAGES) == 8
        expected_keys = {
            "v_h", "v_v", "empty_fraction",
            "aileron_span_fraction", "aileron_chord_ratio",
            "elevator_chord_ratio", "rudder_chord_ratio", "dihedral_deg"
        }
        assert set(BIPOL_1_AVERAGES) == expected_keys

        proj = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
        averages = proj['bipol_projects']['p1']['trend_analysis']["averages"]
        for key in expected_keys:
            assert key in averages, f"Brak klucza {key} w averages"
            if key != "v_v":
                assert averages[key]["mean"] is not None, f"Pusta średnia dla {key}"
        # The database has no documented V_V for piston aircraft: the average stays missing.
        assert averages["v_v"] == {"mean": None, "n": 0}

        motoglider = run_bipol_project(AIRCRAFT_PRESETS['motoglider_aos'])
        vv = motoglider['bipol_projects']['p1']['trend_analysis']["averages"]["v_v"]
        assert vv["n"] > 0 and 0.01 <= vv["mean"] <= 0.05

    def test_two_point_coefficients_eq_one(self):
        """Wzór (1) z BIPOL_1: C = ln(y1/y2) / ln(x1/x2), A = y1 / x1^C."""
        fit = {
            "kind": "power",
            "intercept": math.log(0.92),
            "C": -0.055,
            "x_min": 1000.0,
            "x_max": 4000.0
        }
        res = two_point_coefficients(fit)
        assert res is not None
        A = res["A"]
        C = res["C"]
        x1, y1 = res["x1"], res["y1"]
        x2, y2 = res["x2"], res["y2"]

        # Sprawdzenie w obu punktach
        assert abs(A * (x1 ** C) - y1) < 1e-6
        assert abs(A * (x2 ** C) - y2) < 1e-6


class TestBipol1PreliminaryAndCx0Table:
    """Weryfikacja oszacowań wstępnych, Raymera i tabeli 7 klas Cx0 (BIPOL_1 s. 2–3)."""

    def test_seven_class_cx0_table_coverage(self):
        """Tabela 7 klas oporu szkodliwego Cx0 z BIPOL_1 s. 3 jest zdefiniowana w całości."""
        assert len(BIPOL_1_CX0_TABLE) == 7
        names = [entry["name"] for entry in BIPOL_1_CX0_TABLE.values()]
        assert "Duże samoloty transportowe" in names
        assert "Jednosilnikowe z podwoziem stałym" in names
        assert "Jednosilnikowe z podwoziem chowanym" in names
        assert "Motoszybowce" in names

    def test_classify_bipol_cx0_ranges(self):
        """Funkcja classify_bipol_cx0 przypisuje projekt do właściwej klasy z tabeli."""
        # Motoszybowiec / Szybowiec
        cls_glider = classify_bipol_cx0({"aircraft_type": "glider"})
        assert cls_glider == 'motoglider'
        assert BIPOL_1_CX0_TABLE[cls_glider]['cx0_range'] == (0.014, 0.020)

        # Piston GA fixed
        cls_ga = classify_bipol_cx0({"aircraft_type": "piston_ga", "gear_type": "fixed"})
        assert cls_ga == 'single_fixed'
        assert BIPOL_1_CX0_TABLE[cls_ga]['cx0_range'] == (0.025, 0.040)

        # Jet transport
        cls_jet = classify_bipol_cx0({"aircraft_type": "jet_transport"})
        assert cls_jet == 'large_transport'
        assert BIPOL_1_CX0_TABLE[cls_jet]['cx0_range'] == (0.018, 0.024)

    def test_preliminary_insights_integrates_bipol1_checks(self):
        """preliminary_insights zwraca kompletne sprawdzenia tabeli Cx0 i Raymera."""
        proj = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer'])
        assert 'bipol_projects' in proj
        p1 = proj['bipol_projects']['p1']
        assert 'preliminary' in p1
        prelim = p1['preliminary']

        assert 'cx0_table_check' in prelim
        table_chk = prelim['cx0_table_check']
        assert 'class_name' in table_chk
        assert 'cx0_range' in table_chk
        assert 'in_range' in table_chk

        assert 'raymer' in prelim
        raymer = prelim['raymer']
        assert 'k_max_raymer' in raymer
        assert 'wetted_aspect_ratio' in raymer
        assert 'cx0_from_raymer' in raymer
        assert 'cx0_from_formula3' in raymer
        assert raymer['k_max_raymer'] > 0

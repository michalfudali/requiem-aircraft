"""
Moduł analizy hałasu i zdatności akustycznej (BiPOL Requiem).
Zgodny z wytycznymi ICAO Annex 16 (Vol. 1) oraz EASA CS-36:
- Rozdział 10: Samoloty napędzane silnikami śmigłowymi o MTOW <= 8618 kg,
- Rozdział 14: Samoloty odrzutowe i komunikacyjne,
- Zależności Hubbarda, Gutierreza i Stone'a (NASA RP-1258 / Raymer rozdz. 10.6).
"""
import math
from calculations.atmosphere import RHO0, isa_atmosphere
from calculations.polish_law import resolve_category


def estimate_aircraft_noise(params: dict, sizing: dict, perf: dict, geom: dict, mass: dict) -> dict:
    """
    Szacuje poziomy hałasu w locie (przelot flyover, linia boczna sideline, podejście approach)
    oraz zgodność z limitami certyfikacyjnymi ICAO Annex 16 / CS-36.
    """
    engine_type = params.get("engine_type", "prop")
    m0 = float(mass.get("m0", 1000.0))
    dp = sizing.get("design_point", {})
    speeds = perf.get("speeds", {})
    climb = perf.get("climb", {})
    wing = geom.get("wing", {})

    # 1. SZYBOWIEC BEZ NAPĘDU — Załącznik 16 go nie obejmuje. Motoszybowiec samostartujący z silnikiem
    #    ocenia się jak samolot śmigłowy (10.1.1 wyłącza tylko motoszybowce samoutrzymujące się).
    if engine_type == "none":
        return {
            "status": "success",
            "icao_standard": "ICAO Załącznik 16: nie dotyczy szybowca bez napędu",
            "metric_unit": "dBA",
            "noise_flyover": None,
            "noise_sideline": None,
            "noise_approach": None,
            "limit_flyover": None,
            "margin_flyover": None,
            "compliant": True,
            "propeller_tip_mach": None,
            "acoustic_category": "Nie dotyczy",
            "didactic_advice": "Bez jednostki napędowej certyfikacja hałasu nie obowiązuje; jedynym źródłem dźwięku jest opływ płatowca."
        }

    # 2. SAMOLOTY ŚMIGŁOWE (ICAO Annex 16 Chapter 10 / CS-36)
    if engine_type == "prop":
        power_kw = float(dp.get("power_kw", 100.0) or 100.0)
        n_engines = max(1, int(params.get("n_engines", 1) or 1))
        p_per_eng_kw = power_kw / n_engines

        # Średnica śmigła i obroty
        prop_dia = float(geom.get("propeller", {}).get("diameter_m", 1.85))
        prop_rpm = float(params.get("propeller_rpm", 2400.0))
        n_rps = prop_rpm / 60.0
        v_tip = math.pi * prop_dia * n_rps
        a_sound = 340.3  # m/s SL
        m_tip = round(v_tip / a_sound, 3)

        # Wznoszenie i wysokość nad punktem pomiarowym flyover (2500 m od punktu startu)
        wy_ms = max(2.0, float(climb.get("wy_max_ms", 4.5) or 4.5))
        v_climb_ms = max(25.0, float(speeds.get("v_lof_kmh", 110.0) or 110.0) / 3.6)
        climb_angle = math.atan2(wy_ms, v_climb_ms)
        h_flyover = max(100.0, min(800.0, 2500.0 * math.tan(climb_angle)))

        # Zależność akustyczna Gutierreza / Hubbarda dla hałasu łopat
        # Im większe M_tip powyżej 0.65, tym gwałtowniejszy wzrost hałasu obrotowego i wirowego
        base_dba = 66.0 + 10.0 * math.log10(max(20.0, power_kw))
        if m_tip > 0.65:
            delta_tip = 45.0 * math.log10(m_tip / 0.65)
        else:
            delta_tip = 0.0

        dist_attenuation = 20.0 * math.log10(h_flyover / 150.0)
        noise_flyover = round(max(55.0, base_dba + delta_tip - dist_attenuation), 1)
        noise_sideline = round(max(58.0, base_dba + delta_tip - 20.0 * math.log10(450.0 / 150.0)), 1)
        noise_approach = round(noise_flyover - 4.5, 1)

        # ICAO Załącznik 16, t. I, rozdz. 10.4: a) 76 dB(A) do 600 kg → 88 dB(A) przy 1400 kg;
        # b) (10.1.6: jednosilnikowe lądowe, wniosek o certyfikat typu od 4.11.1999) 70 dB(A) do 570 kg → 85 dB(A)
        # przy 1500 kg; między punktami liniowo względem logarytmu masy, dalej stałe do 8618 kg.
        single_engine_land = n_engines == 1 and params.get("operating_surface", "land") != "water"
        limit = round(chapter10_limit(m0, single_engine_land), 1)
        limit_basis = "10.4 b) jednosilnikowe" if single_engine_land else "10.4 a)"
        # 10.1.1: rozdział nie obejmuje samolotów akrobacyjnych, rolniczych, pożarniczych i motoszybowców samostartujących.
        if resolve_category(params.get("category")) == "cs23_aerobatic":
            limit, limit_basis = None, "nie dotyczy samolotów akrobacyjnych (10.1.1)"
        elif m0 > 8618.0:
            # Powyżej 8618 kg obowiązują limity EPNdB w trzech punktach (rozdz. 14); model dB(A) ich nie obejmuje.
            limit, limit_basis = None, "MTOM > 8618 kg: rozdz. 14 (EPNdB), poza zakresem tego modelu"

        margin = round(limit - noise_flyover, 1) if limit is not None else None
        compliant = limit is None or noise_flyover <= limit

        if m_tip <= 0.72:
            advice = "Doskonała akustyka: prędkość końcówki śmigła M_tip <= 0.72 gwarantuje cichą pracę i niski poziom hałasu zewnętrznego."
        elif m_tip <= 0.85:
            advice = f"Poziom hałasu mieści się w normie. M_tip = {m_tip:.2f}. Aby zredukować hałas, rozważ śmigło 3-łopatowe o mniejszej średnicy."
        else:
            advice = f"Ostrzeżenie: M_tip = {m_tip:.2f} > 0.85! Generuje silny hałas aerodynamiczny i fale uderzeniowe. Zredukuj RPM lub średnicę śmigła."

        return {
            "status": "success",
            "icao_standard": (f"ICAO Załącznik 16 Rozdział 10, {limit_basis} (CS-36)" if limit is not None
                             else f"ICAO Załącznik 16: {limit_basis}"),
            "metric_unit": "dBA",
            "noise_flyover": noise_flyover,
            "noise_sideline": noise_sideline,
            "noise_approach": noise_approach,
            "limit_flyover": limit,
            "margin_flyover": margin,
            "compliant": compliant,
            "propeller_tip_mach": m_tip,
            "flyover_altitude_m": round(h_flyover, 1),
            "acoustic_category": ("Nie oceniono" if limit is None else "Zgodny z ICAO Ch. 10" if compliant
                                  else "Przekroczenie normy ICAO"),
            "didactic_advice": advice
        }

    # 3. SAMOLOTY ODRZUTOWE (ICAO Annex 16 Chapter 14 / CS-36)
    thrust_kn = float(dp.get("thrust_kn", 15.0) or 15.0)
    bpr = float(params.get("bypass_ratio", 4.5))  # stopień dwuprzepływowości

    # Model Stone'a dla silników dwuprzepływowych (BPR redukuje prędkość gazów wylotowych wg Lighthilla)
    noise_flyover_epn = round(74.0 + 11.0 * math.log10(max(5.0, thrust_kn)) - 8.0 * math.log10(1.0 + bpr), 1)
    noise_sideline_epn = round(noise_flyover_epn + 3.2, 1)
    noise_approach_epn = round(noise_flyover_epn + 1.8, 1)

    # ICAO Załącznik 16, t. I, rozdz. 14.4: limity w trzech punktach pomiarowych, suma zapasów ≥ 17 EPNdB
    # i zapas w każdym punkcie ≥ 1 EPNdB (14.4.1.4–14.4.1.5).
    n_engines = max(1, int(params.get("n_engines", 2) or 2))
    limits = chapter14_limits(m0, n_engines)
    levels = dict(lateral=noise_sideline_epn, flyover=noise_flyover_epn, approach=noise_approach_epn)
    margins = {key: round(limits[key] - levels[key], 1) for key in limits}
    limit_epn = round(limits["flyover"], 1)
    margin_epn = margins["flyover"]
    cumulative = round(sum(margins.values()), 1)
    compliant = cumulative >= 17.0 and min(margins.values()) >= 1.0

    return {
        "status": "success",
        "icao_standard": "ICAO Załącznik 16 Rozdział 14 (CS-36 Turbofan)",
        "metric_unit": "EPNdB",
        "noise_flyover": noise_flyover_epn,
        "noise_sideline": noise_sideline_epn,
        "noise_approach": noise_approach_epn,
        "limit_flyover": limit_epn,
        "margin_flyover": margin_epn,
        "compliant": compliant,
        "bypass_ratio": bpr,
        "limits_epndb": {key: round(value, 1) for key, value in limits.items()},
        "margins_epndb": margins,
        "cumulative_margin_epndb": cumulative,
        "acoustic_category": "Zgodny z ICAO Ch. 14" if compliant else "Wymaga wyższego BPR",
        "didactic_advice": (
            f"Silnik turbowentylatorowy o BPR = {bpr:.1f}. "
            + ("Wysoki stopień dwuprzepływowości skutecznie tłumi hałas strumienia gazów wylotowych (prawo Lighthilla V^8)." if bpr >= 3.0 else
               "Niski BPR (< 3.0) powoduje wysoki hałas gorącego strumienia wylotowego; zaleca się wyższy BPR lub tłumiki akustyczne.")
        )
    }


def chapter10_limit(m0, single_engine_land):
    """Limit hałasu przy starcie [dB(A)] wg ICAO Załącznik 16, t. I, rozdz. 10.4 a) lub b)."""
    m_lo, l_lo, m_hi, l_hi = (570.0, 70.0, 1500.0, 85.0) if single_engine_land else (600.0, 76.0, 1400.0, 88.0)
    if m0 <= m_lo:
        return l_lo
    if m0 >= m_hi:
        return l_hi
    return l_lo + (l_hi - l_lo) * math.log10(m0 / m_lo) / math.log10(m_hi / m_lo)


def chapter14_limits(m0, n_engines=2):
    """Limity [EPNdB] w punktach bocznym, przelotu i podejścia wg ICAO Załącznik 16, t. I, rozdz. 14.4.1."""
    def between(m, m1, v1, m2, v2):
        return v1 + (v2 - v1) * math.log10(m / m1) / math.log10(m2 / m1)

    def piecewise(top_mass, top, mid, low):
        if m0 >= top_mass:
            return top
        if m0 >= 35000.0:
            return between(m0, 35000.0, mid, top_mass, top)
        if m0 >= 8618.0:
            return mid
        return between(max(m0, 2000.0), 2000.0, low, 8618.0, mid)

    top = 101.0 if n_engines <= 2 else 104.0 if n_engines == 3 else 106.0
    if m0 >= 8618.0:
        flyover = top if m0 >= 385000.0 else max(89.0, top - 4.0 * math.log2(385000.0 / m0))
    else:
        flyover = 89.0 - 4.0 * math.log2(8618.0 / max(m0, 2000.0))
    return dict(lateral=piecewise(400000.0, 103.0, 94.0, 88.6), flyover=flyover,
                approach=piecewise(280000.0, 105.0, 98.0, 93.1))

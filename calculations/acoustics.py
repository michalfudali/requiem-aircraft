"""
Moduł analizy hałasu i zdatności akustycznej (BiPOL Requiem).
Zgodny z wytycznymi ICAO Annex 16 (Vol. 1) oraz EASA CS-36:
- Rozdział 10: Samoloty napędzane silnikami śmigłowymi o MTOW <= 8618 kg,
- Rozdział 14: Samoloty odrzutowe i komunikacyjne,
- Zależności Hubbarda, Gutierreza i Stone'a (NASA RP-1258 / Raymer rozdz. 10.6).
"""
import math
from calculations.atmosphere import RHO0, isa_atmosphere


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

    # 1. SZYBOWCE — brak napędu
    if engine_type == "none" or params.get("aircraft_type") in ("glider", "motoglider"):
        return {
            "status": "success",
            "icao_standard": "Szybowiec (brak emisji hałasu silnikowego)",
            "metric_unit": "dBA",
            "noise_flyover": 48.0,
            "noise_sideline": 45.0,
            "noise_approach": 52.0,
            "limit_flyover": 68.0,
            "margin_flyover": 20.0,
            "compliant": True,
            "propeller_tip_mach": None,
            "acoustic_category": "Ultra cichy (aerodynamiczny)",
            "didactic_advice": "Brak jednostki napędowej: jedynym źródłem dźwięku jest szum opływu powietrza wokół płatowca."
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

        # Limit ICAO Załącznik 16 Rozdział 10 dla MTOW:
        # <= 600 kg: 68 dBA; 600 - 1500 kg: wzrost liniowy do 88 dBA; > 1500 kg: 88 dBA
        if m0 <= 600.0:
            limit = 68.0
        elif m0 >= 1500.0:
            limit = 88.0
        else:
            limit = round(68.0 + (m0 - 600.0) * (88.0 - 68.0) / 900.0, 1)

        margin = round(limit - noise_flyover, 1)
        compliant = noise_flyover <= limit

        if m_tip <= 0.72:
            advice = "Doskonała akustyka: prędkość końcówki śmigła M_tip <= 0.72 gwarantuje cichą pracę i niski poziom hałasu zewnętrznego."
        elif m_tip <= 0.85:
            advice = f"Poziom hałasu mieści się w normie. M_tip = {m_tip:.2f}. Aby zredukować hałas, rozważ śmigło 3-łopatowe o mniejszej średnicy."
        else:
            advice = f"Ostrzeżenie: M_tip = {m_tip:.2f} > 0.85! Generuje silny hałas aerodynamiczny i fale uderzeniowe. Zredukuj RPM lub średnicę śmigła."

        return {
            "status": "success",
            "icao_standard": "ICAO Załącznik 16 Rozdział 10 (CS-36)",
            "metric_unit": "dBA",
            "noise_flyover": noise_flyover,
            "noise_sideline": noise_sideline,
            "noise_approach": noise_approach,
            "limit_flyover": limit,
            "margin_flyover": margin,
            "compliant": compliant,
            "propeller_tip_mach": m_tip,
            "flyover_altitude_m": round(h_flyover, 1),
            "acoustic_category": "Zgodny z ICAO Ch. 10" if compliant else "Przekroczenie normy ICAO",
            "didactic_advice": advice
        }

    # 3. SAMOLOTY ODRZUTOWE (ICAO Annex 16 Chapter 14 / CS-36)
    thrust_kn = float(dp.get("thrust_kn", 15.0) or 15.0)
    bpr = float(params.get("bypass_ratio", 4.5))  # stopień dwuprzepływowości

    # Model Stone'a dla silników dwuprzepływowych (BPR redukuje prędkość gazów wylotowych wg Lighthilla)
    noise_flyover_epn = round(74.0 + 11.0 * math.log10(max(5.0, thrust_kn)) - 8.0 * math.log10(1.0 + bpr), 1)
    noise_sideline_epn = round(noise_flyover_epn + 3.2, 1)
    noise_approach_epn = round(noise_flyover_epn + 1.8, 1)

    # Limit Chapter 14 dla małych odrzutowców
    limit_epn = round(84.0 + 4.0 * math.log10(max(1.0, m0 / 1000.0)), 1)
    margin_epn = round(limit_epn - noise_flyover_epn, 1)
    compliant = noise_flyover_epn <= limit_epn

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
        "acoustic_category": "Zgodny z ICAO Ch. 14" if compliant else "Wymaga wyższego BPR",
        "didactic_advice": (
            f"Silnik turbowentylatorowy o BPR = {bpr:.1f}. "
            + ("Wysoki stopień dwuprzepływowości skutecznie tłumi hałas strumienia gazów wylotowych (prawo Lighthilla V^8)." if bpr >= 3.0 else
               "Niski BPR (< 3.0) powoduje wysoki hałas gorącego strumienia wylotowego; zaleca się wyższy BPR lub tłumiki akustyczne.")
        )
    }

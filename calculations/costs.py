"""Analiza kosztów wg BIPOL_2 (C. Galiński, Studium wykonalności, wzory 13–21 i 5.10;
współczynniki z T. Corke, Design of Aircraft).

Koszty liczy się dla współczynników z 1970 i 1986 r. i ekstrapoluje liniowo do roku
docelowego. Roboczogodziny i stawki ekstrapoluje się osobno, a koszt robocizny jest ich
iloczynem; koszty podane w USD ekstrapoluje się bezpośrednio. Fazy RDT&E (prototypy)
i produkcji (seria N_P) liczy się osobno; C_D i C_FT występują tylko w fazie RDT&E.
"""
LB_PER_KG = 2.20462
KT_PER_KMH = 0.539957
LBF_PER_KN = 224.809

# C1, C2 (W_s), C3 (V_max), C4 (N), [C5 (R)]
COEFFICIENTS = {
    "H_E": {1970: (0.027, 0.791, 1.526, 0.183), 1986: (4.860, 0.777, 0.894, 0.163)},
    "C_D": {1970: (0.00549, 0.873, 1.890, 0.346), 1986: (45.42, 0.630, 1.300, 0.0)},
    "H_ML": {1970: (20.348, 0.740, 0.543, 0.524), 1986: (7.370, 0.820, 0.484, 0.641)},
    "C_MM": {1970: (18.47, 0.689, 0.624, 0.792), 1986: (11.00, 0.921, 0.621, 0.799)},
    "H_T": {1970: (2.79, 0.764, 0.899, 0.178, 0.066), 1986: (5.99, 0.777, 0.696, 0.263, 0.0)},
    "C_FT": {1970: (0.000714, 1.160, 1.371, 1.281), 1986: (1243.03, 0.325, 0.822, 1.210)},
}
# Tab. 5.9: stawki godzinowe [USD/h]
RATES = {1970: {"E": 16.00, "T": 11.50, "ML": 10.00, "QC": 10.00},
         1986: {"E": 59.10, "T": 61.70, "ML": 55.40, "QC": 50.10}}
# Wzór (20): H_QC = 0,13 H_ML; dla samolotów towarowych 0,076 (tabela 5.7, 1986).
QC_FACTOR = 0.13
QC_FACTOR_CARGO = 0.076
# Wzór (15), 1970: C1 = 109 dla silnika turboodrzutowego, 130 dla turbowentylatorowego.
ENGINE_C1_1970 = {"turbojet": 109.0, "turbofan": 130.0}
# Ceny silników tłokowych i turbośmigłowych są poza wzorem (15); przyjęto ceny rynkowe
# w USD roku docelowego na kW mocy startowej, do zastąpienia ofertą producenta.
PISTON_USD_PER_KW = 350.0
TURBOPROP_USD_PER_KW = 1000.0
AVIONICS_USD = {"glider": 8000.0, "motoglider": 15000.0}
DEFAULT_AVIONICS_USD = 28000.0


def _extrapolate(v1970, v1986, year):
    return v1986 + (v1986 - v1970) * (year - 1986) / (1986 - 1970)


def _cer(name, year, w_lb, v_kt, n, rate=1.0):
    c = COEFFICIENTS[name][year]
    value = c[0] * w_lb ** c[1] * v_kt ** c[2] * n ** c[3]
    return value * rate ** c[4] if len(c) > 4 else value


def engine_price(params, year, thrust_kn, power_kw, mach_max):
    """Cena jednego silnika [USD roku docelowego] i opis podstawy."""
    engine_type = params.get("engine_type", "prop")
    n = max(1, int(params.get("n_engines", 1) or 1))
    if engine_type == "none":
        return 0.0, "brak zespołu napędowego"
    if "engine_price_usd" in params:
        return float(params["engine_price_usd"]), "cena podana w założeniach"
    if engine_type == "jet":
        t_lb = (thrust_kn or 0.0) * LBF_PER_KN / n
        # Stopień dwuprzepływowości 0 oznacza silnik jednoprzepływowy (turboodrzutowy).
        kind = "turbojet" if float(params.get("bypass_ratio", 4.5)) <= 0 else "turbofan"
        tit_k = float(params.get("turbine_inlet_temp_k", 1600.0 if params.get("aircraft_type") == "jet_transport" else 1450.0))
        theta_r = 1.8 * tit_k
        c1970 = ENGINE_C1_1970[kind] * t_lb ** 0.836
        c1986 = 1548.0 * (0.043 * t_lb + 243.25 * mach_max + 0.969 * theta_r - 2228.0)
        label = "turboodrzutowy" if kind == "turbojet" else "turbowentylatorowy"
        return (_extrapolate(c1970, c1986, year),
                f"wzór (15): {label}, T = {t_lb:.0f} lb, M = {mach_max:.2f}, Θ = {theta_r:.0f} °R ({tit_k:.0f} K)")
    per_engine_kw = (power_kw or 0.0) / n
    turboprop = params.get("aircraft_type") == "turboprop_regional"
    rate = TURBOPROP_USD_PER_KW if turboprop else PISTON_USD_PER_KW
    kind = "turbośmigłowy" if turboprop else "tłokowy"
    return rate * per_engine_kw, f"założenie spoza wzoru (15): silnik {kind}, {rate:.0f} USD/kW × {per_engine_kw:.0f} kW"


def calculate_costs(params, m_empty_kg, v_max_kmh, thrust_kn=None, power_kw=None, mach_max=0.3):
    year = int(params.get("cost_year", 2026))
    n_rdte = int(params.get("cost_n_prototypes", 4))
    n_prod = int(params.get("cost_n_production", 250))
    n_am = int(params.get("cost_n_amortization", n_prod))
    rate_rdte = float(params.get("cost_rate_rdte_per_month", n_rdte / 36.0))
    rate_prod = float(params.get("cost_rate_production_per_month", 5.0))
    profit = float(params.get("cost_profit_pct", 12.0)) / 100.0
    qc_factor = float(params.get("cost_qc_factor", QC_FACTOR))
    n_engines = 0 if params.get("engine_type") == "none" else max(1, int(params.get("n_engines", 1) or 1))
    w_lb = m_empty_kg * LB_PER_KG
    v_kt = v_max_kmh * KT_PER_KMH

    rates = {k: _extrapolate(RATES[1970][k], RATES[1986][k], year) for k in RATES[1986]}
    c_en_one, engine_basis = engine_price(params, year, thrust_kn, power_kw, mach_max)
    avionics = float(params.get("avionics_price_usd", AVIONICS_USD.get(params.get("aircraft_type"), DEFAULT_AVIONICS_USD)))

    def phase(n, rate, rdte):
        hours, by_year = {}, {}
        for key, name in (("E", "H_E"), ("ML", "H_ML"), ("T", "H_T")):
            h = [_cer(name, y, w_lb, v_kt, n, rate) for y in (1970, 1986)]
            by_year[name] = h
            hours[key] = max(0.0, _extrapolate(h[0], h[1], year))
        hours["QC"] = qc_factor * hours["ML"]
        usd = {}
        for name in (("C_MM", "C_D", "C_FT") if rdte else ("C_MM",)):
            by_year[name] = [_cer(name, y, w_lb, v_kt, n) for y in (1970, 1986)]
            usd[name] = max(0.0, _extrapolate(*by_year[name], year))
        items = {
            "C_E": hours["E"] * rates["E"],
            "C_D": usd.get("C_D", 0.0),
            "C_ML": hours["ML"] * rates["ML"],
            "C_MM": usd["C_MM"],
            "C_T": hours["T"] * rates["T"],
            "C_QC": hours["QC"] * rates["QC"],
            "C_FT": usd.get("C_FT", 0.0),
            "C_EN": n * (n_engines * c_en_one + avionics),
        }
        total = sum(items.values())
        return {"n": n, "rate_per_month": round(rate, 3), "by_year": by_year,
                "hours_raw": hours, "items_raw": items, "total_raw": total,
                "hours": {k: round(v) for k, v in hours.items()},
                "items_usd": {k: round(v) for k, v in items.items()},
                "total_usd": round(total), "profit_usd": round(profit * total)}

    rdte, prod = phase(n_rdte, rate_rdte, True), phase(n_prod, rate_prod, False)
    # Wzór 5.10: koszty produkcji na egzemplarz serii + RDT&E rozłożone na N_am egzemplarzy.
    min_price = prod["total_usd"] / n_prod + rdte["total_usd"] / n_am
    price = (prod["total_usd"] + prod["profit_usd"]) / n_prod + (rdte["total_usd"] + rdte["profit_usd"]) / n_am
    return {
        "method": "BIPOL_2 (Corke): współczynniki 1970 i 1986, ekstrapolacja liniowa do roku docelowego, wzór 5.10",
        "cost_year": year,
        "series_count": n_prod,
        "amortization_count": n_am,
        "prototypes_rdte": n_rdte,
        "ws_empty_lbs": round(w_lb, 1),
        "vmax_knots": round(v_kt, 1),
        "rates_usd_h": {k: round(v, 2) for k, v in rates.items()},
        "engine_price_usd": round(c_en_one),
        "engine_basis": engine_basis,
        "avionics_price_usd": round(avionics),
        "terms": {"w_lb": w_lb, "v_kt": v_kt, "n_engines": n_engines, "engine_price_raw": c_en_one,
                  "avionics_raw": avionics, "qc_factor": qc_factor, "profit": profit,
                  "rates_raw": rates, "min_price_raw": min_price, "price_raw": price},
        "rdte": rdte,
        "production": prod,
        "rdte_hours": rdte["hours"]["E"],
        "manufacturing_hours_total": prod["hours"]["ML"],
        "quality_control_hours": prod["hours"]["QC"],
        "tooling_hours": prod["hours"]["T"],
        "cd_support_usd": rdte["items_usd"]["C_D"],
        "cft_flight_test_usd": rdte["items_usd"]["C_FT"],
        "cmm_materials_usd": prod["items_usd"]["C_MM"],
        "unit_cost_usd": round(min_price),
        "profit_pct": round(100 * profit, 1),
        "qc_factor": qc_factor,
        "selling_price_usd": round(price),
        "selling_price_pln": round(price * float(params.get("usd_pln", 4.05))),
    }

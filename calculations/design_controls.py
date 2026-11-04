"""Independent design choices which previously required editing project JSON.

Empty optional fields preserve the model's own defaults. Bounds are shared with
server validation; computed values and legacy aliases are never editable here.
"""
GROUPS = [
    ('requirements', 'Lotnisko i wymagania osiągowe', [
        ('airfield_elevation_m', 'Wysokość lotniska [m n.p.m.]'),
        ('airfield_delta_t_k', 'Odchylenie temperatury od ISA [°C]'),
        ('mu_ground', 'Współczynnik oporu toczenia [–]'),
        ('v_max_required_kmh', 'Wymagana prędkość maksymalna przy ziemi TAS [km/h]'),
        ('service_ceiling_m', 'Wymagany pułap praktyczny [m]'),
        ('ceiling_climb_rate_ms', 'Wznoszenie na pułapie [m/s]'),
        ('vmo_kcas', 'VMO / VNO — wymaganie operacyjne [KCAS]'),
        ('mmo', 'MMO — wymaganie operacyjne [–]'),
    ]),
    ('mission', 'Misja i masa załogi', [
        ('loiter_time_min', 'Czas krążenia / oczekiwania [min]'),
        ('mass_iteration_start_kg', 'Pierwsze przybliżenie masy w iteracji [kg]'),
    ]),
    ('towing', 'Holowanie szybowca', [
        ('tow_glider_mass_kg', 'Masa holowanego szybowca [kg]'),
        ('tow_glider_ld', 'Doskonałość holowanego szybowca [–]'),
        ('tow_speed_kmh', 'Prędkość holowania TAS [km/h]'),
        ('tow_climb_rate_ms', 'Wymagane wznoszenie zespołu [m/s]'),
        ('engine_power_limit_kw', 'Graniczna dostępna moc [kW]'),
    ]),
    ('geometry', 'Usterzenie i powierzchnie sterowe', [
        ('v_h', 'Cecha objętościowa usterzenia poziomego V_H [–]'),
        ('v_v', 'Cecha objętościowa usterzenia pionowego V_V [–]'),
        ('ar_h', 'Wydłużenie usterzenia poziomego [–]'),
        ('ar_v', 'Wydłużenie usterzenia pionowego [–]'),
        ('flap_chord_ratio', 'Względna cięciwa klapy c_f/c [–]'),
        ('aileron_span_ratio', 'Rozpiętość lotki względem półskrzydła [–]'),
        ('aileron_chord_ratio', 'Względna cięciwa lotki [–]'),
        ('elevator_chord_ratio', 'Względna cięciwa steru wysokości [–]'),
        ('rudder_chord_ratio', 'Względna cięciwa steru kierunku [–]'),
    ]),
    ('cargo', 'Ładownia', [
        ('cargo_hold_density_kg_m3', 'Gęstość ładunku do szacowania objętości [kg/m³]'),
    ]),
    ('propulsion', 'Napęd i założenia kosztów', [
        ('prop_eff_to', 'Sprawność śmigła podczas startu [–]'),
        ('bypass_ratio', 'Stopień dwuprzepływowości silnika [–]'),
        ('turbine_inlet_temp_k', 'Temperatura przed turbiną do wzoru kosztów [K]'),
        ('cost_rate_rdte_per_month', 'Tempo budowy prototypów [szt./miesiąc]'),
        ('cost_rate_production_per_month', 'Tempo produkcji seryjnej [szt./miesiąc]'),
    ]),
]


def controls():
    from calculations.validation import NUMERIC_LIMITS, NUMERIC_STEPS
    return [{'id': group, 'title': title, 'fields': [
        {'id': key, 'label': label, 'min': NUMERIC_LIMITS[key][0], 'max': NUMERIC_LIMITS[key][1],
         'step': NUMERIC_STEPS.get(key, 'any')}
        for key, label in fields]} for group, title, fields in GROUPS]

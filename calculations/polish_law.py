"""Pomocnicze sprawdzenia wybranych warunków projektu, nie ocena certyfikacyjna.

CS 23.2005: do 19 miejsc pasażerskich i MTOM do 8618 kg dla wszystkich
poziomów 1–4. Poziom osiągów wymaga VNO/VMO (KCAS) i MMO, nie Vcr (TAS).
UE 2019/947 art. 3, 5, 6: kategorie operacji UAS zależą od ryzyka i warunków
operacji. Próg 600 kg nie rozdziela kategorii Specific i Certified.
Przyjęte obciążenia i uproszczona obwiednia są założeniami dydaktycznymi.
Źródła: https://www.easa.europa.eu/en/downloads/22283/en
https://www.easa.europa.eu/en/domains/drones-air-mobility/operating-drone
"""

KT_TO_KMH = 1.852
KMH_TO_KT = 1.0 / 1.852
LB_PER_KG = 2.20462
AVGAS_DENSITY_KG_L = 0.72
JETA1_DENSITY_KG_L = 0.80
CS23_MTOM_MAX_KG = 8618.0
LAW_REF = "t.j. Dz. U. z 2025 r. poz. 1137"
EASA_REF = "Rozporządzenie Parlamentu Europejskiego i Rady (UE) 2018/1139 oraz CS-23/25/VLA/LSA/22"

# Kategorie zdatności wg Tabeli nr 2 t.j. Dz. U. z 2025 r. poz. 1137
K_CATEGORIES = {
    "K1": "K1. Podstawowa (certyfikat typu EASA / UE 2018/1139)",
    "K2": "K2. Konwencyjna (krajowy certyfikat typu, poza UE 2018/1139)",
    "K3": "K3. Specjalna (bez certyfikatu typu, m.in. amatorska do 4 miejsc)",
    "K4": "K4. Kwalifikowana (lista typów zatwierdzonych UL)",
    "K5": "K5. Niekwalifikowana (bez dokumentów zdatności, cele sportowe/rekreacyjne)",
    "K6A": "K6A. Amatorska (≥ 51 % pracy wykonane przez amatora)",
    "K6E": "K6E. Eksperymentalna",
    "K6H": "K6H. Historyczna",
    "K6R": "K6R. Replika",
}

# Pełny rejestr klas i podkategorii EASA oraz prawa krajowego
SUBCATEGORIES = {
    # -------------------------------------------------------------
    # 1. EASA CS-23 Amendment 5 (CS 23.2005) - Normal Category
    # -------------------------------------------------------------
    "cs23_level1": {
        "code": "CS23-L1",
        "easa_code": "CS-23 Level 1",
        "polish_code": "A3.1",
        "class": "A",
        "class_name": "A. Samolot (EASA CS-23 Level 1)",
        "name": "EASA CS-23 Level 1 (Normal • 0–1 pasażer • Lekki / Treningowy)",
        "easa_spec": "CS-23 Amdt 5 (CS 23.2005 Level 1)",
        "mtom_min": None,
        "mtom_max": 8618.0,
        "pax_min": 0,
        "pax_max": 1,
        "occupants_max": 2,
        "crew_min": 1,
        "crew_max": 2,
        "unmanned": False,
        "load_basis": "cs23_normal",
        "design_code": "EASA CS-23 Amdt 5 Level 1",
        "k_allowed": ["K1", "K2", "K3"],
        "occupant_mass_kg": 77.0,
        "aerobatic": False,
    },
    "cs23_level2": {
        "code": "CS23-L2",
        "easa_code": "CS-23 Level 2",
        "polish_code": "A3.1",
        "class": "A",
        "class_name": "A. Samolot (EASA CS-23 Level 2)",
        "name": "EASA CS-23 Level 2 (Normal • 2–6 pasażerów • Turystyczny / GA)",
        "easa_spec": "CS-23 Amdt 5 (CS 23.2005 Level 2)",
        "mtom_min": None,
        "mtom_max": 8618.0,
        "pax_min": 2,
        "pax_max": 6,
        "occupants_max": 8,
        "crew_min": 1,
        "crew_max": 2,
        "unmanned": False,
        "load_basis": "cs23_normal",
        "design_code": "EASA CS-23 Amdt 5 Level 2",
        "k_allowed": ["K1", "K2", "K3"],
        "occupant_mass_kg": 77.0,
        "aerobatic": False,
    },
    "cs23_level3": {
        "code": "CS23-L3",
        "easa_code": "CS-23 Level 3",
        "polish_code": "A3.1",
        "class": "A",
        "class_name": "A. Samolot (EASA CS-23 Level 3)",
        "name": "EASA CS-23 Level 3 (Normal • 7–9 pasażerów • Użytkowy / Dyspozycyjny)",
        "easa_spec": "CS-23 Amdt 5 (CS 23.2005 Level 3)",
        "mtom_min": None,
        "mtom_max": 8618.0,
        "pax_min": 7,
        "pax_max": 9,
        "occupants_max": 11,
        "crew_min": 1,
        "crew_max": 2,
        "unmanned": False,
        "load_basis": "cs23_normal",
        "design_code": "EASA CS-23 Amdt 5 Level 3",
        "k_allowed": ["K1", "K2", "K3"],
        "occupant_mass_kg": 77.0,
        "aerobatic": False,
    },
    "cs23_commuter": {
        "code": "CS23-L4",
        "easa_code": "CS-23 Level 4 / Commuter",
        "polish_code": "A2",
        "class": "A",
        "class_name": "A. Samolot (EASA CS-23 Level 4)",
        "name": "EASA CS-23 Level 4 / Commuter (Regionalny • 10–19 pasażerów • MTOM ≤ 8618 kg)",
        "easa_spec": "CS-23 Amdt 5 (CS 23.2005 Level 4 / Commuter)",
        "mtom_min": None,
        "mtom_max": 8618.0,
        "pax_min": 10,
        "pax_max": 19,
        "occupants_max": 21,
        "crew_min": 1,
        "crew_max": 2,
        "unmanned": False,
        "load_basis": "cs23_commuter",
        "design_code": "EASA CS-23 Amdt 5 Level 4 (Commuter)",
        "k_allowed": ["K1", "K2", "K3"],
        "occupant_mass_kg": 77.0,
        "aerobatic": False,
    },
    "cs23_aerobatic": {
        "code": "CS23-ACRO",
        "easa_code": "CS-23 Aerobatic",
        "polish_code": "A3.3",
        "class": "A",
        "class_name": "A. Samolot (EASA CS-23 Aerobatic)",
        "name": "EASA CS-23 Akrobacyjny (Certified for Aerobatics • n = +6.0 / -3.0)",
        "easa_spec": "CS-23 Amdt 5 (CS 23.2005 Certified for Aerobatics)",
        "mtom_min": None,
        "mtom_max": 8618.0,
        "pax_min": 0,
        "pax_max": 2,
        "occupants_max": 3,
        "crew_min": 1,
        "crew_max": 2,
        "unmanned": False,
        "load_basis": "cs23_aerobatic",
        "design_code": "EASA CS-23 Certified for Aerobatics",
        "k_allowed": ["K1", "K2", "K3"],
        "occupant_mass_kg": 86.0,
        "aerobatic": True,
    },
    # -------------------------------------------------------------
    # 2. EASA CS-VLA (Very Light Aeroplanes)
    # -------------------------------------------------------------
    "cs_vla": {
        "code": "CS-VLA",
        "easa_code": "CS-VLA",
        "polish_code": "A4",
        "class": "A",
        "class_name": "A. Samolot (EASA CS-VLA)",
        "name": "EASA CS-VLA (Bardzo lekki • MTOM ≤ 750 kg, max 2 os., Vs0 ≤ 45 kt)",
        "easa_spec": "EASA CS-VLA (Very Light Aeroplanes)",
        "mtom_min": None,
        "mtom_max": 750.0,
        "occupants_max": 2,
        "pax_min": 0,
        "pax_max": 1,
        "crew_min": 1,
        "crew_max": 1,
        "vs0_max_kmh": 45.0 * KT_TO_KMH,
        "piston_only": True,
        "single_engine": True,
        "unmanned": False,
        "load_basis": "cs_vla",
        "design_code": "EASA CS-VLA",
        "k_allowed": ["K1", "K2"],
        "occupant_mass_kg": 86.0,
        "aerobatic": False,
    },
    # -------------------------------------------------------------
    # 3. EASA CS-LSA (Light Sport Aeroplanes)
    # -------------------------------------------------------------
    "cs_lsa": {
        "code": "CS-LSA",
        "easa_code": "CS-LSA",
        "polish_code": "A5",
        "class": "A",
        "class_name": "A. Samolot (EASA CS-LSA)",
        "name": "EASA CS-LSA (Lekki sportowy • MTOM ≤ 600/650 kg, max 2 os., Vs0 ≤ 45 kt)",
        "easa_spec": "EASA CS-LSA (Light Sport Aeroplanes / ASTM F2245)",
        "mtom_min": None,
        "mtom_max": 600.0,
        "mtom_max_water": 650.0,
        "occupants_max": 2,
        "pax_min": 0,
        "pax_max": 1,
        "crew_min": 1,
        "crew_max": 1,
        "vs0_max_kmh": 45.0 * KT_TO_KMH,
        "piston_only": True,
        "single_engine": True,
        "unmanned": False,
        "load_basis": "cs_lsa",
        "design_code": "EASA CS-LSA (ASTM F2245)",
        "k_allowed": ["K1", "K2"],
        "occupant_mass_kg": 86.0,
        "aerobatic": False,
    },
    # -------------------------------------------------------------
    # 4. EASA CS-25 (Large Aeroplanes)
    # -------------------------------------------------------------
    "cs25_transport": {
        "code": "CS-25",
        "easa_code": "CS-25",
        "polish_code": "A1",
        "class": "A",
        "class_name": "A. Samolot (EASA CS-25)",
        "name": "EASA CS-25 (Large Aeroplanes • podstawa certyfikacji)",
        "easa_spec": "EASA CS-25 (Large Aeroplanes)",
        "mtom_min": None,
        "mtom_max": None,
        "pax_min": 10,
        "pax_max": None,
        "occupants_max": None,
        "crew_min": 2,
        "crew_max": 4,
        "unmanned": False,
        "load_basis": "cs25",
        "design_code": "EASA CS-25",
        "k_allowed": ["K1", "K2", "K3"],
        "occupant_mass_kg": 77.0,
        "aerobatic": False,
    },
    # -------------------------------------------------------------
    # 5. EASA CS-22 (Sailplanes and Powered Sailplanes)
    # -------------------------------------------------------------
    "cs22_glider": {
        "code": "CS-22-GLD",
        "easa_code": "CS-22 Glider",
        "polish_code": "S",
        "class": "S",
        "class_name": "S. Szybowiec (EASA CS-22 Sailplane)",
        "name": "EASA CS-22 (Szybowiec czysty • MTOM ≤ 850 kg, max 2 os., bez napędu)",
        "easa_spec": "EASA CS-22 Subpart A (Sailplanes)",
        "mtom_min": None,
        "mtom_max": 850.0,
        "occupants_max": 2,
        "pax_min": 0,
        "pax_max": 1,
        "crew_min": 1,
        "crew_max": 1,
        "unmanned": False,
        "load_basis": "cs22_utility",
        "design_code": "EASA CS-22 (Sailplanes)",
        "k_allowed": ["K1", "K2"],
        "occupant_mass_kg": 80.0,
        "aerobatic": False,
    },
    "cs22_motoglider": {
        "code": "CS-22-TMG",
        "easa_code": "CS-22 TMG",
        "polish_code": "MG1",
        "class": "MG",
        "class_name": "MG. Motoszybowiec (EASA CS-22 TMG)",
        "name": "EASA CS-22 (Motoszybowiec turystyczny TMG • MTOM ≤ 850 kg, m/b² ≤ 3.0 kg/m²)",
        "easa_spec": "EASA CS-22 Subpart A (Touring Motor Gliders)",
        "mtom_min": None,
        "mtom_max": 850.0,
        "occupants_max": 2,
        "pax_min": 0,
        "pax_max": 1,
        "crew_min": 1,
        "crew_max": 1,
        "w_b2_max": 3.0,
        "unmanned": False,
        "load_basis": "cs22_utility",
        "design_code": "EASA CS-22 (Touring Motor Gliders)",
        "k_allowed": ["K1", "K2"],
        "occupant_mass_kg": 80.0,
        "aerobatic": False,
    },
    # -------------------------------------------------------------
    # 6. EASA Annex I (Art. 2(8) Opt-Out Ultralight / ULM)
    # -------------------------------------------------------------
    "easa_optout_ul": {
        "code": "UL-A",
        "easa_code": "Annex I Opt-out (UL-A)",
        "polish_code": "UL-A",
        "class": "UL",
        "class_name": "UL. Urządzenie latające (EASA 2018/1139 Annex I Opt-out)",
        "name": "EASA Annex I Opt-Out / UL-A (Ultralekki • MTOM ≤ 600/650 kg, max 2 os.)",
        "easa_spec": "Rozporządzenie (UE) 2018/1139 Załącznik I art. 2 ust. 8 / LTF-UL",
        "mtom_min": None,
        "mtom_max": 600.0,
        "mtom_max_water": 650.0,
        "occupants_max": 2,
        "pax_min": 0,
        "pax_max": 1,
        "crew_min": 1,
        "crew_max": 1,
        "vs0_max_kmh": 45.0 * KT_TO_KMH,
        "unmanned": False,
        "load_basis": "ltf_ul",
        "design_code": "LTF-UL / EASA Annex I Opt-Out",
        "k_allowed": ["K4", "K6A", "K6E", "K6H", "K6R"],
        "occupant_mass_kg": 77.0,
        "aerobatic": False,
    },
    "easa_optout_ul115": {
        "code": "UL-115",
        "easa_code": "Annex I (UL-115)",
        "polish_code": "UL-115",
        "class": "UL",
        "class_name": "UL. Urządzenie latające (EASA 2018/1139 Annex I)",
        "name": "EASA Annex I / UL-115 (Jednoosobowy mikrolot • masa własna ≤ 115 kg)",
        "easa_spec": "Rozporządzenie (UE) 2018/1139 Załącznik I pkt 1 lit. e / LTF-UL",
        "mtom_min": None,
        "mtom_max": None,
        "occupants_max": 1,
        "crew_min": 1,
        "crew_max": 1,
        "pax_min": 0,
        "pax_max": 0,
        "empty_mass_max": 115.0,
        "fuel_volume_max_l": 20.0,
        "vmax_kmh": 102.0,
        "empty_wing_loading_max": 10.0,
        "unmanned": False,
        "load_basis": "ltf_ul",
        "design_code": "LTF-UL / EASA Annex I",
        "k_allowed": ["K5"],
        "occupant_mass_kg": 77.0,
        "aerobatic": False,
    },
    # -------------------------------------------------------------
    # 7. EASA UAS (Drones / Unmanned Aircraft Systems)
    # -------------------------------------------------------------
    "easa_uas_specific": {
        "code": "UAS-Spec",
        "easa_code": "UAS Specific",
        "polish_code": "UM (odrębna klasyfikacja krajowa)",
        "class": "UM",
        "class_name": "UM. Bezzałogowy statek powietrzny (EASA UAS Specific)",
        "name": "EASA UAS Specific (kategoria operacji wg ryzyka, bez progu 600 kg)",
        "easa_spec": "UE 2019/947 art. 5 – kategoria operacji Specific",
        "mtom_min": None,
        "mtom_max": None,
        "occupants_max": 0,
        "pax_min": 0,
        "pax_max": 0,
        "crew_min": 0,
        "crew_max": 0,
        "unmanned": True,
        "load_basis": "stanag4671",
        "design_code": "Założenie obliczeniowe STANAG 4671; podstawa zdatności wymaga ustalenia",
        "k_allowed": ["K1"],
        "occupant_mass_kg": 0.0,
        "aerobatic": False,
    },
    "easa_uas_certified": {
        "code": "UAS-Cert",
        "easa_code": "UAS Certified",
        "polish_code": "UM (odrębna klasyfikacja krajowa)",
        "class": "UM",
        "class_name": "UM. Bezzałogowy statek powietrzny (EASA UAS Certified)",
        "name": "EASA UAS Certified (kategoria operacji wg ryzyka, bez progu 600 kg)",
        "easa_spec": "UE 2019/947 art. 6 – kategoria operacji Certified",
        "mtom_min": None,
        "mtom_max": None,
        "occupants_max": 0,
        "pax_min": 0,
        "pax_max": 0,
        "crew_min": 0,
        "crew_max": 0,
        "unmanned": True,
        "load_basis": "stanag4671",
        "design_code": "Założenie obliczeniowe STANAG 4671; podstawa zdatności wymaga ustalenia",
        "k_allowed": ["K1"],
        "occupant_mass_kg": 0.0,
        "aerobatic": False,
    },
}

# Aliasy dla kompatybilności wstecznej (projekty, presety, polskie kody i stare nazwy)
CATEGORY_ALIASES = {
    # Stare nazwy ogólne
    "normal": "cs23_level2",
    "utility": "cs23_level3",
    "aerobatic": "cs23_aerobatic",
    "acrobatic": "cs23_aerobatic",
    "commuter": "cs23_commuter",
    "transport": "cs25_transport",
    "vla": "cs_vla",
    "lsa": "cs_lsa",
    "uav": "easa_uas_specific",
    # Polskie kody t.j. Dz. U. z 2025 r. poz. 1137
    "a1_transport": "cs25_transport",
    "a2_commuter": "cs23_commuter",
    "a3_normal": "cs23_level2",
    "a3_utility": "cs23_level3",
    "a3_aerobatic": "cs23_aerobatic",
    "a4_vla": "cs_vla",
    "a5_lsa": "cs_lsa",
    "mg_utility": "cs22_motoglider",
    "glider": "cs22_glider",
    "szybowiec": "cs22_glider",
    "sailplane": "cs22_glider",
    "motoglider": "cs22_motoglider",
    "motoszybowiec": "cs22_motoglider",
    "tmg": "cs22_motoglider",
    "cs22": "cs22_motoglider",
    "s_glider": "cs22_glider",
    "ul_a": "easa_optout_ul",
    "ul_mg": "cs22_motoglider",
    "ul_115": "easa_optout_ul115",
    "um_heavy": "easa_uas_certified",
    "um_light": "easa_uas_specific",
}

# Dozwolone klasy konstrukcyjne statku w danej podkategorii EASA
AIRCRAFT_TYPE_ALLOWED = {
    "cs23_level1": ["piston_ga", "turboprop_regional", "jet_business"],
    "cs23_level2": ["piston_ga", "turboprop_regional", "jet_business"],
    "cs23_level3": ["piston_ga", "turboprop_regional", "jet_business"],
    "cs23_commuter": ["turboprop_regional", "piston_ga", "jet_business"],
    "cs23_aerobatic": ["piston_ga", "turboprop_regional"],
    "cs_vla": ["piston_ga"],
    "cs_lsa": ["piston_ga"],
    "cs25_transport": ["jet_transport", "turboprop_regional", "jet_business"],
    "cs22_glider": ["glider"],
    "cs22_motoglider": ["piston_ga", "motoglider"],
    "easa_optout_ul": ["piston_ga"],
    "easa_optout_ul115": ["piston_ga"],
    "easa_uas_specific": ["uav"],
    "easa_uas_certified": ["uav"],
}


def resolve_category(category) -> str:
    """Zwraca znormalizowany klucz podkategorii EASA."""
    cat = str(category or "cs23_level2").strip().lower()
    cat = CATEGORY_ALIASES.get(cat, cat)
    return cat if cat in SUBCATEGORIES else "cs23_level2"


def is_unmanned(params: dict) -> bool:
    """Zwraca True, gdy statek jest bezzałogowy (EASA UAS / 0 osób na pokładzie)."""
    if params.get("aircraft_type") == "uav":
        return True
    return SUBCATEGORIES[resolve_category(params.get("category"))]["unmanned"]


def default_category_for(aircraft_type: str) -> str:
    """Domyślna kategoria EASA dla wybranego typu statku."""
    return {
        "glider": "cs22_glider",
        "motoglider": "cs22_motoglider",
        "uav": "easa_uas_specific",
        "jet_transport": "cs25_transport",
        "turboprop_regional": "cs23_commuter",
        "jet_business": "cs23_level3",
    }.get(aircraft_type, "cs23_level2")


def normalize_occupants(params: dict):
    """
    Dostosowuje liczbę osób na pokładzie do wymogów EASA / prawa lotniczego.
    Gwarantuje:
      - 0 osób na pokładzie dla UAS (n_crew=0, n_pax=0, m_pax=0, zadaniowy payload > 0).
      - min. 2 pilotów dla EASA CS-25.
      - max 2 osoby na pokładzie dla CS-VLA, CS-LSA, CS-22, ULM.
      - limity pasażerów dla poziomów CS-23 Amdt 5 (Level 1: max 1, Level 2: max 6, Level 3: max 9, Level 4: max 19).
    """
    p = dict(params)
    notes = []
    ac_type = p.get("aircraft_type", "piston_ga")
    cat_key = resolve_category(p.get("category"))

    # Spójność typu płatowca z kategorią bezzałogową, szybowcową i motoszybowcową
    if ac_type == "uav" and not SUBCATEGORIES[cat_key]["unmanned"]:
        notes.append(f"Typ UAV wymaga kategorii EASA UAS (UE 2019/947) – wybrano 'easa_uas_specific'.")
        cat_key = "easa_uas_specific"
        p["_um_auto"] = True
    elif SUBCATEGORIES[cat_key]["unmanned"] and ac_type != "uav":
        notes.append("Wybrano kategorię bezzałogową EASA UAS – typ statku ustawiono na UAV.")
        ac_type = "uav"
    elif ac_type == "glider":
        if cat_key != "cs22_glider":
            cat_key = "cs22_glider"
            notes.append("Typ Szybowiec przypisano do kategorii EASA CS-22 (Sailplanes).")
        p["engine_type"] = "none"
    elif ac_type == "motoglider":
        if cat_key not in ("cs22_motoglider", "easa_optout_ul"):
            cat_key = "cs22_motoglider"
            notes.append("Typ Motoszybowiec przypisano do kategorii EASA CS-22 (Touring Motor Gliders).")
        if p.get("engine_type") in ("none", "jet"):
            p["engine_type"] = "prop"

    p["aircraft_type"] = ac_type
    p["category"] = cat_key
    sub = SUBCATEGORIES[cat_key]

    n_crew = int(float(p.get("n_crew", 1) or 0))
    n_pax = int(float(p.get("n_pax", 0) or 0))

    if sub["unmanned"]:
        if n_crew or n_pax:
            notes.append(f"EASA UAS (UE 2019/947): Bezzałogowiec – usunięto {n_crew} os. załogi "
                         f"i {n_pax} pasażerów. Na pokładzie 0 osób (sterowanie z GCS).")
        n_crew, n_pax = 0, 0
        p["m_pax"] = 0.0
        m_cargo = float(p.get("m_cargo", 0.0) or 0.0)
        if "m_cargo" not in p:
            p["m_cargo"] = 80.0
            notes.append("UAV bez ładunku – przyjęto domyślnie 80 kg wyposażenia zadaniowego (sensory, łącze C2).")
    else:
        crew_min = sub.get("crew_min", 1)
        if n_crew < crew_min:
            notes.append(f"EASA {sub['easa_code']}: Wymagane min. {crew_min} pilot(ów) na pokładzie – skorygowano.")
            n_crew = crew_min
        # Nie zmieniaj żądanej liczby pasażerów: naruszenie limitu ma być
        # widoczne w wynikach, zamiast obliczania lżejszego, innego samolotu.

        # Masa pilota dla ultralekkich wg przypisów do prawa lotniczego min. 77 kg
        if sub["class"] == "UL":
            m_crew_person = float(p.get("m_crew_person", 90.0) or 90.0)
            if m_crew_person < 77.0:
                p["m_crew_person"] = 77.0
                notes.append("Masa obliczeniowa pilota UL podniesiona do min. 77 kg.")

    p["n_crew"] = n_crew
    p["n_pax"] = n_pax
    return p, notes


def limit_load_factors(category, m0: float):
    """
    Wyznacza dopuszczalne współczynniki przeciążeń manewrowych n+ i n-
    zgodnie z przepisami budowy właściwymi dla danej specyfikacji EASA.
    """
    sub = SUBCATEGORIES[resolve_category(category)]
    basis = sub["load_basis"]
    w_lb = max(1.0, m0) * LB_PER_KG
    n_formula = 2.1 + 24000.0 / (w_lb + 10000.0)

    if basis == "cs25":
        n_pos = min(3.8, max(2.5, n_formula))
        n_neg = -1.0
        ref = "EASA CS-25.337: n+ = max(2,5; 2,1 + 24000/(W+10000)) ≤ 3,8; n- = -1,0"
    elif basis in ("cs23_normal", "cs23_commuter"):
        n_pos = min(3.8, max(2.5, n_formula))
        n_neg = -0.4 * n_pos
        ref = "CS-23 Amdt 4 §23.337(a)(1): n+ = max(2,5; 2,1 + 24000/(W+10000)) ≤ 3,8; n- = -0,4·n+"
    elif basis == "cs23_utility":
        n_pos = 4.4
        n_neg = -0.4 * n_pos
        ref = "CS-23 Amdt 4 §23.337(a)(2) (Utility): n+ = +4,4; n- = -1,76"
    elif basis == "cs23_aerobatic":
        n_pos = 6.0
        n_neg = -0.5 * n_pos
        ref = "CS-23 Amdt 4 §23.337(a)(3) (Aerobatic): n+ = +6,0; n- = -3,0"
    elif basis == "cs_vla":
        n_pos = 3.8
        n_neg = -1.5
        ref = "EASA CS-VLA.337: n+ ≥ 3,8; n- ≥ -1,5"
    elif basis == "cs_lsa":
        n_pos = 4.0
        n_neg = -2.0
        ref = "EASA CS-LSA (ASTM F2245 §4.2): n+ ≥ +4,0; n- ≥ -2,0"
    elif basis == "cs22_utility":
        n_pos = 5.3
        n_neg = -2.65
        ref = "EASA CS-22.337: n1 = +5,3; n4 = -2,65"
    elif basis == "ltf_ul":
        n_pos = 4.0
        n_neg = -2.0
        ref = "LTF-UL §337 / EASA Annex I: n+ = +4,0; n- = -2,0"
    elif basis == "stanag4671":
        w_kg = max(1.0, m0)
        n_pos = min(3.8, 2.1 + 10900.0 / (w_kg + 4536.0))
        n_neg = -0.4 * n_pos
        ref = "EASA CS-UAS / STANAG 4671 USAR.337: n+ = 2,1 + 10900/(W+4536) ≤ 3,8; n- = -0,4·n+"
    else:
        n_pos = min(3.8, max(2.5, n_formula))
        n_neg = -0.4 * n_pos
        ref = "CS-23 Amdt 4 §23.337(a)(1) (Normal)"

    return round(n_pos, 2), round(n_neg, 2), ref


def envelope_speed_family(category) -> str:
    """Zwraca rodzinę współczynników prędkości VC/VD wg CS-23 Amdt 4 §23.335."""
    basis = SUBCATEGORIES[resolve_category(category)]["load_basis"]
    if basis == "cs23_aerobatic":
        return "aerobatic"
    if basis in ("cs23_utility", "cs22_utility"):
        return "utility"
    if basis == "cs25":
        return "transport"
    return "normal"


def suggest_subcategory(m0: float, n_crew: int, n_pax: int, unmanned: bool, engine_type: str, ac_type: str = "piston_ga") -> str:
    """Rekomenduje optymalną kategorię EASA na podstawie obliczonej masy startowej i osób."""
    if unmanned:
        return "easa_uas_specific"
    if ac_type == "glider" or engine_type == "none":
        return "cs22_glider"
    if ac_type == "motoglider":
        return "cs22_motoglider"  # tylko wariant roboczy; wymagana ocena operacji
    if m0 > 8618.0 or n_pax > 19:
        return "cs25_transport"
    if n_pax >= 10:
        return "cs23_commuter"
    if n_pax >= 7:
        return "cs23_level3"
    if n_pax >= 2:
        return "cs23_level2"
    # 0–1 pasażer (max 2 osoby)
    if (n_crew + n_pax) <= 2 and engine_type == "prop":
        if m0 <= 600.0:
            return "cs_lsa"
        if m0 <= 750.0:
            return "cs_vla"
    return "cs23_level1"


def _chk(name, limit, value, ok, source, severity="error"):
    return {
        "name": name,
        "limit": limit,
        "value": value,
        "ok": bool(ok),
        "severity": "ok" if ok else severity,
        "source": source
    }


def check_compliance(params: dict, mass_res: dict, geom_res: dict = None, perf_res: dict = None,
                     envelope_res: dict = None) -> dict:
    """
    Weryfikacja pełnej zgodności projektu ze specyfikacjami EASA
    oraz polskim prawem lotniczym (t.j. Dz. U. z 2025 r. poz. 1137).
    """
    cat_key = resolve_category(params.get("category"))
    sub = SUBCATEGORIES[cat_key]
    ac_type = params.get("aircraft_type", "piston_ga")
    engine_type = params.get("engine_type", "prop")
    k_cat = str(params.get("airworthiness_k") or sub["k_allowed"][0]).upper()
    seaplane = bool(params.get("seaplane", False))

    m0 = float(mass_res.get("m0", 0.0))
    m_empty = float(mass_res.get("m_empty", 0.0))
    m_fuel = float(mass_res.get("m_fuel", 0.0))
    n_crew = int(float(params.get("n_crew", 0) or 0))
    n_pax = int(float(params.get("n_pax", 0) or 0))
    occupants = n_crew + n_pax

    S = float((geom_res or {}).get("wing", {}).get("S", 0.0) or 0.0)
    b = float((geom_res or {}).get("wing", {}).get("b", 0.0) or 0.0)

    speeds = (perf_res or {}).get("speeds", {})
    vs0 = float(speeds.get("vs_lnd_kmh", params.get("v_stall_kmh", 0.0)) or 0.0)
    vmax = float(speeds.get("v_max_sl_kmh", 0.0) or 0.0)
    v_cr = float(speeds.get("v_cruise_kmh", params.get("cruise_speed_kmh", 0.0)) or 0.0)
    v_cr_kt = v_cr * KMH_TO_KT

    checks = []

    # 1. Sprawdzenie dopuszczalności typu statku / napędu w specyfikacji EASA
    allowed_types = AIRCRAFT_TYPE_ALLOWED.get(cat_key, [])
    checks.append(_chk(
        "Klasa konstrukcyjna płatowca zgodna ze specyfikacją EASA",
        ", ".join(allowed_types),
        ac_type,
        ac_type in allowed_types,
        f"{sub['easa_spec']}",
        "warning"
    ))

    # 2. Sprawdzenie limitu masy startowej MTOM wg EASA / t.j. Dz. U. z 2025 r. poz. 1137
    mtom_max = sub.get("mtom_max_water") if (seaplane and sub.get("mtom_max_water")) else sub.get("mtom_max")
    if mtom_max is not None:
        checks.append(_chk(
            "Maksymalna masa startowa MTOM",
            f"≤ {mtom_max:.0f} kg",
            f"{m0:.1f} kg",
            m0 <= mtom_max,
            sub["easa_spec"]
        ))
    if sub.get("mtom_min") is not None:
        checks.append(_chk(
            "Dolna granica masy startowej MTOM",
            f"> {sub['mtom_min']:.0f} kg",
            f"{m0:.1f} kg",
            m0 > sub["mtom_min"],
            sub["easa_spec"],
            "error" if sub["unmanned"] else "warning"
        ))

    # 3. Sprawdzenie liczby osób na pokładzie
    if sub["unmanned"]:
        checks.append(_chk(
            "Osoby na pokładzie (EASA UAS / UE 2019/947)",
            "0 os. (pilot w GCS)",
            f"{occupants} os.",
            occupants == 0,
            "Rozporządzenie (UE) 2019/947 & CS-LUAS/CS-UAS"
        ))
    else:
        # Minimalna załoga
        checks.append(_chk(
            "Minimalna załoga lotnicza",
            f"≥ {sub.get('crew_min', 1)} os.",
            f"{n_crew} os.",
            n_crew >= sub.get("crew_min", 1),
            sub["easa_spec"]
        ))

        # Całkowita liczba miejsc w kabinie
        if sub.get("occupants_max") is not None:
            checks.append(_chk(
                "Maksymalna pojemność kabiny (załoga + pasażerowie)",
                f"≤ {sub['occupants_max']} os.",
                f"{occupants} os.",
                occupants <= sub["occupants_max"],
                sub["easa_spec"]
            ))

        # Liczba pasażerów dla poziomów CS-23 Amdt 5
        if sub.get("pax_max") is not None:
            checks.append(_chk(
                f"Liczba pasażerów dla {sub['easa_code']}",
                f"≤ {sub['pax_max']} pax",
                f"{n_pax} pax",
                n_pax <= sub["pax_max"],
                f"EASA CS 23.2005 ({sub['easa_code']})"
            ))

        # Above the CS-23 mass limit CS-25 applies whatever the seat count (e.g. freighters).
        if sub.get("pax_min") and not (cat_key == "cs25_transport" and m0 > CS23_MTOM_MAX_KG):
            checks.append(_chk(
                f"Zalecany przedział pasażerów dla {sub['easa_code']}",
                f"≥ {sub['pax_min']} pax",
                f"{n_pax} pax",
                n_pax >= sub["pax_min"],
                f"EASA CS 23.2005 ({sub['easa_code']})",
                "warning"
            ))

    # 4. Sprawdzenie prędkości przeciągnięcia VS0 wg EASA (CS-VLA, CS-LSA, ULM ≤ 45 kt CAS)
    if sub.get("vs0_max_kmh"):
        vs0_lim_kmh = sub["vs0_max_kmh"]
        vs0_lim_kt = vs0_lim_kmh * KMH_TO_KT
        checks.append(_chk(
            "Prędkość przeciągnięcia VS0 (CAS)",
            f"≤ {vs0_lim_kmh:.1f} km/h ({vs0_lim_kt:.0f} kt)",
            f"{vs0:.1f} km/h ({vs0 * KMH_TO_KT:.1f} kt)",
            vs0 <= vs0_lim_kmh + 0.1,
            f"{sub['easa_spec']} (wymóg VS0 ≤ 45 kt)"
        ))

    # Vcr jest TAS; nie wolno używać jej zamiast granicznych VMO/VNO (KCAS).
    perf_lvl = "Nie określono – wymagane VMO/VNO (KCAS) i MMO"
    if cat_key.startswith("cs23_"):
        known = params.get("vmo_kcas") is not None and params.get("mmo") is not None
        if known:
            high_speed = float(params["vmo_kcas"]) > 250 or float(params["mmo"]) > 0.6
            perf_lvl = "High Speed" if high_speed else "Low Speed"
        checks.append(_chk(
            "Poziom osiągów CS 23.2005(c)",
            "VMO/VNO ≤ 250 KCAS i MMO ≤ 0,6 dla Low Speed",
            perf_lvl,
            known,
            "EASA CS 23.2005(c); obliczeniowe VC (EAS) nie zastępuje ustalonych VMO/VNO (CAS) i MMO", "warning"
        ))
    if sub["unmanned"]:
        checks.append(_chk(
            "Kategoria operacji UAS wymaga odrębnej oceny ryzyka",
            "Ocena operacji wg UE 2019/947 art. 5–6",
            "Wybrano wariant roboczy; MTOM nie wyznacza kategorii operacji",
            False, "UE 2019/947; kategorie Open / Specific / Certified", "warning"
        ))

    # 6. Napęd pojedynczy tłokowy dla CS-VLA i CS-LSA
    if sub.get("piston_only"):
        checks.append(_chk(
            "Jednostka napędowa: pojedynczy silnik bez turbiny",
            "1 silnik tłokowy / śmigłowy",
            f"{engine_type} ({ac_type})",
            ac_type == "piston_ga" and engine_type == "prop",
            sub["easa_spec"]
        ))

    # 7a. Szybowiec CS-22: brak jednostki napędowej
    if cat_key == "cs22_glider":
        checks.append(_chk(
            "Układ napędowy: brak silnika (szybowiec czysty)",
            "Bez napędu (lot swobodny)",
            "Bez napędu" if engine_type == "none" else f"{engine_type}",
            engine_type == "none",
            "EASA CS-22 Subpart A (Sailplanes)"
        ))

    # 7. Motoszybowiec CS-22: wskaźnik obciążenia rozpiętości m/b² ≤ 3.0 kg/m²
    if sub.get("w_b2_max") and b > 0:
        wb2 = m0 / (b * b)
        checks.append(_chk(
            "Wskaźnik obciążenia rozpiętości motoszybowca m/b²",
            f"≤ {sub['w_b2_max']:.1f} kg/m²",
            f"{wb2:.2f} kg/m²",
            wb2 <= sub["w_b2_max"],
            "EASA CS-22.1(a)"
        ))

    # 8. Ograniczenia dla mikrolota jednoosobowego UL-115 (EASA Annex I pkt 1 lit. e)
    if cat_key == "easa_optout_ul115":
        checks.append(_chk(
            "Masa własna pustego statku (bez paliwa i pilota)",
            "≤ 115.0 kg",
            f"{m_empty:.1f} kg",
            m_empty <= 115.0,
            "UE 2018/1139 Zał. I / t.j. Dz. U. z 2025 r. poz. 1137"
        ))
        rho_f = JETA1_DENSITY_KG_L if engine_type == "jet" else AVGAS_DENSITY_KG_L
        v_fuel = m_fuel / rho_f
        checks.append(_chk(
            "Pojemność instalacji paliwowej",
            "≤ 20.0 l",
            f"{v_fuel:.1f} l",
            v_fuel <= 20.0,
            "UE 2018/1139 Zał. I / t.j. Dz. U. z 2025 r. poz. 1137"
        ))
        if vmax > 0:
            checks.append(_chk(
                "Prędkość maksymalna w locie poziomym na pełnej mocy (CAS)",
                "≤ 102.0 km/h (55 kt)",
                f"{vmax:.1f} km/h",
                vmax <= 102.0,
                "UE 2018/1139 Zał. I / t.j. Dz. U. z 2025 r. poz. 1137"
            ))
        if S > 0:
            wl_empty = m_empty / S
            checks.append(_chk(
                "Obciążenie powierzchni pustego statku",
                "≤ 10.0 kg/m²",
                f"{wl_empty:.2f} kg/m²",
                wl_empty <= 10.0,
                "UE 2018/1139 Zał. I / t.j. Dz. U. z 2025 r. poz. 1137"
            ))

    errors = [c for c in checks if c["severity"] == "error"]
    warnings = [c for c in checks if c["severity"] == "warning"]
    suggested = cat_key if sub["unmanned"] else suggest_subcategory(m0, n_crew, n_pax, False, engine_type, ac_type)
    n_pos, n_neg, n_ref = limit_load_factors(cat_key, m0)


    return {
        "easa_basis": EASA_REF,
        "polish_basis": f"Rozporządzenie Ministra Infrastruktury w sprawie klasyfikacji statków powietrznych ({LAW_REF})",
        "category_key": cat_key,
        "easa_code": sub["easa_code"],
        "easa_spec": sub["easa_spec"],
        "easa_performance_level": perf_lvl,
        "polish_code": sub["polish_code"],
        "class": sub["class_name"],
        "subcategory": sub["name"],
        "code": sub["code"],
        "airworthiness_k": k_cat,
        "airworthiness_k_name": K_CATEGORIES.get(k_cat, k_cat),
        "k_allowed": sub["k_allowed"],
        "design_code": sub["design_code"],
        "unmanned": sub["unmanned"],
        "aerobatic": sub.get("aerobatic", False),
        "load_factors": {"n_pos": n_pos, "n_neg": n_neg, "reference": n_ref},
        "checks": checks,
        "compliant": len(errors) == 0,
        "assessment_scope": "Sprawdzono tylko wybrane warunki modelu dydaktycznego; wynik nie potwierdza zdatności ani certyfikacji.",
        "n_errors": len(errors),
        "n_warnings": len(warnings),
        "suggested_category": suggested,
        "suggested_name": SUBCATEGORIES[suggested]["name"],
        "corrections": list(params.get("_law_corrections", [])),
    }


def catalog_for_frontend() -> dict:
    """Rejestr kategorii i przepisów EASA dla frontendu."""
    out = {}
    for key, s in SUBCATEGORIES.items():
        n_pos, n_neg, ref = limit_load_factors(key, 600.0 if s["class"] != "A" else 1500.0)
        out[key] = {
            "code": s["code"],
            "easa_code": s["easa_code"],
            "polish_code": s["polish_code"],
            "class": s["class"],
            "class_name": s["class_name"],
            "name": s["name"],
            "easa_spec": s["easa_spec"],
            "mtom_min": s.get("mtom_min"),
            "mtom_max": s.get("mtom_max"),
            "k_allowed": s["k_allowed"],
            "unmanned": s["unmanned"],
            "occupants_max": s.get("occupants_max"),
            "pax_min": s.get("pax_min"),
            "pax_max": s.get("pax_max"),
            "crew_min": s.get("crew_min"),
            "crew_max": s.get("crew_max"),
            "design_code": s["design_code"],
            "aircraft_types": AIRCRAFT_TYPE_ALLOWED.get(key, []),
            "n_pos_typ": n_pos,
            "n_neg_typ": n_neg,
            "load_ref": ref,
        }
    return {
        "subcategories": out,
        "k_categories": K_CATEGORIES,
        "aliases": CATEGORY_ALIASES,
        "easa_ref": EASA_REF,
        "legal_basis": LAW_REF,
    }

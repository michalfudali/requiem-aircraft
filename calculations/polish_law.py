"""Klasyfikacja projektowanego statku powietrznego i sprawdzenie wymagań przepisów budowy.

Podstawą są przepisy wybrane w projekcie: JAR-23 (kategorie normalna, użytkowa, akrobacyjna
i transportu lokalnego), JAR-VLA, JAR-22 (szybowce i motoszybowce) i JAR-25 w brzmieniu
„Wyjątków z przepisów” (ZSiS MEiL PW), a dla kategorii spoza wyjątków — CS-LSA, art. 2 ust. 8
rozporządzenia (UE) 2018/1139 i rozporządzenie (UE) 2019/947. Wartości i paragrafy są w
calculations.regulations; tutaj są kategorie, ich granice i sprawdzenia projektu.
Sprawdzenia dotyczą wymagań, które da się ocenić w projekcie wstępnym; nie stanowią
wykazania zgodności w procesie certyfikacji.
"""
import math

from calculations import regulations as R

KT_TO_KMH = 1.852
KMH_TO_KT = 1.0 / 1.852
LB_PER_KG = 2.20462
AVGAS_DENSITY_KG_L = 0.72
JETA1_DENSITY_KG_L = 0.80
# JAR 23.1(a)(1) i (a)(2): granice ciężaru startowego kategorii N/U/A oraz commuter.
JAR23_MTOM_MAX_KG = 5670.0
JAR23_COMMUTER_MTOM_MAX_KG = 8618.0
# JAR 23.45, 23.49(c), 23.65, 23.67, 23.77: próg 2721 kg (6000 lb) dla samolotów tłokowych.
JAR23_LIGHT_PISTON_KG = 2721.0
LAW_REF = "t.j. Dz. U. z 2025 r. poz. 1137"
EASA_REF = "Wyjątki z przepisów JAR-22/23/25/VLA (ZSiS MEiL PW); CS-LSA; UE 2018/1139; UE 2019/947"
TURBINE_TYPES = ("turboprop_regional", "jet_business", "jet_transport")
ENGINE_NAMES = {"prop": "śmigłowy", "jet": "odrzutowy", "none": "bez napędu"}
TYPE_NAMES = {"piston_ga": "samolot tłokowy", "motoglider": "motoszybowiec", "glider": "szybowiec", "uav": "bezzałogowiec",
              "turboprop_regional": "samolot turbośmigłowy", "jet_business": "odrzutowiec dyspozycyjny",
              "jet_transport": "odrzutowiec komunikacyjny"}

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

_JAR23_RULES = dict(scope='jar23.1a1', category='jar23.3', occupant_mass='jar23.25a2', stall='jar23.49c',
                    n_pos='jar23.337a', n_neg='jar23.337b', nu='jar23.303', maneuver='jar23.333b', gust='jar23.333c',
                    gust_formula='jar23.341', vc='jar23.335a', vd='jar23.335b', va='jar23.335c', vb='jar23.335d',
                    flap='jar23.345', flutter='jar23.629')
_JAR22_RULES = dict(scope='jar22.1a1', seats='jar22.1a3', occupant_mass='jar22.25a2', cg_masses='jar22.23b',
                    stall='jar22.49b', n_pos='jar22.337', n_neg='jar22.337', nu='jar22.303', maneuver='jar22.333b',
                    gust='jar22.333c', gust_formula='jar22.341', va='jar22.335a', vf='jar22.335b', vb='jar22.335c',
                    vd='jar22.335f', flap='jar22.345b', flutter='jar22.629')


def _jar23(key, code, polish, label, load_basis, occupant, aerobatic=False, **extra):
    return dict(code=code, easa_code=f"JAR-23 {label}", polish_code=polish, regulation="JAR-23",
                **{"class": "A"}, class_name=f"A. Samolot (JAR-23, kategoria {label})",
                name=extra.pop("name"), easa_spec=f"JAR-23 (wyjątki z przepisów), kategoria {label}",
                mtom_min=None, mtom_max=extra.pop("mtom_max", JAR23_MTOM_MAX_KG), pax_min=0,
                pax_max=extra.pop("pax_max", 9), occupants_max=None, crew_min=1, crew_max=2, unmanned=False,
                load_basis=load_basis, design_code=f"JAR-23, kategoria {label}", k_allowed=["K1", "K2", "K3"],
                occupant_mass_kg=occupant, aerobatic=aerobatic,
                rules={**_JAR23_RULES, **extra.pop("rules", {})}, **extra)


# Rejestr kategorii (klucze są identyfikatorami programu; nazwy i podstawa wg wybranych przepisów).
SUBCATEGORIES = {
    # ------------------------------------------------------------- JAR-23 (JAR 23.1, 23.3)
    "jar23_normal": _jar23("jar23_normal", "JAR23-N", "A3.1", "normalna", "cs23_normal", 77.0,
                           name="JAR-23 kategoria normalna (≤ 9 pasażerów, MTOM ≤ 5670 kg, bez akrobacji)"),
    "jar23_utility": _jar23("jar23_utility", "JAR23-U", "A3.2", "użytkowa", "cs23_utility", 86.0,
                            name="JAR-23 kategoria użytkowa (≤ 9 pasażerów, MTOM ≤ 5670 kg, korkociągi, przechylenie ≤ 90°)"),
    "jar23_aerobatic": _jar23("jar23_aerobatic", "JAR23-A", "A3.3", "akrobacyjna", "cs23_aerobatic", 86.0, aerobatic=True,
                              name="JAR-23 kategoria akrobacyjna (≤ 9 pasażerów, MTOM ≤ 5670 kg, n = +6,0 / −3,0)"),
    "jar23_commuter": _jar23("jar23_commuter", "JAR23-C", "A2", "transportu lokalnego (commuter)", "cs23_commuter", 77.0,
                             name="JAR-23 kategoria transportu lokalnego (dwusilnikowy śmigłowy, ≤ 19 pasażerów, MTOM ≤ 8618 kg)",
                             mtom_max=JAR23_COMMUTER_MTOM_MAX_KG, pax_max=19, engines_exact=2, propeller_only=True,
                             rules=dict(scope='jar23.1a2')),
    # ------------------------------------------------------------- JAR-VLA
    "cs_vla": dict(code="JAR-VLA", easa_code="JAR-VLA", polish_code="A4", regulation="JAR-VLA", **{"class": "A"},
                   class_name="A. Samolot bardzo lekki (JAR-VLA)",
                   name="JAR-VLA (jeden silnik tłokowy, ≤ 2 miejsca, MTOM ≤ 750 kg, VS0 ≤ 45 kt, dzień VFR)",
                   easa_spec="JAR-VLA (wyjątki z przepisów)", mtom_min=None, mtom_max=750.0, occupants_max=2,
                   pax_min=0, pax_max=1, crew_min=1, crew_max=1, vs0_max_kmh=45.0 * KT_TO_KMH, piston_only=True,
                   engines_exact=1, unmanned=False, load_basis="cs_vla", design_code="JAR-VLA",
                   k_allowed=["K1", "K2"], occupant_mass_kg=86.0, aerobatic=False, climb_rate_min_ms=2.0,
                   rules=dict(scope='vla.1', category='vla.3', occupant_mass='vla.25a2', stall='vla.1', climb='vla.65',
                              n_pos='vla.337', n_neg='vla.337', nu='vla.303', maneuver='vla.333b', gust='vla.333c',
                              gust_formula='vla.341', vc='vla.335a', vd='vla.335b', va='vla.335c', flap='vla.345',
                              flutter='vla.629')),
    # ------------------------------------------------------------- CS-LSA (poza wyjątkami)
    "cs_lsa": dict(code="CS-LSA", easa_code="CS-LSA", polish_code="A5", regulation="CS-LSA", **{"class": "A"},
                   class_name="A. Samolot (EASA CS-LSA)",
                   name="EASA CS-LSA (lekki sportowy • MTOM ≤ 600/650 kg, ≤ 2 os., VS0 ≤ 45 kt; poza wyjątkami JAR)",
                   easa_spec="EASA CS-LSA (ASTM F2245)", mtom_min=None, mtom_max=600.0, mtom_max_water=650.0,
                   occupants_max=2, pax_min=0, pax_max=1, crew_min=1, crew_max=1, vs0_max_kmh=45.0 * KT_TO_KMH,
                   piston_only=True, engines_exact=1, unmanned=False, load_basis="cs_lsa",
                   design_code="EASA CS-LSA (ASTM F2245)", k_allowed=["K1", "K2"], occupant_mass_kg=86.0,
                   aerobatic=False, rules=dict(scope='lsa.1', stall='lsa.1', n_pos='lsa.337', n_neg='lsa.337')),
    # ------------------------------------------------------------- JAR-25
    "cs25_transport": dict(code="JAR-25", easa_code="JAR-25", polish_code="A1", regulation="JAR-25", **{"class": "A"},
                           class_name="A. Samolot duży z napędem turbinowym (JAR-25)",
                           name="JAR-25 (duże samoloty z napędem turbinowym)",
                           easa_spec="JAR-25 (wyjątki z przepisów)", mtom_min=None, mtom_max=None, pax_min=0,
                           pax_max=None, occupants_max=None, crew_min=2, crew_max=4, unmanned=False,
                           turbine_only=True, load_basis="cs25", design_code="JAR-25", k_allowed=["K1", "K2", "K3"],
                           occupant_mass_kg=77.0, aerobatic=False,
                           rules=dict(scope='jar25.1', climb='jar25.121', n_pos='jar25.337b', n_neg='jar25.337c',
                                      nu='jar25.303', maneuver='jar25.333b', gust='jar25.341', gust_formula='jar25.341',
                                      vc='jar25.335a', vd='jar25.335b', va='jar25.335c', vf='jar25.335e',
                                      flap='jar25.345', flutter='jar25.629')),
    # ------------------------------------------------------------- JAR-22
    "cs22_glider": dict(code="JAR-22-U", easa_code="JAR-22 szybowiec U", polish_code="S", regulation="JAR-22",
                        **{"class": "S"}, class_name="S. Szybowiec (JAR-22, kategoria U)",
                        name="JAR-22 szybowiec, kategoria użytkowa U (MTOM ≤ 750 kg, ≤ 2 os., bez napędu)",
                        easa_spec="JAR-22 (wyjątki z przepisów), szybowiec kategorii U", mtom_min=None, mtom_max=750.0,
                        occupants_max=2, pax_min=0, pax_max=1, crew_min=1, crew_max=1, unmanned=False,
                        no_engine=True, vs0_max_kmh=80.0, load_basis="cs22_utility", design_code="JAR-22 (szybowce, kat. U)",
                        k_allowed=["K1", "K2"], occupant_mass_kg=110.0, aerobatic=False, rules=dict(_JAR22_RULES)),
    "cs22_aerobatic": dict(code="JAR-22-A", easa_code="JAR-22 szybowiec A", polish_code="S", regulation="JAR-22",
                           **{"class": "S"}, class_name="S. Szybowiec (JAR-22, kategoria A)",
                           name="JAR-22 szybowiec, kategoria akrobacyjna A (MTOM ≤ 750 kg, ≤ 2 os., n = +7 / −5)",
                           easa_spec="JAR-22 (wyjątki z przepisów), szybowiec kategorii A", mtom_min=None, mtom_max=750.0,
                           occupants_max=2, pax_min=0, pax_max=1, crew_min=1, crew_max=1, unmanned=False,
                           no_engine=True, vs0_max_kmh=80.0, load_basis="cs22_aerobatic",
                           design_code="JAR-22 (szybowce, kat. A)", k_allowed=["K1", "K2"], occupant_mass_kg=110.0,
                           aerobatic=True, rules=dict(_JAR22_RULES)),
    "cs22_motoglider": dict(code="JAR-22-P", easa_code="JAR-22 motoszybowiec", polish_code="MG1", regulation="JAR-22",
                            **{"class": "MG"}, class_name="MG. Motoszybowiec (JAR-22)",
                            name="JAR-22 motoszybowiec (jeden silnik tłokowy, MTOM ≤ 850 kg, W/b² ≤ 3 kg/m², ≤ 2 os.)",
                            easa_spec="JAR-22 (wyjątki z przepisów), motoszybowiec", mtom_min=None, mtom_max=850.0,
                            occupants_max=2, pax_min=0, pax_max=1, crew_min=1, crew_max=1, w_b2_max=3.0,
                            piston_only=True, engines_exact=1, vs0_max_kmh=80.0, takeoff_15m_max_m=500.0,
                            climb_rate_min_ms=360.0 / 240.0, unmanned=False, load_basis="cs22_utility",
                            design_code="JAR-22 (motoszybowce)", k_allowed=["K1", "K2"], occupant_mass_kg=110.0,
                            aerobatic=False,
                            rules={**_JAR22_RULES, 'scope': 'jar22.1a2', 'takeoff': 'jar22.51', 'climb': 'jar22.65',
                                   'sink': 'jar22.71'}),
    # ------------------------------------------------------------- UE 2018/1139 (poza wyjątkami)
    "easa_optout_ul": dict(code="UL-A", easa_code="Annex I Opt-out (UL-A)", polish_code="UL-A", regulation="UE 2018/1139",
                           **{"class": "UL"}, class_name="UL. Urządzenie latające (UE 2018/1139 art. 2 ust. 8)",
                           name="UL-A, opt-out art. 2 ust. 8 UE 2018/1139 (MTOM ≤ 600/650 kg, ≤ 2 os., VS0 ≤ 45 kt; poza wyjątkami JAR)",
                           easa_spec="Rozporządzenie (UE) 2018/1139 art. 2 ust. 8 / LTF-UL", mtom_min=None, mtom_max=600.0,
                           mtom_max_water=650.0, occupants_max=2, pax_min=0, pax_max=1, crew_min=1, crew_max=1,
                           vs0_max_kmh=45.0 * KT_TO_KMH, unmanned=False, load_basis="ltf_ul",
                           design_code="LTF-UL / UE 2018/1139 art. 2 ust. 8", k_allowed=["K4", "K6A", "K6E", "K6H", "K6R"],
                           occupant_mass_kg=77.0, aerobatic=False,
                           rules=dict(scope='ul.optout', stall='ul.optout', n_pos='ltf.337', n_neg='ltf.337')),
    "easa_optout_ul115": dict(code="UL-115", easa_code="UL-115", polish_code="UL-115", regulation="UE 2018/1139",
                              **{"class": "UL"}, class_name="UL. Urządzenie latające (UL-115)",
                              name="UL-115 (jednoosobowy mikrolot • masa własna ≤ 115 kg; poza wyjątkami JAR)",
                              easa_spec="Klasyfikacja krajowa UL-115 (t.j. Dz. U. z 2025 r. poz. 1137)", mtom_min=None,
                              mtom_max=None, occupants_max=1, crew_min=1, crew_max=1, pax_min=0, pax_max=0,
                              empty_mass_max=115.0, fuel_volume_max_l=20.0, vmax_kmh=102.0, empty_wing_loading_max=10.0,
                              unmanned=False, load_basis="ltf_ul", design_code="LTF-UL / UL-115", k_allowed=["K5"],
                              occupant_mass_kg=77.0, aerobatic=False,
                              rules=dict(scope='ul.115', n_pos='ltf.337', n_neg='ltf.337')),
    # ------------------------------------------------------------- UAS (poza wyjątkami)
    "easa_uas_specific": dict(code="UAS-Spec", easa_code="UAS Specific", polish_code="UM (odrębna klasyfikacja krajowa)",
                              regulation="UE 2019/947", **{"class": "UM"},
                              class_name="UM. Bezzałogowy statek powietrzny (UE 2019/947, kategoria szczególna)",
                              name="UAS kategoria szczególna (UE 2019/947 art. 5; obciążenia wg STANAG 4671)",
                              easa_spec="UE 2019/947 art. 5 – kategoria operacji Specific", mtom_min=None, mtom_max=None,
                              occupants_max=0, pax_min=0, pax_max=0, crew_min=0, crew_max=0, unmanned=True,
                              load_basis="stanag4671", design_code="STANAG 4671 (USAR); podstawa zdatności wymaga ustalenia",
                              k_allowed=["K1"], occupant_mass_kg=0.0, aerobatic=False,
                              rules=dict(scope='uas.ops', n_pos='stanag.337', n_neg='stanag.337', nu='stanag.303')),
    "easa_uas_certified": dict(code="UAS-Cert", easa_code="UAS Certified", polish_code="UM (odrębna klasyfikacja krajowa)",
                               regulation="UE 2019/947", **{"class": "UM"},
                               class_name="UM. Bezzałogowy statek powietrzny (UE 2019/947, kategoria certyfikowana)",
                               name="UAS kategoria certyfikowana (UE 2019/947 art. 6; obciążenia wg STANAG 4671)",
                               easa_spec="UE 2019/947 art. 6 – kategoria operacji Certified", mtom_min=None, mtom_max=None,
                               occupants_max=0, pax_min=0, pax_max=0, crew_min=0, crew_max=0, unmanned=True,
                               load_basis="stanag4671", design_code="STANAG 4671 (USAR); podstawa zdatności wymaga ustalenia",
                               k_allowed=["K1"], occupant_mass_kg=0.0, aerobatic=False,
                               rules=dict(scope='uas.ops', n_pos='stanag.337', n_neg='stanag.337', nu='stanag.303')),
}

# Grupy wyboru w interfejsie (kolejność jak w wyjątkach z przepisów).
GROUPS = (
    ("JAR-23 — samoloty lekkie (wyjątki z przepisów)", ("jar23_normal", "jar23_utility", "jar23_aerobatic", "jar23_commuter")),
    ("JAR-VLA — samoloty bardzo lekkie", ("cs_vla",)),
    ("JAR-22 — szybowce i motoszybowce", ("cs22_glider", "cs22_aerobatic", "cs22_motoglider")),
    ("JAR-25 — samoloty duże", ("cs25_transport",)),
    ("Poza wyjątkami JAR: CS-LSA i ultralekkie (UE 2018/1139)", ("cs_lsa", "easa_optout_ul", "easa_optout_ul115")),
    ("Bezzałogowe statki powietrzne (UE 2019/947, STANAG 4671)", ("easa_uas_specific", "easa_uas_certified")),
)

# Aliasy: dawne klucze projektów (poziomy CS-23 Amdt 5 i nazwy ogólne) oraz kody krajowe.
CATEGORY_ALIASES = {
    "cs23_level1": "jar23_normal", "cs23_level2": "jar23_normal", "cs23_level3": "jar23_normal",
    "cs23_aerobatic": "jar23_aerobatic", "cs23_commuter": "jar23_commuter",
    "normal": "jar23_normal", "utility": "jar23_utility", "aerobatic": "jar23_aerobatic", "acrobatic": "jar23_aerobatic",
    "commuter": "jar23_commuter", "transport": "cs25_transport", "vla": "cs_vla", "lsa": "cs_lsa",
    "uav": "easa_uas_specific", "jar23": "jar23_normal", "jar25": "cs25_transport", "jar_vla": "cs_vla",
    "jar22": "cs22_glider",
    # Polskie kody t.j. Dz. U. z 2025 r. poz. 1137
    "a1_transport": "cs25_transport", "a2_commuter": "jar23_commuter", "a3_normal": "jar23_normal",
    "a3_utility": "jar23_utility", "a3_aerobatic": "jar23_aerobatic", "a4_vla": "cs_vla", "a5_lsa": "cs_lsa",
    "mg_utility": "cs22_motoglider", "glider": "cs22_glider", "szybowiec": "cs22_glider", "sailplane": "cs22_glider",
    "motoglider": "cs22_motoglider", "motoszybowiec": "cs22_motoglider", "tmg": "cs22_motoglider",
    "cs22": "cs22_motoglider", "s_glider": "cs22_glider", "ul_a": "easa_optout_ul", "ul_mg": "cs22_motoglider",
    "ul_115": "easa_optout_ul115", "um_heavy": "easa_uas_certified", "um_light": "easa_uas_specific",
}

# Klasy konstrukcyjne dopuszczone przez zakres stosowania przepisów kategorii.
AIRCRAFT_TYPE_ALLOWED = {
    "jar23_normal": ["piston_ga", "turboprop_regional", "jet_business"],
    "jar23_utility": ["piston_ga", "turboprop_regional", "jet_business"],
    "jar23_aerobatic": ["piston_ga", "turboprop_regional", "jet_business"],
    "jar23_commuter": ["turboprop_regional", "piston_ga"],
    "cs_vla": ["piston_ga"],
    "cs_lsa": ["piston_ga"],
    "cs25_transport": ["jet_transport", "turboprop_regional", "jet_business"],
    "cs22_glider": ["glider"],
    "cs22_aerobatic": ["glider"],
    "cs22_motoglider": ["motoglider", "piston_ga"],
    "easa_optout_ul": ["piston_ga"],
    "easa_optout_ul115": ["piston_ga"],
    "easa_uas_specific": ["uav"],
    "easa_uas_certified": ["uav"],
}


def resolve_category(category) -> str:
    """Znormalizowany klucz kategorii (dawne klucze i kody krajowe przez aliasy)."""
    cat = str(category or "jar23_normal").strip().lower()
    cat = CATEGORY_ALIASES.get(cat, cat)
    return cat if cat in SUBCATEGORIES else "jar23_normal"


def stored_category(params) -> str:
    """Kategoria JAR zapisanego projektu, presetu lub tematu (dawne poziomy CS-23 Amdt 5 → JAR-23).

    JAR 23.1(a)(2): commuter tylko dla dwusilnikowych samolotów śmigłowych; odrzutowiec z poziomu
    commuter trafia do kategorii normalnej (≤ 9 miejsc) albo JAR-25, a śmigłowy dwusilnikowy powyżej
    9 miejsc do kategorii commuter.
    """
    new = resolve_category(params.get("category"))
    engines = int(params.get("n_engines") or (2 if params.get("engine_location") == "wing"
                                              or params.get("engine_type") == "jet" else 1))
    pax = int(float(params.get("n_pax") or 0))
    jet = params.get("engine_type") == "jet" or params.get("aircraft_type") in ("jet_business", "jet_transport")
    if new == "jar23_commuter" and (jet or engines != 2):
        new = "jar23_normal" if pax <= 9 else "cs25_transport"
    if new == "jar23_normal" and not jet and engines == 2 and (pax > 9 or params.get("category") == "cs23_level3"):
        new = "jar23_commuter"
    return new


def is_jar23(category) -> bool:
    return SUBCATEGORIES[resolve_category(category)]["regulation"] == "JAR-23"


def is_unmanned(params: dict) -> bool:
    """Zwraca True, gdy statek jest bezzałogowy (UAS / 0 osób na pokładzie)."""
    if params.get("aircraft_type") == "uav":
        return True
    return SUBCATEGORIES[resolve_category(params.get("category"))]["unmanned"]


def default_category_for(aircraft_type: str) -> str:
    """Domyślna kategoria przepisów dla wybranej klasy konstrukcyjnej."""
    return {
        "glider": "cs22_glider",
        "motoglider": "cs22_motoglider",
        "uav": "easa_uas_specific",
        "jet_transport": "cs25_transport",
        "turboprop_regional": "jar23_commuter",
        "jet_business": "jar23_normal",
    }.get(aircraft_type, "jar23_normal")


def occupant_mass_minimum(category, seats=1):
    """Najmniejsza masa osoby na miejscu wg przepisów kategorii: (kg, id wymagania) albo (None, None)."""
    sub = SUBCATEGORIES[resolve_category(category)]
    rule_id = sub.get("rules", {}).get("occupant_mass")
    if not rule_id:
        return None, None
    if sub["regulation"] == "JAR-22":
        # JAR 22.25(a)(2): 110 kg dla jednomiejscowego, 180 kg łącznie dla dwumiejscowego.
        return (110.0 if seats <= 1 else 90.0), rule_id
    return float(sub["occupant_mass_kg"]), rule_id


def stall_limit(category, n_engines=1):
    """Górna granica VS0 [km/h CAS] wynikająca z przepisów: (km/h, id wymagania) albo (None, None)."""
    sub = SUBCATEGORIES[resolve_category(category)]
    if sub["regulation"] == "JAR-23":
        # JAR 23.49(c): 61 kt bezwarunkowo dla jednosilnikowych (dwusilnikowe ≤ 2721 kg — zależnie od 23.67(a)(1)).
        return (61.0 * KT_TO_KMH, "jar23.49c") if int(n_engines or 1) == 1 else (None, None)
    if sub.get("vs0_max_kmh"):
        return float(sub["vs0_max_kmh"]), sub["rules"].get("stall")
    return None, None


LIGHT_REGULATIONS = ("JAR-22", "JAR-VLA", "CS-LSA", "UE 2018/1139")
CARGO_HOLD_TYPES = ("turboprop_regional", "jet_transport", "jet_business")


def features(category, aircraft_type="piston_ga", engine_type="prop"):
    """Które elementy projektu istnieją w danej kategorii przepisów i klasie płatowca.

    Szybowiec nie ma napędu, paliwa, bagażu ani ładunku; statki do dwóch miejsc (JAR-22, JAR-VLA,
    CS-LSA, UL) nie przewożą ładunku handlowego; ładownię ma tylko płatowiec transportowy
    (turbośmigłowy, odrzutowy) kategorii JAR-23/JAR-25; bezzałogowiec przewozi wyposażenie zadaniowe.
    """
    sub = SUBCATEGORIES[resolve_category(category)]
    unmanned = sub["unmanned"] or aircraft_type == "uav"
    powered = engine_type != "none" and not sub.get("no_engine") and aircraft_type != "glider"
    light = sub["regulation"] in LIGHT_REGULATIONS
    cargo = unmanned or not light
    return {
        "powered": powered,
        "fuel": powered,
        "passengers": not unmanned and (sub.get("pax_max") is None or sub["pax_max"] > 0),
        "baggage": not unmanned and powered,
        "cargo": cargo,
        "cargo_label": "wyposażenie zadaniowe" if unmanned else "ładunek handlowy",
        "cargo_bay": cargo and not unmanned and aircraft_type in CARGO_HOLD_TYPES,
        "payload_drop": cargo,
        "payload_total_mode": cargo,
        "water": sub["regulation"] != "JAR-22",
        "parachute": sub["regulation"] == "JAR-22",
    }


def _apply_features(p, notes):
    """Usuwa dane, których kategoria i klasa płatowca nie mają (np. ładownię szybowca)."""
    f = features(p.get("category"), p.get("aircraft_type", "piston_ga"), p.get("engine_type", "prop"))
    what = SUBCATEGORIES[resolve_category(p.get("category"))]["easa_code"]

    def drop(keys, reason, value=0):
        present = [k for k in keys if p.get(k) not in (None, 0, 0.0, "", value)]
        for key in keys:
            if key in p:
                p[key] = value
        if present:
            notes.append(f"{what}: {reason} — pominięto {', '.join(present)}.")

    if not f["cargo"]:
        drop(("m_cargo",), "statek nie przewozi ładunku handlowego")
        drop(("payload_drop_kg",), "brak ładunku do zrzutu")
        if p.get("payload_input_mode") == "total":
            p["payload_input_mode"] = "seats"
        p["locked_params"] = [k for k in p.get("locked_params") or [] if k not in ("m_payload", "m_cargo")]
    if not f["cargo_bay"]:
        drop(("cargo_bay_length_m", "cargo_bay_width_m", "cargo_bay_height_m", "cargo_hold_density_kg_m3"),
             "płatowiec tej klasy nie ma ładowni")
    if not f["baggage"]:
        drop(("m_bag",), "szybowiec nie przewozi bagażu")
    if not f["water"] and p.get("operating_surface") == "water":
        p["operating_surface"] = "land"
        notes.append(f"{what}: przepisy nie obejmują operacji z wody — przyjęto pas lądowy.")
    return f


def normalize_occupants(params: dict):
    """
    Dostosowuje dane projektu do wymagań wybranych przepisów:
      - 0 osób na pokładzie dla UAS;
      - minimalna załoga (2 pilotów w JAR-25 — założenie programu);
      - masa osoby nie mniejsza niż wymagana przepisami (JAR 23.25(a)(2), JAR-VLA 25(a)(2), JAR 22.25(a)(2));
      - wymagana prędkość przeciągnięcia nie większa niż granica przepisów (JAR 23.49(c), JAR-VLA 1, JAR 22.49(b)).
    Liczby pasażerów nie zmienia: przekroczenie limitu miejsc ma być widoczne w ocenie zgodności.
    """
    p = dict(params)
    notes = []
    ac_type = p.get("aircraft_type", "piston_ga")
    cat_key = resolve_category(p.get("category"))

    # Spójność klasy płatowca z kategorią bezzałogową, szybowcową i motoszybowcową
    if ac_type == "uav" and not SUBCATEGORIES[cat_key]["unmanned"]:
        notes.append("Typ UAV wymaga kategorii UAS (UE 2019/947) – wybrano 'easa_uas_specific'.")
        cat_key = "easa_uas_specific"
        p["_um_auto"] = True
    elif SUBCATEGORIES[cat_key]["unmanned"] and ac_type != "uav":
        notes.append("Wybrano kategorię bezzałogową UAS – typ statku ustawiono na UAV.")
        ac_type = "uav"
    elif ac_type == "glider":
        if cat_key not in ("cs22_glider", "cs22_aerobatic"):
            cat_key = "cs22_glider"
            notes.append(f"Typ Szybowiec przypisano do kategorii JAR-22 szybowiec U ({R.cite('jar22.1a1')}).")
        p["engine_type"] = "none"
    elif ac_type == "motoglider":
        if cat_key not in ("cs22_motoglider", "easa_optout_ul"):
            cat_key = "cs22_motoglider"
            notes.append(f"Typ Motoszybowiec przypisano do kategorii JAR-22 motoszybowiec ({R.cite('jar22.1a2')}).")
        if p.get("engine_type") in ("none", "jet"):
            p["engine_type"] = "prop"

    p["aircraft_type"] = ac_type
    p["category"] = cat_key
    sub = SUBCATEGORIES[cat_key]

    n_crew = int(float(p.get("n_crew", 1) or 0))
    n_pax = int(float(p.get("n_pax", 0) or 0))

    if sub["unmanned"]:
        if n_crew or n_pax:
            notes.append(f"UAS (UE 2019/947): bezzałogowiec – usunięto {n_crew} os. załogi "
                         f"i {n_pax} pasażerów. Na pokładzie 0 osób (sterowanie z GCS).")
        n_crew, n_pax = 0, 0
        p["m_pax"] = 0.0
        if "m_cargo" not in p:
            p["m_cargo"] = 80.0
            notes.append("UAV bez ładunku – przyjęto domyślnie 80 kg wyposażenia zadaniowego (sensory, łącze C2).")
    else:
        crew_min = sub.get("crew_min", 1)
        if n_crew < crew_min and not p.get("_crew_fixed"):
            basis = (f"{sub['easa_code']}: minimalna załoga 2 pilotów (założenie programu; JAR 25.1523 poza wyjątkami)"
                     if sub["regulation"] == "JAR-25" else f"{sub['easa_code']}: wymagany co najmniej {crew_min} pilot")
            notes.append(f"{basis} – skorygowano.")
            n_crew = crew_min
        # Masa osób przyjmowana do ciężaru maksymalnego nie może być mniejsza niż w przepisach.
        minimum, rule_id = occupant_mass_minimum(cat_key, n_crew + n_pax)
        if minimum:
            for key, who, present in (("m_crew_person", "członka załogi", True), ("m_pax", "pasażera", n_pax > 0)):
                value = float(p.get(key, 90.0 if key == "m_crew_person" else 80.0) or 0.0)
                if present and value < minimum:
                    p[key] = minimum
                    notes.append(f"Masę {who} podniesiono z {value:g} kg do {minimum:g} kg wg {R.cite(rule_id)}.")
        elif sub["class"] == "UL":
            m_crew_person = float(p.get("m_crew_person", 90.0) or 90.0)
            if m_crew_person < 77.0:
                p["m_crew_person"] = 77.0
                notes.append("Masa obliczeniowa pilota UL podniesiona do min. 77 kg.")

    # Wymagana VS0 nie może przekraczać granicy przepisów kategorii.
    limit, rule_id = stall_limit(cat_key, p.get("n_engines", 1))
    if limit and float(p.get("v_stall_kmh", 0) or 0) > limit + 1e-9:
        notes.append(f"Wymaganą prędkość przeciągnięcia VS0 obniżono z {float(p['v_stall_kmh']):g} km/h "
                     f"do {limit:.1f} km/h ({limit * KMH_TO_KT:.0f} kt) wg {R.cite(rule_id)}.")
        p["v_stall_kmh"] = round(limit, 1)

    p["n_crew"] = n_crew
    p["n_pax"] = n_pax
    _apply_features(p, notes)
    return p, notes


def load_factor_rules(category):
    """Identyfikatory wymagań dodatniego i ujemnego współczynnika obciążenia manewrowego."""
    rules = SUBCATEGORIES[resolve_category(category)].get("rules", {})
    return rules.get("n_pos"), rules.get("n_neg")


def limit_load_factors(category, m0: float):
    """Dopuszczalne współczynniki obciążeń manewrowych n+ i n− wg przepisów kategorii."""
    sub = SUBCATEGORIES[resolve_category(category)]
    basis = sub["load_basis"]
    w_lb = max(1.0, m0) * LB_PER_KG
    n_formula = 2.1 + 24000.0 / (w_lb + 10000.0)
    pos, neg = load_factor_rules(category)

    if basis == "cs25":
        n_pos, n_neg = min(3.8, max(2.5, n_formula)), -1.0
        ref = (f"{R.cite(pos)}: n+ = 2,1 + 24000/(W + 10000), nie mniej niż 2,5 i nie więcej niż 3,8; "
               f"{R.cite(neg)}: n− = −1,0 do VC")
    elif basis in ("cs23_normal", "cs23_commuter"):
        n_pos = min(3.8, n_formula)
        n_neg = -0.4 * n_pos
        ref = f"{R.cite(pos)}(1): n+ = 2,1 + 24000/(W + 10000), nie więcej niż 3,8; {R.cite(neg)}(1): n− = −0,4·n+"
    elif basis == "cs23_utility":
        n_pos, n_neg = 4.4, -0.4 * 4.4
        ref = f"{R.cite(pos)}(2): n+ = 4,4 (kategoria użytkowa); {R.cite(neg)}(1): n− = −0,4·n+ = −1,76"
    elif basis == "cs23_aerobatic":
        n_pos, n_neg = 6.0, -0.5 * 6.0
        ref = f"{R.cite(pos)}(3): n+ = 6,0 (kategoria akrobacyjna); {R.cite(neg)}(2): n− = −0,5·n+ = −3,0"
    elif basis == "cs_vla":
        n_pos, n_neg = 3.8, -1.5
        ref = f"{R.cite(pos)}: n+ ≥ 3,8; n− ≤ −1,5"
    elif basis == "cs_lsa":
        n_pos, n_neg = 4.0, -2.0
        ref = f"{R.cite(pos)}: n+ ≥ 4,0; n− ≤ −2,0"
    elif basis == "cs22_utility":
        n_pos, n_neg = 5.3, -2.65
        ref = f"{R.cite(pos)}: kategoria U — n1 = +5,3, n2 = +4,0, n3 = −1,5, n4 = −2,65"
    elif basis == "cs22_aerobatic":
        n_pos, n_neg = 7.0, -5.0
        ref = f"{R.cite(pos)}: kategoria A — n1 = n2 = +7,0, n3 = n4 = −5,0"
    elif basis == "ltf_ul":
        n_pos, n_neg = 4.0, -2.0
        ref = f"{R.cite(pos)}: n+ = +4,0; n− = −2,0"
    elif basis == "stanag4671":
        w_kg = max(1.0, m0)
        n_pos = min(3.8, 2.1 + 10900.0 / (w_kg + 4536.0))
        n_neg = -0.4 * n_pos
        ref = f"{R.cite(pos)}: n+ = 2,1 + 10900/(W + 4536) ≤ 3,8; n− = −0,4·n+"
    else:  # pragma: no cover - każda kategoria ma podstawę obciążeń
        raise ValueError(f"Brak podstawy obciążeń dla kategorii {category}.")

    return round(n_pos, 2), round(n_neg, 2), ref


def envelope_speed_family(category) -> str:
    """Rodzina reguł prędkości VC/VD: JAR 23.335 (N/C, U, A), JAR-VLA 335, JAR 25.335."""
    basis = SUBCATEGORIES[resolve_category(category)]["load_basis"]
    if basis == "cs23_aerobatic":
        return "aerobatic"
    if basis in ("cs23_utility", "cs22_utility"):
        return "utility"
    if basis == "cs25":
        return "transport"
    if basis == "cs_vla":
        return "vla"
    return "normal"


def _twin_propeller(params):
    return int(params.get("n_engines", 1) or 1) == 2 and params.get("engine_type", "prop") == "prop"


def suggest_subcategory(m0: float, n_crew: int, n_pax: int, unmanned: bool, engine_type: str,
                        ac_type: str = "piston_ga", n_engines: int = 1) -> str:
    """Kategoria przepisów, której zakres stosowania obejmuje projekt o danej masie i liczbie miejsc."""
    if unmanned:
        return "easa_uas_specific"
    if ac_type == "glider" or engine_type == "none":
        return "cs22_glider"
    if ac_type == "motoglider":
        return "cs22_motoglider"
    twin_prop = int(n_engines or 1) == 2 and engine_type == "prop"
    if m0 <= JAR23_MTOM_MAX_KG and n_pax <= 9:
        if (n_crew + n_pax) <= 2 and engine_type == "prop" and ac_type == "piston_ga" and int(n_engines or 1) == 1 \
                and m0 <= 750.0:
            return "cs_vla"
        return "jar23_normal"
    if twin_prop and m0 <= JAR23_COMMUTER_MTOM_MAX_KG and n_pax <= 19:
        return "jar23_commuter"
    return "cs25_transport"


def scope_category(params: dict, m0: float):
    """Kategoria wymagana zakresem stosowania JAR 23.1, gdy projekt wykracza poza przydzieloną; inaczej None."""
    cat = resolve_category(params.get("category"))
    if not is_jar23(cat):
        return None
    n_pax = int(float(params.get("n_pax", 0) or 0))
    sub = SUBCATEGORIES[cat]
    commuter_ok = _twin_propeller(params) and m0 <= JAR23_COMMUTER_MTOM_MAX_KG and n_pax <= 19
    if cat == "jar23_commuter":
        if commuter_ok:
            return None
        return "jar23_normal" if (m0 <= JAR23_MTOM_MAX_KG and n_pax <= 9) else "cs25_transport"
    if m0 <= sub["mtom_max"] and n_pax <= sub["pax_max"]:
        return None
    return "jar23_commuter" if commuter_ok else "cs25_transport"


def _chk(name, limit, value, ok, rule_id=None, severity="error", source=None, note=""):
    found = R.rule(rule_id) if rule_id else None
    return {
        "name": name,
        "limit": limit,
        "value": value,
        "ok": bool(ok),
        "severity": "ok" if ok else severity,
        "source": source or (R.reference(rule_id) if rule_id else "Założenie programu"),
        "rule": rule_id,
        "paragraph": found["paragraph"] if found else None,
        "url": found["document"]["url"] if found else None,
        "note": note,
    }


def _value(name, value, unit, rule_id, note=""):
    found = R.rule(rule_id)
    return {"name": name, "value": value, "unit": unit, "rule": rule_id, "paragraph": found["paragraph"],
            "requirement": found["text"], "document": found["document"]["title"], "url": found["document"]["url"],
            "note": note}


def regulation_values(params, mass_res, envelope_res=None):
    """Wartości projektu przyjęte z przepisów (do tabeli „wartości z przepisów” raportu)."""
    cat = resolve_category(params.get("category"))
    sub = SUBCATEGORIES[cat]
    rules = sub.get("rules", {})
    out = []
    seats = int(mass_res.get("n_crew", params.get("n_crew", 1)) or 0) + int(mass_res.get("n_pax", params.get("n_pax", 0)) or 0)
    minimum, rule_id = occupant_mass_minimum(cat, seats)
    if minimum and not sub["unmanned"]:
        out.append(_value("Najmniejsza masa osoby na miejscu do ciężaru maksymalnego", minimum, "kg", rule_id,
                          "z osobą i spadochronem" if sub["regulation"] == "JAR-22" else ""))
    limit, rule_id = stall_limit(cat, params.get("n_engines", 1))
    if limit:
        out.append(_value("Największa prędkość przeciągnięcia VS0 przy ciężarze maksymalnym", round(limit, 1), "km/h", rule_id,
                          f"{limit * KMH_TO_KT:.0f} kt CAS"))
    climb = climb_requirement(params, mass_res.get("m0", 0.0))
    if climb:
        out.append(_value(climb["label"], climb["value"], climb["unit"], climb["rule"]))
    if sub.get("w_b2_max"):
        out.append(_value("Największy iloraz ciężaru i kwadratu rozpiętości W/b²", sub["w_b2_max"], "kg/m²", rules["scope"]))
    if sub.get("takeoff_15m_max_m"):
        out.append(_value("Największa długość startu do wysokości 15 m", sub["takeoff_15m_max_m"], "m", rules["takeoff"]))
    if envelope_res:
        lim = envelope_res["limits"]
        pos, neg = load_factor_rules(cat)
        out.append(_value("Dodatni współczynnik obciążenia manewrowego n+", lim["n_max"], "—", pos))
        out.append(_value("Ujemny współczynnik obciążenia manewrowego n−", lim["n_min"], "—", neg))
        if rules.get("nu"):
            out.append(_value("Współczynnik bezpieczeństwa ν", lim["safety_factor_nu"], "—", rules["nu"]))
        gf = envelope_res["gust_factors"]
        if rules.get("gust"):
            for gust in gf["gusts"]:
                out.append(_value(f"Prędkość podmuchu obliczeniowego przy {gust['speed']}", gust["u_ms"], "m/s", rules["gust"]))
        flap = envelope_res.get("flap") or {}
        if flap.get("applicable") and rules.get("flap"):
            out.append(_value("Współczynnik obciążenia manewrowego z wychyloną mechanizacją", flap["n_flap"], "—", rules["flap"]))
            out.append(_value("Prędkość podmuchu z wychyloną mechanizacją", flap["u_flap_ms"], "m/s", rules["flap"]))
        if rules.get("flutter"):
            out.append(_value("Zakres prędkości analizy flatteru", 1.2, "× VD", rules["flutter"]))
    return out


def climb_requirement(params, m0):
    """Wymaganie wznoszenia przy wszystkich silnikach pracujących, jeśli przepisy je podają."""
    cat = resolve_category(params.get("category"))
    sub = SUBCATEGORIES[cat]
    if params.get("engine_type") == "none":
        return None
    piston = params.get("aircraft_type", "piston_ga") not in TURBINE_TYPES
    if sub["regulation"] == "JAR-23" and cat != "jar23_commuter":
        if piston and m0 <= JAR23_LIGHT_PISTON_KG:
            water = params.get("operating_surface") == "water"
            return dict(kind="gradient", value=6.7 if water else 8.3, unit="%", rule="jar23.65a",
                        label="Najmniejszy gradient ustalonego wznoszenia na poziomie morza "
                              + ("(wodnosamolot)" if water else "(samolot lądowy)"))
        return dict(kind="gradient", value=4.0, unit="%", rule="jar23.65b",
                    label="Najmniejszy gradient ustalonego wznoszenia po starcie")
    if sub.get("climb_rate_min_ms"):
        return dict(kind="rate", value=round(sub["climb_rate_min_ms"], 2), unit="m/s", rule=sub["rules"]["climb"],
                    label="Najmniejsza ustalona prędkość wznoszenia" if cat == "cs_vla"
                    else "Najmniejsza średnia prędkość wznoszenia do 360 m (360 m w 4 min)")
    return None


def check_compliance(params: dict, mass_res: dict, geom_res: dict = None, perf_res: dict = None,
                     envelope_res: dict = None) -> dict:
    """Sprawdzenie wymagań przepisów wybranej kategorii, które można ocenić w projekcie wstępnym."""
    cat_key = resolve_category(params.get("category"))
    sub = SUBCATEGORIES[cat_key]
    rules = sub.get("rules", {})
    ac_type = params.get("aircraft_type", "piston_ga")
    engine_type = params.get("engine_type", "prop")
    n_engines = int(params.get("n_engines", 1) or 1) if engine_type != "none" else 0
    k_cat = str(params.get("airworthiness_k") or sub["k_allowed"][0]).upper()
    seaplane = bool(params.get("seaplane", False)) or params.get("operating_surface") == "water"

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
    scope = rules.get("scope")

    checks = []
    allowed_types = AIRCRAFT_TYPE_ALLOWED.get(cat_key, [])
    checks.append(_chk("Klasa konstrukcyjna objęta zakresem stosowania przepisów",
                       ", ".join(TYPE_NAMES.get(t, t) for t in allowed_types), TYPE_NAMES.get(ac_type, ac_type),
                       ac_type in allowed_types, scope, "warning"))

    mtom_max = sub.get("mtom_max_water") if (seaplane and sub.get("mtom_max_water")) else sub.get("mtom_max")
    if mtom_max is not None:
        checks.append(_chk("Maksymalna masa startowa MTOM", f"≤ {mtom_max:.0f} kg", f"{m0:.1f} kg", m0 <= mtom_max, scope))

    if sub["unmanned"]:
        checks.append(_chk("Osoby na pokładzie (UAS)", "0 os. (pilot w GCS)", f"{occupants} os.", occupants == 0, scope))
    else:
        crew_min = sub.get("crew_min", 1)
        checks.append(_chk("Minimalna załoga lotnicza", f"≥ {crew_min} os.", f"{n_crew} os.", n_crew >= crew_min, None,
                           "warning" if params.get("topic_origin") == "official" else "error",
                           source=("Założenie programu: 2 pilotów (minimalna załoga ustalana w certyfikacji, "
                                   "JAR 25.1523 poza wyjątkami)") if sub["regulation"] == "JAR-25"
                           else "Założenie programu: co najmniej jeden pilot"))
        if sub.get("pax_max") is not None:
            checks.append(_chk("Liczba miejsc oprócz miejsc pilotów", f"≤ {sub['pax_max']}", f"{n_pax}",
                               n_pax <= sub["pax_max"], scope))
        if sub.get("occupants_max") is not None:
            checks.append(_chk("Liczba osób na pokładzie", f"≤ {sub['occupants_max']} os.", f"{occupants} os.",
                               occupants <= sub["occupants_max"], rules.get("seats", scope)))
        minimum, rule_id = occupant_mass_minimum(cat_key, occupants)
        if minimum:
            crew_mass = float(params.get("m_crew_person", 0) or 0)
            checks.append(_chk("Masa członka załogi przyjęta do ciężaru maksymalnego", f"≥ {minimum:g} kg",
                               f"{crew_mass:g} kg", crew_mass >= minimum - 1e-9, rule_id))
            if n_pax:
                pax_mass = float(params.get("m_pax", 0) or 0)
                checks.append(_chk("Masa pasażera przyjęta do ciężaru maksymalnego", f"≥ {minimum:g} kg",
                                   f"{pax_mass:g} kg", pax_mass >= minimum - 1e-9, rule_id))

    # Napęd w zakresie stosowania przepisów.
    if sub.get("no_engine"):
        checks.append(_chk("Układ napędowy: szybowiec bez silnika", "bez napędu",
                           "bez napędu" if engine_type == "none" else engine_type, engine_type == "none", scope))
    if sub.get("engines_exact"):
        exact = sub["engines_exact"]
        kind = "śmigłowe" if sub.get("propeller_only") else ("tłokowy" if sub.get("piston_only") else "")
        checks.append(_chk("Liczba silników", f"{exact} {kind}".strip(), f"{n_engines}", n_engines == exact, scope))
    if sub.get("propeller_only"):
        checks.append(_chk("Rodzaj napędu: śmigłowy", "śmigło", ENGINE_NAMES.get(engine_type, engine_type), engine_type == "prop", scope))
    if sub.get("piston_only"):
        checks.append(_chk("Rodzaj silnika: tłokowy (zapłon iskrowy lub samoczynny) ze śmigłem", "tłokowy",
                           f"{ENGINE_NAMES.get(engine_type, engine_type)} ({TYPE_NAMES.get(ac_type, ac_type)})",
                           engine_type == "prop" and ac_type in ("piston_ga", "motoglider"), scope))
    if sub.get("turbine_only"):
        checks.append(_chk("Rodzaj napędu: turbinowy", "turbinowy (odrzutowy lub turbośmigłowy)", TYPE_NAMES.get(ac_type, ac_type),
                           ac_type in TURBINE_TYPES, scope))

    # Prędkość przeciągnięcia w konfiguracji do lądowania przy ciężarze maksymalnym.
    limit, rule_id = stall_limit(cat_key, n_engines)
    if limit:
        checks.append(_chk("Prędkość przeciągnięcia VS0 przy ciężarze maksymalnym",
                           f"≤ {limit:.1f} km/h ({limit * KMH_TO_KT:.0f} kt)",
                           f"{vs0:.1f} km/h ({vs0 * KMH_TO_KT:.1f} kt)", vs0 <= limit + 0.1, rule_id))
    elif sub["regulation"] == "JAR-23" and n_engines == 2 and ac_type not in TURBINE_TYPES \
            and m0 <= JAR23_LIGHT_PISTON_KG and vs0 > 61.0 * KT_TO_KMH:
        checks.append(_chk("VS0 > 61 kt: wymagany gradient wznoszenia z jednym silnikiem ≥ 1,5 % na 5000 ft",
                           "do wykazania", f"VS0 = {vs0:.1f} km/h", False, "jar23.67a1", "warning"))

    # Wznoszenie przy wszystkich silnikach pracujących (ocena w konfiguracji gładkiej, poziom morza).
    climb = climb_requirement(params, m0)
    climb_data = (perf_res or {}).get("climb", {})
    if climb and climb_data.get("wy_max_ms") is not None:
        rate = float(climb_data["wy_max_ms"])
        if climb["kind"] == "gradient":
            speed = float(climb_data.get("v_wy_max_kmh") or 0) / 3.6
            gradient = 100.0 * rate / speed if speed > 0 else 0.0
            checks.append(_chk(climb["label"], f"≥ {climb['value']:g} %", f"{gradient:.1f} %",
                               gradient >= climb["value"], climb["rule"],
                               note="Gradient wy,max/V przy prędkości najlepszego wznoszenia, konfiguracja gładka, poziom morza; "
                                    "wymaganie dotyczy klap w położeniu do startu."))
        else:
            checks.append(_chk(climb["label"], f"≥ {climb['value']:g} m/s", f"{rate:.2f} m/s", rate >= climb["value"],
                               climb["rule"], note="Największa prędkość wznoszenia na poziomie morza."))
    if sub["regulation"] == "JAR-25" and n_engines >= 2:
        required = {2: 2.4, 3: 2.7}.get(n_engines, 3.0)
        checks.append(_chk("Gradient wznoszenia z jednym silnikiem niepracującym (drugi odcinek startu)",
                           f"≥ {required:g} %", "nie wyznaczono w projekcie wstępnym", False, "jar25.121", "warning"))

    # Motoszybowiec: W/b², start, opadanie.
    if sub.get("w_b2_max") and b > 0:
        wb2 = m0 / (b * b)
        checks.append(_chk("Iloraz ciężaru i kwadratu rozpiętości W/b²", f"≤ {sub['w_b2_max']:.1f} kg/m²",
                           f"{wb2:.2f} kg/m²", wb2 <= sub["w_b2_max"], scope))
    if sub.get("takeoff_15m_max_m") and engine_type != "none":
        # JAR 22.25(a)(2): ciężar maksymalny motoszybowca obejmuje paliwo na 0,5 h przy mocy maksymalnej ciągłej.
        power_kw = float(params.get("engine_power_kw") or 0)
        needed_fuel = .5 * power_kw * float(params.get("sfc") or 0) / 1000
        if needed_fuel > 0:
            checks.append(_chk("Paliwo na 0,5 h lotu przy mocy maksymalnej ciągłej", f"≥ {needed_fuel:.1f} kg", f"{m_fuel:.1f} kg",
                               m_fuel >= needed_fuel, rules.get("occupant_mass")))
    if sub.get("takeoff_15m_max_m"):
        distance = ((perf_res or {}).get("takeoff") or {}).get("distance_to_15m")
        if distance is not None:
            checks.append(_chk("Długość startu do wysokości 15 m", f"≤ {sub['takeoff_15m_max_m']:g} m", f"{distance:g} m",
                               distance <= sub["takeoff_15m_max_m"], rules["takeoff"]))
    if rules.get("sink"):
        glide = (perf_res or {}).get("glide") or {}
        sink = (glide.get("minimum_sink") or {}).get("sink_ms")
        if sink is not None and glide.get("rho"):
            # JAR 22.45: osiągi na poziomie morza; opadanie skaluje się jak 1/√ρ.
            sink_sl = float(sink) * math.sqrt(float(glide["rho"]) / 1.225)
            required = 1.0 if occupants <= 1 else 1.2
            checks.append(_chk("Najmniejsza prędkość opadania z mocą zdławioną", f"≤ {required:g} m/s", f"{sink_sl:.2f} m/s",
                               sink_sl <= required, rules["sink"], note="Przeliczona na poziom morza z biegunowej szybowania."))

    # UL-115 (klasyfikacja krajowa).
    if cat_key == "easa_optout_ul115":
        checks.append(_chk("Masa własna pustego statku (bez paliwa i pilota)", "≤ 115.0 kg", f"{m_empty:.1f} kg",
                           m_empty <= 115.0, scope))
        rho_f = JETA1_DENSITY_KG_L if engine_type == "jet" else AVGAS_DENSITY_KG_L
        v_fuel = m_fuel / rho_f
        checks.append(_chk("Pojemność instalacji paliwowej", "≤ 20.0 l", f"{v_fuel:.1f} l", v_fuel <= 20.0, scope))
        if vmax > 0:
            checks.append(_chk("Prędkość maksymalna w locie poziomym na pełnej mocy (CAS)", "≤ 102.0 km/h (55 kt)",
                               f"{vmax:.1f} km/h", vmax <= 102.0, scope))
        if S > 0:
            wl_empty = m_empty / S
            checks.append(_chk("Obciążenie powierzchni pustego statku", "≤ 10.0 kg/m²", f"{wl_empty:.2f} kg/m²",
                               wl_empty <= 10.0, scope))
    if sub["unmanned"]:
        checks.append(_chk("Kategoria operacji UAS wymaga odrębnej oceny ryzyka", "Ocena operacji wg UE 2019/947 art. 5–6",
                           "Wybrano wariant roboczy; MTOM nie wyznacza kategorii operacji", False, scope, "warning"))

    errors = [c for c in checks if c["severity"] == "error"]
    warnings = [c for c in checks if c["severity"] == "warning"]
    suggested = cat_key if sub["unmanned"] else (scope_category(params, m0) or (
        cat_key if not errors else suggest_subcategory(m0, n_crew, n_pax, False, engine_type, ac_type, n_engines)))
    n_pos, n_neg, n_ref = limit_load_factors(cat_key, m0)

    return {
        "easa_basis": EASA_REF,
        "polish_basis": f"Rozporządzenie Ministra Infrastruktury w sprawie klasyfikacji statków powietrznych ({LAW_REF})",
        "course_page": R.COURSE_PAGE,
        "regulation": sub["regulation"],
        "scope_rule": scope,
        "scope_text": R.RULES[scope]["text"] if scope else None,
        "category_key": cat_key,
        "easa_code": sub["easa_code"],
        "easa_spec": sub["easa_spec"],
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
        "regulation_values": regulation_values(params, mass_res, envelope_res),
        "compliant": len(errors) == 0,
        "assessment_scope": "Sprawdzono wymagania przepisów, które można ocenić w projekcie wstępnym; wynik nie "
                            "stanowi wykazania zgodności w procesie certyfikacji.",
        "n_errors": len(errors),
        "n_warnings": len(warnings),
        "suggested_category": suggested,
        "suggested_name": SUBCATEGORIES[suggested]["name"],
        "corrections": list(params.get("_law_corrections", [])),
    }


def ui_limits(key):
    """Ograniczenia pól kreatora i formularza wynikające z przepisów kategorii (z odwołaniem)."""
    sub = SUBCATEGORIES[key]
    rules = sub.get("rules", {})
    scope = rules.get("scope")
    out = {}

    def add(param, rule_id, **bounds):
        out[param] = {**bounds, "rule": rule_id, "paragraph": R.cite(rule_id) if rule_id else None,
                      "url": R.rule(rule_id)["document"]["url"] if rule_id else None}

    if sub["unmanned"]:
        add("n_crew", scope, max=0, min=0, text="bez osób na pokładzie")
        add("n_pax", scope, max=0, min=0, text="bez osób na pokładzie")
        return out
    if sub.get("pax_max") is not None:
        text = (f"≤ {sub['pax_max']} miejsc oprócz pilotów" if sub["regulation"] == "JAR-23"
                else f"≤ {sub['occupants_max'] or sub['pax_max'] + 1} osoby na pokładzie")
        add("n_pax", rules.get("seats", scope), max=sub["pax_max"], text=text)
    crew_min, crew_max = sub.get("crew_min", 1), sub.get("crew_max", 2)
    # Liczbę pilotów ogranicza przepis tylko w statkach do dwóch osób; w pozostałych to założenie programu.
    seats_rule = rules.get("seats", scope) if sub.get("occupants_max") is not None else None
    add("n_crew", seats_rule, min=crew_min, max=crew_max,
        text=("co najmniej 2 pilotów" if sub["regulation"] == "JAR-25" else
              f"{crew_min} pilot" if crew_min == crew_max == 1 else f"{crew_min}–{crew_max} pilotów"))
    minimum, rule_id = occupant_mass_minimum(key, 1)
    if minimum:
        text = (f"≥ {minimum:g} kg z osobą i spadochronem (jednomiejscowy), 180 kg łącznie (dwumiejscowy)"
                if sub["regulation"] == "JAR-22" else f"≥ {minimum:g} kg na osobę")
        add("m_crew_person", rule_id, min=minimum, text=text)
        add("m_pax", rule_id, min=occupant_mass_minimum(key, 2)[0], text=text)
        if sub["regulation"] == "JAR-22":
            # The same seat-count policy must reach both the solver and the UI.
            for param in ("m_crew_person", "m_pax"):
                out[param]["min_by_occupants"] = {
                    str(seats): occupant_mass_minimum(key, seats)[0] for seats in (1, 2)
                }
    limit, rule_id = stall_limit(key, 1)
    if limit:
        add("v_stall_kmh", rule_id, max=round(limit, 1),
            text=f"VS0 ≤ {limit:.1f} km/h ({limit * KMH_TO_KT:.0f} kt)"
                 + (" dla samolotu jednosilnikowego" if sub["regulation"] == "JAR-23" else ""),
            single_engine_only=sub["regulation"] == "JAR-23")
    if sub.get("engines_exact"):
        add("n_engines", scope, min=sub["engines_exact"], max=sub["engines_exact"],
            text=f"{sub['engines_exact']} silnik{'i' if sub['engines_exact'] > 1 else ''}")
    if sub.get("no_engine"):
        add("engine_type", scope, allowed=["none"], text="szybowiec bez napędu")
    elif sub.get("propeller_only") or sub.get("piston_only"):
        add("engine_type", scope, allowed=["prop"], text="napęd śmigłowy" + (" z silnikiem tłokowym" if sub.get("piston_only") else ""))
    elif sub.get("turbine_only"):
        add("engine_type", scope, allowed=["prop", "jet"], text="napęd turbinowy (turbośmigłowy lub odrzutowy)")
    if sub.get("climb_rate_min_ms"):
        add("climb_rate_ms", rules["climb"], min=round(sub["climb_rate_min_ms"], 2),
            text=f"wznoszenie ≥ {sub['climb_rate_min_ms']:.2g} m/s")
    if sub.get("takeoff_15m_max_m"):
        add("takeoff_distance_m", rules["takeoff"], max=sub["takeoff_15m_max_m"],
            text=f"start do 15 m ≤ {sub['takeoff_15m_max_m']:g} m")
    return out


def catalog_for_frontend() -> dict:
    """Rejestr kategorii i przepisów dla interfejsu (wybór, limity pól, odwołania)."""
    out = {}
    for key, s in SUBCATEGORIES.items():
        n_pos, n_neg, ref = limit_load_factors(key, 600.0 if s["class"] != "A" else 1500.0)
        scope = s.get("rules", {}).get("scope")
        out[key] = {
            "code": s["code"], "easa_code": s["easa_code"], "polish_code": s["polish_code"], "class": s["class"],
            "class_name": s["class_name"], "name": s["name"], "easa_spec": s["easa_spec"],
            "regulation": s["regulation"], "mtom_min": s.get("mtom_min"), "mtom_max": s.get("mtom_max"),
            "k_allowed": s["k_allowed"], "unmanned": s["unmanned"], "occupants_max": s.get("occupants_max"),
            "pax_min": s.get("pax_min"), "pax_max": s.get("pax_max"), "crew_min": s.get("crew_min"),
            "crew_max": s.get("crew_max"), "design_code": s["design_code"],
            "aircraft_types": AIRCRAFT_TYPE_ALLOWED.get(key, []), "n_pos_typ": n_pos, "n_neg_typ": n_neg,
            "load_ref": ref, "scope_paragraph": R.cite(scope) if scope else None,
            "scope_text": R.RULES[scope]["text"] if scope else None,
            "scope_url": R.rule(scope)["document"]["url"] if scope else None,
            "limits": ui_limits(key),
            "features": {ac: features(key, ac, "none" if ac == "glider" else "prop") for ac in AIRCRAFT_TYPE_ALLOWED.get(key, [])},
        }
    return {
        "subcategories": out,
        "defaults": {ac: default_category_for(ac) for ac in
                     ("piston_ga", "turboprop_regional", "jet_business", "jet_transport", "glider", "motoglider", "uav")},
        "groups": [{"label": label, "keys": list(keys)} for label, keys in GROUPS],
        "k_categories": K_CATEGORIES,
        "aliases": CATEGORY_ALIASES,
        "easa_ref": EASA_REF,
        "legal_basis": LAW_REF,
        "course_page": R.COURSE_PAGE,
    }

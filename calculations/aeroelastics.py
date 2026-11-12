"""Preliminary uniform-wing aeroelastic screening; never a compliance demonstration.

The isotropic box and quasi-steady typical section omit damping, unsteady airloads,
laminate coupling, controls and spanwise distributions. EI/GJ inputs may replace
the box estimate, but do not remove those limitations.
"""
import math

from calculations.atmosphere import RHO0


SECTION_INPUTS = {
    'wing_bending_stiffness_nm2': (1e-6, 1e15),
    'wing_torsional_stiffness_nm2': (1e-6, 1e15),
    'wing_mass_per_length_kg_m': (1e-6, 1e6),
    'wing_elastic_axis_ratio': (0, 1),
    'wing_section_cg_ratio': (0, 1),
    'wing_radius_gyration_ratio': (1e-6, 10),
}
MATERIALS = {
    'metallic': (72e9, 27e9, 'Stop aluminium — model zastępczy'),
    'composite': (60e9, 25e9, 'Kompozyt — izotropowy model zastępczy'),
    'wood': (10e9, 1.2e9, 'Drewno — model zastępczy'),
    'steel': (200e9, 77e9, 'Stal — model zastępczy'),
}
ALIASES = {'metal': 'metallic', 'aluminum': 'metallic', 'carbon': 'composite',
           'composites': 'composite', 'advanced_composites': 'composite'}


def validate_aeroelastic_inputs(params):
    """Validate declared equivalent section data, including a positive mass matrix."""
    mode = params.get('aeroelastic_input_mode', 'estimated')
    if mode not in ('estimated', 'documented'):
        raise ValueError('Aeroelastyczność: nieznany sposób określenia danych.')
    if params.get('wing_structure_material', 'auto') not in ('auto', *MATERIALS):
        raise ValueError('Aeroelastyczność: nieznany materiał skrzydła.')
    # Inactive values are retained as a draft but cannot affect the estimate.
    if mode == 'estimated':
        return
    for key, (low, high) in SECTION_INPUTS.items():
        value = params.get(key)
        try:
            number = float(value)
        except (ValueError, TypeError):
            raise ValueError(f'Aeroelastyczność: podaj {key}.') from None
        if isinstance(value, bool) or not math.isfinite(number) or not low <= number <= high:
            raise ValueError(f'Aeroelastyczność: nieprawidłowa wartość {key}.')
        params[key] = number
    for key in ('aeroelastic_data_source', 'aeroelastic_data_conditions'):
        value = params.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 4000:
            raise ValueError('Aeroelastyczność: podaj źródło danych i opis konfiguracji (do 4000 znaków).')
    # r_alpha is measured about EA and normalized by HALF chord. Positive inertia
    # about CG requires I_EA/m > (x_CG-x_EA)^2, not just a positive I_EA.
    offset = 2 * abs(params['wing_section_cg_ratio'] - params['wing_elastic_axis_ratio'])
    if params['wing_radius_gyration_ratio'] <= offset:
        raise ValueError('Aeroelastyczność: promień bezwładności względem osi sprężystej musi '
                         'być większy niż 2·|x_CG/c − x_EA/c| (dodatnia macierz mas).')


def _material(params):
    explicit = params.get('wing_structure_material', 'auto')
    technology = ALIASES.get(params.get('technology'), params.get('technology'))
    legacy = params.get('structure_material', params.get('structural_material'))
    if explicit != 'auto':
        value, source = explicit, 'wing_structure_material'
    elif technology in ('metallic', 'composite'):
        value, source = technology, 'technology'
    elif legacy:
        value, source = ALIASES.get(legacy, legacy), 'structure_material / structural_material'
    else:
        value, source = 'metallic', 'założenie materiału skrzydła'
    if value not in MATERIALS:
        raise ValueError('Aeroelastyczność: nieznany materiał skrzydła.')
    notes = []
    if technology in ('wood', 'steel_tube') and explicit == 'auto':
        notes.append('Technologia kadłuba nie określa materiału skrzydła; wybierz go osobno.')
    if legacy and ALIASES.get(legacy, legacy) != value:
        notes.append('Pominięto sprzeczny starszy parametr materiału; zastosowano ' + source + '.')
    return value, source, notes


def comparison_basis(params):
    """Scope-specific comparison, rather than a universal claim of 1.20 VD."""
    from calculations.polish_law import SUBCATEGORIES, resolve_category
    category = SUBCATEGORIES[resolve_category(params.get('category', 'jar23_normal'))]
    rule = category.get('rules', {}).get('flutter')
    source22 = ('https://www.easa.europa.eu/sites/default/files/dfu/'
                'CS-22%20Amendment%201.pdf')
    if rule == 'jar22.629':
        return dict(factor=1.2, rule=rule, label='CS 22.629(b)(1)(i): zakres analizy do 1,20 VD',
                    source_url=source22,
                    note='CS 22.629(a): brak niestateczności do co najmniej VD; '
                         'zakres analizy do 1,20 VD nie zastępuje oceny tłumienia, badań drgań i prób w locie.')
    if rule == 'jar25.629':
        return dict(factor=1.15, rule=rule, label='CS 25.629(b)(1): przekrój obwiedni 1,15 VD EAS',
                    source_url='https://www.easa.europa.eu/sites/default/files/dfu/CS-25%20Consolidated%20version.pdf',
                    note='Porównanie w jednym punkcie EAS; wymaganie obejmuje całą obwiednię VD/MD '
                         'powiększoną o 15% EAS przy stałych M i wysokości, konfiguracje i przypadki uszkodzeń.')
    if rule in ('jar23.629', 'vla.629'):
        return dict(factor=1.2, rule=rule, label='Zakres analizy racjonalnej: 1,20 VD',
                    source_url=('https://www.easa.europa.eu/sites/default/files/dfu/'
                                'Easy%20Access%20Rules%20CS-VLA%20%28Amendment%201%29.pdf') if rule == 'vla.629' else
                               'https://www.meil.pw.edu.pl/zsis/ZSiS/Dydaktyka/Prowadzone-przedmioty/WTLK/Wyjatki-z-przepisow',
                    note='Metoda analizy racjonalnej według wybranej podstawy dydaktycznej JAR/CS; '
                         'ten model nie jest wykazaniem zgodności ani pełną analizą racjonalną.')
    return dict(factor=1.2, rule=None, label='Przyjęty cel porównawczy: 1,20 VD', source_url=None,
                note='Brak wyznaczonego w aplikacji wymagania aeroelastycznego dla tej kategorii; '
                     '1,20 VD jest założeniem porównania, a nie wymaganiem jej przepisów.')


def estimate_aeroelastics(geom, aero, mass, envelope, params=None):
    params = dict(params or {})
    validate_aeroelastic_inputs(params)
    wing = geom.get('wing', {})
    b, mac = float(wing.get('b', 10)), float(wing.get('mac', 1.4))
    tc, sweep = float(wing.get('tc_ratio', .12)), float(wing.get('sweep_deg', 0))
    vd = float(envelope.get('speeds', {}).get('v_d_kmh') or 0)
    vd_assumed = vd <= 0
    if vd_assumed:
        vd = 1.25 * float(envelope.get('speeds', {}).get('v_c_kmh') or 250)
    a = float(aero.get('a_w_rad', 4.8))
    mw = float(mass.get('breakdown', {}).get('m_wing', .12 * mass.get('m0', 1000)))
    for name, value in (('rozpiętość', b), ('cięciwa', mac), ('grubość względna', tc),
                        ('masa skrzydła', mw), ('gradient siły nośnej', a), ('VD', vd)):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f'Aeroelastyczność: {name} musi być dodatnia i skończona.')
    material, mat_source, notes = _material(params)
    E, G, mat_label = MATERIALS[material]
    t = max(.0008, .0012 * math.sqrt(mw / 150))
    area, perimeter = .6 * mac * tc * mac, 2 * (.6 * mac + tc * mac)
    gj = G * 4 * area**2 * t / perimeter
    ei = E * 2 * (.6 * mac) * t * (.9 * tc * mac / 2)**2
    mode = params.get('aeroelastic_input_mode', 'estimated')
    mline, xea, xcg, radius = mw / b, .4, .45, .5
    if mode == 'documented':
        ei, gj, mline, xea, xcg, radius = [params[key] for key in SECTION_INPUTS]
    limitations = [
        'Model belki o stałych parametrach i przekroju typowego 2DOF; pomija rozkłady po rozpiętości, '
        'aerodynamikę niestacjonarną, tłumienie, układ sterowania oraz drgania usterzenia i zabudowy napędu.',
        'Rewers lotek nie został obliczony: potrzebne są pochodne aerodynamiczne lotki, jej położenie '
        'i rozkład sztywności skrzydła. Stała proporcja prędkości dywergencji nie wyznacza rewersu.',
    ]
    if mode == 'estimated':
        limitations.append('EI i GJ z założonego cienkościennego kesonu, E i G z umownych wartości materiału; '
                           'masa równomierna, oś sprężysta 40% c, środek masy 45% c, r/(c/2)=0,50.')
    else:
        limitations.append('Zadeklarowana masa liniowa dotyczy tego modelu aeroelastycznego; '
                           'nie zastępuje analizy masowej P3 ani jej domknięcia.')
    if material in ('composite', 'wood'):
        limitations.append('Model nie uwzględnia anizotropii ani sprzężenia giętno-skrętnego; '
                           'dla laminatu potrzebne są układ warstw, macierze sztywności i analiza konstrukcji.')
    if vd_assumed:
        limitations.append('Brak VD w obwiedni: przyjęto 1,25 VC do porównania.')
    limitations.extend(notes)
    length, e = b / 2, (xea - .25) * mac
    qdiv = math.pi**2 * gj / (4 * e * mac * a * length**2) if e > 0 else math.inf
    # Qualitative sweep correction, not a coupled swept-wing structural solution.
    if sweep > 0:
        qdiv *= 1 + 1.8 * math.sin(math.radians(sweep))
    elif sweep < 0:
        qdiv /= 1 + 2 * math.sin(math.radians(abs(sweep))) * length / mac
    if sweep:
        limitations.append('Wpływ skosu jest jedynie poprawką jakościową; brak rozwiązania sprzężonego skrzydła skośnego.')
    vdiv = math.sqrt(2 * qdiv / RHO0) * 3.6
    section = typical_section_flutter(mline, mac, gj, ei, length, a, xea, xcg, radius)
    vf = section['v_flutter_ms'] * 3.6
    basis = comparison_basis(params)
    target = basis['factor'] * vd
    finite = math.isfinite(vf)
    flutter_comparison = vf >= target if finite else None
    divergence_comparison = vdiv >= target if math.isfinite(vdiv) else None
    return dict(
        status='success', assessment_scope='preliminary', certification_compliant=None,
        material=mat_label, material_key=material, material_source=mat_source,
        input_basis=dict(mode=mode, source=params.get('aeroelastic_data_source') if mode == 'documented' else None,
                         conditions=params.get('aeroelastic_data_conditions') if mode == 'documented' else None,
                         wing_mass_per_length_kg_m=mline, skin_thickness_m=t if mode == 'estimated' else None),
        limitations=limitations, comparison_basis=basis, dive_speed_vd_kmh=round(vd, 1),
        divergence_speed_kmh=round(vdiv, 1) if math.isfinite(vdiv) else None,
        aileron_reversal_speed_kmh=None, reversal_safe=None, margin_reversal=None,
        flutter_speed_kmh=round(vf, 1) if finite else None,
        required_flutter_speed_kmh=round(target, 1),
        margin_flutter=round(vf/vd, 2) if finite else None,
        margin_divergence=round(vdiv/vd, 2) if math.isfinite(vdiv) else None,
        # Compatibility keys denote numerical comparison only, never certification.
        flutter_safe=flutter_comparison, divergence_safe=divergence_comparison,
        flutter_comparison_passed=flutter_comparison, divergence_comparison_passed=divergence_comparison,
        torsional_stiffness_gj=gj, bending_stiffness_ei=ei,
        bending_frequency_hz=round(section['omega_h']/(2*math.pi), 2),
        torsion_frequency_hz=round(section['omega_alpha']/(2*math.pi), 2),
        flutter_model=dict(method='Przekrój typowy 2DOF, aerodynamika quasi-stacjonarna; zbiegnięcie częstości.',
                           mass_ratio_mu=round(section['mu'], 2), elastic_axis_chord=xea, section_cg_chord=xcg,
                           radius_of_gyration=radius, coalescence=finite,
                           coalescence_beyond_divergence=finite and vf > vdiv),
        explanation=dict(flutter='Flatter to samowzbudne drgania konstrukcji. Model nie oblicza tłumienia; '
                                 'brak zbiegnięcia częstości nie dowodzi braku flatteru. ' + basis['note'],
                         reversal=limitations[1], divergence='Rozbieżność skrętna z teorii pasowej prostego '
                         'skrzydła wspornikowego: q_D = π²GJ/(4e·c·a·l²), e = (x_EA/c − 0,25)c. '
                         'Dla osi przed lub na 25% c model nie wyznacza dodatniej prędkości dywergencji.'))


def typical_section_flutter(m_line, chord, GJ, EI, l_semi, lift_slope,
                            x_ea=.40, x_cg=.45, r_alpha=.50, rho=RHO0):
    """Quasi-steady 2DOF frequency coalescence, not a damping calculation.

    det[[kh-mω², L-Sαω²], [-Sαω², kα-Le-Iαω²]]=0, L=qca.
    Only coalescence at positive ω² and a positive-definite mass matrix qualifies.
    r_alpha is about EA, normalized by HALF chord.
    """
    for value in (m_line, chord, GJ, EI, l_semi, lift_slope, rho, r_alpha):
        if not math.isfinite(value) or value <= 0:
            raise ValueError('Przekrój typowy: wymagane dodatnie, skończone parametry.')
    if not all(math.isfinite(x) and 0 <= x <= 1 for x in (x_ea, x_cg)):
        raise ValueError('Przekrój typowy: położenia osi i środka masy muszą należeć do [0, 1] c.')
    if r_alpha <= 2 * abs(x_cg-x_ea):
        raise ValueError('Przekrój typowy: macierz mas nie jest dodatnio określona.')
    bs = chord / 2
    ia, sa = m_line * (r_alpha*bs)**2, m_line * (x_cg-x_ea) * chord
    wh = 1.875**2 * math.sqrt(EI/(m_line*l_semi**4))
    wa = math.pi/(2*l_semi) * math.sqrt(GJ/ia)
    kh, ka, e = m_line*wh**2, ia*wa**2, (x_ea-.25)*chord
    A = m_line*ia - sa**2
    B0, B1 = -(m_line*ka + ia*kh), m_line*e + sa
    C0, C1 = kh*ka, -kh*e
    qa, qb, qc = B1**2, 2*B0*B1 - 4*A*C1, B0**2 - 4*A*C0
    disc = 16*A*kh*sa*(ka*(m_line*e+sa) - kh*e*(ia+sa*e))  # factored: exactly zero when Sα=0
    roots = []
    if qa > 0 and disc > 64 * math.ulp(1.0) * max(qb**2, abs(4*qa*qc)):
        root = -.5 * (qb + math.copysign(math.sqrt(disc), qb))
        roots = [root/qa, qc/root] if root else []
    elif qa == 0 and qb < 0:
        roots = [-qc/qb]
    lifts = [x for x in roots if x > 0 and -(B0+B1*x)/(2*A) > 0]
    vf = math.sqrt(2*min(lifts)/(rho*chord*lift_slope)) if lifts else math.inf
    return dict(v_flutter_ms=vf, omega_h=wh, omega_alpha=wa,
                mu=m_line/(math.pi*rho*bs**2), matrices=(m_line, ia, sa, kh, ka, e))

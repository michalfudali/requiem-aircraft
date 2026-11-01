"""ML1 P2: measured polars, Reynolds correction, finite-wing conversion and slopes."""
import math

from calculations.atmosphere import G0, RHO0
from .geometry import SOURCE_URL
from .numerics import pairs, interpolate, linear_fit, bracketed_root
from .validation import finite, finite_result

NU0 = 1.4607e-5
MATERIAL_TECH_FACTORS = {'metal_composite': .15, 'wood_fabric_mixed': .50}
P3_SOURCE_URL = 'https://www.meil.pw.edu.pl/zm/content/download/23966/126688/file/Projekt%203.pdf'


def assemble_tunnel_polar(lift_rows,drag_rows,*,allow_critical_extrapolation=False):
    """P2 II-3 explicitly permits completing missing CD near critical endpoints.

    Keep the measured lift curve and interpolate CD against CL. Extrapolation
    requires an explicit choice and every extrapolated row is marked.
    """
    if not isinstance(lift_rows,list) or not 3<=len(lift_rows)<=1000:
        raise ValueError('Podaj 3–1000 punktów zmierzonej charakterystyki Cz(α).')
    drag=pairs([(finite(r.get('cl'),'Cz oporu'),finite(r.get('cd'),'Cx pomiaru',positive=True)) for r in drag_rows])
    rows=[]
    for row in lift_rows:
        cl=finite(row.get('cl'),'Cz siły nośnej')
        extrapolated=not drag[0][0]<=cl<=drag[-1][0]
        cd=interpolate(drag,cl,extrapolate=allow_critical_extrapolation)
        finite(cd,'Cx uzupełniony przy kącie krytycznym',positive=True)
        rows.append(dict(cl=cl,cd=cd,alpha_deg=finite(row.get('alpha_deg'),'Kąt natarcia'),
                         cd_extrapolated=extrapolated))
    validated=normalize_polar(rows)
    flags={r['cl']:r['cd_extrapolated'] for r in rows}
    return dict(method='ml1.p2.tunnel_data_assembly',source_url=SOURCE_URL,
                rows=[dict(r,cd_extrapolated=flags[r['cl']]) for r in validated],
                extrapolation_basis='linear_endpoint_segments_explicit_opt_in',
                extrapolated_count=sum(flags.values()))


def select_reynolds_data(datasets, mass_kg, area_m2, mac_m, measured_stall_speed_ms=None,*,finite_wing_data=False):
    """P2 §2.1: estimate VS1 from the lowest-Re dataset if no measurement exists."""
    minimum=1 if finite_wing_data else 3
    if not isinstance(datasets, list) or not minimum <= len(datasets) <= 20:
        raise ValueError('Standardowy profil ML1 wymaga charakterystyk dla co najmniej trzech różnych Re.')
    curves = []
    for curve in datasets:
        if not isinstance(curve, dict):
            raise ValueError('Zestaw tunelowy musi zawierać re i rows.')
        curves.append(dict(re=finite(curve.get('re'),'Re badania tunelowego',positive=True),
                           rows=normalize_polar(curve.get('rows'))))
    curves.sort(key=lambda row: row['re'])
    if len({c['re'] for c in curves}) != len(curves):
        raise ValueError('Liczby Reynoldsa zestawów tunelowych muszą być różne.')
    mass = finite(mass_kg,'Masa obliczeniowa',positive=True)
    area = finite(area_m2,'Powierzchnia nośna',positive=True)
    mac = finite(mac_m,'Średnia cięciwa aerodynamiczna',positive=True)
    speed = (math.sqrt(2*mass*G0/(RHO0*area*curves[0]['rows'][-1]['cl']))
             if measured_stall_speed_ms is None else finite(measured_stall_speed_ms,'Zmierzona VS1',positive=True))
    re = speed*mac/NU0
    selected = min(curves,key=lambda row:abs(row['re']-re))
    finite_result(speed,re)
    return dict(method='ml1.p2.reynolds_selection', source='ML1 Projekt 2, (2.6), (2.6a), §2.1', source_url=SOURCE_URL,
                stall_speed_ms=speed, stall_speed_source='estimate_lowest_re' if measured_stall_speed_ms is None else 'measured',
                reynolds_stall=re, stall_estimate_dataset_re=curves[0]['re'], selected=selected,
                dataset_count=len(curves),has_three_reynolds_datasets=len(curves)>=3,
                data_basis='finite_wing_tunnel_exception' if finite_wing_data else 'section_three_reynolds')


def sample_lift_coefficients(cl_max):
    """The nonuniform positive-CL sampling recommended in ML1 Table 2.0."""
    maximum = finite(cl_max,'Cz maksymalny',positive=True)
    bands = [(maximum,.8*maximum,.1),(.8*maximum,.6,.2),(.6,.3,.1),(.3,.1,.05),(.1,0.,.02)]
    values = {0.,maximum}
    for high, low, step in bands:
        high = min(maximum, high)
        if high < low or low > maximum:
            continue
        values.add(high);values.add(low)
        index = 1
        while high-index*step > low+1e-12:
            values.add(high-index*step);index+=1
    ordered = sorted(values,reverse=True)
    unique = []
    for value in ordered:
        if not unique or abs(value-unique[-1])>1e-12*maximum:
            unique.append(value)
    return unique


def normalize_polar(rows):
    if not isinstance(rows, list) or not 3 <= len(rows) <= 1000:
        raise ValueError('Charakterystyka tunelowa: podaj od 3 do 1000 wierszy cl, cd, alpha_deg.')
    data = []
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f'Wiersz tunelowy {i}: wymagane cl, cd, alpha_deg.')
        data.append(dict(cl=finite(row.get('cl'), f'Cz tunelowy {i}'),
                         cd=finite(row.get('cd'), f'Cx tunelowy {i}', positive=True),
                         alpha_deg=finite(row.get('alpha_deg'), f'Kąt natarcia {i}')))
    data.sort(key=lambda row: row['cl'])
    if any(a['cl'] == b['cl'] for a, b in zip(data, data[1:])):
        raise ValueError('Dane tunelowe muszą mieć różne wartości Cz; wybierz gałąź przed przeciągnięciem.')
    if not data[0]['cl'] < 0 < data[-1]['cl']:
        raise ValueError('Dane tunelowe muszą obejmować ujemną i dodatnią wartość krytyczną Cz.')
    if any(a['alpha_deg'] >= b['alpha_deg'] for a, b in zip(data, data[1:])):
        raise ValueError('W zakresie danych tunelowych Cz musi rosnąć z kątem natarcia.')
    return data


def fit_lift_slope(rows, alpha_min_deg=None, alpha_max_deg=None):
    data = normalize_polar(rows)
    low = .8*data[0]['alpha_deg'] if alpha_min_deg is None else finite(alpha_min_deg, 'Dolny kąt aproksymacji')
    high = .8*data[-1]['alpha_deg'] if alpha_max_deg is None else finite(alpha_max_deg, 'Górny kąt aproksymacji')
    selected = [(r['alpha_deg'], r['cl']) for r in data if low <= r['alpha_deg'] <= high]
    result = linear_fit(selected)
    if result['slope'] <= 0:
        raise ValueError('Wybrany liniowy zakres charakterystyki musi mieć dodatnią pochodną dCz/dα.')
    return dict(method='ml1.p2.lift_slope_fit', source='ML1 Projekt 2, II-3, uwaga 1', source_url=SOURCE_URL,
                **result, alpha_min_deg=low, alpha_max_deg=high,
                a_per_deg=result['slope'], a_per_rad=result['slope']*180/math.pi,
                alpha_zero_lift_deg=-result['intercept']/result['slope'])


def compare_wing_slope(rows, theoretical_a_rad, alpha_min_deg=None, alpha_max_deg=None):
    fitted = fit_lift_slope(rows,alpha_min_deg,alpha_max_deg)
    theory = finite(theoretical_a_rad,'Pochodna płata z (2.27)',positive=True)
    difference = 100*(fitted['a_per_rad']-theory)/theory
    return dict(method='ml1.p2.wing_slope_check',source='ML1 Projekt 2, (2.27), II-10',source_url=SOURCE_URL,
                fitted=fitted,theoretical_a_rad=theory,relative_difference_pct=difference,
                within_ten_percent=abs(difference)<=10)


def glauert_coefficients(aspect_ratio, taper_ratio, a_inf_rad, sweep_quarter_deg=0., *, elliptical=False):
    ar = finite(aspect_ratio, 'Wydłużenie', positive=True)
    taper = finite(taper_ratio, 'Zbieżność', nonnegative=True)
    slope = finite(a_inf_rad, 'Pochodna profilu 1/rad', positive=True)
    sweep = finite(sweep_quarter_deg, 'Skos linii ćwiartek cięciw')
    if elliptical:
        if sweep != 0:
            raise ValueError('Zerowe poprawki Glauerta dotyczą niezwichrzonej elipsy bez skosu.')
        return dict(tau=0., delta=0., terms=dict(ideal_ellipse=True), within_typical_range=True,
                    source='ML1 Projekt 2, II-7: płat eliptyczny', source_url=SOURCE_URL)
    u = ar/slope
    tau1 = .023*u**3-.103*u**2+.25*u
    tau2 = -.18*taper**5+1.52*taper**4-3.51*taper**3+3.5*taper**2-1.33*taper+.17
    delta1 = .0537*u-.005
    delta2 = -.43*taper**5+1.83*taper**4-3.06*taper**3+2.56*taper**2-taper+.148
    delta3 = (-2.2e-7*ar**3+1e-7*ar**2+1.6e-5)*sweep**3+1
    tau = tau1*tau2/.17
    delta = delta1*delta2*delta3/.048
    finite_result(tau, delta)
    if min(tau, delta) < 0:
        raise ValueError('Dane leżą poza zakresem dodatnich poprawek wielomianowych Glauerta; użyj danych z obliczeń płata.')
    return dict(tau=tau, delta=delta, within_typical_range=max(tau,delta) <= .2,
                terms=dict(u=u,tau1=tau1,tau2=tau2,delta1=delta1,delta2=delta2,delta3=delta3),
                source='ML1 Projekt 2, (2.14)–(2.20)', source_url=SOURCE_URL)


def reynolds_drag_correction(cl, cd, cl_critical_positive, cl_critical_negative,
                             cd_min_reference, re_from, re_to=1e7):
    cl = finite(cl, 'Cz')
    cd = finite(cd, 'Cx', positive=True)
    positive = finite(cl_critical_positive, 'Cz krytyczny dodatni', positive=True)
    negative = finite(cl_critical_negative, 'Cz krytyczny ujemny')
    if negative >= 0 or not negative <= cl <= positive:
        raise ValueError('Cz musi należeć do zakresu pomiędzy ujemnym i dodatnim punktem krytycznym.')
    reference_cd = finite(cd_min_reference, 'Cx minimalny źródłowy', positive=True)
    re1 = finite(re_from, 'Re źródłowe', positive=True)
    re2 = finite(re_to, 'Re docelowe', positive=True)
    corrected_min = reference_cd*(re1/re2)**.11
    # Each branch reaches its own critical endpoint, where the correction is zero.
    critical = positive if cl >= 0 else abs(negative)
    delta = (corrected_min-reference_cd)*(1-abs(cl)/critical)
    corrected = cd+delta
    finite(corrected, 'Cx po korekcie Reynoldsa', positive=True)
    return dict(cd=corrected, delta_cd=delta, cd_min_corrected=corrected_min,
                re_from=re1, re_to=re2, critical_branch_cl=critical)


def wing_from_section(rows, aspect_ratio, taper_ratio, *, a_inf_rad=None, sweep_quarter_deg=0.,
                      re_from=3e6, re_to=1e7, material='metal_composite', elliptical=False):
    data = normalize_polar(rows)
    slope_fit = fit_lift_slope(data) if a_inf_rad is None else None
    a_inf = slope_fit['a_per_rad'] if slope_fit else finite(a_inf_rad, 'Pochodna profilu 1/rad', positive=True)
    corrections = glauert_coefficients(aspect_ratio,taper_ratio,a_inf,sweep_quarter_deg,elliptical=elliptical)
    if material not in MATERIAL_TECH_FACTORS:
        raise ValueError('Nieznany rodzaj oporu technicznego: wybierz metal_composite lub wood_fabric_mixed.')
    cd_min = min(row['cd'] for row in data)
    corrected_min = cd_min*(finite(re_from,'Re źródłowe',positive=True)/finite(re_to,'Re docelowe',positive=True))**.11
    technical = MATERIAL_TECH_FACTORS[material]*corrected_min
    ar = finite(aspect_ratio,'Wydłużenie',positive=True)
    out = []
    for row in data:
        cl = row['cl']
        re = reynolds_drag_correction(cl,row['cd'],data[-1]['cl'],data[0]['cl'],cd_min,re_from,re_to)
        induced_alpha = cl*(1+corrections['tau'])/(math.pi*ar)
        induced_cd = cl*cl*(1+corrections['delta'])/(math.pi*ar)
        out.append(dict(cl=cl, alpha_section_deg=row['alpha_deg'], cd_section=row['cd'],
                        cd_reynolds=re['cd'], delta_cd_reynolds=re['delta_cd'],
                        alpha_induced_rad=induced_alpha,
                        alpha_wing_deg=row['alpha_deg']+math.degrees(induced_alpha),
                        cd_induced=induced_cd, cd_technical=technical,
                        cd_wing=re['cd']+technical+induced_cd))
    gradient = a_inf/(1+a_inf*(1+corrections['tau'])/(math.pi*ar))
    return dict(method='ml1.p2.section_to_wing', source='ML1 Projekt 2, (2.7)–(2.20), (2.27)',
                source_url=SOURCE_URL, rows=out, corrections=corrections,
                a_inf_rad=a_inf, a_wing_rad=gradient, a_inf_fit=slope_fit,
                cd_min_corrected=corrected_min, cd_technical=technical, material=material,
                note='Cz zachowuje wartości danych tunelowych; metoda P2 pomija niewielką zmianę wartości krytycznych od wydłużenia.')


def infer_section_slope(a_wing_rad, aspect_ratio, taper_ratio=1., sweep_quarter_deg=0.,*,elliptical=False):
    measured = finite(a_wing_rad,'Pochodna płata 1/rad',positive=True)
    ar = finite(aspect_ratio,'Wydłużenie płata badanego',positive=True)
    if elliptical:
        if sweep_quarter_deg!=0:raise ValueError('Zerowe poprawki elipsy dotyczą płata bez skosu.')
        denominator=1-measured/(math.pi*ar)
        if denominator<=0:raise ValueError('Pochodna płata przekracza asymptotę modelu eliptycznego.')
        return measured/denominator
    def residual(a_inf):
        correction = glauert_coefficients(ar,taper_ratio,a_inf,sweep_quarter_deg)
        return a_inf/(1+a_inf*(1+correction['tau'])/(math.pi*ar))-measured
    low = measured
    # The lifting-line inverse has a physical upper asymptote; failure is explicit.
    high = max(2*measured, 2*math.pi)
    for _ in range(12):
        try:
            if residual(high) >= 0:
                return bracketed_root(residual,low,high)
        except ValueError:
            break
        high *= 1.5
    raise ValueError('Nie można odtworzyć dodatniej pochodnej profilu z danych płata i poprawek Glauerta.')


def fit_parabolic_polar(rows, aspect_ratio, *, cl_fit_min=0., cl_fit_max=None):
    """ML1 P3 §3.6: least squares CD = CD0 + k CL², with an explicit fit interval."""
    if not isinstance(rows,list) or len(rows)<3:
        raise ValueError('Aproksymacja biegunowej wymaga co najmniej trzech punktów cl, cd.')
    points = [(finite(row.get('cl'),'Cz biegunowej'),finite(row.get('cd'),'Cx biegunowej',positive=True)) for row in rows]
    ar = finite(aspect_ratio,'Wydłużenie geometryczne',positive=True)
    low = finite(cl_fit_min,'Dolna granica Cz aproksymacji')
    high = .85*max(cl for cl,_ in points) if cl_fit_max is None else finite(cl_fit_max,'Górna granica Cz aproksymacji')
    if low >= high:
        raise ValueError('Zakres aproksymacji biegunowej musi mieć rosnące granice.')
    selected = [(cl*cl,cd) for cl,cd in points if low<=cl<=high]
    fit = linear_fit(selected)
    cd0, k = fit['intercept'], fit['slope']
    if cd0<=0 or k<=0:
        raise ValueError('Aproksymacja nie daje dodatniej biegunowej CD0 + k Cz²; sprawdź dane i zakres.')
    effective_ar = 1/(math.pi*k)
    oswald = effective_ar/ar
    cd_min = min(cd for _,cd in points)
    return dict(method='ml1.p3.parabolic_fit', source='ML1 Projekt 3, (3.11), §3.6', source_url=P3_SOURCE_URL,
                cd0=cd0,k=k,effective_aspect_ratio=effective_ar,oswald_e=oswald,
                oswald_in_course_range=.7<=oswald<=.98, cd_min_data=cd_min,
                cd0_minus_cd_min=cd0-cd_min, fit=fit,cl_fit_min=low,cl_fit_max=high,
                fit_range_basis='user' if cl_fit_max is not None else 'default_positive_85pct',
                note='Domyślny zakres 0–0,85 Cz_max jest wyborem roboczym. Źródło wymaga sprawdzenia e = 0,7–0,98 i porównania Cx0 z minimum danych.')


def parabolic_polar_from_chart(point_a, point_b, aspect_ratio):
    """P3 graphical/arithmetic method: read two points of the line CD(CL²)."""
    data = pairs([(finite(p.get('cl_squared'),'Cz² na wykresie',nonnegative=True),
                   finite(p.get('cd'),'Cx na wykresie',positive=True)) for p in (point_a,point_b)],
                 'Prosta Cx(Cz²) odczytana z wykresu')
    line = linear_fit(data)
    cd0,k = line['intercept'],line['slope']
    if cd0<=0 or k<=0:
        raise ValueError('Odczyt z wykresu musi dawać dodatnie Cx0 i nachylenie biegunowej.')
    ar = finite(aspect_ratio,'Wydłużenie geometryczne',positive=True)
    effective = 1/(math.pi*k)
    oswald = effective/ar
    return dict(method='ml1.p3.graphical_parabolic_fit',source='ML1 Projekt 3, III-8, rys. 3.4',source_url=P3_SOURCE_URL,
                cd0=cd0,k=k,effective_aspect_ratio=effective,oswald_e=oswald,
                oswald_in_course_range=.7<=oswald<=.98,points=data)


def transfer_finite_wing(rows, source_aspect_ratio, target_aspect_ratio, *, source_taper=1., target_taper=1.,
                         a_inf_rad=None, source_sweep_quarter_deg=0., target_sweep_quarter_deg=0.,
                         re_from=3e6, re_to=3e6, material='metal_composite',
                         source_elliptical=False,target_elliptical=False):
    data = normalize_polar(rows)
    measured = fit_lift_slope(data)
    a_inf = (infer_section_slope(measured['a_per_rad'],source_aspect_ratio,source_taper,source_sweep_quarter_deg,elliptical=source_elliptical)
             if a_inf_rad is None else finite(a_inf_rad,'Pochodna profilu 1/rad',positive=True))
    old = glauert_coefficients(source_aspect_ratio,source_taper,a_inf,source_sweep_quarter_deg,elliptical=source_elliptical)
    new = glauert_coefficients(target_aspect_ratio,target_taper,a_inf,target_sweep_quarter_deg,elliptical=target_elliptical)
    if material not in MATERIAL_TECH_FACTORS:
        raise ValueError('Nieznany rodzaj oporu technicznego.')
    ar1 = finite(source_aspect_ratio,'Wydłużenie źródłowe',positive=True)
    ar2 = finite(target_aspect_ratio,'Wydłużenie docelowe',positive=True)
    cd_min = min(row['cd'] for row in data)
    out = []
    for row in data:
        cl = row['cl']
        delta_induced = cl*cl/math.pi*((1+new['delta'])/ar2-(1+old['delta'])/ar1)
        alpha_delta = cl/math.pi*((1+new['tau'])/ar2-(1+old['tau'])/ar1)
        re = reynolds_drag_correction(cl,row['cd'],data[-1]['cl'],data[0]['cl'],cd_min,re_from,re_to)
        technical = MATERIAL_TECH_FACTORS[material]*re['cd_min_corrected']
        cd = re['cd']+delta_induced+technical
        finite(cd,'Cx płata po przeliczeniu wydłużenia',positive=True)
        out.append(dict(cl=cl, alpha_wing_deg=row['alpha_deg']+math.degrees(alpha_delta),
                        cd_wing=cd, cd_before_technical=re['cd']+delta_induced,
                        delta_cd_induced=delta_induced, alpha_delta_rad=alpha_delta,
                        delta_cd_reynolds=re['delta_cd'], cd_technical=technical))
    return dict(method='ml1.p2.finite_wing_transfer', source='ML1 Projekt 2, (2.22)–(2.27)', source_url=SOURCE_URL,
                a_inf_rad=a_inf, measured_slope=measured, source_corrections=old, target_corrections=new,
                rows=out, note='Wpływ Re na Cz_max wymaga danych tunelowych; metoda nie wymyśla zmiany wartości krytycznych.')

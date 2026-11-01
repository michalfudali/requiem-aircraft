"""ML1 project 3: measured component drag, longitudinal trim and aircraft polar.

Coefficients retain their declared reference areas. Chart readings are inputs,
never guessed from the aircraft category. All quantities are SI.
"""
import math

from ..atmosphere import isa_atmosphere
from .validation import finite, finite_result
from .numerics import pairs, interpolate

SOURCE_URL = 'https://www.meil.pw.edu.pl/zm/content/download/23966/126688/file/Projekt%203.pdf'
TAIL_PRESSURE = {'t_tail': .98, 'below_fuselage': .90, 'fuselage_axis': .85}


def chart_reading(points, argument, *, logarithmic_x=False):
    """Interpolate digitized annex curves, including logarithmic Reynolds axes."""
    data=pairs(points, 'Odczyty wykresu')
    x=finite(argument,'Argument wykresu')
    if logarithmic_x:
        if x<=0 or data[0][0]<=0:
            raise ValueError('Logarytmiczna oś wykresu wymaga dodatnich argumentów.')
        data=[(math.log10(a),b) for a,b in data]
        x=math.log10(x)
    return interpolate(data,x)


def chart_surface(curves,argument,parameter,*,logarithmic_x=False):
    """Interpolate between neighboring chart curves, e.g. etaMa(Ma, nose L/D)."""
    if not isinstance(curves,list) or not 2<=len(curves)<=100:
        raise ValueError('Wykres rodziny krzywych wymaga 2–100 krzywych.')
    data=sorted((finite(c.get('parameter'),'Parametr krzywej'),c.get('points')) for c in curves)
    pairs([(p,0) for p,_ in data])
    p=finite(parameter,'Parametr odczytu')
    if not data[0][0]<=p<=data[-1][0]:raise ValueError('Parametr jest poza zakresem rodziny krzywych.')
    exact=next((points for value,points in data if value==p),None)
    if exact is not None:return chart_reading(exact,argument,logarithmic_x=logarithmic_x)
    a,b=next((a,b) for a,b in zip(data,data[1:]) if a[0]<p<b[0])
    return interpolate([(a[0],chart_reading(a[1],argument,logarithmic_x=logarithmic_x)),
                        (b[0],chart_reading(b[1],argument,logarithmic_x=logarithmic_x))],p)


def drag_statistics(cd_min,cd_parasite_min=None):
    """Annex tables A/B/C are independent checks, never forced calibration."""
    from ..paturski_ml import PATURSKI_TABELA_A,PATURSKI_TABELA_B,PATURSKI_TABELA_C
    actual=finite(cd_min,'Minimalny Cx całego samolotu',positive=True)
    parasite=None if cd_parasite_min is None else finite(cd_parasite_min,'Minimalny Cx szkodliwy',nonnegative=True)
    table_a=[dict(row,computed_cd_min=actual,within_range=row['cx_min_low']<=actual<=row['cx_min_high']) for row in PATURSKI_TABELA_A]
    table_b=[dict(row,computed_cd_parasite_min=parasite,difference=None if parasite is None else parasite-row['cx_szk_min']) for row in PATURSKI_TABELA_B]
    return dict(method='ml1.p3.drag_statistics',table_a=table_a,table_b=table_b,table_c=PATURSKI_TABELA_C,
                source_url='https://www.meil.pw.edu.pl/zm/content/download/23995/126804/file/Zestawienie.pdf',
                note='Zestawienie porównawcze; nie zmienia biegunowej ani nie dopasowuje wyniku do klasy statystycznej.')


def fuselage_drag(length_m, frontal_area_m2, nose_length_m, velocity_ms, altitude_m,
                  *, cf, eta_shape, eta_mach, wetted_area_m2=None):
    """Ostoslavski relation (3.1); cf and eta are measured/digitized chart inputs."""
    length=finite(length_m,'Długość kadłuba',positive=True)
    area=finite(frontal_area_m2,'Przekrój czołowy kadłuba',positive=True)
    nose=finite(nose_length_m,'Długość nosa',positive=True)
    speed=finite(velocity_ms,'Prędkość odniesienia',positive=True)
    height=finite(altitude_m,'Wysokość',nonnegative=True)
    if nose>length or height>20000:
        raise ValueError('Nos musi mieścić się w kadłubie, a wysokość w zakresie ISA 0–20 km.')
    atmosphere=isa_atmosphere(height)
    wetted=(2.85*length*math.sqrt(area) if wetted_area_m2 is None else
            finite(wetted_area_m2,'Powierzchnia omywana kadłuba',positive=True))
    friction=finite(cf,'Cf z wykresu',positive=True)
    shape=finite(eta_shape,'Eta k z wykresu',positive=True)
    compressibility=finite(eta_mach,'Eta Ma z wykresu',positive=True)
    cd=friction*shape*compressibility*wetted/area
    slenderness=length/math.sqrt(4*area/math.pi)
    finite_result(cd,slenderness,wetted)
    return dict(method='ml1.p3.fuselage',source_url=SOURCE_URL,cd=cd,
                reference_area_m2=area,drag_area_m2=cd*area,cf=friction,
                eta_shape=shape,eta_mach=compressibility,wetted_area_m2=wetted,
                wetted_basis='approximation_2.85' if wetted_area_m2 is None else 'measured',
                slenderness=slenderness,nose_slenderness=nose/math.sqrt(4*area/math.pi),
                reynolds=speed*length*atmosphere['rho']/atmosphere['mu'],mach=speed/atmosphere['a'],
                meets_course_minimum=cd>=.06,in_streamlined_course_range=.08<=cd<=.15)


def component_drag_area(component):
    """Both source formats: CD*declared S, or measured force/dynamic pressure."""
    if not isinstance(component,dict):
        raise ValueError('Podzespół musi być obiektem z danymi pomiaru.')
    name=str(component.get('name','Podzespół'))[:200]
    source=str(component.get('source','')).strip()
    if not source:
        raise ValueError(f'{name}: podaj źródło i stronę lub wykres pomiaru.')
    if component.get('drag_n') is not None:
        force=finite(component['drag_n'],'Siła oporu',nonnegative=True)
        if component.get('dynamic_pressure_pa') is not None:
            q=finite(component['dynamic_pressure_pa'],'Ciśnienie dynamiczne pomiaru',positive=True)
        else:
            rho=finite(component.get('rho_kgm3'),'Gęstość pomiaru',positive=True)
            speed=finite(component.get('velocity_ms'),'Prędkość pomiaru',positive=True)
            q=.5*rho*speed*speed
        area=force/q
        basis='force_over_dynamic_pressure'
    else:
        cd=finite(component.get('cd'),'Cx podzespołu',nonnegative=True)
        reference=finite(component.get('reference_area_m2'),'Powierzchnia odniesienia Cx',positive=True)
        area=cd*reference
        basis='coefficient_times_reference_area'
    finite_result(area)
    return dict(name=name,source=source,drag_area_m2=area,basis=basis)


def vertical_tail_drag(profile_cd_min, gap_cd, area_m2):
    cd=finite(profile_cd_min,'Minimalny Cx profilu pionowego',positive=True)
    gap=finite(gap_cd,'Opór szczelin',nonnegative=True)
    area=finite(area_m2,'Pole usterzenia pionowego',positive=True)
    return dict(method='ml1.p3.vertical_tail',source_url=SOURCE_URL,cd=cd+gap,
                reference_area_m2=area,drag_area_m2=(cd+gap)*area)


def aircraft_polar(wing_rows, area_m2, mac_m, tail, components, *, cm_ac, x_cg_mac,
                   x_ac_mac, zeta=6., interference=.04):
    """Equations (3.3)–(3.10), preserving the course reference conventions.

    In (3.9)/(3.10) the course multiplies tail CD/CL by S_H/S. The local
    pressure ratio is already used in kappa' for the trim coefficient (3.4).
    This implements that published approximation and states its convention.
    """
    area=finite(area_m2,'Pole płata',positive=True)
    mac=finite(mac_m,'Średnia cięciwa aerodynamiczna',positive=True)
    cm=finite(cm_ac,'Moment płata względem środka aerodynamicznego')
    cg=finite(x_cg_mac,'Położenie środka masy / MAC')
    ac=finite(x_ac_mac,'Położenie środka aerodynamicznego / MAC')
    coefficient=finite(zeta,'Współczynnik zeta',positive=True)
    interf=finite(interference,'Współczynnik interferencji',nonnegative=True)
    if not 3<=coefficient<=6 or interf>.5:
        raise ValueError('Zeta musi mieścić się w przedziale 3–6, interferencja 0–0,5.')
    if not isinstance(components,list) or len(components)>100:
        raise ValueError('Podaj listę do 100 składników oporu szkodliwego.')
    entries=[component_drag_area(c) for c in components]
    drag_area=math.fsum(c['drag_area_m2'] for c in entries)
    cd_parasite_min=drag_area/area
    sh=finite(tail.get('area_m2'),'Pole usterzenia poziomego',positive=True)
    arm=finite(tail.get('arm_m'),'Ramię usterzenia od środka masy',positive=True)
    span=finite(tail.get('span_m'),'Rozpiętość usterzenia',positive=True)
    e=finite(tail.get('oswald_e'),'Oswald usterzenia',positive=True)
    if not .7<=e<=.9:
        raise ValueError('Według (3.5) przyjmij e usterzenia w zakresie 0,7–0,9.')
    if tail.get('pressure_ratio') is not None:
        ratio=finite(tail['pressure_ratio'],'Stosunek ciśnień dynamicznych usterzenia',positive=True)
    elif tail.get('position') in TAIL_PRESSURE:
        ratio=TAIL_PRESSURE[tail['position']]
    else:
        raise ValueError('Podaj położenie usterzenia lub zmierzony stosunek ciśnień.')
    profile=finite(tail.get('profile_cd_min'),'Minimalny Cx profilu usterzenia',positive=True)
    gap=finite(tail.get('gap_cd'),'Opór szczelin usterzenia',nonnegative=True)
    volume=sh*arm/(area*mac)*ratio
    effective=e*span*span/sh
    if not isinstance(wing_rows,list) or not 3<=len(wing_rows)<=1000:
        raise ValueError('Biegunowa płata musi zawierać 3–1000 wierszy.')
    out=[]
    for row in wing_rows:
        cl=finite(row.get('cl'),'Cz płata')
        cd=finite(row.get('cd_wing',row.get('cd')),'Cx płata',positive=True)
        alpha=finite(row.get('alpha_wing_deg',row.get('alpha_deg')),'Kąt natarcia płata')
        clh=(cm+cl*(cg-ac))/volume
        cdh=profile+gap+clh*clh/(math.pi*effective)
        parasite=cd_parasite_min*(1+abs(cl)/coefficient)
        full_cd=(cd+parasite+cdh*sh/area)*(1+interf)
        full_cl=cl+clh*sh/area
        finite_result(clh,cdh,full_cd,full_cl)
        out.append(dict(cl=full_cl,cd=full_cd,alpha_deg=alpha,cl_wing=cl,cd_wing=cd,
                        cl_tail=clh,cd_tail=cdh,cd_parasite=parasite,
                        ld=full_cl/full_cd,energy_function=max(0,full_cl)**1.5/full_cd,
                        trim_moment_residual=cm+cl*(cg-ac)-volume*clh))
    return dict(method='ml1.p3.aircraft_polar',source_url=SOURCE_URL,rows=out,components=entries,
                parasite_drag_area_m2=drag_area,cd_parasite_min=cd_parasite_min,
                tail_pressure_ratio=ratio,tail_volume_effective=volume,tail_effective_ar=effective,
                tail_area_ratio=sh/area,zeta=coefficient,interference=interf,
                convention='ML1 (3.9)/(3.10): S_H/S; stosunek q_H/q w kappa-prime (3.4).')

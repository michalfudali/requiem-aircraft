"""Direct steady force equilibrium for large climb angles / high installed power.

Uses P6 equilibrium before cos(gamma)≈1, with optional thrust inclination.
Independent force convention: NASA GRC, Forces in a Climb.
https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/forces-in-a-climb/
"""
import math

from ..atmosphere import G0
from .validation import finite,finite_result
from .numerics import pairs,interpolate
from .propulsion import atmosphere_at,_roots_on_grid
from .performance import availability_model
from .prandtl import prandtl_corrected_cd


def exact_force_equilibrium(mass_kg,area_m2,altitude_m,velocities_ms,polar,propulsion_config,*,
                            prandtl=False,thrust_axis_deg=None):
    """Solve both force components without a small-gamma approximation.

    With thrust parallel to V, epsilon=0. If thrust_axis_deg is supplied, use
    epsilon=alpha(CL)+thrust_axis_deg, where polar rows must include alpha_deg.
    At each V solve (T cos epsilon-D)^2+(L+T sin epsilon)^2=W^2 over the supplied
    CL domain. Return every bracketed equilibrium and its two force residuals.
    """
    mass=finite(mass_kg,'Masa w locie',positive=True)
    area=finite(area_m2,'Pole płata',positive=True)
    atm=atmosphere_at(altitude_m);weight=mass*G0
    if not isinstance(velocities_ms,list) or not 1<=len(velocities_ms)<=300:raise ValueError('Podaj 1–300 prędkości.')
    if not isinstance(polar,list) or not 3<=len(polar)<=1000:raise ValueError('Podaj 3–1000 punktów biegunowej.')
    data=pairs([(finite(r.get('cl'),'Cz'),finite(r.get('cd'),'Cx',positive=True)) for r in polar])
    axis=None if thrust_axis_deg is None else finite(thrust_axis_deg,'Odchylenie osi ciągu od cięciwy [stopnie]')
    angles=None if axis is None else pairs([(finite(r.get('cl'),'Cz'),finite(r.get('alpha_deg'),'Kąt natarcia [stopnie]')) for r in polar])
    available=availability_model(propulsion_config)
    kind=propulsion_config.get('kind')
    if prandtl and kind!='jet':raise ValueError('Suplement Prandtla dotyczy odrzutowców.')
    grid=[]
    for a,b in zip(data,data[1:]):grid.extend(a[0]+(b[0]-a[0])*i/12 for i in range(12))
    grid.append(data[-1][0])
    rows=[]
    for value in velocities_ms:
        v=finite(value,'Prędkość lotu [m/s]',positive=True)
        try:
            mach=v/atm['a'];useful=finite(available(v,atm['altitude']),'Dostępna moc lub ciąg',nonnegative=True)
            thrust=useful/v if kind=='propeller' else useful
            q_area=.5*atm['rho']*v*v*area
            def terms(cl):
                base=interpolate(data,cl);drag=prandtl_corrected_cd(base,mach) if prandtl else base
                epsilon=0 if axis is None else math.radians(interpolate(angles,cl)+axis)
                tangent=thrust*math.cos(epsilon)-q_area*drag
                normal=q_area*cl+thrust*math.sin(epsilon)
                return tangent,normal,drag,epsilon
            def equation(cl):
                tangent,normal,_,_=terms(cl)
                return (tangent/weight)**2+(normal/weight)**2-1
            roots=_roots_on_grid(equation,grid)
            equilibria=[]
            for cl in roots:
                tangent,normal,drag,epsilon=terms(cl)
                if normal<0:continue
                gamma=math.atan2(tangent,normal)
                equilibria.append(dict(cl=cl,cd=drag,gamma_deg=math.degrees(gamma),
                    roc_ms=v*math.sin(gamma),thrust_inclination_deg=math.degrees(epsilon),
                    lift_n=q_area*cl,drag_n=q_area*drag,thrust_n=thrust,
                    tangential_residual_n=tangent-weight*math.sin(gamma),
                    normal_residual_n=normal-weight*math.cos(gamma)))
            rows.append(dict(available=bool(equilibria),velocity_ms=v,mach=mach,equilibria=equilibria,
                             best_rate=max(equilibria,key=lambda r:r['roc_ms']) if equilibria else None,
                             reason='' if equilibria else 'Brak równowagi w zakresie dostarczonej biegunowej.'))
        except ValueError as error:rows.append(dict(available=False,velocity_ms=v,equilibria=[],best_rate=None,reason=str(error)))
    valid=[dict(r['best_rate'],velocity_ms=r['velocity_ms']) for r in rows if r['available']]
    return dict(method='ml1.p6.exact_force_equilibrium',
                source_url='https://www.meil.pw.edu.pl/zm/content/download/23969/126700/file/Projekt%206.pdf',
                force_reference='https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/forces-in-a-climb/',
                rows=rows,best_rate=max(valid,key=lambda r:r['roc_ms']) if valid else None,
                best_gradient=max(valid,key=lambda r:r['gamma_deg']) if valid else None,
                thrust_convention='parallel_to_velocity' if axis is None else 'axis_relative_to_chord_plus_alpha',
                prandtl=prandtl,
                scope='Dokładna równowaga ustalona w płaszczyźnie pionowej w ramach podanej biegunowej; bez przybliżenia małego kąta toru.')

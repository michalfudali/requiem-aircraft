"""ML1 project 4: exact speed polar and the distinct small-angle approximation."""
import math

from ..atmosphere import isa_atmosphere, G0
from .validation import finite, finite_result
from .numerics import pairs,interpolate,bracketed_root

SOURCE_URL='https://www.meil.pw.edu.pl/zm/content/download/23967/126692/file/Projekt%204.pdf'


def glide_polar(polar, area_m2, cases,*,maximum_level_speed_ms=None):
    area=finite(area_m2,'Pole płata',positive=True)
    if not isinstance(cases,list) or len(cases)!=3:
        raise ValueError('Projekt 4 wymaga dokładnie trzech przypadków masy i wysokości.')
    if not isinstance(polar,list) or not 3<=len(polar)<=1000:
        raise ValueError('Biegunowa musi zawierać 3–1000 punktów.')
    maximum_speed=None if maximum_level_speed_ms is None else 1.2*finite(maximum_level_speed_ms,'Źródłowa prędkość maksymalna pozioma',positive=True)
    result=[]
    for case in cases:
        mass=finite(case.get('mass_kg'),'Masa lotu',positive=True)
        h=finite(case.get('altitude_m'),'Wysokość lotu',nonnegative=True)
        if h>20000:raise ValueError('Wysokość przekracza 20 km.')
        rho=isa_atmosphere(h)['rho']
        rows=[]
        for point in polar:
            cl=finite(point.get('cl'),'Cz',nonnegative=True)
            cd=finite(point.get('cd'),'Cx',positive=True)
            # q S sqrt(CL²+CD²)=mg, valid also for a vertical dive (CL=0).
            resultant=math.hypot(cl,cd)
            speed=math.sqrt(2*mass*G0/(rho*area*resultant))
            gamma=math.atan2(cd,cl)
            sink=speed*math.sin(gamma)
            horizontal=speed*math.cos(gamma)
            finite_result(speed,sink,horizontal)
            rows.append(dict(cl=cl,cd=cd,velocity_ms=speed,horizontal_ms=horizontal,
                             sink_ms=sink,gamma_down_deg=math.degrees(gamma),
                             ld=cl/cd,force_residual_n=.5*rho*area*speed*speed*resultant-mass*G0))
        terminal_covered=None
        if maximum_speed is not None:
            drag_data=pairs([(r['cl'],r['cd']) for r in rows])
            by_cl=sorted(rows,key=lambda r:r['cl'])
            for a,b in zip(by_cl,by_cl[1:]):
                if (a['velocity_ms']-maximum_speed)*(b['velocity_ms']-maximum_speed)<0:
                    def speed_at(cl):return math.sqrt(2*mass*G0/(rho*area*math.hypot(cl,interpolate(drag_data,cl))))
                    lift=bracketed_root(lambda cl:speed_at(cl)-maximum_speed,a['cl'],b['cl'])
                    drag=interpolate(drag_data,lift);gamma=math.atan2(drag,lift)
                    rows.append(dict(cl=lift,cd=drag,velocity_ms=maximum_speed,
                        horizontal_ms=maximum_speed*math.cos(gamma),sink_ms=maximum_speed*math.sin(gamma),
                        gamma_down_deg=math.degrees(gamma),ld=lift/drag,
                        force_residual_n=.5*rho*area*maximum_speed**2*math.hypot(lift,drag)-mass*G0))
            rows=[r for r in rows if r['velocity_ms']<=maximum_speed*(1+1e-10)]
            if not rows:raise ValueError('Zakres biegunowej nie obejmuje prędkości do 1,2 Vmax.')
            rows.sort(key=lambda r:r['cl'],reverse=True)
            terminal_covered=abs(max(r['velocity_ms'] for r in rows)-maximum_speed)<=1e-7*maximum_speed
        best_ld=min(rows,key=lambda r:r['gamma_down_deg'])
        best_sink=min(rows,key=lambda r:r['sink_ms'])
        result.append(dict(mass_kg=mass,altitude_m=h,rho=rho,rows=rows,
                           optimum=best_ld,economic=best_sink,
                           extrema_basis='discrete_input_polar',target_terminal_velocity_ms=maximum_speed,
                           terminal_speed_covered=terminal_covered))
    return dict(method='ml1.p4.exact_glide',source_url=SOURCE_URL,cases=result)


def approximate_glide(cd0,k,mass_kg,area_m2,altitude_m,*,cl_max=None):
    cd0=finite(cd0,'Cx0',positive=True)
    k=finite(k,'Nachylenie biegunowej k',positive=True)
    m=finite(mass_kg,'Masa',positive=True)
    area=finite(area_m2,'Pole płata',positive=True)
    h=finite(altitude_m,'Wysokość',nonnegative=True)
    if h>20000:raise ValueError('Wysokość przekracza 20 km.')
    rho=isa_atmosphere(h)['rho']
    maximum=None if cl_max is None else finite(cl_max,'Cz maksymalne',positive=True)
    out={}
    for name,cl in [('optimum',math.sqrt(cd0/k)),('economic',math.sqrt(3*cd0/k))]:
        cd=cd0+k*cl*cl
        speed=math.sqrt(2*m*G0/(rho*area*cl))
        sink=speed*cd/cl
        out[name]=dict(cl=cl,cd=cd,velocity_ms=speed,sink_ms=sink,
                       gamma_down_deg=math.degrees(cd/cl),
                       within_cl_max=None if maximum is None else cl<=maximum)
    return dict(method='ml1.p4.approximate_glide',source_url=SOURCE_URL,**out,
                speed_ratio=out['optimum']['velocity_ms']/out['economic']['velocity_ms'],
                sink_ratio=out['optimum']['sink_ms']/out['economic']['sink_ms'],
                assumption='Mały kąt toru lotu i Cx² znacznie mniejsze od Cz².')

"""Map P3's horizontal planform to OpenVSP's unprojected section dimensions.

OpenVSP 3.55 WingGeom.cpp: section offsets at lines 1704-1708 and total
projected span / unprojected area at lines 2657-2702. Sweep must be converted
with span; changing span alone moves the quarter-chord line in plan view.
"""
import math


ELLIPSE_SEGMENTS = 32


def projected_wing_stations(wing, params):
    """Return stations (horizontal y, chord) and a traceable approximation.

    The ellipse uses equal angular increments, clustering stations at the tip.
    Its root and closed tip remain exact. A single interior-chord correction
    preserves the analytic area; for 32 segments it is below 0.042 percent.
    """
    b, area, root = (float(wing[key]) for key in ('b', 'S', 'cr'))
    tip = float(wing['ct'])
    gamma = float(wing['dihedral_deg'])
    sweep = float(wing['sweep_deg'])
    if not all(math.isfinite(v) for v in (b, area, root, tip, gamma, sweep)) or min(b, area, root) <= 0 or tip < 0:
        raise ValueError('OpenVSP: niepoprawne wymiary skrzydła.')
    if abs(gamma) >= 89 or abs(sweep) >= 89:
        raise ValueError('OpenVSP: wznios i skos skrzydła muszą mieć moduł mniejszy niż 89°.')
    planform = str(params.get('wing_planform') or wing.get('wing_planform') or 'trapezoidal')
    half = b/2
    correction = 1.
    if planform == 'elliptical':
        if not math.isclose(root, 4*area/(math.pi*b), rel_tol=1e-7):
            raise ValueError('OpenVSP: obrys eliptyczny nie odpowiada geometrii P3. Przelicz projekt po zmianie obrysu.')
        angles = [math.pi*i/(2*ELLIPSE_SEGMENTS) for i in range(ELLIPSE_SEGMENTS+1)]
        stations = [[half*math.sin(a), root*math.cos(a)] for a in angles]
        stations[-1] = [half, 0.]
        polygon_area = sum((r[0]-l[0])*(l[1]+r[1]) for l, r in zip(stations, stations[1:]))
        fixed_root_area = root*stations[1][0]
        correction = (area-fixed_root_area)/(polygon_area-fixed_root_area)
        for station in stations[1:-1]:
            station[1] *= correction
    elif planform == 'compound_trapezoid':
        station = wing.get('break_station_m')
        station = float(station) if station is not None else float(params.get('break_span_ratio', .4))*half
        if not 0 < station < half:
            raise ValueError('OpenVSP: załamanie obrysu musi leżeć wewnątrz półrozpiętości.')
        stations = [[0., root], [station, root], [half, tip]]
    elif planform in ('trapezoidal', 'rectangular', 'swept_trapezoidal'):
        stations = [[0., root], [half, tip]]
    else:
        raise ValueError('OpenVSP: nieobsługiwany obrys skrzydła.')
    projected_area = sum((r[0]-l[0])*(l[1]+r[1]) for l, r in zip(stations, stations[1:]))
    if not math.isclose(projected_area, area, rel_tol=1e-7):
        raise ValueError('OpenVSP: wymiary obrysu nie domykają powierzchni P3. Przelicz projekt.')
    cosine = math.cos(math.radians(gamma))
    return stations, dict(planform=planform, segments=len(stations)-1,
        projected_span_m=b, projected_area_m2=projected_area, projected_aspect_ratio=b*b/projected_area,
        unprojected_span_m=b/cosine, unprojected_area_m2=projected_area/cosine,
        dihedral_deg=gamma, sweep_quarter_projected_deg=sweep,
        sweep_quarter_unprojected_deg=math.degrees(math.atan(math.tan(math.radians(sweep))*cosine)),
        ellipse_interior_chord_factor=correction,
        note=('Obrys eliptyczny: 32 segmenty, zachowana powierzchnia, cięciwa u nasady i zamknięta końcówka; '
              'korekta cięciw pośrednich poniżej 0,042%.' if planform == 'elliptical' else
              'Geometria odpowiada rzutowi obrysu P3 na płaszczyznę poziomą.'))


def configure_projected_wing(vsp, wing_id, wing, params):
    """Apply the same physical planform in both native model builders."""
    stations, info = projected_wing_stations(wing, params)
    count = len(stations)-1
    for i in range(1, count):
        vsp.InsertXSec(wing_id, i, vsp.XS_FOUR_SERIES)
        vsp.Update()
    vsp.SetParmVal(wing_id, 'RelativeDihedralFlag', 'WingGeom', 0.)
    vsp.SetParmVal(wing_id, 'RelativeTwistFlag', 'WingGeom', 0.)
    cosine = math.cos(math.radians(info['dihedral_deg']))
    twist = float(params.get('wing_twist_deg', 0. if info['planform'] == 'rectangular' else -2.))
    surface = vsp.GetXSecSurf(wing_id, 0)
    for i, (inside, outside) in enumerate(zip(stations, stations[1:]), 1):
        vsp.SetDriverGroup(wing_id, i, vsp.SPAN_WSECT_DRIVER, vsp.ROOTC_WSECT_DRIVER, vsp.TIPC_WSECT_DRIVER)
        section = vsp.GetXSec(surface, i)
        values = dict(Span=(outside[0]-inside[0])/cosine, Root_Chord=inside[1], Tip_Chord=outside[1],
                      Sweep=info['sweep_quarter_unprojected_deg'], Sweep_Location=.25,
                      Dihedral=info['dihedral_deg'], Twist=twist*outside[0]/stations[-1][0])
        for name, value in values.items():
            vsp.SetParmVal(vsp.GetXSecParm(section, name), value)
        # OpenVSP recomputes driver-dependent Area/Aspect for the active section
        # and its neighbour. One Update after all sections leaves earlier areas stale.
        vsp.Update()
    vsp.Update()
    manager = vsp.ErrorMgrSingleton.getInstance()
    errors = []
    while manager.GetNumTotalErrors() > 0:
        errors.append(manager.PopLastError().GetErrorString())
    if errors:
        raise ValueError('OpenVSP nie przyjął obrysu skrzydła: ' + '; '.join(errors))
    return info

"""Separate landing high-lift manoeuvre and vertical-gust cases, in EAS.

The linear gust estimate deliberately has no static-stall reduction. It is a
preliminary wing-load model; local flap, hinge and slipstream loads are separate.
"""
import math


def calculate_flap_envelope(vs_ms, vf_ms, n_flap, u_ms, gust_slope, applicable, basis):
    """gust_slope is the unrounded increment dn/V, including the selected U."""
    if not applicable:
        return dict(applicable=False, status='not_applicable', basis=basis,
                    n_flap=None, u_flap_ms=None, v_f_kmh=None, loop=[],
                    maneuver_polygon=[], gust_pos=[], gust_neg=[], composite_polygon=[],
                    gust_at_vf=None, limits=None, terms=None,
                    note='Brak wychylanej mechanizacji płata — konfiguracja do lądowania nie ma osobnej obwiedni.')

    kmh = lambda v: round(v * 3.6, 1)
    point = lambda v, n: dict(v_kmh=kmh(v), n=round(n, 2))
    va_ms = vs_ms * math.sqrt(n_flap)
    loop = [
        dict(point='Sf (przeciągnięcie z mechanizacją VS0)', **point(vs_ms, 1.)),
        dict(point=f'Af (wejście na n=+{n_flap:g} z mechanizacją)', **point(va_ms, n_flap)),
        dict(point='Ff (prędkość obliczeniowa mechanizacji VF)', **point(vf_ms, n_flap)),
        dict(point='Df (dolny punkt manewrowy przy VF)', **point(vf_ms, 0.)),
    ]
    maneuver = [point(va_ms * i/18, n_flap * (i/18)**2) for i in range(19)]
    maneuver += [point(vf_ms, n_flap), point(vf_ms, 0.), point(0., 0.)]
    speeds = sorted({i*vf_ms/60 for i in range(61)} | {vs_ms*(1-1e-9), vs_ms, va_ms, vf_ms})
    upper, lower = [], []
    for v in speeds:
        man = min((v/vs_ms)**2, n_flap)
        pos, neg = (max(man, 1+gust_slope*v), min(0., 1-gust_slope*v)) if v >= vs_ms else (man, 0.)
        upper.append(point(v, pos))
        lower.append(point(v, neg))
    dn = gust_slope * vf_ms
    positive, negative = max(n_flap, 1+dn), min(0., 1-dn)
    return dict(
        applicable=True, status='estimated', basis=basis, n_flap=n_flap,
        u_flap_ms=u_ms, v_f_kmh=kmh(vf_ms), loop=loop, maneuver_polygon=maneuver,
        gust_pos=[point(v, 1+gust_slope*v) for v in (vs_ms, vf_ms)],
        gust_neg=[point(v, 1-gust_slope*v) for v in (vs_ms, vf_ms)],
        composite_polygon=upper+list(reversed(lower)),
        gust_at_vf=dict(v_ms=vf_ms, v_kmh=kmh(vf_ms), u_ms=u_ms, delta_n=dn,
                        n_positive=1+dn, n_negative=1-dn),
        limits=dict(n_maneuver_pos=n_flap, n_maneuver_neg=0., n_gust_max=1+dn,
                    n_gust_min=1-dn, n_dimensioning_pos=positive, n_dimensioning_neg=negative,
                    n_ult_pos=1.5*positive, n_ult_neg=1.5*negative),
        terms=dict(vs_ms=vs_ms, va_ms=va_ms, vf_ms=vf_ms, gust_slope=gust_slope),
        note=('Konfiguracja do lądowania, masa startowa, ISA poziom morza; manewr i podmuch liczone osobno. '
              'W modelu mechanizacji Cz zmienia się o stały przyrost, dlatego przyjęto tę samą pochodną a '
              'co dla płata czystego. Liniowe podmuchy bez redukcji przez statyczne Czmax. '
              'Nie obejmuje lokalnych sił, momentów zawiasowych, strugi śmigła ani klap przelotowych.'))

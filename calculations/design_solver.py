"""Close mass/geometry/aerodynamics and verify installed propulsion against P4."""
import math

from calculations.atmosphere import G0, isa_atmosphere
from calculations.polish_law import oei_gradient_required
from calculations.flight_model import mission_masses, one_engine_out_drag, propeller_efficiency, propulsion_lapse

# Finer than the course's 0.1% mass criterion, but above the precision of
# tabulated component correlations. Final range is independently checked in P5.
DESIGN_TOLERANCE = 5e-4


MASS_NOT_CLOSED = 'Nie osiągnięto tolerancji domknięcia'


def resolve_design(params, states, size_airframe):
    # Recompute internal aerodynamics after every input edit or imported project.
    params.pop('_mission_polar', None)
    params.pop('_k_empty_p3', None)
    coupled = params.get('design_iteration_mode') == 'coupled' and params['engine_type'] != 'none'
    history, previous, last_mass, failure = [], None, None, None
    converged = not coupled
    for step in range(1, 41 if coupled else 2):
        try:
            solution = size_airframe(params, states)
        except ValueError as error:
            if not history:
                raise
            failure = str(error)
            # Keep the last physically calculated state, with an explicit failed closure.
            params.clear()
            params.update(last_params)
            break
        mass, sizing, geometry, aero = solution
        polar = dict(S=geometry['wing']['S'], cx0=aero['cx0_clean'], k=aero['k_clean'], reference_mass_kg=mass['m0'])
        relative = max(abs(polar[k]-previous[k])/polar[k] for k in polar) if previous else None
        if last_mass is not None:
            relative = max(relative, abs(mass['m0']-last_mass)/mass['m0'])
        used = params.get('_mission_polar')
        if used and relative is not None:
            # Small changes between iterates alone do not establish closure of
            # an under-relaxed polar. Check its actual use in the fuel balance.
            relative = max(relative, *(abs(polar[k]-used[k])/polar[k] for k in ('cx0', 'k')))
        # BIPOL_3: the sum of the component masses replaces the sample's m_e when the author asks for it.
        close_components = coupled and params.get('empty_mass_closure') == 'components'
        ratio = mass['component_closure']['sum_kg']/mass['m_empty'] if close_components else 1.
        if close_components and relative is not None:
            relative = max(relative, abs(ratio-1))
        history.append(dict(iteration=step, m0=mass['m0'], **polar, relative_error=relative))
        if not coupled or relative is not None and relative <= DESIGN_TOLERANCE:
            converged = True
            break
        if step == 40:
            break
        last_params = dict(params)
        previous, last_mass = polar, mass['m0']
        if close_components:
            # m_0 reacts violently to K in eq. (5), so K is taken from the mass the components imply.
            law, components = mass['empty_mass_law'], mass['component_closure']['sum_kg']
            target = (components+mass['m_crew']+mass['m_payload'])/(1-mass['m_fuel']/mass['m0'])
            wanted = components/target/(law['A']*target**law['C']*law['k_vs'])
            current = float(params.get('_k_empty_p3', 1.))
            params['_k_empty_p3'] = current+.7*(wanted-current)
        # A direct replacement can jump from the small preliminary aircraft to
        # a distant, unstable mass branch. Relax drag coefficients from the
        # preliminary polar on the first step, then from the last used polar.
        # Geometry is updated in full; loading mode scales S with trial mass.
        prior = used or dict(cx0=mass['preliminary_polar']['cx0'],
                             k=1/(math.pi*params['aspect_ratio']*params['oswald_e']))
        params['_mission_polar'] = {**polar, **{
            key: .5*(prior[key]+polar[key]) for key in ('cx0', 'k')}}
    refine_flight_sizing(sizing, geometry, aero, params, mass)
    if not converged and failure is None:
        failure = MASS_NOT_CLOSED + ' w 40 iteracjach. Zmień założenia i sprawdź ostatnie kroki iteracji.'
    return (*solution, dict(mode='coupled' if coupled else 'preliminary', converged=converged,
                           iterations=len(history), history=history, failure=failure,
                           tolerance=DESIGN_TOLERANCE, route_margin=1.001 if coupled else 1.0))


def refine_flight_sizing(sizing, geom, aero, params, mass):
    """Required total installed rating for actual drag, climb and cruise-entry mass.

    Sizing is free only in sized mode. A supplied engine rating is never increased.
    The preliminary course chart stays available as a study; this is its P4 check.
    """
    engine = params['engine_type']
    if engine == 'none':
        return
    dp, area = sizing['design_point'], geom['wing']['S']
    weight = mass['m0'] * G0
    cruise_mass = mission_masses(mass)['cruise_start']
    speed = params['cruise_speed_kmh'] / 3.6
    atmosphere = isa_atmosphere(params['cruise_altitude_m'])

    def drag(m, rho, v):
        qs = .5 * rho * v*v * area
        return qs*aero['cx0_clean'] + aero['k_clean']*(m*G0)**2/qs

    lapse = propulsion_lapse(params, params['cruise_altitude_m'], speed)
    cruise_thrust = drag(cruise_mass, atmosphere['rho'], speed) / max(lapse, 1e-12)
    stall = math.sqrt(2*weight/(1.225*area*aero['cz_max_clean']))

    def climb_rating(v):
        needed = drag(mass['m0'], 1.225, v) + weight*params['climb_rate_ms']/v
        needed /= max(propulsion_lapse(params, 0, v), 1e-12)
        return needed if engine == 'jet' else needed*v/propeller_efficiency(params, v)

    left, right = stall*1.05, max(stall*4, speed*1.5)
    for _ in range(55):
        a, b = left+(right-left)/3, right-(right-left)/3
        if climb_rating(a) < climb_rating(b):
            right = b
        else:
            left = a
    climb = climb_rating((left+right)/2)
    cruise = cruise_thrust if engine == 'jet' else cruise_thrust*speed/propeller_efficiency(params, speed)

    def rating_at(needed, v):
        needed /= max(propulsion_lapse(params, 0, v), 1e-12)
        return needed if engine == 'jet' else needed*v/propeller_efficiency(params, v)
    # Maximum speed of the topic, from the P4 polar rather than the preliminary one.
    required_top = float(params.get('v_max_required_kmh') or 0)/3.6
    top = rating_at(drag(mass['m0'], 1.225, required_top), required_top) if required_top else 0.
    # JAR 25.121: the remaining engines carry the second segment.
    gradient, engines, one_out = oei_gradient_required(params), int(float(params.get('n_engines', 1) or 1)), 0.
    if gradient and engines >= 2:
        v2, drag_v2 = one_engine_out_drag(mass['m0'], area, aero['cz_max_to'], aero['cx0_to'], aero['k_to'])
        one_out = rating_at(drag_v2+weight*gradient/100, v2)*engines/(engines-1)
    candidates = {'przelot (biegunowa P4)': cruise, 'wznoszenie (biegunowa P4)': climb,
                  'prędkość maksymalna (biegunowa P4)': top, 'wznoszenie z jednym silnikiem niepracującym': one_out}
    governing = max(candidates, key=candidates.get)
    requirement = candidates[governing]
    sizing['flight_model_requirement'] = dict(engine_type=engine, cruise_entry_mass_kg=cruise_mass,
        cruise_rating=cruise, climb_rating=climb, required_rating=requirement,
        unit='N' if engine == 'jet' else 'W', cx0=aero['cx0_clean'], k=aero['k_clean'],
        note='Wymaganie z końcowej biegunowej; całkowity ciąg statyczny lub moc na wale wszystkich silników.')
    if engine == 'jet':
        required = requirement*1.06/weight
        dp['required_thrust_kn'] = max(dp.get('required_thrust_kn') or 0, required * weight / 1000)
        if required > dp['tw'] and not params.get('engine_static_thrust_kn'):
            dp.update(tw=required, thrust_kn=required*weight/1000, governing=governing)
    else:
        required = requirement*1.08/1000
        if required > dp['required_power_kw']:
            dp.update(required_power_kw=required, governing=governing)
        if params.get('power_input_mode') != 'fixed':
            power = dp['required_power_kw']
            dp.update(power_kw=power, power_hp=power*1000/735.5, pw=power*1000/weight,
                      pw_hp_kg=power*1000/735.5/mass['m0'])

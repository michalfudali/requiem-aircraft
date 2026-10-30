"""Shared preliminary take-off model, from standstill to a 15 m obstacle."""
import math
from calculations.atmosphere import G0, RHO0


def takeoff_distance(ws, cz_max, cx0, k, engine, loading, eta=.82, eta_to=.65, mu_ground=0.03):
    """loading is P/W [W/N] for propellers or T/W [-] for jets.

    Constant mean acceleration, transition at n=1.15, ISA sea level.
    Return unavailable, never fictitious positive acceleration/climb, if power
    cannot overcome drag and rolling resistance. No regulatory field factors.
    """
    if engine == 'none':
        return dict(available=False, ground_roll_m=0., transition_m=0., climb_to_15m_m=0.,
                    air_distance_m=0., climb_angle_deg=0., distance_to_15m=0.,
                    ground_roll_time_s=None, time_to_15m_s=None,
                    note='Start samodzielny nie dotyczy statku bez napędu.')
    vs = math.sqrt(2 * ws / (RHO0 * cz_max))
    vlof, v2, vtr = 1.15 * vs, 1.2 * vs, 1.175 * vs
    vrms = vlof / math.sqrt(2)
    q = .5 * RHO0 * vrms**2
    phi = 1.6**2 / (1 + 1.6**2)
    thrust_roll = loading if engine == 'jet' else loading * eta_to / vrms
    net = thrust_roll - q / ws * (cx0 + phi * k * .25**2) - mu_ground * (1 - q / ws * .25)
    q2 = .5 * RHO0 * v2**2
    thrust_climb = loading if engine == 'jet' else loading * eta / v2
    gradient = thrust_climb - q2 / ws * (cx0 + k * (ws / q2)**2)
    ground = vlof**2 / (2 * G0 * net) if net > 0 else None
    if net <= 0 or gradient <= 0:
        return dict(available=False, ground_roll_m=ground, transition_m=None, climb_to_15m_m=None,
                    air_distance_m=None, climb_angle_deg=None, distance_to_15m=None,
                    ground_roll_time_s=None, time_to_15m_s=None,
                    note='Brak nadmiaru ciągu do rozbiegu lub wznoszenia nad przeszkodę 15 m.')
    # Czas startu (Opis projektów, P5): rozbieg ze stałym średnim przyspieszeniem g·net,
    # łuk przejściowy przy V_tr i wznoszenie do 15 m przy V2.
    t_ground = vlof / (G0 * net)
    gamma = math.asin(min(.35, gradient))
    radius = vtr**2 / (G0 * .15)
    height = radius * (1 - math.cos(gamma))
    if height >= 15:
        gamma = math.acos(max(0., 1 - 15 / radius))
        transition, climb = radius * math.sin(gamma), 0.
    else:
        transition = radius * math.sin(gamma)
        climb = (15 - height) / math.tan(gamma)
    t_air = gamma * radius / vtr + (climb / (v2 * math.cos(gamma)) if climb else 0.0)
    terms = dict(ws=ws, cz_max=cz_max, cx0=cx0, k=k, loading=loading, eta=eta, eta_to=eta_to,
                 mu_ground=mu_ground, vs=vs, vlof=vlof, v2=v2, vtr=vtr, vrms=vrms, q=q, phi=phi,
                 thrust_roll=thrust_roll, net=net, q2=q2, thrust_climb=thrust_climb,
                 gradient=gradient, gamma=gamma, radius=radius, height=height)
    return dict(available=True, terms=terms, ground_roll_m=ground, transition_m=transition,
                climb_to_15m_m=climb, air_distance_m=transition + climb,
                climb_angle_deg=math.degrees(gamma), distance_to_15m=ground + transition + climb,
                ground_roll_time_s=t_ground, time_to_15m_s=t_ground + t_air,
                note='ISA, poziom morza, przeszkoda 15 m; odcinek naziemny i powietrzny, bez współczynników operacyjnych.')


def required_takeoff_loading(ws, cz_max, cx0, k, engine, distance, eta=.82, eta_to=.65, mu_ground=0.03):
    """Solve the same complete-distance model for the matching chart."""
    low, high = 0., 2. if engine == 'jet' else 200.
    def adequate(value):
        result = takeoff_distance(ws, cz_max, cx0, k, engine, value, eta, eta_to, mu_ground=mu_ground)
        return result['available'] and result['distance_to_15m'] <= distance
    if not adequate(high):
        return None
    for _ in range(45):
        middle = (low + high) / 2
        if adequate(middle):
            high = middle
        else:
            low = middle
    return high


def refine_takeoff_sizing(sizing, geom, aero, params, mass):
    """Check the course estimate (BIPOL_2 eq. 2) with the take-off model and the actual flap polar.

    The matching chart keeps the course curve; only the design point is raised when the
    flight-mechanics model needs more thrust or power. Known engine power stays fixed.
    """
    target = params.get('takeoff_distance_m', 0)
    engine = params['engine_type']
    if not target or engine == 'none' or params.get('operating_surface') == 'water':
        return
    dp = sizing['design_point']
    requirement = required_takeoff_loading(mass * G0 / geom['wing']['S'], aero['cz_max_to'], aero['cx0_to'],
                                           aero['k_to'], engine, target, params['prop_efficiency'],
                                           params['prop_eff_to'])
    if requirement is None:
        raise ValueError('Zadana całkowita długość startu jest nieosiągalna w modelu. Zwiększ drogę startu lub zmniejsz obciążenie powierzchni.')
    sizing['takeoff_model_requirement'] = requirement
    if engine == 'jet':
        if requirement * 1.06 > dp['tw']:
            dp['governing'] = 'start (model mechaniki lotu)'
        dp['tw'] = max(dp['tw'], requirement * 1.06)
        dp['thrust_kn'] = dp['tw'] * mass * G0 / 1000
    else:
        model_power_kw = requirement * mass * G0 / 1000 * 1.08
        if model_power_kw > dp['required_power_kw']:
            dp['governing'] = 'start (model mechaniki lotu)'
        dp['required_power_kw'] = max(dp['required_power_kw'], model_power_kw)
        if params.get('power_input_mode') != 'fixed':
            dp['power_kw'] = dp['required_power_kw']
            dp['power_hp'] = dp['power_kw'] * 1000 / 735.5
            dp['pw'] = dp['power_kw'] * 1000 / (mass * G0)
            dp['pw_hp_kg'] = dp['power_hp'] / mass

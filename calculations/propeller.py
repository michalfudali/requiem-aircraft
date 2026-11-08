"""Shared propeller inputs and kinematics; RPM always belongs to the propeller shaft."""
import math

from calculations.atmosphere import isa_atmosphere


def shaft_rpm(params):
    """Support the older standalone clearance input without accepting conflicting RPMs."""
    canonical = params.get('propeller_rpm')
    legacy = params.get('prop_rpm')
    if canonical is not None and legacy is not None and float(canonical) != float(legacy):
        raise ValueError('Sprzeczne obroty śmigła: propeller_rpm i prop_rpm. Podaj jedną wartość wału śmigła.')
    rpm = canonical if canonical is not None else legacy
    if rpm is None:
        rpm = 2000.0 if params.get('aircraft_type') == 'turboprop_regional' else 2400.0
    rpm = float(rpm)
    if not math.isfinite(rpm) or rpm <= 0:
        raise ValueError('Obroty wału śmigła muszą być dodatnią, skończoną liczbą.')
    return rpm


def design_propeller(params, total_power_w):
    """Preliminary propeller of the P4 selection (Paturski, P5): speed, advance ratio and diameter."""
    n_engines = max(1, int(float(params.get('n_engines', 1) or 1)))
    altitude = (float(params.get('cruise_altitude_m', 2500.0))
                if params.get('aircraft_type') in ('turboprop_regional', 'twin_piston') else 0.0)
    atmosphere = isa_atmosphere(altitude)
    speed = max(35.0, float(params.get('cruise_speed_kmh', 220.0)) * 1.15 / 3.6)
    revolutions = shaft_rpm(params) / 60.0
    power = total_power_w / n_engines
    speed_coefficient = speed * math.pow(atmosphere['rho'] / max(1.0, power * revolutions ** 2), 0.2)
    advance = max(0.45, min(1.35, 0.52 * math.pow(max(0.2, speed_coefficient), 0.78)))
    diameter = max(1.10, min(3.80, speed / (advance * revolutions)))
    if params.get('propeller_diameter_m') is not None:
        diameter = float(params['propeller_diameter_m'])
    return dict(altitude_m=altitude, rho=atmosphere['rho'], a=atmosphere['a'], speed_ms=speed, revolutions_s=revolutions,
                power_w=power, speed_coefficient=speed_coefficient, advance=advance, diameter_m=diameter)


def helical_tip_mach(diameter_m, rpm, axial_speed_ms, speed_of_sound_ms):
    """Vector sum of the rotational tip speed and the free-stream axial speed.

    This is a kinematic estimate, without the induced velocity through the disk.
    NASA TP 19780005911, discussion of helical tip Mach number, equations (8).
    """
    return math.hypot(math.pi * diameter_m * rpm / 60.0, axial_speed_ms) / speed_of_sound_ms

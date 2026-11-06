"""Shared propeller inputs and kinematics; RPM always belongs to the propeller shaft."""
import math


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


def helical_tip_mach(diameter_m, rpm, axial_speed_ms, speed_of_sound_ms):
    """Vector sum of the rotational tip speed and the free-stream axial speed.

    This is a kinematic estimate, without the induced velocity through the disk.
    NASA TP 19780005911, discussion of helical tip Mach number, equations (8).
    """
    return math.hypot(math.pi * diameter_m * rpm / 60.0, axial_speed_ms) / speed_of_sound_ms

"""
Moduł obliczeń Międzynarodowej Atmosfery Wzorcowej (ISA)
Według normy ICAO / BIPOL MEiL PW
"""
import math

# Stałe fizyczne ISA
T0 = 288.15        # Temperatura na poziomie morza [K]
P0 = 101325.0      # Ciśnienie na poziomie morza [Pa]
RHO0 = 1.225       # Gęstość na poziomie morza [kg/m^3]
G0 = 9.80665       # Przyspieszenie ziemskie [m/s^2]
R_AIR = 287.05287  # Indywidualna stała gazowa dla powietrza [J/(kg*K)]
KAPPA = 1.4        # Wykładnik adiabaty dla powietrza
BETA_T = -0.0065   # Pionowy gradient temperatury w troposferze [K/m]
H_TROPO = 11000.0  # Wysokość tropopauzy [m]
T_TROPO = 216.65   # Temperatura w tropopauzie [K]
SUTHERLAND_C = 120.0
SUTHERLAND_MU0 = 1.7894e-5

def isa_atmosphere(altitude_m: float):
    """
    Oblicza parametry atmosfery ISA na zadanej wysokości h [m].
    Zwraca słownik:
      - T: temperatura [K]
      - p: ciśnienie [Pa]
      - rho: gęstość [kg/m^3]
      - a: prędkość dźwięku [m/s]
      - sigma: względna gęstość rho / rho0 [-]
      - delta: względne ciśnienie p / p0 [-]
      - theta: względna temperatura T / T0 [-]
    """
    # Continue the tropospheric law below sea level for low-lying airfields.
    # The design-input domain extends to -500 m (e.g. the Dead Sea region).
    h = max(-500.0, float(altitude_m))
    
    if h <= H_TROPO:
        # Troposfera
        T = T0 + BETA_T * h
        p = P0 * math.pow(T / T0, -G0 / (BETA_T * R_AIR))
    else:
        # Dolna stratosfera (izotermiczna)
        T_tropo = T0 + BETA_T * H_TROPO
        p_tropo = P0 * math.pow(T_tropo / T0, -G0 / (BETA_T * R_AIR))
        delta_h = h - H_TROPO
        T = T_tropo
        p = p_tropo * math.exp(-G0 * delta_h / (R_AIR * T))
        
    rho = p / (R_AIR * T)
    a = math.sqrt(KAPPA * R_AIR * T)
    
    # Lepkość dynamiczna wg prawa Sutherlanda
    mu = SUTHERLAND_MU0 * math.pow(T / T0, 1.5) * (T0 + SUTHERLAND_C) / (T + SUTHERLAND_C)
    
    return {
        "altitude": h,
        # Keep physical calculations continuous; presentation rounds the values.
        "T": T,
        "T_C": T - 273.15,
        "p": p,
        "rho": rho,
        "a": a,
        "mu": mu,
        "sigma": rho / RHO0,
        "delta": p / P0,
        "theta": T / T0
    }

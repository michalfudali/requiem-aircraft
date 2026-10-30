"""
Moduł profili lotniczych i generator rzędnych profilu dla arkusza P3 (BiPOL Requiem).
Zgodnie z wymaganiami MEiL PW:
- Wyznaczanie geometrii profilu skrzydła przeskalowanego do cięciwy c = 200 mm,
- Współrzędne stacji pomiarowych: x [mm], y_górna [mm], y_dolna [mm], grubość dy [mm],
- profile NACA 4-cyfrowe, NACA 5-cyfrowe (np. NACA 23012), profile szybowcowe (Wortmann FX),
  profile nadkrytyczne NASA SC(2)-0412.
"""
import math
from typing import List, Dict, Tuple


STANDARD_STATIONS_PCT = [
    0.0, 0.5, 1.25, 2.5, 5.0, 7.5, 10.0, 15.0, 20.0, 25.0,
    30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0,
    80.0, 85.0, 90.0, 95.0, 100.0
]


def naca_4digit_coords(m: float, p: float, t: float, stations_pct: List[float] = None) -> List[Dict]:
    """
    Oblicza współrzędne profilu NACA 4-cyfrowego:
    m - maksymalne ugięcie linii szkieletowej (np. 0.02 dla NACA 2412)
    p - położenie maksymalnego ugięcia (np. 0.4 dla NACA 2412)
    t - maksymalna względna grubość profilu (np. 0.12 dla NACA 2412)
    """
    if stations_pct is None:
        stations_pct = STANDARD_STATIONS_PCT

    table = []
    c_mm = 200.0

    for xc_pct in stations_pct:
        x = xc_pct / 100.0
        # Rozkład grubości symetrycznej
        yt = 5.0 * t * (
            0.2969 * math.sqrt(max(0.0, x))
            - 0.1260 * x
            - 0.3516 * (x ** 2)
            + 0.2843 * (x ** 3)
            - 0.1036 * (x ** 4)  # 0.1036 daje domkniętą krawędź spływu
        )

        # Linia szkieletowa
        if p > 0 and m > 0:
            if x < p:
                yc = (m / (p ** 2)) * (2.0 * p * x - (x ** 2))
                dyc_dx = (2.0 * m / (p ** 2)) * (p - x)
            else:
                yc = (m / ((1.0 - p) ** 2)) * ((1.0 - 2.0 * p) + 2.0 * p * x - (x ** 2))
                dyc_dx = (2.0 * m / ((1.0 - p) ** 2)) * (p - x)
            theta = math.atan(dyc_dx)
        else:
            yc = 0.0
            theta = 0.0

        xu = x - yt * math.sin(theta)
        yu = yc + yt * math.cos(theta)
        xl = x + yt * math.sin(theta)
        yl = yc - yt * math.cos(theta)

        x_mm = round(x * c_mm, 2)
        yu_mm = round(yu * c_mm, 2)
        yl_mm = round(yl * c_mm, 2)
        dy_mm = round((yu - yl) * c_mm, 2)

        table.append({
            "xc_pct": xc_pct,
            "x_mm": x_mm,
            "y_upper_mm": yu_mm,
            "y_lower_mm": yl_mm,
            "dy_mm": dy_mm, "thick_mm": dy_mm,
            "xu_norm": round(xu, 5),
            "yu_norm": round(yu, 5),
            "xl_norm": round(xl, 5),
            "yl_norm": round(yl, 5),
        })

    return table


def naca_23012_coords(stations_pct: List[float] = None) -> List[Dict]:
    """
    Współrzędne wzorcowego profilu lotnictwa ogólnego (GA) NACA 23012.
    Linia szkieletowa 230: r = 0.2025, k1 = 361.4, m = 0.0580.
    """
    if stations_pct is None:
        stations_pct = STANDARD_STATIONS_PCT

    table = []
    c_mm = 200.0
    t = 0.12
    r = 0.2025
    k1 = 361.4

    for xc_pct in stations_pct:
        x = xc_pct / 100.0
        yt = 5.0 * t * (
            0.2969 * math.sqrt(max(0.0, x))
            - 0.1260 * x
            - 0.3516 * (x ** 2)
            + 0.2843 * (x ** 3)
            - 0.1036 * (x ** 4)
        )

        if x < r:
            yc = (k1 / 6.0) * ((x ** 3) - 3.0 * r * (x ** 2) + (r ** 2) * (3.0 - r) * x)
            dyc_dx = (k1 / 6.0) * (3.0 * (x ** 2) - 6.0 * r * x + (r ** 2) * (3.0 - r))
        else:
            yc = (k1 * (r ** 3) / 6.0) * (1.0 - x)
            dyc_dx = -(k1 * (r ** 3) / 6.0)

        theta = math.atan(dyc_dx)
        xu = x - yt * math.sin(theta)
        yu = yc + yt * math.cos(theta)
        xl = x + yt * math.sin(theta)
        yl = yc - yt * math.cos(theta)

        table.append({
            "xc_pct": xc_pct,
            "x_mm": round(x * c_mm, 2),
            "y_upper_mm": round(yu * c_mm, 2),
            "y_lower_mm": round(yl * c_mm, 2),
            "dy_mm": round((yu - yl) * c_mm, 2), "thick_mm": round((yu - yl) * c_mm, 2),
            "xu_norm": round(xu, 5),
            "yu_norm": round(yu, 5),
            "xl_norm": round(xl, 5),
            "yl_norm": round(yl, 5),
        })

    return table


def wortmann_fx61_163_coords(stations_pct: List[float] = None) -> List[Dict]:
    """
    Rzędne laminarnego profilu szybowcowego Wortmann FX 61-163 (grubość 16.3%, ugięcie 6.1%).
    """
    if stations_pct is None:
        stations_pct = STANDARD_STATIONS_PCT

    # Wzorcowe punkty profilu FX 61-163 (Abbott / Selig database)
    raw_points = [
        (0.0, 0.0, 0.0),
        (0.5, 0.0163, -0.0118),
        (1.25, 0.0264, -0.0182),
        (2.5, 0.0385, -0.0248),
        (5.0, 0.0558, -0.0335),
        (7.5, 0.0691, -0.0398),
        (10.0, 0.0801, -0.0448),
        (15.0, 0.0975, -0.0522),
        (20.0, 0.1105, -0.0568),
        (25.0, 0.1198, -0.0592),
        (30.0, 0.1256, -0.0595),
        (35.0, 0.1281, -0.0578),
        (40.0, 0.1274, -0.0542),
        (45.0, 0.1235, -0.0488),
        (50.0, 0.1167, -0.0420),
        (55.0, 0.1070, -0.0342),
        (60.0, 0.0949, -0.0260),
        (65.0, 0.0808, -0.0180),
        (70.0, 0.0655, -0.0108),
        (75.0, 0.0500, -0.0050),
        (80.0, 0.0355, -0.0008),
        (85.0, 0.0225, 0.0016),
        (90.0, 0.0118, 0.0022),
        (95.0, 0.0042, 0.0012),
        (100.0, 0.0000, 0.0000),
    ]

    raw_dict = {pt[0]: (pt[1], pt[2]) for pt in raw_points}
    table = []
    c_mm = 200.0

    for xc_pct in stations_pct:
        if xc_pct in raw_dict:
            yu, yl = raw_dict[xc_pct]
        else:
            # Interpolacja liniowa
            pts_sorted = sorted(raw_dict.keys())
            for i in range(len(pts_sorted) - 1):
                if pts_sorted[i] <= xc_pct <= pts_sorted[i + 1]:
                    x0, x1 = pts_sorted[i], pts_sorted[i + 1]
                    f = (xc_pct - x0) / (x1 - x0)
                    yu = raw_dict[x0][0] + f * (raw_dict[x1][0] - raw_dict[x0][0])
                    yl = raw_dict[x0][1] + f * (raw_dict[x1][1] - raw_dict[x0][1])
                    break
            else:
                yu, yl = 0.0, 0.0

        x = xc_pct / 100.0
        table.append({
            "xc_pct": xc_pct,
            "x_mm": round(x * c_mm, 2),
            "y_upper_mm": round(yu * c_mm, 2),
            "y_lower_mm": round(yl * c_mm, 2),
            "dy_mm": round((yu - yl) * c_mm, 2), "thick_mm": round((yu - yl) * c_mm, 2),
            "xu_norm": round(x, 5),
            "yu_norm": round(yu, 5),
            "xl_norm": round(x, 5),
            "yl_norm": round(yl, 5),
        })

    return table


def nasa_sc2_0412_coords(stations_pct: List[float] = None) -> List[Dict]:
    """
    Rzędne nadkrytycznego profilu odrzutowców biznesowych NASA SC(2)-0412.
    """
    if stations_pct is None:
        stations_pct = STANDARD_STATIONS_PCT

    raw_points = [
        (0.0, 0.0, 0.0),
        (0.5, 0.0152, -0.0115),
        (1.25, 0.0245, -0.0175),
        (2.5, 0.0352, -0.0232),
        (5.0, 0.0505, -0.0305),
        (7.5, 0.0618, -0.0352),
        (10.0, 0.0705, -0.0385),
        (15.0, 0.0832, -0.0428),
        (20.0, 0.0915, -0.0448),
        (25.0, 0.0965, -0.0452),
        (30.0, 0.0988, -0.0442),
        (35.0, 0.0985, -0.0418),
        (40.0, 0.0958, -0.0380),
        (45.0, 0.0908, -0.0332),
        (50.0, 0.0838, -0.0278),
        (55.0, 0.0752, -0.0220),
        (60.0, 0.0652, -0.0162),
        (65.0, 0.0542, -0.0110),
        (70.0, 0.0428, -0.0065),
        (75.0, 0.0315, -0.0032),
        (80.0, 0.0210, -0.0012),
        (85.0, 0.0122, -0.0005),
        (90.0, 0.0058, -0.0002),
        (95.0, 0.0018, -0.0001),
        (100.0, 0.0000, 0.0000),
    ]

    raw_dict = {pt[0]: (pt[1], pt[2]) for pt in raw_points}
    table = []
    c_mm = 200.0

    for xc_pct in stations_pct:
        if xc_pct in raw_dict:
            yu, yl = raw_dict[xc_pct]
        else:
            pts_sorted = sorted(raw_dict.keys())
            for i in range(len(pts_sorted) - 1):
                if pts_sorted[i] <= xc_pct <= pts_sorted[i + 1]:
                    x0, x1 = pts_sorted[i], pts_sorted[i + 1]
                    f = (xc_pct - x0) / (x1 - x0)
                    yu = raw_dict[x0][0] + f * (raw_dict[x1][0] - raw_dict[x0][0])
                    yl = raw_dict[x0][1] + f * (raw_dict[x1][1] - raw_dict[x0][1])
                    break
            else:
                yu, yl = 0.0, 0.0

        x = xc_pct / 100.0
        table.append({
            "xc_pct": xc_pct,
            "x_mm": round(x * c_mm, 2),
            "y_upper_mm": round(yu * c_mm, 2),
            "y_lower_mm": round(yl * c_mm, 2),
            "dy_mm": round((yu - yl) * c_mm, 2), "thick_mm": round((yu - yl) * c_mm, 2),
            "xu_norm": round(x, 5),
            "yu_norm": round(yu, 5),
            "xl_norm": round(x, 5),
            "yl_norm": round(yl, 5),
        })

    return table


def generate_airfoil_200mm(airfoil_name: str, tc_ratio: float = 0.12) -> Tuple[List[Dict], str]:
    """
    Generuje tabelę rzędnych dla cięciwy 200 mm oraz notę techniczną.
    Obsługuje profile: NACA 23012, NACA 2412, NACA 0012, NACA 4412, NACA 2415,
    Wortmann FX 61-163, NASA SC(2)-0412.
    """
    name = (airfoil_name or "NACA 23012").strip()
    upper = name.upper()

    if "23012" in upper or "230" in upper:
        coords = naca_23012_coords()
        note = "Rzędne zweryfikowanego profilu NACA 23012 (linia szkieletowa 230, t/c = 12%) przeskalowane do c = 200 mm."
    elif "WORTMANN" in upper or "FX 61" in upper or "FX61" in upper:
        coords = wortmann_fx61_163_coords()
        note = "Rzędne laminarnego profilu szybowcowego Wortmann FX 61-163 (t/c = 16.3%) przeskalowane do c = 200 mm."
    elif "NASA SC" in upper or "SC(2)" in upper or "SC2" in upper:
        coords = nasa_sc2_0412_coords()
        note = "Rzędne profilu nadkrytycznego NASA SC(2)-0412 (t/c = 12%) przeskalowane do c = 200 mm."
    elif "NACA 2412" in upper:
        coords = naca_4digit_coords(0.02, 0.4, 0.12)
        note = "Rzędne profilu NACA 2412 (m = 2%, p = 40%, t/c = 12%) przeskalowane do c = 200 mm."
    elif "NACA 2415" in upper:
        coords = naca_4digit_coords(0.02, 0.4, 0.15)
        note = "Rzędne profilu NACA 2415 (m = 2%, p = 40%, t/c = 15%) przeskalowane do c = 200 mm."
    elif "NACA 4412" in upper:
        coords = naca_4digit_coords(0.04, 0.4, 0.12)
        note = "Rzędne profilu NACA 4412 (m = 4%, p = 40%, t/c = 12%) przeskalowane do c = 200 mm."
    elif "0012" in upper:
        coords = naca_4digit_coords(0.0, 0.0, 0.12)
        note = "Rzędne symetrycznego profilu NACA 0012 (t/c = 12%) przeskalowane do c = 200 mm."
    else:
        # Domyślnie profil NACA 4-cyfrowy dopasowany do zadanego tc_ratio
        t = max(0.06, min(0.24, float(tc_ratio or 0.12)))
        coords = naca_4digit_coords(0.02, 0.4, t)
        note = f"Rzędne profilu NACA 24{int(t*100):02d} (t/c = {t*100:.1f}%) przeskalowane do c = 200 mm."

    return coords, note


def generate_airfoil_svg(coords: List[Dict], c_mm: float = 200.0) -> str:
    """
    Generuje wektorowy rysunek SVG profilu 200 mm z siatką milimetrową i osiami,
    gotowy do osadzenia w raporcie P3 lub wydruku A4.
    """
    if not coords:
        return ""

    width_px = 640
    height_px = 220
    margin_x = 40
    margin_y = 40
    plot_w = width_px - 2 * margin_x
    plot_h = height_px - 2 * margin_y

    # Max grubość dla skali
    y_max = max(pt["y_upper_mm"] for pt in coords)
    y_min = min(pt["y_lower_mm"] for pt in coords)
    y_span = max(30.0, (y_max - y_min) * 1.3)
    y_mid = (y_max + y_min) / 2.0

    def to_svg_x(x_mm):
        return margin_x + (x_mm / c_mm) * plot_w

    def to_svg_y(y_mm):
        return margin_y + (plot_h / 2.0) - ((y_mm - y_mid) / y_span) * plot_h

    # Path górny i dolny
    pts_upper = [f"{to_svg_x(pt['x_mm']):.1f},{to_svg_y(pt['y_upper_mm']):.1f}" for pt in coords]
    pts_lower = [f"{to_svg_x(pt['x_mm']):.1f},{to_svg_y(pt['y_lower_mm']):.1f}" for pt in reversed(coords)]
    full_path = "M " + " L ".join(pts_upper + pts_lower) + " Z"

    # Linia szkieletowa (camber line)
    camber_pts = [f"{to_svg_x(pt['x_mm']):.1f},{to_svg_y((pt['y_upper_mm'] + pt['y_lower_mm'])/2.0):.1f}" for pt in coords]
    camber_path = "M " + " L ".join(camber_pts)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width_px} {height_px}" class="airfoil-200mm-svg" style="width:100%; max-width:680px; height:auto; background:#ffffff; border:1px solid #dce6e8; border-radius:6px;">',
        f'<defs>',
        f'<pattern id="mm_grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="#f1f5f9" stroke-width="0.8"/></pattern>',
        f'</defs>',
        f'<rect width="{width_px}" height="{height_px}" fill="url(#mm_grid)" />',
        # Oś cięciwy
        f'<line x1="{margin_x - 10}" y1="{to_svg_y(0.0):.1f}" x2="{margin_x + plot_w + 10}" y2="{to_svg_y(0.0):.1f}" stroke="#94a3b8" stroke-width="1" stroke-dasharray="4,4" />',
        # Profil
        f'<path d="{full_path}" fill="rgba(2, 132, 199, 0.08)" stroke="#0369a1" stroke-width="2" />',
        # Linia szkieletowa
        f'<path d="{camber_path}" fill="none" stroke="#d97706" stroke-width="1.2" stroke-dasharray="3,3" />',
        # Oznaczenia
        f'<text x="{margin_x}" y="{height_px - 10}" font-size="10" font-family="sans-serif" fill="#64748b">x = 0 mm</text>',
        f'<text x="{margin_x + plot_w}" y="{height_px - 10}" font-size="10" font-family="sans-serif" fill="#64748b" text-anchor="end">x = {c_mm:.0f} mm</text>',
        f'<text x="{width_px / 2}" y="22" font-size="11" font-weight="bold" font-family="sans-serif" fill="#1e293b" text-anchor="middle">Rysunek profilu skrzydła przeskalowanego do cięciwy c = 200 mm</text>',
        f'</svg>'
    ]

    return "".join(svg)

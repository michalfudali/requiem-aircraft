"""
Moduł integracji z programem NASA OpenVSP (Open Vehicle Sketch Pad).
Wykorzystuje wyłącznie oficjalne API Python OpenVSP (`openvsp`).

Realizuje:
1. Parametryczną budowę modelu 3D samolotu w jądrze OpenVSP (`AddGeom`, `SetParmVal`,
   `ChangeXSecShape`, `SplitWingXSec`, `AddSubSurf`, `Update`):
   - Skrzydło główne (trapezowe, prostokątne, prostokątno-trapezowe, eliptyczne, skośne)
     wraz z wybranym profilem z rzędnych lub oznaczenia NACA obsługiwanego w P3
     oraz powierzchniami sterowymi i mechanizacją (`SS_CONTROL`: klapy, lotki, sloty),
   - Kadłub przekrojowy (`FUSELAGE` z wieloma przekrojami `XSec`),
   - Usterzenie poziome i pionowe lub motylkowe V-tail (wraz ze sterem wysokości i kierunku),
   - Gondole silnikowe (`POD`) oraz śmigła (`PROP`).
2. Analizy inżynierskie przez natywny menedżer analiz OpenVSP (`ExecAnalysis`):
   - `CompGeom`: dokładne powierzchnie omywane, objętości i przenikania brył 3D,
   - `MassProp`: masa całkowita, środek ciężkości 3D (CG) oraz tensor bezwładności (Ixx, Iyy, Izz),
   - `ParasiteDrag`: opór profilowy i szkodliwy $C_{D0}$ metodą współczynników kształtu i tarcia,
   - `VSPAeroComputeGeometry` + `VSPAEROSweep`: obliczenia metodą siatki wirowej (VLM) lub panelową
     (biegunowa $C_L(\alpha)$, $C_{Di}$, doskonałość $L/D$, punkt neutralny $X_{NP}$, pochodne stateczności),
   - `Projection` oraz `WaveDrag`: rzuty powierzchni czołowej i opór falowy reguły pól.
3. Eksport i import natywnych plików `.vsp3` oraz formatów CAD/CAE (`WriteVSPFile`, `ReadVSPFile`,
   `ExportFile`: STEP, IGES, STL, OBJ, DXF, GMSH, XSEC).
"""
from __future__ import annotations

import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class OpenVSPNotAvailableError(RuntimeError):
    """Wyjątek zgłaszany, gdy natywny pakiet Python `openvsp` nie jest zainstalowany w środowisku."""


class OpenVSPAPIError(RuntimeError):
    """Wyjątek zgłaszany, gdy wywołanie funkcji w API OpenVSP zwróci błąd w ErrorMgr."""


def _load_vsp(vsp_module: Any = None) -> Any:
    """Zwraca przekazany moduł API lub importuje oficjalny pakiet `openvsp`."""
    if vsp_module is not None:
        return vsp_module
    try:
        import openvsp as vsp  # type: ignore[import-untyped]
        return vsp
    except ImportError as exc:
        raise OpenVSPNotAvailableError(
            "Pakiet Python `openvsp` nie jest dostępny w bieżącym środowisku Pythona. "
            "Zainstaluj oficjalne API OpenVSP (NASA OpenVSP Python API), aby korzystać z tego modułu."
        ) from exc


def check_openvsp_availability(vsp_module: Any = None) -> Dict[str, Any]:
    """Sprawdza dostępność biblioteki OpenVSP API i przeprowadza kontrolę `VSPCheckSetup`."""
    try:
        vsp = _load_vsp(vsp_module)
        vsp.VSPCheckSetup()
        version = getattr(vsp, "GetVSPVersion", lambda: "OpenVSP API")()
        return {
            "available": True,
            "version": str(version),
            "error": None,
        }
    except Exception as exc:
        return {
            "available": False,
            "version": None,
            "error": str(exc),
        }


def _check_vsp_errors(vsp: Any, context: str = "") -> List[str]:
    """Odczytuje i czyści stos błędów z `ErrorMgrSingleton` w API OpenVSP."""
    errors: List[str] = []
    if not hasattr(vsp, "ErrorMgrSingleton"):
        return errors
    err_mgr = vsp.ErrorMgrSingleton.getInstance()
    while err_mgr.GetNumTotalErrors() > 0:
        err = err_mgr.PopLastError()
        msg = err.GetErrorString() if hasattr(err, "GetErrorString") else str(err)
        if msg:
            errors.append(f"{context}: {msg}" if context else msg)
    return errors


def _set_parm(vsp: Any, geom_id: str, name: str, group: str, value: float) -> float:
    """Ustawia wartość parametru w API OpenVSP za pomocą `SetParmVal(geom_id, name, group, val)`."""
    val = float(value)
    res = vsp.SetParmVal(geom_id, name, group, val)
    _check_vsp_errors(vsp, f"SetParmVal({geom_id}, {name}, {group}, {val})")
    return float(res) if res is not None else val


def _configure_wing_airfoils(
    vsp: Any,
    wing_id: str,
    airfoil_name: str,
    tc_ratio: float,
    airfoil_file_path: Optional[str] = None,
    coordinates: str = '',
    profile_source: str = '',
) -> Dict[str, Any]:
    """Konfiguruje profile przekrojów skrzydła (`XSecCurve`) wyłącznie przez API OpenVSP."""
    xsec_surf = vsp.GetXSecSurf(wing_id, 0)
    num_xsecs = int(vsp.GetNumXSec(xsec_surf))
    from calculations.vsp_airfoils import resolve_wing_airfoil, set_coordinate_airfoil
    if airfoil_file_path and not os.path.isfile(airfoil_file_path):
        raise ValueError('Nie znaleziono wskazanego pliku rzędnych profilu OpenVSP.')
    profile, info = (None, dict(mode='FILE_AIRFOIL', assumed=False, source=os.path.basename(airfoil_file_path),
                               tc_ratio=None, warnings=[])) if airfoil_file_path else resolve_wing_airfoil(
        dict(airfoil=airfoil_name, airfoil_coordinates=coordinates, airfoil_source=profile_source), tc_ratio)

    for i in range(num_xsecs):
        if airfoil_file_path and os.path.isfile(airfoil_file_path):
            vsp.ChangeXSecShape(xsec_surf, i, vsp.XS_FILE_AIRFOIL)
            xsec_id = vsp.GetXSec(xsec_surf, i)
            vsp.ReadFileAirfoil(xsec_id, airfoil_file_path)
            errors = _check_vsp_errors(vsp, 'ReadFileAirfoil')
            if errors:
                raise OpenVSPAPIError('; '.join(errors))
        elif profile is not None:
            set_coordinate_airfoil(vsp, xsec_surf, i, profile)
        else:
            vsp.ChangeXSecShape(xsec_surf, i, vsp.XS_FOUR_SERIES)
            xsec_id = vsp.GetXSec(xsec_surf, i)
            camber, camber_loc, thick = 0.02, 0.40, tc_ratio
            vsp.SetParmVal(vsp.GetXSecParm(xsec_id, "Camber"), camber)
            vsp.SetParmVal(vsp.GetXSecParm(xsec_id, "CamberLoc"), camber_loc)
            vsp.SetParmVal(vsp.GetXSecParm(xsec_id, "ThickChord"), thick)

    return dict(info, num_xsecs=num_xsecs)


def _build_main_wing(
    vsp: Any,
    geom_res: Dict[str, Any],
    balance_res: Optional[Dict[str, Any]],
    params: Dict[str, Any],
    airfoil_file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Buduje skrzydło główne wraz z obrysem, profilami i powierzchniami sterowymi w API OpenVSP."""
    wing_data = geom_res.get("wing", {})
    fus_data = geom_res.get("fuselage", {})

    wing_id = vsp.AddGeom("WING", "")
    vsp.SetGeomName(wing_id, "Skrzydlo_Glowne")
    _set_parm(vsp, wing_id, "Sym_Planar_Flag", "Sym", vsp.SYM_XZ)

    # Pozycjonowanie skrzydła względem kadłuba
    fus_diam = float(fus_data.get("diameter", 1.25))
    fus_len = float(fus_data.get("length", 8.0))
    wing_config = str(wing_data.get("wing_config", params.get("wing_config", "low")))
    z_offset = (
        0.38 * fus_diam if wing_config == "high"
        else (-0.35 * fus_diam if wing_config == "low" else 0.0)
    )
    x_lemac = float(
        (balance_res or {}).get("x_lemac_m")
        or (0.32 * fus_len)
    )
    x_root = max(0.05 * fus_len, x_lemac - float(wing_data.get("x_le_mac", 0.0)))
    incidence_deg = float(params.get("wing_incidence_deg", 2.0))

    _set_parm(vsp, wing_id, "X_Rel_Location", "XForm", x_root)
    _set_parm(vsp, wing_id, "Y_Rel_Location", "XForm", 0.0)
    _set_parm(vsp, wing_id, "Z_Rel_Location", "XForm", z_offset)
    _set_parm(vsp, wing_id, "Y_Rel_Rotation", "XForm", incidence_deg)

    b = float(wing_data.get("b", 10.0))
    cr = float(wing_data.get("cr", 1.5))
    ct = float(wing_data.get("ct", 0.9))
    tc_ratio = float(wing_data.get("tc_ratio", params.get("tc_ratio", 0.12)))
    planform = str(params.get("wing_planform") or wing_data.get("planform") or wing_data.get("wing_planform") or "trapezoidal")

    from calculations.vsp_wing import configure_projected_wing
    planform_info = configure_projected_wing(vsp, wing_id, wing_data, params)

    airfoil_info = _configure_wing_airfoils(
        vsp,
        wing_id,
        str(params.get("airfoil") or ''),
        tc_ratio,
        airfoil_file_path=airfoil_file_path,
        coordinates=params.get('airfoil_coordinates') or '',
        profile_source=params.get('airfoil_source') or '',
    )

    # Powierzchnie sterowe i mechanizacja (SubSurfaces: SS_CONTROL)
    cs = geom_res.get("control_surfaces", {})
    subsurfaces: Dict[str, str] = {}

    flaps = cs.get("flaps", {})
    if flaps.get("type", "none") != "none" and float(flaps.get("bf_over_b", 0.0)) > 0.01:
        flap_ss_id = vsp.AddSubSurf(wing_id, vsp.SS_CONTROL, 0)
        vsp.SetSubSurfName(wing_id, flap_ss_id, "Klapa_Zaskrzydlowa")
        _set_parm(vsp, wing_id, "EtaFlag", f"SS_Control_{len(subsurfaces) + 1}", 1.0)
        _set_parm(vsp, wing_id, "UStart", f"SS_Control_{len(subsurfaces) + 1}", max(0.05, float(flaps.get("eta_in", 0.12))))
        _set_parm(vsp, wing_id, "UEnd", f"SS_Control_{len(subsurfaces) + 1}", min(0.95, float(flaps.get("eta_out", 0.65))))
        _set_parm(vsp, wing_id, "Length_C_Start", f"SS_Control_{len(subsurfaces) + 1}", float(flaps.get("cf_over_c", 0.25)))
        _set_parm(vsp, wing_id, "LE_Flag", f"SS_Control_{len(subsurfaces) + 1}", 0.0)
        subsurfaces["flap"] = flap_ss_id

    ailerons = cs.get("ailerons", {})
    if not cs.get("is_flaperon", False) and float(ailerons.get("ba_over_b", 0.0)) > 0.01:
        ail_ss_id = vsp.AddSubSurf(wing_id, vsp.SS_CONTROL, 0)
        idx = len(subsurfaces) + 1
        vsp.SetSubSurfName(wing_id, ail_ss_id, "Lotka")
        _set_parm(vsp, wing_id, "EtaFlag", f"SS_Control_{idx}", 1.0)
        _set_parm(vsp, wing_id, "UStart", f"SS_Control_{idx}", max(0.10, float(ailerons.get("eta_in", 0.68))))
        _set_parm(vsp, wing_id, "UEnd", f"SS_Control_{idx}", min(0.98, float(ailerons.get("eta_out", 0.95))))
        _set_parm(vsp, wing_id, "Length_C_Start", f"SS_Control_{idx}", float(ailerons.get("ca_over_c", 0.22)))
        _set_parm(vsp, wing_id, "LE_Flag", f"SS_Control_{idx}", 0.0)
        subsurfaces["aileron"] = ail_ss_id

    slats = cs.get("slats", {})
    if slats.get("type", "none") != "none" and float(slats.get("s_equipped_over_s", 0.0)) > 0.01:
        slat_ss_id = vsp.AddSubSurf(wing_id, vsp.SS_CONTROL, 0)
        idx = len(subsurfaces) + 1
        vsp.SetSubSurfName(wing_id, slat_ss_id, "Przedskrzydlo_Slat")
        _set_parm(vsp, wing_id, "LE_Flag", f"SS_Control_{idx}", 1.0)
        _set_parm(vsp, wing_id, "Length_C_Start", f"SS_Control_{idx}", 0.15)
        subsurfaces["slat"] = slat_ss_id

    num_sections = max(1, int(vsp.GetNumXSec(vsp.GetXSecSurf(wing_id, 0))) - 1)

    return {
        "geom_id": wing_id,
        "planform": planform,
        "num_sections": num_sections,
        "span_m": b,
        "planform_geometry": planform_info,
        "root_chord_m": cr,
        "tip_chord_m": ct,
        "x_root_m": x_root,
        "z_offset_m": z_offset,
        "airfoil": airfoil_info,
        "subsurfaces": subsurfaces,
    }


def _build_fuselage(vsp: Any, geom_res: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Buduje bryłę kadłuba (`FUSELAGE`) wraz z przekrojami `XSec` przez API OpenVSP."""
    fus_data = geom_res.get("fuselage", {})
    fus_len = float(fus_data.get("length", 8.0))
    fus_diam = float(fus_data.get("diameter", 1.25))

    cargo_bay = fus_data.get("cargo_bay")
    if cargo_bay:
        width = max(fus_diam, float(cargo_bay.get("width_m", fus_diam)) + 0.20)
        height = max(fus_diam * 0.9, float(cargo_bay.get("height_m", fus_diam)) + 0.20)
    else:
        width = fus_diam
        height = fus_diam * 1.05

    fus_id = vsp.AddGeom("FUSELAGE", "")
    vsp.SetGeomName(fus_id, "Kadlub")
    _set_parm(vsp, fus_id, "Length", "Design", fus_len)

    xsec_surf = vsp.GetXSecSurf(fus_id, 0)
    num_xsecs = int(vsp.GetNumXSec(xsec_surf))
    # Domyślny kadłub OpenVSP posiada 5 przekrojów:
    # 0 (nos - punkt), 1 (przednia część kabiny), 2 (środek kabiny), 3 (część ogonowa), 4 (ogon - punkt)
    station_scales = [0.0, 0.78, 1.00, 0.62, 0.0]
    for i in range(num_xsecs):
        scale = station_scales[i] if i < len(station_scales) else (0.0 if i == num_xsecs - 1 else 0.8)
        if scale > 0.0:
            vsp.ChangeXSecShape(xsec_surf, i, vsp.XS_ELLIPSE)
            xsec_id = vsp.GetXSec(xsec_surf, i)
            w_parm = vsp.GetXSecParm(xsec_id, "Ellipse_Width")
            h_parm = vsp.GetXSecParm(xsec_id, "Ellipse_Height")
            if w_parm:
                vsp.SetParmVal(w_parm, width * scale)
            if h_parm:
                vsp.SetParmVal(h_parm, height * scale)

    return {
        "geom_id": fus_id,
        "length_m": fus_len,
        "width_m": width,
        "height_m": height,
        "num_xsecs": num_xsecs,
    }


def _build_empennage(
    vsp: Any,
    geom_res: Dict[str, Any],
    params: Dict[str, Any],
    fuselage_id: str,
) -> Dict[str, Any]:
    """Buduje usterzenie poziome i pionowe (lub motylkowe V-tail) w API OpenVSP."""
    ht_data = geom_res.get("horizontal_tail", {})
    vt_data = geom_res.get("vertical_tail", {})
    fus_data = geom_res.get("fuselage", {})
    fus_len = float(fus_data.get("length", 8.0))
    fus_diam = float(fus_data.get("diameter", 1.25))

    empennage_type = str(params.get("empennage_type") or params.get("tail_type") or "conventional")

    # Usterzenie poziome
    ht_id = vsp.AddGeom("WING", fuselage_id)
    vsp.SetGeomName(ht_id, "Usterzenie_Poziome")
    _set_parm(vsp, ht_id, "Sym_Planar_Flag", "Sym", vsp.SYM_XZ)

    b_h = float(ht_data.get("b_h", 3.2))
    cr_h = float(ht_data.get("cr_h", 0.9))
    ct_h = float(ht_data.get("ct_h", 0.55))
    x_ht = max(0.5 * fus_len, float(ht_data.get("x_ac_m", 0.90 * fus_len)) - 0.25 * float(ht_data.get("mac_h", cr_h)))
    h_v = float(vt_data.get("h_v", 1.4))
    z_ht = 0.92 * h_v if empennage_type == "t_tail" else 0.12 * fus_diam
    dihedral_h = 35.0 if empennage_type == "v_tail" else 0.0

    _set_parm(vsp, ht_id, "X_Rel_Location", "XForm", x_ht)
    _set_parm(vsp, ht_id, "Z_Rel_Location", "XForm", z_ht)
    _set_parm(vsp, ht_id, "Span", "XSec_1", b_h / 2.0)
    _set_parm(vsp, ht_id, "Root_Chord", "XSec_1", cr_h)
    _set_parm(vsp, ht_id, "Tip_Chord", "XSec_1", ct_h)
    _set_parm(vsp, ht_id, "Sweep", "XSec_1", 8.0)
    _set_parm(vsp, ht_id, "Sweep_Location", "XSec_1", 0.25)
    _set_parm(vsp, ht_id, "Dihedral", "XSec_1", dihedral_h)
    _configure_wing_airfoils(vsp, ht_id, "NACA 0009", 0.09)

    ce_over_ch = float(ht_data.get("ce_over_ch", 0.35))
    elev_ss_id = vsp.AddSubSurf(ht_id, vsp.SS_CONTROL, 0)
    vsp.SetSubSurfName(ht_id, elev_ss_id, "Ster_Wysokosci")
    _set_parm(vsp, ht_id, "EtaFlag", "SS_Control_1", 1.0)
    _set_parm(vsp, ht_id, "UStart", "SS_Control_1", 0.10)
    _set_parm(vsp, ht_id, "UEnd", "SS_Control_1", 0.95)
    _set_parm(vsp, ht_id, "Length_C_Start", "SS_Control_1", ce_over_ch)

    result: Dict[str, Any] = {
        "empennage_type": empennage_type,
        "tail_type": empennage_type,
        "horizontal_tail_id": ht_id,
        "vertical_tail_id": None,
    }

    if empennage_type != "v_tail":
        vt_id = vsp.AddGeom("WING", fuselage_id)
        vsp.SetGeomName(vt_id, "Usterzenie_Pionowe")
        is_twin_tail = empennage_type in ("twin_tail", "h_tail")
        _set_parm(vsp, vt_id, "Sym_Planar_Flag", "Sym", vsp.SYM_XZ if is_twin_tail else vsp.SYM_NONE)

        cr_v = float(vt_data.get("cr_v", 1.1))
        ct_v = float(vt_data.get("ct_v", 0.65))
        x_vt = max(0.5 * fus_len, float(vt_data.get("x_ac_m", 0.90 * fus_len)) - 0.25 * float(vt_data.get("mac_v", cr_v)))
        y_vt = (b_h / 2.0) if is_twin_tail else 0.0

        _set_parm(vsp, vt_id, "X_Rel_Location", "XForm", x_vt)
        _set_parm(vsp, vt_id, "Y_Rel_Location", "XForm", y_vt)
        _set_parm(vsp, vt_id, "Z_Rel_Location", "XForm", 0.15 * fus_diam)
        _set_parm(vsp, vt_id, "X_Rel_Rotation", "XForm", 90.0)
        _set_parm(vsp, vt_id, "Span", "XSec_1", h_v)
        _set_parm(vsp, vt_id, "Root_Chord", "XSec_1", cr_v)
        _set_parm(vsp, vt_id, "Tip_Chord", "XSec_1", ct_v)
        _set_parm(vsp, vt_id, "Sweep", "XSec_1", 22.0)
        _set_parm(vsp, vt_id, "Sweep_Location", "XSec_1", 0.25)
        _configure_wing_airfoils(vsp, vt_id, "NACA 0009", 0.09)

        cr_over_cv = float(vt_data.get("cr_over_cv", 0.35))
        rud_ss_id = vsp.AddSubSurf(vt_id, vsp.SS_CONTROL, 0)
        vsp.SetSubSurfName(vt_id, rud_ss_id, "Ster_Kierunku")
        _set_parm(vsp, vt_id, "EtaFlag", "SS_Control_1", 1.0)
        _set_parm(vsp, vt_id, "UStart", "SS_Control_1", 0.10)
        _set_parm(vsp, vt_id, "UEnd", "SS_Control_1", 0.92)
        _set_parm(vsp, vt_id, "Length_C_Start", "SS_Control_1", cr_over_cv)
        result["vertical_tail_id"] = vt_id

    return result


def _build_propulsion(
    vsp: Any,
    geom_res: Dict[str, Any],
    params: Dict[str, Any],
    fuselage_id: str,
) -> Dict[str, Any]:
    """Buduje gondole silnikowe (`POD`) oraz śmigła (`PROP`) w API OpenVSP."""
    engine_type = str(params.get("engine_type", "piston"))
    if engine_type == "none" or params.get("aircraft_type") == "glider":
        return {"engine_type": "none", "pod_id": None, "prop_id": None}

    wing_data = geom_res.get("wing", {})
    fus_data = geom_res.get("fuselage", {})
    b = float(wing_data.get("b", 10.0))
    fus_len = float(fus_data.get("length", 8.0))
    fus_diam = float(fus_data.get("diameter", 1.25))
    n_engines = max(1, int(params.get("n_engines", 1)))
    engine_loc = str(params.get("engine_location", "nose"))

    pod_id = None
    prop_id = None

    if n_engines >= 2 or engine_loc in ("wing", "rear"):
        pod_id = vsp.AddGeom("POD", fuselage_id)
        vsp.SetGeomName(pod_id, "Gondola_Silnika")
        is_symmetric = n_engines >= 2
        _set_parm(vsp, pod_id, "Sym_Planar_Flag", "Sym", vsp.SYM_XZ if is_symmetric else vsp.SYM_NONE)

        pod_len = max(1.2, 0.18 * fus_len)
        _set_parm(vsp, pod_id, "Length", "Design", pod_len)
        _set_parm(vsp, pod_id, "FineRatio", "Design", 4.5)

        x_pod = 0.68 * fus_len if engine_loc == "rear" else 0.28 * fus_len
        y_pod = (0.26 * (b / 2.0) if engine_loc != "rear" else 0.65 * fus_diam) if is_symmetric else 0.0
        z_pod = 0.25 * fus_diam if engine_loc == "rear" else -0.10 * fus_diam
        _set_parm(vsp, pod_id, "X_Rel_Location", "XForm", x_pod)
        _set_parm(vsp, pod_id, "Y_Rel_Location", "XForm", y_pod)
        _set_parm(vsp, pod_id, "Z_Rel_Location", "XForm", z_pod)

    if engine_type in ("piston", "turboprop", "electric"):
        prop_id = vsp.AddGeom("PROP", fuselage_id)
        vsp.SetGeomName(prop_id, "Smiglo")
        is_symmetric = n_engines >= 2
        _set_parm(vsp, prop_id, "Sym_Planar_Flag", "Sym", vsp.SYM_XZ if is_symmetric else vsp.SYM_NONE)

        prop_diam = float(params.get("propeller_diameter_m") or geom_res.get('propeller',{}).get('diameter_m')
                          or max(1.5, 0.17 * b))
        n_blades = int(params.get("propeller_blades", 3 if engine_type == "turboprop" else 2))
        _set_parm(vsp, prop_id, "Diameter", "Design", prop_diam)
        _set_parm(vsp, prop_id, "NumBlade", "Design", n_blades)

        x_prop = 0.02 * fus_len if engine_loc == "nose" and not is_symmetric else 0.27 * fus_len
        y_prop = (0.26 * (b / 2.0)) if is_symmetric else 0.0
        _set_parm(vsp, prop_id, "X_Rel_Location", "XForm", x_prop)
        _set_parm(vsp, prop_id, "Y_Rel_Location", "XForm", y_prop)

    return {
        "engine_type": engine_type,
        "n_engines": n_engines,
        "pod_id": pod_id,
        "prop_id": prop_id,
    }


def build_vsp_aircraft_model(
    project_results: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None,
    airfoil_file_path: Optional[str] = None,
    vsp_module: Any = None,
) -> Dict[str, Any]:
    """
    Buduje kompletny parametryczny model 3D samolotu w pamięci OpenVSP
    wyłącznie za pomocą wywołań oficjalnego API `openvsp`.
    """
    vsp = _load_vsp(vsp_module)
    vsp.VSPCheckSetup()
    effective_params = dict(params or project_results.get("params") or project_results.get("inputs") or {})
    from calculations.vsp_airfoils import resolve_wing_airfoil
    if airfoil_file_path:
        if not os.path.isfile(airfoil_file_path):
            raise ValueError('Nie znaleziono wskazanego pliku rzędnych profilu OpenVSP.')
    else:
        resolve_wing_airfoil(effective_params, project_results.get('geometry', {}).get('wing', {}).get('tc_ratio', .12))
    from calculations.vsp_wing import projected_wing_stations
    projected_wing_stations(project_results['geometry']['wing'], effective_params)
    vsp.VSPRenew()
    vsp.ClearVSPModel()

    geom_res = project_results.get("geometry", {})
    balance_res = project_results.get("balance", {})

    vehicle_name = str(effective_params.get("name", "Samolot_BIPOL"))
    if hasattr(vsp, "SetVehicleName"):
        vsp.SetVehicleName(vehicle_name)

    fuselage_info = _build_fuselage(vsp, geom_res, effective_params)
    wing_info = _build_main_wing(
        vsp,
        geom_res,
        balance_res,
        effective_params,
        airfoil_file_path=airfoil_file_path,
    )
    empennage_info = _build_empennage(
        vsp,
        geom_res,
        effective_params,
        fuselage_id=fuselage_info["geom_id"],
    )
    propulsion_info = _build_propulsion(
        vsp,
        geom_res,
        effective_params,
        fuselage_id=fuselage_info["geom_id"],
    )

    vsp.Update()
    errors = _check_vsp_errors(vsp, "build_vsp_aircraft_model")
    if errors:
        raise OpenVSPAPIError("; ".join(errors))

    all_geoms = list(vsp.FindGeoms()) if hasattr(vsp, "FindGeoms") else []

    return {
        "vehicle_name": vehicle_name,
        "geom_ids": all_geoms,
        "fuselage": fuselage_info,
        "wing": wing_info,
        "empennage": empennage_info,
        "propulsion": propulsion_info,
    }


def run_vsp_comp_geom(
    half_mesh: bool = False,
    subsurf_flag: bool = True,
    vsp_module: Any = None,
) -> Dict[str, Any]:
    """
    Uruchamia analizę geometryczną `CompGeom` przez menedżer analiz OpenVSP (`ExecAnalysis`).
    Wyznacza dokładne powierzchnie omywane 3D ($S_{wet}$), powierzchnie teoretyczne oraz objętości
    z uwzględnieniem przenikania brył (kadłub-skrzydło-usterzenie).
    """
    vsp = _load_vsp(vsp_module)
    analysis_name = "CompGeom"
    vsp.SetAnalysisInputDefaults(analysis_name)
    vsp.SetIntAnalysisInput(analysis_name, "HalfMeshFlag", [1 if half_mesh else 0], 0)
    vsp.SetIntAnalysisInput(analysis_name, "SubsurfFlag", [1 if subsurf_flag else 0], 0)

    res_id = vsp.ExecAnalysis(analysis_name)
    errors = _check_vsp_errors(vsp, "ExecAnalysis(CompGeom)")
    if errors:
        raise OpenVSPAPIError("; ".join(errors))

    comp_names = list(vsp.GetStringResults(res_id, "comp_name", 0))
    theo_areas = list(vsp.GetDoubleResults(res_id, "theo_area", 0))
    wet_areas = list(vsp.GetDoubleResults(res_id, "wet_area", 0))
    theo_vols = list(vsp.GetDoubleResults(res_id, "theo_vol", 0))
    wet_vols = list(vsp.GetDoubleResults(res_id, "wet_vol", 0))

    # Usuwamy tymczasową siatkę wygenerowaną przez CompGeom, aby model pozostał czysty
    mesh_geom_ids = list(vsp.GetStringResults(res_id, "Mesh_GeomID", 0))
    if mesh_geom_ids and hasattr(vsp, "DeleteGeomVec"):
        vsp.DeleteGeomVec(mesh_geom_ids)

    components = []
    for idx, name in enumerate(comp_names):
        components.append({
            "name": str(name),
            "theo_area_m2": float(theo_areas[idx]) if idx < len(theo_areas) else 0.0,
            "wet_area_m2": float(wet_areas[idx]) if idx < len(wet_areas) else 0.0,
            "theo_vol_m3": float(theo_vols[idx]) if idx < len(theo_vols) else 0.0,
            "wet_vol_m3": float(wet_vols[idx]) if idx < len(wet_vols) else 0.0,
        })

    total_wet_area = sum(c["wet_area_m2"] for c in components)
    total_wet_vol = sum(c["wet_vol_m3"] for c in components)

    return {
        "analysis": analysis_name,
        "result_id": res_id,
        "total_wet_area_m2": round(total_wet_area, 4),
        "total_wet_vol_m3": round(total_wet_vol, 4),
        "components": components,
    }


def run_vsp_mass_properties(
    num_slices: int = 50,
    vsp_module: Any = None,
) -> Dict[str, Any]:
    """
    Uruchamia analizę masowo-bezwładnościową `MassProp` przez `ExecAnalysis("MassProp")`.
    Wyznacza masę całkowitą, środek ciężkości 3D oraz składowe tensora bezwładności.
    """
    vsp = _load_vsp(vsp_module)
    analysis_name = "MassProp"
    vsp.SetAnalysisInputDefaults(analysis_name)
    vsp.SetIntAnalysisInput(analysis_name, "NumSlices", [max(10, int(num_slices))], 0)

    res_id = vsp.ExecAnalysis(analysis_name)
    errors = _check_vsp_errors(vsp, "ExecAnalysis(MassProp)")
    if errors:
        raise OpenVSPAPIError("; ".join(errors))

    total_mass_res = list(vsp.GetDoubleResults(res_id, "Total_Mass", 0))
    ixx_res = list(vsp.GetDoubleResults(res_id, "Total_Ixx", 0))
    iyy_res = list(vsp.GetDoubleResults(res_id, "Total_Iyy", 0))
    izz_res = list(vsp.GetDoubleResults(res_id, "Total_Izz", 0))
    cg_vec_res = list(vsp.GetVec3dResults(res_id, "Total_CG", 0)) if hasattr(vsp, "GetVec3dResults") else []

    if cg_vec_res and hasattr(cg_vec_res[0], "x"):
        cg = (float(cg_vec_res[0].x()), float(cg_vec_res[0].y()), float(cg_vec_res[0].z()))
    else:
        cg_x = list(vsp.GetDoubleResults(res_id, "Total_CGx", 0))
        cg_y = list(vsp.GetDoubleResults(res_id, "Total_CGy", 0))
        cg_z = list(vsp.GetDoubleResults(res_id, "Total_CGz", 0))
        cg = (
            float(cg_x[0]) if cg_x else 0.0,
            float(cg_y[0]) if cg_y else 0.0,
            float(cg_z[0]) if cg_z else 0.0,
        )

    mesh_geom_ids = list(vsp.GetStringResults(res_id, "Mesh_GeomID", 0))
    if mesh_geom_ids and hasattr(vsp, "DeleteGeomVec"):
        vsp.DeleteGeomVec(mesh_geom_ids)

    return {
        "analysis": analysis_name,
        "result_id": res_id,
        "total_mass": float(total_mass_res[0]) if total_mass_res else 0.0,
        "cg_m": {"x": cg[0], "y": cg[1], "z": cg[2]},
        "inertia": {
            "Ixx": float(ixx_res[0]) if ixx_res else 0.0,
            "Iyy": float(iyy_res[0]) if iyy_res else 0.0,
            "Izz": float(izz_res[0]) if izz_res else 0.0,
        },
    }


def run_vsp_parasite_drag(
    s_ref_m2: float,
    v_inf_ms: float = 65.0,
    altitude_m: float = 2000.0,
    vsp_module: Any = None,
) -> Dict[str, Any]:
    """
    Uruchamia analizę oporu szkodliwego `ParasiteDrag` przez `ExecAnalysis("ParasiteDrag")`.
    Wyznacza opór tarcia i współczynniki kształtu wszystkich komponentów w modelu OpenVSP.
    """
    vsp = _load_vsp(vsp_module)
    analysis_name = "ParasiteDrag"
    vsp.SetAnalysisInputDefaults(analysis_name)

    vsp.SetDoubleAnalysisInput(analysis_name, "Sref", [float(s_ref_m2)], 0)
    vsp.SetDoubleAnalysisInput(analysis_name, "Vinf", [float(v_inf_ms)], 0)
    vsp.SetDoubleAnalysisInput(analysis_name, "Alt", [float(altitude_m)], 0)

    res_id = vsp.ExecAnalysis(analysis_name)
    errors = _check_vsp_errors(vsp, "ExecAnalysis(ParasiteDrag)")
    if errors:
        raise OpenVSPAPIError("; ".join(errors))

    total_cd = list(vsp.GetDoubleResults(res_id, "Total_CD_Total", 0))
    comp_names = list(vsp.GetStringResults(res_id, "Comp_Name", 0))
    comp_swet = list(vsp.GetDoubleResults(res_id, "Comp_Swet", 0))
    comp_cf = list(vsp.GetDoubleResults(res_id, "Comp_Cf", 0))
    comp_ff = list(vsp.GetDoubleResults(res_id, "Comp_FF", 0))
    comp_cd = list(vsp.GetDoubleResults(res_id, "Comp_CD", 0))

    breakdown = []
    for idx, name in enumerate(comp_names):
        breakdown.append({
            "name": str(name),
            "swet_m2": float(comp_swet[idx]) if idx < len(comp_swet) else 0.0,
            "cf": float(comp_cf[idx]) if idx < len(comp_cf) else 0.0,
            "form_factor": float(comp_ff[idx]) if idx < len(comp_ff) else 1.0,
            "cd": float(comp_cd[idx]) if idx < len(comp_cd) else 0.0,
        })

    return {
        "analysis": analysis_name,
        "result_id": res_id,
        "s_ref_m2": float(s_ref_m2),
        "v_inf_ms": float(v_inf_ms),
        "altitude_m": float(altitude_m),
        "cd0_total": float(total_cd[0]) if total_cd else sum(c["cd"] for c in breakdown),
        "components": breakdown,
    }


def run_vsp_aero_analysis(
    s_ref_m2: float,
    b_ref_m: float,
    c_ref_m: float,
    x_cg_m: float,
    alpha_start_deg: float = -2.0,
    alpha_end_deg: float = 10.0,
    alpha_npts: int = 5,
    mach: float = 0.20,
    re_cref: float = 3.5e6,
    method: str = "vlm",
    vsp_module: Any = None,
) -> Dict[str, Any]:
    """
    Uruchamia solwer aerodynamiczny VSPAERO (`VSPAeroComputeGeometry` + `VSPAEROSweep`)
    przez natywne API OpenVSP.
    """
    vsp = _load_vsp(vsp_module)

    # Krok 1: Generacja siatki obliczeniowej VSPAeroComputeGeometry
    comp_geom_analysis = "VSPAeroComputeGeometry"
    vsp.SetAnalysisInputDefaults(comp_geom_analysis)
    analysis_method = (
        getattr(vsp, "PANEL", 1) if method.lower() == "panel"
        else getattr(vsp, "VORTEX_LATTICE", 0)
    )
    vsp.SetIntAnalysisInput(comp_geom_analysis, "AnalysisMethod", [int(analysis_method)], 0)
    comp_geom_res_id = vsp.ExecAnalysis(comp_geom_analysis)
    errors = _check_vsp_errors(vsp, "ExecAnalysis(VSPAeroComputeGeometry)")
    if errors:
        raise OpenVSPAPIError("; ".join(errors))

    # Krok 2: Obliczenie biegunowej w VSPAEROSweep
    sweep_analysis = "VSPAEROSweep"
    vsp.SetAnalysisInputDefaults(sweep_analysis)
    vsp.SetIntAnalysisInput(sweep_analysis, "AnalysisMethod", [int(analysis_method)], 0)
    vsp.SetIntAnalysisInput(sweep_analysis, "RefFlag", [0], 0)
    vsp.SetDoubleAnalysisInput(sweep_analysis, "Sref", [float(s_ref_m2)], 0)
    vsp.SetDoubleAnalysisInput(sweep_analysis, "bref", [float(b_ref_m)], 0)
    vsp.SetDoubleAnalysisInput(sweep_analysis, "cref", [float(c_ref_m)], 0)
    vsp.SetDoubleAnalysisInput(sweep_analysis, "X_cg", [float(x_cg_m)], 0)
    vsp.SetDoubleAnalysisInput(sweep_analysis, "Y_cg", [0.0], 0)
    vsp.SetDoubleAnalysisInput(sweep_analysis, "Z_cg", [0.0], 0)

    vsp.SetDoubleAnalysisInput(sweep_analysis, "AlphaStart", [float(alpha_start_deg)], 0)
    vsp.SetDoubleAnalysisInput(sweep_analysis, "AlphaEnd", [float(alpha_end_deg)], 0)
    vsp.SetIntAnalysisInput(sweep_analysis, "AlphaNpts", [max(1, int(alpha_npts))], 0)
    vsp.SetDoubleAnalysisInput(sweep_analysis, "MachStart", [float(mach)], 0)
    vsp.SetIntAnalysisInput(sweep_analysis, "MachNpts", [1], 0)
    vsp.SetDoubleAnalysisInput(sweep_analysis, "ReCref", [float(re_cref)], 0)

    sweep_res_id = vsp.ExecAnalysis(sweep_analysis)
    errors = _check_vsp_errors(vsp, "ExecAnalysis(VSPAEROSweep)")
    if errors:
        raise OpenVSPAPIError("; ".join(errors))

    polar_ids = list(vsp.GetStringResults(sweep_res_id, "ResultsVec", 0))
    polar_res_id = polar_ids[0] if polar_ids else sweep_res_id

    alphas = list(vsp.GetDoubleResults(polar_res_id, "Alpha", 0))
    cl_vals = list(vsp.GetDoubleResults(polar_res_id, "CL", 0))
    cdi_vals = list(vsp.GetDoubleResults(polar_res_id, "CDi", 0))
    cdo_vals = list(vsp.GetDoubleResults(polar_res_id, "CDo", 0))
    cdtot_vals = list(vsp.GetDoubleResults(polar_res_id, "CDtot", 0))
    ld_vals = list(vsp.GetDoubleResults(polar_res_id, "L_D", 0))
    cmy_vals = list(vsp.GetDoubleResults(polar_res_id, "CMy", 0))

    polar_points = []
    for i, alpha in enumerate(alphas):
        polar_points.append({
            "alpha_deg": float(alpha),
            "CL": float(cl_vals[i]) if i < len(cl_vals) else 0.0,
            "CDi": float(cdi_vals[i]) if i < len(cdi_vals) else 0.0,
            "CDo": float(cdo_vals[i]) if i < len(cdo_vals) else 0.0,
            "CDtot": float(cdtot_vals[i]) if i < len(cdtot_vals) else 0.0,
            "L_D": float(ld_vals[i]) if i < len(ld_vals) else 0.0,
            "CMy": float(cmy_vals[i]) if i < len(cmy_vals) else 0.0,
        })

    return {
        "analysis": sweep_analysis,
        "method": "PANEL" if method.lower() == "panel" else "VORTEX_LATTICE",
        "comp_geom_result_id": comp_geom_res_id,
        "sweep_result_id": sweep_res_id,
        "polar_points": polar_points,
    }


def export_vsp_model(
    output_dir: str | Path,
    base_name: str = "samolot_bipol",
    formats: Tuple[str, ...] = ("vsp3", "stl", "step", "obj", "dxf"),
    vsp_module: Any = None,
) -> Dict[str, str]:
    """
    Zapisuje model OpenVSP do natywnego pliku `.vsp3` (`WriteVSPFile`) oraz eksportuje
    geometrię CAD/CAE (`ExportFile`) do wybranych formatów za pomocą API OpenVSP.
    """
    vsp = _load_vsp(vsp_module)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    safe_base = re.sub(r"[^a-zA-Z0-9_-]+", "_", base_name).strip("_") or "samolot_bipol"

    format_map = {
        "stl": ("stl", getattr(vsp, "EXPORT_STL", 2)),
        "step": ("stp", getattr(vsp, "EXPORT_STEP", 4)),
        "iges": ("igs", getattr(vsp, "EXPORT_IGES", 7)),
        "obj": ("obj", getattr(vsp, "EXPORT_OBJ", 12)),
        "dxf": ("dxf", getattr(vsp, "EXPORT_DXF", 9)),
        "gmsh": ("msh", getattr(vsp, "EXPORT_GMSH", 10)),
        "xsec": ("hrm", getattr(vsp, "EXPORT_XSEC", 1)),
    }

    exported: Dict[str, str] = {}
    set_all = getattr(vsp, "SET_ALL", 0)

    for fmt in formats:
        fmt_key = fmt.lower().lstrip(".")
        if fmt_key == "vsp3":
            file_path = str(out_path / f"{safe_base}.vsp3")
            vsp.WriteVSPFile(file_path, set_all)
            errors = _check_vsp_errors(vsp, f"WriteVSPFile({file_path})")
            if errors:
                raise OpenVSPAPIError("; ".join(errors))
            exported["vsp3"] = file_path
        elif fmt_key in format_map:
            ext, export_const = format_map[fmt_key]
            file_path = str(out_path / f"{safe_base}.{ext}")
            vsp.ExportFile(file_path, set_all, export_const)
            errors = _check_vsp_errors(vsp, f"ExportFile({file_path}, {fmt_key})")
            if errors:
                raise OpenVSPAPIError("; ".join(errors))
            exported[fmt_key] = file_path
        else:
            raise ValueError(f"Nieobsługiwany format eksportu OpenVSP: {fmt}")

    return exported


def run_vsp_wave_drag(
    s_ref_m2: float,
    mach: float = 1.2,
    num_slices: int = 40,
    num_rot_sects: int = 12,
    vsp_module: Any = None,
) -> Dict[str, Any]:
    """
    Uruchamia analizę oporu falowego `WaveDrag` (reguła pól Supersonic Area Rule)
    przez natywne API OpenVSP (`ExecAnalysis("WaveDrag")`).
    """
    vsp = _load_vsp(vsp_module)
    analysis_name = "WaveDrag"
    vsp.SetAnalysisInputDefaults(analysis_name)

    vsp.SetIntAnalysisInput(analysis_name, "UseMode", [0], 0)
    vsp.SetDoubleAnalysisInput(analysis_name, "Sref", [float(s_ref_m2)], 0)
    vsp.SetDoubleAnalysisInput(analysis_name, "Mach", [max(1.01, float(mach))], 0)
    vsp.SetIntAnalysisInput(analysis_name, "NumSlices", [max(10, int(num_slices))], 0)
    vsp.SetIntAnalysisInput(analysis_name, "NumRotSects", [max(4, int(num_rot_sects))], 0)

    res_id = vsp.ExecAnalysis(analysis_name)
    errors = _check_vsp_errors(vsp, "ExecAnalysis(WaveDrag)")
    if errors:
        raise OpenVSPAPIError("; ".join(errors))

    cd_wave = list(vsp.GetDoubleResults(res_id, "CDWave", 0))
    d_on_q = list(vsp.GetDoubleResults(res_id, "D_on_q", 0))
    max_area = list(vsp.GetDoubleResults(res_id, "MaxCrossSectArea", 0))

    mesh_geom_ids = list(vsp.GetStringResults(res_id, "Mesh_GeomID", 0))
    if mesh_geom_ids and hasattr(vsp, "DeleteGeomVec"):
        vsp.DeleteGeomVec(mesh_geom_ids)

    return {
        "analysis": analysis_name,
        "result_id": res_id,
        "mach": max(1.01, float(mach)),
        "s_ref_m2": float(s_ref_m2),
        "cd_wave": float(cd_wave[0]) if cd_wave else 0.0,
        "d_on_q_m2": float(d_on_q[0]) if d_on_q else 0.0,
        "max_cross_sect_area_m2": float(max_area[0]) if max_area else 0.0,
    }


def run_vsp_projection_area(
    direction: str = "x",
    vsp_module: Any = None,
) -> Dict[str, Any]:
    """
    Uruchamia analizę rzutu geometrycznego `Projection` przez `ExecAnalysis("Projection")`.
    Wyznacza pole powierzchni rzutu bryły samolotu wzdłuż wybranej osi (`x` - pole czołowe,
    `y` - pole boczne, `z` - pole rzutu poziomego).
    """
    vsp = _load_vsp(vsp_module)
    analysis_name = "Projection"
    vsp.SetAnalysisInputDefaults(analysis_name)

    dir_map = {
        "x": getattr(vsp, "X_DIR", 0),
        "y": getattr(vsp, "Y_DIR", 1),
        "z": getattr(vsp, "Z_DIR", 2),
    }
    dir_key = direction.lower().strip()
    if dir_key not in dir_map:
        raise ValueError(f"Nieprawidłowy kierunek rzutu OpenVSP Projection: {direction} (dozwolone: x, y, z)")

    vsp.SetIntAnalysisInput(analysis_name, "DirectionType", [int(dir_map[dir_key])], 0)
    vsp.SetIntAnalysisInput(analysis_name, "TargetType", [int(getattr(vsp, "SET_TARGET", 0))], 0)
    vsp.SetIntAnalysisInput(analysis_name, "BoundaryType", [int(getattr(vsp, "NO_BOUNDARY", 0))], 0)

    res_id = vsp.ExecAnalysis(analysis_name)
    errors = _check_vsp_errors(vsp, "ExecAnalysis(Projection)")
    if errors:
        raise OpenVSPAPIError("; ".join(errors))

    area_res = list(vsp.GetDoubleResults(res_id, "Area", 0))
    mesh_geom_ids = list(vsp.GetStringResults(res_id, "Mesh_GeomID", 0))
    if mesh_geom_ids and hasattr(vsp, "DeleteGeomVec"):
        vsp.DeleteGeomVec(mesh_geom_ids)

    return {
        "analysis": analysis_name,
        "result_id": res_id,
        "direction": dir_key,
        "projected_area_m2": float(area_res[0]) if area_res else 0.0,
    }


def compute_vsp_degen_geom(
    vsp_module: Any = None,
) -> Dict[str, Any]:
    """
    Uruchamia analizę geometrii zdegenerowanej `DegenGeom` (`ExecAnalysis("DegenGeom")` /
    `ComputeDegenGeom`) w OpenVSP, generującą reprezentacje płytowe (Camber Surface),
    belkowe (Stick) oraz punktowe dla solwerów aerodynamicznych i strukturalnych.
    """
    vsp = _load_vsp(vsp_module)
    analysis_name = "DegenGeom"
    vsp.SetAnalysisInputDefaults(analysis_name)
    vsp.SetIntAnalysisInput(analysis_name, "WriteCSVFlag", [0], 0)
    vsp.SetIntAnalysisInput(analysis_name, "WriteMFileFlag", [0], 0)

    res_id = vsp.ExecAnalysis(analysis_name)
    errors = _check_vsp_errors(vsp, "ExecAnalysis(DegenGeom)")
    if errors:
        raise OpenVSPAPIError("; ".join(errors))

    degen_obj_ids = list(vsp.GetStringResults(res_id, "Degen_Obj", 0))
    comp_names = []
    for obj_id in degen_obj_ids:
        names = list(vsp.GetStringResults(obj_id, "name", 0))
        if names:
            comp_names.append(str(names[0]))

    return {
        "analysis": analysis_name,
        "result_id": res_id,
        "degen_object_ids": degen_obj_ids,
        "component_names": comp_names,
    }


def load_vsp_file(
    file_path: str | Path,
    clear_existing: bool = True,
    vsp_module: Any = None,
) -> Dict[str, Any]:
    """
    Wczytuje plik `.vsp3` do sesji OpenVSP za pomocą `ReadVSPFile` i zwraca listę
    załadowanych komponentów geometrycznych wraz z ich typami i nazwami.
    """
    vsp = _load_vsp(vsp_module)
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Plik modelu OpenVSP (.vsp3) nie istnieje: {path_obj}")

    vsp.VSPCheckSetup()
    if clear_existing:
        vsp.VSPRenew()
        vsp.ClearVSPModel()

    vsp.ReadVSPFile(str(path_obj))
    errors = _check_vsp_errors(vsp, f"ReadVSPFile({path_obj})")
    if errors:
        raise OpenVSPAPIError("; ".join(errors))

    vsp.Update()
    geom_ids = list(vsp.FindGeoms()) if hasattr(vsp, "FindGeoms") else []
    geometries = []
    for gid in geom_ids:
        g_name = vsp.GetGeomName(gid) if hasattr(vsp, "GetGeomName") else gid
        g_type = vsp.GetGeomTypeName(gid) if hasattr(vsp, "GetGeomTypeName") else "UNKNOWN"
        geometries.append({
            "geom_id": str(gid),
            "name": str(g_name),
            "type": str(g_type),
        })

    return {
        "file_path": str(path_obj),
        "num_geometries": len(geometries),
        "geometries": geometries,
    }


def run_full_vsp_pipeline(
    project_results: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None,
    run_vspaero: bool = False,
    export_dir: Optional[str | Path] = None,
    export_formats: Tuple[str, ...] = ("vsp3", "stl", "step"),
    vsp_module: Any = None,
) -> Dict[str, Any]:
    """
    Wykonuje pełny potok obliczeniowy OpenVSP dla projektu samolotu BIPOL:
    1. Buduje model 3D w API OpenVSP (`build_vsp_aircraft_model`),
    2. Oblicza dokładne powierzchnie omywane i objętości 3D (`CompGeom`),
    3. Oblicza właściwości masowo-bezwładnościowe (`MassProp`),
    4. Oblicza opór szkodliwy $C_{D0}$ (`ParasiteDrag`),
    5. Opcjonalnie uruchamia solwer aerodynamiczny `VSPAERO` oraz eksportuje pliki `.vsp3` / CAD.
    """
    vsp = _load_vsp(vsp_module)
    effective_params = dict(params or project_results.get("params") or project_results.get("inputs") or {})
    geom_res = project_results.get("geometry", {})
    wing_data = geom_res.get("wing", {})
    balance_res = project_results.get("balance", {})

    model_summary = build_vsp_aircraft_model(
        project_results,
        params=effective_params,
        vsp_module=vsp,
    )

    comp_geom = run_vsp_comp_geom(vsp_module=vsp)
    mass_prop = run_vsp_mass_properties(vsp_module=vsp)

    s_ref = float(wing_data.get("S", 15.0))
    b_ref = float(wing_data.get("b", 10.0))
    c_ref = float(wing_data.get("mac", 1.5))
    v_cruise_ms = float(effective_params.get("v_cruise", 220.0)) / 3.6
    alt_cruise_m = float(effective_params.get("h_cruise", 2000.0))

    parasite_drag = run_vsp_parasite_drag(
        s_ref_m2=s_ref,
        v_inf_ms=v_cruise_ms,
        altitude_m=alt_cruise_m,
        vsp_module=vsp,
    )

    aero_result = None
    if run_vspaero:
        x_cg = float(balance_res.get("x_cg_most_forward_m") or (0.30 * float(geom_res.get("fuselage", {}).get("length", 8.0))))
        aero_result = run_vsp_aero_analysis(
            s_ref_m2=s_ref,
            b_ref_m=b_ref,
            c_ref_m=c_ref,
            x_cg_m=x_cg,
            vsp_module=vsp,
        )

    exported_files: Dict[str, str] = {}
    if export_dir is not None:
        exported_files = export_vsp_model(
            output_dir=export_dir,
            base_name=model_summary["vehicle_name"],
            formats=export_formats,
            vsp_module=vsp,
        )

    return {
        "model": model_summary,
        "comp_geom": comp_geom,
        "mass_properties": mass_prop,
        "parasite_drag": parasite_drag,
        "vspaero": aero_result,
        "exported_files": exported_files,
    }

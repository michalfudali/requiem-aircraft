"""
Most integracyjny OpenVSP 3.55.0 API <-> BiPOL Requiem.
Zapewnia:
1. Pełną introspekcję i katalog wszystkich funkcji (~1 069 funkcji C++/SWIG w `openvsp.vsp`
   oraz funkcji pomocniczych `utilities`, `surface_patches`, `parasite_drag`, `degen_geom_parse`,
   `vsp_airfoils`, `avlpy`, `charm`, `pypmarc`), wszystkich stałych (~1 046 enumów/stałych),
   22 analiz (`ListAnalysis`) i 16 typów geometrii (`GetGeomTypes`).
2. Uniwersalny wykonawca dowolnej funkcji API (`call_api_function`) z automatyczną konwersją
   typów (vec3d, Matrix4d, stałe symboliczne `SET_ALL`/`EXPORT_STEP`, ścieżki względne ASCII).
3. Automatyczny generator parametrycznego modelu 3D samolotu w OpenVSP z aktywnego projektu
   BiPOL (`build_model_from_bipol`) wraz z ekstrakcją siatki powierzchni 3D (`SurfacePatches`).
4. Inspektor i edytor drzewa geometrii (`Geom`, `Parm`, `XSec`, `SubSurf`, `Airfoil`, `Sets`,
   `DesignVar`, `UserParm`, `AdvLink`, `Probe`/`Ruler`).
5. Uruchamianie wszystkich 22 analiz OpenVSP (`CompGeom`, `ParasiteDrag`, `VSPAEROComputeGeometry`,
   `VSPAEROSweep`, `VSPAEROSinglePoint`, `MassProp`, `WaveDrag`, `PlanarSlice`, `SurfacePatches`,
   `DegenGeom`, `BladeElement`, `CpSlicer`, `Projection`, `EmintonLord`, `SurfaceIntersection`,
   `CfdMeshAnalysis`, `FeaMeshAnalysis`, itd.) z automatycznym porównaniem z wynikami BiPOL P3/P4.
6. Eksport i import plików CAD/CFD/FEA (`.vsp3`, `STEP`, `IGES`, `STL`, `OBJ`, `X3D`, `DXF`,
   `SVG`, `GMSH`, `NASTRAN`, `CalculiX`, `Cart3D`, `VSPGeom`, `Airfoils`, `.des`, `.xddm`).
7. Studio skryptowe Python `openvsp` oraz AngelScript `.vspscript` (`vspscript.exe`).
"""
from __future__ import annotations

import contextlib
import inspect
import io
import json
import math
import os
import re
import subprocess
import threading
import time
import traceback
from typing import Any

from flask import Blueprint, abort, jsonify, request, send_file

try:
    import openvsp as vsp
except (ImportError, OSError):
    # Native OpenVSP bindings must match the interpreter/OS. The optional
    # integration must not prevent BIPOL or ML1 from starting without them.
    vsp = None
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS

blueprint = Blueprint("openvsp", __name__, url_prefix="/api/openvsp")


@blueprint.before_request
def require_openvsp():
    if vsp is None and request.endpoint != 'openvsp.api_status':
        return jsonify(status='error', available=False,
                       message='OpenVSP jest niedostępny. Zainstaluj API OpenVSP zgodne z wersją Pythona i systemem.'), 503


def _vspscript_path():
    directory = os.environ.get('BIPOL_OPENVSP_DIR')
    if not directory or not os.path.isdir(directory):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        local_vsp = root / 'OpenVSP-3.55.0'
        if local_vsp.is_dir():
            directory = str(local_vsp)
        else:
            sibling_vsp = root.parent / 'bipol' / 'OpenVSP-3.55.0'
            if sibling_vsp.is_dir():
                directory = str(sibling_vsp)
    directory = directory or 'OpenVSP-3.55.0'
    return os.path.abspath(os.path.join(directory, 'vspscript.exe' if os.name == 'nt' else 'vspscript'))

# Globalny RLock chroniący singleton C++ OpenVSP przed równoległym dostępem wątków Flask
_VSP_LOCK = threading.RLock()

# Katalog roboczy o czysto ASCII ścieżce względnej (wymóg SWIG std::string na Windows przy 'Michał')
WORK_REL_DIR = "work/openvsp"
os.makedirs(WORK_REL_DIR, exist_ok=True)
DEFAULT_VSP3_REL = f"{WORK_REL_DIR}/bipol_current.vsp3"

# Cache katalogu API (budowany leniwie raz na proces)
_CATALOG_CACHE: dict[str, Any] | None = None
# Ostatni wynik BiPOL zsynchronizowany z modelem OpenVSP
_LAST_BIPOL_RESULT: dict[str, Any] | None = None
_LAST_BUILD_META: dict[str, Any] = {}


def _ascii_rel_path(filename: str) -> str:
    """Zwraca bezpieczną, względną ścieżkę ASCII wewnątrz work/openvsp."""
    clean = os.path.basename(str(filename or "model.vsp3").strip().replace("\\", "/"))
    clean = re.sub(r"[^A-Za-z0-9._-]", "_", clean)
    if not clean or clean in (".", ".."):
        clean = "model.vsp3"
    os.makedirs(WORK_REL_DIR, exist_ok=True)
    return f"{WORK_REL_DIR}/{clean}"


def _pop_vsp_errors() -> list[dict[str, Any]]:
    """Pobiera i czyści stos błędów/ostrzeżeń z singletona ErrorMgr OpenVSP."""
    errors = []
    try:
        while vsp.GetNumTotalErrors() > 0:
            err = vsp.PopLastError()
            errors.append({
                "code": int(getattr(err, "m_ErrorCode", 0)),
                "string": str(getattr(err, "m_ErrorString", "")),
                "function": str(getattr(err, "m_FunctionName", "")),
            })
    except Exception:
        pass
    return errors


def _set_geom_parm(geom_id: str, name: str, group: str, value: float) -> float | None:
    """
    Bezpiecznie ustawia wartość parametru w OpenVSP, obsługując zarówno standardowe grupy (`Design`, `XForm`, `Sym`),
    jak i przekroje `XSec_N` / `XSecCurve_N` poprzez `GetXSecParm` oraz `GetParmDisplayGroupName`.
    """
    val_f = float(value)
    if group.startswith(("XSec_", "XSecCurve_")):
        try:
            idx = int(group.split("_", 1)[1])
            xsurf = vsp.GetXSecSurf(geom_id, 0)
            xsec = vsp.GetXSec(xsurf, idx)
            if xsec:
                pid = vsp.GetXSecParm(xsec, name)
                if pid:
                    return vsp.SetParmVal(pid, val_f)
        except Exception:
            pass
    for pid in vsp.GetGeomParmIDs(geom_id):
        if vsp.GetParmName(pid) == name:
            disp_grp = vsp.GetParmDisplayGroupName(pid)
            base_grp = vsp.GetParmGroupName(pid)
            if group in (disp_grp, base_grp):
                return vsp.SetParmVal(pid, val_f)
    try:
        return vsp.SetParmVal(geom_id, name, group, val_f)
    except Exception:
        return None


def _serialize_vsp_value(val: Any, _depth: int = 0) -> Any:
    """Konwertuje dowolny obiekt zwracany przez OpenVSP/SWIG na strukturę JSON-serializowalną."""
    if _depth > 8:
        return str(val)
    if val is None or isinstance(val, (bool, int)):
        return val
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    if isinstance(val, str):
        return val
    if isinstance(val, vsp.vec3d):
        return {
            "__type__": "vec3d",
            "x": _serialize_vsp_value(val.x(), _depth + 1),
            "y": _serialize_vsp_value(val.y(), _depth + 1),
            "z": _serialize_vsp_value(val.z(), _depth + 1),
        }
    if isinstance(val, vsp.Matrix4d):
        try:
            data = list(val.data())
            mat = [data[i * 4:(i + 1) * 4] for i in range(4)]
        except Exception:
            mat = []
        return {"__type__": "Matrix4d", "matrix": _serialize_vsp_value(mat, _depth + 1)}
    if isinstance(val, vsp.ErrorObj):
        return {
            "__type__": "ErrorObj",
            "code": int(getattr(val, "m_ErrorCode", 0)),
            "string": str(getattr(val, "m_ErrorString", "")),
            "function": str(getattr(val, "m_FunctionName", "")),
        }
    if hasattr(val, "_asdict"):
        return {k: _serialize_vsp_value(v, _depth + 1) for k, v in val._asdict().items()}
    if isinstance(val, dict):
        return {str(k): _serialize_vsp_value(v, _depth + 1) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [_serialize_vsp_value(x, _depth + 1) for x in val]
    if hasattr(val, "tolist"):
        try:
            return _serialize_vsp_value(val.tolist(), _depth + 1)
        except Exception:
            return str(val)
    if hasattr(val, "__iter__"):
        try:
            return [_serialize_vsp_value(x, _depth + 1) for x in list(val)]
        except Exception:
            pass
    return str(val)


def _categorize_function(name: str, module_name: str = "openvsp.vsp") -> str:
    """Przypisuje funkcję API OpenVSP do czytelnej kategorii funkcjonalnej."""
    if module_name != "openvsp.vsp":
        return f"Moduły Python ({module_name})"
    n = name
    if any(k in n for k in ("VSPAERO", "ControlSurfaceGroup")):
        return "VSPAERO i Aerodynamika Wirowa/Panelowa"
    if any(k in n for k in ("CFD", "Cfd", "Fea", "FEA")):
        return "Siatki Obliczeniowe CFD i FEA (CfdMesh / FeaMesh)"
    if any(k in n for k in ("ParasiteDrag", "Excrescence", "Freestream", "WaveDrag")):
        return "Opór Profilowy (ParasiteDrag) i Falowy (WaveDrag)"
    if any(k in n for k in ("Analysis", "Results", "DataNames", "ExecAnalysis")):
        return "Solwery, Analizy i Menedżer Wyników (ResultsMgr)"
    if any(k in n for k in ("Airfoil", "AF", "UpperLower", "CST", "VKTAirfoil", "FourSeries", "SixSeries")):
        return "Profile Lotnicze i Krzywe (Airfoil)"
    if any(k in n for k in ("XSec", "EditXSec", "Bezier", "Skin", "BOR")):
        return "Przekroje Poprzeczne i Powierzchnie (XSec / XSecSurf)"
    if any(k in n for k in ("SubSurf", "SS_")):
        return "Podpowierzchnie i Powierzchnie Sterowe (SubSurf)"
    if any(k in n for k in ("Prop", "Blade", "PCurve")):
        return "Śmigła, Wirniki i Łopaty (Prop / Blade)"
    if any(k in n for k in ("DesignVar", "UserParm", "Link", "AdvLink", "VarPreset", "Mode")):
        return "Zmienne Projektowe, Powiązania i Tryby (DesignVar / AdvLink / Modes)"
    if any(k in n for k in ("Set", "Group")) and "Parm" not in n and "Analysis" not in n and "XSec" not in n:
        return "Zbiory i Grupowanie Komponentów (Sets)"
    if any(k in n for k in ("Measure", "Probe", "Ruler", "Protractor", "RST", "LMN", "UVW", "CompPnt", "Project")):
        return "Pomiary, Sondy i Rzutowanie (Measure / Probes / Coordinates)"
    if any(k in n for k in ("Gui", "GUI", "Screen", "Window", "Background", "View", "Trackball", "Snap", "Facade")):
        return "Interfejs Graficzny, Widoki i Serwer Facade (GUI / Views)"
    if any(k in n for k in ("Error", "CheckFor", "Version", "VSPFile", "Export", "Import", "Read", "Write", "ClearVSP", "Update", "Vehicle")):
        return "System, Pliki CAD/VSP3 i Zarządzanie Modelem (System & I/O)"
    if any(k in n for k in ("Parm", "Container")):
        return "Parametry i Kontenery (Parm & ContainerMgr)"
    if any(k in n for k in ("Geom", "Cut", "Copy", "Paste", "Material", "BBox")):
        return "Geometria i Komponenty 3D (Geom)"
    if any(k in n for k in ("vec", "Vec", "Matrix", "Angle", "Dist", "Intersect", "Map", "To", "From")):
        return "Matematyka, Wektory 3D i Transformacje (Math & Vectors)"
    return "Pozostałe Funkcje Jądra OpenVSP"


def _parse_swig_signature(func_name: str, obj: Any) -> dict[str, Any]:
    """Wyciąga sygnaturę, parametry i opis funkcji SWIG lub czystego Pythona."""
    doc = inspect.getdoc(obj) or ""
    params_info = []
    return_type = "Any"
    signature_str = f"{func_name}()"

    try:
        sig = inspect.signature(obj)
        signature_str = f"{func_name}{sig}"
        for p_name, p in sig.parameters.items():
            if p_name == "self":
                continue
            default_val = None if p.default is inspect.Parameter.empty else _serialize_vsp_value(p.default)
            has_default = p.default is not inspect.Parameter.empty
            annotation = str(p.annotation) if p.annotation is not inspect.Parameter.empty else "Any"
            params_info.append({
                "name": p_name,
                "type": annotation,
                "required": not has_default and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD),
                "default": default_val,
                "kind": str(p.kind.name),
            })
        if sig.return_annotation is not inspect.Parameter.empty:
            return_type = str(sig.return_annotation)
    except (ValueError, TypeError):
        pass

    first_line = doc.splitlines()[0].strip() if doc else ""
    if "->" in first_line:
        parts = first_line.split("->", 1)
        return_type = parts[1].strip()
        signature_str = first_line
    elif first_line.startswith(func_name + "("):
        signature_str = first_line

    if first_line.startswith(func_name + "(") and "(" in first_line and ")" in first_line:
        inside = first_line.split("(", 1)[1].rsplit(")", 1)[0].strip()
        if inside and (not params_info or (len(params_info) == 1 and params_info[0]["name"] == "args")):
            params_info = []
            for idx, raw_arg in enumerate(inside.split(",")):
                raw_arg = raw_arg.strip()
                if not raw_arg:
                    continue
                has_def = "=" in raw_arg
                left, def_val = (raw_arg.split("=", 1) + [""])[:2] if has_def else (raw_arg, None)
                tokens = left.strip().split()
                arg_name = tokens[-1] if tokens else f"arg_{idx + 1}"
                arg_type = " ".join(tokens[:-1]) if len(tokens) > 1 else "Any"
                params_info.append({
                    "name": arg_name,
                    "type": arg_type,
                    "required": not has_def,
                    "default": def_val.strip() if def_val is not None else None,
                    "kind": "POSITIONAL_OR_KEYWORD",
                })
        elif inside and params_info:
            raw_parts = [p.strip() for p in inside.split(",") if p.strip()]
            if len(raw_parts) == len(params_info):
                for p_dict, raw_arg in zip(params_info, raw_parts):
                    left = raw_arg.split("=", 1)[0].strip()
                    tokens = left.split()
                    if len(tokens) > 1 and p_dict["type"] == "Any":
                        p_dict["type"] = " ".join(tokens[:-1])

    return {
        "name": func_name,
        "signature": signature_str,
        "return_type": return_type,
        "params": params_info,
        "doc": doc,
    }


def get_api_catalog(force_refresh: bool = False) -> dict[str, Any]:
    """Buduje i zwraca kompletny katalog wszystkich funkcji, stałych, klas i analiz OpenVSP API."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None and not force_refresh:
        return _CATALOG_CACHE

    with _VSP_LOCK:
        functions: list[dict[str, Any]] = []
        constants: list[dict[str, Any]] = []
        classes: list[dict[str, Any]] = []
        seen_funcs: set[str] = set()

        # 1. Wszystkie funkcje, stałe i klasy z głównego modułu C++/SWIG openvsp.vsp
        for name in sorted(dir(vsp.vsp)):
            if name.startswith("_"):
                continue
            obj = getattr(vsp.vsp, name)
            if inspect.isfunction(obj) or inspect.isbuiltin(obj):
                meta = _parse_swig_signature(name, obj)
                meta["module"] = "openvsp.vsp"
                meta["category"] = _categorize_function(name, "openvsp.vsp")
                functions.append(meta)
                seen_funcs.add(name)
            elif inspect.isclass(obj):
                methods = [
                    m for m in sorted(dir(obj))
                    if not m.startswith("_") and callable(getattr(obj, m, None))
                ]
                classes.append({
                    "name": name,
                    "module": "openvsp.vsp",
                    "methods": methods,
                    "doc": inspect.getdoc(obj) or "",
                })
            elif isinstance(obj, (int, float, str)):
                prefix = name.split("_", 1)[0] if "_" in name else "OTHER"
                constants.append({
                    "name": name,
                    "value": obj,
                    "group": prefix,
                })

        # 2. Funkcje z modułów rozszerzeń Pythona OpenVSP (z tłumieniem banneru stdout np. z charm)
        helper_modules = [
            ("openvsp.utilities", getattr(vsp, "utilities", None)),
            ("openvsp.surface_patches", getattr(vsp, "surface_patches", None)),
            ("openvsp.parasite_drag", getattr(vsp, "parasite_drag", None)),
            ("openvsp.degen_geom_parse", getattr(vsp, "degen_geom_parse", None)),
        ]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            for extra_mod_name in ("vsp_airfoils", "degen_geom", "avlpy", "charm", "pypmarc"):
                try:
                    mod = __import__(extra_mod_name)
                    helper_modules.append((extra_mod_name, mod))
                except Exception:
                    pass

        for mod_name, mod in helper_modules:
            if mod is None:
                continue
            for name in sorted(dir(mod)):
                if name.startswith("_") or name in seen_funcs:
                    continue
                obj = getattr(mod, name)
                if inspect.isfunction(obj):
                    meta = _parse_swig_signature(name, obj)
                    meta["module"] = mod_name
                    meta["category"] = _categorize_function(name, mod_name)
                    functions.append(meta)
                    seen_funcs.add(name)
                elif inspect.isclass(obj) and name not in {c["name"] for c in classes}:
                    methods = [
                        m for m in sorted(dir(obj))
                        if not m.startswith("_") and callable(getattr(obj, m, None))
                    ]
                    classes.append({
                        "name": name,
                        "module": mod_name,
                        "methods": methods,
                        "doc": inspect.getdoc(obj) or "",
                    })

        # 3. Wszystkie 22 analizy OpenVSP wraz z ich wejściami i typami
        analyses_info = []
        type_map = {
            getattr(vsp, "INT_DATA", 1): "INT",
            getattr(vsp, "DOUBLE_DATA", 2): "DOUBLE",
            getattr(vsp, "STRING_DATA", 3): "STRING",
            getattr(vsp, "VEC3D_DATA", 4): "VEC3D",
            getattr(vsp, "DOUBLE_MATRIX_DATA", 5): "DOUBLE_MATRIX",
        }
        for analysis_name in vsp.ListAnalysis():
            inputs = []
            for inp_name in vsp.GetAnalysisInputNames(analysis_name):
                t_code = vsp.GetAnalysisInputType(analysis_name, inp_name)
                t_label = type_map.get(t_code, f"TYPE_{t_code}")
                val = []
                try:
                    if t_code == vsp.INT_DATA:
                        val = list(vsp.GetIntAnalysisInput(analysis_name, inp_name))
                    elif t_code == vsp.DOUBLE_DATA:
                        val = [_serialize_vsp_value(x) for x in vsp.GetDoubleAnalysisInput(analysis_name, inp_name)]
                    elif t_code == vsp.STRING_DATA:
                        val = list(vsp.GetStringAnalysisInput(analysis_name, inp_name))
                    elif t_code == vsp.VEC3D_DATA:
                        val = [_serialize_vsp_value(x) for x in vsp.GetVec3dAnalysisInput(analysis_name, inp_name)]
                except Exception:
                    val = []
                inputs.append({
                    "name": inp_name,
                    "type": t_label,
                    "type_code": t_code,
                    "default": val,
                })
            analyses_info.append({
                "name": analysis_name,
                "num_inputs": len(inputs),
                "inputs": inputs,
            })

        # 4. Wszystkie 16 typów geometrii
        geom_types = list(vsp.GetGeomTypes())

        # 5. Podsumowanie kategorii
        categories_summary: dict[str, int] = {}
        for f in functions:
            cat = f["category"]
            categories_summary[cat] = categories_summary.get(cat, 0) + 1

        constant_groups: dict[str, int] = {}
        for c in constants:
            grp = c["group"]
            constant_groups[grp] = constant_groups.get(grp, 0) + 1

        _pop_vsp_errors()
        _CATALOG_CACHE = {
            "status": "ok",
            "version": vsp.GetVSPVersion(),
            "vspaero_available": bool(vsp.CheckForVSPAERO(vsp.GetVSPAEROPath())),
            "vspaero_path": vsp.GetVSPAEROPath(),
            "vspscript_available": os.path.isfile(_vspscript_path()),
            "counts": {
                "functions": len(functions),
                "core_vsp_functions": sum(1 for f in functions if f["module"] == "openvsp.vsp"),
                "helper_functions": sum(1 for f in functions if f["module"] != "openvsp.vsp"),
                "constants": len(constants),
                "classes": len(classes),
                "analyses": len(analyses_info),
                "geom_types": len(geom_types),
            },
            "categories": [
                {"name": k, "count": v}
                for k, v in sorted(categories_summary.items(), key=lambda x: (-x[1], x[0]))
            ],
            "constant_groups": [
                {"name": k, "count": v}
                for k, v in sorted(constant_groups.items(), key=lambda x: (-x[1], x[0]))
            ],
            "geom_types": geom_types,
            "analyses": analyses_info,
            "classes": classes,
            "functions": functions,
            "constants": constants,
        }
        return _CATALOG_CACHE


def _coerce_arg_for_vsp(arg: Any, param_meta: dict[str, Any] | None = None, func_name: str = "") -> Any:
    """Konwertuje argument JSON na typ oczekiwany przez funkcję C++/SWIG OpenVSP."""
    if isinstance(arg, str):
        stripped = arg.strip()
        if stripped.startswith("vsp."):
            const_key = stripped[4:].strip()
            if hasattr(vsp, const_key):
                return getattr(vsp, const_key)
        elif hasattr(vsp, stripped) and stripped.isupper():
            return getattr(vsp, stripped)

        p_name = (param_meta or {}).get("name", "").lower()
        if any(k in p_name for k in ("file", "fname", "path")) or any(
            k in func_name for k in ("File", "Export", "Import", "Write", "Read")
        ):
            if ("/" in stripped or "\\" in stripped or stripped.endswith(
                (".vsp3", ".stp", ".step", ".igs", ".iges", ".stl", ".obj", ".x3d", ".dxf", ".svg",
                 ".msh", ".dat", ".inp", ".tri", ".vspgeom", ".csv", ".des", ".xddm", ".af", ".vspscript")
            )):
                return _ascii_rel_path(stripped)

        p_type = (param_meta or {}).get("type", "").lower()
        if "int" in p_type and "vector" not in p_type:
            try:
                return int(float(stripped))
            except ValueError:
                pass
        elif ("double" in p_type or "float" in p_type) and "vector" not in p_type:
            try:
                return float(stripped)
            except ValueError:
                pass
        elif "bool" in p_type and "vector" not in p_type:
            if stripped.lower() in ("true", "1", "yes"):
                return True
            if stripped.lower() in ("false", "0", "no"):
                return False

    if isinstance(arg, dict):
        if arg.get("__type__") == "vec3d" or set(arg.keys()) == {"x", "y", "z"}:
            return vsp.vec3d(float(arg.get("x", 0.0)), float(arg.get("y", 0.0)), float(arg.get("z", 0.0)))
        if arg.get("__type__") == "Matrix4d":
            return vsp.Matrix4d()

    if isinstance(arg, list):
        p_type = (param_meta or {}).get("type", "").lower()
        if "vec3d" in p_type and len(arg) == 3 and all(isinstance(x, (int, float)) for x in arg):
            return vsp.vec3d(float(arg[0]), float(arg[1]), float(arg[2]))
        if "vec3d" in p_type and all(isinstance(x, (list, dict)) for x in arg):
            out = []
            for item in arg:
                if isinstance(item, dict):
                    out.append(vsp.vec3d(float(item.get("x", 0)), float(item.get("y", 0)), float(item.get("z", 0))))
                elif isinstance(item, (list, tuple)) and len(item) >= 3:
                    out.append(vsp.vec3d(float(item[0]), float(item[1]), float(item[2])))
            return out
        return [_coerce_arg_for_vsp(x) for x in arg]

    return arg


def _resolve_callable(func_name: str) -> tuple[Any, dict[str, Any] | None]:
    """Znajduje funkcję w `openvsp` lub modułach pomocniczych wraz z jej metadanymi."""
    clean_name = str(func_name or "").strip()
    if clean_name.startswith("vsp."):
        clean_name = clean_name[4:]

    catalog = get_api_catalog()
    func_meta = next((f for f in catalog["functions"] if f["name"] == clean_name), None)

    if hasattr(vsp, clean_name):
        return getattr(vsp, clean_name), func_meta
    if hasattr(vsp.vsp, clean_name):
        return getattr(vsp.vsp, clean_name), func_meta

    for extra_mod_name in ("vsp_airfoils", "degen_geom", "avlpy", "charm", "pypmarc"):
        try:
            mod = __import__(extra_mod_name)
            if hasattr(mod, clean_name):
                return getattr(mod, clean_name), func_meta
        except Exception:
            pass

    raise ValueError(f"Nieznana funkcja OpenVSP API: '{func_name}'")


def call_api_function(
    func_name: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    auto_update: bool = False,
) -> dict[str, Any]:
    """Wykonuje dowolną funkcję z katalogu OpenVSP API i zwraca wynik oraz ewentualne komunikaty ErrorMgr."""
    with _VSP_LOCK:
        _pop_vsp_errors()
        fn, meta = _resolve_callable(func_name)
        raw_args = list(args or [])
        raw_kwargs = dict(kwargs or {})

        params_meta = (meta or {}).get("params", [])
        coerced_args = [
            _coerce_arg_for_vsp(a, params_meta[i] if i < len(params_meta) else None, func_name)
            for i, a in enumerate(raw_args)
        ]
        coerced_kwargs = {}
        for k, v in raw_kwargs.items():
            p_m = next((p for p in params_meta if p["name"] == k), None)
            coerced_kwargs[k] = _coerce_arg_for_vsp(v, p_m, func_name)

        t0 = time.perf_counter()
        result = fn(*coerced_args, **coerced_kwargs)
        if auto_update:
            vsp.Update()
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        errors = _pop_vsp_errors()

        serialized = _serialize_vsp_value(result)
        parsed_results = None
        if isinstance(result, str) and len(result) >= 4 and func_name in ("ExecAnalysis", "FindLatestResultsID", "FindResultsID"):
            try:
                parsed_results = _parse_results_recursive(result)
            except Exception:
                parsed_results = None

        return {
            "status": "ok",
            "function": func_name,
            "signature": (meta or {}).get("signature", f"{func_name}()"),
            "args": _serialize_vsp_value(coerced_args),
            "kwargs": _serialize_vsp_value(coerced_kwargs),
            "result": serialized,
            "result_type": type(result).__name__,
            "parsed_results": parsed_results,
            "elapsed_ms": elapsed_ms,
            "vsp_errors": errors,
        }


def _extract_3d_preview_mesh() -> dict[str, Any]:
    """Ekstrahuje rzeczywiste płaty powierzchni 3D z OpenVSP (`SurfacePatches`) dla widoku 3D w UI."""
    components_out = []
    bbox = {"min_x": 0.0, "max_x": 10.0, "min_y": -5.0, "max_y": 5.0, "min_z": -2.0, "max_z": 2.0}
    min_x, max_x = float("inf"), float("-inf")
    min_y, max_y = float("inf"), float("-inf")
    min_z, max_z = float("inf"), float("-inf")

    try:
        comps = vsp.export_surface_patches(vsp.SET_ALL)
        for comp in comps:
            geom_type = ""
            try:
                geom_type = vsp.GetGeomTypeName(comp.id)
            except Exception:
                pass
            patches_data = []
            for surf in comp.surfaces:
                for patch in surf.patches:
                    x_arr = patch.x
                    y_arr = patch.y
                    z_arr = patch.z
                    nu, nw = x_arr.shape
                    step_u = max(1, nu // 18)
                    step_w = max(1, nw // 18)
                    u_idx = list(range(0, nu, step_u))
                    if u_idx[-1] != nu - 1:
                        u_idx.append(nu - 1)
                    w_idx = list(range(0, nw, step_w))
                    if w_idx[-1] != nw - 1:
                        w_idx.append(nw - 1)

                    xs = [[round(float(x_arr[i, j]), 4) for j in w_idx] for i in u_idx]
                    ys = [[round(float(y_arr[i, j]), 4) for j in w_idx] for i in u_idx]
                    zs = [[round(float(z_arr[i, j]), 4) for j in w_idx] for i in u_idx]

                    for row_x, row_y, row_z in zip(xs, ys, zs):
                        for vx, vy, vz in zip(row_x, row_y, row_z):
                            if vx < min_x:
                                min_x = vx
                            if vx > max_x:
                                max_x = vx
                            if vy < min_y:
                                min_y = vy
                            if vy > max_y:
                                max_y = vy
                            if vz < min_z:
                                min_z = vz
                            if vz > max_z:
                                max_z = vz

                    patches_data.append({
                        "surf_index": int(surf.surf_index),
                        "patch_index": int(patch.patch_index),
                        "nu": len(u_idx),
                        "nw": len(w_idx),
                        "x": xs,
                        "y": ys,
                        "z": zs,
                    })
            components_out.append({
                "id": comp.id,
                "name": comp.name,
                "type": geom_type,
                "num_surfaces": len(comp.surfaces),
                "patches": patches_data,
            })
    except Exception:
        pass

    if min_x < float("inf"):
        bbox = {
            "min_x": round(min_x, 3),
            "max_x": round(max_x, 3),
            "min_y": round(min_y, 3),
            "max_y": round(max_y, 3),
            "min_z": round(min_z, 3),
            "max_z": round(max_z, 3),
        }
    _pop_vsp_errors()
    return {
        "components": components_out,
        "bbox": bbox,
    }


def get_model_state(include_mesh: bool = True, include_all_parms: bool = True) -> dict[str, Any]:
    """Zwraca pełny stan bieżącego modelu 3D w pamięci OpenVSP (drzewo Geom, Parm, SubSurf, XSec, Sets, DesignVars)."""
    with _VSP_LOCK:
        _pop_vsp_errors()
        geom_ids = list(vsp.FindGeoms())
        geoms_info = []

        for gid in geom_ids:
            g_name = vsp.GetGeomName(gid)
            g_type = vsp.GetGeomTypeName(gid)
            parent_id = vsp.GetGeomParent(gid)
            children_ids = list(vsp.GetGeomChildren(gid))

            subsurfs = []
            try:
                for ssid in vsp.GetSubSurfIDVec(gid):
                    subsurfs.append({
                        "id": ssid,
                        "name": vsp.GetSubSurfName(gid, ssid),
                        "type": vsp.GetSubSurfType(ssid),
                    })
            except Exception:
                pass

            xsecs_info = []
            try:
                num_xsec_surfs = vsp.GetNumXSecSurfs(gid)
                for s_idx in range(num_xsec_surfs):
                    xsurf_id = vsp.GetXSecSurf(gid, s_idx)
                    num_xsecs = vsp.GetNumXSec(xsurf_id)
                    for x_idx in range(num_xsecs):
                        xsec_id = vsp.GetXSec(xsurf_id, x_idx)
                        shape_type = vsp.GetXSecShape(xsec_id)
                        xsecs_info.append({
                            "surf_index": s_idx,
                            "xsec_index": x_idx,
                            "xsec_id": xsec_id,
                            "shape_type": shape_type,
                            "width": round(float(vsp.GetXSecWidth(xsec_id)), 4),
                            "height": round(float(vsp.GetXSecHeight(xsec_id)), 4),
                        })
            except Exception:
                pass

            groups: dict[str, list[dict[str, Any]]] = {}
            if include_all_parms:
                for pid in vsp.GetGeomParmIDs(gid):
                    try:
                        p_name = vsp.GetParmName(pid)
                        grp_name = vsp.GetParmDisplayGroupName(pid) or vsp.GetParmGroupName(pid) or "Other"
                        p_val = vsp.GetParmVal(pid)
                        p_type = vsp.GetParmType(pid)
                        p_min = vsp.GetParmLowerLimit(pid)
                        p_max = vsp.GetParmUpperLimit(pid)
                        p_desc = vsp.GetParmDescript(pid)
                        groups.setdefault(grp_name, []).append({
                            "id": pid,
                            "name": p_name,
                            "group": grp_name,
                            "value": _serialize_vsp_value(p_val),
                            "type": p_type,
                            "min": _serialize_vsp_value(p_min),
                            "max": _serialize_vsp_value(p_max),
                            "descript": p_desc,
                        })
                    except Exception:
                        continue

            member_sets = []
            try:
                for s_idx in range(vsp.GetNumSets()):
                    if vsp.GetSetFlag(gid, s_idx):
                        member_sets.append(s_idx)
            except Exception:
                pass

            geoms_info.append({
                "id": gid,
                "name": g_name,
                "type": g_type,
                "parent_id": parent_id,
                "children_ids": children_ids,
                "subsurfaces": subsurfs,
                "xsecs": xsecs_info,
                "parameter_groups": groups,
                "num_parameters": sum(len(v) for v in groups.values()),
                "sets": member_sets,
            })

        sets_info = []
        try:
            for s_idx in range(vsp.GetNumSets()):
                s_name = vsp.GetSetName(s_idx)
                geoms_in_set = list(vsp.GetGeomSetAtIndex(s_idx))
                sets_info.append({
                    "index": s_idx,
                    "name": s_name,
                    "geom_ids": geoms_in_set,
                    "count": len(geoms_in_set),
                })
        except Exception:
            pass

        design_vars = []
        try:
            for dv_idx in range(vsp.GetNumDesignVars()):
                pid = vsp.GetDesignVar(dv_idx)
                design_vars.append({
                    "index": dv_idx,
                    "parm_id": pid,
                    "parm_name": vsp.GetParmName(pid) if vsp.ValidParm(pid) else "",
                    "group": vsp.GetParmDisplayGroupName(pid) if vsp.ValidParm(pid) else "",
                    "value": _serialize_vsp_value(vsp.GetParmVal(pid)) if vsp.ValidParm(pid) else None,
                    "type": vsp.GetDesignVarType(dv_idx),
                })
        except Exception:
            pass

        probes_info = []
        try:
            for prid in vsp.GetAllProbes():
                p_name = vsp.GetContainerName(prid) if hasattr(vsp, "GetContainerName") else prid
                probes_info.append({"id": prid, "name": p_name or prid})
        except Exception:
            pass
        rulers_info = []
        try:
            for rlid in vsp.GetAllRulers():
                r_name = vsp.GetContainerName(rlid) if hasattr(vsp, "GetContainerName") else rlid
                rulers_info.append({"id": rlid, "name": r_name or rlid})
        except Exception:
            pass

        mesh_preview = _extract_3d_preview_mesh() if include_mesh else None
        _pop_vsp_errors()

        return {
            "status": "ok",
            "vsp_version": vsp.GetVSPVersion(),
            "vsp3_file": vsp.GetVSPFileName(),
            "vehicle_id": vsp.FindContainer("Vehicle", 0),
            "num_geoms": len(geoms_info),
            "geoms": geoms_info,
            "sets": sets_info,
            "design_vars": design_vars,
            "probes": probes_info,
            "rulers": rulers_info,
            "mesh": mesh_preview,
            "build_meta": _LAST_BUILD_META,
        }


def _set_wing_airfoil(geom_id: str, xsec_idx: int, camber: float, camber_loc: float, thickness: float, profile=None) -> None:
    """Zachowuje wybrane rzędne; bez wyboru profilu używa jawnego założenia NACA 4."""
    grp = f"XSecCurve_{xsec_idx}"
    if profile is not None:
        from calculations.vsp_airfoils import set_coordinate_airfoil
        set_coordinate_airfoil(vsp, vsp.GetXSecSurf(geom_id, 0), xsec_idx, profile)
        return
    try:
        xsurf = vsp.GetXSecSurf(geom_id, 0)
        vsp.ChangeXSecShape(xsurf, xsec_idx, vsp.XS_FOUR_SERIES)
    except Exception:
        pass
    _set_geom_parm(geom_id, "ThickChord", grp, max(0.04, min(0.30, float(thickness))))
    _set_geom_parm(geom_id, "Camber", grp, max(0.0, min(0.09, abs(float(camber)))))
    _set_geom_parm(geom_id, "CamberLoc", grp, max(0.15, min(0.70, float(camber_loc) if camber_loc > 0.05 else 0.40)))


def _add_control_subsurface(
    geom_id: str,
    name: str,
    eta_start: float,
    eta_end: float,
    chord_ratio: float,
    le_flag: int = 0,
) -> str | None:
    """Dodaje powierzchnię sterową (SubSurf SS_CONTROL) na płacie i ustawia jej zakres eta oraz cięciwę względną."""
    if eta_end <= eta_start + 0.01 or chord_ratio <= 0.01:
        return None
    ssid = vsp.AddSubSurf(geom_id, vsp.SS_CONTROL, 0)
    if not ssid:
        return None
    vsp.SetSubSurfName(geom_id, ssid, name)
    ss_parms = {vsp.GetParmName(pid): pid for pid in vsp.GetSubSurfParmIDs(ssid)}
    for p_name, p_val in (
        ("EtaFlag", 1.0),
        ("EtaStart", max(0.02, min(0.96, float(eta_start)))),
        ("EtaEnd", max(0.05, min(0.99, float(eta_end)))),
        ("Length_C_Start", max(0.05, min(0.60, float(chord_ratio)))),
        ("Length_C_End", max(0.05, min(0.60, float(chord_ratio)))),
        ("SE_Const_Flag", 1.0),
        ("LE_Flag", float(le_flag)),
    ):
        if p_name in ss_parms:
            vsp.SetParmVal(ss_parms[p_name], p_val)
    return ssid


def build_model_from_bipol(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Buduje kompletny, parametryczny model 3D samolotu w OpenVSP na podstawie bieżącego projektu BiPOL:
    - Kadłub (FUSELAGE) z dobranymi przekrojami (nos, kabina, belka ogonowa z uniesieniem),
    - Skrzydło główne (WING) o obrysie prostokątnym, trapezowym, skośnym, prostokątno-trapezowym (2 sekcje) lub eliptycznym,
      z profilem lotniczym, wzniosem, skosem, zwichrzeniem oraz podpowierzchniami sterowymi (Klapy, Lotki, Sloty),
    - Usterzenie poziome (WING) w układzie klasycznym, krzyżowym, T-tail lub Rudlickiego (V-tail) ze sterem wysokości,
    - Usterzenie pionowe (WING) pojedyncze lub podwójne (twin) ze sterem kierunku,
    - Zespół napędowy (PROP + gondole POD dla śmigła ciągnącego/pchającego/skrzydłowego/chowanego lub gondole odrzutowe),
    - Podwozie (POD dla kół głównych i przedniego/tylnego wg obliczonej bazy i rozstawu).
    """
    global _LAST_BIPOL_RESULT, _LAST_BUILD_META

    data = dict(payload or {})
    if "geometry" in data and "params" in data and "balance" in data:
        bipol_res = data
    else:
        raw_params = data.get("params") if isinstance(data.get("params"), dict) else data
        if not raw_params:
            raw_params = dict(AIRCRAFT_PRESETS["pzl_kos"])
        bipol_res = run_bipol_project(raw_params)

    params = bipol_res["params"]
    geom = bipol_res["geometry"]
    balance = bipol_res["balance"]
    profile_geom = bipol_res.get("profile_geometry") or {}

    wing = geom["wing"]
    fus = geom["fuselage"]
    htail = geom["horizontal_tail"]
    vtail = geom["vertical_tail"]
    ctrl = geom.get("control_surfaces") or {}

    L_fus = float(fus["length"])
    D_fus = float(fus["diameter"])
    b = float(wing["b"])
    half_span = b / 2.0
    S = float(wing["S"])
    cr = float(wing["cr"])
    ct = max(0.15, float(wing["ct"]))
    sweep_q_deg = float(wing["sweep_deg"])
    dihedral_deg = float(wing["dihedral_deg"])
    tc_ratio = float(wing.get("tc_ratio", params.get("tc_ratio", 0.12)))
    from calculations.vsp_airfoils import resolve_wing_airfoil
    wing_profile, wing_airfoil_meta = resolve_wing_airfoil(params, tc_ratio)
    _LAST_BIPOL_RESULT = bipol_res
    planform = str(wing.get("wing_planform", params.get("wing_planform", "trapezoidal")))
    wing_config = str(wing.get("wing_config", params.get("wing_config", "low")))
    tail_type = str(params.get("tail_type", "conventional"))
    engine_type = str(params.get("engine_type", "prop"))
    engine_loc = str(params.get("engine_location", "nose"))
    engine_count = int(params.get("engine_count", 1) or 1)
    camber = float(profile_geom.get("max_camber_ratio", 0.02))
    camber_loc = float(profile_geom.get("max_camber_x", 0.40))

    x_le_wing = float(balance.get("x_le_wing_m", 0.30 * L_fus))
    if wing_config == "high":
        z_wing = 0.38 * D_fus
    elif wing_config == "mid":
        z_wing = 0.0
    else:
        z_wing = -0.36 * D_fus

    with _VSP_LOCK:
        _pop_vsp_errors()
        vsp.ClearVSPModel()

        created_ids: dict[str, str] = {}

        # 1. KADŁUB (FUSELAGE)
        fus_id = vsp.AddGeom("FUSELAGE", "")
        vsp.SetGeomName(fus_id, "Kadlub")
        created_ids["fuselage"] = fus_id
        _set_geom_parm(fus_id, "Length", "Design", L_fus)
        fus_stations = [
            (1, 0.16, 0.72 * D_fus, 0.76 * D_fus, -0.04 * D_fus),
            (2, 0.38, 1.00 * D_fus, 1.04 * D_fus, 0.00),
            (3, 0.72, 0.56 * D_fus, 0.62 * D_fus, 0.05 * D_fus),
        ]
        xsurf_fus = vsp.GetXSecSurf(fus_id, 0)
        for idx, x_pct, w_m, h_m, z_off in fus_stations:
            try:
                vsp.ChangeXSecShape(xsurf_fus, idx, vsp.XS_ELLIPSE)
            except Exception:
                pass
            _set_geom_parm(fus_id, "XLocPercent", f"XSec_{idx}", x_pct)
            _set_geom_parm(fus_id, "ZLocPercent", f"XSec_{idx}", z_off / max(1.0, L_fus))
            _set_geom_parm(fus_id, "Ellipse_Width", f"XSecCurve_{idx}", w_m)
            _set_geom_parm(fus_id, "Ellipse_Height", f"XSecCurve_{idx}", h_m)
        _set_geom_parm(fus_id, "ZLocPercent", "XSec_4", 0.035)

        # 2. SKRZYDŁO GŁÓWNE (WING)
        wing_id = vsp.AddGeom("WING", "")
        vsp.SetGeomName(wing_id, "Skrzydlo_Glowne")
        created_ids["wing"] = wing_id
        _set_geom_parm(wing_id, "Sym_Planar_Flag", "Sym", float(vsp.SYM_XZ))
        _set_geom_parm(wing_id, "X_Rel_Location", "XForm", x_le_wing)
        _set_geom_parm(wing_id, "Z_Rel_Location", "XForm", z_wing)

        if planform == "compound_trapezoid":
            y_brk = float(wing.get("break_station_m") or (0.40 * half_span))
            span_in = max(0.3, min(half_span - 0.3, y_brk))
            span_out = max(0.3, half_span - span_in)

            vsp.InsertXSec(wing_id, 1, vsp.XS_FOUR_SERIES)
            vsp.SetDriverGroup(wing_id, 1, vsp.SPAN_WSECT_DRIVER, vsp.ROOTC_WSECT_DRIVER, vsp.TIPC_WSECT_DRIVER)
            _set_geom_parm(wing_id, "Span", "XSec_1", span_in)
            _set_geom_parm(wing_id, "Root_Chord", "XSec_1", cr)
            _set_geom_parm(wing_id, "Tip_Chord", "XSec_1", cr)
            _set_geom_parm(wing_id, "Sweep", "XSec_1", 0.0)
            _set_geom_parm(wing_id, "Sweep_Location", "XSec_1", 0.25)
            _set_geom_parm(wing_id, "Dihedral", "XSec_1", dihedral_deg)
            _set_geom_parm(wing_id, "Twist", "XSec_1", 0.0)

            vsp.SetDriverGroup(wing_id, 2, vsp.SPAN_WSECT_DRIVER, vsp.ROOTC_WSECT_DRIVER, vsp.TIPC_WSECT_DRIVER)
            _set_geom_parm(wing_id, "Span", "XSec_2", span_out)
            _set_geom_parm(wing_id, "Root_Chord", "XSec_2", cr)
            _set_geom_parm(wing_id, "Tip_Chord", "XSec_2", ct)
            _set_geom_parm(wing_id, "Sweep", "XSec_2", sweep_q_deg)
            _set_geom_parm(wing_id, "Sweep_Location", "XSec_2", 0.25)
            _set_geom_parm(wing_id, "Dihedral", "XSec_2", dihedral_deg)
            _set_geom_parm(wing_id, "Twist", "XSec_2", -2.0)

            for idx in (0, 1, 2):
                _set_wing_airfoil(wing_id, idx, camber, camber_loc, tc_ratio, profile=wing_profile)
        elif planform == "elliptical":
            span_1 = 0.60 * half_span
            span_2 = 0.40 * half_span
            c_mid = cr * math.sqrt(max(0.05, 1.0 - 0.60 ** 2))
            c_tip = max(0.22 * cr, ct)

            vsp.InsertXSec(wing_id, 1, vsp.XS_FOUR_SERIES)
            vsp.SetDriverGroup(wing_id, 1, vsp.SPAN_WSECT_DRIVER, vsp.ROOTC_WSECT_DRIVER, vsp.TIPC_WSECT_DRIVER)
            _set_geom_parm(wing_id, "Span", "XSec_1", span_1)
            _set_geom_parm(wing_id, "Root_Chord", "XSec_1", cr)
            _set_geom_parm(wing_id, "Tip_Chord", "XSec_1", c_mid)
            _set_geom_parm(wing_id, "Sweep", "XSec_1", sweep_q_deg)
            _set_geom_parm(wing_id, "Sweep_Location", "XSec_1", 0.25)
            _set_geom_parm(wing_id, "Dihedral", "XSec_1", dihedral_deg)

            vsp.SetDriverGroup(wing_id, 2, vsp.SPAN_WSECT_DRIVER, vsp.ROOTC_WSECT_DRIVER, vsp.TIPC_WSECT_DRIVER)
            _set_geom_parm(wing_id, "Span", "XSec_2", span_2)
            _set_geom_parm(wing_id, "Root_Chord", "XSec_2", c_mid)
            _set_geom_parm(wing_id, "Tip_Chord", "XSec_2", c_tip)
            _set_geom_parm(wing_id, "Sweep", "XSec_2", sweep_q_deg)
            _set_geom_parm(wing_id, "Sweep_Location", "XSec_2", 0.25)
            _set_geom_parm(wing_id, "Dihedral", "XSec_2", dihedral_deg)
            _set_geom_parm(wing_id, "Twist", "XSec_2", -1.5)

            for idx in (0, 1, 2):
                _set_wing_airfoil(wing_id, idx, camber, camber_loc, tc_ratio, profile=wing_profile)
        else:
            vsp.SetDriverGroup(wing_id, 1, vsp.SPAN_WSECT_DRIVER, vsp.ROOTC_WSECT_DRIVER, vsp.TIPC_WSECT_DRIVER)
            _set_geom_parm(wing_id, "Span", "XSec_1", half_span)
            _set_geom_parm(wing_id, "Root_Chord", "XSec_1", cr)
            _set_geom_parm(wing_id, "Tip_Chord", "XSec_1", ct)
            _set_geom_parm(wing_id, "Sweep", "XSec_1", sweep_q_deg)
            _set_geom_parm(wing_id, "Sweep_Location", "XSec_1", 0.25)
            _set_geom_parm(wing_id, "Dihedral", "XSec_1", dihedral_deg)
            _set_geom_parm(wing_id, "Twist", "XSec_1", -1.5 if planform != "rectangular" else 0.0)
            for idx in (0, 1):
                _set_wing_airfoil(wing_id, idx, camber, camber_loc, tc_ratio, profile=wing_profile)

        _set_geom_parm(wing_id, "CapUMaxOption", "EndCap", float(vsp.ROUND_END_CAP))

        flaps_cfg = ctrl.get("flaps") or {}
        ail_cfg = ctrl.get("ailerons") or {}
        slats_cfg = ctrl.get("slats") or {}
        if flaps_cfg.get("type") not in (None, "none") and float(flaps_cfg.get("cf_over_c", 0)) > 0:
            _add_control_subsurface(
                wing_id,
                "Klapy_Podskrzydlowe",
                float(flaps_cfg.get("eta_in", 0.12)),
                float(flaps_cfg.get("eta_out", 0.65)),
                float(flaps_cfg.get("cf_over_c", 0.25)),
                le_flag=0,
            )
        if not ctrl.get("is_flaperon") and float(ail_cfg.get("ca_over_c", 0.22)) > 0:
            _add_control_subsurface(
                wing_id,
                "Lotki",
                float(ail_cfg.get("eta_in", 0.68)),
                float(ail_cfg.get("eta_out", 0.95)),
                float(ail_cfg.get("ca_over_c", 0.22)),
                le_flag=0,
            )
        if slats_cfg.get("type") not in (None, "none"):
            _add_control_subsurface(wing_id, "Sloty_LE", 0.15, 0.92, 0.15, le_flag=1)

        # 3. USTERZENIE POZIOME I PIONOWE (EMPENNAGE)
        b_h = float(htail["b_h"])
        cr_h = float(htail["cr_h"])
        ct_h = max(0.12, float(htail["ct_h"]))
        x_ac_h = float(htail.get("x_ac_m", 0.90 * L_fus))
        x_le_h = max(0.55 * L_fus, x_ac_h - 0.25 * float(htail["mac_h"]))

        h_v = float(vtail["h_v"])
        cr_v = float(vtail["cr_v"])
        ct_v = max(0.12, float(vtail["ct_v"]))
        x_ac_v = float(vtail.get("x_ac_m", 0.90 * L_fus))
        x_le_v = max(0.55 * L_fus, x_ac_v - 0.25 * float(vtail["mac_v"]))
        z_tail_base = 0.12 * D_fus

        if tail_type == "v_tail":
            s_vtail_total = float(htail["S_h"]) + float(vtail["S_v"])
            dihedral_v = math.degrees(math.atan2(math.sqrt(max(0.01, float(vtail["S_v"]))), math.sqrt(max(0.01, float(htail["S_h"])))))
            span_v_half = 0.5 * math.sqrt(max(0.2, s_vtail_total * float(htail["AR_h"])))
            ht_id = vsp.AddGeom("WING", "")
            vsp.SetGeomName(ht_id, "Usterzenie_V_Rudlickiego")
            created_ids["horizontal_tail"] = ht_id
            _set_geom_parm(ht_id, "Sym_Planar_Flag", "Sym", float(vsp.SYM_XZ))
            _set_geom_parm(ht_id, "X_Rel_Location", "XForm", x_le_h)
            _set_geom_parm(ht_id, "Z_Rel_Location", "XForm", z_tail_base)
            vsp.SetDriverGroup(ht_id, 1, vsp.SPAN_WSECT_DRIVER, vsp.ROOTC_WSECT_DRIVER, vsp.TIPC_WSECT_DRIVER)
            _set_geom_parm(ht_id, "Span", "XSec_1", span_v_half)
            _set_geom_parm(ht_id, "Root_Chord", "XSec_1", cr_h)
            _set_geom_parm(ht_id, "Tip_Chord", "XSec_1", ct_h)
            _set_geom_parm(ht_id, "Sweep", "XSec_1", 12.0)
            _set_geom_parm(ht_id, "Dihedral", "XSec_1", dihedral_v)
            for idx in (0, 1):
                _set_wing_airfoil(ht_id, idx, 0.0, 0.40, 0.09)
            _add_control_subsurface(ht_id, "Sterolotki_Rudlickiego", 0.12, 0.92, float(htail.get("ce_over_ch", 0.35)))
        else:
            vt_id = vsp.AddGeom("WING", "")
            vsp.SetGeomName(vt_id, "Usterzenie_Pionowe")
            created_ids["vertical_tail"] = vt_id
            is_twin = tail_type == "twin"
            _set_geom_parm(vt_id, "Sym_Planar_Flag", "Sym", float(vsp.SYM_XZ if is_twin else vsp.SYM_NONE))
            _set_geom_parm(vt_id, "X_Rel_Location", "XForm", x_le_v)
            if is_twin:
                _set_geom_parm(vt_id, "Y_Rel_Location", "XForm", 0.46 * b_h)
            _set_geom_parm(vt_id, "Z_Rel_Location", "XForm", z_tail_base)
            _set_geom_parm(vt_id, "X_Rel_Rotation", "XForm", 90.0)
            vsp.SetDriverGroup(vt_id, 1, vsp.SPAN_WSECT_DRIVER, vsp.ROOTC_WSECT_DRIVER, vsp.TIPC_WSECT_DRIVER)
            _set_geom_parm(vt_id, "Span", "XSec_1", h_v * (0.72 if is_twin else 1.0))
            _set_geom_parm(vt_id, "Root_Chord", "XSec_1", cr_v)
            _set_geom_parm(vt_id, "Tip_Chord", "XSec_1", ct_v)
            _set_geom_parm(vt_id, "Sweep", "XSec_1", 26.0)
            _set_geom_parm(vt_id, "Sweep_Location", "XSec_1", 0.25)
            for idx in (0, 1):
                _set_wing_airfoil(vt_id, idx, 0.0, 0.40, 0.09)
            _add_control_subsurface(vt_id, "Ster_Kierunku", 0.10, 0.92, float(vtail.get("cr_over_cv", 0.35)))

            if tail_type == "t_tail":
                z_ht = z_tail_base + 0.92 * h_v
                x_ht = x_le_v + 0.30 * cr_v
            elif tail_type == "cruciform":
                z_ht = z_tail_base + 0.48 * h_v
                x_ht = x_le_v + 0.15 * cr_v
            else:
                z_ht = z_tail_base
                x_ht = x_le_h

            ht_id = vsp.AddGeom("WING", "")
            vsp.SetGeomName(ht_id, "Usterzenie_Poziome")
            created_ids["horizontal_tail"] = ht_id
            _set_geom_parm(ht_id, "Sym_Planar_Flag", "Sym", float(vsp.SYM_XZ))
            _set_geom_parm(ht_id, "X_Rel_Location", "XForm", x_ht)
            _set_geom_parm(ht_id, "Z_Rel_Location", "XForm", z_ht)
            vsp.SetDriverGroup(ht_id, 1, vsp.SPAN_WSECT_DRIVER, vsp.ROOTC_WSECT_DRIVER, vsp.TIPC_WSECT_DRIVER)
            _set_geom_parm(ht_id, "Span", "XSec_1", 0.5 * b_h)
            _set_geom_parm(ht_id, "Root_Chord", "XSec_1", cr_h)
            _set_geom_parm(ht_id, "Tip_Chord", "XSec_1", ct_h)
            _set_geom_parm(ht_id, "Sweep", "XSec_1", max(6.0, sweep_q_deg * 0.7))
            _set_geom_parm(ht_id, "Sweep_Location", "XSec_1", 0.25)
            for idx in (0, 1):
                _set_wing_airfoil(ht_id, idx, 0.0, 0.40, 0.09)
            _add_control_subsurface(ht_id, "Ster_Wysokosci", 0.08, 0.94, float(htail.get("ce_over_ch", 0.35)))

        # 4. ZESPÓŁ NAPĘDOWY (PROP / POD)
        if engine_type != "none":
            prop_diam = float(params.get("propeller_diameter_m") or geom.get('propeller',{}).get('diameter_m')
                              or max(1.3, min(2.4, 0.15 * b)))
            blade_cnt = int(params.get("blade_count") or 3)
            if engine_type == "prop":
                if engine_loc == "nose" or (engine_count == 1 and engine_loc not in ("rear", "wing", "retractable")):
                    prop_id = vsp.AddGeom("PROP", "")
                    vsp.SetGeomName(prop_id, "Smiglo_Ciagnace")
                    created_ids["propeller"] = prop_id
                    _set_geom_parm(prop_id, "Diameter", "Design", prop_diam)
                    _set_geom_parm(prop_id, "NumBlade", "Design", float(blade_cnt))
                    _set_geom_parm(prop_id, "X_Rel_Location", "XForm", -0.05)
                elif engine_loc == "wing" or engine_count >= 2:
                    y_nac = 0.28 * half_span
                    x_nac = x_le_wing - 0.35 * cr
                    z_nac = z_wing - 0.06 * D_fus
                    nac_id = vsp.AddGeom("POD", "")
                    vsp.SetGeomName(nac_id, "Gondola_Silnika")
                    created_ids["nacelle"] = nac_id
                    _set_geom_parm(nac_id, "Sym_Planar_Flag", "Sym", float(vsp.SYM_XZ))
                    _set_geom_parm(nac_id, "Length", "Design", max(1.4, 0.95 * cr))
                    _set_geom_parm(nac_id, "FineRatio", "Design", 4.2)
                    _set_geom_parm(nac_id, "X_Rel_Location", "XForm", x_nac)
                    _set_geom_parm(nac_id, "Y_Rel_Location", "XForm", y_nac)
                    _set_geom_parm(nac_id, "Z_Rel_Location", "XForm", z_nac)

                    prop_id = vsp.AddGeom("PROP", "")
                    vsp.SetGeomName(prop_id, "Smigla_Skrzydlowe")
                    created_ids["propeller"] = prop_id
                    _set_geom_parm(prop_id, "Sym_Planar_Flag", "Sym", float(vsp.SYM_XZ))
                    _set_geom_parm(prop_id, "Diameter", "Design", prop_diam)
                    _set_geom_parm(prop_id, "NumBlade", "Design", float(blade_cnt))
                    _set_geom_parm(prop_id, "X_Rel_Location", "XForm", x_nac - 0.04)
                    _set_geom_parm(prop_id, "Y_Rel_Location", "XForm", y_nac)
                    _set_geom_parm(prop_id, "Z_Rel_Location", "XForm", z_nac)
                else:
                    prop_id = vsp.AddGeom("PROP", "")
                    vsp.SetGeomName(prop_id, "Smiglo_Pchajace")
                    created_ids["propeller"] = prop_id
                    _set_geom_parm(prop_id, "Diameter", "Design", prop_diam)
                    _set_geom_parm(prop_id, "NumBlade", "Design", float(blade_cnt))
                    _set_geom_parm(prop_id, "X_Rel_Location", "XForm", 0.52 * L_fus if engine_loc == "retractable" else L_fus + 0.05)
                    _set_geom_parm(prop_id, "Z_Rel_Location", "XForm", 0.65 * D_fus if engine_loc == "retractable" else 0.12 * D_fus)
            else:
                nac_id = vsp.AddGeom("POD", "")
                vsp.SetGeomName(nac_id, "Gondola_Odrzutowa")
                created_ids["nacelle"] = nac_id
                _set_geom_parm(nac_id, "Sym_Planar_Flag", "Sym", float(vsp.SYM_XZ if engine_count >= 2 else vsp.SYM_NONE))
                nac_len = max(1.8, 0.22 * L_fus)
                _set_geom_parm(nac_id, "Length", "Design", nac_len)
                _set_geom_parm(nac_id, "FineRatio", "Design", 3.6)
                if engine_loc == "wing":
                    _set_geom_parm(nac_id, "X_Rel_Location", "XForm", x_le_wing + 0.10 * cr)
                    _set_geom_parm(nac_id, "Y_Rel_Location", "XForm", 0.30 * half_span)
                    _set_geom_parm(nac_id, "Z_Rel_Location", "XForm", z_wing - 0.28 * D_fus)
                else:
                    _set_geom_parm(nac_id, "X_Rel_Location", "XForm", 0.68 * L_fus)
                    _set_geom_parm(nac_id, "Y_Rel_Location", "XForm", 0.62 * D_fus if engine_count >= 2 else 0.0)
                    _set_geom_parm(nac_id, "Z_Rel_Location", "XForm", 0.25 * D_fus if engine_count >= 2 else 0.55 * D_fus)

        # 5. PODWOZIE (LANDING GEAR - koła główne i przednie/tylne)
        if str(params.get("operating_surface", "concrete")) != "water" and str(params.get("gear_type", "fixed")) == "fixed":
            track = float(geom["gear"]["track"])
            tailwheel=params.get('landing_gear_type')=='tailwheel'
            x_main_gear=float(balance['arms']['gear'])
            x_aux_gear=float(balance['arms']['gear_aux'])
            from calculations.geometry import axis_height_m
            ground=-axis_height_m(params,D_fus,(geom.get('propeller') or {}).get('diameter_m'))
            main_length,aux_length=max(.55,.07*L_fus),max(.45,.055*L_fus)
            # A POD starts at its nose; FineRatio is length/radius. Place its
            # centre on the wheel station and its lowest point on the ground.
            fine_ratio=2.8

            mg_id = vsp.AddGeom("POD", "")
            vsp.SetGeomName(mg_id, "Podwozie_Glowne")
            created_ids["main_gear"] = mg_id
            _set_geom_parm(mg_id, "Sym_Planar_Flag", "Sym", float(vsp.SYM_XZ))
            _set_geom_parm(mg_id, "Length", "Design", main_length)
            _set_geom_parm(mg_id, "FineRatio", "Design", fine_ratio)
            _set_geom_parm(mg_id, "X_Rel_Location", "XForm", x_main_gear-main_length/2)
            _set_geom_parm(mg_id, "Y_Rel_Location", "XForm", 0.5 * track)
            _set_geom_parm(mg_id, "Z_Rel_Location", "XForm", ground+main_length/fine_ratio)

            ng_id = vsp.AddGeom("POD", "")
            vsp.SetGeomName(ng_id, "Kolko_Ogonowe" if tailwheel else "Podwozie_Przednie")
            created_ids["tail_gear" if tailwheel else "nose_gear"] = ng_id
            _set_geom_parm(ng_id, "Length", "Design", aux_length)
            _set_geom_parm(ng_id, "FineRatio", "Design", fine_ratio)
            _set_geom_parm(ng_id, "X_Rel_Location", "XForm", x_aux_gear-aux_length/2)
            _set_geom_parm(ng_id, "Z_Rel_Location", "XForm", ground+aux_length/fine_ratio)

        vsp.Update()
        vsp.SetVSP3FileName(DEFAULT_VSP3_REL)
        vsp.WriteVSPFile(DEFAULT_VSP3_REL, vsp.SET_ALL)

        aero_res = bipol_res.get("aerodynamics") or {}
        ld_max = float(aero_res.get("k_max") or aero_res.get("k_clean") or 0.0)

        _LAST_BUILD_META = {
            "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "vsp3_file": DEFAULT_VSP3_REL,
            "created_ids": created_ids,
            "wing_airfoil": wing_airfoil_meta,
            "bipol_summary": {
                "m0_kg": round(float(bipol_res["mass"]["m0"]), 2),
                "S_m2": round(S, 3),
                "b_m": round(b, 3),
                "mac_m": round(float(wing["mac"]), 3),
                "L_fus_m": round(L_fus, 3),
                "D_fus_m": round(D_fus, 3),
                "S_h_m2": round(float(htail["S_h"]), 3),
                "S_v_m2": round(float(vtail["S_v"]), 3),
                "S_wet_bipol_m2": round(float(geom["wetted_area"]["total_m2"]), 3),
                "cx0_clean_bipol": round(float(aero_res.get("cx0_clean", 0.025)), 5),
                "ld_max_bipol": round(ld_max, 2),
                "x_le_wing_m": round(x_le_wing, 3),
                "wing_planform": planform,
                "tail_type": tail_type,
            },
            "schrenk": geom.get("schrenk", []),
        }
        state = get_model_state(include_mesh=True, include_all_parms=True)
        return state


def modify_geometry(payload: dict[str, Any]) -> dict[str, Any]:
    """Obsługuje dodawanie/usuwanie/kopiowanie komponentów Geom, podpowierzchni SubSurf, przekrojów XSec i profili."""
    action = str(payload.get("action") or "add_geom").strip()
    with _VSP_LOCK:
        _pop_vsp_errors()
        created_id = None

        if action == "add_geom":
            geom_type = str(payload.get("geom_type") or "WING").strip().upper()
            parent_id = str(payload.get("parent_id") or "")
            name = str(payload.get("name") or f"{geom_type}_Nowy")
            created_id = vsp.AddGeom(geom_type, parent_id)
            if created_id and name:
                vsp.SetGeomName(created_id, name)

        elif action == "delete_geom":
            geom_id = str(payload.get("geom_id") or "")
            if geom_id:
                vsp.DeleteGeom(geom_id)

        elif action == "rename_geom":
            geom_id = str(payload.get("geom_id") or "")
            name = str(payload.get("name") or "")
            if geom_id and name:
                vsp.SetGeomName(geom_id, name)

        elif action == "copy_paste_geom":
            geom_id = str(payload.get("geom_id") or "")
            parent_id = str(payload.get("parent_id") or "")
            if geom_id:
                vsp.CopyGeomToClipboard(geom_id)
                pasted = list(vsp.PasteGeomClipboard(parent_id))
                created_id = pasted[0] if pasted else None

        elif action == "add_subsurf":
            geom_id = str(payload.get("geom_id") or "")
            ss_type = _coerce_arg_for_vsp(payload.get("subsurf_type", "SS_CONTROL"))
            name = str(payload.get("name") or "SubSurf_Nowy")
            if geom_id:
                created_id = vsp.AddSubSurf(geom_id, int(ss_type), 0)
                if created_id and name:
                    vsp.SetSubSurfName(geom_id, created_id, name)

        elif action == "delete_subsurf":
            geom_id = str(payload.get("geom_id") or "")
            sub_id = str(payload.get("subsurf_id") or "")
            if geom_id and sub_id:
                vsp.DeleteSubSurf(geom_id, sub_id)

        elif action == "insert_xsec":
            geom_id = str(payload.get("geom_id") or "")
            index = int(payload.get("xsec_index", 1))
            shape = _coerce_arg_for_vsp(payload.get("xsec_type", "XS_FOUR_SERIES"))
            if geom_id:
                created_id = vsp.InsertXSec(geom_id, index, int(shape))

        elif action == "cut_xsec":
            geom_id = str(payload.get("geom_id") or "")
            index = int(payload.get("xsec_index", 1))
            if geom_id:
                vsp.CutXSec(geom_id, index)

        elif action == "change_xsec_shape":
            geom_id = str(payload.get("geom_id") or "")
            surf_idx = int(payload.get("surf_index", 0))
            xsec_idx = int(payload.get("xsec_index", 0))
            shape = _coerce_arg_for_vsp(payload.get("xsec_type", "XS_FOUR_SERIES"))
            if geom_id:
                xsurf = vsp.GetXSecSurf(geom_id, surf_idx)
                vsp.ChangeXSecShape(xsurf, xsec_idx, int(shape))

        elif action == "clear_model":
            vsp.ClearVSPModel()
            _LAST_BUILD_META.clear()

        else:
            raise ValueError(f"Nieznana akcja geometrii: {action}")

        vsp.Update()
        if vsp.FindGeoms():
            vsp.WriteVSPFile(DEFAULT_VSP3_REL, vsp.SET_ALL)
        errors = _pop_vsp_errors()
        state = get_model_state(include_mesh=True, include_all_parms=True)
        state["action"] = action
        state["created_id"] = created_id
        state["vsp_errors"] = errors
        return state


def update_parameters(payload: dict[str, Any]) -> dict[str, Any]:
    """Aktualizuje jeden lub wiele parametrów OpenVSP (`SetParmVal`) i przebudowuje siatkę 3D."""
    updates = payload.get("updates")
    if not isinstance(updates, list):
        updates = [payload]

    applied = []
    with _VSP_LOCK:
        _pop_vsp_errors()
        for item in updates:
            val = float(item.get("value", 0.0))
            parm_id = str(item.get("parm_id") or "").strip()
            geom_id = str(item.get("geom_id") or "").strip()
            name = str(item.get("name") or "").strip()
            group = str(item.get("group") or "").strip()

            if parm_id:
                new_val = vsp.SetParmVal(parm_id, val)
                applied.append({"parm_id": parm_id, "value": new_val})
            elif geom_id and name and group:
                new_val = _set_geom_parm(geom_id, name, group, val)
                applied.append({"geom_id": geom_id, "name": name, "group": group, "value": new_val})
            else:
                raise ValueError("Wymagane 'parm_id' lub trójka ('geom_id', 'name', 'group').")

        vsp.Update()
        if vsp.FindGeoms():
            vsp.WriteVSPFile(DEFAULT_VSP3_REL, vsp.SET_ALL)
        errors = _pop_vsp_errors()
        state = get_model_state(include_mesh=True, include_all_parms=True)
        state["applied"] = applied
        state["vsp_errors"] = errors
        return state


def _parse_results_recursive(res_id: str, visited: set[str] | None = None) -> dict[str, Any]:
    """Rekurencyjnie parsuje obiekt wyników `ResultsMgr` OpenVSP wraz z pod-wynikami (np. VSPAERO ResultsVec)."""
    if not res_id:
        return {}
    if visited is None:
        visited = set()
    if res_id in visited:
        return {"id": res_id, "note": "already_visited"}
    visited.add(res_id)

    res_name = vsp.GetResultsName(res_id)
    data_names = list(vsp.GetAllDataNames(res_id))
    data_dict: dict[str, Any] = {}
    children: list[dict[str, Any]] = []

    for d_name in data_names:
        d_type = vsp.GetResultsType(res_id, d_name)
        vals: Any = []
        if d_type == vsp.INT_DATA:
            vals = list(vsp.GetIntResults(res_id, d_name))
        elif d_type == vsp.DOUBLE_DATA:
            vals = [_serialize_vsp_value(x) for x in vsp.GetDoubleResults(res_id, d_name)]
        elif d_type == vsp.STRING_DATA:
            vals = list(vsp.GetStringResults(res_id, d_name))
            if d_name in ("ResultsVec", "HistoryResID", "LoadResID", "CpSlice_Case_ID_Vec", "components", "surfaces"):
                for sub_id in vals[:12]:
                    try:
                        if vsp.GetAllDataNames(sub_id):
                            children.append(_parse_results_recursive(sub_id, visited))
                    except Exception:
                        pass
        elif d_type == vsp.VEC3D_DATA:
            vals = [_serialize_vsp_value(x) for x in vsp.GetVec3dResults(res_id, d_name)]
        elif d_type == vsp.DOUBLE_MATRIX_DATA:
            vals = _serialize_vsp_value(vsp.GetDoubleMatResults(res_id, d_name))
        data_dict[d_name] = vals

    return {
        "id": res_id,
        "name": res_name,
        "data": data_dict,
        "children": children,
    }


def run_vsp_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Konfiguruje i uruchamia dowolną z 22 analiz OpenVSP (`ExecAnalysis`), parsuje drzewo wyników
    oraz generuje zestawienie porównawcze z projektem BiPOL (dla CompGeom, ParasiteDrag, VSPAERO, MassProp, WaveDrag).
    """
    analysis_name = str(payload.get("analysis") or "CompGeom").strip()
    custom_inputs = dict(payload.get("inputs") or {})
    reset_defaults = bool(payload.get("reset_defaults", True))

    with _VSP_LOCK:
        _pop_vsp_errors()
        if not vsp.FindGeoms():
            build_model_from_bipol()

        vsp.Update()
        vsp.SetVSP3FileName(DEFAULT_VSP3_REL)
        vsp.WriteVSPFile(DEFAULT_VSP3_REL, vsp.SET_ALL)

        available_analyses = list(vsp.ListAnalysis())
        if analysis_name not in available_analyses:
            raise ValueError(f"Nieznana analiza OpenVSP: '{analysis_name}'. Dostępne: {', '.join(available_analyses)}")

        if reset_defaults:
            vsp.SetAnalysisInputDefaults(analysis_name)

        bipol_meta = _LAST_BUILD_META.get("bipol_summary") or {}
        s_ref = float(bipol_meta.get("S_m2") or 12.0)
        b_ref = float(bipol_meta.get("b_m") or 10.0)
        c_ref = float(bipol_meta.get("mac_m") or 1.3)

        if analysis_name == "CompGeom":
            vsp.SetIntAnalysisInput("CompGeom", "WriteCSVFlag", [0])

        elif analysis_name == "ParasiteDrag":
            vsp.SetIntAnalysisInput("ParasiteDrag", "GeomSet", [vsp.SET_ALL])
            vsp.SetIntAnalysisInput("ParasiteDrag", "RecomputeGeom", [1])
            vsp.SetIntAnalysisInput("ParasiteDrag", "LengthUnit", [vsp.LEN_M])
            vsp.SetIntAnalysisInput("ParasiteDrag", "VelocityUnit", [vsp.V_UNIT_KM_HR])
            vsp.SetIntAnalysisInput("ParasiteDrag", "AltLengthUnit", [vsp.LEN_M])
            vsp.SetIntAnalysisInput("ParasiteDrag", "RefFlag", [0])
            vsp.SetDoubleAnalysisInput("ParasiteDrag", "Sref", [s_ref])
            cruise_kmh = float((_LAST_BIPOL_RESULT or {}).get("params", {}).get("cruise_speed_kmh", 220.0))
            cruise_alt_m = float((_LAST_BIPOL_RESULT or {}).get("params", {}).get("cruise_altitude_m", 2000.0))
            vsp.SetDoubleAnalysisInput("ParasiteDrag", "Vinf", [cruise_kmh])
            vsp.SetDoubleAnalysisInput("ParasiteDrag", "Altitude", [cruise_alt_m])
            vsp.SetStringAnalysisInput("ParasiteDrag", "FileName", [_ascii_rel_path("parasite_drag.csv")])

        elif analysis_name in ("VSPAEROSweep", "VSPAEROSinglePoint"):
            vsp.SetAnalysisInputDefaults("VSPAEROComputeGeometry")
            vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "GeomSet", [vsp.SET_NONE])
            vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "ThinGeomSet", [vsp.SET_ALL])
            vsp.ExecAnalysis("VSPAEROComputeGeometry")

            vsp.SetIntAnalysisInput(analysis_name, "GeomSet", [vsp.SET_NONE])
            vsp.SetIntAnalysisInput(analysis_name, "ThinGeomSet", [vsp.SET_ALL])
            vsp.SetIntAnalysisInput(analysis_name, "RefFlag", [0])
            vsp.SetDoubleAnalysisInput(analysis_name, "Sref", [s_ref])
            vsp.SetDoubleAnalysisInput(analysis_name, "bref", [b_ref])
            vsp.SetDoubleAnalysisInput(analysis_name, "cref", [c_ref])
            vsp.SetDoubleAnalysisInput(analysis_name, "AlphaStart", [-2.0])
            vsp.SetDoubleAnalysisInput(analysis_name, "AlphaEnd", [10.0])
            vsp.SetIntAnalysisInput(analysis_name, "AlphaNpts", [4])
            vsp.SetDoubleAnalysisInput(analysis_name, "MachStart", [0.18])
            vsp.SetIntAnalysisInput(analysis_name, "MachNpts", [1])
            vsp.SetIntAnalysisInput(analysis_name, "WakeNumIter", [3])
            vsp.SetIntAnalysisInput(analysis_name, "NCPU", [4])

        valid_inputs = set(vsp.GetAnalysisInputNames(analysis_name))
        for inp_name, raw_val in custom_inputs.items():
            if inp_name not in valid_inputs:
                continue
            t_code = vsp.GetAnalysisInputType(analysis_name, inp_name)
            val_list = raw_val if isinstance(raw_val, list) else [raw_val]
            if t_code == vsp.INT_DATA:
                vsp.SetIntAnalysisInput(analysis_name, inp_name, [int(_coerce_arg_for_vsp(x)) for x in val_list])
            elif t_code == vsp.DOUBLE_DATA:
                vsp.SetDoubleAnalysisInput(analysis_name, inp_name, [float(_coerce_arg_for_vsp(x)) for x in val_list])
            elif t_code == vsp.STRING_DATA:
                vsp.SetStringAnalysisInput(
                    analysis_name,
                    inp_name,
                    [str(_coerce_arg_for_vsp(x, {"name": inp_name}, analysis_name)) for x in val_list],
                )
            elif t_code == vsp.VEC3D_DATA:
                vsp.SetVec3dAnalysisInput(
                    analysis_name,
                    inp_name,
                    [_coerce_arg_for_vsp(x, {"type": "vec3d"}) for x in val_list],
                )

        t0 = time.perf_counter()
        res_id = vsp.ExecAnalysis(analysis_name)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        parsed = _parse_results_recursive(res_id)

        comparison = _build_analysis_comparison(analysis_name, parsed)
        errors = _pop_vsp_errors()

        return {
            "status": "ok",
            "analysis": analysis_name,
            "result_id": res_id,
            "elapsed_ms": elapsed_ms,
            "results": parsed,
            "comparison": comparison,
            "vsp_errors": errors,
        }


def _build_analysis_comparison(analysis_name: str, parsed: dict[str, Any]) -> dict[str, Any]:
    """Buduje czytelne tabele i serie wykresów porównujące wyniki OpenVSP z obliczeniami BiPOL."""
    data = parsed.get("data") or {}
    bipol_meta = _LAST_BUILD_META.get("bipol_summary") or {}

    if analysis_name == "CompGeom":
        comp_names = data.get("Comp_Name") or []
        wet_areas = data.get("Wet_Area") or []
        theo_areas = data.get("Theo_Area") or []
        wet_vols = data.get("Wet_Vol") or []
        total_wet = (data.get("Total_Wet_Area") or [sum(wet_areas)])[0] if wet_areas else 0.0
        total_vol = (data.get("Total_Wet_Vol") or [sum(wet_vols)])[0] if wet_vols else 0.0
        bipol_swet = float(bipol_meta.get("S_wet_bipol_m2") or 0.0)
        diff_pct = ((total_wet - bipol_swet) / bipol_swet * 100.0) if bipol_swet > 0 else 0.0

        rows = []
        for idx, name in enumerate(comp_names):
            rows.append({
                "component": name,
                "wet_area_m2": round(float(wet_areas[idx] or 0), 3) if idx < len(wet_areas) else 0.0,
                "theo_area_m2": round(float(theo_areas[idx] or 0), 3) if idx < len(theo_areas) else 0.0,
                "wet_vol_m3": round(float(wet_vols[idx] or 0), 4) if idx < len(wet_vols) else 0.0,
            })
        return {
            "type": "CompGeom",
            "total_wet_area_vsp_m2": round(float(total_wet), 3),
            "total_wet_area_bipol_m2": round(bipol_swet, 3),
            "diff_pct": round(diff_pct, 2),
            "total_volume_vsp_m3": round(float(total_vol), 4),
            "components": rows,
        }

    if analysis_name == "ParasiteDrag":
        labels = data.get("Comp_Label") or []
        cds = data.get("Comp_CD") or []
        swets = data.get("Comp_Swet") or []
        cfs = data.get("Comp_Cf") or []
        ffs = data.get("Comp_FFOut") or []
        total_cd = float((data.get("Total_CD_Total") or [0.0])[0] or 0.0)
        bipol_cx0 = float(bipol_meta.get("cx0_clean_bipol") or 0.0)
        rows = []
        for idx, lbl in enumerate(labels):
            rows.append({
                "component": lbl,
                "swet_m2": round(float(swets[idx] or 0), 3) if idx < len(swets) else 0.0,
                "cf": round(float(cfs[idx] or 0), 5) if idx < len(cfs) else 0.0,
                "form_factor": round(float(ffs[idx] or 0), 3) if idx < len(ffs) else 0.0,
                "cd0": round(float(cds[idx] or 0), 5) if idx < len(cds) else 0.0,
            })
        return {
            "type": "ParasiteDrag",
            "cd0_vsp": round(total_cd, 5),
            "cx0_bipol": round(bipol_cx0, 5),
            "diff_pct": round(((total_cd - bipol_cx0) / bipol_cx0 * 100.0) if bipol_cx0 > 0 else 0.0, 2),
            "components": rows,
        }

    if analysis_name in ("VSPAEROSweep", "VSPAEROSinglePoint"):
        children = parsed.get("children") or []
        polar_node = next((c for c in children if c.get("name") == "VSPAERO_Polar"), None)
        load_nodes = [c for c in children if c.get("name") == "VSPAERO_Load"]

        polar_rows = []
        if polar_node:
            pdata = polar_node.get("data") or {}
            alphas = pdata.get("Alpha") or []
            cls = pdata.get("CLtot") or []
            cds = pdata.get("CDtot") or []
            cdis = pdata.get("CDi") or []
            cdos = pdata.get("CDo") or []
            lds = pdata.get("L_D") or []
            cmys = pdata.get("CMytot") or []
            for idx, a in enumerate(alphas):
                polar_rows.append({
                    "alpha_deg": round(float(a or 0), 2),
                    "CL": round(float(cls[idx] or 0), 4) if idx < len(cls) else 0.0,
                    "CD": round(float(cds[idx] or 0), 5) if idx < len(cds) else 0.0,
                    "CDi": round(float(cdis[idx] or 0), 5) if idx < len(cdis) else 0.0,
                    "CDo": round(float(cdos[idx] or 0), 5) if idx < len(cdos) else 0.0,
                    "L_D": round(float(lds[idx] or 0), 2) if idx < len(lds) else 0.0,
                    "Cmy": round(float(cmys[idx] or 0), 4) if idx < len(cmys) else 0.0,
                })

        span_load = []
        if load_nodes:
            ldata = load_nodes[-1].get("data") or {}
            y_avgs = ldata.get("Yavg") or []
            cl_locs = ldata.get("cl") or []
            chords = ldata.get("Chord") or []
            b_half = max(0.5, float(bipol_meta.get("b_m", 10.0)) / 2.0)
            pts = []
            for y_val, cl_val, c_val in zip(y_avgs, cl_locs, chords):
                if y_val is not None and float(y_val) >= 0:
                    pts.append({
                        "y_m": round(float(y_val), 3),
                        "eta": round(float(y_val) / b_half, 3),
                        "cl": round(float(cl_val or 0), 4),
                        "chord_m": round(float(c_val or 0), 3),
                    })
            span_load = sorted(pts, key=lambda x: x["y_m"])

        return {
            "type": "VSPAERO",
            "polar": polar_rows,
            "spanwise_load": span_load,
            "schrenk_bipol": _LAST_BUILD_META.get("schrenk", []),
        }

    if analysis_name == "MassProp":
        return {
            "type": "MassProp",
            "total_mass": (data.get("Total_Mass") or [0.0])[0],
            "total_volume": (data.get("Total_Volume") or [0.0])[0],
            "total_cg": (data.get("Total_CG") or [None])[0],
            "ixx": (data.get("Total_Ixx") or [0.0])[0],
            "iyy": (data.get("Total_Iyy") or [0.0])[0],
            "izz": (data.get("Total_Izz") or [0.0])[0],
        }

    if analysis_name in ("PlanarSlice", "WaveDrag"):
        return {
            "type": analysis_name,
            "slice_loc": data.get("Slice_Loc") or data.get("X_Norm") or [],
            "slice_area": data.get("Slice_Area") or [],
            "cd_wave": (data.get("CDWave") or [None])[0],
            "max_area": (data.get("MaxArea") or [None])[0],
        }

    return {"type": analysis_name}


EXPORT_FORMATS: dict[str, tuple[str, int | None]] = {
    "VSP3": (".vsp3", None),
    "EXPORT_STEP": (".stp", getattr(vsp, "EXPORT_STEP", 4)),
    "EXPORT_IGES": (".igs", getattr(vsp, "EXPORT_IGES", 5)),
    "EXPORT_STL": (".stl", getattr(vsp, "EXPORT_STL", 2)),
    "EXPORT_OBJ": (".obj", getattr(vsp, "EXPORT_OBJ", 14)),
    "EXPORT_X3D": (".x3d", getattr(vsp, "EXPORT_X3D", 1)),
    "EXPORT_DXF": (".dxf", getattr(vsp, "EXPORT_DXF", 10)),
    "EXPORT_SVG": (".svg", getattr(vsp, "EXPORT_SVG", 11)),
    "EXPORT_GMSH": (".msh", getattr(vsp, "EXPORT_GMSH", 7)),
    "EXPORT_NASTRAN": (".dat", getattr(vsp, "EXPORT_NASTRAN", 3)),
    "EXPORT_CALCULIX": (".inp", getattr(vsp, "EXPORT_CALCULIX", 19)),
    "EXPORT_CART3D": (".tri", getattr(vsp, "EXPORT_CART3D", 13)),
    "EXPORT_VSPGEOM": (".vspgeom", getattr(vsp, "EXPORT_VSPGEOM", 15)),
    "EXPORT_BEM": (".bem", getattr(vsp, "EXPORT_BEM", 6)),
    "EXPORT_SELIG_AIRFOIL": (".csv", getattr(vsp, "EXPORT_SELIG_AIRFOIL", 17)),
    "EXPORT_BEZIER_AIRFOIL": (".csv", getattr(vsp, "EXPORT_BEZIER_AIRFOIL", 18)),
    "EXPORT_PMARC": (".pma", getattr(vsp, "EXPORT_PMARC", 12)),
    "DES": (".des", None),
    "XDDM": (".xddm", None),
}


def export_model_file(payload: dict[str, Any]) -> dict[str, Any]:
    """Eksportuje bieżący model OpenVSP do wybranego formatu CAD / siatki / zmiennych projektowych."""
    fmt_key = str(payload.get("format") or "VSP3").strip().upper()
    set_idx = int(_coerce_arg_for_vsp(payload.get("set_index", "SET_ALL")))
    base_name = str(payload.get("filename") or "bipol_aircraft").strip()
    base_name = re.sub(r"\.[A-Za-z0-9]+$", "", os.path.basename(base_name)) or "bipol_aircraft"

    if fmt_key not in EXPORT_FORMATS:
        raise ValueError(f"Nieobsługiwany format eksportu: {fmt_key}")

    ext, vsp_fmt_const = EXPORT_FORMATS[fmt_key]
    rel_path = _ascii_rel_path(f"{base_name}{ext}")

    with _VSP_LOCK:
        _pop_vsp_errors()
        if not vsp.FindGeoms():
            build_model_from_bipol()
        vsp.Update()

        if fmt_key == "VSP3":
            vsp.WriteVSPFile(rel_path, set_idx)
        elif fmt_key == "DES":
            vsp.WriteDESFile(rel_path)
        elif fmt_key == "XDDM":
            vsp.WriteXDDMFile(rel_path)
        else:
            vsp.ExportFile(rel_path, set_idx, int(vsp_fmt_const))

        errors = _pop_vsp_errors()
        exists = os.path.isfile(rel_path)
        size_bytes = os.path.getsize(rel_path) if exists else 0
        fname = os.path.basename(rel_path)

        return {
            "status": "ok" if exists else "warning",
            "format": fmt_key,
            "filename": fname,
            "relative_path": rel_path,
            "size_bytes": size_bytes,
            "download_url": f"/api/openvsp/download/{fname}",
            "vsp_errors": errors,
        }


def list_workspace_files() -> list[dict[str, Any]]:
    """Zwraca listę wygenerowanych plików w katalogu roboczym `work/openvsp`."""
    os.makedirs(WORK_REL_DIR, exist_ok=True)
    items = []
    for entry in sorted(os.listdir(WORK_REL_DIR)):
        full = os.path.join(WORK_REL_DIR, entry)
        if os.path.isfile(full):
            items.append({
                "filename": entry,
                "size_bytes": os.path.getsize(full),
                "modified_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(full))),
                "download_url": f"/api/openvsp/download/{entry}",
            })
    return items


def execute_vsp_script(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Uruchamia skrypt użytkownika:
    - w trybie `python`: wykonuje kod Python z pełnym dostępem do `vsp` (`openvsp`), `math`, `bipol_result`
      oraz aktualizuje stan modelu 3D w pamięci;
    - w trybie `vspscript`: zapisuje plik `.vspscript` i wykonuje `OpenVSP-3.55.0/vspscript.exe -script <plik>`.
    """
    mode = str(payload.get("mode") or "python").strip().lower()
    code = str(payload.get("code") or "")
    if not code.strip():
        raise ValueError("Kod skryptu nie może być pusty.")

    with _VSP_LOCK:
        _pop_vsp_errors()
        t0 = time.perf_counter()

        if mode == "vspscript":
            script_rel = _ascii_rel_path("user_script.vspscript")
            with open(script_rel, "w", encoding="utf-8") as f:
                f.write(code)
            exe_path = _vspscript_path()
            if not os.path.isfile(exe_path):
                raise ValueError("Nie znaleziono vspscript. Wskaż katalog instalacji przez BIPOL_OPENVSP_DIR.")
            proc = subprocess.run(
                [exe_path, "-script", script_rel],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            state = get_model_state(include_mesh=True, include_all_parms=True)
            has_script_error = proc.returncode != 0 or "ERROR" in (proc.stdout + proc.stderr).upper()
            return {
                "status": "error" if has_script_error else "ok",
                "mode": "vspscript",
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "elapsed_ms": elapsed_ms,
                "model": state,
                "files": list_workspace_files(),
            }

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        import numpy as np

        scope: dict[str, Any] = {
            "__builtins__": __builtins__,
            "vsp": vsp,
            "openvsp": vsp,
            "math": math,
            "np": np,
            "json": json,
            "bipol_result": _LAST_BIPOL_RESULT,
            "WORK_DIR": WORK_REL_DIR,
            "result": None,
        }
        status = "ok"
        tb_str = ""
        try:
            with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                exec(code, scope, scope)
            vsp.Update()
        except Exception:
            status = "error"
            tb_str = traceback.format_exc()

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        errors = _pop_vsp_errors()
        state = get_model_state(include_mesh=True, include_all_parms=True)

        return {
            "status": status,
            "mode": "python",
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue() + ("\n" + tb_str if tb_str else ""),
            "result": _serialize_vsp_value(scope.get("result")),
            "elapsed_ms": elapsed_ms,
            "vsp_errors": errors,
            "model": state,
            "files": list_workspace_files(),
        }


def manage_design_vars_sets_links(payload: dict[str, Any]) -> dict[str, Any]:
    """Zarządza zbiorami (Sets), zmiennymi projektowymi (DesignVars), parametrami użytkownika i sondami pomiarowymi."""
    action = str(payload.get("action") or "").strip()
    with _VSP_LOCK:
        _pop_vsp_errors()
        res_data: Any = None

        if action == "set_name":
            idx = int(payload.get("set_index", 3))
            name = str(payload.get("name") or f"Set_{idx}")
            vsp.SetSetName(idx, name)
        elif action == "set_flag":
            geom_id = str(payload.get("geom_id") or "")
            idx = int(payload.get("set_index", 3))
            flag = bool(payload.get("flag", True))
            vsp.SetSetFlag(geom_id, idx, flag)
        elif action == "add_design_var":
            parm_id = str(payload.get("parm_id") or "")
            dv_type = int(payload.get("type", getattr(vsp, "XDDM_VAR", 0)))
            vsp.AddDesignVar(parm_id, dv_type)
        elif action == "del_all_design_vars":
            vsp.DeleteAllDesignVars()
        elif action == "add_ruler":
            start_gid = str(payload.get("start_geom_id") or "")
            end_gid = str(payload.get("end_geom_id") or start_gid)
            name = str(payload.get("name") or "Miarka_3D")
            res_data = vsp.AddRuler(start_gid, 0, 0.0, 0.0, end_gid, 0, 0.5, 0.5, name)
        elif action == "add_probe":
            gid = str(payload.get("geom_id") or "")
            name = str(payload.get("name") or "Sonda_3D")
            res_data = vsp.AddProbe(gid, 0, 0.5, 0.5, name)
        elif action == "del_all_rulers":
            vsp.DeleteAllRulers()
        elif action == "del_all_probes":
            vsp.DeleteAllProbes()
        else:
            raise ValueError(f"Nieznana akcja konfiguracji: {action}")

        vsp.Update()
        errors = _pop_vsp_errors()
        state = get_model_state(include_mesh=False, include_all_parms=False)
        state["result"] = _serialize_vsp_value(res_data)
        state["vsp_errors"] = errors
        return state


# ============================================================================
# ENDPOINTY HTTP FLASK (/api/openvsp/*)
# ============================================================================

@blueprint.get("/status")
def api_status():
    from calculations.openvsp_integration import check_openvsp_availability
    if vsp is None:
        return jsonify(
            status='unavailable',
            available=False,
            files=[],
            openvsp={"available": False, "version": None, "error": "Brak zgodnego API OpenVSP."},
            message='Brak zgodnego API OpenVSP. Pozostałe obliczenia BIPOL i ML1 są dostępne.'
        )
    int_info = check_openvsp_availability(vsp_module=vsp)
    if not bool(int_info.get("available", False)):
        return jsonify(
            status='unavailable',
            available=False,
            files=[],
            openvsp=int_info,
            message='Brak zgodnego API OpenVSP. Pozostałe obliczenia BIPOL i ML1 są dostępne.'
        )
    cat = get_api_catalog()
    return jsonify({
        "status": "ok",
        "available": True,
        "version": cat["version"],
        "vsp_version": cat["version"],
        "vspaero_available": cat["vspaero_available"],
        "vspaero_exists": cat["vspaero_available"],
        "vspaero_path": cat["vspaero_path"],
        "vspscript_available": cat["vspscript_available"],
        "counts": cat["counts"],
        "files": list_workspace_files(),
        "openvsp": int_info,
    })


@blueprint.get("/catalog")
def api_catalog():
    return jsonify(get_api_catalog())


@blueprint.get("/model")
def api_get_model():
    include_mesh = request.args.get("mesh", "1") != "0"
    include_parms = request.args.get("parms", "1") != "0"
    return jsonify(get_model_state(include_mesh=include_mesh, include_all_parms=include_parms))


@blueprint.post("/build-from-bipol")
def api_build_from_bipol():
    payload = request.get_json(force=True, silent=True) or {}
    return jsonify(build_model_from_bipol(payload))


@blueprint.post("/geom")
def api_modify_geom():
    payload = request.get_json(force=True, silent=True) or {}
    return jsonify(modify_geometry(payload))


@blueprint.post("/parm")
def api_update_parm():
    payload = request.get_json(force=True, silent=True) or {}
    return jsonify(update_parameters(payload))


@blueprint.post("/analysis")
def api_run_analysis():
    payload = request.get_json(force=True, silent=True) or {}
    return jsonify(run_vsp_analysis(payload))


@blueprint.post("/call")
def api_call_function():
    payload = request.get_json(force=True, silent=True) or {}
    func_name = payload.get("function") or payload.get("name")
    if not func_name:
        raise ValueError("Wymagane pole 'function'.")
    args = payload.get("args") or []
    kwargs = payload.get("kwargs") or {}
    auto_update = bool(payload.get("auto_update", False))
    res = call_api_function(func_name, args=args, kwargs=kwargs, auto_update=auto_update)
    if payload.get("include_model"):
        res["model"] = get_model_state(include_mesh=True, include_all_parms=True)
    return jsonify(res)


@blueprint.post("/export")
def api_export_file():
    payload = request.get_json(force=True, silent=True) or {}
    res = export_model_file(payload)
    res["files"] = list_workspace_files()
    return jsonify(res)


@blueprint.post("/import")
def api_import_file():
    if "file" in request.files:
        f = request.files["file"]
        rel_path = _ascii_rel_path(f.filename or "imported.vsp3")
        f.save(rel_path)
    else:
        payload = request.get_json(force=True, silent=True) or {}
        rel_path = _ascii_rel_path(payload.get("filename") or "bipol_current.vsp3")

    if not os.path.isfile(rel_path):
        raise ValueError(f"Plik nie istnieje: {rel_path}")

    with _VSP_LOCK:
        _pop_vsp_errors()
        ext = os.path.splitext(rel_path)[1].lower()
        if ext == ".vsp3":
            vsp.ClearVSPModel()
            vsp.ReadVSPFile(rel_path)
            _LAST_BUILD_META.clear()
        elif ext == ".des":
            vsp.ReadDESFile(rel_path)
        elif ext == ".xddm":
            vsp.ReadXDDMFile(rel_path)
        else:
            fmt = int(_coerce_arg_for_vsp(request.form.get("format") or "IMPORT_STL"))
            vsp.ImportFile(rel_path, fmt)
        vsp.Update()
        errors = _pop_vsp_errors()
        state = get_model_state(include_mesh=True, include_all_parms=True)
        state["imported_file"] = rel_path
        state["vsp_errors"] = errors
        state["files"] = list_workspace_files()
        return jsonify(state)


@blueprint.get("/download/<path:filename>")
def api_download_file(filename: str):
    rel_path = _ascii_rel_path(filename)
    abs_path = os.path.abspath(rel_path)
    if not os.path.isfile(abs_path):
        abort(404)
    return send_file(abs_path, as_attachment=True, download_name=os.path.basename(abs_path))


@blueprint.post("/script")
def api_run_script():
    payload = request.get_json(force=True, silent=True) or {}
    return jsonify(execute_vsp_script(payload))


@blueprint.post("/manage")
def api_manage():
    payload = request.get_json(force=True, silent=True) or {}
    return jsonify(manage_design_vars_sets_links(payload))

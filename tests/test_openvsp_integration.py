"""
Testy jednostkowe i kontraktowe modułu integracji OpenVSP (`calculations/openvsp_integration.py`).
Weryfikują, że budowa geometrii 3D, powierzchnie sterowe, analizy (`CompGeom`, `MassProp`,
`ParasiteDrag`, `VSPAERO`, `WaveDrag`, `Projection`, `DegenGeom`) oraz eksport plików (`.vsp3`,
`STL`, `STEP`, `IGES`, `OBJ`, `DXF`, `GMSH`, `XSEC`) korzystają wyłącznie z oficjalnego API OpenVSP.
"""
from __future__ import annotations

from pathlib import Path
import pytest

from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.openvsp_integration import (
    OpenVSPAPIError,
    OpenVSPNotAvailableError,
    build_vsp_aircraft_model,
    check_openvsp_availability,
    compute_vsp_degen_geom,
    export_vsp_model,
    load_vsp_file,
    run_full_vsp_pipeline,
    run_vsp_aero_analysis,
    run_vsp_comp_geom,
    run_vsp_mass_properties,
    run_vsp_parasite_drag,
    run_vsp_projection_area,
    run_vsp_wave_drag,
)


class _MockVec3d:
    def __init__(self, x: float, y: float, z: float):
        self._x = x
        self._y = y
        self._z = z

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y

    def z(self) -> float:
        return self._z


class _MockErrorObj:
    def __init__(self, func_name: str, error_string: str):
        self._func = func_name
        self._msg = error_string

    def GetFunctionName(self) -> str:
        return self._func

    def GetErrorString(self) -> str:
        return self._msg


class _MockErrorMgr:
    def __init__(self):
        self._errors: list[_MockErrorObj] = []

    def push_error(self, func_name: str, msg: str) -> None:
        self._errors.append(_MockErrorObj(func_name, msg))

    def GetErrorLastCallFlag(self) -> bool:
        return bool(self._errors)

    def GetNumTotalErrors(self) -> int:
        return len(self._errors)

    def PopLastError(self) -> _MockErrorObj:
        return self._errors.pop()


class MockOpenVSP:
    """Wierna stanowa makieta natywnego modułu SWIG `openvsp` (NASA OpenVSP Python API)."""
    vec3d = _MockVec3d
    SPAN_WSECT_DRIVER = 1
    ROOTC_WSECT_DRIVER = 6
    TIPC_WSECT_DRIVER = 7

    SYM_NONE = 0
    SYM_XY = 1
    SYM_XZ = 2
    SYM_YZ = 4

    XS_POINT = 0
    XS_CIRCLE = 1
    XS_ELLIPSE = 2
    XS_SUPER_ELLIPSE = 3
    XS_ROUNDED_RECTANGLE = 4
    XS_GENERAL_FUSE = 5
    XS_FOUR_SERIES = 6
    XS_SIX_SERIES = 7
    XS_BICONVEX = 8
    XS_WEDGE = 9
    XS_FILE_AIRFOIL = 11

    SS_CONTROL = 2

    ABS = 0
    REL = 1

    VORTEX_LATTICE = 0
    PANEL = 1

    SET_ALL = 0
    SET_TARGET = 0
    NO_BOUNDARY = 0

    X_DIR = 0
    Y_DIR = 1
    Z_DIR = 2

    EXPORT_XSEC = 1
    EXPORT_STL = 2
    EXPORT_STEP = 4
    EXPORT_IGES = 7
    EXPORT_DXF = 9
    EXPORT_GMSH = 10
    EXPORT_OBJ = 12

    def __init__(self):
        self.error_mgr = _MockErrorMgr()
        self.ErrorMgrSingleton = self
        self.reset_state()

    def getInstance(self) -> _MockErrorMgr:
        return self.error_mgr

    def reset_state(self):
        self.vehicle_name = "Default_Vehicle"
        self.geoms: dict[str, dict] = {}
        self.xsec_surfs: dict[str, list[dict]] = {}
        self.subsurfs: dict[str, list[dict]] = {}
        self.parms: dict[tuple[str, str, str], float] = {}
        self.xsec_parms: dict[tuple[str, str], float] = {}
        self.airfoil_points = {}
        self.analysis_inputs: dict[str, dict[str, list]] = {}
        self.executed_analyses: list[str] = []
        self.exported_files: list[tuple[str, int, int | None]] = []
        self.update_count = 0
        self._geom_counter = 0
        self._subsurf_counter = 0

    def GetVSPVersion(self) -> str:
        return "OpenVSP 3.41.1"

    def VSPCheckSetup(self) -> None:
        return None

    def VSPRenew(self) -> None:
        self.reset_state()

    def ClearVSPModel(self) -> None:
        self.geoms.clear()
        self.xsec_surfs.clear()
        self.subsurfs.clear()
        self.parms.clear()
        self.xsec_parms.clear()

    def SetVehicleName(self, name: str) -> None:
        self.vehicle_name = name

    def AddGeom(self, geom_type: str, parent_id: str = "") -> str:
        self._geom_counter += 1
        gid = f"GEOM_{self._geom_counter}_{geom_type}"
        self.geoms[gid] = {
            "type": geom_type,
            "name": gid,
            "parent": parent_id,
        }
        surf_id = f"SURF_{gid}_0"
        if geom_type == "FUSELAGE":
            self.xsec_surfs[surf_id] = [
                {"id": f"{surf_id}_XS_{i}", "shape": self.XS_POINT if i in (0, 4) else self.XS_ELLIPSE}
                for i in range(5)
            ]
        elif geom_type == "WING":
            self.xsec_surfs[surf_id] = [
                {"id": f"{surf_id}_XS_0", "shape": self.XS_FOUR_SERIES},
                {"id": f"{surf_id}_XS_1", "shape": self.XS_FOUR_SERIES},
            ]
        else:
            self.xsec_surfs[surf_id] = []
        self.subsurfs[gid] = []
        return gid

    def SetGeomName(self, geom_id: str, name: str) -> None:
        if geom_id in self.geoms:
            self.geoms[geom_id]["name"] = name

    def GetGeomName(self, geom_id: str) -> str:
        return self.geoms.get(geom_id, {}).get("name", geom_id)

    def GetGeomTypeName(self, geom_id: str) -> str:
        return self.geoms.get(geom_id, {}).get("type", "UNKNOWN")

    def FindGeoms(self) -> list[str]:
        return list(self.geoms.keys())

    def DeleteGeomVec(self, geom_vec: list[str]) -> None:
        for gid in geom_vec:
            self.geoms.pop(gid, None)

    def SetParmVal(self, *args) -> float:
        if len(args) == 2:
            parm_id, val = args
            self.xsec_parms[parm_id] = float(val)
            return float(val)
        if len(args) == 4:
            geom_id, name, group, val = args
            self.parms[(geom_id, group, name)] = float(val)
            return float(val)
        raise TypeError(f"Unexpected SetParmVal signature: {args}")

    def GetXSecSurf(self, geom_id: str, index: int = 0) -> str:
        return f"SURF_{geom_id}_{index}"

    def GetNumXSec(self, xsec_surf_id: str) -> int:
        return len(self.xsec_surfs.get(xsec_surf_id, []))

    def GetXSec(self, xsec_surf_id: str, xsec_idx: int) -> str:
        xsecs = self.xsec_surfs.get(xsec_surf_id, [])
        if 0 <= xsec_idx < len(xsecs):
            return xsecs[xsec_idx]["id"]
        return f"{xsec_surf_id}_XS_{xsec_idx}"

    def ChangeXSecShape(self, xsec_surf_id: str, xsec_idx: int, shape_type: int) -> None:
        xsecs = self.xsec_surfs.get(xsec_surf_id, [])
        if 0 <= xsec_idx < len(xsecs):
            xsecs[xsec_idx]["shape"] = shape_type

    def InsertXSec(self, geom_id: str, index: int, shape_type: int) -> str:
        surf_id = self.GetXSecSurf(geom_id, 0)
        xsecs = self.xsec_surfs.setdefault(surf_id, [])
        new_id = f"{surf_id}_XS_{len(xsecs)}"
        xsecs.insert(index + 1, {"id": new_id, "shape": shape_type})
        return new_id

    def GetXSecParm(self, xsec_id: str, parm_name: str) -> tuple[str, str]:
        return (xsec_id, parm_name)

    def ReadFileAirfoil(self, xsec_id: str, file_path: str) -> None:
        self.xsec_parms[(xsec_id, "AirfoilFile")] = file_path

    def SetAirfoilPnts(self, xsec_id, upper, lower):
        self.airfoil_points[xsec_id] = dict(upper=[(p.x(), p.y(), p.z()) for p in upper],
                                          lower=[(p.x(), p.y(), p.z()) for p in lower])

    def AddSubSurf(self, geom_id: str, subsurf_type: int, index: int = 0) -> str:
        self._subsurf_counter += 1
        ss_id = f"SUBSURF_{self._subsurf_counter}"
        self.subsurfs.setdefault(geom_id, []).append(
            {"id": ss_id, "type": subsurf_type, "name": ss_id}
        )
        return ss_id

    def SetSubSurfName(self, geom_id: str, subsurf_id: str, name: str) -> None:
        for ss in self.subsurfs.get(geom_id, []):
            if ss["id"] == subsurf_id:
                ss["name"] = name

    def Update(self) -> None:
        self.update_count += 1

    def SetDriverGroup(self, geom_id, section, *drivers):
        self.geoms[geom_id].setdefault('drivers', {})[section] = drivers

    def ErrorMgrSingleton_getInstance(self) -> _MockErrorMgr:
        return self.error_mgr

    def SetAnalysisInputDefaults(self, analysis_name: str) -> None:
        self.analysis_inputs[analysis_name] = {}

    def SetIntAnalysisInput(self, analysis_name: str, name: str, values: list[int], index: int = 0) -> None:
        self.analysis_inputs.setdefault(analysis_name, {})[name] = list(values)

    def SetDoubleAnalysisInput(self, analysis_name: str, name: str, values: list[float], index: int = 0) -> None:
        self.analysis_inputs.setdefault(analysis_name, {})[name] = list(values)

    def ExecAnalysis(self, analysis_name: str) -> str:
        self.executed_analyses.append(analysis_name)
        if analysis_name == "CompGeom":
            self.geoms["MESH_TEMP"] = {"type": "MESH", "name": "CompGeom_Mesh", "parent": ""}
        return f"RES_{analysis_name}"

    def GetStringResults(self, res_id: str, name: str, index: int = 0) -> tuple[str, ...]:
        if res_id == "RES_CompGeom":
            if name == "comp_name":
                return ("Kadlub", "Skrzydlo_Glowne", "Usterzenie_Poziome", "Usterzenie_Pionowe")
            if name == "Mesh_GeomID":
                return ("MESH_TEMP",)
        if res_id == "RES_MassProp" and name == "Mesh_GeomID":
            return ()
        if res_id == "RES_ParasiteDrag" and name == "Comp_Name":
            return ("Kadlub", "Skrzydlo_Glowne", "Usterzenie_Poziome", "Usterzenie_Pionowe")
        if res_id == "RES_VSPAEROSweep" and name == "ResultsVec":
            return ("RES_VSPAERO_POLAR_0",)
        if res_id == "RES_DegenGeom" and name == "Degen_Obj":
            return ("DEGEN_OBJ_1", "DEGEN_OBJ_2")
        if res_id in ("DEGEN_OBJ_1", "DEGEN_OBJ_2") and name == "name":
            return ("Skrzydlo_Glowne" if res_id == "DEGEN_OBJ_1" else "Kadlub",)
        return ()

    def GetDoubleResults(self, res_id: str, name: str, index: int = 0) -> tuple[float, ...]:
        if res_id == "RES_CompGeom":
            if name == "theo_area":
                return (22.5, 31.0, 6.2, 3.8)
            if name == "wet_area":
                return (21.2, 29.4, 5.8, 3.6)
            if name == "theo_vol":
                return (4.8, 1.4, 0.22, 0.12)
            if name == "wet_vol":
                return (4.6, 1.3, 0.20, 0.11)
        if res_id == "RES_MassProp":
            mapping = {
                "Total_Mass": (1150.0,),
                "Total_Ixx": (1420.0,),
                "Total_Iyy": (1980.0,),
                "Total_Izz": (2890.0,),
            }
            return mapping.get(name, (0.0,))
        if res_id == "RES_ParasiteDrag":
            mapping = {
                "Total_CD_Total": (0.0248,),
                "Comp_Swet": (21.2, 29.4, 5.8, 3.6),
                "Comp_Cf": (0.0028, 0.0031, 0.0034, 0.0035),
                "Comp_FF": (1.18, 1.24, 1.22, 1.21),
                "Comp_CD": (0.0072, 0.0126, 0.0031, 0.0019),
            }
            return mapping.get(name, ())
        if res_id == "RES_VSPAERO_POLAR_0":
            mapping = {
                "Alpha": (-2.0, 1.0, 4.0, 7.0, 10.0),
                "CL": (-0.08, 0.22, 0.52, 0.81, 1.08),
                "CDi": (0.0004, 0.0021, 0.0115, 0.0280, 0.0498),
                "CDo": (0.0245, 0.0245, 0.0245, 0.0245, 0.0245),
                "CDtot": (0.0249, 0.0266, 0.0360, 0.0525, 0.0743),
                "L_D": (-3.21, 8.27, 14.44, 15.43, 14.53),
                "CMy": (0.04, 0.01, -0.03, -0.07, -0.11),
            }
            return mapping.get(name, ())
        if res_id == "RES_WaveDrag":
            mapping = {
                "CDWave": (0.0185,),
                "D_on_q": (0.275,),
                "MaxCrossSectArea": (1.42,),
            }
            return mapping.get(name, ())
        if res_id == "RES_Projection" and name == "Area":
            return (15.4,)
        return ()

    def GetVec3dResults(self, res_id: str, name: str, index: int = 0) -> list[_MockVec3d]:
        if res_id == "RES_MassProp" and name == "Total_CG":
            return [_MockVec3d(2.45, 0.0, 0.12)]
        return []

    def WriteVSPFile(self, file_name: str, set_index: int = 0) -> None:
        Path(file_name).write_text("<Vsp_Geometry>Mock VSP3</Vsp_Geometry>", encoding="utf-8")
        self.exported_files.append((file_name, set_index, None))

    def ExportFile(self, file_name: str, set_index: int, file_type: int) -> None:
        Path(file_name).write_text(f"MOCK_EXPORT_TYPE_{file_type}", encoding="utf-8")
        self.exported_files.append((file_name, set_index, file_type))

    def ReadVSPFile(self, file_name: str) -> None:
        self.AddGeom("FUSELAGE")
        self.AddGeom("WING")


@pytest.fixture
def mock_vsp() -> MockOpenVSP:
    return MockOpenVSP()


@pytest.fixture
def sample_project_results() -> dict:
    preset_entry = AIRCRAFT_PRESETS["pzl_kos"]
    params = dict(preset_entry.get("params", preset_entry))
    return run_bipol_project(params)


def test_check_openvsp_availability_with_mock(mock_vsp):
    info = check_openvsp_availability(vsp_module=mock_vsp)
    assert info["available"] is True
    assert info["version"] == "OpenVSP 3.41.1"
    assert info["error"] is None


def test_build_vsp_aircraft_model_standard_configuration(mock_vsp, sample_project_results):
    summary = build_vsp_aircraft_model(sample_project_results, vsp_module=mock_vsp)

    assert summary["fuselage"]["geom_id"].startswith("GEOM_")
    assert summary["wing"]["geom_id"].startswith("GEOM_")
    assert summary["empennage"]["horizontal_tail_id"] is not None
    assert summary["empennage"]["vertical_tail_id"] is not None
    assert mock_vsp.update_count >= 1

    # Weryfikacja podpowierzchni sterowych SS_CONTROL na skrzydle i usterzeniu
    wing_subsurfs = mock_vsp.subsurfs[summary["wing"]["geom_id"]]
    subsurf_names = {ss["name"] for ss in wing_subsurfs}
    assert "Klapa_Zaskrzydlowa" in subsurf_names
    assert "Lotka" in subsurf_names


@pytest.mark.parametrize(
    "planform,expected_sections",
    [
        ("trapezoidal", 1),
        ("rectangular", 1),
        ("compound_trapezoid", 2),
        ("elliptical", 32),
    ],
)
def test_build_vsp_wing_planforms(mock_vsp, sample_project_results, planform, expected_sections):
    result = run_bipol_project(dict(sample_project_results['params'], wing_planform=planform))
    summary = build_vsp_aircraft_model(result, vsp_module=mock_vsp)
    assert summary["wing"]["num_sections"] == expected_sections


@pytest.mark.parametrize("tail_type", ["conventional", "t_tail", "v_tail", "twin_tail"])
def test_build_vsp_empennage_configurations(mock_vsp, sample_project_results, tail_type):
    params = dict(sample_project_results["params"])
    params["tail_type"] = tail_type
    summary = build_vsp_aircraft_model(sample_project_results, params=params, vsp_module=mock_vsp)

    emp = summary["empennage"]
    assert emp["tail_type"] == tail_type
    assert emp["horizontal_tail_id"] is not None
    if tail_type == "v_tail":
        assert emp["vertical_tail_id"] is None
    else:
        assert emp["vertical_tail_id"] is not None


def test_vsp_analyses_comp_geom_mass_parasite_aero_wave_projection_degen(mock_vsp, sample_project_results):
    build_vsp_aircraft_model(sample_project_results, vsp_module=mock_vsp)

    comp = run_vsp_comp_geom(vsp_module=mock_vsp)
    assert comp["analysis"] == "CompGeom"
    assert comp["total_wet_area_m2"] == pytest.approx(60.0)
    assert len(comp["components"]) == 4
    assert "MESH_TEMP" not in mock_vsp.geoms  # tymczasowa siatka usunięta przez DeleteGeomVec

    mass = run_vsp_mass_properties(num_slices=60, vsp_module=mock_vsp)
    assert mass["total_mass"] == pytest.approx(1150.0)
    assert mass["cg_m"]["x"] == pytest.approx(2.45)
    assert mass["inertia"]["Iyy"] == pytest.approx(1980.0)

    drag = run_vsp_parasite_drag(s_ref_m2=15.0, v_inf_ms=60.0, altitude_m=2000.0, vsp_module=mock_vsp)
    assert drag["cd0_total"] == pytest.approx(0.0248)
    assert len(drag["components"]) == 4

    aero = run_vsp_aero_analysis(
        s_ref_m2=15.0,
        b_ref_m=10.5,
        c_ref_m=1.45,
        x_cg_m=2.3,
        method="vlm",
        vsp_module=mock_vsp,
    )
    assert aero["method"] == "VORTEX_LATTICE"
    assert len(aero["polar_points"]) == 5
    assert aero["polar_points"][2]["CL"] == pytest.approx(0.52)

    wave = run_vsp_wave_drag(s_ref_m2=15.0, mach=1.25, vsp_module=mock_vsp)
    assert wave["cd_wave"] == pytest.approx(0.0185)

    proj = run_vsp_projection_area(direction="z", vsp_module=mock_vsp)
    assert proj["projected_area_m2"] == pytest.approx(15.4)

    degen = compute_vsp_degen_geom(vsp_module=mock_vsp)
    assert degen["component_names"] == ["Skrzydlo_Glowne", "Kadlub"]


def test_export_and_load_vsp_model(mock_vsp, sample_project_results, tmp_path):
    build_vsp_aircraft_model(sample_project_results, vsp_module=mock_vsp)
    exported = export_vsp_model(
        output_dir=tmp_path,
        base_name="PZL Kos Test",
        formats=("vsp3", "stl", "step", "iges", "obj", "dxf", "gmsh", "xsec"),
        vsp_module=mock_vsp,
    )
    assert set(exported.keys()) == {"vsp3", "stl", "step", "iges", "obj", "dxf", "gmsh", "xsec"}
    for path_str in exported.values():
        assert Path(path_str).exists()

    loaded = load_vsp_file(exported["vsp3"], vsp_module=mock_vsp)
    assert loaded["num_geometries"] == 2


def test_full_vsp_pipeline_and_error_handling(mock_vsp, sample_project_results, tmp_path):
    pipeline_res = run_full_vsp_pipeline(
        sample_project_results,
        run_vspaero=True,
        export_dir=tmp_path,
        export_formats=("vsp3", "stl"),
        vsp_module=mock_vsp,
    )
    assert "model" in pipeline_res
    assert pipeline_res["comp_geom"]["total_wet_area_m2"] > 0
    assert pipeline_res["vspaero"] is not None
    assert "vsp3" in pipeline_res["exported_files"]

    # Sprawdzenie obsługi błędów ErrorMgrSingleton OpenVSP
    mock_vsp.error_mgr.push_error("SetParmVal", "Invalid Parm ID")
    with pytest.raises(OpenVSPAPIError, match="Invalid Parm ID"):
        run_vsp_comp_geom(vsp_module=mock_vsp)


def test_flask_openvsp_endpoints(monkeypatch, mock_vsp):
    import app as flask_app
    import calculations.openvsp_integration as vsp_mod
    import calculations.openvsp_bridge as bridge

    client = flask_app.app.test_client()

    # 1. Status endpoint (gdy openvsp jest dostępny przez wstrzyknięcie)
    monkeypatch.setattr(vsp_mod, "_load_vsp", lambda vsp_module=None: mock_vsp)
    # The HTTP studio requires the native bridge as well as the analysis adapter.
    # Mocking only the adapter must not advertise an unavailable native studio.
    with monkeypatch.context() as absent:
        absent.setattr(bridge, 'vsp', None)
        response = client.get('/api/openvsp/status')
        assert response.status_code == 200
        assert response.json['status'] == 'unavailable'
        assert response.json['available'] is False
    monkeypatch.setattr(bridge, 'vsp', mock_vsp)
    # Full SWIG catalog introspection is covered by native tests, not this adapter fake.
    monkeypatch.setattr(bridge, 'get_api_catalog', lambda: dict(
        version=mock_vsp.GetVSPVersion(), vspaero_available=False, vspaero_path='',
        vspscript_available=False, counts={}))
    resp_status = client.get("/api/openvsp/status")
    assert resp_status.status_code == 200
    data_status = resp_status.get_json()
    assert data_status["status"] == "ok"
    assert data_status['available'] is True
    assert data_status["openvsp"]["available"] is True
    assert data_status["openvsp"]["version"] == "OpenVSP 3.41.1"

    # 2. Analyze endpoint
    preset_entry = AIRCRAFT_PRESETS["pzl_kos"]
    params = dict(preset_entry.get("params", preset_entry))
    resp_analyze = client.post("/api/openvsp/analyze", json={"params": params, "run_vspaero": True})
    assert resp_analyze.status_code == 200
    data_analyze = resp_analyze.get_json()
    assert data_analyze["status"] == "ok"
    assert data_analyze["openvsp"]["comp_geom"]["total_wet_area_m2"] == pytest.approx(60.0)
    assert len(data_analyze["openvsp"]["vspaero"]["polar_points"]) == 5

    # 3. Export endpoint (.vsp3 i .stl)
    resp_export = client.post("/api/openvsp/export/vsp3", json={"params": params})
    assert resp_export.status_code == 200
    assert b"<Vsp_Geometry>" in resp_export.data
    resp_export.close()


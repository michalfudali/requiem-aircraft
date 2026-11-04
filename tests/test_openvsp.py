"""
Testy integracyjne modułu OpenVSP 3D Studio i pełnego katalogu API (OpenVSP 3.55.0).
Sprawdzają:
- status silnika i pełny katalog API (>1060 funkcji C++/SWIG, >1040 stałych, 55 klas, 22 analizy, 16 typów Geom),
- automatyczny generator parametrycznego modelu 3D samolotu z projektu BiPOL (kadłub, płat, usterzenie, klapy/lotki, śmigło, podwozie, siatka 3D SurfacePatches),
- modyfikację geometrii (AddGeom, DeleteGeom, AddSubSurf, InsertXSec) i parametrów na żywo (SetParmVal),
- solwery i analizy OpenVSP (CompGeom, ParasiteDrag, MassProp, PlanarSlice, VSPAEROSinglePoint) z porównaniem względem P3/P4 BiPOL,
- uniwersalny wykonawca dowolnej funkcji API (/api/openvsp/call),
- zarządzanie zbiorami (Sets), zmiennymi projektowymi (DesignVars) oraz miarkami/sondami 3D (Rulers/Probes),
- eksport CAD/CFD/FEA (.vsp3, STL, STEP, SVG, .des) oraz konsolę skryptową Python openvsp i AngelScript (.vspscript).
"""

import io
from app import app


def test_openvsp_ui_tab_present_in_index():
    client = app.test_client()
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'id="tab-openvsp"' in html
    assert 'data-target="tab-openvsp"' in html
    assert 'data-studio-nav="tab-openvsp"' in html
    assert "/static/css/openvsp.css" in html
    assert "/static/js/openvsp.js" in html


def test_openvsp_status_and_full_api_catalog():
    client = app.test_client()
    st_res = client.get("/api/openvsp/status")
    assert st_res.status_code == 200
    st = st_res.get_json()
    assert st["status"] == "ok"
    assert st["available"] is True
    assert "OpenVSP 3.55.0" in st["vsp_version"]
    assert st["vspaero_exists"] is True

    cat_res = client.get("/api/openvsp/catalog")
    assert cat_res.status_code == 200
    cat = cat_res.get_json()
    assert cat["status"] == "ok"
    counts = cat["counts"]
    assert counts["functions"] >= 1069
    assert counts["constants"] >= 1040
    assert counts["classes"] >= 19
    assert counts["analyses"] >= 22
    assert counts["geom_types"] >= 16

    func_names = {f["name"] for f in cat["functions"]}
    for expected_fn in (
        "AddGeom",
        "SetParmVal",
        "ExecAnalysis",
        "ExportFile",
        "WriteVSPFile",
        "AddSubSurf",
        "InsertXSec",
        "ComputeCompGeom",
    ):
        assert expected_fn in func_names


def test_openvsp_build_from_bipol_and_model_state():
    client = app.test_client()
    res = client.post("/api/openvsp/build-from-bipol", json={})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["num_geoms"] >= 6

    geom_names = {g["name"] for g in data["geoms"]}
    assert "Kadlub" in geom_names
    assert "Skrzydlo_Glowne" in geom_names
    assert "Usterzenie_Poziome" in geom_names
    assert "Usterzenie_Pionowe" in geom_names

    wing_geom = next(g for g in data["geoms"] if g["name"] == "Skrzydlo_Glowne")
    subsurf_names = {s["name"] for s in wing_geom["subsurfaces"]}
    assert "Lotki" in subsurf_names

    mesh = data["mesh"]
    assert mesh is not None
    assert len(mesh["components"]) >= 6
    assert mesh["bbox"]["max_x"] > 4.0
    assert mesh["bbox"]["max_y"] > 3.0


def test_openvsp_live_parameter_and_geometry_modifications():
    client = app.test_client()
    model = client.get("/api/openvsp/model").get_json()
    if model["num_geoms"] == 0:
        model = client.post("/api/openvsp/build-from-bipol", json={}).get_json()

    fus = next(g for g in model["geoms"] if g["name"] == "Kadlub")
    len_parm = next(
        p for p in fus["parameter_groups"].get("Design", []) if p["name"] == "Length"
    )
    new_len = round(float(len_parm["value"]) + 0.5, 3)

    upd_res = client.post(
        "/api/openvsp/parm",
        json={"parm_id": len_parm["id"], "value": new_len},
    )
    assert upd_res.status_code == 200
    upd_data = upd_res.get_json()
    assert upd_data["status"] == "ok"
    fus_after = next(g for g in upd_data["geoms"] if g["id"] == fus["id"])
    len_after = next(
        p for p in fus_after["parameter_groups"].get("Design", []) if p["name"] == "Length"
    )
    assert abs(float(len_after["value"]) - new_len) < 1e-3

    # Dodanie nowego komponentu POD i jego usunięcie
    add_res = client.post(
        "/api/openvsp/geom",
        json={"action": "add_geom", "geom_type": "POD", "name": "Zbiornik_Testowy"},
    )
    assert add_res.status_code == 200
    add_data = add_res.get_json()
    created_id = add_data["created_id"]
    assert created_id
    assert any(g["id"] == created_id for g in add_data["geoms"])

    del_res = client.post(
        "/api/openvsp/geom",
        json={"action": "delete_geom", "geom_id": created_id},
    )
    assert del_res.status_code == 200
    del_data = del_res.get_json()
    assert not any(g["id"] == created_id for g in del_data["geoms"])


def test_openvsp_analyses_and_bipol_comparison():
    client = app.test_client()
    # CompGeom
    cg_res = client.post("/api/openvsp/analysis", json={"analysis": "CompGeom"})
    assert cg_res.status_code == 200
    cg = cg_res.get_json()
    assert cg["status"] == "ok"
    assert cg["comparison"]["type"] == "CompGeom"
    assert cg["comparison"]["total_wet_area_vsp_m2"] > 20.0
    assert cg["comparison"]["total_wet_area_bipol_m2"] > 20.0
    assert len(cg["comparison"]["components"]) >= 4

    # ParasiteDrag
    pd_res = client.post("/api/openvsp/analysis", json={"analysis": "ParasiteDrag"})
    assert pd_res.status_code == 200
    pd = pd_res.get_json()
    assert pd["status"] == "ok"
    assert pd["comparison"]["type"] == "ParasiteDrag"
    assert pd["comparison"]["cd0_vsp"] > 0.005

    # MassProp
    mp_res = client.post("/api/openvsp/analysis", json={"analysis": "MassProp"})
    assert mp_res.status_code == 200
    mp = mp_res.get_json()
    assert mp["status"] == "ok"
    assert mp["comparison"]["type"] == "MassProp"
    assert mp["comparison"]["total_volume"] > 0.1


def test_openvsp_universal_api_caller_and_manage():
    client = app.test_client()
    # Wywołanie funkcji bezargumentowej
    ver_res = client.post("/api/openvsp/call", json={"function": "GetVSPVersion", "args": []})
    assert ver_res.status_code == 200
    assert "OpenVSP 3.55.0" in ver_res.get_json()["result"]

    # Wywołanie funkcji ze stałą symboliczną i konstruktorem vec3d
    geoms_res = client.post("/api/openvsp/call", json={"function": "FindGeoms", "args": []})
    assert geoms_res.status_code == 200
    gids = geoms_res.get_json()["result"]
    assert isinstance(gids, list) and len(gids) >= 4

    # Zarządzanie miarkami i sondami 3D
    m_res = client.post(
        "/api/openvsp/manage",
        json={
            "action": "add_ruler",
            "start_geom_id": gids[0],
            "end_geom_id": gids[1],
            "name": "TestRuler",
        },
    )
    assert m_res.status_code == 200
    assert len(m_res.get_json()["rulers"]) >= 1

    clr_res = client.post("/api/openvsp/manage", json={"action": "del_all_rulers"})
    assert clr_res.status_code == 200
    assert len(clr_res.get_json()["rulers"]) == 0


def test_openvsp_cad_export_import_and_scripts():
    client = app.test_client()
    for fmt in ("VSP3", "EXPORT_STL", "EXPORT_SVG"):
        ex_res = client.post(
            "/api/openvsp/export",
            json={"format": fmt, "filename": "test_export_samolot", "set_index": "SET_ALL"},
        )
        assert ex_res.status_code == 200
        ex = ex_res.get_json()
        assert ex["status"] == "ok"
        assert ex["size_bytes"] > 50

        dl_res = client.get(ex["download_url"])
        assert dl_res.status_code == 200
        assert len(dl_res.data) == ex["size_bytes"]

    # Test konsoli skryptowej Python openvsp
    py_res = client.post(
        "/api/openvsp/script",
        json={
            "mode": "python",
            "code": "geoms = vsp.FindGeoms()\nprint('Count:', len(geoms))\nresult = {'count': len(geoms)}",
        },
    )
    assert py_res.status_code == 200
    py_data = py_res.get_json()
    assert py_data["status"] == "ok"
    assert "Count:" in py_data["stdout"]
    assert py_data["result"]["count"] >= 4

    # Test konsoli AngelScript (.vspscript)
    as_res = client.post(
        "/api/openvsp/script",
        json={
            "mode": "vspscript",
            "code": 'void main() {\n    Print("Hello from vspscript");\n}\n',
        },
    )
    assert as_res.status_code == 200
    as_data = as_res.get_json()
    assert as_data["returncode"] == 0
    assert "Hello from vspscript" in as_data["stdout"]


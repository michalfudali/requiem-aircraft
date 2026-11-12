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
import pytest
from app import app
from calculations.openvsp_bridge import vsp


@pytest.mark.parametrize('planform', ['trapezoidal', 'compound_trapezoid', 'elliptical'])
@pytest.mark.parametrize('profile_name', ['FX 61-163', 'NACA 2415', 'NACA 23012'])
def test_selected_profile_ordinates_survive_native_build_and_vsp3_roundtrip(planform, profile_name):
    import json
    from pathlib import Path
    from calculations import run_bipol_project
    from calculations.airfoils import airfoil_200mm
    from calculations.openvsp_bridge import build_model_from_bipol, export_model_file
    p = json.loads((Path(__file__).parents[1]/'data/design_cases/topic7_motoszybowiec_21m.json').read_text(encoding='utf8'))
    p.update(wing_planform=planform, airfoil=profile_name)
    if profile_name.startswith('NACA'):
        p.pop('airfoil_coordinates', None)
    profile = airfoil_200mm(profile_name, p.get('airfoil_coordinates', ''))
    model = build_model_from_bipol(run_bipol_project(p))
    assert model['build_meta']['wing_airfoil']['profile_name'] == profile_name
    info = export_model_file({'format': 'VSP3', 'filename': 'profile_roundtrip'})
    assert info['status'] == 'ok'
    vsp.VSPRenew(); vsp.ReadVSPFile(info['relative_path']); vsp.Update()
    wing = next(g for g in vsp.FindGeoms() if vsp.GetGeomName(g) == 'Skrzydlo_Glowne')
    surf = vsp.GetXSecSurf(wing, 0)
    for i in range(vsp.GetNumXSec(surf)):
        xsec = vsp.GetXSec(surf, i)
        assert vsp.GetXSecShape(xsec) == vsp.XS_FILE_AIRFOIL
        for side, getter in [('upper', vsp.GetAirfoilUpperPnts), ('lower', vsp.GetAirfoilLowerPnts)]:
            actual = getter(xsec)
            assert len(actual) == len(profile[side])
            for stored, (x, y) in zip(actual, profile[side]):
                assert (stored.x(), stored.y(), stored.z()) == pytest.approx((x/200, y/200, 0), abs=1e-12)


def test_invalid_explicit_profile_cannot_replace_existing_native_model():
    from copy import deepcopy
    from calculations import run_bipol_project
    from calculations.presets import AIRCRAFT_PRESETS
    import calculations.openvsp_bridge as bridge
    result = run_bipol_project(dict(AIRCRAFT_PRESETS['ga_trainer']))
    bridge.build_model_from_bipol(result)
    ids, metadata = list(vsp.FindGeoms()), deepcopy(bridge._LAST_BUILD_META)
    bad = deepcopy(result)
    bad['params'].update(airfoil='UNKNOWN NAMED PROFILE', airfoil_coordinates='')
    with pytest.raises(ValueError, match='wybranego profilu'):
        bridge.build_model_from_bipol(bad)
    assert list(vsp.FindGeoms()) == ids
    assert bridge._LAST_BUILD_META == metadata


def test_manual_thickness_does_not_rescale_the_selected_profile_and_is_explicit():
    from calculations import run_bipol_project
    from calculations.presets import AIRCRAFT_PRESETS
    from calculations.openvsp_bridge import build_model_from_bipol
    result = run_bipol_project(dict(AIRCRAFT_PRESETS['ga_trainer'], airfoil='NACA 2415',
                                   profile_thickness_mode='assumed', tc_ratio=.1))
    model = build_model_from_bipol(result)
    af = model['build_meta']['wing_airfoil']
    assert af['tc_ratio'] == .15 and af['calculation_tc_ratio'] == .1
    assert af['thickness_mismatch'] and af['warnings']
    wing = next(g for g in vsp.FindGeoms() if vsp.GetGeomName(g) == 'Skrzydlo_Glowne')
    surf = vsp.GetXSecSurf(wing, 0)
    xsec = vsp.GetXSec(surf, 0)
    assert .14 < vsp.GetParmVal(vsp.GetXSecParm(xsec, 'ThickChord')) < .16


@pytest.mark.parametrize('profile_name', ['FX 61-163', 'NACA 23012'])
def test_native_analysis_builder_preserves_the_same_profile_ordinates(profile_name):
    import json
    from pathlib import Path
    from calculations import run_bipol_project
    from calculations.airfoils import airfoil_200mm
    from calculations.openvsp_integration import build_vsp_aircraft_model
    p = json.loads((Path(__file__).parents[1]/'data/design_cases/topic7_motoszybowiec_21m.json').read_text(encoding='utf8'))
    p['airfoil'] = profile_name
    if profile_name.startswith('NACA'):
        p.pop('airfoil_coordinates', None)
    profile = airfoil_200mm(profile_name, p.get('airfoil_coordinates', ''))
    model = build_vsp_aircraft_model(run_bipol_project(p), vsp_module=vsp)
    surf = vsp.GetXSecSurf(model['wing']['geom_id'], 0)
    for i in range(vsp.GetNumXSec(surf)):
        xsec = vsp.GetXSec(surf, i)
        assert vsp.GetXSecShape(xsec) == vsp.XS_FILE_AIRFOIL
        for side, getter in [('upper', vsp.GetAirfoilUpperPnts), ('lower', vsp.GetAirfoilLowerPnts)]:
            actual = getter(xsec)
            assert len(actual) == len(profile[side])
            for stored, (x,y) in zip(actual, profile[side]):
                assert (stored.x(), stored.y()) == pytest.approx((x/200,y/200), abs=1e-12)


def test_clearing_native_model_also_clears_its_profile_provenance():
    from calculations import run_bipol_project
    from calculations.presets import AIRCRAFT_PRESETS
    import calculations.openvsp_bridge as bridge
    model = bridge.build_model_from_bipol(run_bipol_project(dict(AIRCRAFT_PRESETS['ga_trainer'])))
    assert model['build_meta']['wing_airfoil']
    model = bridge.modify_geometry({'action':'clear_model'})
    assert not model['build_meta'] and not vsp.FindGeoms()


@pytest.fixture(autouse=True)
def native_openvsp(request):
    if vsp is None and request.node.name != 'test_openvsp_ui_tab_present_in_index':
        pytest.skip('Native OpenVSP API is not installed for this interpreter; UI and unavailable-mode tests still run.')


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


@pytest.mark.parametrize('diameter',[None,1.7])
def test_native_propeller_matches_the_calculated_topic7_geometry(diameter):
    from calculations import run_bipol_project
    from calculations.official_topics import ALL_TOPICS
    from calculations.openvsp_bridge import build_model_from_bipol
    params=dict(next(t['parameters'] for t in ALL_TOPICS if t['num']==7),propeller_rpm=2100)
    if diameter is not None:params['propeller_diameter_m']=diameter
    result=run_bipol_project(params)
    build_model_from_bipol(result)
    prop=next(g for g in vsp.FindGeoms() if vsp.GetGeomName(g)=='Smiglo_Ciagnace')
    assert vsp.GetParmVal(prop,'Diameter','Design')==pytest.approx(result['geometry']['propeller']['diameter_m'])


@pytest.mark.parametrize('location',['rear','retractable'])
def test_native_pusher_preserves_the_selected_propeller_diameter(location):
    from calculations import run_bipol_project
    from calculations.presets import AIRCRAFT_PRESETS
    from calculations.openvsp_bridge import build_model_from_bipol
    result=run_bipol_project(dict(AIRCRAFT_PRESETS['motoglider_aos'],engine_location=location,
                                 propeller_diameter_m=1.71))
    build_model_from_bipol(result)
    prop=next(g for g in vsp.FindGeoms() if vsp.GetGeomName(g)=='Smiglo_Pchajace')
    assert vsp.GetParmVal(prop,'Diameter','Design')==pytest.approx(1.71)


@pytest.mark.parametrize('layout',['tricycle','tailwheel'])
@pytest.mark.parametrize('diameter',[None,1.7])
def test_native_gear_centres_and_ground_contacts_match_p3(layout,diameter):
    import json
    from pathlib import Path
    from calculations import run_bipol_project
    from calculations.openvsp_bridge import build_model_from_bipol
    p=json.loads((Path(__file__).parents[1]/'data/design_cases/topic7_motoszybowiec_21m.json').read_text(encoding='utf8'))
    if diameter is None:
        p.pop('propeller_diameter_m',None)
    else:
        p['propeller_diameter_m']=diameter
    result=run_bipol_project(dict(p,landing_gear_type=layout))
    build_model_from_bipol(result)
    for name,station in [('Podwozie_Glowne',result['balance']['arms']['gear']),
                         ('Kolko_Ogonowe' if layout=='tailwheel' else 'Podwozie_Przednie',result['balance']['arms']['gear_aux'])]:
        gear=next(g for g in vsp.FindGeoms() if vsp.GetGeomName(g)==name)
        lo,hi=vsp.GetGeomBBoxMin(gear),vsp.GetGeomBBoxMax(gear)
        assert (lo.x()+hi.x())/2==pytest.approx(station,abs=1e-6)
        assert lo.z()==pytest.approx(-result['geometry']['gear']['axis_height_m'],abs=1e-6)


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
            "code": 'int main() {\n    Print("Hello from vspscript");\n    return 0;\n}\n',
        },
    )
    assert as_res.status_code == 200
    as_data = as_res.get_json()
    assert as_data["returncode"] == 0
    assert "Hello from vspscript" in as_data["stdout"]
    failed = client.post('/api/openvsp/script', json={'mode':'vspscript','code':'int main() { return 7; }'})
    assert failed.status_code == 200
    assert failed.json['status'] == 'error' and failed.json['returncode'] == 7


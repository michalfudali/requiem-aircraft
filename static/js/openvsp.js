/**
 * Moduł UI OpenVSP 3.55.0 Studio & Pełny Wykonawca API (static/js/openvsp.js)
 * Obsługuje:
 * 1. Synchronizację projektu BiPOL -> parametryczny model 3D OpenVSP (`build-from-bipol`)
 * 2. Interaktywny renderer 3D Canvas dla rzeczywistych płatów powierzchni OpenVSP (`SurfacePatches`)
 * 3. Drzewo Geometrii (`Geom`, `SubSurf`, `XSec`) oraz żywy edytor wszystkich parametrów (`SetParmVal`)
 * 4. Konfigurator i uruchamianie wszystkich 22 analiz OpenVSP (`CompGeom`, `ParasiteDrag`, `VSPAEROSweep`, `MassProp`, `WaveDrag`, `PlanarSlice`, itd.)
 * 5. Katalog, wyszukiwarkę i żywy wykonawca wszystkich 1 094 funkcji API oraz 1 046 stałych OpenVSP
 * 6. Zarządzanie zbiorami (`Sets`), zmiennymi projektowymi (`DesignVars`) oraz sondami 3D (`Probes`/`Rulers`)
 * 7. Eksport i import CAD/CFD/FEA (`.vsp3`, `STEP`, `IGES`, `STL`, `OBJ`, `X3D`, `DXF`, `SVG`, `Gmsh`, `Nastran`, `CalculiX`, `Cart3D`, `.des`)
 * 8. Studio skryptowe Python `openvsp` oraz AngelScript `.vspscript`
 */
(function () {
    'use strict';

    const state = {
        catalog: null,
        model: null,
        selectedGeomId: null,
        selectedFunc: null,
        camera: {
            yaw: -0.62,
            pitch: 0.34,
            zoom: 1.0,
            panX: 0,
            panY: 0,
            dragging: false,
            lastX: 0,
            lastY: 0,
        },
        initialized: false,
    };

    const SCRIPT_TEMPLATES = {
        inspect_bipol: `# Szablon 1: Inspekcja modelu 3D OpenVSP i analiza powierzchni omywanej CompGeom
geoms = vsp.FindGeoms()
print(f"Wersja silnika: {vsp.GetVSPVersion()}")
print(f"Liczba komponentów w modelu: {len(geoms)}")
for gid in geoms:
    print(f" - [{gid}] {vsp.GetGeomName(gid)} ({vsp.GetGeomTypeName(gid)}) | SubSurfs: {len(vsp.GetSubSurfIDVec(gid))}")

res_id = vsp.ExecAnalysis("CompGeom")
wet_total = vsp.GetDoubleResults(res_id, "Total_Wet_Area")[0]
vol_total = vsp.GetDoubleResults(res_id, "Total_Wet_Vol")[0]
print(f"\\nCałkowita powierzchnia omywana 3D (CompGeom): {wet_total:.3f} m^2")
print(f"Całkowita objętość 3D (CompGeom): {vol_total:.4f} m^3")
result = {"wet_area_m2": round(wet_total, 3), "wet_vol_m3": round(vol_total, 4)}
`,
        parametric_wing: `# Szablon 2: Parametryczna modyfikacja skrzydła głównego w OpenVSP
wing_id = vsp.FindGeom("Skrzydlo_Glowne", 0)
if not wing_id and vsp.FindGeoms():
    wing_id = vsp.FindGeoms()[0]

if wing_id:
    xsurf = vsp.GetXSecSurf(wing_id, 0)
    xsec1 = vsp.GetXSec(xsurf, 1)
    span_parm = vsp.GetXSecParm(xsec1, "Span")
    sweep_parm = vsp.GetXSecParm(xsec1, "Sweep")
    dihedral_parm = vsp.GetXSecParm(xsec1, "Dihedral")

    old_span = vsp.GetParmVal(span_parm)
    vsp.SetParmVal(sweep_parm, 8.0)
    vsp.SetParmVal(dihedral_parm, 4.5)
    vsp.Update()
    print(f"Zaktualizowano skrzydło {wing_id}: półrozpiętość={old_span:.2f} m, skos=8.0 deg, wznios=4.5 deg")
    result = {"wing_id": wing_id, "half_span_m": old_span, "sweep_deg": 8.0, "dihedral_deg": 4.5}
`,
        vspaero_polar: `# Szablon 3: Obliczenie biegunowej metodą powierzchni wirowych (VSPAERO VLM)
vsp.SetAnalysisInputDefaults("VSPAEROComputeGeometry")
vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "GeomSet", [vsp.SET_NONE])
vsp.SetIntAnalysisInput("VSPAEROComputeGeometry", "ThinGeomSet", [vsp.SET_ALL])
vsp.ExecAnalysis("VSPAEROComputeGeometry")

vsp.SetAnalysisInputDefaults("VSPAEROSweep")
vsp.SetIntAnalysisInput("VSPAEROSweep", "GeomSet", [vsp.SET_NONE])
vsp.SetIntAnalysisInput("VSPAEROSweep", "ThinGeomSet", [vsp.SET_ALL])
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "AlphaStart", [0.0])
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "AlphaEnd", [8.0])
vsp.SetIntAnalysisInput("VSPAEROSweep", "AlphaNpts", [3])
vsp.SetDoubleAnalysisInput("VSPAEROSweep", "MachStart", [0.18])
vsp.SetIntAnalysisInput("VSPAEROSweep", "MachNpts", [1])
vsp.SetIntAnalysisInput("VSPAEROSweep", "WakeNumIter", [2])
vsp.SetIntAnalysisInput("VSPAEROSweep", "NCPU", [4])

sw_res = vsp.ExecAnalysis("VSPAEROSweep")
rvec = vsp.GetStringResults(sw_res, "ResultsVec")
polar_id = [r for r in rvec if vsp.GetResultsName(r) == "VSPAERO_Polar"][0]
alphas = list(vsp.GetDoubleResults(polar_id, "Alpha"))
cls = list(vsp.GetDoubleResults(polar_id, "CLtot"))
cds = list(vsp.GetDoubleResults(polar_id, "CDtot"))
for a, cl, cd in zip(alphas, cls, cds):
    print(f"Alpha = {a:5.1f} deg | CL = {cl:7.4f} | CDi+CDo = {cd:7.5f}")
result = {"Alpha": alphas, "CL": cls, "CD": cds}
`,
        batch_cad: `# Szablon 4: Wsadowy eksport modelu 3D do STEP, IGES, STL i SVG
exports = [
    ("bipol_batch.vsp3", None),
    ("bipol_batch.stp", vsp.EXPORT_STEP),
    ("bipol_batch.igs", vsp.EXPORT_IGES),
    ("bipol_batch.stl", vsp.EXPORT_STL),
    ("bipol_batch.svg", vsp.EXPORT_SVG),
]
generated = []
for fname, fmt in exports:
    rel = f"{WORK_DIR}/{fname}"
    if fmt is None:
        vsp.WriteVSPFile(rel, vsp.SET_ALL)
    else:
        vsp.ExportFile(rel, vsp.SET_ALL, fmt)
    print(f"Wyeksportowano: {rel}")
    generated.append(rel)
result = {"exported_files": generated}
`,
        vspscript_demo: `// Szablon 5: Natywny skrypt AngelScript (.vspscript) wykonywany przez vspscript.exe
int main()
{
    Print( "=== Uruchomiono silnik AngelScript OpenVSP ===" );
    string wid = AddGeom( "WING", "" );
    SetGeomName( wid, "Skrzydlo_AngelScript" );
    SetParmVal( wid, "Span", "XSec_1", 6.5 );
    SetParmVal( wid, "Root_Chord", "XSec_1", 1.6 );
    SetParmVal( wid, "Tip_Chord", "XSec_1", 0.95 );
    Update();
    SetComputationFileName( COMP_GEOM_TXT_TYPE, "work/openvsp/angelscript_compgeom.txt" );
    SetComputationFileName( COMP_GEOM_CSV_TYPE, "work/openvsp/angelscript_compgeom.csv" );
    string comp_res = ExecAnalysis( "CompGeom" );
    PrintResults( comp_res );
    WriteVSPFile( "work/openvsp/angelscript_wing.vsp3", SET_ALL );
    return 0;
}
`,
    };

    function el(id) {
        return document.getElementById(id);
    }

    function escapeHtml(str) {
        return String(str == null ? '' : str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    async function apiFetch(url, options) {
        const resp = await fetch(url, options);
        const data = await resp.json();
        if (!resp.ok || data.status === 'error') {
            throw new Error(data.message || data.stderr || `Błąd HTTP ${resp.status}`);
        }
        return data;
    }

    // =========================================================================
    // 1. INICJALIZACJA KATALOGU API I STANU MODELU
    // =========================================================================
    async function loadCatalogAndInitialModel() {
        if (state.catalogLoaded) return;
        state.catalogLoaded = true;
        try {
            const availability = await apiFetch('/api/openvsp/status');
            const notice = el('vspAvailability');
            if (!availability.available) {
                if (notice) { notice.hidden = false; notice.textContent = availability.message; }
                document.querySelectorAll('#tab-openvsp button, #tab-openvsp input, #tab-openvsp select, #tab-openvsp textarea')
                    .forEach(control => { control.disabled = true; });
                document.querySelectorAll('#tab-openvsp a[download]').forEach(link => {
                    link.removeAttribute('href'); link.setAttribute('aria-disabled', 'true');
                });
                return;
            }
            const cat = await apiFetch('/api/openvsp/catalog');
            state.catalog = cat;
            renderKpiFromCatalog(cat);
            populateCategoryFilter(cat);
            populateConstantsTable(cat);
            populateAnalysisSelector(cat);
            renderFunctionList();
            if (cat.functions && cat.functions.length > 0) {
                selectFunction(cat.functions.find(f => f.name === 'GetVSPVersion') || cat.functions[0]);
            }

            // Pobierz aktualny model lub zbuduj z aktywnego projektu BiPOL
            const model = await apiFetch('/api/openvsp/model');
            if (model.num_geoms === 0) {
                await syncModelFromBipol(false);
            } else {
                applyModelState(model);
            }
            const status = await apiFetch('/api/openvsp/status');
            renderWorkspaceFiles(status.files || []);
        } catch (err) {
            console.error('OpenVSP init error:', err);
        }
    }

    function renderKpiFromCatalog(cat) {
        if (!cat) return;
        const verEl = el('vspStatVersion');
        const aeroEl = el('vspStatVspaero');
        const funcsEl = el('vspStatFuncs');
        const constsEl = el('vspStatConsts');
        if (verEl) verEl.textContent = cat.version || 'OpenVSP 3.55.0';
        if (aeroEl) {
            aeroEl.textContent = cat.vspaero_available
                ? 'Solwer VSPAERO aktywny · vspscript aktywny'
                : 'Tryb geometryczny C++';
        }
        if (funcsEl && cat.counts) {
            funcsEl.textContent = `${cat.counts.functions} funkcji API (${cat.counts.core_vsp_functions} C++)`;
        }
        if (constsEl && cat.counts) {
            constsEl.textContent = `${cat.counts.constants} stałych · ${cat.counts.analyses} analiz · ${cat.counts.geom_types} typów Geom`;
        }
    }

    async function syncModelFromBipol(showToast = true) {
        const btn = el('vspSyncFromBipolBtn');
        const overlay = el('vspCanvasOverlay');
        if (btn) {
            btn.disabled = true;
            btn.textContent = '⏳ Generowanie bryły 3D w OpenVSP...';
        }
        if (overlay) overlay.textContent = 'Trwa budowa parametrycznej geometrii 3D w OpenVSP...';
        try {
            const payload = typeof currentResults !== 'undefined' && currentResults?.geometry ? currentResults : null;
            if (!payload) throw new Error('Najpierw oblicz bieżący projekt, a następnie zsynchronizuj model 3D.');
            const model = await apiFetch('/api/openvsp/build-from-bipol', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            applyModelState(model);
            const status = await apiFetch('/api/openvsp/status');
            renderWorkspaceFiles(status.files || []);
            if (showToast && overlay) {
                overlay.textContent = `Zsynchronizowano model 3D (${model.num_geoms} komponentów) z bieżącym projektem BiPOL.`;
            }
        } catch (err) {
            if (overlay) overlay.textContent = `Błąd synchronizacji: ${err.message}`;
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = '🔄 Synchronizuj model 3D z projektem BiPOL';
            }
        }
    }

    function applyModelState(model) {
        if (!model) return;
        state.model = model;
        const geoms = model.geoms || [];
        if (!state.selectedGeomId || !geoms.some(g => g.id === state.selectedGeomId)) {
            const wingGeom = geoms.find(g => g.type === 'Wing');
            state.selectedGeomId = wingGeom ? wingGeom.id : (geoms[0] ? geoms[0].id : null);
        }

        const totalParms = geoms.reduce((acc, g) => acc + (g.num_parameters || 0), 0);
        const geomsEl = el('vspStatGeoms');
        const parmsEl = el('vspStatParms');
        if (geomsEl) geomsEl.textContent = `${geoms.length} komponentów 3D`;
        if (parmsEl) parmsEl.textContent = `${totalParms} parametrów w kontenerach`;

        const meta = (model.build_meta && model.build_meta.bipol_summary) || null;
        const wingRefEl = el('vspStatWingRef');
        const swetRefEl = el('vspStatSwetRef');
        if (meta && wingRefEl && swetRefEl) {
            wingRefEl.textContent = `S = ${meta.S_m2} m² · b = ${meta.b_m} m`;
            swetRefEl.textContent = `S_wet (BiPOL P3): ${meta.S_wet_bipol_m2} m² · Cx0: ${meta.cx0_clean_bipol}`;
        } else {
            if (wingRefEl) wingRefEl.textContent = '—';
            if (swetRefEl) swetRefEl.textContent = 'Brak powiązania modelu z obliczeniami P3';
        }
        const airfoil = model.build_meta?.wing_airfoil;
        const planform = model.build_meta?.wing_planform;
        const planformStatus = el('vspWingPlanformStatus');
        if (planformStatus) {
            const number = value => Number(value).toFixed(3).replace('.', ',');
            planformStatus.textContent = planform
                ? `Rzut skrzydła przy budowie: b = ${number(planform.projected_span_m)} m · S = ${number(planform.projected_area_m2)} m². ${planform.note}`
                : 'Brak danych o obrysie wybranym przy budowie modelu.';
        }
        const airfoilStatus = el('vspWingAirfoilStatus');
        if (airfoilStatus) {
            airfoilStatus.textContent = !airfoil ? 'Brak danych o profilu wybranym przy budowie modelu.' :
                airfoil.assumed ? airfoil.warnings.join(' ') :
                `Profil skrzydła przy budowie: ${airfoil.profile_name} · ${airfoil.point_count} rzędnych · t/c = ${airfoil.tc_ratio}. ${airfoil.warnings.join(' ')}`;
        }

        renderGeomTree();
        renderSelectedGeomInspector();
        renderSetsAndDesignVars();
        draw3dViewport();
        if (model.files) {
            renderWorkspaceFiles(model.files);
        }
    }

    // =========================================================================
    // 2. RENDERER 3D CANVAS DLA SIATKI SURFACE PATCHES Z OPENVSP
    // =========================================================================
    const COMP_COLORS = {
        Fuselage: { fill: 'rgba(148, 163, 184, 0.44)', stroke: '#cbd5e1' },
        Wing: { fill: 'rgba(56, 189, 248, 0.46)', stroke: '#38bdf8' },
        Propeller: { fill: 'rgba(251, 191, 36, 0.55)', stroke: '#fbbf24' },
        Pod: { fill: 'rgba(167, 139, 250, 0.48)', stroke: '#a78bfa' },
        Default: { fill: 'rgba(52, 211, 153, 0.45)', stroke: '#34d399' },
    };

    function draw3dViewport() {
        const canvas = el('vsp3dCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const rect = canvas.getBoundingClientRect();
        if (rect.width > 50 && rect.height > 50) {
            canvas.width = rect.width * (window.devicePixelRatio || 1);
            canvas.height = rect.height * (window.devicePixelRatio || 1);
            ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
        }
        const W = rect.width || 800;
        const H = rect.height || 430;
        ctx.clearRect(0, 0, W, H);

        const mesh = state.model && state.model.mesh;
        if (!mesh || !mesh.components || mesh.components.length === 0) {
            return;
        }

        const bbox = mesh.bbox || { min_x: 0, max_x: 10, min_y: -5, max_y: 5, min_z: -2, max_z: 2 };
        const cx = 0.5 * (bbox.min_x + bbox.max_x);
        const cy = 0.5 * (bbox.min_y + bbox.max_y);
        const cz = 0.5 * (bbox.min_z + bbox.max_z);
        const maxSpan = Math.max(
            0.5,
            bbox.max_x - bbox.min_x,
            bbox.max_y - bbox.min_y,
            bbox.max_z - bbox.min_z
        );
        const scale = (Math.min(W, H) * 0.72 * state.camera.zoom) / maxSpan;

        const cosY = Math.cos(state.camera.yaw);
        const sinY = Math.sin(state.camera.yaw);
        const cosP = Math.cos(state.camera.pitch);
        const sinP = Math.sin(state.camera.pitch);

        function project(vx, vy, vz) {
            const dx = vx - cx;
            const dy = vy - cy;
            const dz = vz - cz;
            const x1 = dx * cosY - dy * sinY;
            const y1 = dx * sinY + dy * cosY;
            const z1 = dz;
            const sx = x1;
            const sy = y1 * sinP - z1 * cosP;
            const depth = y1 * cosP + z1 * sinP;
            return {
                x: W * 0.5 + state.camera.panX + sx * scale,
                y: H * 0.5 + state.camera.panY + sy * scale,
                depth: depth,
            };
        }

        const showWire = el('vspWireframeToggle') ? el('vspWireframeToggle').checked : true;
        const showShade = el('vspShadedToggle') ? el('vspShadedToggle').checked : true;

        const quads = [];
        for (const comp of mesh.components) {
            const isSelected = comp.id === state.selectedGeomId;
            const palette = isSelected
                ? { fill: 'rgba(244, 63, 94, 0.52)', stroke: '#fb7185' }
                : (COMP_COLORS[comp.type] || COMP_COLORS.Default);

            for (const patch of comp.patches || []) {
                const X = patch.x;
                const Y = patch.y;
                const Z = patch.z;
                const nu = X.length;
                if (nu < 2) continue;
                const nw = X[0].length;
                if (nw < 2) continue;

                const pts = [];
                for (let i = 0; i < nu; i++) {
                    const row = [];
                    for (let j = 0; j < nw; j++) {
                        row.push(project(X[i][j], Y[i][j], Z[i][j]));
                    }
                    pts.push(row);
                }

                for (let i = 0; i < nu - 1; i++) {
                    for (let j = 0; j < nw - 1; j++) {
                        const p00 = pts[i][j];
                        const p10 = pts[i + 1][j];
                        const p11 = pts[i + 1][j + 1];
                        const p01 = pts[i][j + 1];
                        const avgDepth = 0.25 * (p00.depth + p10.depth + p11.depth + p01.depth);
                        quads.push({ p00, p10, p11, p01, depth: avgDepth, palette });
                    }
                }
            }
        }

        quads.sort((a, b) => a.depth - b.depth);

        ctx.lineWidth = 0.65;
        for (const q of quads) {
            ctx.beginPath();
            ctx.moveTo(q.p00.x, q.p00.y);
            ctx.lineTo(q.p10.x, q.p10.y);
            ctx.lineTo(q.p11.x, q.p11.y);
            ctx.lineTo(q.p01.x, q.p01.y);
            ctx.closePath();
            if (showShade) {
                ctx.fillStyle = q.palette.fill;
                ctx.fill();
            }
            if (showWire) {
                ctx.strokeStyle = q.palette.stroke;
                ctx.stroke();
            }
        }

        const overlay = el('vspCanvasOverlay');
        if (overlay && state.model) {
            overlay.textContent = `Komponenty: ${mesh.components.length} · Siatka czworokątów UV: ${quads.length} · Wybrany: ${state.selectedGeomId || '—'}`;
        }
    }

    function setupCanvasInteractions() {
        const canvas = el('vsp3dCanvas');
        if (!canvas) return;

        canvas.addEventListener('mousedown', (e) => {
            state.camera.dragging = true;
            state.camera.lastX = e.clientX;
            state.camera.lastY = e.clientY;
        });

        window.addEventListener('mousemove', (e) => {
            if (!state.camera.dragging) return;
            const dx = e.clientX - state.camera.lastX;
            const dy = e.clientY - state.camera.lastY;
            state.camera.lastX = e.clientX;
            state.camera.lastY = e.clientY;
            if (e.shiftKey) {
                state.camera.panX += dx;
                state.camera.panY += dy;
            } else {
                state.camera.yaw += dx * 0.01;
                state.camera.pitch = Math.max(-1.45, Math.min(1.45, state.camera.pitch + dy * 0.01));
            }
            draw3dViewport();
        });

        window.addEventListener('mouseup', () => {
            state.camera.dragging = false;
        });

        canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const factor = e.deltaY < 0 ? 1.12 : 0.89;
            state.camera.zoom = Math.max(0.25, Math.min(5.0, state.camera.zoom * factor));
            draw3dViewport();
        }, { passive: false });

        document.querySelectorAll('[data-vsp-cam]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const mode = btn.getAttribute('data-vsp-cam');
                state.camera.panX = 0;
                state.camera.panY = 0;
                state.camera.zoom = 1.0;
                if (mode === 'top') {
                    state.camera.yaw = 0;
                    state.camera.pitch = 1.55;
                } else if (mode === 'side') {
                    state.camera.yaw = 0;
                    state.camera.pitch = 0;
                } else if (mode === 'front') {
                    state.camera.yaw = -Math.PI / 2;
                    state.camera.pitch = 0;
                } else {
                    state.camera.yaw = -0.62;
                    state.camera.pitch = 0.34;
                }
                draw3dViewport();
            });
        });

        ['vspWireframeToggle', 'vspShadedToggle'].forEach((id) => {
            const cb = el(id);
            if (cb) cb.addEventListener('change', draw3dViewport);
        });
    }

    // =========================================================================
    // 3. DRZEWO GEOMETRII I EDYTOR PARAMETRÓW (GEOM & PARM INSPECTOR)
    // =========================================================================
    function renderGeomTree() {
        const container = el('vspGeomTreeList');
        if (!container || !state.model) return;
        const geoms = state.model.geoms || [];
        if (geoms.length === 0) {
            container.innerHTML = '<div class="vsp-empty-state">Brak komponentów w modelu OpenVSP.</div>';
            return;
        }
        container.innerHTML = geoms.map((g) => {
            const isAct = g.id === state.selectedGeomId ? 'active' : '';
            const ssCount = (g.subsurfaces || []).length;
            const ssBadge = ssCount > 0 ? `<span class="vsp-geom-type-tag">${ssCount} SubSurf</span>` : '';
            return `<button type="button" class="vsp-geom-pill ${isAct}" data-vsp-geom-id="${escapeHtml(g.id)}">
                <span>${escapeHtml(g.name)}</span>
                <span class="vsp-geom-type-tag">${escapeHtml(g.type)}</span>
                ${ssBadge}
            </button>`;
        }).join('');

        container.querySelectorAll('[data-vsp-geom-id]').forEach((btn) => {
            btn.addEventListener('click', () => {
                state.selectedGeomId = btn.getAttribute('data-vsp-geom-id');
                renderGeomTree();
                renderSelectedGeomInspector();
                draw3dViewport();
            });
        });
    }

    function renderSelectedGeomInspector() {
        const titleEl = el('vspSelectedGeomTitle');
        const groupSelect = el('vspParmGroupSelect');
        const tbody = el('vspParmTableBody');
        if (!tbody || !state.model) return;

        const geom = (state.model.geoms || []).find(g => g.id === state.selectedGeomId);
        if (!geom) {
            if (titleEl) titleEl.textContent = 'Brak wybranego komponentu';
            tbody.innerHTML = '<tr><td colspan="5" class="vsp-empty-cell">Wybierz komponent z drzewa powyżej.</td></tr>';
            return;
        }

        const ssNames = (geom.subsurfaces || []).map(s => s.name).join(', ');
        if (titleEl) {
            titleEl.textContent = `${geom.name} [${geom.id}] · Typ: ${geom.type} · Przekroje XSec: ${(geom.xsecs || []).length}${ssNames ? ' · Sterowanie: ' + ssNames : ''}`;
        }

        const groups = geom.parameter_groups || {};
        const groupNames = Object.keys(groups).sort();
        const prevGroup = groupSelect ? groupSelect.value : 'ALL';
        if (groupSelect) {
            groupSelect.innerHTML = '<option value="ALL">Wszystkie grupy (' + geom.num_parameters + ')</option>' +
                groupNames.map(g => `<option value="${escapeHtml(g)}">${escapeHtml(g)} (${groups[g].length})</option>`).join('');
            if (groupNames.includes(prevGroup)) {
                groupSelect.value = prevGroup;
            }
        }

        renderParmTableRows(geom);
    }

    function renderParmTableRows(geom) {
        const tbody = el('vspParmTableBody');
        if (!tbody || !geom) return;
        const grpFilter = el('vspParmGroupSelect') ? el('vspParmGroupSelect').value : 'ALL';
        const q = (el('vspParmSearchInput') ? el('vspParmSearchInput').value : '').trim().toLowerCase();

        const groups = geom.parameter_groups || {};
        const rows = [];
        for (const [grp, plist] of Object.entries(groups)) {
            if (grpFilter !== 'ALL' && grp !== grpFilter) continue;
            for (const p of plist) {
                if (q && !p.name.toLowerCase().includes(q) && !grp.toLowerCase().includes(q) && !(p.descript || '').toLowerCase().includes(q)) {
                    continue;
                }
                rows.push(p);
            }
        }

        if (rows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="vsp-empty-cell">Brak parametrów spełniających filtr.</td></tr>';
            return;
        }

        tbody.innerHTML = rows.slice(0, 160).map((p) => {
            const valNum = typeof p.value === 'number' ? Number(p.value.toFixed(5)) : p.value;
            const minStr = typeof p.min === 'number' ? p.min.toExponential(2).replace('+00', '') : '—';
            const maxStr = typeof p.max === 'number' ? p.max.toExponential(2).replace('+00', '') : '—';
            return `<tr>
                <td><code>${escapeHtml(p.group)}</code></td>
                <td title="${escapeHtml(p.descript || '')}">
                    <strong>${escapeHtml(p.name)}</strong>
                    <div class="vsp-arg-type">${escapeHtml(p.descript || p.id)}</div>
                </td>
                <td>
                    <input type="number" step="0.01" class="vsp-parm-val-input" data-parm-input="${escapeHtml(p.id)}" value="${escapeHtml(valNum)}">
                </td>
                <td><small>${escapeHtml(minStr)} .. ${escapeHtml(maxStr)}</small></td>
                <td>
                    <button type="button" class="btn-chip" data-parm-save="${escapeHtml(p.id)}">Zastosuj</button>
                </td>
            </tr>`;
        }).join('');

        tbody.querySelectorAll('[data-parm-save]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const pid = btn.getAttribute('data-parm-save');
                const inp = tbody.querySelector(`[data-parm-input="${pid}"]`);
                if (!inp) return;
                const val = parseFloat(inp.value);
                if (Number.isNaN(val)) return;
                btn.disabled = true;
                btn.textContent = '...';
                try {
                    const updatedModel = await apiFetch('/api/openvsp/parm', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ parm_id: pid, value: val }),
                    });
                    applyModelState(updatedModel);
                } catch (err) {
                    alert(`Błąd aktualizacji parametru: ${err.message}`);
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Zastosuj';
                }
            });
        });
    }

    // =========================================================================
    // 4. SOLWERY I WSZYSTKIE 22 ANALIZY OPENVSP
    // =========================================================================
    function populateAnalysisSelector(cat) {
        const sel = el('vspAnalysisSelect');
        if (!sel || !cat || !cat.analyses) return;
        sel.innerHTML = cat.analyses.map(a =>
            `<option value="${escapeHtml(a.name)}">${escapeHtml(a.name)} (${a.num_inputs} wejść)</option>`
        ).join('');
        sel.value = 'CompGeom';
        renderAnalysisInputsTable('CompGeom');

        sel.addEventListener('change', () => {
            renderAnalysisInputsTable(sel.value);
        });
    }

    function renderAnalysisInputsTable(analysisName) {
        const tbody = el('vspAnalysisInputsBody');
        if (!tbody || !state.catalog) return;
        const analysis = (state.catalog.analyses || []).find(a => a.name === analysisName);
        if (!analysis || !analysis.inputs.length) {
            tbody.innerHTML = '<tr><td colspan="3" class="vsp-empty-cell">Ta analiza nie wymaga dodatkowych parametrów wejściowych.</td></tr>';
            return;
        }
        tbody.innerHTML = analysis.inputs.map((inp) => {
            const defVal = Array.isArray(inp.default) && inp.default.length === 1
                ? JSON.stringify(inp.default[0])
                : JSON.stringify(inp.default);
            return `<tr>
                <td><strong>${escapeHtml(inp.name)}</strong></td>
                <td><code>${escapeHtml(inp.type)}</code></td>
                <td>
                    <input type="text" class="vsp-input" data-analysis-inp="${escapeHtml(inp.name)}" value="${escapeHtml(defVal)}">
                </td>
            </tr>`;
        }).join('');
    }

    async function executeAnalysis(analysisName, customInputs) {
        const titleEl = el('vspAnalysisResultTitle');
        const metaEl = el('vspAnalysisResultMeta');
        const compBox = el('vspAnalysisComparisonBox');
        const rawJson = el('vspAnalysisRawJson');

        if (titleEl) titleEl.textContent = `⏳ Wykonywanie analizy ${analysisName}...`;
        if (compBox) compBox.innerHTML = '<div class="vsp-empty-state">Trwają obliczenia w jądrze OpenVSP / VSPAERO...</div>';

        try {
            const res = await apiFetch('/api/openvsp/analysis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    analysis: analysisName,
                    inputs: customInputs || {},
                    reset_defaults: true,
                }),
            });
            if (titleEl) titleEl.textContent = `Wyniki analizy: ${res.analysis} (ID: ${res.result_id})`;
            if (metaEl) metaEl.textContent = `Czas obliczeń C++: ${res.elapsed_ms} ms`;
            if (rawJson) rawJson.textContent = JSON.stringify(res.results, null, 2);
            renderAnalysisComparison(res);
        } catch (err) {
            if (titleEl) titleEl.textContent = `Błąd analizy ${analysisName}`;
            if (compBox) compBox.innerHTML = `<div class="vsp-empty-state">Błąd: ${escapeHtml(err.message)}</div>`;
        }
    }

    function renderAnalysisComparison(res) {
        const compBox = el('vspAnalysisComparisonBox');
        if (!compBox) return;
        const cmp = res.comparison || {};

        if (cmp.type === 'CompGeom') {
            const rowsHtml = (cmp.components || []).map(c => `<tr>
                <td><strong>${escapeHtml(c.component)}</strong></td>
                <td>${c.wet_area_m2.toFixed(3)} m²</td>
                <td>${c.theo_area_m2.toFixed(3)} m²</td>
                <td>${c.wet_vol_m3.toFixed(4)} m³</td>
            </tr>`).join('');
            compBox.innerHTML = `
                <div class="vsp-kpi-strip">
                    <div class="vsp-kpi-card">
                        <span class="vsp-kpi-label">S_wet 3D (OpenVSP CompGeom)</span>
                        <strong class="vsp-kpi-val">${cmp.total_wet_area_vsp_m2} m²</strong>
                    </div>
                    <div class="vsp-kpi-card">
                        <span class="vsp-kpi-label">S_wet Analityczne (BiPOL P3)</span>
                        <strong class="vsp-kpi-val">${cmp.total_wet_area_bipol_m2} m²</strong>
                    </div>
                    <div class="vsp-kpi-card">
                        <span class="vsp-kpi-label">Różnica (3D vs Raymer/Torenbeek)</span>
                        <strong class="vsp-kpi-val">${cmp.diff_pct > 0 ? '+' : ''}${cmp.diff_pct}%</strong>
                        <span class="vsp-kpi-sub">Objętość całkowita 3D: ${cmp.total_volume_vsp_m3} m³</span>
                    </div>
                </div>
                <table class="vsp-table">
                    <thead><tr><th>Komponent</th><th>Pow. omywana S_wet</th><th>Pow. teoretyczna</th><th>Objętość 3D</th></tr></thead>
                    <tbody>${rowsHtml}</tbody>
                </table>`;
            return;
        }

        if (cmp.type === 'ParasiteDrag') {
            const rowsHtml = (cmp.components || []).map(c => `<tr>
                <td><strong>${escapeHtml(c.component)}</strong></td>
                <td>${c.swet_m2.toFixed(3)} m²</td>
                <td>${c.cf.toFixed(5)}</td>
                <td>${c.form_factor.toFixed(3)}</td>
                <td><strong>${c.cd0.toFixed(5)}</strong></td>
            </tr>`).join('');
            compBox.innerHTML = `
                <div class="vsp-kpi-strip">
                    <div class="vsp-kpi-card">
                        <span class="vsp-kpi-label">CD0 3D (OpenVSP ParasiteDrag)</span>
                        <strong class="vsp-kpi-val">${cmp.cd0_vsp}</strong>
                    </div>
                    <div class="vsp-kpi-card">
                        <span class="vsp-kpi-label">Cx0 Czysty (BiPOL P4)</span>
                        <strong class="vsp-kpi-val">${cmp.cx0_bipol}</strong>
                    </div>
                    <div class="vsp-kpi-card">
                        <span class="vsp-kpi-label">Różnica Względna</span>
                        <strong class="vsp-kpi-val">${cmp.diff_pct > 0 ? '+' : ''}${cmp.diff_pct}%</strong>
                    </div>
                </div>
                <table class="vsp-table">
                    <thead><tr><th>Komponent</th><th>S_wet [m²]</th><th>C_f</th><th>Wsp. kształtu FF</th><th>Udział ΔCD0</th></tr></thead>
                    <tbody>${rowsHtml}</tbody>
                </table>`;
            return;
        }

        if (cmp.type === 'VSPAERO') {
            const polarRows = (cmp.polar || []).map(p => `<tr>
                <td>${p.alpha_deg}°</td>
                <td><strong>${p.CL}</strong></td>
                <td>${p.CDi}</td>
                <td>${p.CDo}</td>
                <td>${p.CD}</td>
                <td><strong>${p.L_D}</strong></td>
                <td>${p.Cmy}</td>
            </tr>`).join('');
            const spanRows = (cmp.spanwise_load || []).slice(0, 14).map(s => `<tr>
                <td>${s.y_m} m</td>
                <td>${s.eta}</td>
                <td><strong>${s.cl}</strong></td>
                <td>${s.chord_m} m</td>
            </tr>`).join('');
            compBox.innerHTML = `
                <h4>Biegunowa Aerodynamiczna z Solwera Wirowego VSPAERO (VLM)</h4>
                <table class="vsp-table">
                    <thead><tr><th>Kąt natarcia α</th><th>CL</th><th>CDi (indukowany)</th><th>CDo</th><th>CD całkowity</th><th>Doskonałość L/D</th><th>Cmy</th></tr></thead>
                    <tbody>${polarRows || '<tr><td colspan="7">Brak punktów biegunowej</td></tr>'}</tbody>
                </table>
                <hr class="vsp-divider">
                <h4>Rozkład Współczynnika Siły Nośnej cl(y) wzdłuż Półrozpiętości (VSPAERO)</h4>
                <table class="vsp-table">
                    <thead><tr><th>y [m]</th><th>η = 2y/b</th><th>Lokalne cl (VSPAERO)</th><th>Cięciwa c(y)</th></tr></thead>
                    <tbody>${spanRows || '<tr><td colspan="4">Brak danych pasmowych</td></tr>'}</tbody>
                </table>`;
            return;
        }

        if (cmp.type === 'MassProp') {
            const cg = cmp.total_cg || { x: 0, y: 0, z: 0 };
            compBox.innerHTML = `
                <div class="vsp-kpi-strip">
                    <div class="vsp-kpi-card"><span class="vsp-kpi-label">Masa Bryły 3D</span><strong class="vsp-kpi-val">${Number(cmp.total_mass || 0).toFixed(2)}</strong></div>
                    <div class="vsp-kpi-card"><span class="vsp-kpi-label">Objętość 3D</span><strong class="vsp-kpi-val">${Number(cmp.total_volume || 0).toFixed(4)} m³</strong></div>
                    <div class="vsp-kpi-card"><span class="vsp-kpi-label">Środek Masy (X, Y, Z)</span><strong class="vsp-kpi-val">(${Number(cg.x || 0).toFixed(2)}, ${Number(cg.y || 0).toFixed(2)}, ${Number(cg.z || 0).toFixed(2)}) m</strong></div>
                    <div class="vsp-kpi-card"><span class="vsp-kpi-label">Momenty (Ixx, Iyy, Izz)</span><strong class="vsp-kpi-val">${Number(cmp.ixx || 0).toFixed(1)} / ${Number(cmp.iyy || 0).toFixed(1)} / ${Number(cmp.izz || 0).toFixed(1)}</strong></div>
                </div>`;
            return;
        }

        const dataKeys = Object.keys((res.results && res.results.data) || {});
        compBox.innerHTML = `<div class="vsp-empty-state">Analiza <strong>${escapeHtml(res.analysis)}</strong> zakończona pomyślnie. Zwrócono ${dataKeys.length} wektorów danych w drzewie <code>ResultsMgr</code> poniżej.</div>`;
    }

    // =========================================================================
    // 5. EKSPLORATOR I ŻYWY WYKONAWCA WSZYSTKICH 1094 FUNKCJI API + STAŁE
    // =========================================================================
    function populateCategoryFilter(cat) {
        const sel = el('vspFuncCategorySelect');
        if (!sel || !cat) return;
        sel.innerHTML = `<option value="ALL">Wszystkie kategorie (${cat.counts.functions} funkcji)</option>` +
            (cat.categories || []).map(c =>
                `<option value="${escapeHtml(c.name)}">${escapeHtml(c.name)} (${c.count})</option>`
            ).join('');
    }

    function renderFunctionList() {
        const container = el('vspFuncListContainer');
        const countBar = el('vspFuncCountBar');
        if (!container || !state.catalog) return;

        const q = (el('vspFuncSearchInput') ? el('vspFuncSearchInput').value : '').trim().toLowerCase();
        const catFilter = el('vspFuncCategorySelect') ? el('vspFuncCategorySelect').value : 'ALL';

        const filtered = (state.catalog.functions || []).filter((f) => {
            if (catFilter !== 'ALL' && f.category !== catFilter) return false;
            if (!q) return true;
            return f.name.toLowerCase().includes(q) ||
                (f.signature || '').toLowerCase().includes(q) ||
                (f.doc || '').toLowerCase().includes(q);
        });

        if (countBar) {
            countBar.textContent = `Pasujących funkcji API: ${filtered.length} z ${state.catalog.counts.functions}`;
        }

        const shown = filtered.slice(0, 250);
        container.innerHTML = shown.map((f) => {
            const isAct = state.selectedFunc && state.selectedFunc.name === f.name ? 'active' : '';
            return `<button type="button" class="vsp-func-item ${isAct}" data-vsp-func="${escapeHtml(f.name)}">
                <span class="vsp-func-item-name">${escapeHtml(f.name)}()</span>
                <span class="vsp-func-item-cat">${escapeHtml(f.category)} · → ${escapeHtml(f.return_type)}</span>
            </button>`;
        }).join('');

        container.querySelectorAll('[data-vsp-func]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const fname = btn.getAttribute('data-vsp-func');
                const fObj = (state.catalog.functions || []).find(x => x.name === fname);
                if (fObj) selectFunction(fObj);
            });
        });
    }

    function selectFunction(fObj) {
        state.selectedFunc = fObj;
        const nameEl = el('vspRunnerFuncName');
        const sigEl = el('vspRunnerFuncSig');
        const docEl = el('vspRunnerDocstring');
        const argsBox = el('vspRunnerArgsContainer');

        if (nameEl) nameEl.textContent = `vsp.${fObj.name}`;
        if (sigEl) sigEl.textContent = fObj.signature || `${fObj.name}()`;
        if (docEl) docEl.textContent = fObj.doc || 'Brak dodatkowego opisu docstring SWIG.';

        if (argsBox) {
            const params = fObj.params || [];
            if (params.length === 0) {
                argsBox.innerHTML = '<div class="vsp-runner-hint">Funkcja bezargumentowa — gotowa do bezpośredniego wywołania.</div>';
            } else {
                const defaultGeomId = state.selectedGeomId || ((state.model && state.model.geoms && state.model.geoms[0]) ? state.model.geoms[0].id : '');
                argsBox.innerHTML = params.map((p, idx) => {
                    let placeholder = p.default != null ? String(p.default) : '';
                    let initialVal = p.default != null ? String(p.default) : '';
                    if (!initialVal && p.name.toLowerCase().includes('geom_id')) {
                        initialVal = defaultGeomId;
                    } else if (!initialVal && p.name.toLowerCase().includes('analysis')) {
                        initialVal = 'CompGeom';
                    } else if (!initialVal && p.name.toLowerCase() === 'set') {
                        initialVal = 'SET_ALL';
                    }
                    return `<div class="vsp-arg-row">
                        <div class="vsp-arg-label">
                            ${escapeHtml(p.name)}${p.required ? ' *' : ''}
                            <span class="vsp-arg-type">${escapeHtml(p.type)}</span>
                        </div>
                        <input type="text" class="vsp-input" data-vsp-arg-idx="${idx}" data-vsp-arg-name="${escapeHtml(p.name)}"
                               placeholder="${escapeHtml(placeholder || p.type)}" value="${escapeHtml(initialVal)}">
                    </div>`;
                }).join('');
            }
        }
        renderFunctionList();
    }

    function collectRunnerArgs() {
        const inputs = Array.from(document.querySelectorAll('#vspRunnerArgsContainer [data-vsp-arg-idx]'));
        const args = [];
        for (const inp of inputs) {
            const raw = inp.value.trim();
            if (raw === '') {
                continue;
            }
            try {
                args.push(JSON.parse(raw));
            } catch (_) {
                args.push(raw);
            }
        }
        return args;
    }

    async function executeSelectedApiFunction() {
        if (!state.selectedFunc) return;
        const outEl = el('vspRunnerResultJson');
        const timeEl = el('vspRunnerTimingBadge');
        const autoUpd = el('vspRunnerAutoUpdateToggle') ? el('vspRunnerAutoUpdateToggle').checked : false;
        const args = collectRunnerArgs();

        if (outEl) outEl.textContent = '⏳ Wykonywanie wywołania C++/SWIG...';
        try {
            const res = await apiFetch('/api/openvsp/call', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    function: state.selectedFunc.name,
                    args: args,
                    auto_update: autoUpd,
                    include_model: autoUpd,
                }),
            });
            if (timeEl) timeEl.textContent = `${res.elapsed_ms} ms · ${res.result_type}`;
            if (outEl) outEl.textContent = JSON.stringify(res, null, 2);
            if (res.model) {
                applyModelState(res.model);
            }
        } catch (err) {
            if (outEl) outEl.textContent = JSON.stringify({ status: 'error', message: err.message }, null, 2);
        }
    }

    function populateConstantsTable(cat) {
        const grpSel = el('vspConstGroupSelect');
        if (!grpSel || !cat) return;
        grpSel.innerHTML = `<option value="ALL">Wszystkie grupy (${cat.counts.constants})</option>` +
            (cat.constant_groups || []).map(g =>
                `<option value="${escapeHtml(g.name)}">${escapeHtml(g.name)}_* (${g.count})</option>`
            ).join('');
        renderConstantsRows();
    }

    function renderConstantsRows() {
        const tbody = el('vspConstTableBody');
        if (!tbody || !state.catalog) return;
        const grp = el('vspConstGroupSelect') ? el('vspConstGroupSelect').value : 'ALL';
        const q = (el('vspConstSearchInput') ? el('vspConstSearchInput').value : '').trim().toLowerCase();

        const filtered = (state.catalog.constants || []).filter((c) => {
            if (grp !== 'ALL' && c.group !== grp) return false;
            if (q && !c.name.toLowerCase().includes(q)) return false;
            return true;
        });

        tbody.innerHTML = filtered.slice(0, 150).map(c => `<tr>
            <td><code>vsp.${escapeHtml(c.name)}</code></td>
            <td>${escapeHtml(c.group)}</td>
            <td><strong>${escapeHtml(c.value)}</strong></td>
            <td><button type="button" class="btn-chip" data-copy-const="${escapeHtml(c.name)}">Kopiuj</button></td>
        </tr>`).join('');

        tbody.querySelectorAll('[data-copy-const]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const cname = btn.getAttribute('data-copy-const');
                if (navigator.clipboard) navigator.clipboard.writeText(cname);
                btn.textContent = 'Skopiowano!';
                setTimeout(() => { btn.textContent = 'Kopiuj'; }, 1000);
            });
        });
    }

    // =========================================================================
    // 6. ZBIORY (SETS), ZMIENNE PROJEKTOWE (DESIGNVARS) I POMIARY 3D
    // =========================================================================
    function renderSetsAndDesignVars() {
        if (!state.model) return;
        const geoms = state.model.geoms || [];
        const sets = (state.model.sets || []).slice(0, 8);

        const headEl = el('vspSetsMatrixHead');
        const bodyEl = el('vspSetsMatrixBody');
        if (headEl && bodyEl) {
            headEl.innerHTML = `<tr><th>Komponent</th>${sets.map(s => `<th>Set ${s.index}: ${escapeHtml(s.name)}</th>`).join('')}</tr>`;
            bodyEl.innerHTML = geoms.map(g => `<tr>
                <td><strong>${escapeHtml(g.name)}</strong></td>
                ${sets.map((s) => {
                    const checked = (g.sets || []).includes(s.index) ? 'checked' : '';
                    const disabled = s.index <= 2 ? 'disabled' : '';
                    return `<td><input type="checkbox" data-set-geom="${escapeHtml(g.id)}" data-set-idx="${s.index}" ${checked} ${disabled}></td>`;
                }).join('')}
            </tr>`).join('');

            bodyEl.querySelectorAll('[data-set-geom]').forEach((cb) => {
                cb.addEventListener('change', async () => {
                    await apiFetch('/api/openvsp/manage', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            action: 'set_flag',
                            geom_id: cb.getAttribute('data-set-geom'),
                            set_index: parseInt(cb.getAttribute('data-set-idx'), 10),
                            flag: cb.checked,
                        }),
                    });
                });
            });
        }

        // Lista wszystkich parametrów do wyboru jako DesignVar
        const dvSelect = el('vspDvParmSelect');
        if (dvSelect) {
            const opts = [];
            for (const g of geoms) {
                for (const [grp, plist] of Object.entries(g.parameter_groups || {})) {
                    for (const p of plist) {
                        if (['Design', 'XSec_1', 'XSec_2', 'XForm', 'XSecCurve_0'].includes(grp)) {
                            opts.push(`<option value="${escapeHtml(p.id)}">${escapeHtml(g.name)} : ${escapeHtml(grp)} : ${escapeHtml(p.name)} (${Number(p.value || 0).toFixed(3)})</option>`);
                        }
                    }
                }
            }
            dvSelect.innerHTML = opts.join('');
        }

        const dvBody = el('vspDesignVarsBody');
        if (dvBody) {
            const dvars = state.model.design_vars || [];
            if (dvars.length === 0) {
                dvBody.innerHTML = '<tr><td colspan="5" class="vsp-empty-cell">Brak zarejestrowanych zmiennych projektowych.</td></tr>';
            } else {
                dvBody.innerHTML = dvars.map(d => `<tr>
                    <td>${d.index}</td>
                    <td><code>${escapeHtml(d.parm_id)}</code></td>
                    <td><strong>${escapeHtml(d.parm_name)}</strong></td>
                    <td>${escapeHtml(d.group)}</td>
                    <td>${escapeHtml(d.value)}</td>
                </tr>`).join('');
            }
        }

        const measEl = el('vspMeasuresList');
        if (measEl) {
            const rulers = state.model.rulers || [];
            const probes = state.model.probes || [];
            if (!rulers.length && !probes.length) {
                measEl.innerHTML = '<div class="vsp-runner-hint">Brak aktywnych linijek i sond pomiarowych.</div>';
            } else {
                measEl.innerHTML = [
                    ...rulers.map(r => `<span class="vsp-geom-pill">📏 Miarka: ${escapeHtml(r.name)} (${escapeHtml(r.id)})</span>`),
                    ...probes.map(p => `<span class="vsp-geom-pill">📍 Sonda: ${escapeHtml(p.name)} (${escapeHtml(p.id)})</span>`),
                ].join(' ');
            }
        }
    }

    // =========================================================================
    // 7. EKSPORT I IMPORT PLIKÓW CAD / SIATEK
    // =========================================================================
    function renderWorkspaceFiles(files) {
        const tbody = el('vspWorkspaceFilesBody');
        if (!tbody) return;
        if (!files || files.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="vsp-empty-cell">Brak wygenerowanych plików w katalogu roboczym.</td></tr>';
            return;
        }
        tbody.innerHTML = files.map((f) => {
            const kb = (f.size_bytes / 1024).toFixed(1);
            return `<tr>
                <td><strong>${escapeHtml(f.filename)}</strong></td>
                <td>${kb} KB</td>
                <td>${escapeHtml(f.modified_at)}</td>
                <td><a class="btn-chip" href="${escapeHtml(f.download_url)}" download>⬇ Pobierz</a></td>
            </tr>`;
        }).join('');
    }

    // =========================================================================
    // 8. ZDARZENIA INTERFEJSU UŻYTKOWNIKA
    // =========================================================================
    function bindEvents() {
        // Przełączanie pod-zakładek OpenVSP Studio
        document.querySelectorAll('[data-vsp-subtab]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const target = btn.getAttribute('data-vsp-subtab');
                document.querySelectorAll('[data-vsp-subtab]').forEach(b => b.classList.toggle('active', b === btn));
                document.querySelectorAll('.vsp-subpanel').forEach(p => p.classList.toggle('active', p.id === target));
                if (target === 'vsp-sub-model') {
                    setTimeout(draw3dViewport, 50);
                }
            });
        });

        // Synchronizacja z BiPOL
        const syncBtn = el('vspSyncFromBipolBtn');
        if (syncBtn) syncBtn.addEventListener('click', () => syncModelFromBipol(true));

        const refreshBtn = el('vspRefreshStateBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                const model = await apiFetch('/api/openvsp/model');
                applyModelState(model);
            });
        }

        // Dodawanie / modyfikacja komponentów Geom
        const addGeomBtn = el('vspAddGeomBtn');
        if (addGeomBtn) {
            addGeomBtn.addEventListener('click', async () => {
                const gType = el('vspAddGeomTypeSelect') ? el('vspAddGeomTypeSelect').value : 'WING';
                const gName = el('vspAddGeomNameInput') ? el('vspAddGeomNameInput').value : 'Nowy_Komponent';
                const m = await apiFetch('/api/openvsp/geom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'add_geom', geom_type: gType, name: gName }),
                });
                if (m.created_id) state.selectedGeomId = m.created_id;
                applyModelState(m);
            });
        }

        const addSubSurfBtn = el('vspAddSubSurfBtn');
        if (addSubSurfBtn) {
            addSubSurfBtn.addEventListener('click', async () => {
                if (!state.selectedGeomId) return;
                const ssType = el('vspAddSubSurfTypeSelect') ? el('vspAddSubSurfTypeSelect').value : 'SS_CONTROL';
                const ssName = el('vspAddSubSurfNameInput') ? el('vspAddSubSurfNameInput').value : 'Ster_Dodatkowy';
                const m = await apiFetch('/api/openvsp/geom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action: 'add_subsurf',
                        geom_id: state.selectedGeomId,
                        subsurf_type: ssType,
                        name: ssName,
                    }),
                });
                applyModelState(m);
            });
        }

        const insXSecBtn = el('vspInsertXSecBtn');
        if (insXSecBtn) {
            insXSecBtn.addEventListener('click', async () => {
                if (!state.selectedGeomId) return;
                const m = await apiFetch('/api/openvsp/geom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'insert_xsec', geom_id: state.selectedGeomId, xsec_index: 1 }),
                });
                applyModelState(m);
            });
        }

        const dupGeomBtn = el('vspCopyPasteGeomBtn');
        if (dupGeomBtn) {
            dupGeomBtn.addEventListener('click', async () => {
                if (!state.selectedGeomId) return;
                const m = await apiFetch('/api/openvsp/geom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'copy_paste_geom', geom_id: state.selectedGeomId }),
                });
                if (m.created_id) state.selectedGeomId = m.created_id;
                applyModelState(m);
            });
        }

        const delGeomBtn = el('vspDeleteGeomBtn');
        if (delGeomBtn) {
            delGeomBtn.addEventListener('click', async () => {
                if (!state.selectedGeomId) return;
                const m = await apiFetch('/api/openvsp/geom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'delete_geom', geom_id: state.selectedGeomId }),
                });
                state.selectedGeomId = null;
                applyModelState(m);
            });
        }

        // Filtrowanie parametrów
        ['vspParmGroupSelect', 'vspParmSearchInput'].forEach((id) => {
            const node = el(id);
            if (!node) return;
            node.addEventListener('input', () => {
                const geom = state.model && (state.model.geoms || []).find(g => g.id === state.selectedGeomId);
                if (geom) renderParmTableRows(geom);
            });
        });

        // Szybkie karty analiz
        document.querySelectorAll('[data-vsp-quick-analysis]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const aName = btn.getAttribute('data-vsp-quick-analysis');
                const sel = el('vspAnalysisSelect');
                if (sel) {
                    sel.value = aName;
                    renderAnalysisInputsTable(aName);
                }
                executeAnalysis(aName, {});
            });
        });

        const execAnaBtn = el('vspExecuteSelectedAnalysisBtn');
        if (execAnaBtn) {
            execAnaBtn.addEventListener('click', () => {
                const sel = el('vspAnalysisSelect');
                const aName = sel ? sel.value : 'CompGeom';
                const inputs = {};
                document.querySelectorAll('#vspAnalysisInputsBody [data-analysis-inp]').forEach((inp) => {
                    const k = inp.getAttribute('data-analysis-inp');
                    const raw = inp.value.trim();
                    if (!raw) return;
                    try {
                        inputs[k] = JSON.parse(raw);
                    } catch (_) {
                        inputs[k] = raw;
                    }
                });
                executeAnalysis(aName, inputs);
            });
        }

        const resetAnaBtn = el('vspResetAnalysisDefaultsBtn');
        if (resetAnaBtn) {
            resetAnaBtn.addEventListener('click', () => {
                const sel = el('vspAnalysisSelect');
                if (sel) renderAnalysisInputsTable(sel.value);
            });
        }

        // Katalog funkcji i stałych
        ['vspFuncSearchInput', 'vspFuncCategorySelect'].forEach((id) => {
            const node = el(id);
            if (node) node.addEventListener('input', renderFunctionList);
        });

        const execFuncBtn = el('vspExecuteApiFuncBtn');
        if (execFuncBtn) execFuncBtn.addEventListener('click', executeSelectedApiFunction);

        const copyPyBtn = el('vspCopyPythonCallBtn');
        if (copyPyBtn) {
            copyPyBtn.addEventListener('click', () => {
                if (!state.selectedFunc) return;
                const args = collectRunnerArgs().map(a => JSON.stringify(a)).join(', ');
                const code = `import openvsp as vsp\nres = vsp.${state.selectedFunc.name}(${args})\nprint(res)`;
                if (navigator.clipboard) navigator.clipboard.writeText(code);
                copyPyBtn.textContent = 'Skopiowano kod Python!';
                setTimeout(() => { copyPyBtn.textContent = 'Kopiuj jako Python'; }, 1200);
            });
        }

        ['vspConstGroupSelect', 'vspConstSearchInput'].forEach((id) => {
            const node = el(id);
            if (node) node.addEventListener('input', renderConstantsRows);
        });

        // Zmienne projektowe i pomiary
        const addDvBtn = el('vspAddDesignVarBtn');
        if (addDvBtn) {
            addDvBtn.addEventListener('click', async () => {
                const sel = el('vspDvParmSelect');
                if (!sel || !sel.value) return;
                const res = await apiFetch('/api/openvsp/manage', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'add_design_var', parm_id: sel.value }),
                });
                state.model.design_vars = res.design_vars;
                renderSetsAndDesignVars();
            });
        }

        const clrDvBtn = el('vspClearDesignVarsBtn');
        if (clrDvBtn) {
            clrDvBtn.addEventListener('click', async () => {
                const res = await apiFetch('/api/openvsp/manage', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'del_all_design_vars' }),
                });
                state.model.design_vars = res.design_vars;
                renderSetsAndDesignVars();
            });
        }

        const addRulerBtn = el('vspAddRulerBtn');
        if (addRulerBtn) {
            addRulerBtn.addEventListener('click', async () => {
                const gid = state.selectedGeomId || ((state.model && state.model.geoms[0]) ? state.model.geoms[0].id : '');
                const name = el('vspRulerNameInput') ? el('vspRulerNameInput').value : 'Miarka_3D';
                const res = await apiFetch('/api/openvsp/manage', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'add_ruler', start_geom_id: gid, end_geom_id: gid, name: name }),
                });
                state.model.rulers = res.rulers;
                renderSetsAndDesignVars();
            });
        }

        const addProbeBtn = el('vspAddProbeBtn');
        if (addProbeBtn) {
            addProbeBtn.addEventListener('click', async () => {
                const gid = state.selectedGeomId || ((state.model && state.model.geoms[0]) ? state.model.geoms[0].id : '');
                const name = el('vspRulerNameInput') ? el('vspRulerNameInput').value : 'Sonda_3D';
                const res = await apiFetch('/api/openvsp/manage', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'add_probe', geom_id: gid, name: name }),
                });
                state.model.probes = res.probes;
                renderSetsAndDesignVars();
            });
        }

        const clrMeasBtn = el('vspClearMeasuresBtn');
        if (clrMeasBtn) {
            clrMeasBtn.addEventListener('click', async () => {
                await apiFetch('/api/openvsp/manage', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'del_all_rulers' }),
                });
                const res = await apiFetch('/api/openvsp/manage', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'del_all_probes' }),
                });
                state.model.rulers = res.rulers;
                state.model.probes = res.probes;
                renderSetsAndDesignVars();
            });
        }

        // Eksport plików CAD / CFD / FEA
        document.querySelectorAll('[data-vsp-export]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const fmt = btn.getAttribute('data-vsp-export');
                const baseName = el('vspExportBaseName') ? el('vspExportBaseName').value : 'bipol_samolot';
                const setVal = el('vspExportSetSelect') ? el('vspExportSetSelect').value : 'SET_ALL';
                btn.disabled = true;
                try {
                    const res = await apiFetch('/api/openvsp/export', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ format: fmt, filename: baseName, set_index: setVal }),
                    });
                    renderWorkspaceFiles(res.files || []);
                    if (res.download_url) {
                        const a = document.createElement('a');
                        a.href = res.download_url;
                        a.download = res.filename || '';
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                    }
                } catch (err) {
                    alert(`Błąd eksportu ${fmt}: ${err.message}`);
                } finally {
                    btn.disabled = false;
                }
            });
        });

        // Import pliku .vsp3 / .des / .stl
        const importBtn = el('vspUploadImportBtn');
        if (importBtn) {
            importBtn.addEventListener('click', async () => {
                const fileInp = el('vspImportFileInput');
                if (!fileInp || !fileInp.files || !fileInp.files[0]) {
                    alert('Wybierz plik .vsp3, .des, .xddm lub .stl z dysku.');
                    return;
                }
                const fd = new FormData();
                fd.append('file', fileInp.files[0]);
                const res = await apiFetch('/api/openvsp/import', { method: 'POST', body: fd });
                applyModelState(res);
            });
        }

        // Konsola skryptowa Python / vspscript
        const tplSelect = el('vspScriptTemplateSelect');
        const modeSelect = el('vspScriptModeSelect');
        const scriptEditor = el('vspScriptEditor');
        if (scriptEditor) {
            scriptEditor.value = SCRIPT_TEMPLATES.inspect_bipol;
        }
        if (tplSelect && scriptEditor) {
            tplSelect.addEventListener('change', () => {
                const key = tplSelect.value;
                scriptEditor.value = SCRIPT_TEMPLATES[key] || '';
                if (modeSelect) {
                    modeSelect.value = key === 'vspscript_demo' ? 'vspscript' : 'python';
                }
            });
        }

        const runScriptBtn = el('vspRunScriptBtn');
        if (runScriptBtn && scriptEditor) {
            runScriptBtn.addEventListener('click', async () => {
                const mode = modeSelect ? modeSelect.value : 'python';
                const outBox = el('vspScriptOutputBox');
                const metaBox = el('vspScriptStatusMeta');
                runScriptBtn.disabled = true;
                if (outBox) outBox.textContent = '⏳ Wykonywanie skryptu...';
                try {
                    const res = await apiFetch('/api/openvsp/script', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode: mode, code: scriptEditor.value }),
                    });
                    if (metaBox) metaBox.textContent = `Tryb: ${res.mode} · Czas: ${res.elapsed_ms} ms · Status: ${res.status}`;
                    const parts = [];
                    if (res.stdout) parts.push(`=== STDOUT ===\n${res.stdout}`);
                    if (res.result != null) parts.push(`=== RESULT ===\n${JSON.stringify(res.result, null, 2)}`);
                    if (res.stderr && res.stderr.trim()) parts.push(`=== STDERR ===\n${res.stderr}`);
                    if (outBox) outBox.textContent = parts.join('\n\n') || '(Skrypt zakończył się bez wyjścia tekstowego)';
                    if (res.model) applyModelState(res.model);
                } catch (err) {
                    if (outBox) outBox.textContent = `BŁĄD: ${err.message}`;
                } finally {
                    runScriptBtn.disabled = false;
                }
            });
        }
    }

    function initOpenVspStudio() {
        if (state.initialized) return;
        if (!el('tab-openvsp')) return;
        state.initialized = true;
        setupCanvasInteractions();
        bindEvents();
        if (document.querySelector('.tab-content.active')?.id === 'tab-openvsp') {
            loadCatalogAndInitialModel();
        }
        document.addEventListener('bipol:tab', () => {
            if (document.querySelector('.tab-content.active')?.id === 'tab-openvsp') {
                loadCatalogAndInitialModel();
            }
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        initOpenVspStudio();
    });

    window.OpenVSPStudio = {
        init: initOpenVspStudio,
        ensureLoaded: loadCatalogAndInitialModel,
        syncFromBipol: syncModelFromBipol,
        redraw3D: draw3dViewport,
    };
})();

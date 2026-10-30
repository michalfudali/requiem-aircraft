"""
Aplikacja Webowa BiPOL Requiem - Wstępne Projektowanie Samolotów
Wydział Mechaniczny Energetyki i Lotnictwa Politechniki Warszawskiej (MEiL PW)
Zakład Samolotów i Śmigłowców (ZSiS)
"""
import os
import json
import math
import sqlite3
from pathlib import Path
from flask import Flask, Response, render_template, request, jsonify, send_file, send_from_directory, abort
from werkzeug.exceptions import BadRequest
from calculations import run_bipol_project, refine_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.aircraft_store import export_source
from calculations.official_topics import ALL_TOPICS, OFFICIAL_CATEGORIES
from calculations.polish_law import catalog_for_frontend
from calculations.trends import reference_catalog, SOURCES, DATA, CLASSES, get_trend_suggestions
from calculations.aircraft_db import (
    create_aircraft, get_aircraft, update_aircraft, delete_aircraft,
    AircraftValidationError, AircraftNotFoundError, AircraftDuplicateError
)
from calculations.aircraft_db import validate_aircraft
from calculations.trends import derived
from calculations.trend_report import trend_chart
from calculations.report_assets import math_assets
from calculations.report_document import report_document, report_number, report_metadata, tex_number
from calculations.report_sketch import report_sketch
from calculations.drawing_sheet import drawing_sheet
from calculations import report_figures
from calculations.calc_sheet import build_sheet, worked_iteration
from calculations.report_docx import build_docx

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.jinja_env.globals['trend_chart'] = trend_chart
app.jinja_env.globals['math_assets'] = math_assets
app.jinja_env.filters['reportnum'] = report_number
app.jinja_env.filters['texnum'] = tex_number
app.jinja_env.filters['trendnum'] = lambda v, digits=3: f'{v:.{digits}f}' if isinstance(v, (int, float)) else '—'
app.jinja_env.globals['report_metadata'] = report_metadata
app.jinja_env.globals['report_sketch'] = report_sketch
app.jinja_env.globals['drawing_sheet'] = drawing_sheet
app.jinja_env.globals['figs'] = report_figures
app.jinja_env.globals['worked_iteration'] = worked_iteration
PROJECT_TITLES = {'const': 'Stałe fizyczne', 'p1': 'P1 · Projekt koncepcyjny', 'p2': 'P2 · Studium wykonalności',
                  'p3': 'P3 · Projekt wstępny i analiza masowa', 'p4': 'P4 · Charakterystyki aerodynamiczne',
                  'p5': 'P5 · Osiągi', 'p6': 'P6 · Obwiednia obciążeń'}


@app.get('/healthz')
def health():
    from calculations.aircraft_store import connect
    try:
        with connect() as con:
            con.execute('SELECT revision FROM catalog_state WHERE singleton = 1').fetchone()
        return jsonify(status='ok', application='BiPOL Requiem')
    except (sqlite3.Error, OSError, RuntimeError):
        return jsonify(status='unavailable'), 503


@app.context_processor
def designer_defaults():
    return {'designer_defaults': {f['key']: f['value'] for f in report_metadata({})}}


def report_parameters():
    if request.method == 'POST':
        return request.get_json(force=True)
    if request.args.get('params_json'):
        try:
            return json.loads(request.args['params_json'])
        except (TypeError, ValueError):
            raise ValueError('Nieprawidłowy JSON parametrów raportu.') from None
    preset_id = request.args.get('preset', 'pzl_kos')
    if preset_id not in AIRCRAFT_PRESETS:
        raise ValueError('Nieznany preset raportu.')
    return dict(AIRCRAFT_PRESETS[preset_id])


@app.errorhandler(ValueError)
@app.errorhandler(BadRequest)
def invalid_parameters(error):
    return jsonify(status='error', message=str(error)), 400

@app.route('/')
def index():
    return render_template(
        'index.html',
        presets=AIRCRAFT_PRESETS,
        categories=OFFICIAL_CATEGORIES,
        topics=ALL_TOPICS
    )

@app.route('/api/presets', methods=['GET'])
def get_presets():
    return jsonify(AIRCRAFT_PRESETS)

@app.route('/api/aircraft-classification', methods=['GET'])
def get_aircraft_classification():
    """Klasyfikacja statków powietrznych wg rozporządzenia MI (t.j. Dz. U. z 2025 r. poz. 1137), tabele nr 1-3."""
    return jsonify(catalog_for_frontend())

@app.route('/api/topics', methods=['GET'])
def get_topics():
    return jsonify({
        "categories": OFFICIAL_CATEGORIES,
        "topics": ALL_TOPICS
    })

@app.route('/api/constraints/suggestions', methods=['GET'])
def get_constraint_suggestions():
    category = request.args.get('category', 'cs23_level2')
    aircraft_type = request.args.get('aircraft_type', 'piston_ga')
    from calculations.constraints import get_initial_constraint_suggestions, WING_PLANFORMS, LOCKABLE_PARAMETERS
    return jsonify({
        'success': True,
        'suggestions': get_initial_constraint_suggestions(category, aircraft_type),
        'planforms': WING_PLANFORMS,
        'lockable_parameters': LOCKABLE_PARAMETERS
    })

@app.route('/api/aircraft', methods=['GET', 'POST'])
def aircraft_collection():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict):
            return jsonify(status='error', message='Invalid or malformed JSON payload'), 400
        try:
            record = create_aircraft(data)
            resp = dict(record)
            resp['status'] = 'ok'
            resp['message'] = 'Aircraft created'
            resp['aircraft'] = record
            resp['record'] = record
            return jsonify(resp), 201
        except AircraftDuplicateError as err:
            return jsonify(status='error', message=str(err)), 409
        except AircraftValidationError as err:
            return jsonify(status='error', message=str(err)), 400
    return jsonify(reference_catalog())


@app.post('/api/aircraft/preview')
def preview_aircraft():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('record'), dict):
        return jsonify(status='error', message='Podaj dane statku powietrznego.'), 400
    aircraft_id = data.get('id')
    if aircraft_id is not None and not isinstance(aircraft_id, str):
        return jsonify(status='error', message='Nieprawidłowy identyfikator samolotu.'), 400
    existing = get_aircraft(aircraft_id) if aircraft_id else None
    if aircraft_id and existing is None:
        return jsonify(status='error', message='Nie znaleziono samolotu.'), 404
    try:
        record = validate_aircraft({**(existing or {}), **data['record']},
                                    is_create=existing is None, existing=existing)
        return jsonify(status='ok', aircraft=derived(record))
    except AircraftValidationError as err:
        return jsonify(status='error', message=str(err)), 400


@app.route('/api/aircraft/<path:aircraft_id>', methods=['GET', 'PUT', 'DELETE'])
def aircraft_item(aircraft_id):
    if request.method == 'GET':
        record = get_aircraft(aircraft_id)
        if record is None:
            return jsonify(status='error', message=f"Aircraft '{aircraft_id}' not found"), 404
        resp = dict(record)
        resp['status'] = 'ok'
        resp['aircraft'] = record
        resp['record'] = record
        return jsonify(resp), 200

    elif request.method == 'PUT':
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict):
            return jsonify(status='error', message='Invalid or malformed JSON payload'), 400
        try:
            record = update_aircraft(aircraft_id, data)
            resp = dict(record)
            resp['status'] = 'ok'
            resp['message'] = 'Aircraft updated'
            resp['aircraft'] = record
            resp['record'] = record
            return jsonify(resp), 200
        except AircraftNotFoundError as err:
            return jsonify(status='error', message=str(err)), 404
        except AircraftValidationError as err:
            return jsonify(status='error', message=str(err)), 400

    elif request.method == 'DELETE':
        try:
            delete_aircraft(aircraft_id)
            return jsonify({
                'status': 'ok',
                'message': 'Aircraft deleted',
                'id': aircraft_id,
                'deleted_id': aircraft_id
            }), 200
        except AircraftNotFoundError as err:
            return jsonify(status='error', message=str(err)), 404



@app.route('/api/trends/suggestions', methods=['GET'])
def get_trends_suggestions():
    aircraft_type = request.args.get('aircraft_type')
    if not aircraft_type:
        return jsonify(status='error', message="Missing required parameter: 'aircraft_type'"), 400
    if aircraft_type not in CLASSES:
        return jsonify(status='error', message=f"Unknown aircraft_type: '{aircraft_type}'"), 400

    m0_param = request.args.get('m0')
    m0 = None
    if m0_param is not None and m0_param != '':
        try:
            m0 = float(m0_param)
            if not math.isfinite(m0) or m0 < 0:
                return jsonify(status='error', message="Parameter 'm0' must be a non-negative number"), 400
            if m0 == 0:
                m0 = None
        except (ValueError, TypeError):
            return jsonify(status='error', message="Invalid 'm0' parameter: must be a number"), 400

    wing_cfg = request.args.get('wing_configuration', request.args.get('wing_config'))
    engine_type = request.args.get('engine_type') or None
    if engine_type not in (None, 'prop', 'jet', 'none'):
        return jsonify(status='error', message=f"Unknown engine_type: '{engine_type}'"), 400
    res = get_trend_suggestions(aircraft_type, m0=m0, wing_configuration=wing_cfg, engine_type=engine_type)
    return jsonify(res)


@app.post('/api/trends/import')
def import_trend_observations():
    from calculations.trend_observations import import_observations
    try:
        if request.content_length and request.content_length > 1_100_000:
            raise ValueError('Plik uzupełnień może mieć maksymalnie 1 MB.')
        upload = request.files.get('file')
        if not upload:
            raise ValueError('Wybierz plik CSV wyeksportowany z arkusza.')
        text = upload.read(1_000_001).decode('utf-8-sig')
        if not text.strip():
            raise ValueError('Plik CSV jest pusty.')
        return jsonify(observations=import_observations(text))
    except (ValueError, UnicodeError) as error:
        return jsonify(error=str(error)), 400


@app.route('/download/aircraft/<source>/<kind>')
def aircraft_source_download(source, kind):
    if source not in SOURCES or kind not in ('data', 'license'):
        abort(404)
    if kind == 'license':
        return send_from_directory(DATA / 'licenses', SOURCES[source]['license_file'], as_attachment=True)
    # Exported from the database; ODbL requires the CADO-derived records to stay downloadable.
    body = json.dumps(export_source(source), ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    return Response(body, mimetype='application/json',
                    headers={'Content-Disposition': f'attachment; filename={source}.json'})

# Course materials are not redistributed: the app links to the source pages
# and lists only the user's own local copies (git-ignored scraped_materials/).
app.config['MATERIALS_DIR'] = os.path.join(app.root_path, 'scraped_materials')
MATERIAL_FOLDERS = ('danilecki', 'bipol', 'mechanika_lotu', 'zpk_cad')
MATERIAL_SOURCES = [
    {"name": "BIPOL I — strona przedmiotu (ZSiS)",
     "url": "https://www.meil.pw.edu.pl/zsis/ZSiS/Dydaktyka/Prowadzone-przedmioty/BIPOL/BIPOL-I",
     "note": "Pliki chronione hasłem podawanym na zajęciach."},
    {"name": "Mechanika Lotu I — materiały do pobrania (ZM)",
     "url": "https://www.meil.pw.edu.pl/zm/ZM/Dydaktyka/Prowadzone-przedmioty/Mechanika-Lotu-I/Materialy-do-pobrania",
     "note": "Wymaga zalogowania danymi od prowadzącego."},
    {"name": "Zapis Konstrukcji CAD I — materiały dla studentów (ZPK)",
     "url": "https://www.meil.pw.edu.pl/zpk/ZPK/Dydaktyka/Materialy-dla-studentow-Files-for-students/Zapis-Konstrukcji-CAD1",
     "note": "Normy rysunku technicznego i formatki A3/A4."},
    {"name": "J. Danilecki — Konstruowanie samolotów (Dolnośląska Biblioteka Cyfrowa)",
     "url": "https://www.dbc.wroc.pl/Content/1004/Danilecki_Konstruowanie.pdf",
     "note": "Wydanie cyfrowe udostępnione przez DBC."},
    {"name": "C. Galiński — Wybrane zagadnienia projektowania samolotów (Łukasiewicz – ILOT)",
     "url": "https://ilot.lukasiewicz.gov.pl/wp-content/uploads/sites/47/2026/09/Cezary_Galinski_Wybrane_zagadnienia_projektowania_samolotow.pdf",
     "note": "Odnośnik ze strony przedmiotu BIPOL I."},
    {"name": "NASA Technical Reports Server — raport 19930094469",
     "url": "https://ntrs.nasa.gov/citations/19930094469",
     "note": "Raport NACA/NASA udostępniony publicznie w NTRS."},
]


@app.route('/api/scraped-files', methods=['GET'])
def list_scraped_files():
    def scan_dir(folder_key):
        d = os.path.join(app.config['MATERIALS_DIR'], folder_key)
        if not os.path.isdir(d):
            return []
        return [{"name": f,
                 "path": f"/download/scraped/{folder_key}/{f}",
                 "size": os.path.getsize(os.path.join(d, f))}
                for f in sorted(os.listdir(d)) if f.lower().endswith('.pdf')]

    files = {key: scan_dir(key) for key in MATERIAL_FOLDERS}
    return jsonify({**files,
                    "sources": MATERIAL_SOURCES,
                    "total_count": sum(len(items) for items in files.values())})

@app.route('/download/scraped/<folder>/<path:filename>')
def download_scraped(folder, filename):
    if folder not in MATERIAL_FOLDERS:
        abort(404)
    directory = os.path.join(app.config['MATERIALS_DIR'], folder)
    return send_from_directory(directory, filename, as_attachment=False)

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.get_json(force=True)
    return jsonify(run_bipol_project(data))


@app.route('/api/airfoil/200mm', methods=['GET'])
def get_airfoil_200mm():
    """Generuje rzędne profilu skrzydła przeskalowanego do cięciwy c = 200 mm oraz wektorowy rysunek SVG."""
    from calculations.airfoils import generate_airfoil_200mm, generate_airfoil_svg
    airfoil_name = (request.args.get('airfoil') or 'NACA 23012').strip()
    try:
        tc = float(request.args.get('tc', 0.12))
        tc = max(0.05, min(0.35, tc))
    except (ValueError, TypeError):
        tc = 0.12
    coords, note = generate_airfoil_200mm(airfoil_name, tc_ratio=tc)
    svg = generate_airfoil_svg(coords)
    return jsonify({
        'status': 'ok',
        'airfoil': airfoil_name,
        'tc': tc,
        'table': coords,
        'svg': svg,
        'note': note
    })


@app.post('/api/coursework/grade')
def coursework_grade():
    from calculations.coursework import grade_plan
    return jsonify(grade_plan(request.get_json(force=True)))


@app.post('/api/coursework/iterate-polar')
def coursework_iterate_polar():
    """Refined sizing P2←P4 to convergence; no project or catalogue is modified here."""
    baseline, result, steps = refine_bipol_project(request.get_json(force=True))
    return jsonify(result=result, before=baseline['submission_review']['polar'],
                   after=result['submission_review']['polar'], iterations=steps,
                   mtow_before=baseline['mass']['m0'], mtow_after=result['mass']['m0'])

@app.route('/report', methods=['GET', 'POST'])
def report():
    allowed_sections = ('p1', 'p2', 'p3', 'p4', 'p5', 'p6')
    requested = request.args.get('sections')
    selected_sections = list(allowed_sections) if requested is None else list(dict.fromkeys(requested.split(',')))
    if not selected_sections or any(section not in allowed_sections for section in selected_sections):
        raise ValueError('Wybierz poprawny zakres raportu: P1–P6.')
    params = report_parameters()
    results = run_bipol_project(params)
    return render_template('report.html', **document_context(results, selected_sections))


def document_context(results, sections, folder_cover=False):
    assets = {
        'css': 'static/css/report.css',
        'symbols': 'static/js/symbols.js',
        'core': 'static/js/studio-core.js',
        'visuals': 'static/js/studio-visuals.js',
        'document': 'static/js/report.js',
        'editor': 'static/js/report-editor.js',
    }
    return dict(res=results, params=results['params'], selected_sections=sections,
                sheet=build_sheet(results),
                doc=report_document(results, sections, request.args, folder_cover),
                figure_results={key: results[key] for key in
                                ('sizing', 'aerodynamics', 'envelope', 'geometry', 'performance', 'bipol_projects')},
                report_assets={name: (Path(app.root_path) / path).read_text(encoding='utf-8')
                               .replace('</script', '<\\/script') for name, path in assets.items()})

@app.post('/report/docx')
def report_docx():
    """Edytowalny DOCX z dokumentu w oknie podglądu, razem z poprawkami autora."""
    if (request.content_length or 0) > 80 * 1024 * 1024:
        raise ValueError('Raport jest zbyt duży do eksportu DOCX (limit 80 MB).')
    payload = request.get_json(silent=True)
    html = payload.get('html') if isinstance(payload, dict) else None
    if not isinstance(html, str) or not html.strip():
        raise ValueError('Brak treści raportu do eksportu DOCX.')
    data = build_docx(html, title=str(payload.get('title') or '')[:300],
                      author=str(payload.get('author') or '')[:160])
    return Response(data, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    headers={'Content-Disposition': 'attachment; filename="raport.docx"'})


@app.post('/api/report/catalog')
def report_catalog():
    """Wielkości i procedury dostępne w raporcie parametrów dla bieżącego projektu."""
    sheet = build_sheet(run_bipol_project(report_parameters()))
    catalog = sheet.catalog()
    return jsonify(status='ok', projects=PROJECT_TITLES, **catalog)


@app.route('/report/parameters', methods=['GET', 'POST'])
def parameter_report():
    """Raport wybranych parametrów: wzory, podstawienia i (opcjonalnie) cały tok obliczeń."""
    keys = [k for k in dict.fromkeys((request.args.get('keys') or '').split(',')) if k]
    if not keys or len(keys) > 400:
        raise ValueError('Wybierz od 1 do 400 parametrów raportu.')
    chain = request.args.get('chain', '1') != '0'
    full_iterations = request.args.get('iterations', 'all') != 'first'
    results = run_bipol_project(report_parameters())
    context = document_context(results, [])
    sheet = context['sheet']
    unknown = [k for k in keys if (k[1:] not in sheet.blocks if k.startswith('@') else k not in sheet.entries)]
    if unknown:
        raise ValueError('Nieznane parametry raportu: ' + ', '.join(unknown[:5]) + '.')
    ordered, blocks = sheet.chain(keys, follow=chain)
    if not chain:
        ordered = [k for k in sheet.order if k in keys]
        blocks = [k[1:] for k in keys if k.startswith('@')]
    selected = [sheet.entries[k] for k in keys if not k.startswith('@')]
    # Sekcje w kolejności części projektu (stałe, P1…P6); bloki przed sekcją, która z nich korzysta.
    members = {}
    for key in ordered:
        members.setdefault(sheet.entries[key]['section'], []).append(key)
    sections = [s for s in sheet.sections if s in members]
    placed, plan = set(), []
    for section in sections:
        for block in blocks:
            if block not in placed and any('@' + block in sheet.entries[k]['deps'] for k in members[section]):
                plan.append(('block', block))
                placed.add(block)
        plan.append(('section', section))
    plan += [('block', b) for b in blocks if b not in placed]
    return render_template('parameter_report.html', **context, plan=plan, members=members, chain=chain,
                           selected=selected, selected_blocks=[sheet.blocks[b] for b in blocks if '@' + b in keys],
                           full_iterations=full_iterations, project_titles=PROJECT_TITLES)


@app.route('/holistic')
def holistic_portal():
    return render_template(
        'index.html',
        presets=AIRCRAFT_PRESETS,
        categories=OFFICIAL_CATEGORIES,
        topics=ALL_TOPICS,
        initial_portal_mode='holistic'
    )

@app.route('/projekty')
def projects_portal():
    return render_template(
        'index.html',
        presets=AIRCRAFT_PRESETS,
        categories=OFFICIAL_CATEGORIES,
        topics=ALL_TOPICS,
        initial_portal_mode='projects'
    )

@app.route('/report/project/<p_id>', methods=['GET', 'POST'])
def project_report(p_id):
    if p_id not in ('p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'folder_cover'):
        abort(404)
    results = run_bipol_project(report_parameters())
    sections = [] if p_id == 'folder_cover' else [p_id]
    return render_template('project_report.html',
                           **document_context(results, sections, p_id == 'folder_cover'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Local only by default: the Werkzeug debugger allows code execution.
    host = os.environ.get('HOST', '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG') == '1'
    print(f"Startowanie serwera BiPOL Requiem: http://{host}:{port} (debug={'tak' if debug else 'nie'})...")
    app.run(host=host, port=port, debug=debug)

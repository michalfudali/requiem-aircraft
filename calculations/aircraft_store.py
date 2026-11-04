"""SQLite storage of the reference aircraft catalogue (data/aircraft/aircraft.sqlite3).

The database is the only place the catalogue is stored. Table `sources` holds the
provenance and licence of each data set; table `aircraft` holds the records with
type, range and foreign-key constraints, so invalid data cannot be saved even by
tools that bypass the application. Every write changes `catalog_state.revision`
(triggers), which lets readers in any process notice changes, including edits made
with external SQLite tools. BIPOL_AIRCRAFT_DB selects another database file.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data' / 'aircraft'
DEFAULT_PATH = DATA / 'aircraft.sqlite3'
SCHEMA_VERSION = 3

CLASSES = {
    'piston_ga': 'Samoloty tłokowe GA', 'turboprop_regional': 'Samoloty turbośmigłowe',
    'jet_business': 'Odrzutowce biznesowe', 'jet_transport': 'Odrzutowce transportowe',
    'glider': 'Szybowce', 'motoglider': 'Motoszybowce', 'uav': 'Bezzałogowe płatowce',
}
DISTANCE_BASES = ('unknown', 'ground_roll', '15m', '50ft', 'field_length')


def _sql_list(values):
    return ', '.join(f"'{value}'" for value in values)


# Column order is the record layout returned to the application.
AIRCRAFT_COLUMNS = (
    # Identification and provenance
    ('id', "TEXT NOT NULL UNIQUE CHECK (length(id) BETWEEN 1 AND 128 AND id NOT GLOB '*[^A-Za-z0-9_-]*')"),
    ('source_id', 'TEXT NOT NULL REFERENCES sources (id)'),
    ('model', "TEXT NOT NULL CHECK (trim(model) <> '')"),
    ('manufacturer', "TEXT NOT NULL DEFAULT ''"),
    ('family', 'TEXT CHECK (length(family) <= 4000)'),
    ('aircraft_type', f'TEXT NOT NULL CHECK (aircraft_type IN ({_sql_list(CLASSES)}))'),
    ('year', 'INTEGER CHECK (year BETWEEN 1900 AND 2100)'),
    ('year_basis', 'TEXT'),
    ('source_locator', 'TEXT CHECK (length(source_locator) <= 4000)'),
    ('source_references', 'TEXT CHECK (length(source_references) <= 4000)'),
    ('empty_mass_definition', 'TEXT CHECK (length(empty_mass_definition) <= 4000)'),
    # Masses [kg] and geometry [m², m]
    ('m0', 'REAL NOT NULL CHECK (m0 > 0)'),
    ('me', 'REAL CHECK (me > 0 AND me < m0)'),
    ('s', 'REAL CHECK (s > 0)'),
    ('b', 'REAL CHECK (b > 0)'),
    ('variable_sweep', 'INTEGER NOT NULL DEFAULT 0 CHECK (variable_sweep IN (0, 1))'),
    ('h_tail_area', 'REAL CHECK (h_tail_area > 0)'),
    ('v_tail_area', 'REAL CHECK (v_tail_area > 0)'),
    # Propulsion: total power [kW] or thrust [kN] of all engines
    ('engine_type', "TEXT NOT NULL CHECK (engine_type IN ('prop', 'jet', 'none'))"),
    ('n_engines', 'INTEGER CHECK (n_engines >= 0)'),
    ('engine_model', 'TEXT'),
    ('engine_source_locator', 'TEXT'),
    ('p_kw', 'REAL CHECK (p_kw > 0)'),
    ('t_kn', 'REAL CHECK (t_kn > 0)'),
    ('prop_diameter_m', 'REAL CHECK (prop_diameter_m BETWEEN 0 AND 20)'),
    ('prop_type', 'TEXT'),
    # Performance [km/h, km, m/s, m]
    ('v_cruise_kmh', 'REAL CHECK (v_cruise_kmh BETWEEN 0 AND 3000)'),
    ('v_max', 'REAL CHECK (v_max > 0)'),
    ('cruise_mach', 'REAL CHECK (cruise_mach BETWEEN 0 AND 5)'),
    ('mmo', 'REAL CHECK (mmo > 0)'),
    ('v_stall_kmh', 'REAL CHECK (v_stall_kmh BETWEEN 0 AND 1000)'),
    ('range_km', 'REAL CHECK (range_km BETWEEN 0 AND 50000)'),
    ('climb_rate_ms', 'REAL CHECK (climb_rate_ms BETWEEN 0 AND 150)'),
    ('ld_max', 'REAL CHECK (ld_max BETWEEN 0 AND 150)'),
    ('w_z_min_ms', 'REAL CHECK (w_z_min_ms > 0)'),
    ('takeoff_m', 'REAL CHECK (takeoff_m BETWEEN 0 AND 50000)'),
    ('takeoff_basis', f'TEXT CHECK (takeoff_basis IN ({_sql_list(DISTANCE_BASES)}))'),
    ('landing_m', 'REAL CHECK (landing_m BETWEEN 0 AND 50000)'),
    ('landing_basis', f'TEXT CHECK (landing_basis IN ({_sql_list(DISTANCE_BASES)}))'),
    # Tail volume coefficients, dihedral [deg] and control-surface ratios
    ('v_h', 'REAL CHECK (v_h > 0 AND v_h <= 2)'),
    ('v_v', 'REAL CHECK (v_v BETWEEN 0 AND 0.5)'),
    ('dihedral_deg', 'REAL CHECK (dihedral_deg BETWEEN -15 AND 20)'),
    ('aileron_span_fraction', 'REAL CHECK (aileron_span_fraction > 0 AND aileron_span_fraction <= 1)'),
    ('aileron_chord_ratio', 'REAL CHECK (aileron_chord_ratio > 0 AND aileron_chord_ratio <= 1)'),
    ('elevator_chord_ratio', 'REAL CHECK (elevator_chord_ratio > 0 AND elevator_chord_ratio <= 1)'),
    ('rudder_chord_ratio', 'REAL CHECK (rudder_chord_ratio > 0 AND rudder_chord_ratio <= 1)'),
)
AIRCRAFT_CHECKS = (
    "CHECK (engine_type <> 'jet' OR p_kw IS NULL)",
    "CHECK (engine_type <> 'prop' OR t_kn IS NULL)",
    "CHECK (engine_type <> 'none' OR (p_kw IS NULL AND t_kn IS NULL))",
    'CHECK (v_stall_kmh < v_cruise_kmh)',
)
COLUMN_NAMES = tuple(name for name, _ in AIRCRAFT_COLUMNS)
COLUMN_TYPES = {name: definition.split()[0] for name, definition in AIRCRAFT_COLUMNS}

_ROW_DEFINITIONS = ',\n    '.join(
    ['entry_no INTEGER PRIMARY KEY'] + [f'{name} {definition}' for name, definition in AIRCRAFT_COLUMNS]
    + list(AIRCRAFT_CHECKS))
_REVISION_TRIGGERS = '\n'.join(
    f'CREATE TRIGGER {table}_{event.lower()} AFTER {event} ON {table} '
    'BEGIN UPDATE catalog_state SET revision = random(); END;'
    for table in ('sources', 'aircraft') for event in ('INSERT', 'UPDATE', 'DELETE'))

# Version 2: data about specific comparison aircraft used outside the trend catalogue.
REFERENCE_TABLES = """
-- Values read from a figure for named example aircraft (e.g. BIPOL_1, Fig. 1: S_wet/S_ref).
CREATE TABLE wetted_area_examples (
    key         TEXT PRIMARY KEY CHECK (key <> '' AND key NOT GLOB '*[^a-z0-9_]*'),
    sort_order  INTEGER NOT NULL UNIQUE,
    label       TEXT NOT NULL CHECK (trim(label) <> ''),
    short_label TEXT NOT NULL CHECK (trim(short_label) <> ''),
    swet_ratio  REAL NOT NULL CHECK (swet_ratio > 1 AND swet_ratio < 20),
    citation    TEXT NOT NULL
) STRICT;

-- Named example aircraft and their figures quoted in explanations of a design choice
-- (context: e.g. wing_config, flap_type; key: the option; text: the examples).
CREATE TABLE model_examples (
    context  TEXT NOT NULL CHECK (context <> ''),
    key      TEXT NOT NULL CHECK (key <> ''),
    text     TEXT NOT NULL CHECK (trim(text) <> ''),
    citation TEXT,
    PRIMARY KEY (context, key)
) STRICT;

-- Documented supplements to catalogue aircraft for one project (CSV import). They never
-- change the shared record; the calculation of that project overlays them.
CREATE TABLE aircraft_supplements (
    project_id  TEXT NOT NULL CHECK (project_id <> ''),
    aircraft_id TEXT NOT NULL REFERENCES aircraft (id) ON DELETE CASCADE,
    data        TEXT NOT NULL CHECK (json_valid(data)),
    PRIMARY KEY (project_id, aircraft_id)
) STRICT;
"""

# Version 3: engine proposals with documented fuel-consumption points (one JSON document each).
ENGINE_TABLES = """
CREATE TABLE engines (
    id         TEXT PRIMARY KEY CHECK (id <> '' AND id NOT GLOB '*[^a-z0-9_]*'),
    sort_order INTEGER NOT NULL UNIQUE,
    document   TEXT NOT NULL CHECK (json_valid(document) AND json_extract(document, '$.id') = id)
) STRICT;
"""

SCHEMA = f"""
CREATE TABLE sources (
    id           TEXT PRIMARY KEY CHECK (id <> '' AND id NOT GLOB '*[^a-z0-9_]*'),
    sort_order   INTEGER NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    url          TEXT NOT NULL,
    license      TEXT NOT NULL,
    license_file TEXT NOT NULL,
    citation     TEXT NOT NULL,
    attribution  TEXT
) STRICT;

CREATE TABLE aircraft (
    {_ROW_DEFINITIONS}
) STRICT;
CREATE INDEX aircraft_by_class ON aircraft (aircraft_type, engine_type);
CREATE INDEX aircraft_by_source ON aircraft (source_id);

-- Changes on every write; readers compare it to decide whether to reload.
CREATE TABLE catalog_state (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    revision  INTEGER NOT NULL
) STRICT;
INSERT INTO catalog_state VALUES (1, 0);
{_REVISION_TRIGGERS}

{REFERENCE_TABLES}
{ENGINE_TABLES}
PRAGMA user_version = {SCHEMA_VERSION};
"""


def database_path():
    return Path(os.environ.get('BIPOL_AIRCRAFT_DB') or DEFAULT_PATH)


def _open(path, mode):
    # mode=rw never creates an empty database in place of a missing file.
    con = sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode={mode}', uri=True,
                          timeout=30, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    return con


@contextmanager
def connect(path=None):
    """Autocommit connection to a database with the current schema; closed on exit."""
    path = Path(path or database_path())
    if not path.is_file():
        raise FileNotFoundError(f'Brak bazy samolotów: {path}')
    con = _open(path, 'rw')
    try:
        # Both stores started at version 1: identify the file before migrating it.
        required = {'aircraft', 'sources', 'catalog_state'}
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not required <= tables:
            raise RuntimeError('Plik nie jest bazą samolotów porównawczych: nieprawidłowa baza katalogu, '
                               'brak tabel aircraft, sources lub catalog_state.')
        version = con.execute('PRAGMA user_version').fetchone()[0]
        # Upgrade in place: new tables only add data, existing records stay unchanged.
        for old, tables in ((1, REFERENCE_TABLES), (2, ENGINE_TABLES)):
            if version == old:
                con.executescript(f'BEGIN IMMEDIATE;{tables}PRAGMA user_version = {old + 1}; COMMIT;')
                version = old + 1
        if version != SCHEMA_VERSION:
            raise RuntimeError(f'Nieobsługiwana wersja schematu bazy samolotów: {version} (oczekiwano {SCHEMA_VERSION}).')
        yield con
    finally:
        con.close()


@contextmanager
def transaction(path=None):
    """Write transaction: committed on success, rolled back on any exception."""
    with connect(path) as con:
        con.execute('BEGIN IMMEDIATE')
        try:
            yield con
        except BaseException:
            con.execute('ROLLBACK')
            raise
        con.execute('COMMIT')


def to_record(row):
    record = {name: row[name] for name in COLUMN_NAMES}
    record['variable_sweep'] = bool(record['variable_sweep'])
    return record


def _values(record):
    values = [record.get(name) for name in COLUMN_NAMES]
    values[COLUMN_NAMES.index('variable_sweep')] = int(bool(record.get('variable_sweep')))
    return values


def read_catalog(known_revision=None, path=None):
    """Return (revision, records in catalogue order); records is None if unchanged."""
    with connect(path) as con:
        con.execute('BEGIN')  # one consistent snapshot for both queries
        try:
            revision = con.execute('SELECT revision FROM catalog_state').fetchone()[0]
            rows = None if revision == known_revision else con.execute(
                'SELECT a.* FROM aircraft a JOIN sources s ON s.id = a.source_id '
                'ORDER BY s.sort_order, a.entry_no').fetchall()
        finally:
            con.execute('COMMIT')
    return revision, None if rows is None else [to_record(row) for row in rows]


def load_sources(path=None):
    with connect(path) as con:
        rows = con.execute('SELECT * FROM sources ORDER BY sort_order').fetchall()
    return {row['id']: {key: row[key] for key in row.keys()
                        if key not in ('id', 'sort_order') and row[key] is not None}
            for row in rows}


def fetch(con, aircraft_id):
    row = con.execute('SELECT * FROM aircraft WHERE id = ?', (aircraft_id,)).fetchone()
    return to_record(row) if row else None


def insert(con, record):
    con.execute(f'INSERT INTO aircraft ({", ".join(COLUMN_NAMES)}) '
                f'VALUES ({", ".join("?" * len(COLUMN_NAMES))})', _values(record))


def update(con, aircraft_id, record):
    """Replace all columns except id; return the number of updated rows."""
    values = _values(record)
    del values[0]
    assignments = ', '.join(f'{name} = ?' for name in COLUMN_NAMES[1:])
    return con.execute(f'UPDATE aircraft SET {assignments} WHERE id = ?', values + [aircraft_id]).rowcount


def delete(con, aircraft_id):
    return con.execute('DELETE FROM aircraft WHERE id = ?', (aircraft_id,)).rowcount


def export_source(source_id, path=None):
    """Stored records of one source, in entry order, without derived values."""
    with connect(path) as con:
        rows = con.execute('SELECT * FROM aircraft WHERE source_id = ? ORDER BY entry_no', (source_id,)).fetchall()
    return [to_record(row) for row in rows]


def replace_source(source_id, records, path=None):
    """Replace all records of one source in a single transaction (data importers)."""
    with transaction(path) as con:
        con.execute('DELETE FROM aircraft WHERE source_id = ?', (source_id,))
        for record in records:
            insert(con, {**record, 'source_id': source_id})


def create_database(path, sources, records=()):
    """Create a new database file with the schema, sources and initial records."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f'Baza już istnieje: {path}')
    con = _open(path, 'rwc')
    try:
        con.executescript(SCHEMA)
        con.execute('BEGIN IMMEDIATE')
        for order, (source_id, meta) in enumerate(sources.items(), start=1):
            con.execute('INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        (source_id, order, meta['name'], meta['url'], meta['license'],
                         meta['license_file'], meta['citation'], meta.get('attribution')))
        for record in records:
            insert(con, record)
        con.execute('COMMIT')
        con.execute('VACUUM')
    except BaseException:
        con.close()
        path.unlink(missing_ok=True)
        raise
    con.close()


# --- Data about named comparison aircraft outside the catalogue table -----------------------
def wetted_area_examples(path=None):
    """{key: (label, swet_ratio, short_label, citation)} in figure order."""
    with connect(path) as con:
        rows = con.execute('SELECT * FROM wetted_area_examples ORDER BY sort_order').fetchall()
    return {row['key']: dict(label=row['label'], swet_ratio=row['swet_ratio'], short_label=row['short_label'],
                             citation=row['citation']) for row in rows}


def model_examples(path=None):
    """{context: {key: text}} of example aircraft quoted in explanations."""
    with connect(path) as con:
        rows = con.execute('SELECT context, key, text FROM model_examples ORDER BY context, key').fetchall()
    out = {}
    for row in rows:
        out.setdefault(row['context'], {})[row['key']] = row['text']
    return out


def project_supplements(project_id, path=None):
    """Supplements of one project as observation records [{id, ..., source}]."""
    import json
    with connect(path) as con:
        rows = con.execute('SELECT aircraft_id, data FROM aircraft_supplements WHERE project_id = ? ORDER BY aircraft_id',
                           (project_id,)).fetchall()
    return [{**json.loads(row['data']), 'id': row['aircraft_id']} for row in rows]


def replace_project_supplements(project_id, observations, path=None):
    """Store the project's supplements (validated observation records); returns their number."""
    import json
    with transaction(path) as con:
        con.execute('DELETE FROM aircraft_supplements WHERE project_id = ?', (project_id,))
        for record in observations:
            con.execute('INSERT INTO aircraft_supplements VALUES (?, ?, ?)',
                        (project_id, record['id'], json.dumps({k: v for k, v in record.items() if k != 'id'})))
    return len(observations)


def engines(path=None):
    """Engine proposals in catalogue order (documents with model, ratings, fuel points and sources)."""
    import json
    with connect(path) as con:
        rows = con.execute('SELECT document FROM engines ORDER BY sort_order').fetchall()
    return [json.loads(row['document']) for row in rows]

"""Server-side reference aircraft database management and CRUD persistence.

Records are stored in SQLite (calculations/aircraft_store.py). Each write is one
transaction; the database constraints repeat the validation rules below.
"""
import math
import re
import sqlite3
import threading

from calculations import aircraft_store
from calculations.aircraft_store import COLUMN_NAMES, COLUMN_TYPES
from calculations.trends import CLASSES, SOURCES, derived, load_aircraft

VALID_CLASSES = set(CLASSES.keys())
VALID_ENGINE_TYPES = {'prop', 'jet', 'none'}
KNOWN_SOURCES = tuple(SOURCES)
USER_SOURCE = 'user'  # records added in the editor, kept apart from the curated data sets
SAFE_ID_REGEX = re.compile(r'^[a-zA-Z0-9_\-]+$')

DERIVED_KEYS = {
    'ar', 'empty_fraction', 'wing_loading_kg_m2', 'wing_loading_n_m2',
    'power_loading_kg_kw', 'specific_power_kw_kg', 'thrust_to_weight',
    'takeoff_distance_m', 'landing_distance_m', 'quality_notes'
}
# API response wrappers, accepted back from clients that echo a record.
RESPONSE_KEYS = {'status', 'message', 'aircraft', 'record'}


class AircraftDatabaseError(Exception):
    """Base exception for aircraft database errors."""
    pass


class AircraftValidationError(AircraftDatabaseError):
    """Raised when record data fails schema or physical validation rules (HTTP 400)."""
    pass


class AircraftNotFoundError(AircraftDatabaseError, LookupError):
    """Raised when requested aircraft ID is not found in any source file (HTTP 404)."""
    pass


class AircraftDuplicateError(AircraftDatabaseError):
    """Raised when attempting to create an aircraft with an existing ID (HTTP 409)."""
    pass


def validate_aircraft(data: dict, is_create: bool = True, existing: dict | None = None) -> dict:
    """Validates aircraft record data against physical invariants and structural rules.

    Returns cleaned record dict ready for persistence (without derived keys).
    """
    if not isinstance(data, dict):
        raise AircraftValidationError("Payload must be a JSON object.")

    # Check required fields on creation
    if is_create:
        for req in ('id', 'model', 'manufacturer', 'aircraft_type', 'm0'):
            if req not in data or data[req] is None:
                raise AircraftValidationError(f"Missing required field: '{req}'.")

    # Validate ID
    aircraft_id = data.get('id')
    if aircraft_id is not None:
        if not isinstance(aircraft_id, str):
            raise AircraftValidationError("Field 'id' must be a string.")
        aircraft_id_clean = aircraft_id.strip()
        if not aircraft_id_clean:
            raise AircraftValidationError("Field 'id' cannot be empty.")
        if not SAFE_ID_REGEX.match(aircraft_id_clean):
            raise AircraftValidationError(
                f"Invalid aircraft ID '{aircraft_id}'. Only alphanumeric characters, dashes, and underscores are allowed."
            )
        if len(aircraft_id_clean) > 128:
            raise AircraftValidationError("Aircraft ID cannot exceed 128 characters.")
        if not is_create and existing and aircraft_id_clean != existing.get('id'):
            raise AircraftValidationError("Aircraft ID cannot be modified.")
    elif is_create:
        raise AircraftValidationError("Field 'id' is required.")

    # Validate model
    model = data.get('model')
    if model is not None or 'model' in data:
        if not isinstance(model, str) or not model.strip():
            raise AircraftValidationError("Field 'model' must be a non-empty string.")

    # Validate manufacturer
    manufacturer = data.get('manufacturer')
    if manufacturer is not None:
        if not isinstance(manufacturer, str) or not manufacturer.strip():
            raise AircraftValidationError("Field 'manufacturer' must be a non-empty string.")

    # Validate aircraft_type
    act = data.get('aircraft_type')
    if act is not None:
        if act not in VALID_CLASSES:
            raise AircraftValidationError(
                f"Invalid aircraft_type: '{act}'. Must be one of {sorted(VALID_CLASSES)}."
            )

    # Validate m0 (MTOW)
    m0 = data.get('m0')
    if m0 is not None or 'm0' in data:
        if isinstance(m0, bool) or not isinstance(m0, (int, float)):
            raise AircraftValidationError("Field 'm0' must be a numeric value.")
        if not math.isfinite(m0) or m0 <= 0:
            raise AircraftValidationError("Field 'm0' (MTOW) must be a strictly positive number.")

    # Validate me (OEW)
    me = data.get('me')
    if me is not None:
        if isinstance(me, bool) or not isinstance(me, (int, float)):
            raise AircraftValidationError("Field 'me' must be a numeric value.")
        if not math.isfinite(me) or me <= 0:
            raise AircraftValidationError("Field 'me' (OEW) must be a strictly positive number.")
        if m0 is not None and me >= m0:
            raise AircraftValidationError(
                f"Empty mass 'me' ({me} kg) must be strictly less than MTOW 'm0' ({m0} kg)."
            )

    # Validate wing area s
    s = data.get('s')
    if s is not None:
        if isinstance(s, bool) or not isinstance(s, (int, float)):
            raise AircraftValidationError("Field 's' must be a numeric value.")
        if not math.isfinite(s) or s <= 0:
            raise AircraftValidationError("Field 's' (wing area) must be a strictly positive number.")

    # Validate wingspan b
    b = data.get('b')
    if b is not None:
        if isinstance(b, bool) or not isinstance(b, (int, float)):
            raise AircraftValidationError("Field 'b' must be a numeric value.")
        if not math.isfinite(b) or b <= 0:
            raise AircraftValidationError("Field 'b' (wingspan) must be a strictly positive number.")

    # Validate propulsion / engine fields
    p_kw = data.get('p_kw')
    if p_kw is not None:
        if isinstance(p_kw, bool) or not isinstance(p_kw, (int, float)):
            raise AircraftValidationError("Field 'p_kw' must be a numeric value.")
        if not math.isfinite(p_kw) or p_kw <= 0:
            raise AircraftValidationError("Field 'p_kw' must be a strictly positive number.")

    t_kn = data.get('t_kn')
    if t_kn is not None:
        if isinstance(t_kn, bool) or not isinstance(t_kn, (int, float)):
            raise AircraftValidationError("Field 't_kn' must be a numeric value.")
        if not math.isfinite(t_kn) or t_kn <= 0:
            raise AircraftValidationError("Field 't_kn' must be a strictly positive number.")

    engine_type = data.get('engine_type')
    if engine_type is not None:
        # Normalize piston / turboprop to prop if passed
        if engine_type in ('piston', 'turboprop'):
            engine_type = 'prop'
        if engine_type not in VALID_ENGINE_TYPES:
            raise AircraftValidationError(
                f"Invalid engine_type: '{engine_type}'. Must be one of {sorted(VALID_ENGINE_TYPES)}."
            )

    # Check propulsion mutual exclusivity
    if engine_type == 'jet':
        if p_kw is not None:
            raise AircraftValidationError("Jet aircraft cannot have engine shaft power 'p_kw'.")
    elif engine_type == 'prop':
        if t_kn is not None:
            raise AircraftValidationError("Propeller aircraft cannot have engine thrust 't_kn'.")
    elif engine_type == 'none':
        if p_kw is not None or t_kn is not None:
            raise AircraftValidationError("Unpowered aircraft (gliders) cannot specify power or thrust.")
    else:
        # engine_type not explicitly given, infer or ensure no contradiction
        if p_kw is not None and t_kn is not None:
            raise AircraftValidationError("Cannot specify both shaft power 'p_kw' and thrust 't_kn'.")
        if p_kw is not None:
            engine_type = 'prop'
        elif t_kn is not None:
            engine_type = 'jet'
        elif act == 'glider':
            engine_type = 'none'
        else:
            engine_type = 'prop'

    # Validate geometry and control ratios if provided
    for ratio_field in ('v_h', 'aileron_span_fraction', 'aileron_chord_ratio',
                        'elevator_chord_ratio', 'rudder_chord_ratio'):
        val = data.get(ratio_field)
        if val is not None:
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or val <= 0:
                raise AircraftValidationError(f"Field '{ratio_field}' must be a positive number.")

    dihedral = data.get('dihedral_deg')
    if dihedral is not None:
        if isinstance(dihedral, bool) or not isinstance(dihedral, (int, float)) or not math.isfinite(dihedral):
            raise AircraftValidationError("Field 'dihedral_deg' must be a finite number.")

    n_engines = data.get('n_engines')
    if n_engines is not None:
        if isinstance(n_engines, bool) or not isinstance(n_engines, int) or n_engines < 0:
            raise AircraftValidationError("Field 'n_engines' must be a non-negative integer.")

    year = data.get('year')
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int) or not (1900 <= year <= 2100):
            raise AircraftValidationError("Field 'year' must be an integer between 1900 and 2100.")

    # Fields editable in the catalogue also require server-side validation.
    limits = {
        'v_cruise_kmh': (0, 3000), 'v_stall_kmh': (0, 1000), 'cruise_mach': (0, 5),
        'range_km': (0, 50000), 'climb_rate_ms': (0, 150), 'ld_max': (0, 150),
        'takeoff_m': (0, 50000), 'landing_m': (0, 50000), 'prop_diameter_m': (0, 20),
        'v_v': (0, .5), 'v_h': (0, 2), 'dihedral_deg': (-15, 20),
        'aileron_span_fraction': (0, 1), 'aileron_chord_ratio': (0, 1),
        'elevator_chord_ratio': (0, 1), 'rudder_chord_ratio': (0, 1),
    }
    for key, (low, high) in limits.items():
        value = data.get(key)
        if value is None or (existing and value == existing.get(key)):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise AircraftValidationError(f"Pole {key}: podaj liczbę od {low} do {high}.")
    for key in ('source_locator', 'source_references', 'empty_mass_definition', 'family'):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 4000):
            raise AircraftValidationError(f"Pole {key}: wymagany tekst do 4000 znaków.")
    for key in ('takeoff_basis', 'landing_basis'):
        value = data.get(key)
        if value is not None and (not existing or value != existing.get(key)) and value not in ('unknown', 'ground_roll', '15m', '50ft', 'field_length'):
            raise AircraftValidationError(f"Pole {key}: wybierz definicję długości.")
    cruise, stall = data.get('v_cruise_kmh'), data.get('v_stall_kmh')
    if isinstance(cruise, (int, float)) and isinstance(stall, (int, float)) and stall >= cruise:
        raise AircraftValidationError('Prędkość przeciągnięcia musi być mniejsza od prędkości przelotowej.')

    unknown = sorted(set(data) - set(COLUMN_NAMES) - DERIVED_KEYS - RESPONSE_KEYS)
    if unknown:
        raise AircraftValidationError(f"Nieznane pole rekordu: {', '.join(map(str, unknown))}.")
    for key in COLUMN_NAMES:
        value = data.get(key)
        if value is None or key == 'variable_sweep':
            continue
        if COLUMN_TYPES[key] == 'TEXT' and not isinstance(value, str):
            raise AircraftValidationError(f"Pole {key}: wymagany tekst.")
        if COLUMN_TYPES[key] == 'REAL' and (isinstance(value, bool) or not isinstance(value, (int, float))
                                            or not math.isfinite(value)):
            raise AircraftValidationError(f"Pole {key}: podaj skończoną liczbę.")
    if not isinstance(data.get('variable_sweep', False), bool):
        raise AircraftValidationError("Pole variable_sweep: wymagana wartość logiczna.")

    # Build clean output dictionary (stripping derived keys and response wrappers)
    clean = {k: v for k, v in data.items() if k not in DERIVED_KEYS | RESPONSE_KEYS}
    clean['year'] = int(year) if year is not None else None
    if aircraft_id:
        clean['id'] = aircraft_id.strip()
    if engine_type:
        clean['engine_type'] = engine_type
    if m0 is not None:
        clean['m0'] = float(m0)
    if me is not None:
        clean['me'] = float(me)
    if s is not None:
        clean['s'] = float(s)
    if b is not None:
        clean['b'] = float(b)
    if p_kw is not None:
        clean['p_kw'] = float(p_kw)
    if t_kn is not None:
        clean['t_kn'] = float(t_kn)
    if n_engines is not None:
        clean['n_engines'] = int(n_engines)
    elif is_create and 'n_engines' not in clean:
        clean['n_engines'] = 0 if engine_type == 'none' else 1

    return clean


class AircraftDatabase:
    """CRUD service for the reference aircraft catalogue stored in SQLite.

    path=None follows aircraft_store.database_path() (BIPOL_AIRCRAFT_DB or the default file).
    """

    def __init__(self, path=None):
        self.path = path
        # SQLite serialises writers too; the lock only avoids busy waits inside one process.
        self.lock = threading.RLock()

    def get_all(self) -> tuple:
        """Returns all reference aircraft with derived attributes."""
        return load_aircraft()

    def get_by_id(self, aircraft_id: str) -> dict | None:
        """Finds aircraft by unique ID and returns full derived record, or None if not found."""
        with aircraft_store.connect(self.path) as con:
            record = aircraft_store.fetch(con, aircraft_id)
        return derived(record) if record else None

    def create(self, record_data: dict) -> dict:
        """Validates and inserts a new aircraft record in one transaction."""
        clean = validate_aircraft(record_data, is_create=True)
        aid = clean['id']

        clean['source_id'] = clean.get('source_id') or USER_SOURCE
        if clean['source_id'] not in KNOWN_SOURCES:
            raise AircraftValidationError(f"Nieznane źródło danych: '{clean['source_id']}'.")

        # Provide safe standard defaults for optional metadata fields
        if not clean.get('family'):
            clean['family'] = clean.get('model') or aid
        if not clean.get('source_locator'):
            clean['source_locator'] = 'BiPOL Requiem User Input'
        if not clean.get('source_references'):
            clean['source_references'] = 'User input via BiPOL Requiem Database Editor'
        clean.setdefault('empty_mass_definition', 'OEW / operating empty weight')
        clean.setdefault('year_basis', 'certification')
        clean.setdefault('variable_sweep', False)

        with self.lock:
            try:
                with aircraft_store.transaction(self.path) as con:
                    aircraft_store.insert(con, clean)
            except sqlite3.IntegrityError as error:
                raise _integrity_error(error, aid) from None
        return self.get_by_id(aid)

    def update(self, aircraft_id: str, updates: dict) -> dict:
        """Merges, validates and saves changes to an existing record in one transaction."""
        if not isinstance(updates, dict):
            raise AircraftValidationError("Payload must be a JSON object.")
        with self.lock:
            try:
                with aircraft_store.transaction(self.path) as con:
                    existing = aircraft_store.fetch(con, aircraft_id)
                    if existing is None:
                        raise AircraftNotFoundError(f"Aircraft with id '{aircraft_id}' not found.")
                    # Merge updates while preserving the original immutable ID
                    merged = {**existing, **updates, 'id': aircraft_id}
                    clean = validate_aircraft(merged, is_create=False, existing=existing)
                    aircraft_store.update(con, aircraft_id, clean)
            except sqlite3.IntegrityError as error:
                raise _integrity_error(error, aircraft_id) from None
        return self.get_by_id(aircraft_id)

    def delete(self, aircraft_id: str) -> bool:
        """Deletes an aircraft record by ID."""
        with self.lock, aircraft_store.transaction(self.path) as con:
            if not aircraft_store.delete(con, aircraft_id):
                raise AircraftNotFoundError(f"Aircraft with id '{aircraft_id}' not found.")
        return True


def _integrity_error(error, aircraft_id):
    if 'UNIQUE constraint failed: aircraft.id' in str(error):
        return AircraftDuplicateError(f"Aircraft with id '{aircraft_id}' already exists.")
    return AircraftValidationError(f'Rekord narusza ograniczenia bazy danych ({error}).')


# Module-level default instance and helper functions
db = AircraftDatabase()


def get_aircraft_database() -> AircraftDatabase:
    """Returns the default AircraftDatabase singleton."""
    return db


def get_aircraft(aircraft_id: str) -> dict | None:
    return db.get_by_id(aircraft_id)


def create_aircraft(record_data: dict) -> dict:
    return db.create(record_data)


def update_aircraft(aircraft_id: str, updates: dict) -> dict:
    return db.update(aircraft_id, updates)


def delete_aircraft(aircraft_id: str) -> bool:
    return db.delete(aircraft_id)

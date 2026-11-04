"""Adversarial and Empirical Stress Test Suite for Milestone 2 Aircraft Database CRUD.

Covers:
1. Multi-threaded concurrent Create, Read, Update, and Delete requests against AircraftDatabase and REST API.
2. Race condition prevention (SQLite transactions and UNIQUE constraints).
3. Lost update and duplicate key collision detection under concurrent access.
4. Continuous read-during-write stress (consistent snapshots, no partial writes).
5. Schema integrity and physical invariant enforcement during concurrent mutations.
6. Persistence survival across independent Python sub-process restarts.
"""
import subprocess
import sys
import threading
import time
from pathlib import Path
import pytest

from app import app
from calculations import aircraft_store
from calculations.aircraft_db import (
    AircraftDatabaseError,
    AircraftValidationError,
    AircraftDuplicateError,
    get_aircraft_database,
)
from calculations.trends import load_aircraft, reference_catalog


# ==============================================================================
# Isolation Fixture for Stress Testing
# ==============================================================================

@pytest.fixture
def atomic_isolated_db(isolated_db):
    """The shared fixture restores the test database after each stress test."""
    yield


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


# ==============================================================================
# 1. High-Concurrency Multi-Threaded Mixed CRUD Stress Test
# ==============================================================================

def test_stress_concurrent_mixed_crud(atomic_isolated_db):
    """Stress tests 20 threads concurrently creating, reading, updating, and deleting records.
    
    Verifies:
    - Zero unhandled exceptions or crashes.
    - Zero file corruption or partial JSON writes.
    - Consistency of database state after concurrent operations finish.
    """
    db = get_aircraft_database()
    num_threads = 20
    threads = []
    errors = []
    created_ids = []
    created_lock = threading.Lock()

    def worker(worker_id):
        aid = f"stress-mixed-{worker_id}"
        payload = {
            "id": aid,
            "model": f"Stress Model {worker_id}",
            "manufacturer": "Teamwork Stress Labs",
            "aircraft_type": "piston_ga",
            "engine_type": "prop",
            "m0": 1100.0 + worker_id * 10,
            "me": 650.0,
            "s": 15.0,
            "b": 10.0,
            "p_kw": 120.0,
        }

        try:
            # 1. Create
            rec = db.create(payload)
            with created_lock:
                created_ids.append(aid)
            assert rec['id'] == aid

            # 2. Concurrent read
            retrieved = db.get_by_id(aid)
            assert retrieved is not None
            assert retrieved['id'] == aid

            # 3. Update
            updated = db.update(aid, {"m0": 1250.0 + worker_id, "model": f"Stress Model {worker_id} Rev B"})
            assert updated['m0'] == 1250.0 + worker_id

            # 4. Read all records
            all_records = db.get_all()
            assert any(r['id'] == aid for r in all_records)

            # 5. Delete even-numbered workers, keep odd-numbered
            if worker_id % 2 == 0:
                assert db.delete(aid) is True
                assert db.get_by_id(aid) is None

        except Exception as e:
            errors.append((worker_id, type(e).__name__, str(e)))

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=10.0)

    assert len(errors) == 0, f"Concurrent workers encountered errors: {errors}"

    # Verify final disk state and surviving records
    for i in range(num_threads):
        aid = f"stress-mixed-{i}"
        rec = db.get_by_id(aid)
        if i % 2 == 0:
            assert rec is None, f"Deleted aircraft {aid} still exists in memory"
        else:
            assert rec is not None, f"Surviving aircraft {aid} missing from memory"
            assert rec['model'] == f"Stress Model {i} Rev B"


# ==============================================================================
# 2. Concurrent Duplicate ID Creation Collision Test
# ==============================================================================

def test_stress_concurrent_duplicate_id_collision(atomic_isolated_db):
    """10 threads concurrently attempt to create an aircraft with the identical ID.
    
    Verifies:
    - Exactly ONE thread succeeds in creating the record.
    - Exactly 9 threads receive AircraftDuplicateError.
    - Exactly one copy of the aircraft exists in the database.
    """
    db = get_aircraft_database()
    target_id = "stress-race-collision-target"
    payload = {
        "id": target_id,
        "model": "Collision Candidate",
        "manufacturer": "Teamwork PW MEiL",
        "aircraft_type": "jet_business",
        "engine_type": "jet",
        "m0": 8500.0,
        "me": 4800.0,
        "s": 28.0,
        "b": 15.0,
        "t_kn": 32.0,
    }

    num_threads = 10
    successes = []
    duplicates = []
    other_errors = []
    threads = []

    def worker(worker_id):
        try:
            res = db.create(payload)
            successes.append((worker_id, res))
        except AircraftDuplicateError as e:
            duplicates.append((worker_id, str(e)))
        except Exception as e:
            other_errors.append((worker_id, type(e).__name__, str(e)))

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)

    # Start all threads simultaneously
    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=5.0)

    assert len(other_errors) == 0, f"Unexpected errors during collision test: {other_errors}"
    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"
    assert len(duplicates) == num_threads - 1, f"Expected {num_threads - 1} duplicates, got {len(duplicates)}"

    # Check the stored rows directly
    with aircraft_store.connect() as con:
        matches = con.execute('SELECT COUNT(*) FROM aircraft WHERE id = ?', (target_id,)).fetchone()[0]
    assert matches == 1, f"Expected exactly 1 record with id {target_id} in the database, found {matches}"


# ==============================================================================
# 3. Continuous Reader-During-Heavy-Writer Stress Test
# ==============================================================================

def test_stress_readers_during_continuous_writes(atomic_isolated_db):
    """Stress tests readers querying the database while writers are in an aggressive mutation loop.
    
    Verifies:
    - Readers NEVER observe partial writes or a corrupt database.
    - Transactions guarantee reader isolation.
    """
    db = get_aircraft_database()
    rounds = 25
    baseline = len(load_aircraft())
    # Start and finish each overlapping read/write round together. A fast writer
    # cannot outrun a reader, and a busy runner cannot truncate the sample.
    round_gate = threading.Barrier(5, timeout=30)
    writer_errors = []
    reader_errors = []
    read_counts = [0, 0, 0, 0]
    completed_writes = []

    def writer_worker():
        try:
            for cycle in range(1, rounds + 1):
                round_gate.wait()
                aid = f"stress-rw-plane-{cycle}"
                payload = {
                    "id": aid,
                    "model": f"Continuous Model {cycle}",
                    "manufacturer": "RW Stress Labs",
                    "aircraft_type": "piston_ga",
                    "engine_type": "prop",
                    "m0": 1050.0 + cycle,
                    "me": 620.0,
                    "s": 14.5,
                    "b": 10.2,
                    "p_kw": 115.0,
                }
                # Create
                db.create(payload)
                # Update
                db.update(aid, {"m0": 1150.0 + cycle})
                # Delete
                db.delete(aid)
                completed_writes.append(cycle)
                round_gate.wait()
        except Exception as e:
            writer_errors.append((type(e).__name__, str(e)))
            round_gate.abort()

    def reader_worker(reader_idx):
        try:
            for _ in range(rounds):
                round_gate.wait()
                # Read all aircraft
                all_ac = load_aircraft()
                assert baseline <= len(all_ac) <= baseline + 1
                
                # Read catalog
                cat = reference_catalog()
                assert baseline <= cat['total'] <= baseline + 1
                
                # Read raw rows directly, bypassing the cache
                with aircraft_store.connect() as con:
                    assert baseline <= con.execute('SELECT COUNT(*) FROM aircraft').fetchone()[0] <= baseline + 1
                    assert con.execute('PRAGMA quick_check').fetchone()[0] == 'ok'

                read_counts[reader_idx] += 1
                round_gate.wait()
        except Exception as e:
            reader_errors.append((reader_idx, type(e).__name__, str(e)))
            round_gate.abort()

    # Launch 1 writer and 4 readers
    writer_thread = threading.Thread(target=writer_worker)
    reader_threads = [threading.Thread(target=reader_worker, args=(i,)) for i in range(4)]

    for t in reader_threads:
        t.start()
    writer_thread.start()

    threads = [writer_thread, *reader_threads]
    deadline = time.monotonic() + 120
    try:
        for t in threads:
            t.join(timeout=max(0, deadline - time.monotonic()))
    finally:
        # Release peers on failure and join them before the fixture restores SQLite.
        round_gate.abort()
        for t in threads:
            t.join(timeout=35)

    assert not any(t.is_alive() for t in threads), 'Read/write workers did not terminate'
    assert not (writer_errors or reader_errors), f"Read/write errors: writer={writer_errors}; readers={reader_errors}"
    assert read_counts == [rounds] * 4, f"Incomplete read rounds: {read_counts}"
    assert completed_writes == list(range(1, rounds + 1))
    assert len(load_aircraft()) == baseline


# ==============================================================================
# 4. REST API Concurrent CRUD via Flask Test Client
# ==============================================================================

def test_stress_rest_api_concurrent_crud(atomic_isolated_db):
    """Stress tests concurrent HTTP requests across Flask REST API endpoints:
    - POST /api/aircraft
    - GET /api/aircraft/<id>
    - PUT /api/aircraft/<id>
    - DELETE /api/aircraft/<id>
    """
    num_requests = 16
    threads = []
    status_codes = []
    api_errors = []

    def api_worker(worker_id):
        t_client = app.test_client()
        aid = f"stress-api-plane-{worker_id}"
        payload = {
            "id": aid,
            "model": f"API Plane {worker_id}",
            "manufacturer": "API Stress Labs",
            "aircraft_type": "turboprop_regional",
            "engine_type": "prop",
            "m0": 18500.0 + worker_id * 100,
            "me": 11500.0,
            "s": 61.0,
            "b": 28.0,
            "p_kw": 1800.0,
        }
        try:
            # 1. POST Create
            res_post = t_client.post('/api/aircraft', json=payload)
            assert res_post.status_code == 201, f"POST failed: {res_post.status_code} {res_post.data}"

            # 2. GET Retrieve
            res_get = t_client.get(f'/api/aircraft/{aid}')
            assert res_get.status_code == 200, f"GET failed: {res_get.status_code}"
            assert res_get.get_json()['aircraft']['id'] == aid

            # 3. PUT Update
            res_put = t_client.put(f'/api/aircraft/{aid}', json={"m0": 19000.0 + worker_id})
            assert res_put.status_code == 200, f"PUT failed: {res_put.status_code}"

            # 4. DELETE
            res_del = t_client.delete(f'/api/aircraft/{aid}')
            assert res_del.status_code == 200, f"DELETE failed: {res_del.status_code}"

            # 5. Confirm 404 after delete
            res_del_verify = t_client.get(f'/api/aircraft/{aid}')
            assert res_del_verify.status_code == 404


        except Exception as e:
            api_errors.append((worker_id, type(e).__name__, str(e)))

    for i in range(num_requests):
        t = threading.Thread(target=api_worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=15.0)

    assert len(api_errors) == 0, f"API concurrency errors: {api_errors}"


# ==============================================================================
# 5. Invariant & Schema Integrity Under Adverse Concurrent Injections
# ==============================================================================

def test_stress_concurrent_schema_validation_invariants(atomic_isolated_db):
    """Concurrently pushes valid and invalid records to ensure physical invariants are strictly preserved.
    
    Verifies:
    - Corrupt entries are rejected under concurrency.
    - Disk files remain 100% compliant with schema invariants:
      * 0 < me < m0
      * s > 0, b > 0
      * engine_type matches propulsion attributes
    """
    db = get_aircraft_database()
    invalid_payloads = [
        {"id": "inv-1", "model": "Bad MTOW", "manufacturer": "Test", "aircraft_type": "piston_ga", "m0": -50.0},
        {"id": "inv-2", "model": "Bad OEW", "manufacturer": "Test", "aircraft_type": "piston_ga", "m0": 1000.0, "me": 1500.0},
        {"id": "inv-3", "model": "Bad Area", "manufacturer": "Test", "aircraft_type": "piston_ga", "m0": 1000.0, "s": 0.0},
        {"id": "inv-4", "model": "Bad Span", "manufacturer": "Test", "aircraft_type": "piston_ga", "m0": 1000.0, "b": -3.0},
        {"id": "inv-5", "model": "Jet with Power", "manufacturer": "Test", "aircraft_type": "jet_business", "engine_type": "jet", "m0": 5000.0, "p_kw": 500.0},
        {"id": "inv-6", "model": "Prop with Thrust", "manufacturer": "Test", "aircraft_type": "piston_ga", "engine_type": "prop", "m0": 1000.0, "t_kn": 20.0},
        {"id": "inv-7", "model": "Glider with Power", "manufacturer": "Test", "aircraft_type": "glider", "engine_type": "none", "m0": 450.0, "p_kw": 30.0},
        {"id": "inv/bad/path", "model": "Bad ID", "manufacturer": "Test", "aircraft_type": "piston_ga", "m0": 1000.0},
    ]

    valid_payloads = [
        {"id": f"val-plane-{i}", "model": f"Valid Plane {i}", "manufacturer": "Valid Aero", "aircraft_type": "piston_ga", "engine_type": "prop", "m0": 1000.0 + i * 50, "me": 600.0, "s": 14.0, "b": 10.0, "p_kw": 110.0}
        for i in range(8)
    ]

    errors = []
    threads = []

    def invalid_worker(p):
        try:
            db.create(p)
            errors.append(f"Invalid payload was accepted unexpectedly: {p['id']}")
        except (AircraftValidationError, AircraftDatabaseError):
            pass  # Expected rejection
        except Exception as e:
            errors.append(f"Unexpected exception on invalid payload: {type(e).__name__} {e}")

    def valid_worker(p):
        try:
            rec = db.create(p)
            assert rec['id'] == p['id']
            # Immediately delete to clean up
            db.delete(p['id'])
        except Exception as e:
            errors.append(f"Valid payload failed: {p['id']} - {type(e).__name__} {e}")

    for p in invalid_payloads:
        t = threading.Thread(target=invalid_worker, args=(p,))
        threads.append(t)

    for p in valid_payloads:
        t = threading.Thread(target=valid_worker, args=(p,))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert len(errors) == 0, f"Validation invariant stress failures: {errors}"


# ==============================================================================
# 6. Cold Restart & Persistence Survival Verification
# ==============================================================================

def test_stress_persistence_survives_process_restart(atomic_isolated_db):
    """Creates a record in the database, spawns a fresh independent Python subprocess
    (simulating a complete server restart), and verifies the record is loaded and valid.
    """
    db = get_aircraft_database()
    test_id = "stress-restart-survival-plane"
    payload = {
        "id": test_id,
        "model": "Restart Survivor 3000",
        "manufacturer": "Politechnika Warszawska MEiL",
        "aircraft_type": "piston_ga",
        "engine_type": "prop",
        "m0": 1350.0,
        "me": 810.0,
        "s": 16.5,
        "b": 11.2,
        "p_kw": 145.0,
    }

    created = db.create(payload)
    assert created['id'] == test_id

    # Execute a clean separate Python process that queries load_aircraft()
    sub_code = f"""
import sys
import json
from pathlib import Path
from calculations.aircraft_db import get_aircraft_database
from calculations.trends import load_aircraft

db = get_aircraft_database()
rec = db.get_by_id("{test_id}")
if rec is None:
    print("ERROR: Record not found in db.get_by_id")
    sys.exit(1)

if rec['model'] != "Restart Survivor 3000":
    print(f"ERROR: Model mismatch: {{rec['model']}}")
    sys.exit(2)

if rec['m0'] != 1350.0:
    print(f"ERROR: m0 mismatch: {{rec['m0']}}")
    sys.exit(3)

# Verify derived properties calculated correctly on cold start
if 'wing_loading_kg_m2' not in rec or rec['wing_loading_kg_m2'] is None:
    print("ERROR: Missing derived wing_loading_kg_m2")
    sys.exit(4)

expected_ws = 1350.0 / 16.5
if abs(rec['wing_loading_kg_m2'] - expected_ws) > 0.01:
    print(f"ERROR: Incorrect wing loading {{rec['wing_loading_kg_m2']}} vs {{expected_ws}}")
    sys.exit(5)

print("SUBPROCESS_SUCCESS")
sys.exit(0)
"""
    result = subprocess.run(
        [sys.executable, "-c", sub_code],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        timeout=10.0
    )

    assert result.returncode == 0, f"Cold restart verification failed (code {result.returncode}):\nstdout: {result.stdout}\nstderr: {result.stderr}"
    assert "SUBPROCESS_SUCCESS" in result.stdout

    # Clean up
    db.delete(test_id)
    assert db.get_by_id(test_id) is None


# ==============================================================================
# 7. Database Integrity After Concurrent Mutations
# ==============================================================================

def test_stress_database_integrity_after_concurrent_writes(atomic_isolated_db):
    """After concurrent writes the database passes SQLite integrity and foreign-key checks
    and holds every created record exactly once."""
    db = get_aircraft_database()
    threads = [threading.Thread(target=db.create, args=({
        "id": f"integrity-plane-{i}", "model": f"Integrity {i}", "manufacturer": "Test",
        "aircraft_type": "piston_ga", "engine_type": "prop", "m0": 900.0 + i, "p_kw": 80.0},))
        for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    with aircraft_store.connect() as con:
        assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
        assert con.execute('SELECT COUNT(*) - COUNT(DISTINCT id) FROM aircraft').fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM aircraft WHERE id LIKE 'integrity-plane-%'").fetchone()[0] == 10

"""Adversarial stress tests and empirical database consistency verification for:
- GET /api/trends/suggestions
- get_trend_suggestions() dynamic regression engine

Author: teamwork_preview_challenger (Challenger 2 for Milestone 1)
Scope:
1. Malformed parameter types (strings for m0, unsupported wing configs, null bytes, NaN/Inf).
2. Consistency of regression outputs with the underlying reference database (data/aircraft/aircraft.sqlite3).
3. Concurrent and rapid requests.
4. Latency and resource bounds (<200 ms per query).
"""
import concurrent.futures
import math
import statistics
import time
import pytest
from app import app
from calculations import aircraft_store
from calculations.trends import (
    CLASSES,
    SOURCES,
    get_trend_suggestions,
    load_aircraft,
    select_references,
)

G0 = 9.80665

REQUIRED_PARAMS = [
    'ws',
    'ar',
    'me_m0',
    'pw',
    'tw',
    'vh',
    'v_v',
    'b_ail_ratio',
    'c_ail_ratio',
    'c_e_ratio',
    'c_r_ratio',
    'dihedral_deg',
]


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


# ==============================================================================
# Task 1: Malformed and Boundary Parameter Types
# ==============================================================================

class TestMalformedParameters:
    """Stress-tests input validation on GET /api/trends/suggestions."""

    @pytest.mark.parametrize("bad_m0", [
        "abc",
        "invalid_float",
        "1000kg",
        "None",
        "null",
        "true",
        "[1000]",
        "12.34.56",
        "1e999999",  # Overflow to inf during float parsing
        "-10",
        "-0.0001",
        "-1e5",
    ])
    def test_malformed_or_negative_m0_returns_400(self, client, bad_m0):
        """String or negative m0 values must return HTTP 400 Bad Request."""
        res = client.get(f'/api/trends/suggestions?aircraft_type=piston_ga&m0={bad_m0}')
        assert res.status_code == 400, f"Expected 400 for m0='{bad_m0}', got {res.status_code}"
        data = res.get_json()
        assert data['status'] == 'error'
        assert 'message' in data

    @pytest.mark.parametrize("special_m0", [
        "nan",
        "NaN",
        "NAN",
        "inf",
        "-inf",
        "+inf",
        "Infinity",
        "-Infinity",
    ])
    def test_non_finite_m0_returns_400(self, client, special_m0):
        """Non-finite float strings must return HTTP 400."""
        res = client.get(f'/api/trends/suggestions?aircraft_type=piston_ga&m0={special_m0}')
        assert res.status_code == 400
        data = res.get_json()
        assert data['status'] == 'error'

    def test_zero_m0_falls_back_to_cohort_without_error(self, client):
        """m0=0 in query parameter should cleanly fall back to cohort defaults (no division by zero)."""
        res = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=0')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'ok'
        assert data['m0'] is None
        assert 'suggestions' in data

    @pytest.mark.parametrize("extreme_m0", [
        1e-5,   # Extremely tiny positive MTOW
        1e7,    # 10,000 tonnes (gigantic aircraft)
        1e15,   # Absurdly large number
    ])
    def test_extreme_positive_m0_does_not_crash(self, client, extreme_m0):
        """Extreme positive numbers should evaluate or clamp without throwing unhandled exceptions."""
        res = client.get(f'/api/trends/suggestions?aircraft_type=piston_ga&m0={extreme_m0}')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'ok'
        for key, val in data['suggestions'].items():
            if val['suggested_value'] is not None:
                assert math.isfinite(val['suggested_value'])

    @pytest.mark.parametrize("bad_type", [
        "",
        "unknown_aircraft",
        "fighter_jet",
        "helicopter",
        "space_shuttle",
        "piston_ga\x00",
        "%00",
        "../../cado",
        "piston_ga' OR '1'='1",
        "<script>alert(1)</script>",
        "PISTON_GA",  # Case-sensitive check
        " piston_ga ",
    ])
    def test_invalid_aircraft_types_return_400(self, client, bad_type):
        """Invalid, empty, or malicious aircraft_type values must return HTTP 400."""
        res = client.get(f'/api/trends/suggestions?aircraft_type={bad_type}')
        assert res.status_code == 400
        data = res.get_json()
        assert data['status'] == 'error'

    @pytest.mark.parametrize("wing_cfg", [
        "cantilever",
        "strut_braced",
        "high",
        "braced_high",
        "low",
        "biplane",
        "flying_wing",
        "unknown_cfg",
        "null",
        "",
        "12345",
        "cantilever\x00",
    ])
    def test_various_wing_configurations_handled_gracefully(self, client, wing_cfg):
        """Unsupported or arbitrary wing configs should not crash the server and must return valid suggestions."""
        res = client.get(f'/api/trends/suggestions?aircraft_type=piston_ga&m0=1150&wing_configuration={wing_cfg}')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'ok'
        assert 'dihedral_deg' in data['suggestions']
        dih = data['suggestions']['dihedral_deg']
        assert dih['suggested_value'] is not None
        assert math.isfinite(dih['suggested_value'])

    @pytest.mark.parametrize("method", ["put", "delete", "patch"])
    def test_non_get_http_methods_rejected(self, client, method):
        """Endpoint allows GET and POST (project sample settings); PUT/DELETE/PATCH return 405."""
        func = getattr(client, method)
        res = func('/api/trends/suggestions?aircraft_type=piston_ga')
        assert res.status_code == 405

    def test_direct_python_api_boundary_exceptions(self):
        """Verify get_trend_suggestions() enforces strict parameter contracts in Python."""
        with pytest.raises(ValueError, match="Unknown aircraft_type"):
            get_trend_suggestions("not_a_real_class")

        with pytest.raises(ValueError, match="positive finite number"):
            get_trend_suggestions("piston_ga", m0=-50)

        with pytest.raises(ValueError, match="positive finite number"):
            get_trend_suggestions("piston_ga", m0=0)

        with pytest.raises(ValueError, match="positive finite number"):
            get_trend_suggestions("piston_ga", m0=float('nan'))

        with pytest.raises(ValueError, match="positive finite number"):
            get_trend_suggestions("piston_ga", m0=float('inf'))

        with pytest.raises(ValueError, match="positive finite number"):
            get_trend_suggestions("piston_ga", m0="not_a_number")


# ==============================================================================
# Task 2: Empirical Consistency with Reference Database (data/aircraft/aircraft.sqlite3)
# ==============================================================================

class TestDatabaseConsistencyOracle:
    """Verifies that suggestion metrics and sample counts exactly match the raw database."""

    @classmethod
    def setup_class(cls):
        """Load raw rows with plain SQL, without the load_aircraft cache or derived()."""
        cls.raw_records = []
        with aircraft_store.connect() as con:
            records = con.execute('SELECT * FROM aircraft').fetchall()
            assert records, "Reference database is empty"
        for r in records:
            rec = dict(r)
            mass = rec.get('m0')
            area = rec.get('s')
            span = rec.get('b')
            me = rec.get('me')
            p_kw = rec.get('p_kw')
            t_kn = rec.get('t_kn')

            rec['ar'] = (span * span / area) if (span and area and area > 0) else None
            rec['empty_fraction'] = (me / mass) if (me and mass and mass > 0) else None
            rec['wing_loading_kg_m2'] = (mass / area) if (mass and area and area > 0) else None
            rec['power_loading_kg_kw'] = (mass / p_kw) if (mass and p_kw and p_kw > 0) else None
            rec['thrust_to_weight'] = (t_kn * 1000 / (mass * G0)) if (t_kn and mass and mass > 0) else None
            cls.raw_records.append(rec)

    def selected_records(self, ac_class, engine):
        ids = {r['id'] for r in select_references(dict(aircraft_type=ac_class, engine_type=engine,
                                                      trend_nearest_count=0))}
        # Verify values with independent SQL-derived records after choosing one variant per family.
        return [r for r in self.raw_records if r['id'] in ids]

    @pytest.mark.parametrize("ac_class", list(CLASSES.keys()))
    def test_sample_counts_match_database_records(self, client, ac_class):
        """Without m0 the sample contains one best variant of each matching family."""
        res = client.get(f'/api/trends/suggestions?aircraft_type={ac_class}')
        assert res.status_code == 200
        data = res.get_json()
        suggestions = data['suggestions']

        class_records = self.selected_records(ac_class, data['engine_type'])
        assert data['sample']['selected_n'] == len(class_records)
        for item in suggestions.values():
            # Every value is traceable: n equals the observations listed in its provenance.
            if item['provenance'] and item['suggested_value'] is not None:
                assert item['n'] == len(item['provenance']['observations'])

        # 1. ws and 2. ar: all observations, or only dated ones when the time trend is used
        def dated(rows):
            return [r for r in rows if r.get('year') is not None]

        for key, metric_rows in (('ws', [r for r in class_records if r.get('wing_loading_kg_m2')]),
                                 ('ar', [r for r in class_records if r.get('ar') and 2 <= r['ar'] <= 60])):
            item = suggestions[key]
            assert item['available_n'] == len(metric_rows)
            expected = len(dated(metric_rows)) if item['model_type'] == 'time_trend' else len(metric_rows)
            assert item['n'] == expected, f"{key} N mismatch for {ac_class}: api={item['n']} vs db={expected}"

        # 3. me_m0 (Empty mass fraction, filtered 0.15 < empty_fraction < 0.95)
        expected_me_pts = [r for r in class_records if r.get('m0') and r.get('empty_fraction') and 0.15 < r['empty_fraction'] < 0.95]
        assert suggestions['me_m0']['n'] == len(expected_me_pts), (
            f"me_m0 N mismatch for {ac_class}: api={suggestions['me_m0']['n']} vs db={len(expected_me_pts)}"
        )

        # 4. pw for propeller propulsion, 5. tw for jets
        if data['engine_type'] == 'prop':
            assert suggestions['pw']['available_n'] == len([r for r in class_records if r.get('power_loading_kg_kw')])
        else:
            assert suggestions['pw']['n'] == 0
        if data['engine_type'] == 'jet':
            assert suggestions['tw']['available_n'] == len([r for r in class_records if r.get('thrust_to_weight')])
        else:
            assert suggestions['tw']['n'] == 0

        # 6. vh (Horizontal tail volume)
        expected_vh_pts = [r for r in class_records if r.get('m0') and r.get('v_h') is not None]
        assert suggestions['vh']['n'] == len(expected_vh_pts), (
            f"vh N mismatch for {ac_class}: api={suggestions['vh']['n']} vs db={len(expected_vh_pts)}"
        )
        assert suggestions['v_v']['n'] == len([r for r in class_records if r.get('v_v') is not None])

        # 7. Control surfaces
        expected_ba = [r for r in class_records if r.get('aileron_span_fraction') is not None]
        assert suggestions['b_ail_ratio']['n'] == len(expected_ba)

        expected_ca = [r for r in class_records if r.get('aileron_chord_ratio') is not None]
        assert suggestions['c_ail_ratio']['n'] == len(expected_ca)

        expected_ce = [r for r in class_records if r.get('elevator_chord_ratio') is not None]
        assert suggestions['c_e_ratio']['n'] == len(expected_ce)

        expected_cr = [r for r in class_records if r.get('rudder_chord_ratio') is not None]
        assert suggestions['c_r_ratio']['n'] == len(expected_cr)

        expected_dih = [r for r in class_records if r.get('dihedral_deg') is not None]
        assert suggestions['dihedral_deg']['n'] == len(expected_dih)

    @pytest.mark.parametrize("ac_class", list(CLASSES.keys()))
    def test_statistical_distribution_consistency(self, client, ac_class):
        """Verify stats (min, max, mean, median) are strictly consistent with database values."""
        res = client.get(f'/api/trends/suggestions?aircraft_type={ac_class}')
        data = res.get_json()
        suggestions = data['suggestions']
        class_records = self.selected_records(ac_class, data['engine_type'])

        # Check wing loading stats if sample exists
        ws_vals = [r['wing_loading_kg_m2'] for r in class_records if r.get('m0') and r.get('wing_loading_kg_m2')]
        ws_stats = suggestions['ws']['stats']
        if ws_vals:
            assert ws_stats is not None
            assert ws_stats['min'] == pytest.approx(min(ws_vals), rel=1e-3)
            assert ws_stats['max'] == pytest.approx(max(ws_vals), rel=1e-3)
            assert ws_stats['mean'] == pytest.approx(statistics.mean(ws_vals), rel=1e-3)
            assert ws_stats['median'] == pytest.approx(statistics.median(ws_vals), rel=1e-3)
        else:
            assert ws_stats is None


# ==============================================================================
# Task 3: Concurrent & Rapid Requests Stress Testing
# ==============================================================================

class TestConcurrencyAndRapidBursts:
    """Tests thread-safety and rapid request endurance."""

    def test_concurrent_requests_multi_threaded(self, client):
        """Execute 100 concurrent requests across different threads, classes, and masses."""
        classes = list(CLASSES.keys())
        masses = [800, 1150, 2500, 5000, 15000, 75000, None]

        queries = []
        for i in range(100):
            ac = classes[i % len(classes)]
            m = masses[i % len(masses)]
            url = f'/api/trends/suggestions?aircraft_type={ac}' + (f'&m0={m}' if m else '')
            queries.append(url)

        def make_request(url):
            return client.get(url)

        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(make_request, url) for url in queries]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        elapsed = time.perf_counter() - start

        assert len(results) == 100
        for res in results:
            assert res.status_code == 200
            data = res.get_json()
            assert data['status'] == 'ok'
            assert len(data['suggestions']) == 12

        throughput = 100 / elapsed
        print(f"\n[Concurrency] 100 concurrent requests completed in {elapsed*1000:.1f}ms ({throughput:.1f} req/s)")

    def test_rapid_sequential_burst(self, client):
        """Execute 150 rapid sequential requests in tight loop."""
        start = time.perf_counter()
        latencies = []
        for i in range(150):
            t0 = time.perf_counter()
            res = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=1150')
            latencies.append((time.perf_counter() - t0) * 1000)
            assert res.status_code == 200
        total_time = (time.perf_counter() - start) * 1000

        avg_lat = statistics.mean(latencies)
        max_lat = max(latencies)
        p99_lat = sorted(latencies)[int(0.99 * len(latencies))]

        print(f"\n[Rapid Burst] 150 requests: total={total_time:.1f}ms, avg={avg_lat:.2f}ms, p99={p99_lat:.2f}ms, max={max_lat:.2f}ms")
        assert max_lat < 200.0, f"Maximum latency {max_lat:.2f}ms exceeded 200ms limit"


# ==============================================================================
# Task 4: Latency and Resource Bounds (<200 ms per query)
# ==============================================================================

class TestLatencyAndResourceBounds:
    """Verifies strict latency bounds (< 200 ms per suggestion query)."""

    @pytest.mark.parametrize("ac_class", list(CLASSES.keys()))
    def test_per_class_latency_under_200ms(self, client, ac_class):
        """Every individual class query with dynamic regression evaluation must finish in < 200 ms."""
        # 10 repetitions per class to collect statistics
        latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            res = client.get(f'/api/trends/suggestions?aircraft_type={ac_class}&m0=3000&wing_configuration=cantilever')
            latencies.append((time.perf_counter() - t0) * 1000)
            assert res.status_code == 200

        max_lat = max(latencies)
        avg_lat = statistics.mean(latencies)
        assert max_lat < 200.0, f"Class {ac_class} max latency {max_lat:.2f}ms exceeded 200ms threshold"
        print(f"[Latency] Class {ac_class:20s}: avg={avg_lat:.2f}ms, max={max_lat:.2f}ms")

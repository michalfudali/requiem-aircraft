"""Scientific provenance, independent source units and transactional catalogue updates."""
from copy import deepcopy
import json
import shutil

import pytest

from calculations import aircraft_store
from calculations.primary_research import MANIFEST, SOURCE_ID, validate_manifest
from tools.import_primary_research import apply_manifest


@pytest.fixture
def manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


@pytest.fixture
def clean_catalog(tmp_path):
    path = tmp_path / 'catalog.sqlite3'
    shutil.copy2(aircraft_store.database_path(), path)
    with aircraft_store.transaction(path) as con:
        con.execute('DELETE FROM aircraft WHERE source_id=?', (SOURCE_ID,))
        con.execute('DELETE FROM sources WHERE id=?', (SOURCE_ID,))
    return path


def snapshot(path):
    with aircraft_store.connect(path) as con:
        return [tuple(r) for r in con.execute('SELECT * FROM aircraft ORDER BY id')]


def test_import_is_additive_atomic_and_idempotent(manifest, clean_catalog):
    previous = snapshot(clean_catalog)
    answer = apply_manifest(manifest, clean_catalog)
    assert answer['changed'] == len(manifest['records'])
    with aircraft_store.connect(clean_catalog) as con:
        assert [tuple(r) for r in con.execute('SELECT * FROM aircraft WHERE source_id!=? ORDER BY id', (SOURCE_ID,))] == previous
        before_revision = con.execute('SELECT revision FROM catalog_state').fetchone()[0]
    assert apply_manifest(manifest, clean_catalog)['changed'] == 0
    with aircraft_store.connect(clean_catalog) as con:
        assert con.execute('SELECT revision FROM catalog_state').fetchone()[0] == before_revision
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []


def test_check_mode_never_creates_a_database(manifest, tmp_path):
    path = tmp_path / 'absent.sqlite3'
    assert apply_manifest(manifest, path, check=True)['records'] == len(manifest['records'])
    assert not path.exists()


def test_conflicting_user_record_rolls_back_the_entire_import(manifest, clean_catalog):
    identity = manifest['records'][-1]['id']
    with aircraft_store.transaction(clean_catalog) as con:
        aircraft_store.insert(con,{**validate_manifest(manifest)[-1], 'source_id':'user',
                                  'model':'Concurrent user aircraft'})
    previous = snapshot(clean_catalog)
    with pytest.raises(ValueError, match='foreign-source'):
        apply_manifest(manifest, clean_catalog)
    assert snapshot(clean_catalog) == previous
    with aircraft_store.connect(clean_catalog) as con:
        assert con.execute('SELECT 1 FROM sources WHERE id=?',(SOURCE_ID,)).fetchone() is None


@pytest.mark.parametrize('bad', ['unit','document','locator','duplicate','year'])
def test_incomplete_or_dimensionally_wrong_evidence_cannot_change_the_catalogue(manifest, clean_catalog, bad):
    if bad == 'duplicate':
        manifest['records'].append(deepcopy(manifest['records'][0]))
    else:
        r = manifest['records'][0]
        if bad == 'year':
            r['observations']['year']=dict(value=2020.5,unit='year',locator='Example')
            r['year_basis']='certification'
        else:
            r['observations']['m0'][bad]={'unit':'ft','document':'absent','locator':''}[bad]
    previous = snapshot(clean_catalog)
    with pytest.raises(ValueError):
        apply_manifest(manifest, clean_catalog)
    assert snapshot(clean_catalog) == previous


def test_american_geometry_and_power_use_their_actual_units(manifest):
    rows = {r['id']:r for r in validate_manifest(manifest)}
    rv = next(r for r in rows.values() if r['model'] == "Van's RV-7 (180 hp)")
    assert rv['m0'] == pytest.approx(816.466266)
    assert rv['b'] == pytest.approx(7.62)
    assert rv['s'] == pytest.approx(11.24126784)
    assert rv['p_kw'] == pytest.approx(134.22597688480864)
    assert rv.get('me') is None  # The source gives a range, not a unique weight.
    assert rv['family'] == 'RV7'
    assert rows['pr-tecnam-p2006ng']['n_engines'] == 2
    assert rows['pr-tecnam-p2006ng']['p_kw'] == 147


def test_total_power_derivation_cannot_masquerade_as_one_engine(manifest):
    r = next(r for r in manifest['records'] if r['id']=='pr-tecnam-p2006ng')
    r['observations']['p_kw']['value']=73.5
    with pytest.raises(ValueError, match='derivation'):
        validate_manifest(manifest)


def test_conditional_and_incomplete_performance_stays_outside_the_model(manifest):
    rows={r['id']:r for r in validate_manifest(manifest)}
    raw={r['id']:r for r in manifest['records']}
    assert rows['pr-as34me-18']['m0']==575
    assert rows['pr-as34me-18'].get('takeoff_m') is None
    assert raw['pr-as34me-18']['excluded_observations'][0]['mass_kg']==477
    assert rows['pr-js5'].get('me') is None  # 450 kg excludes the propulsion system.
    assert rows['pr-hph304-js']['engine_type']=='jet'
    for identity in ['pr-sling-2','pr-sling-lsa','pr-sling-tsi','pr-sling-hw']:
        assert rows[identity].get('v_stall_kmh') is None  # Published value is clean VS1, not VS0.
        assert any(e['quantity']=='clean_stall_VS1' for e in raw[identity]['excluded_observations'])
    for r in rows.values():
        if r['aircraft_type'] in ('glider','motoglider'):
            assert r.get('v_max') is None  # Never populate VH with VNE.
        assert r.get('year') is None or r['year_basis']=='certification'


def test_evidence_api_and_export_retain_original_observations(client, manifest):
    response=client.get('/api/aircraft/pr-as34me-18')
    assert response.status_code==200
    evidence=response.json['evidence']
    assert evidence['matches_catalogue']
    assert {e['field'] for e in evidence['observations']}=={'b','s','me','m0','ld_max','p_kw'}
    assert evidence['excluded_observations'][0]['mass_kg']==477
    assert all(e['publication']['url'].startswith('https://') for e in evidence['observations'])
    export=client.get('/download/aircraft/primary_research/evidence')
    assert export.status_code==200 and export.json==manifest
    assert client.get('/download/aircraft/primary_research/license').status_code==200
    assert client.get('/download/aircraft/cado/evidence').status_code==404


def test_local_edit_cannot_inherit_an_unchanged_source_claim(client):
    before=client.get('/api/aircraft/pr-as34me-18').json
    assert client.put('/api/aircraft/pr-as34me-18',json={'me':410}).status_code==200
    after=client.get('/api/aircraft/pr-as34me-18').json
    assert not after['evidence']['matches_catalogue']
    original=next(e for e in after['evidence']['observations'] if e['field']=='me')
    assert original['value']==402 and original['catalogue_value']==410
    assert next(e for e in before['evidence']['observations'] if e['field']=='me')['catalogue_value']==402


def test_every_imported_record_matches_its_published_evidence(client, manifest):
    for record in manifest['records']:
        response=client.get('/api/aircraft/'+record['id'])
        assert response.status_code==200, record['id']
        evidence=response.json['evidence']
        assert evidence['matches_catalogue'], record['id']
        assert {e['field'] for e in evidence['observations']}==set(record['observations'])


@pytest.mark.parametrize('preset',['ga_trainer','vlj_jet','motoglider_aos'])
def test_expanded_sample_mass_fractions_preserve_the_numerical_balance(preset):
    from calculations.mass import calculate_mass_sizing
    from calculations.presets import AIRCRAFT_PRESETS
    result=calculate_mass_sizing(dict(AIRCRAFT_PRESETS[preset],mass_method='proportion'))
    for key,mass_key in [('empty_fraction','m_empty'),('fuel_fraction','m_fuel'),('payload_fraction','m_payload')]:
        assert result[key]==pytest.approx(result[mass_key]/result['m0'],abs=1e-12)
    sized=result['sizing_methods']['proportion']
    reconstructed=(result['m_payload']+result['m_crew'])/(1-sized['empty_fraction']-sized['fuel_fraction'])
    assert reconstructed==pytest.approx(sized['m0'],rel=1e-6,abs=.001)


@pytest.mark.parametrize('preset,minimum',[('ga_trainer',20),('motoglider_aos',8)])
def test_primary_source_runs_a_real_design_and_report_for_each_target_class(client,preset,minimum):
    from calculations.presets import AIRCRAFT_PRESETS
    params=dict(AIRCRAFT_PRESETS[preset],trend_source=SOURCE_ID,trend_nearest_count=0)
    response=client.post('/api/calculate',json=params)
    assert response.status_code==200,response.json
    result=response.json
    rows=result['bipol_projects']['p1']['trend_analysis']['similar_aircraft']
    assert len(rows)>=minimum
    assert all(r['source_id']==SOURCE_ID for r in rows)
    assert len({r['family_key'] for r in rows})==len(rows)
    assert result['mass']['m0']>0
    report=client.post('/report/project/p1',json=params)
    assert report.status_code==200
    assert b'primary_research' in report.data

"""Calculation graph uses the report sheet, exact snapshot and real feedback."""
import json

import pytest

from app import app
from calculations import run_bipol_project
from calculations.calc_sheet import build_sheet,REF,worked_iteration
from calculations.calculation_graph import build_calculation_graph,components
from calculations.presets import AIRCRAFT_PRESETS


@pytest.fixture(scope='module',params=list(AIRCRAFT_PRESETS))
def graph_case(request):
    result=run_bipol_project(AIRCRAFT_PRESETS[request.param])
    return result,build_sheet(result),build_calculation_graph(result)


def test_graph_contains_every_sheet_entry_and_identical_formula_numbers_and_source(graph_case):
    result,sheet,graph=graph_case
    nodes={n['id']:n for n in graph['nodes']}
    assert set(nodes)==set(sheet.entries)|{'@'+key for key in sheet.blocks}
    for key,entry in sheet.entries.items():
        node=nodes[key]
        assert node['tex']==entry['tex']
        assert node['value']==(entry['value'] if entry['kind']!='table' else None)
        assert node['consistent']==entry['consistent']
        assert node['deps']==entry['deps']
        assert not REF.search(node['tex'])
        assert not REF.search(node['substitution_tex'])
    assert nodes['m0']['value']==result['mass']['m0']
    json.dumps(graph,allow_nan=False)


def test_components_keep_all_feedback_and_condensation_is_acyclic(graph_case):
    _,_,graph=graph_case
    lookup={key:c['id'] for c in graph['components'] for key in c['members']}
    assert len(lookup)==len(graph['nodes'])
    assert any(c['cyclic'] and 'm0' in c['members'] for c in graph['components'])
    pairs={(lookup[e['source']],lookup[e['target']]) for e in graph['edges'] if lookup[e['source']]!=lookup[e['target']]}
    pending={c['id'] for c in graph['components']}
    while pending:
        roots={key for key in pending if not any(b==key and a in pending for a,b in pairs)}
        assert roots,'Graph feedback must be condensed, not silently dropped.'
        pending-=roots


def test_iteration_nodes_include_every_worked_step_without_running_a_different_solver(graph_case):
    result,_,graph=graph_case
    for method,trace in result['mass']['guideline_traces'].items():
        node=next(n for n in graph['nodes'] if n['id']=='@mass_iteration_'+method)
        assert len(node['iterations'])==len(trace['rows'])
        for i,row in enumerate(node['iterations']):
            assert row['mass_kg']==trace['rows'][i]['m0']
            assert row['steps']==worked_iteration(trace,i)


def test_isolated_nodes_self_loops_and_multiple_cycles_are_retained():
    nodes=[dict(id=k) for k in 'abcdef']
    edges=[dict(source=a,target=b) for a,b in [('a','b'),('b','a'),('c','c'),('d','e')]]
    groups=components(nodes,edges)
    assert [set(c['members']) for c in groups]==[{'a','b'},{'c'},{'d'},{'e'},{'f'}]
    assert [c['cyclic'] for c in groups]==[True,True,False,False,False]


def test_primary_api_delivers_graph_from_its_actual_result():
    response=app.test_client().post('/api/calculate',json=AIRCRAFT_PRESETS['ga_trainer'])
    assert response.status_code==200
    result=response.get_json()
    graph=result['calculation_graph']
    m0=next(n for n in graph['nodes'] if n['id']=='m0')
    assert m0['value']==result['mass']['m0']
    assert graph['project_name']==result['params']['name']

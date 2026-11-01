"""Graph and worked equations from the SAME result used by the UI and reports.

Strongly connected components retain numerical feedback instead of presenting
the mass/geometry coupling as an acyclic series of independent calculations.
"""
from .calc_sheet import build_sheet, worked_iteration, REF
from .report_document import TITLES


def components(nodes,edges):
    """Tarjan components, including isolated quantities, in stable node order."""
    adjacency={node['id']:[] for node in nodes}
    for edge in edges:
        adjacency[edge['source']].append(edge['target'])
    index={};low={};stack=[];on_stack=set();found=[]
    def visit(key):
        index[key]=low[key]=len(index);stack.append(key);on_stack.add(key)
        for target in adjacency[key]:
            if target not in index:
                visit(target);low[key]=min(low[key],low[target])
            elif target in on_stack:low[key]=min(low[key],index[target])
        if low[key]==index[key]:
            group=[]
            while True:
                member=stack.pop();on_stack.remove(member);group.append(member)
                if member==key:break
            found.append(group)
    for node in nodes:
        if node['id'] not in index:visit(node['id'])
    position={node['id']:i for i,node in enumerate(nodes)}
    found.sort(key=lambda group:min(position[k] for k in group))
    loops={e['source'] for e in edges if e['source']==e['target']}
    return [dict(id=f'component-{i}',members=sorted(group,key=position.get),
                 cyclic=len(group)>1 or group[0] in loops) for i,group in enumerate(found)]


def build_calculation_graph(result):
    sheet=build_sheet(result)
    nodes=[]
    for key in sheet.order:
        entry=sheet.entries[key]
        substitution=REF.sub(lambda m:sheet.num(m.group(1),wrap=True),entry.get('subst',''))
        nodes.append(dict(id=key,key=key,label=entry['label'],kind=entry['kind'],
            project=entry['project'],section=entry['section'],value=entry['value'] if entry['kind']!='table' else None,
            sym=entry['sym'],unit=entry['unit'],digits=entry['digits'],value_tex=entry['value_tex'],
            formula=entry.get('formula',''),substitution_tex=substitution,tex=entry['tex'],
            source=entry.get('source','') or sheet.sections[entry['section']].get('source',''),
            note=entry.get('note',''),deps=list(entry['deps']),consistent=entry['consistent'],
            computed=entry['computed']))
    traces=result['mass'].get('guideline_traces',{})
    for key,block in sheet.blocks.items():
        method=key.removeprefix('mass_iteration_')
        trace=traces.get(method)
        iterations=[]
        if trace:
            iterations=[dict(index=i,number=row['k'],mass_kg=row['m0'],relative=row.get('relative'),
                             steps=worked_iteration(trace,i)) for i,row in enumerate(trace['rows'])]
        nodes.append(dict(id='@'+key,key='@'+key,label=block['title'],kind='procedure',
            project=block['project'],section='p2.iteration',value=trace.get('m0') if trace else None,
            sym='m_0',unit=r'\mathrm{kg}',digits=2,value_tex='',formula='',substitution_tex='',tex='',
            deps=list(block['deps']),source='BIPOL_1, s. 4–6',note=block['note'],
            consistent=None,computed=None,iterations=iterations,
            converged=trace.get('converged') if trace else None))
    known={n['id'] for n in nodes}
    edges=[]
    for node in nodes:
        for dep in node['deps']:
            if dep not in known:raise ValueError(f"Graf obliczeń: brak zależności {dep} dla {node['id']}.")
            edges.append(dict(source=dep,target=node['id']))
    return dict(version=1,nodes=nodes,edges=edges,components=components(nodes,edges),
                sections=list(sheet.sections.values()),
                projects=dict(const='Stałe i atmosfera',**TITLES),
                project_name=result['params'].get('name','Projekt'),
                iteration=result.get('design_iteration'),
                scope='Arkusz obliczeń projektu BIPOL. Strzałka prowadzi od wielkości użytej do obliczanego wyniku. Grupy sprzężeń zachowują wzajemne zależności.')

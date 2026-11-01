"""Readable report tables without duplicating every nested diagnostic object."""
import copy


def _columns(row,names):
    return {key:row.get(key) for key in names if key in row}


def report_projection(result,method):
    """Presentation only: exact values are copied, never recomputed or rounded."""
    if method!='workbook':return result
    view=copy.deepcopy(result)
    p6=view.get('p6')
    if not p6:return view
    offer=p6['offer']
    performance_columns=['available','velocity_ms','cl','cd','mach','energy_function',
        'required_power_w','available_power_w','required_thrust_n','available_thrust_n',
        'roc_ms','gamma_deg','within_small_angle_scope','reason']
    offer['tables']=[dict(altitude_m=t['altitude_m'],prandtl=t['prandtl'],scope=t['scope'],
                         rows=[_columns(r,performance_columns) for r in t['rows']]) for t in offer['tables']]
    exact=[]
    for table in p6.get('exact_force_tables',[]):
        rows=[]
        for r in table['rows']:
            base=_columns(r,['available','velocity_ms','mach','reason'])
            base['equilibrium_count']=len(r['equilibria'])
            if r['best_rate']:
                base.update(_columns(r['best_rate'],['cl','cd','gamma_deg','roc_ms',
                    'thrust_inclination_deg','tangential_residual_n','normal_residual_n']))
            rows.append(base)
        exact.append(dict(altitude_m=table['altitude_m'],thrust_convention=table['thrust_convention'],
                          source_url=table['source_url'],force_reference=table['force_reference'],rows=rows))
    p6['exact_force_tables']=exact
    p6['report_table_note']='Tablice dokładnej równowagi podają gałąź o największym wznoszeniu oraz liczbę rozwiązań. Pełne gałęzie i diagnostyka pozostają w eksporcie JSON.'
    return view

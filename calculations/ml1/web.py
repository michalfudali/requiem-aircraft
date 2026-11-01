"""Isolated ML1 UI/API/report routes. No authentication secrets or manuscripts."""
import json
import math
from pathlib import Path

from flask import Blueprint,request,jsonify,render_template,Response

from .catalog import catalog,calculate
from .examples import example_workbook
from .charts import result_charts

blueprint=Blueprint('ml1',__name__)
SOURCE_PATH=Path(__file__).resolve().parents[2]/'data'/'ml1_sources.json'


def _payload():
    if request.content_length is not None and request.content_length>4*1024*1024:
        raise ValueError('Zeszyt ML1 przekracza limit 4 MB.')
    data=request.get_json()
    if not isinstance(data,dict):raise ValueError('Podaj obiekt JSON z metodą i parametrami.')
    count=[0]
    def check(value,depth=0):
        count[0]+=1
        if depth>30 or count[0]>100000:raise ValueError('Zbyt rozbudowany zestaw danych ML1.')
        if isinstance(value,float) and not math.isfinite(value):raise ValueError('Dane ML1 nie mogą zawierać NaN ani nieskończoności.')
        if isinstance(value,dict):
            for item in value.values():check(item,depth+1)
        elif isinstance(value,list):
            for item in value:check(item,depth+1)
    check(data)
    return data


def _run(payload):
    try:return calculate(payload.get('method'),payload.get('inputs'))
    except (TypeError,KeyError,AttributeError,IndexError,OverflowError) as error:
        raise ValueError('Sprawdź strukturę i zakres parametrów ML1: '+str(error)) from None


@blueprint.get('/ml1')
def workspace():
    return render_template('ml1.html')


@blueprint.get('/api/ml1/catalog')
def method_catalog():
    sources=json.loads(SOURCE_PATH.read_text(encoding='utf-8'))
    return jsonify(methods=catalog(),sources=sources,
                   projects=['Dane znanego samolotu','Charakterystyki płata','Charakterystyki samolotu',
                             'Lot szybowy','Zespół napędowy','Osiągi, zasięg i długotrwałość'])


@blueprint.get('/api/ml1/example/<kind>')
def example(kind):
    if kind not in ('propeller','fixed','jet','glider'):raise ValueError('Nieznany przykład ML1.')
    return jsonify(example_workbook('propeller' if kind=='fixed' else kind,'fixed' if kind=='fixed' else 'variable'))


@blueprint.post('/api/ml1/calculate')
def calculation():
    payload=_payload()
    result=_run(payload)
    # No non-standard JSON values can slip through as apparently valid results.
    serialized=json.dumps(dict(status='ok',method=payload.get('method'),inputs=payload.get('inputs'),result=result),
                          ensure_ascii=False,allow_nan=False)
    return Response(serialized,content_type='application/json; charset=utf-8')


@blueprint.post('/ml1/report')
def report():
    payload=_payload()
    result=_run(payload)
    return render_template('ml1_report.html',method=payload.get('method'),inputs=payload.get('inputs'),result=result,
                           charts=result_charts(result,payload.get('method')),
                           row_columns=lambda rows:list(dict.fromkeys(key for row in rows for key in row)))

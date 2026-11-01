"""Self-contained SVG charts for offline ML1 reports (no remote assets)."""
import html
import math


def svg_chart(title,series,x_key,y_key,x_label,y_label):
    clean=[]
    for name,rows in series:
        points=[(r.get(x_key),r.get(y_key)) for r in rows]
        points=[(x,y) for x,y in points if isinstance(x,(int,float)) and isinstance(y,(int,float)) and math.isfinite(x) and math.isfinite(y)]
        if len(points)>1:clean.append((str(name),points))
    if not clean:return ''
    all_points=[p for _,points in clean for p in points]
    xmin=min(x for x,_ in all_points);xmax=max(x for x,_ in all_points)
    ymin=min(y for _,y in all_points);ymax=max(y for _,y in all_points)
    if xmin==xmax:xmax=xmin+1
    if ymin==ymax:ymax=ymin+1
    def x(v):return 80+(v-xmin)/(xmax-xmin)*780
    def y(v):return 340-(v-ymin)/(ymax-ymin)*285
    def esc(v):return html.escape(str(v),quote=True)
    out=[f'<figure><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 400" role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>',
         f'<text x="80" y="25" font-size="17">{esc(title)}</text>']
    for i in range(6):
        xv=xmin+(xmax-xmin)*i/5;yv=ymin+(ymax-ymin)*i/5
        out.append(f'<path d="M{x(xv):.3f},55 V340 M80,{y(yv):.3f} H860" stroke="#dce3e9" fill="none"/>')
        out.append(f'<text x="{x(xv):.3f}" y="360" text-anchor="middle" font-size="12">{xv:.5g}</text>')
        out.append(f'<text x="73" y="{y(yv)+4:.3f}" text-anchor="end" font-size="12">{yv:.5g}</text>')
    colors=['#075879','#b75611','#47863d','#8a469a','#bc3131','#526cca']
    legend=[]
    for i,(name,points) in enumerate(clean):
        coords=' '.join(f'{x(a):.3f},{y(b):.3f}' for a,b in points)
        color=colors[i%len(colors)]
        out.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"/>')
        legend.append(f'<span style="color:{color}">{esc(name)}</span>')
    out.append(f'<text x="470" y="390" text-anchor="middle" font-size="13">{esc(x_label)}</text><text x="80" y="48" font-size="13">{esc(y_label)}</text></svg>')
    out.append('<figcaption class="legend">'+' · '.join(legend)+'</figcaption></figure>')
    return ''.join(out)


def result_charts(result,method):
    if not isinstance(result,dict):return []
    charts=[]
    if method=='workbook':
        charts.append(svg_chart('P3 · Biegunowa samolotu',[('P3',result['p3']['polar']['rows'])],'cl','cd','Cz','Cx'))
        charts.append(svg_chart('P4 · Biegunowe prędkości',[(f"{c['mass_kg']:g} kg / {c['altitude_m']:g} m",c['rows']) for c in result['p4']['cases']],
                                'velocity_ms','sink_ms','V [m/s]','Opadanie [m/s]'))
        if result.get('p5'):
            jet=result['p1']['propulsion']=='jet'
            charts.append(svg_chart('P5 · Charakterystyki napędu',[(f"{t['altitude_m']:g} m",t['rows']) for t in result['p5']['tables']],
                                    'velocity_ms','thrust_n' if jet else 'useful_power_w','V [m/s]','Ciąg [N]' if jet else 'Moc użyteczna [W]'))
        if result.get('p6'):
            p6=result['p6']
            charts.append(svg_chart('P6 · Wykres ofertowy',[('wmax(h)',p6['offer']['rows'])],'altitude_m','maximum_roc_ms','h [m]','wmax [m/s]'))
            series=[(s['schedule'],s['rows']) for s in p6['ranges']['schedules']]
            charts.append(svg_chart('P6 · Zasięg',series,'reference_velocity_ms','range_km','V przy masie średniej [m/s]','Zasięg [km]'))
            charts.append(svg_chart('P6 · Długotrwałość',series,'reference_velocity_ms','time_h','V przy masie średniej [m/s]','Czas [h]'))
    elif isinstance(result.get('rows'),list):
        rows=result['rows']
        if rows and 'roc_ms' in rows[0]:charts.append(svg_chart('Wznoszenie',[('w(V)',rows)],'velocity_ms','roc_ms','V [m/s]','w [m/s]'))
        elif rows and 'cd_wing' in rows[0]:charts.append(svg_chart('Biegunowa płata',[('Płat',rows)],'cl','cd_wing','Cz','Cx'))
        elif rows and 'cd' in rows[0]:charts.append(svg_chart('Biegunowa',[('Cx(Cz)',rows)],'cl','cd','Cz','Cx'))
    return [c for c in charts if c]

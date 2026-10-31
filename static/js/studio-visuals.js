/* Wizualizacje zaadaptowane z załączonego BIPOL_Studio, bez zależności od jego silnika. */
(function (root) {
'use strict';
const {format: fmt, escape: esc} = root.BipolStudio;
const COLORS = ['#168c83', '#667ed5', '#d89b45', '#bf728e', '#65a4c3'];
let chartSequence = 0;
function icon(name,size=20){const paths={plane:'M22 2 9.5 14.5M22 2l-7 20-4-9-9-4 20-7Z',grid:'M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z',target:'M20 11.1V12a8 8 0 1 1-4.8-7.3M20 4l-8 8-3-3',wing:'M3 15 21 5l-5 13-6-4-7 1Z',chart:'M3 3v18h18M6 15l5-5 4 3 6-8',layers:'m12 3 10 5-10 5L2 8l10-5Zm-10 9 10 5 10-5M2 16l10 5 10-5',shield:'M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7l-9-4Zm-4 9 3 3 5-6',file:'M14 2H5v20h14V7l-5-5Zm0 0v6h5M8 12h8M8 16h8',book:'M3 4h6c2 0 3 1 3 2 0-1 1-2 3-2h6v16h-6c-2 0-3 1-3 2 0-1-1-2-3-2H3V4Zm9 2v16',save:'M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12l4 4v12a2 2 0 0 1-2 2ZM7 3v6h10V3M7 21v-8h10v8',download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',plus:'M12 5v14M5 12h14',chevron:'m9 5 7 7-7 7',arrow:'M5 12h14m-5-5 5 5-5 5',check:'m5 12 4 4L19 6',warn:'m12 3 10 18H2L12 3Zm0 6v5m0 3v.01',close:'m6 6 12 12M6 18 18 6',upload:'M12 16V4m-5 5 5-5 5 5M4 17v4h16v-4',compare:'M8 3v18M16 3v18M3 7h10M11 17h10',settings:'M4 6h16M4 18h16M8 3v6M16 15v6M4 12h16M12 9v6',clock:'M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',external:'M15 3h6v6m0-6L10 14M11 3H3v18h18v-8',menu:'M3 6h18M3 12h18M3 18h18',glider:'M2 12h20M12 3v18m-4-2h8',drone:'M8 8h8v8H8Zm-5-5 5 5m8 8 5 5M3 21l5-5M16 8l5-5M1 3h4M19 3h4M1 21h4m14 0h4',refresh:'M20 7a9 9 0 1 0 1 9M20 2v6h-6',info:'M12 11v6m0-10v.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',trash:'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7',edit:'m16 3 5 5-12 12-6 1 1-6L16 3Z'};
 return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.plane}"/></svg>`;}
function chart({series,xLabel='',yLabel='',width=640,height=270,xMin,xMax,yMin,yMax,vertical=[],points=[],shade=false,title=''}){
 const clipId='bipol-plot-'+(++chartSequence);
 const all=series.flatMap(s=>s.data.filter(p=>p&&Number.isFinite(p[0])&&Number.isFinite(p[1])));if(!all.length)return '<p class="empty">Brak danych do wykresu.</p>';
 xMin=xMin??Math.min(...all.map(p=>p[0]));xMax=xMax??Math.max(...all.map(p=>p[0]));yMin=yMin??Math.min(0,...all.map(p=>p[1]));yMax=yMax??Math.max(...all.map(p=>p[1]))*1.1;
 if(xMax===xMin)xMax=xMin+1;if(yMax===yMin)yMax=yMin+1;
 const l=66,r=20,t=22,b=49,w=width-l-r,h=height-t-b,X=x=>l+(x-xMin)/(xMax-xMin)*w,Y=y=>t+h-(y-yMin)/(yMax-yMin)*h;
 let out=`<svg class="plot" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title||`${yLabel} w funkcji ${xLabel}`)}"><title>${esc(title||`${yLabel} w funkcji ${xLabel}`)}</title><defs><clipPath id="${clipId}"><rect x="${l}" y="${t}" width="${w}" height="${h}"/></clipPath></defs>`;
 for(let i=0;i<=5;i++){const x=xMin+(xMax-xMin)*i/5,y=yMin+(yMax-yMin)*i/5;out+=`<path d="M${X(x)} ${t}V${t+h}M${l} ${Y(y)}H${width-r}" stroke="#e7ecef" stroke-dasharray="3 4"/><text x="${X(x)}" y="${height-b+22}" text-anchor="middle" class="axis">${fmt(x,Math.abs(xMax)<3?2:0)}</text><text x="${l-10}" y="${Y(y)+4}" text-anchor="end" class="axis">${fmt(y,Math.abs(yMax)<5?2:0)}</text>`;}
 for(const v of vertical){if(v.x>=xMin&&v.x<=xMax)out+=`<path d="M${X(v.x)} ${t}V${t+h}" stroke="${v.color||'#c48b39'}" stroke-dasharray="5 4"/><text x="${Math.min(X(v.x)+5,width-100)}" y="${t+12}" class="axis" fill="${v.color||'#a16d26'}">${esc(v.label)}</text>`;}
 series.forEach((s,i)=>{let pen=false;let path='';for(const p of s.data){if(!p||!Number.isFinite(p[1])){pen=false;continue;}path+=`${pen?'L':'M'}${X(p[0]).toFixed(2)},${Y(p[1]).toFixed(2)} `;pen=true;}out+=`<path d="${path}" clip-path="url(#${clipId})" fill="none" stroke="${s.color||COLORS[i%COLORS.length]}" stroke-width="2.5" ${s.dash?'stroke-dasharray="6 5"':''}/>`;});
 for(const p of points)if(p.x>=xMin&&p.x<=xMax&&p.y>=yMin&&p.y<=yMax){const px=X(p.x),py=Y(p.y),dx=p.dx??9,dy=p.dy??-9,anc=p.anchor||(dx<0?'end':'start');out+=`<circle cx="${px}" cy="${py}" r="5" fill="${p.color||'#102d38'}" stroke="white" stroke-width="2"/><text x="${px+dx}" y="${py+dy}" text-anchor="${anc}" class="axis" fill="#102d38" paint-order="stroke" stroke="#ffffff" stroke-width="3.5" stroke-linejoin="round">${esc(p.label||'Projekt')}</text>`;}
 out+=`<text x="${l+w/2}" y="${height-6}" class="axis-label" text-anchor="middle">${esc(xLabel)}</text><text transform="translate(15 ${t+h/2}) rotate(-90)" class="axis-label" text-anchor="middle">${esc(yLabel)}</text></svg><div class="legend">${series.map((s,i)=>`<span><i style="background:${s.color||COLORS[i%COLORS.length]}"></i>${esc(s.name)}</span>`).join('')}</div>`;return out;
}
function aircraft(result, view = 'iso', orientation) {
 return root.BipolAircraftPreview.render(root.BipolAircraftPreview.model(result), view, orientation);
}
function flapEnvelope(flap) {
 if (!flap?.applicable) return `<p class="empty">${esc(flap?.note || 'Mechanizacja: nie dotyczy.')}</p>`;
 const series=[['Manewry','maneuver_polygon'],['Podmuch dodatni','gust_pos'],['Podmuch ujemny','gust_neg'],['Granica wypadkowa','composite_polygon']]
   .map(([name,key],i)=>({name,dash:i===1||i===2,data:flap[key].map(p=>[p.v_kmh,p.n])}));
 const values=series.flatMap(s=>s.data.map(p=>p[1]));
 return chart({title:'Mechanizacja do lądowania — manewry i podmuchy',xLabel:'V [km/h EAS]',yLabel:'n [—]',
   xMin:0,xMax:flap.v_f_kmh*1.05,yMin:Math.min(0,...values)*1.1,yMax:Math.max(...values)*1.1,
   series,vertical:[{x:flap.v_f_kmh,label:'VF'}]});
}
root.BipolVisuals = {icon, chart, aircraft, flapEnvelope};
})(globalThis);

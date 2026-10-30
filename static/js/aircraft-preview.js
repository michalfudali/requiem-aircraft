/* Parametryczny model poglądowy. Współrzędne w metrach: x do ogona, y w poprzek, z w górę. */
(function (root) {
  'use strict';
  const rad = Math.PI / 180;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const finite = (v, fallback) => Number.isFinite(v) ? v : fallback;
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const format = value => value.toLocaleString('pl-PL', {maximumFractionDigits:2});
  const styles = {
    fuselage:['#e8edf3', 'Kadłub'], wing:['#e5ebf0', 'Skrzydło'], tail:['#dce5ee', 'Usterzenie'],
    canopy:['#285a68', 'Osłona kabiny'], gear:['#334c57', 'Podwozie'],
    engine:['#c8d5e2', 'Silnik / gondola'], propeller:['#304b5e', 'Śmigło'],
    aileron:['#91a9c9', 'Lotki'], flap:['#cfb689', 'Klapy'], slat:['#81b2a7', 'Sloty / przedskrzydła'],
    flaperon:['#9b7ac2', 'Klapolotki']
  };
  const presets = {iso:{yaw:38, elevation:25}, top:{yaw:90, elevation:90}, side:{yaw:0, elevation:0}, front:{yaw:90, elevation:0}};
  function camera(view = 'iso', value = {}) {
    const base = presets[view] || presets.iso;
    const yaw = finite(value.yaw, base.yaw);
    return {yaw:((yaw + 180) % 360 + 360) % 360 - 180, elevation:clamp(finite(value.elevation, base.elevation), -90, 90)};
  }
  function project(point, orientation) {
    const a = orientation.yaw * rad, e = orientation.elevation * rad;
    const [x,y,z] = point, across = -Math.sin(a) * x + Math.cos(a) * y;
    return [Math.cos(a) * x + Math.sin(a) * y, Math.sin(e) * across - Math.cos(e) * z,
      Math.cos(e) * across + Math.sin(e) * z];
  }

  function model(result, options = {}) {
    const p = result.params, g = result.geometry, w = g.wing, f = g.fuselage;
    const ht = g.horizontal_tail, vt = g.vertical_tail, controls = g.control_surfaces || {};
    const L = f.length, half = w.b / 2, concept = options.proportions === 'concept';
    const kind = p.aircraft_type || 'piston_ga';
    const passenger = ['turboprop_regional','jet_transport','jet_business'].includes(kind);
    const sailplane = ['glider','motoglider'].includes(kind);
    // Concept mode is explicitly illustrative; calculated mode keeps the source dimensions.
    const ratios = passenger ? (kind==='jet_transport' ? [.085,.15] : [.08,.14]) : sailplane ? [.055,.11] : [.10,.17];
    const fw = concept ? clamp(f.diameter,L*ratios[0],L*ratios[1]) : f.diameter;
    const wingZ = ['high','braced_high'].includes(w.wing_config) ? fw * .36 : w.wing_config === 'low' ? -fw * .32 : 0;
    const faces = [], parts = new Set();
    function face(points, part, label = styles[part][1], color = styles[part][0], line = false, outward) {
      let normal;
      if (!line && outward) {
        for (let i=1;i<points.length-1;i++) {
          const u=points[i].map((v,j)=>v-points[0][j]), v=points[i+1].map((v,j)=>v-points[0][j]);
          normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
          if (Math.hypot(...normal)>1e-10) break;
        }
        const size=Math.hypot(...normal);
        if (size>1e-10) {
          const direction=normal.reduce((sum,v,i)=>sum+v*outward[i],0)<0?-1:1;
          normal=normal.map(v=>v/size*direction);
        } else return;
      }
      faces.push({points, part, label, color, line, normal}); parts.add(part);
    }
    // Closed surfaces allow inspection from below and from either side.
    function lathe(stations, center, part, label, axis = 'x', color) {
      const count=24;
      const rings = stations.map(([along, radius]) => Array.from({length:count}, (_, i) => {
        const angle = i * Math.PI * 2/count;
        return axis === 'x' ? [along, center[1] + Math.cos(angle) * radius, center[2] + Math.sin(angle) * radius]
          : [center[0] + Math.cos(angle) * radius, along, center[2] + Math.sin(angle) * radius];
      }));
      for (let j = 0; j < rings.length - 1; j++) for (let i = 0; i < count; i++) {
        const k = (i + 1) % count, angle=(i+.5)*Math.PI*2/count;
        face([rings[j][i], rings[j+1][i], rings[j+1][k], rings[j][k]], part, label, color, false,
          axis==='x'?[0,Math.cos(angle),Math.sin(angle)]:[Math.cos(angle),0,Math.sin(angle)]);
      }
      face(rings[0], part, label, color, false, axis==='x'?[-1,0,0]:[0,-1,0]);
      face(rings.at(-1), part, label, color, false, axis==='x'?[1,0,0]:[0,1,0]);
    }
    function solid(outline, offset, part, label) {
      const upper=outline.map(p=>p.map((v,i)=>v+offset[i])), lower=outline.map(p=>p.map((v,i)=>v-offset[i]));
      face(upper,part,label,undefined,false,offset);face(lower,part,label,undefined,false,offset.map(v=>-v));
      const center=outline[0].map((_,i)=>outline.reduce((sum,p)=>sum+p[i],0)/outline.length);
      for (let i=0;i<outline.length;i++) {
        const j=(i+1)%outline.length, outward=outline[i].map((v,k)=>(v+outline[j][k])/2-center[k]);
        face([upper[i],upper[j],lower[j],lower[i]],part,label,undefined,false,outward);
      }
    }
    function strut(a,b,radius,part='gear',label='Goleń podwozia') {
      const d=b.map((v,i)=>v-a[i]), length=Math.hypot(...d), axis=d.map(v=>v/length);
      const helper=Math.abs(axis[2])<.9?[0,0,1]:[1,0,0];
      let u=[axis[1]*helper[2]-axis[2]*helper[1],axis[2]*helper[0]-axis[0]*helper[2],axis[0]*helper[1]-axis[1]*helper[0]];
      const size=Math.hypot(...u);u=u.map(v=>v/size);
      const v=[axis[1]*u[2]-axis[2]*u[1],axis[2]*u[0]-axis[0]*u[2],axis[0]*u[1]-axis[1]*u[0]];
      const ring=(p,i)=>p.map((value,k)=>value+radius*(u[k]*Math.cos(i*Math.PI/4)+v[k]*Math.sin(i*Math.PI/4)));
      for (let i=0;i<8;i++) face([ring(a,i),ring(a,i+1),ring(b,i+1),ring(b,i)],part,label,undefined,false,ring([0,0,0],i+.5));
    }
    // Matching short longitudinal panels keep the cabin and skin in depth order.
    function sample(stations, x) {
      const index=stations.findIndex(station=>station[0]>=x);
      if (index<=0) return [...stations[Math.max(0,index)]];
      const a=stations[index-1], b=stations[index], t=(x-a[0])/(b[0]-a[0]);
      return a.map((value,i)=>i===0?x:value+(b[i]-value)*t);
    }
    const bodyShape = passenger
      ? [[0,.012],[.018,.20],[.045,.36],[.08,.46],[.14,.50],[.70,.50],[.78,.48],[.86,.38],[.94,.20],[1,.012]]
      : sailplane ? [[0,.015],[.04,.27],[.12,.43],[.22,.5],[.34,.43],[.45,.25],[.58,.12],[.87,.065],[1,.018]]
      : [[0,.08],[.035,.29],[.12,.44],[.25,.50],[.46,.48],[.61,.37],[.78,.21],[.94,.07],[1,.018]];
    const cockpit = sailplane ? [[.06,0,0,.35],[.12,.29,.25,.40],[.26,.30,.26,.43],[.38,0,0,.36]]
      : [[.13,0,0,.465],[.23,.33,.27,.40],[.39,.33,.28,.40],[.50,0,0,.45]];
    const windowCount=passenger?clamp(Math.round(finite(p.n_pax,16)/4),6,22):0;
    const windows=Array.from({length:windowCount},(_,i)=>.18+i*.48/Math.max(1,windowCount-1));
    const windowHalf=Math.min(.007,fw/L*.12);
    const longitudinal = [...new Set([...bodyShape.map(p=>p[0]),...cockpit.map(p=>p[0]),
      ...windows.flatMap(x=>[x-windowHalf,x+windowHalf]), ...(passenger?[.045,.075,.105]:[]),
      ...Array.from({length:41},(_,i)=>i/40)])].sort((a,b)=>a-b).filter((x,i,all)=>i===0||x-all[i-1]>1e-8);
    const body=longitudinal.map(x=>sample(bodyShape,x));
    const radialCount=24;
    const rings = body.map(([x, radius]) => Array.from({length:radialCount}, (_, i) => [x*L, Math.cos(i*Math.PI*2/radialCount)*radius*fw, Math.sin(i*Math.PI*2/radialCount)*radius*fw]));
    for (let j = 0; j < rings.length-1; j++) for (let i = 0; i < radialCount; i++) {
      const angle=(i+.5)*Math.PI*2/radialCount, x=(body[j][0]+body[j+1][0])/2;
      const glass=passenger && ((x>.045&&x<.105&&Math.sin(angle)>.5&&Math.sin(angle)<.97)
        || (windows.some(center=>Math.abs(x-center)<windowHalf)&&[1,10].includes(i)));
      face([rings[j][i], rings[j+1][i], rings[j+1][(i+1)%radialCount], rings[j][(i+1)%radialCount]], glass?'canopy':'fuselage',
        glass?(x<.12?'Oszklenie kokpitu':'Okno kabiny pasażerskiej'):undefined, undefined, false,[0,Math.cos(angle),Math.sin(angle)]);
    }
    face(rings[0], 'fuselage',undefined,undefined,false,[-1,0,0]);
    face(rings.at(-1), 'fuselage',undefined,undefined,false,[1,0,0]);
    // Only the exposed canopy roof is meshed; its base follows the fuselage skin.
    const canopy = longitudinal.filter(x=>!passenger&&x>=cockpit[0][0]&&x<=cockpit.at(-1)[0]).map(x=>sample(cockpit,x)).map(([x,width,height,base]) => Array.from({length:9}, (_,i) => {
      const angle=i*Math.PI/8;
      return [x*L,Math.cos(angle)*width*fw,(base+Math.sin(angle)*height)*fw];
    }));
    for (let j=0; j<canopy.length-1; j++) for (let i=0; i<8; i++) {
      face([canopy[j][i],canopy[j+1][i],canopy[j+1][i+1],canopy[j][i+1]],'canopy',undefined,undefined,false,[0,Math.cos((i+.5)*Math.PI/8),Math.sin((i+.5)*Math.PI/8)]);
    }

    function chord(y) {
      if (w.wing_planform === 'elliptical') return w.cr * Math.sqrt(Math.max(0, 1-(y/half)**2));
      if (w.wing_planform === 'rectangular') return w.cr;
      if (w.wing_planform === 'compound_trapezoid') {
        const split = finite(w.break_station_m, half*.4);
        return w.cr - (w.cr-w.ct)*clamp((y-split)/(half-split), 0, 1);
      }
      return w.cr + (w.ct-w.cr)*y/half;
    }
    function leading(y) {
      // The solver defines quarter-chord sweep; keep its planform convention.
      return result.balance.x_le_wing_m + y*Math.tan(w.sweep_deg*rad) + (w.cr-chord(y))*.25;
    }
    function device(source, fallbackIn, fallbackOut, ratio, enabled) {
      return {in:clamp(finite(source?.y_in_m, half*fallbackIn), 0, half),
        out:clamp(finite(source?.y_out_m, half*fallbackOut), 0, half), ratio, enabled};
    }
    const combined = controls.is_flaperon || p.flap_type === 'flaperon' || p.aileron_type === 'flaperon';
    const flap = device(controls.flaps, Math.max(.08,fw/w.b), .7,
      clamp(finite(controls.flaps?.cf_over_c, finite(p.flap_chord_ratio,.25)), .05,.5), combined || p.flap_type !== 'none');
    const aileron = device(controls.ailerons, .72, .97,
      clamp(finite(controls.ailerons?.ca_over_c, finite(p.aileron_chord_ratio,.22)), .05,.5), p.aileron_type !== 'none');
    const slatType = p.slat_type || 'none', hasSlats = slatType !== 'none';
    const slat = {in:finite(controls.slats?.y_in_m,Math.max(fw*.6,half*.08)), out:finite(controls.slats?.y_out_m,half*.94)};
    const slatName = {fixed_slot:'Slot stały', slats_auto:'Slot automatyczny', auto_slat:'Slot automatyczny', krueger:'Klapa Kruegera'}[slatType] || 'Przedskrzydło';
    const spanStations = [...new Set([0,half,flap.in,flap.out,aileron.in,aileron.out,
      ...(hasSlats ? [slat.in,slat.out] : []), finite(w.break_station_m,0),
      ...Array.from({length:11}, (_,i) => half*i/10)])].filter(y=>y>=0&&y<=half).sort((a,b)=>a-b);
    const chordStations = [...new Set([0,.04,.12,.3,.5,1-flap.ratio,1-aileron.ratio,.9,1])].sort((a,b)=>a-b);
    const contains = (device,y) => device.enabled !== false && y>device.in && y<device.out;
    function wingPoint(y, fraction, sign, side) {
      const c = chord(y), thickness = finite(w.tc_ratio,.12)*c*.5*Math.sin(Math.PI*fraction**.65);
      return [leading(y)+c*fraction,sign*y,wingZ + y*Math.tan(w.dihedral_deg*rad)+side*thickness];
    }
    for (const sign of [-1,1]) for (let i=0; i<spanStations.length-1; i++) {
      const a=spanStations[i], b=spanStations[i+1], mid=(a+b)/2;
      for (let j=0; j<chordStations.length-1; j++) {
        const u=chordStations[j], v=chordStations[j+1], fraction=(u+v)/2;
        let part='wing', label=styles.wing[1];
        if (combined && contains(flap,mid) && fraction>1-flap.ratio) { part='flaperon'; label='Klapolotka'; }
        else if (!combined && contains(flap,mid) && fraction>1-flap.ratio) { part='flap'; label=controls.flaps?.name || 'Klapa'; }
        else if (!combined && contains(aileron,mid) && fraction>1-aileron.ratio) { part='aileron'; label=controls.ailerons?.name || 'Lotka'; }
        if (hasSlats && contains(slat,mid) && fraction<.12) { part='slat'; label=slatName; }
        for (const side of [-1,1]) {
          face([wingPoint(a,u,sign,side),wingPoint(b,u,sign,side),wingPoint(b,v,sign,side),wingPoint(a,v,sign,side)],part,label,undefined,false,[0,0,side]);
          const hinge = part==='slat' ? v : u;
          if (part==='slat' || (['flap','flaperon'].includes(part) && u===1-flap.ratio) || (part==='aileron' && u===1-aileron.ratio)) {
            face([wingPoint(a,hinge,sign,side),wingPoint(b,hinge,sign,side)],part,label,'#486873',true);
          }
        }
        if (b===half) face([wingPoint(b,u,sign,-1),wingPoint(b,u,sign,1),wingPoint(b,v,sign,1),wingPoint(b,v,sign,-1)],part,label,undefined,false,[0,sign,0]);
      }
    }
    // Tail outlines use the calculated root/tip chords and span/height.
    const tailChoice=p.tail_type||p.tail_config;
    const tTail=['t','t_tail'].includes(tailChoice) || (!tailChoice && concept && ['turboprop_regional','jet_business'].includes(kind));
    const tailZ=tTail?vt.h_v*.93:fw*.1, tailRoot=finite(ht.cr_h,ht.S_h/ht.b_h*1.25), tailTip=finite(ht.ct_h,tailRoot*.6);
    const tailAc=finite(ht.x_ac_m,L-tailRoot*.65), tailX=tailAc-.25*tailRoot;
    for (const sign of [-1,1]) {
      solid([[tailX,0,tailZ],[tailAc-.25*tailTip,sign*ht.b_h/2,tailZ],
        [tailAc+.75*tailTip,sign*ht.b_h/2,tailZ],
        [tailX+tailRoot,0,tailZ]],[0,0,tailRoot*.022],'tail','Usterzenie poziome');
    }
    const finRoot=finite(vt.cr_v,tailRoot), finTip=finite(vt.ct_v,finRoot*.5);
    const finAc=finite(vt.x_ac_m,L-finRoot*.75);
    solid([[finAc-.25*finRoot,0,fw*.06],[finAc-.25*finTip,0,vt.h_v],
      [finAc+.75*finTip,0,vt.h_v],[finAc+.75*finRoot,0,fw*.06]], [0,fw*.025,0], 'tail','Usterzenie pionowe');

    if (p.engine_type && p.engine_type!=='none' && p.engine_location!=='none') {
      const jet=p.engine_type==='jet', loc=p.engine_location || 'nose';
      const diameter=finite(result.bipol_projects?.p4?.paturski_propulsion?.propeller_selection?.diameter_m, Math.min(3,w.b*.2));
      const propRadius=Math.max(.1,diameter/2,concept?fw*(passenger ? .78 : .72):0);
      const length=Math.max(fw*1.1,L*(jet ? .12 : passenger ? .105 : .10));
      let engines;
      const count=Math.max(1,Math.min(8,Math.trunc(Number(p.n_engines ?? (loc==='wing'||jet?2:1)))));
      const stations=Array.from({length:count},(_,i)=>i-(count-1)/2);
      if (loc==='wing') engines=stations.map(station=>{
        const y=station*2*Math.max(fw*.95,half*.32)/Math.max(1,count/2);
        return {x:leading(Math.abs(y))-length*.65,y,z:wingZ+Math.abs(y)*Math.tan(w.dihedral_deg*rad)-fw*(jet ? .52 : .28),pusher:false};
      });
      else if (loc==='rear' && jet) engines=stations.map(station=>({x:L*.68,y:station*fw*1.44,z:fw*.12,pusher:false}));
      else if (loc==='retractable') engines=stations.map(station=>({x:L*.51,y:station*fw*1.44,z:fw*.6+propRadius,pusher:true}));
      else if (loc==='rear') engines=stations.map(station=>({x:L*.68,y:station*fw*1.44,z:fw*.7,pusher:true}));
      else engines=stations.map(station=>({x:-fw*.06,y:station*fw*1.44,z:0,pusher:false}));
      for (const engine of engines) {
        const {x,y,z,pusher}=engine, radius=fw*(jet ? .29 : loc==='nose' ? .34 : .24);
        lathe([[x,radius*.73],[x+length*.08,radius*.92],[x+length*.22,radius],[x+length*.58,radius*.97],
          [x+length*.85,radius*.75],[x+length,radius*.24]], [0,y,z], 'engine', jet?'Gondola silnika odrzutowego':'Osłona silnika śmigłowego');
        if (loc==='wing') {
          const wingHeight=wingZ+Math.abs(y)*Math.tan(w.dihedral_deg*rad), lead=leading(Math.abs(y));
          solid([[x+length*.45,y,z+radius*.6],[lead+chord(Math.abs(y))*.18,y,wingHeight],
            [lead+chord(Math.abs(y))*.42,y,wingHeight],[x+length*.85,y,z+radius*.6]], [0,radius*.18,0], 'engine','Pylon gondoli');
        } else if (loc==='retractable' || loc==='rear') strut([x+length*.5,y,z],[x+length*.5,y,fw*.3],fw*.06,'engine','Mocowanie silnika');
        if (jet) {
          lathe([[x-.005*fw,radius*.67],[x+.01*fw,radius*.67]],[0,y,z],'engine','Wlot silnika odrzutowego','x','#243e49');
          lathe([[x+length,radius*.5],[x+length+.01*fw,radius*.5]],[0,y,z],'engine','Dysza silnika odrzutowego','x','#243e49');
        } else {
          const px=pusher?x+length+.08*fw:x-.08*fw;
          const bladeCount=kind==='turboprop_regional'?4:3;
          for (let blade=0; blade<bladeCount; blade++) {
            const angle=(blade*360/bladeCount+20)*rad;
            const propPoint=(r,offset,side)=>[px+side*fw*.012,y+Math.cos(angle)*r-Math.sin(angle)*offset,z+Math.sin(angle)*r+Math.cos(angle)*offset];
            for (const side of [-1,1]) face([propPoint(propRadius*.12,-propRadius*.045,side),propPoint(propRadius*.65,-propRadius*.075,side),
              propPoint(propRadius*.94,-propRadius*.035,side),propPoint(propRadius,propRadius*.02,side),propPoint(propRadius*.88,propRadius*.075,side),
              propPoint(propRadius*.2,propRadius*.085,side)],'propeller','Łopata śmigła',undefined,false,[side,0,0]);
          }
          const spinner=pusher?[[px-fw*.04,fw*.09],[px,fw*.1],[px+fw*.1,fw*.065],[px+fw*.15,fw*.005]]
            :[[px-fw*.15,fw*.005],[px-fw*.1,fw*.065],[px,fw*.1],[px+fw*.04,fw*.09]];
          lathe(spinner,[0,y,z],'propeller','Kołpak śmigła');
        }
      }
    }
    const track=concept?(passenger?fw*1.2:Math.min(finite(g.gear?.track,fw*1.8),fw*2.5)):finite(g.gear?.track,fw*1.3), ground=-fw*.95;
    const wheels=concept&&sailplane?[[L*.31,0,fw*.14,-fw*.46],[L*.92,0,fw*.045,-fw*.13]]
      :[[L*.47,-track/2,fw*.115,ground],[L*.47,track/2,fw*.115,ground],[L*.14,0,fw*.085,ground]];
    for (const [x,y,radius,wheelZ] of p.operating_surface==='water'?[]:wheels) {
      const rootY=p.gear_attachment==='wing'?y:y*.4;
      if(Math.abs(wheelZ+fw*.15)>.001)strut([x,rootY,-fw*.15],[x,y,wheelZ],fw*.022);
      lathe([[y-fw*.04,radius],[y+fw*.04,radius]],[x,0,wheelZ],'gear','Koło podwozia','y');
    }
    return {faces, parts:[...parts].map(id=>({id,color:styles[id][0],label:id==='slat'?slatName:styles[id][1]})),
      name:p.name || 'Samolot', area:w.S, span:w.b, proportions:concept?'concept':'calculated',
      dimensions:{length:L,diameter:fw,sourceDiameter:f.diameter},
      cg:[finite(result.balance.loading_states?.at(-1)?.xcg_m,L*.4),0,0]};
  }

  function render(aircraft, view = 'iso', orientation) {
    const angle=camera(view,orientation), a=angle.yaw*rad, e=angle.elevation*rad;
    const ca=Math.cos(a), sa=Math.sin(a), ce=Math.cos(e), se=Math.sin(e);
    const transform=([x,y,z])=>[ca*x+sa*y,se*(-sa*x+ca*y)-ce*z,ce*(-sa*x+ca*y)+se*z];
    const toward=[-sa*ce,ca*ce,se];
    const projected=aircraft.faces.map(face=>({...face, projected:face.points.map(transform)}));
    const points=projected.flatMap(face=>face.projected);
    const xs=points.map(p=>p[0]), ys=points.map(p=>p[1]);
    const minX=Math.min(...xs), maxX=Math.max(...xs), minY=Math.min(...ys), maxY=Math.max(...ys);
    const scale=Math.min(650/Math.max(.1,maxX-minX),285/Math.max(.1,maxY-minY));
    const screen=p=>[380+(p[0]-(minX+maxX)/2)*scale,205+(p[1]-(minY+maxY)/2)*scale];
    const str=points=>points.map(p=>screen(p).map(v=>v.toFixed(2)).join(',')).join(' ');
    const title=({iso:'AXONOMETRIA',top:'RZUT Z GÓRY',side:'RZUT Z BOKU',front:'RZUT Z PRZODU'})[view] || 'WIDOK SWOBODNY';
    let svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 410" role="img" aria-label="${escape(aircraft.name)} — obracany schemat samolotu" data-yaw="${angle.yaw}" data-elevation="${angle.elevation}" data-proportions="${aircraft.proportions}"><title>${escape(aircraft.name)} — schemat poglądowy</title><defs><radialGradient id="aircraft-studio-light"><stop stop-color="#ffffff"/><stop offset="1" stop-color="#f1f5f8"/></radialGradient></defs><rect width="760" height="410" fill="url(#aircraft-studio-light)"/>`;
    if(angle.elevation>0&&angle.elevation<70) svg+='<ellipse cx="385" cy="321" rx="232" ry="16" fill="#cad6df" opacity=".22"/>';
    // Painter order is recalculated for every orientation, including underside views.
    projected.forEach(face=>{face.depth=face.projected.reduce((sum,p)=>sum+p[2],0)/face.points.length+(face.line ? .0001 : 0);});
    projected.sort((a,b)=>a.depth-b.depth);
    for (const face of projected) {
      if (face.normal && face.normal.reduce((sum,n,i)=>sum+n*toward[i],0)<-1e-7) continue;
      const label=`data-aircraft-part="${face.part}"`;
      if (face.line) svg+=`<polyline ${label} points="${str(face.projected)}" fill="none" stroke="${face.color}" stroke-width="1.2"><title>${escape(face.label)}</title></polyline>`;
      else {
        const [a,b,c]=face.points, u=b.map((v,i)=>v-a[i]), v=c.map((v,i)=>v-a[i]);
        const normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
        const direction=face.normal || normal.map(n=>n/Math.max(1e-8,Math.hypot(...normal)));
        const light=.72+.28*Math.max(0,-.35*direction[0]-.20*direction[1]+.91*direction[2]);
        const rgb=face.color.match(/\w\w/g).map(hex=>Math.round(parseInt(hex,16)*light));
        const color=`rgb(${rgb.join(',')})`;
        svg+=`<polygon ${label} points="${str(face.projected)}" fill="${color}" stroke="${color}" stroke-width="${['fuselage','canopy','engine'].includes(face.part)?1:.55}" stroke-linejoin="round"><title>${escape(face.label)}</title></polygon>`;
      }
    }
    const cg=screen(project(aircraft.cg,angle));
    svg+=`<circle cx="${cg[0].toFixed(2)}" cy="${cg[1].toFixed(2)}" r="4" fill="#e1a94c" stroke="white" stroke-width="1.5"><title>Środek ciężkości</title></circle>`;
    const shortName=aircraft.name.length>54?aircraft.name.slice(0,51)+'…':aircraft.name;
    const mode=aircraft.proportions==='concept'?'KONCEPCJA · PROPORCJE UPROSZCZONE':'PROPORCJE Z OBLICZEŃ';
    svg+=`<g font-family="system-ui, sans-serif" font-size="11" fill="#607989"><text x="25" y="32">${title}</text><text x="735" y="32" text-anchor="end">${Math.round(angle.yaw)}° / ${Math.round(angle.elevation)}°</text><text x="25" y="375">${escape(shortName)}</text><text x="735" y="375" text-anchor="end">S = ${format(aircraft.area)} m² · b = ${format(aircraft.span)} m</text><text x="25" y="397">${mode}</text><text x="735" y="397" text-anchor="end">● Środek ciężkości</text></g></svg>`;
    return svg;
  }
  // The interactive mesh uses a depth buffer and interpolated normals. SVG remains
  // the portable vector export and fallback when WebGL is unavailable.
  const contexts = new WeakMap();
  function draw(canvas, aircraft, view='iso', orientation, viewport={width:760,height:410,pixelRatio:1}) {
    let state=contexts.get(canvas);
    if (state===false) return false;
    if (!state) {
      const gl=canvas.getContext('webgl',{alpha:true,antialias:true,premultipliedAlpha:false});
      if (!gl) { contexts.set(canvas,false); return false; }
      const shader=(type,source)=>{
        const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
        if (!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
        return s;
      };
      try {
        const vertex=shader(gl.VERTEX_SHADER,`
          attribute vec3 a_position, a_normal, a_color;
          uniform mat4 u_matrix;
          uniform vec3 u_eye;
          uniform bool u_point;
          uniform float u_pixel;
          varying vec3 v_normal, v_color, v_view;
          void main() {
            gl_Position=u_matrix*vec4(a_position,1.0);
            gl_PointSize=9.0*u_pixel;
            v_normal=a_normal;v_color=a_color;v_view=u_eye;
          }`);
        const fragment=shader(gl.FRAGMENT_SHADER,`
          precision mediump float;
          varying vec3 v_normal, v_color, v_view;
          uniform bool u_point;
          void main() {
            if(u_point) {
              float radius=length(gl_PointCoord-vec2(.5));
              if(radius>.5) discard;
              gl_FragColor=vec4(radius>.34?vec3(1.0):vec3(.88,.64,.28),1.0);
            } else {
              vec3 n=normalize(v_normal);
              vec3 light=normalize(vec3(-.45,.35,1.0));
              float diffuse=max(dot(n,light),0.0);
              vec3 halfLight=normalize(light+v_view);
              float specular=pow(max(dot(n,halfLight),0.0),42.0)*.14;
              gl_FragColor=vec4(v_color*(.66+.34*diffuse)+vec3(specular),1.0);
            }
          }`);
        const program=gl.createProgram();gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);
        gl.deleteShader(vertex);gl.deleteShader(fragment);
        if(!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
        state={gl,program,position:gl.getAttribLocation(program,'a_position'),normal:gl.getAttribLocation(program,'a_normal'),
          color:gl.getAttribLocation(program,'a_color'),matrix:gl.getUniformLocation(program,'u_matrix'),eye:gl.getUniformLocation(program,'u_eye'),
          point:gl.getUniformLocation(program,'u_point'),pixel:gl.getUniformLocation(program,'u_pixel'),
          triangles:gl.createBuffer(),lines:gl.createBuffer(),marker:gl.createBuffer()};
        contexts.set(canvas,state);
      } catch (_) { contexts.set(canvas,false);return false; }
    }
    const {gl}=state;
    if(gl.isContextLost()) return false;
    if(state.model!==aircraft) {
      const smooth=new Map(), triangles=[], lines=[];
      const family=part=>['wing','aileron','flap','slat','flaperon'].includes(part)?'wing':['fuselage','canopy'].includes(part)?'cabin':part;
      const key=(p,part)=>family(part)+':'+p.map(v=>v.toFixed(6)).join(',');
      const round=part=>['fuselage','canopy','engine','propeller','wing','aileron','flap','slat','flaperon'].includes(part);
      for(const face of aircraft.faces) if(!face.line&&face.normal&&round(face.part)) for(const p of face.points) {
        const id=key(p,face.part), n=smooth.get(id)||[0,0,0];
        smooth.set(id,n.map((v,i)=>v+face.normal[i]));
      }
      const append=(array,p,n,color)=>array.push(...p,...n,...color);
      for(const face of aircraft.faces) {
        const color=face.color.match(/\w\w/g).map(hex=>parseInt(hex,16)/255);
        if(face.line) {
          for(let i=0;i<face.points.length-1;i++) {
            append(lines,face.points[i],[0,0,1],color);append(lines,face.points[i+1],[0,0,1],color);
          }
        } else {
          for(let i=1;i<face.points.length-1;i++) for(const p of [face.points[0],face.points[i],face.points[i+1]]) {
            let n=(round(face.part)&&smooth.get(key(p,face.part)))||face.normal||[0,0,1];
            const size=Math.hypot(...n); n=size>1e-8?n.map(v=>v/size):face.normal||[0,0,1];
            append(triangles,p,n,color);
          }
        }
      }
      gl.bindBuffer(gl.ARRAY_BUFFER,state.triangles);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(triangles),gl.STATIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER,state.lines);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(lines),gl.STATIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER,state.marker);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([...aircraft.cg,0,0,1,1,1,1]),gl.STATIC_DRAW);
      state.model=aircraft;state.triangleCount=triangles.length/9;state.lineCount=lines.length/9;
    }
    const angle=camera(view,orientation), a=angle.yaw*rad,e=angle.elevation*rad;
    const ca=Math.cos(a),sa=Math.sin(a),ce=Math.cos(e),se=Math.sin(e);
    const across=[ca,sa,0], down=[-sa*se,ca*se,-ce], depth=[-sa*ce,ca*ce,se];
    const dot=(u,v)=>u.reduce((sum,n,i)=>sum+n*v[i],0);
    const bounds={min:[Infinity,Infinity,Infinity],max:[-Infinity,-Infinity,-Infinity]};
    for(const face of aircraft.faces) for(const p of face.points) {
      [across,down,depth].forEach((axis,i)=>{const v=dot(axis,p);bounds.min[i]=Math.min(bounds.min[i],v);bounds.max[i]=Math.max(bounds.max[i],v);});
    }
    const center=bounds.min.map((v,i)=>(v+bounds.max[i])/2), extents=bounds.max.map((v,i)=>v-bounds.min[i]);
    const fit=Math.min(650/Math.max(.1,extents[0]),285/Math.max(.1,extents[1]));
    const {width,height}=viewport,pixelRatio=Math.min(2,viewport.pixelRatio||1),meet=Math.min(width/760,height/410);
    const sx=fit*meet*2/width,sy=-fit*meet*2/height,sz=-1.8/Math.max(.1,extents[2]);
    const matrix=new Float32Array([
      across[0]*sx,down[0]*sy,depth[0]*sz,0,
      across[1]*sx,down[1]*sy,depth[1]*sz,0,
      across[2]*sx,down[2]*sy,depth[2]*sz,0,
      -center[0]*sx,-center[1]*sy,-center[2]*sz,1
    ]);
    const widthPx=Math.max(1,Math.round(width*pixelRatio)),heightPx=Math.max(1,Math.round(height*pixelRatio));
    if(canvas.width!==widthPx||canvas.height!==heightPx) {canvas.width=widthPx;canvas.height=heightPx;}
    gl.viewport(0,0,widthPx,heightPx);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    gl.useProgram(state.program);gl.uniformMatrix4fv(state.matrix,false,matrix);gl.uniform3fv(state.eye,new Float32Array(depth));
    gl.uniform1f(state.pixel,pixelRatio);gl.uniform1i(state.point,0);
    gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.disable(gl.CULL_FACE);
    const attributes=buffer=>{
      gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
      for(const [slot,offset] of [[state.position,0],[state.normal,12],[state.color,24]]) if(slot>=0) {
        gl.enableVertexAttribArray(slot);gl.vertexAttribPointer(slot,3,gl.FLOAT,false,36,offset);
      }
    };
    gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(1,1);
    attributes(state.triangles);gl.drawArrays(gl.TRIANGLES,0,state.triangleCount);gl.disable(gl.POLYGON_OFFSET_FILL);
    attributes(state.lines);gl.drawArrays(gl.LINES,0,state.lineCount);
    gl.disable(gl.DEPTH_TEST);gl.uniform1i(state.point,1);attributes(state.marker);gl.drawArrays(gl.POINTS,0,1);
    return true;
  }
  const api={model,render,camera,project,draw};
  if (typeof module==='object' && module.exports) module.exports=api;
  else root.BipolAircraftPreview=api;
})(globalThis);

/* Generic affine ballast solver. Physical coefficients are supplied by Python. */
(function(root){
  'use strict';
  const residual=(c,p)=>c.a*p[0]+c.b*p[1]+c.c;
  const tolerance=(c,p)=>64*Number.EPSILON*Math.max(1,Math.abs(c.a*p[0])+Math.abs(c.b*p[1])+Math.abs(c.c));
  function clip(polygon,c){
    const out=[];let previous=polygon.at(-1),vp=residual(c,previous),ip=vp>=-tolerance(c,previous);
    for(const current of polygon){const vc=residual(c,current),ic=vc>=-tolerance(c,current);
      if(ip!==ic){const t=Math.max(0,Math.min(1,vp/(vp-vc)));out.push([previous[0]+t*(current[0]-previous[0]),previous[1]+t*(current[1]-previous[1])]);}
      if(ic)out.push(current);previous=current;vp=vc;ip=ic;
    }return out;
  }
  function solve(model,person,station=null){
    if(!Number.isFinite(person)||person<0)throw Error('Nieprawidłowa masa osoby.');
    const [xmin,xmax]=model.station_domain_m;
    if(station!==null&&(!Number.isFinite(station)||station<xmin||station>xmax))throw Error('Położenie poza badanym zakresem.');
    const constraints=model.constraints.map(c=>({...c,c:c.c0+c.cp*person}));
    function states(w,z){return model.cases.map(c=>{
      const mass=c.base_mass_kg+model.n_crew*person+w,moment=c.base_moment_kg_m+model.n_crew*person*model.crew_arm_m+z;
      const pct=100*(moment/mass-model.lemac_m)/model.mac_m;
      const failed=constraints.filter(v=>v.state_key===c.key&&residual(v,[w,z]) < -tolerance(v,[w,z])).map(v=>v.label);
      return {key:c.key,name:c.name,mass_kg:mass,moment_kg_m:moment,xcg_m:moment/mass,xcg_mac_pct:pct,static_margin_pct:model.neutral_point_pct-pct,failed,passed:!failed.length};
    });}
    const before=states(0,0),cap=Math.min(...constraints.filter(c=>c.kind==='mass').map(c=>c.c));
    const common={person_kg:person,station_m:station,before,mass_headroom_kg:Math.max(0,cap),constraints};
    if(before.every(c=>c.passed))return {...common,status:'unnecessary',feasible:true,mass_kg:0,moment_kg_m:0,after:before,vertices:[],active_constraints:[]};
    const impossible=reason=>({...common,status:'infeasible',feasible:false,mass_kg:null,moment_kg_m:null,after:[],vertices:[],active_constraints:[],reason});
    if(cap<0)return impossible('mass');
    let polygon=station===null?[[0,0],[cap,xmin*cap],[cap,xmax*cap]]:[[0,0],[cap,station*cap]];
    for(const c of constraints){polygon=clip(polygon,c);if(!polygon.length)return impossible('balance');}
    polygon.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);let [w,z]=polygon[0];
    const position=w>0?Math.max(xmin,Math.min(xmax,z/w)):station;if(position!==null)z=w*position;
    return {...common,station_m:position,status:'feasible',feasible:true,mass_kg:w,moment_kg_m:z,after:states(w,z),vertices:polygon,
      active_constraints:constraints.filter(c=>Math.abs(residual(c,[w,z]))<=tolerance(c,[w,z]))};
  }
  if(typeof module==='object'&&module.exports)module.exports={solve};else root.BipolBallast={solve};
})(typeof globalThis!=='undefined'?globalThis:this);

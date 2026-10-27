"use strict";
/* Animated visualisation: identifiers come only from NOVENS CORE' real public catalog.
   Orbiting is aesthetic; only the ledger/history counts as real progress.
*/
(() => {
  const $ = (id) => document.getElementById(id);
  const canvas = $("universe");
  const ctx = canvas.getContext("2d", { alpha: false, desynchronized: true });
  const shell = $("shell");
  const palette = {
    github: [101,204,255],
    models: [169,136,255],
    datasets: [255,192,119],
    spaces: [99,237,187],
    skill: [255,228,130],
  };
  const labels = { github:"GitHub", models:"Modèles IA", datasets:"Datasets", spaces:"Spaces", skill:"Capacité prouvée" };
  const white = [205,245,255];
  let w = 1, h = 1, ratio = 1;
  let backgroundStars = [], dustCloud = [];
  let particles = [], previousIds = new Set(), hasLoaded = false;
  let lastSnapshot = null;
  let hovered = null;
  let projected = [];
  let pointer = { x:-999, y:-999 };
  let isPaused = false;
  let speed = 4, zoom = 1, turn = 0;
  let t = 0, lastFrame = performance.now();
  let drag = null;
  let formation = 0;
  let reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const shellWidth = () => Math.max(1,shell.clientWidth);
  function hash(s) {
    let a = 2166136261 >>> 0;
    for(let i=0;i<s.length;i++){a ^= s.charCodeAt(i);a = Math.imul(a,16777619);}
    return a>>>0;
  }
  const rand = (v) => ((v >>> 0) % 100000) / 100000;
  const clamp = (x,min,max) => Math.max(min,Math.min(max,x));
  const rgba = (v,a) => "rgba("+v.join(",")+","+a+")";
  const money = (v) => new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR",maximumFractionDigits:2}).format(Number(v)||0);
  function resize() {
    w=shellWidth(); h=Math.max(1,shell.clientHeight);
    ratio=Math.min(window.devicePixelRatio || 1,2);
    canvas.width = Math.round(w*ratio); canvas.height = Math.round(h*ratio);
    canvas.style.width = w+"px"; canvas.style.height = h+"px";
    ctx.setTransform(ratio,0,0,ratio,0,0);
    makeBackground();
  }
  function makeBackground(){
    backgroundStars=[]; dustCloud=[];
    for(let i=0;i<270;i++){
      const s=hash("b:"+i), v=hash("q:"+i);
      backgroundStars.push({x:rand(s)*w,y:rand(v)*h,
        size:.3+1.1*rand(hash("z:"+i)),phase:6.28*rand(hash("u:"+i)),
        omega:.4+1.5*rand(hash("s:"+i)),alpha:.10+.42*rand(hash("c:"+i))});
    }
    for(let i=0;i<160;i++){
      const s=hash("d:"+i);
      dustCloud.push({x:.22+rand(s)*.56,y:.21+rand(hash("y:"+i))*.56,
        a:.05+rand(hash("a:"+i))*.16,phase:rand(hash("p:"+i))*Math.PI*2});
    }
  }
  function construct(item,index) {
    const seed=hash(item.id), s2=hash("r:"+item.id);
    const catIdx=Object.keys(palette).indexOf(item.category);
    const arm=(seed%4+4)%4;
    return {
      ...item,seed,
      categoryIndex:catIdx,
      arm,spread:rand(s2),shiver:rand(hash("sh:"+item.id)),
      radius:.13+Math.sqrt(rand(hash("dist:"+item.id)))*.87,
      phase:rand(hash("phi:"+item.id))*Math.PI*2,
      size:item.category==="skill"?6:1.6+rand(hash("sz:"+item.id))*2.1,
      born:performance.now()-(hasLoaded?0:1300+index*19),
      x:0,y:0,opacity:0
    };
  }
  function applySnapshot(data) {
    if(!data || !Array.isArray(data.nodes)) return;
    lastSnapshot=data;
    let old=new Map(particles.map(x=>[x.id,x]));
    const validSkills=(Array.isArray(data.skills)?data.skills:[]).filter(item=>
      item && item.status==="validated" && typeof item.id==="string" &&
      typeof item.title==="string" && /^evidence\/[a-z0-9-]+\.json$/.test(item.proofPath || ""));
    let incoming=data.nodes.concat(validSkills.map(item=>({
      id:"skill:"+item.id,category:"skill",name:item.title,url:"./"+item.proofPath
    })));
    particles=incoming.map((item,index)=>{
      const prev=old.get(item.id);
      return prev || construct(item,index);
    });
    const count=Number(data.resourceCount || particles.length);
    $("resourceCount").textContent=count.toLocaleString("fr-FR");
    $("verifiedCount").textContent=validSkills.length.toLocaleString("fr-FR");
    const exercises=validSkills.reduce((total,item)=>total+(Array.isArray(item.resourcesTested)?item.resourcesTested.length:0),0);
    $("practiceCount").textContent=exercises.toLocaleString("fr-FR")+" exercices prouvés";
    const proofLink=$("capabilityProof");
    proofLink.hidden=validSkills.length===0;
    if(validSkills.length) {
      proofLink.href="./capacites.html";
      proofLink.textContent="✓ Voir les preuves ("+validSkills.length+")";
      proofLink.title="Consulter le journal des capacités et toutes les preuves";
    }
    $("profitCount").textContent=money(data.netProfitEuro);
    $("countGitHub").textContent=data.categoryCounts.github ?? 0;
    $("countModels").textContent=data.categoryCounts.models ?? 0;
    $("countDatasets").textContent=data.categoryCounts.datasets ?? 0;
    $("countSpaces").textContent=data.categoryCounts.spaces ?? 0;
    if(data.growth24h === null || data.growth24h === undefined) {
      $("status24h").textContent="Historique insuffisant";
      $("resourceEvolution").textContent="Comparaison 24 h en construction";
    } else {
      const delta=Number(data.growth24h);
      $("status24h").textContent=delta ? "+"+delta+" point"+(delta>1?"s":"")+" en 24 h" : "Stagnation sur 24 h";
      $("resourceEvolution").textContent=delta ? "↗ +"+delta+" ressources sur 24 h" : "→ 0 nouveau point sur 24 h";
    }
    $("latestReleve").textContent="Dernier relevé : "+String(data.asOf || "non disponible");
    $("connectionText").textContent="Catalogue cloud disponible";
    $("connectionBadge").classList.remove("offline");
    hasLoaded=true;
  }
  async function refresh(){
    try{
      const result=await fetch("./state.json?actualisation="+Date.now(),{cache:"no-store",signal:AbortSignal.timeout(10000)});
      if(!result.ok) throw new Error("Status "+result.status);
      applySnapshot(await result.json());
    }catch(e){
      $("connectionText").textContent="Données non accessibles";
      $("connectionBadge").classList.add("offline");
      if(!hasLoaded){$("resourceEvolution").textContent="En attente du moteur NOVENS CORE";}
    }
  }
  function background(){
    ctx.fillStyle="#050b17";
    ctx.fillRect(0,0,w,h);
    let bloom=ctx.createRadialGradient(w*.51,h*.50,35,w*.51,h*.50,Math.max(w,h)*.70);
    bloom.addColorStop(0,"#112742");
    bloom.addColorStop(.25,"#0a1d36");
    bloom.addColorStop(.62,"#071123");
    bloom.addColorStop(1,"#030713");
    ctx.fillStyle=bloom;ctx.fillRect(0,0,w,h);
    const haze=ctx.createRadialGradient(w*.55,h*.53,15,w*.51,h*.49,Math.min(w,h)*.57);
    haze.addColorStop(0,rgba([51,116,170],.12));
    haze.addColorStop(.45,rgba([43,57,112],.08));
    haze.addColorStop(1,rgba([10,30,51],0));
    ctx.fillStyle=haze;ctx.fillRect(0,0,w,h);
    for(const s of backgroundStars){
      const v=s.alpha*(.65+.35*Math.sin(t*s.omega+s.phase));
      ctx.fillStyle=rgba([172,216,247],v);
      ctx.beginPath();ctx.arc(s.x,s.y,s.size,0,6.283);ctx.fill();
    }
  }
  function worldCenter(){ return { x:w*.515, y:h*.50 }; }
  function getPos(p){
    const c=worldCenter();
    const r=p.radius, start=turn+p.phase*.25;
    let a, xx, yy;
    const scale=Math.min(w*.53,h*.70)*zoom;
    if(formation===0) {
      // 4 continuously rotating spiral arms.
      a=p.arm*Math.PI/2 + r*3.8 + (p.shiver-.5)*.94 + start + t*(.034/(.65+r));
      xx=Math.cos(a)*scale*(.2+r*.88);
      yy=Math.sin(a)*scale*.64*(.15+r*.85);
    } else if(formation===1) {
      // Concentric self-organising rings, still in motion.
      a=p.phase+turn+t*(.023/(.5+r));
      xx=Math.cos(a)*scale*(.16+r*.91);
      yy=Math.sin(a)*scale*.67*(.12+r*.94);
    } else {
      // Four luminous orbiting families.
      const ang=p.categoryIndex*(Math.PI/2)+turn+t*.012;
      const cx=Math.cos(ang)*scale*.47,cy=Math.sin(ang)*scale*.3;
      a=p.phase+t*(.02/(.4+r));
      xx=cx+Math.cos(a)*scale*(.08+r*.34);
      yy=cy+Math.sin(a)*scale*.62*(.08+r*.34);
    }
    const float=Math.sin(t*.75+p.phase*9.1)*2.5;
    const bob=Math.sin(t*.4+p.phase*6.4)*3.2;
    return {x:c.x+xx+float,y:c.y+yy+bob};
  }
  function drawCore(){
    const c=worldCenter();
    const pulse=.6+.4*Math.sin(t*1.4);
    let g=ctx.createRadialGradient(c.x,c.y,3,c.x,c.y,90+15*pulse);
    g.addColorStop(0,rgba([209,255,250],.42));
    g.addColorStop(.1,rgba([108,239,225],.3));
    g.addColorStop(.38,rgba([62,115,216],.12));
    g.addColorStop(1,rgba([42,64,114],0));
    ctx.fillStyle=g;ctx.beginPath();ctx.arc(c.x,c.y,107,0,6.283);ctx.fill();
    ctx.strokeStyle=rgba([108,227,227],.1+.04*pulse);
    ctx.lineWidth=1;ctx.beginPath();ctx.ellipse(c.x,c.y,36,36,0,0,6.283);ctx.stroke();
  }
  function drawGalaxyLanes(){
    const c=worldCenter(), sc=Math.min(w*.53,h*.70)*zoom;
    ctx.save();
    ctx.lineWidth=1.2;ctx.globalAlpha=.19;
    for(let arm=0;arm<4;arm++){
      ctx.beginPath();
      for(let i=0;i<=100;i++){
        const r=i/100, a=arm*Math.PI/2+r*3.8+turn+t*(.034/(.65+r));
        const x=c.x+Math.cos(a)*sc*(.2+r*.88),y=c.y+Math.sin(a)*sc*.64*(.15+r*.85);
        if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
      }
      ctx.strokeStyle=arm%2?"#667deb":"#41b5e3";ctx.stroke();
    }
    ctx.restore();
  }
  function drawConnections(items) {
    // Restrict lines to neighboring positions; they represent a visual constellation,
    // not proven model dependencies.
    ctx.lineWidth=.65;
    for(let i=0;i<items.length;i++) {
      const p=items[i];
      let match=null,closest=Infinity;
      for(let j=Math.max(0,i-16);j<i;j++){
        const q=items[j];
        if(q.category!==p.category)continue;
        const d=(q.x-p.x)**2+(q.y-p.y)**2;
        if(d<closest){closest=d;match=q;}
      }
      if(match && closest<100*100){
        ctx.strokeStyle=rgba(palette[p.category]||white,.08+.08*(Math.sin(t*1.3+i)*.5+.5));
        ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(match.x,match.y);ctx.stroke();
      }
    }
  }
  function point(p,now) {
    const age=now-p.born;
    const emerging=clamp(age/1400,0,1);
    const flicker=.73+.27*Math.sin(t*1.27+p.phase*7);
    const col=palette[p.category]||white;
    const halo=(p===hovered?25:11+p.size*3)*Math.max(.1,emerging);
    const grad=ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,halo);
    grad.addColorStop(0,rgba(col,.25*emerging));
    grad.addColorStop(.4,rgba(col,.09*emerging));
    grad.addColorStop(1,rgba(col,0));
    ctx.fillStyle=grad;ctx.beginPath();ctx.arc(p.x,p.y,halo,0,6.283);ctx.fill();
    ctx.fillStyle=rgba(col,(.7+.27*flicker)*emerging);
    ctx.beginPath();ctx.arc(p.x,p.y,(p.size+(p===hovered?2.5:0))*emerging,0,6.283);ctx.fill();
    ctx.fillStyle=rgba([220,250,255],(.18+.17*flicker)*emerging);
    ctx.beginPath();ctx.arc(p.x-.35,p.y-.45,.8*emerging,0,6.283);ctx.fill();
    if(p===hovered){
      ctx.strokeStyle=rgba(col,.72);
      ctx.lineWidth=1.1;
      ctx.beginPath();ctx.arc(p.x,p.y,12+Math.sin(t*1.8)*1.3,0,6.283);ctx.stroke();
    }
  }
  function drawFrame(now) {
    const dtSec=clamp((now-lastFrame)/1000,0,.07);
    lastFrame=now;
    if(!isPaused)t += dtSec*(speed*.65)*(reducedMotion?.45:1);
    ctx.save();ctx.setTransform(ratio,0,0,ratio,0,0);
    background();
    if(formation===0)drawGalaxyLanes();
    drawCore();
    projected=particles.map(p=>{ const pos=getPos(p);p.x=pos.x;p.y=pos.y;return p;});
    if(projected.length<=2500)drawConnections(projected);
    for(const p of projected)point(p,now);
    ctx.restore();
    requestAnimationFrame(drawFrame);
  }
  function hoverFromPointer(){
    let nearest=null,dist=20*20;
    for(const p of projected){
      const d=(p.x-pointer.x)**2+(p.y-pointer.y)**2;
      if(d<dist){dist=d;nearest=p;}
    }
    hovered=nearest;
    const tip=$("tooltip");
    if(!nearest){tip.hidden=true;return;}
    tip.hidden=false;
    $("tipType").textContent=labels[nearest.category]||nearest.category;
    $("tipName").textContent=nearest.name;
    $("tipStatus").textContent=nearest.category==="skill"
      ? "Compétence testée et validée · double-cliquer pour consulter la preuve."
      : "Ressource référencée, pas encore une compétence validée.";
    const maxX=w-285,maxY=h-160;
    tip.style.left=clamp(pointer.x+20,8,Math.max(8,maxX))+"px";
    tip.style.top=clamp(pointer.y+18,8,Math.max(8,maxY))+"px";
  }
  canvas.addEventListener("pointermove",(e)=>{
    const box=canvas.getBoundingClientRect();
    pointer={x:e.clientX-box.left,y:e.clientY-box.top};
    if(drag){
      turn+=(e.clientX-drag.lastX)*.004;
      drag.lastX=e.clientX;
      hovered=null;$("tooltip").hidden=true;
    } else hoverFromPointer();
  });
  canvas.addEventListener("pointerleave",()=>{hovered=null;$("tooltip").hidden=true;});
  canvas.addEventListener("pointerdown",(e)=>{
    drag={lastX:e.clientX,initialX:e.clientX};
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener("pointerup",(e)=>{
    const moved=drag && Math.abs(e.clientX-drag.initialX)>6;
    drag=null;
    if(!moved && hovered && hovered.url && e.detail===2)window.open(hovered.url,"_blank","noopener,noreferrer");
  });
  canvas.addEventListener("wheel",(e)=>{
    e.preventDefault();
    zoom=clamp(zoom+(e.deltaY<0?.075:-.075),.55,1.55);
  },{passive:false});
  $("pauseButton").addEventListener("click",()=>{
    isPaused=!isPaused;
    $("pauseButton").innerHTML=isPaused?"▶ <span>Reprendre</span>":"Ⅱ <span>Pause</span>";
    $("pauseButton").setAttribute("aria-pressed",String(isPaused));
  });
  $("modeButton").addEventListener("click",()=>{
    formation=(formation+1)%3;
    $("modeButton").innerHTML=["◎ <span>Spirale</span>","◎ <span>Orbites</span>","◎ <span>Amas</span>"][formation];
  });
  $("speedSlider").addEventListener("input",(e)=>{speed=Number(e.target.value);});
  $("resetButton").addEventListener("click",()=>{turn=0;zoom=1;speed=4;$("speedSlider").value="4";});
  window.addEventListener("keydown",e=>{
    if(e.code==="Space" && e.target.tagName!=="INPUT"){e.preventDefault();$("pauseButton").click();}
  });
  window.addEventListener("resize",resize);
  resize();
  requestAnimationFrame(drawFrame);
  refresh();
  window.setInterval(refresh,15000);
})();
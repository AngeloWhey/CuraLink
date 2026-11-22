"""Ground connections and restricted two-surface autorouter exchange.

Native KiCad pcbnew/WSL. Commands: prepare, import, fill. RF remains excluded.
Ground planes are never offered to the autorouter as signal routing layers.
"""
from pathlib import Path
import json, math, re, sys
import pcbnew as k
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'hardware/rev-a'; SUP=OUT/'pcb'
BOARD=OUT/'curalink-rev-a.kicad_pcb'
MM=k.FromMM; V=lambda x,y:k.VECTOR2I(MM(x),MM(y))
b=k.LoadBoard(str(BOARD)); mode=sys.argv[1]
def pos(p):
    v=p.GetPosition(); return k.ToMM(v.x),k.ToMM(v.y)
def addtrack(a,c,net,width=.15):
    if math.dist(a,c)<.001:return
    t=k.PCB_TRACK(b);t.SetStart(V(*a));t.SetEnd(V(*c));t.SetWidth(MM(width));t.SetLayer(k.F_Cu);t.SetNetCode(net);b.Add(t)
def addvia(p,net):
    via=k.PCB_VIA(b);via.SetPosition(V(*p));via.SetWidth(MM(.45));via.SetDrill(MM(.20));via.SetViaType(k.VIATYPE_THROUGH);via.SetLayerPair(k.F_Cu,k.B_Cu);via.SetNetCode(net);b.Add(via)
def intersects(a,c,bb):
    # Liang-Barsky segment / conservative axis-aligned pad bounding rectangle.
    t0,t1=0.,1.; dx,dy=c[0]-a[0],c[1]-a[1]
    for p,q in [(-dx,a[0]-bb[0]),(dx,bb[2]-a[0]),(-dy,a[1]-bb[1]),(dy,bb[3]-a[1])]:
        if abs(p)<1e-12:
            if q<0:return False
        elif p<0:t0=max(t0,q/p)
        else:t1=min(t1,q/p)
        if t0>t1:return False
    return True
if mode=='prepare':
    if list(b.GetTracks()): raise RuntimeError('Prepare requires fresh placement; existing routing would be duplicated. Rebuild explicitly before preparation.')
    pads=[p for f in b.GetFootprints() for p in f.Pads() if p.GetNumber() and p.IsOnLayer(k.F_Cu)]
    obstacles=[]
    for p in pads:
        bb=p.GetBoundingBox()
        obstacles.append((p.GetNetCode(),tuple(k.ToMM(t) for t in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()])))
    created=[]; misses=[]; used=[]; ep=[]
    gnd=next(n.GetNetCode() for n in b.GetNetsByNetcode().values() if n.GetNetname()=='GND')
    for p in pads:
        if p.GetNetCode()!=gnd:continue
        xy=pos(p); f=p.GetParentFootprint(); ref=f.GetReference(); size=p.GetSize()
        thermal=(ref=='U401' and p.GetNumber()=='49') or (ref in ['U501','U502','U511'] and k.ToMM(size.x)>.65 and k.ToMM(size.y)>.9)
        if thermal:
            candidates=[xy] if ref!='U401' else [(xy[0]+dx,xy[1]+dy) for dx in [-1.2,1.2] for dy in [-1.2,1.2]]
            for vv in candidates: addvia(vv,gnd);used.append(vv);ep.append({'ref':ref,'position_mm':vv})
            created.append({'ref':ref,'pin':p.GetNumber(),'method':'EP vias — cap/fill/assembly process OPEN'})
            continue
        found=None
        for radius in [.55,.75,1.,1.3,1.7,2.2,2.8]:
            for angle in range(0,360,45):
                vv=(xy[0]+radius*math.cos(math.radians(angle)),xy[1]+radius*math.sin(math.radians(angle)))
                if not (.6<vv[0]<79.4 and .6<vv[1]<73.4):continue
                if vv[0]>73.5 and vv[1]<6.5:continue
                if any(math.dist(vv,v)<.7 for v in used):continue
                clear=True
                for net,bb in obstacles:
                    if net==gnd:continue
                    ext=(bb[0]-.18,bb[1]-.18,bb[2]+.18,bb[3]+.18)
                    if intersects(xy,vv,ext) or (bb[0]-.33<=vv[0]<=bb[2]+.33 and bb[1]-.33<=vv[1]<=bb[3]+.33): clear=False;break
                if clear:found=vv;break
            if found:break
        if found:
            addtrack(xy,found,gnd,.15);addvia(found,gnd);used.append(found)
            created.append({'ref':ref,'pin':p.GetNumber(),'via_mm':found,'trace_mm':math.dist(xy,found)})
        else:misses.append({'ref':ref,'pin':p.GetNumber(),'position_mm':xy})
    # Additional stitching around board edge, away from the antenna corner.
    for x in range(2,79,8):
        for y in [2,72]:
            vv=(float(x),float(y))
            if x>73.5 and y<6.5:continue
            if any(net!=gnd and bb[0]-.33<x<bb[2]+.33 and bb[1]-.33<y<bb[3]+.33 for net,bb in obstacles):continue
            if any(math.dist(vv,v)<.7 for v in used):continue
            addvia(vv,gnd);used.append(vv)
    k.SaveBoard(str(BOARD),b)
    (SUP/'ground-connections.json').write_text(json.dumps({'date':'2026-10-02','connected_pad_groups':created,'unresolved_ground_pads':misses,'EP_vias':ep,'EP_assembly_gate':'Filled/capped or independently qualified via/paste process required before manufacture.'},indent=2)+'\n')
    # Export a temporary two-layer view only. Restore native four-layer board
    # by loading it again for SES import; internal reference zones are retained.
    for zone in list(b.Zones()): b.Remove(zone)
    b.SetCopperLayerCount(2)
    dsn=SUP/'candidate-routing.dsn'
    if not k.ExportSpecctraDSN(b,str(dsn)):raise RuntimeError('DSN export failed')
    raw=dsn.read_text()
    # The exported default class is edited structurally, preserving every net
    # and geometry. Ignored classes stay as airwires in the editable board.
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',raw)
    def parse(i):
        if tokens[i]!='(':return tokens[i],i+1
        out=[];i+=1
        while tokens[i]!=')':
            item,i=parse(i);out.append(item)
        return out,i+1
    tree,_=parse(0)
    def routing_rules(t):
        if not isinstance(t,list): return
        if t and t[0]=='rule':
            for r in t[1:]:
                if isinstance(r,list) and r[0]=='width': r[1]='150'
                elif isinstance(r,list) and r[0]=='clearance' and len(r)==2: r[1]='100'
        for child in t: routing_rules(child)
    routing_rules(tree)
    structure=next(x for x in tree if isinstance(x,list) and x[0]=='structure')
    via_rule=next(x for x in structure if isinstance(x,list) and x[0]=='via')
    via_rule[1:]=sorted(via_rule[1:],key=lambda t:'450:200' not in t)
    network=next(x for x in tree if isinstance(x,list) and x[0]=='network')
    rf={'MCU_RF','RF_50OHM','RF_COAX','ANT_T_IN','ANT_T_MID','ANT_FEED'}
    for cl in network:
        if isinstance(cl,list) and cl[0]=='class':
            cl[:]=[t for i,t in enumerate(cl) if i<2 or isinstance(t,list) or t.strip('"') not in rf|{'GND'}]
    network.append(['class','"Ground"','"GND"',['rule',['width','150'],['clearance','100']]])
    network.append(['class','"ReservedRF"']+['"'+n+'"' for n in sorted(rf)]+[['rule',['width','150'],['clearance','100']]])
    def dump(t):return '('+' '.join(map(dump,t))+')' if isinstance(t,list) else t
    dsn.write_text(dump(tree)+'\n')
    print(json.dumps({'ground_pad_groups':len(created),'unresolved_ground_pads':len(misses),'DSN':str(dsn),'surface_routing_only':True}),flush=True)
elif mode=='import':
    ses=SUP/'candidate-routing.ses'
    if not k.ImportSpecctraSES(b,str(ses)):raise RuntimeError('SES import failed')
    k.SaveBoard(str(BOARD),b)
    print('SES imported; internal planes preserved')
elif mode=='fill':
    b.BuildConnectivity();filler=k.ZONE_FILLER(b);filler.Fill(b.Zones());k.SaveBoard(str(BOARD),b)
    print('Ground planes filled')
else:raise ValueError(mode)

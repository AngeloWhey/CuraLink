"""Read-only physical review of the actual CuraLink KiCad PCB.

Run with Ubuntu-24.04's native KiCad Python after SES import and zone fill:
  python3 review_sensitive_geometry.py --board ../curalink-rev-a.kicad_pcb

This is a geometric screening tool, not a capacitance extractor or SI pass.
It never fills zones, edits footprints, routes traces or saves the board.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import csv
import hashlib
import json
import math
import re
import pcbnew

HERE=Path(__file__).resolve().parent
REV=HERE.parent
ROOT=REV.parents[1]
NM=1_000_000
SURFACES=(pcbnew.F_Cu,pcbnew.B_Cu)
EPS=1e-10

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def xy(p):
    return (p.x/NM,p.y/NM)

def uid(item):
    return item.m_Uuid.AsString()

def vec(a,b):
    return (b[0]-a[0],b[1]-a[1])

def dot(a,b):
    return a[0]*b[0]+a[1]*b[1]

def cross(a,b):
    return a[0]*b[1]-a[1]*b[0]

def dist(a,b):
    return math.hypot(a[0]-b[0],a[1]-b[1])

def project(p,a,b):
    ab=vec(a,b);l2=dot(ab,ab)
    t=min(1,max(0,dot(vec(a,p),ab)/l2)) if l2>EPS else 0
    q=(a[0]+t*ab[0],a[1]+t*ab[1])
    return dist(p,q),q

def segdistance(a,b,c,d):
    ab=vec(a,b);cd=vec(c,d);den=cross(ab,cd)
    if abs(den)>EPS:
        ac=vec(a,c);t=cross(ac,cd)/den;u=cross(ac,ab)/den
        if -EPS<=t<=1+EPS and -EPS<=u<=1+EPS:
            p=(a[0]+t*ab[0],a[1]+t*ab[1])
            return 0,p,p
    choices=[]
    for p in (a,b):
        distance,q=project(p,c,d);choices.append((distance,p,q))
    for p in (c,d):
        distance,q=project(p,a,b);choices.append((distance,q,p))
    return min(choices,key=lambda r:r[0])

def inside(p,poly):
    hit=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>p[1])!=(b[1]>p[1]):
            x=a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if p[0]<x:
                hit=not hit
    return hit

def edges(g):
    if g["kind"]=="track":
        return [(g["a"],g["b"])]
    if g["kind"]=="via":
        return [(g["a"],g["a"])]
    return list(zip(g["vertices"],g["vertices"][1:]+g["vertices"][:1]))

def representative(g):
    return g["a"] if g["kind"]!="pad" else g["vertices"][0]

def gap(a,b):
    if a["kind"]=="pad" and inside(representative(b),a["vertices"]):
        p=representative(b);return 0,p,p
    if b["kind"]=="pad" and inside(representative(a),b["vertices"]):
        p=representative(a);return 0,p,p
    best=(float("inf"),(0,0),(0,0))
    for aa,ab in edges(a):
        for ba,bb in edges(b):
            r=segdistance(aa,ab,ba,bb)
            if r[0]<best[0]:best=r
            if best[0]<=EPS:break
        if best[0]<=EPS:break
    return max(0,best[0]-a.get("radius",0)-b.get("radius",0)),best[1],best[2]

def make_bbox(g):
    pts=g["vertices"] if g["kind"]=="pad" else [g["a"],g.get("b",g["a"])]
    r=g.get("radius",0)
    return (min(p[0]for p in pts)-r,min(p[1]for p in pts)-r,
            max(p[0]for p in pts)+r,max(p[1]for p in pts)+r)

def bbox_gap(a,b):
    return math.hypot(max(0,a[0]-b[2],b[0]-a[2]),max(0,a[1]-b[3],b[1]-a[3]))

def brief(g):
    keys=("kind","net","layer","uuid","ref","pin","arc_sample_index")
    return {k:g[k]for k in keys if k in g}

def nearest(source,aggressors):
    result=None;best=float("inf")
    for a in source:
        for b in aggressors:
            if a["layer"]!=b["layer"] or a["net"]==b["net"]:continue
            if bbox_gap(a["bbox"],b["bbox"])>best:continue
            d,pa,pb=gap(a,b)
            if d<best:
                best=d
                result={"clearance_lower_bound_mm":round(d,6),"source":brief(a),"aggressor":brief(b),
                        "source_nearest_xy_mm":[round(x,6)for x in pa],
                        "aggressor_nearest_xy_mm":[round(x,6)for x in pb]}
    return result

def category(net):
    if re.fullmatch(r"(?:AFE_OUT|ADC_IN)_[1-8]",net):return "late-output"
    if net.startswith(("MCU_RF","RF_","ANT_")):return "RF"
    if net.startswith(("HSE_","LSE_","SWCLK","SWDIO","SWO","UART_")) or net in {"ACQ_MARKER","GPIO_TEST","NRST","BOOT0"}:return "digital-clock-debug"
    if net.startswith(("WPT_","SYS_","DVDD","AVDD","CTRL_","VDDHPA","VCAP","SW_GATE","PCM_COMMON","PMOS_COMMON")) or net in {"PACK+","BAT_RUN","BAT_CHG","CELLP","CELLN","ANALOG_DISCHARGE","DIGITAL_DISCHARGE","RUN_ENABLE","NOT_RUN","CHG_IN","CHG_SYS","BENCH_CHG_5V"}:return "power-control"
    if net=="REF_PRE" or re.fullmatch(r"CH[1-8]_(?:PRE|LP1_OUT)",net):return "intermediate-analog"
    return None

def clip_region(a,b,box):
    # Liang-Barsky clipping, including traces crossing a box with neither end in it.
    dx=b[0]-a[0];dy=b[1]-a[1];lo=0;hi=1
    for p,q in [(-dx,a[0]-box[0]),(dx,box[2]-a[0]),(-dy,a[1]-box[1]),(dy,box[3]-a[1])]:
        if abs(p)<EPS:
            if q<0:return None
        else:
            r=q/p
            if p<0:lo=max(lo,r)
            else:hi=min(hi,r)
            if lo>hi:return None
    return {"entry_xy_mm":[round(a[0]+lo*dx,6),round(a[1]+lo*dy,6)],
            "centerline_length_inside_mm":round((hi-lo)*math.hypot(dx,dy),6)}

def parallel_pairs(source,aggressors):
    found=[]
    for a in source:
        if a["kind"]!="track":continue
        va=vec(a["a"],a["b"]);la=math.hypot(*va)
        if la<.5:continue
        axis=(va[0]/la,va[1]/la)
        for b in aggressors:
            if b["kind"]!="track" or a["layer"]!=b["layer"] or a["net"]==b["net"]:continue
            if bbox_gap(a["bbox"],b["bbox"])>1:continue
            vb=vec(b["a"],b["b"]);lb=math.hypot(*vb)
            if lb<.5:continue
            cosine=min(1,abs(dot(va,vb)/(la*lb)))
            if cosine<math.cos(math.radians(10)):continue
            projections=[dot(vec(a["a"],p),axis)for p in (b["a"],b["b"])]
            overlap=min(la,max(projections))-max(0,min(projections))
            if overlap<1:continue
            d,pa,pb=gap(a,b)
            if d>1:continue
            found.append({"source":brief(a),"aggressor":brief(b),"clearance_lower_bound_mm":round(d,6),
                          "projected_overlap_mm":round(overlap,6),"acute_angle_deg":round(math.degrees(math.acos(cosine)),3),
                          "location_xy_mm":[round((pa[i]+pb[i])/2,6)for i in (0,1)]})
    return sorted(found,key=lambda r:(r["clearance_lower_bound_mm"],-r["projected_overlap_mm"]))

def track_pieces(item):
    a=xy(item.GetStart());b=xy(item.GetEnd());radius=item.GetWidth()/NM/2
    base={"kind":"track","net":item.GetNetname(),"layer":pcbnew.LayerName(item.GetLayer()),"uuid":uid(item),"radius":radius}
    if not isinstance(item,pcbnew.PCB_ARC):return [{**base,"a":a,"b":b}]
    # The router normally produces straight segments. For arcs, use <=0.05 mm
    # chords and expand their copper radius by a conservative 0.01 mm error.
    center=xy(item.GetCenter());mid=xy(item.GetMid());r=dist(a,center)
    start=math.atan2(a[1]-center[1],a[0]-center[0])
    end=math.atan2(b[1]-center[1],b[0]-center[0]);ma=math.atan2(mid[1]-center[1],mid[0]-center[0])
    ccw=(end-start)%(2*math.pi);midccw=(ma-start)%(2*math.pi)
    angle=ccw if midccw<=ccw+1e-8 else ccw-2*math.pi
    n=max(1,math.ceil(abs(angle)*r/.05))
    pts=[(center[0]+r*math.cos(start+i*angle/n),center[1]+r*math.sin(start+i*angle/n))for i in range(n+1)]
    return [{**base,"a":aa,"b":bb,"radius":radius+.01,"arc_sample_index":i}for i,(aa,bb)in enumerate(zip(pts,pts[1:]))]

def collect(board):
    objects=[];native=[];vias=[]
    for item in board.GetTracks():
        if isinstance(item,pcbnew.PCB_VIA):
            pos=xy(item.GetPosition());vias.append(item)
            for layer in SURFACES:
                if item.IsOnLayer(layer):objects.append({"kind":"via","net":item.GetNetname(),"layer":pcbnew.LayerName(layer),"uuid":uid(item),"a":pos,"radius":item.GetWidth()/NM/2})
        else:
            native.append(item)
            if item.GetLayer()in SURFACES:objects.extend(track_pieces(item))
    pads={}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH or not p.GetNumber():continue
            pads[(fp.GetReference(),p.GetNumber())]=p
            if not category(p.GetNetname()) and not re.fullmatch(r"(?:CH[1-8]|REF)_PLUS",p.GetNetname()):continue
            for layer in SURFACES:
                if not p.IsOnLayer(layer):continue
                poly=p.GetEffectivePolygon(layer,pcbnew.ERROR_OUTSIDE)
                for index in range(poly.OutlineCount()):
                    chain=poly.Outline(index)
                    vertices=[xy(chain.CPoint(i))for i in range(chain.PointCount())]
                    if len(vertices)<3:continue
                    objects.append({"kind":"pad","net":p.GetNetname(),"layer":pcbnew.LayerName(layer),"uuid":uid(p),"ref":fp.GetReference(),"pin":p.GetNumber(),"vertices":vertices})
    for obj in objects:obj["bbox"]=make_bbox(obj)
    return objects,native,vias,pads

def plane_review(board,native,highz):
    zones=[];checks=[]
    for z in board.Zones():
        for layer in z.GetLayerSet().Seq():
            if not pcbnew.IsCopperLayer(layer)or z.GetIsRuleArea():continue
            row={"net":z.GetNetname(),"layer":pcbnew.LayerName(layer),"uuid":uid(z),
                 "outline_count":z.Outline().OutlineCount(),"filled":z.HasFilledPolysForLayer(layer)}
            if row["filled"]:
                poly=z.GetFilledPolysList(layer)
                row.update({"filled_outline_island_count":poly.OutlineCount(),"filled_hole_count":sum(poly.HoleCount(i)for i in range(poly.OutlineCount())),"filled_area_mm2":round(poly.Area()/1e12,6)})
            zones.append(row)
    for layer in (pcbnew.In1_Cu,pcbnew.In2_Cu):
        name=pcbnew.LayerName(layer)
        rows=[r for r in zones if r["layer"]==name]
        filled=[z.GetFilledPolysList(layer)for z in board.Zones()if z.IsOnLayer(layer)and not z.GetIsRuleArea()and z.GetNetname()=="GND"and z.HasFilledPolysForLayer(layer)]
        gaps=[];tested=0
        if filled:
            for item in native:
                if item.GetNetname()not in highz or item.GetLayer()not in SURFACES:continue
                for part in track_pieces(item):
                    length=dist(part["a"],part["b"]);n=max(1,math.ceil(length/.5))
                    for i in range(n):
                        t=(i+.5)/n;p=(part["a"][0]+t*(part["b"][0]-part["a"][0]),part["a"][1]+t*(part["b"][1]-part["a"][1]))
                        tested+=1
                        v=pcbnew.VECTOR2I(round(p[0]*NM),round(p[1]*NM))
                        if not any(poly.Contains(v)for poly in filled):gaps.append({"net":item.GetNetname(),"xy_mm":[round(x,6)for x in p],"track_uuid":uid(item)})
        checks.append({"layer":name,"zone_count":len(rows),"all_declared_zones_GND":bool(rows)and all(r["net"]=="GND"for r in rows),
                       "signal_track_count":sum(item.GetLayer()==layer for item in native),
                       "filled_GND_available":bool(filled),"highz_projection_sample_count":tested,
                       "highz_projection_missing_GND_count":len(gaps),"missing_samples":gaps,
                       "continuity_status":"NOT CHECKED: no saved fill"if not filled else "Sampled projection coverage only; island counts and holes reported, not a complete return-current proof"})
    return {"zones":zones,"inner_layer_checks":checks,
            "limitations":"No zone fill is performed. Filled GND islands/holes and 0.5 mm maximum-step samples beneath high-Z traces are reported. Via antipads and intentional clearances can create local missing samples; inspect coordinates. Neither full return-path connectivity nor return impedance is inferred from these counts."}

def bypass_review(groups,pads,vias):
    rows=[]
    groundvias=[v for v in vias if v.GetNetname()=="GND"]
    for c in groups["components"]:
        ref=c["ref"]
        if not ref.startswith("C")or "local_proximity"not in c:continue
        host=c["local_proximity"];cp=pads.get((ref,"1"));hp=pads.get((host["near_ref"],host["near_pin"]))
        if cp is None or hp is None:
            rows.append({"ref":ref,"host_ref":host["near_ref"],"host_pin":host["near_pin"],"status":"MISSING PAD"});continue
        center=dist(xy(cp.GetPosition()),xy(hp.GetPosition()))
        returnpad=pads.get((ref,"2"));ret=returnpad.GetNetname()if returnpad else None
        gv=min(groundvias,key=lambda v:dist(xy(returnpad.GetPosition()),xy(v.GetPosition())))if returnpad and ret=="GND"and groundvias else None
        grounddist=dist(xy(returnpad.GetPosition()),xy(gv.GetPosition()))if gv else None
        rows.append({"ref":ref,"host_ref":host["near_ref"],"host_pin":host["near_pin"],"populate":c["populate"],
                     "capacitor_net":cp.GetNetname(),"host_net":hp.GetNetname(),"same_net":cp.GetNetname()==hp.GetNetname(),
                     "pad_center_distance_mm":round(center,6),"over_2mm_placement_objective":center>2,
                     "capacitor_xy_mm":[round(x,6)for x in xy(cp.GetPosition())],"host_xy_mm":[round(x,6)for x in xy(hp.GetPosition())],
                     "capacitor_side":pcbnew.LayerName(cp.GetParentFootprint().GetLayer()),
                     "host_side":pcbnew.LayerName(hp.GetParentFootprint().GetLayer()),"return_net":ret,
                     "nearest_GND_via_distance_mm":round(grounddist,6)if grounddist is not None else None,
                     "nearest_GND_via_xy_mm":[round(x,6)for x in xy(gv.GetPosition())]if gv else None,
                     "purpose":host["purpose"],"status":"PLACEMENT FLAG"if center>2 else "GEOMETRY RECORDED"})
    return rows

def write_csv(path,rows,fields):
    with path.open("w",newline="")as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");writer.writeheader();writer.writerows(rows)

def write_md(report,path):
    lines=["# Actual PCB sensitive geometry review", "",f"Checked {report['checked_local']} with KiCad {report['kicad_version']}.","",
           f"Board: `{report['board']}`. SHA-256: `{report['board_sha256']}`.","",
           f"**{report['status']}** The geometry is read-only evidence, not a signal-integrity or fabrication pass.","",
           "## High-impedance input geometry", "", "| Net | Surface centerline length (mm) | Vias | Closest late-output copper lower bound (mm) | Location on victim (mm) |",
           "|---|---:|---:|---:|---|"]
    for row in report["highz_nets"]:
        near=row["nearest_by_category"].get("late-output")
        lines.append(f"| {row['net']} | {row['surface_length_mm']:.3f} | {row['via_count']} | {near['clearance_lower_bound_mm'] if near else 'no same-layer geometry'} | {near['source_nearest_xy_mm'] if near else '—'} |")
    lines += ["",f"Same-layer parallel review triggers: **{len(report['parallel_review_flags'])}** (projected overlap ≥1 mm, clearance ≤1 mm, acute angle ≤10°). These are screening thresholds, not coupling limits.","",
              "| Victim | Aggressor | Layer | Clearance lower bound (mm) | Projected overlap (mm) | Location (mm) |","|---|---|---|---:|---:|---|"]
    for r in report["parallel_review_flags"][:30]:
        lines.append(f"| {r['source']['net']} | {r['aggressor']['net']} | {r['source']['layer']} | {r['clearance_lower_bound_mm']:.3f} | {r['projected_overlap_mm']:.3f} | {r['location_xy_mm']} |")
    lines += ["",f"Late-output items entering the early-input/reference boxes: **{len(report['late_outputs_in_sensitive_regions'])}**. Inspect the exact nets, item UUIDs and coordinates in the JSON; the region is a floorplan heuristic.","",
              "## Power local bypass placement", "", "| Capacitor | Host pin | Pad-center separation (mm) | Nearest GND via (mm) | Flag |", "|---|---|---:|---:|---|"]
    for r in report["power_bypass_placement"]:
        if r.get("over_2mm_placement_objective")or r["status"]=="MISSING PAD":
            lines.append(f"| {r['ref']} | {r['host_ref']}:{r['host_pin']} | {r.get('pad_center_distance_mm','missing')} | {r.get('nearest_GND_via_distance_mm','—')} | {r['status']} |")
    lines += ["","The capacitor distance is pad-center Euclidean distance, a placement lower bound on routed path length. A short distance does not prove a short loop or low inductance. Opposite-side placement and ground-via distance are reported separately. C505 is coupled to ISET through R505, so its direct-net mismatch is intentional; optional PCM C530 returns to CELLN, not GND.","",
              "## Inner ground layers", "", "| Layer | GND-only declared zones | Inner tracks | Saved GND fill | Missing ground projection samples |", "|---|---|---:|---|---:|"]
    for r in report["planes"]["inner_layer_checks"]:
        lines.append(f"| {r['layer']} | {r['all_declared_zones_GND']} | {r['signal_track_count']} | {r['filled_GND_available']} | {r['highz_projection_missing_GND_count']} / {r['highz_projection_sample_count']} |")
    lines += ["",report["planes"]["limitations"],"","## Priorities and limitations",""]
    lines += ["- "+r for r in report["priority_findings"]]
    lines += ["", "Track/via copper is treated as finite-width capsules/circles. Pad outlines come from KiCad's ERROR_OUTSIDE polygon, so reported separations are conservative geometric lower bounds; no dielectric, guard effectiveness, capacitance, drive waveform or noise spectrum is extracted. Arcs, if present, use short chords with an additional 0.01 mm conservative radius allowance. Same-layer checks do not model cross-layer coupling. Unrouted pads do not establish route isolation.","",
              "The existing shared VMID crosstalk and offset-recovery results remain circuit limitations regardless of physical separation. RF impedance, antenna efficiency, battery safety and complete return-current topology require their separate verification. The board and canonical sources were not modified."]
    path.write_text("\n".join(lines)+"\n")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board",type=Path,default=REV/"curalink-rev-a.kicad_pcb")
    parser.add_argument("--output-dir",type=Path,default=HERE)
    parser.add_argument("--stage",default="post-SES inspection")
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    before=sha(args.board);board=pcbnew.LoadBoard(str(args.board))
    objects,native,vias,pads=collect(board)
    highz=[f"CH{i}_PLUS"for i in range(1,9)]+["REF_PLUS"]
    cats=("late-output","digital-clock-debug","RF","power-control","intermediate-analog")
    aggr={c:[g for g in objects if category(g["net"])==c]for c in cats}
    sensitive=[g for g in objects if g["net"]in highz]
    rows=[]
    for net in highz:
        tracks=[t for t in native if t.GetNetname()==net]
        source=[g for g in sensitive if g["net"]==net]
        rows.append({"net":net,"surface_length_mm":round(sum(t.GetLength()/NM for t in tracks if t.GetLayer()in SURFACES),6),
                     "by_layer_length_mm":{pcbnew.LayerName(layer):round(sum(t.GetLength()/NM for t in tracks if t.GetLayer()==layer),6)for layer in board.GetEnabledLayers().Seq()if pcbnew.IsCopperLayer(layer)},
                     "surface_track_segment_count":sum(t.GetLayer()in SURFACES for t in tracks),
                     "via_count":sum(v.GetNetname()==net for v in vias),
                     "surface_Cu_pad_count":sum(g["kind"]=="pad"for g in source),
                     "nearest_by_category":{c:nearest(source,aggr[c])for c in cats}})
    parallel=parallel_pairs(sensitive,[g for c in ("late-output","digital-clock-debug","RF","power-control")for g in aggr[c]])
    regions={"early-input-banks":[0,0,22,46],"shared-reference":[0,44,22,50]}
    incursion=[]
    for g in aggr["late-output"]:
        for name,box in regions.items():
            if g["kind"]=="track":
                crossing=clip_region(g["a"],g["b"],box)
                if crossing and crossing["centerline_length_inside_mm"]>0:incursion.append({**brief(g),"region":name,**crossing})
            elif bbox_gap(g["bbox"],box)<=EPS:
                incursion.append({**brief(g),"region":name,"copper_bounds_mm":list(g["bbox"]),"note":"Copper envelope touches floorplan region; inspect actual pad/via boundary"})
    groups=json.loads((HERE/"power-placement-groups.json").read_text())
    bypass=bypass_review(groups,pads,vias)
    planes=plane_review(board,native,set(highz))
    findings=[]
    if incursion:findings.append(f"P1 review: {len(incursion)} late-output surface items enter an early-input/reference floorplan box; reroute or inspect clearance/guarding before physical SI claims.")
    if parallel:findings.append(f"P1 review: {len(parallel)} same-layer parallel runs meet the declared proximity screen; late-output/input runs are especially important because signal amplitude is amplified downstream.")
    badcaps=[r for r in bypass if r.get("over_2mm_placement_objective")]
    if badcaps:findings.append("P2 placement: bypass/filter capacitors exceed the 2 mm host-pad placement objective: "+", ".join(r["ref"]for r in badcaps)+". Inspect loop and host purpose; this is not a routed-length measurement.")
    innertracks=sum(r["signal_track_count"]for r in planes["inner_layer_checks"])
    if innertracks:findings.append(f"P1 plane rule: {innertracks} tracks exist on In1/In2; these layers were reserved for continuous GND only.")
    for r in planes["inner_layer_checks"]:
        if not r["all_declared_zones_GND"]:findings.append(f"P1 plane rule: {r['layer']} lacks exclusively GND plane declarations.")
        if not r["filled_GND_available"]:findings.append(f"P1 qualification: {r['layer']} has no saved ground fill, so ground projection coverage cannot be checked.")
        elif r["highz_projection_missing_GND_count"]:findings.append(f"P2 return-path review: {r['layer']} lacks GND at {r['highz_projection_missing_GND_count']} sampled high-Z projections; review holes/antipads and any long unreferenced run.")
    findings.append("Shared VMID coupling is already demonstrated in the circuit model; physical routing cannot by itself close that issue.")
    if not native:findings.insert(0,"No actual trace routing was present; placement-only geometry cannot be treated as routed-board evidence.")
    after=sha(args.board);assert before==after,"Board changed while review was running; rerun on a stable post-import artifact"
    report={"checked_local":datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds"),"kicad_version":pcbnew.GetBuildVersion(),
            "stage":args.stage,"status":"GEOMETRY SCREENING — review findings remain; no SI pass claimed",
            "board":str(args.board),"board_sha256":before,"board_not_modified":True,
            "power_group_source_sha256":sha(HERE/"power-placement-groups.json"),
            "native_nonvia_track_count":len(native),"native_via_count":len(vias),
            "native_arc_count":sum(isinstance(t,pcbnew.PCB_ARC)for t in native),
            "thresholds":{"parallel_clearance_max_mm":1,"parallel_projected_overlap_min_mm":1,"parallel_acute_angle_max_deg":10,"power_cap_host_placement_objective_max_mm":2},
            "highz_nets":rows,"parallel_review_flags":parallel,"late_outputs_in_sensitive_regions":incursion,
            "region_boxes_mm":regions,"power_bypass_placement":bypass,"planes":planes,"priority_findings":findings}
    (args.output_dir/"sensitive-geometry-review.json").write_text(json.dumps(report,indent=2)+"\n")
    write_md(report,args.output_dir/"sensitive-geometry-review.md")
    write_csv(args.output_dir/"power-local-bypass-placement.csv",bypass,["ref","host_ref","host_pin","populate","capacitor_net","host_net","same_net","pad_center_distance_mm","over_2mm_placement_objective","capacitor_side","host_side","return_net","nearest_GND_via_distance_mm","purpose","status"])
    write_csv(args.output_dir/"sensitive-high-z-copper.csv",rows,["net","surface_length_mm","surface_track_segment_count","via_count","surface_Cu_pad_count"])
    print(json.dumps({"tracks":len(native),"vias":len(vias),"parallel_flags":len(parallel),"late_output_input_region_items":len(incursion),"cap_placement_flags":len(badcaps),"inner_tracks":innertracks,"findings":findings,"output":str(args.output_dir)},indent=2))

if __name__=="__main__":main()

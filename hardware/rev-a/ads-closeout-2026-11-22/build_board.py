"""Create the unrouted 80×74 mm four-channel placement from the native XML.

Run with KiCad 10's bundled Python. Add --low-c to select the MAX44280 project.
Do not regenerate after manual routing or moving footprints.
"""
from pathlib import Path
import argparse
import hashlib
import math
import json
import re
import xml.etree.ElementTree as ET

import pcbnew as pcb


HERE = Path(__file__).resolve().parent
REV = HERE.parent
mm = pcb.FromMM


def shape(fp):
    fp.BuildCourtyardCaches()
    poly = fp.GetCourtyard(fp.GetLayer())
    # Some API versions take the side's courtyard layer explicitly.
    if not poly.OutlineCount():
        poly = fp.GetCourtyard(pcb.F_CrtYd)
    box = poly.BBox() if poly.OutlineCount() else fp.GetBoundingBox(False,False)
    return tuple(v/1e6 for v in (box.GetLeft(),box.GetTop(),box.GetRight(),box.GetBottom()))


def overlaps(a,b,margin=.075):
    return a[0] < b[2]+margin and a[2] > b[0]-margin and a[1] < b[3]+margin and a[3] > b[1]-margin


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--low-c",action="store_true", help="Build only the MAX44280 sibling from its own native schematic export")
    low_c=parser.parse_args().low_c
    dest=REV/("bench-four-coax-low-c" if low_c else "bench-four-coax")
    audit=HERE/"low-c-board" if low_c else HERE
    audit.mkdir(exist_ok=True)
    netlist=dest/"curalink-four-coax.net.xml"
    board=dest/"curalink-rev-a.kicad_pcb"
    if board.exists():
        existing = pcb.LoadBoard(str(board))
        if list(existing.GetTracks()):
            raise RuntimeError("Existing variant contains copper. Preserve manual routing.")
        saved = audit/"board-snapshot-sha256.txt"
        if not saved.exists() or hashlib.sha256(board.read_bytes()).hexdigest() != saved.read_text().strip():
            raise RuntimeError("Existing variant has been edited. Preserve manual placement.")
    original = pcb.LoadBoard(str(REV/"curalink-rev-a.kicad_pcb"))
    old = {f.GetReference():(f.GetPosition().x/1e6,f.GetPosition().y/1e6,
                             f.GetOrientationDegrees()) for f in original.GetFootprints()}
    artwork = [item for item in original.GetDrawings() if item.GetLayer() not in (pcb.Edge_Cuts,pcb.Dwgs_User)]
    for item in artwork+list(original.GetTracks()):
        original.Delete(item)
    original.DeleteAllFootprints()
    root = ET.parse(netlist)
    parts = {c.get("ref"):c for c in root.findall(".//components/comp") if c.findtext("footprint")}
    if low_c:
        assert "U101" not in parts and all(f"U{x}" in parts for x in range(631,636))
        raw=next(n for n in root.findall(".//nets/net") if n.get("name")=="VMID_RAW")
        assert all(raw.find(f"node[@ref='R{r}'][@pin='2']") is not None for r in (1002,1020,1038,1056,1146))
    else:
        assert "U101" in parts and all(f"U{x}" not in parts for x in range(631,636))
    new_antenna = "D010" in parts["AE401"].findtext("footprint")
    for i in reversed(range(original.GetAreaCount())):
        zone=original.GetArea(i)
        if zone.GetIsRuleArea() and new_antenna:
            original.Delete(zone)
        else:
            zone.UnFill()
    net_for = {}
    for n in root.findall(".//nets/net"):
        name = n.get("name")
        net = original.FindNet(name)
        if not net:
            net = pcb.NETINFO_ITEM(original,name)
            original.Add(net)
        for pin in n.findall("node"):
            net_for[(pin.get("ref"),pin.get("pin"))] = (net,pin.get("pinfunction",""),pin.get("pintype",""))
    libs = {"CuraLink":REV/"pcb/footprints/CuraLink.pretty", "CuraLinkFour":dest/"CuraLinkFour.pretty"}
    changed={
        **{f"J{601+i}":(2.0,10+6*i,90) for i in range(4)},
        **{f"R{601+i}":(5.0,10+6*i,0) for i in range(4)},
        "R605":(8,31,0),"D610":(65,50,0),"D611":(65,46,0),"U610":(61,48,0),
        "C610":(59,48,0),"Q610":(55,48,0),"Q611":(55,45,0),"R610":(57.5,48,0),"R611":(57.5,45,0),
    }
    overrides = json.loads((REV/"pcb/mcu-placement-overrides.json").read_text())["overrides"]
    for ref, spec in overrides.items():
        if ref in old:
            old[ref] = (spec["x_mm"],spec["y_mm"],spec["rotation_deg"])
    if new_antenna:
        changed.update(AE401=(79.05,37,-90), R612=(72.6,35.5,0), C613=(71.3,36.7,90), C614=(73.2,36.7,90))
    priorities=set()
    if low_c:
        # Keep the four input assemblies around one shared ESD array. The cable
        # lands upstream of the input resistors. Guard the bias and feedback
        # placements from unrelated footprints during courtyard fitting.
        changed.update(U110=(12.3,18.8,0),U112=(8.25,33.2,0),R605=(6.3,32.3,0))
        priorities.update(("U110","U112","R605"))
        for i,(x,y,angle) in enumerate(((9.1,13.3,180),(16.0,14.4,90),(17.0,22.2,0),(9.0,24.7,-90),(12.1,34.3,0))):
            r=1001+18*i if i<4 else 1145
            cap=f"C{1001+7*i}" if i<4 else "C1057"
            bypass="C1059" if i==0 else f"C{631+i}"
            def rotate(dx,dy,orientation):
                a=math.radians(angle)
                return (x+dx*math.cos(a)+dy*math.sin(a),y-dx*math.sin(a)+dy*math.cos(a),angle+orientation)
            placements={f"U{631+i}":rotate(0,0,0),bypass:rotate(2.2,-.65,90),
                        cap:rotate(-2.55,-.65,0),f"R{r}":rotate(-3.3,-2.15,-90),
                        f"R{r+1}":rotate(-1.65,-2.1,180),f"R{r+2}":rotate(-.95,2.25,0),
                        f"R{r+3}":rotate(1.0,2.25,180)}
            changed.update(placements)
            priorities.update(placements)
        for i,(x,y) in enumerate(((10.1,17.3),(10.1,18.6),(10.1,19.9),(10.1,21.2))):
            changed[f"R{601+i}"]=(x,y,0)
            priorities.add(f"R{601+i}")
    schematic = (dest/"curalink-rev-a.kicad_sch").read_text()
    root_uuid = re.search(r'\(uuid\s+"?([\da-f-]{36})', schematic)[1]
    expected_path = {}
    expected_net = {}
    occupied = []
    keepout = (73.95,34.95,80.0,39.05)
    moved=[]
    def sequence(ref):
        if ref == "AE401": return (0,ref)
        if ref in ("R612","C613","C614") or ref in changed and ref.startswith("J"): return (1,ref)
        if ref in priorities: return (2 if ref.startswith("U") else 3,ref)
        if ref.startswith(("U","Q","J","AE")): return (4,ref)
        return (5,ref)
    for ref in sorted(parts,key=sequence):
        c=parts[ref]
        lib_id=c.findtext("footprint")
        lib,partname=lib_id.split(":")
        fp=pcb.FootprintLoad(str(libs[lib]),partname)
        if not fp: raise ValueError(f"Missing footprint {lib_id}")
        fp.SetFPIDAsString(lib_id);fp.SetReference(ref);fp.SetValue(c.findtext("value"))
        fp.GetField(pcb.FIELD_T_DATASHEET).SetText(c.findtext("datasheet",""))
        fp.SetExcludedFromBOM(c.find("property[@name='exclude_from_bom']") is not None)
        fp.SetSheetfile(next((p.get("value","") for p in c.findall("property") if p.get("name")=="Sheetfile"),""))
        fp.SetSheetname(next((p.get("value","") for p in c.findall("property") if p.get("name")=="Sheetname"),""))
        path="/"+root_uuid+c.find("sheetpath").get("tstamps")+c.findtext("tstamps").split()[0]
        expected_path[ref]=path
        fp.SetPath(pcb.KIID_PATH(path))
        for fld in c.findall("./fields/field"):
            key=fld.get("name");value=fld.text or ""
            if key in ("LCSC","MPN","DNP","Assembly"):
                field=pcb.PCB_FIELD(fp,pcb.FIELD_T_USER,key);field.SetText(value);field.SetVisible(False);fp.Add(field)
                if key=="DNP" and value=="yes": fp.SetDNP(True)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        exp=set(pin for (r,pin) in net_for if r==ref)
        actual={pad.GetNumber() for pad in fp.Pads() if pad.GetNumber()}
        if exp != actual: raise ValueError((ref,"footprint pin mismatch",exp-actual,actual-exp))
        original.Add(fp)
        for pad in fp.Pads():
            pin=pad.GetNumber()
            if not pin: continue
            net,function,pintype=net_for[(ref,pin)]
            pad.SetNet(net);pad.SetPinFunction(function);pad.SetPinType(pintype)
            expected_net[(ref,pin)]=net.GetNetname()
        anchor=changed.get(ref,old.get(ref))
        if anchor is None: raise ValueError(f"Provide initial position for {ref}")
        ax,ay,rot=anchor
        fp.SetOrientationDegrees(rot)
        # Preserve existing grouping and move within the nearest available
        # courtyard only when a new part or a changed footprint creates overlap.
        for radius in range(33):
            offsets=[(x,y) for x in range(-radius,radius+1) for y in range(-radius,radius+1)
                     if max(abs(x),abs(y))==radius]
            offsets.sort(key=lambda xy:xy[0]**2+xy[1]**2)
            for dx,dy in offsets:
                px=ax+.5*dx;py=ay+.5*dy
                fp.SetPosition(pcb.VECTOR2I(mm(px),mm(py)))
                bb=shape(fp)
                # Antenna's pad/land outline intentionally reaches the edge.
                edge = -.35 if ref=="AE401" else .20
                if (bb[0]<edge or bb[1]<edge or bb[2]>80-edge or bb[3]>74-edge or
                    (new_antenna and ref!="AE401" and overlaps(bb,keepout)) or any(overlaps(bb,x) for x in occupied)):
                    continue
                break
            else: continue
            break
        else: raise ValueError(f"Could not place {ref}")
        if ref=="AE401" and radius!=0: raise ValueError("Antenna edge position changed")
        if radius: moved.append([ref,ax,ay,px,py])
        occupied.append(bb)
    # Labels remain readable with cables unplugged and identify the four
    # otherwise identical edge connectors during single-aggressor testing.
    for n in range(4):
        label=pcb.PCB_TEXT(original)
        label.SetText(f"CH{n+1}");label.SetTextSize(pcb.VECTOR2I(mm(.7),mm(.7)))
        label.SetTextThickness(mm(.14));label.SetLayer(pcb.F_SilkS)
        label.SetPosition(pcb.VECTOR2I(mm(3.0),mm(12.85+6*n)))
        original.Add(label)
    original.RemoveUnusedNets(None)
    pcb.SaveBoard(str(board),original)
    head=pcb.LoadBoard(str(board))
    found={f.GetReference():f for f in head.GetFootprints()}
    assert set(found)==set(expected_path) and not list(head.GetTracks())
    for ref, fp in found.items():
        assert fp.GetPath().AsString()==expected_path[ref],ref
        for field in ("LCSC","MPN","DNP"):
            value=parts[ref].find(f"fields/field[@name='{field}']")
            if value is not None: assert fp.GetFieldText(field)==(value.text or ""),(ref,field)
        for pad in fp.Pads():
            if pad.GetNumber():
                assert pad.GetNetname()==expected_net[ref,pad.GetNumber()],(ref,pad.GetNumber(),pad.GetNetname())
    (audit/"board-snapshot-sha256.txt").write_text(hashlib.sha256(board.read_bytes()).hexdigest()+"\n")
    info=dict(footprints=len(found), connected_or_explicit_NC_pad_names=len(expected_net), footprint_paths_verified=len(expected_path),
              copper_layers=head.GetCopperLayerCount(), tracks_or_vias=len(list(head.GetTracks())), nearest_nonoverlap_moves=moved,
              antenna=[found["AE401"].GetPosition().x/1e6, found["AE401"].GetPosition().y/1e6, found["AE401"].GetOrientationDegrees()])
    info.update(variant=dest.name,source_netlist_sha256=hashlib.sha256(netlist.read_bytes()).hexdigest(),
                R501_DNP=found["R501"].IsDNP())
    if low_c:
        by_net={}
        for f in found.values():
            for pad in f.Pads():
                if pad.GetNumber():
                    point=pad.GetPosition()
                    by_net.setdefault(pad.GetNetname(),[]).append((point.x/1e6,point.y/1e6))
        spans={}
        for ch in ("CH1","CH2","CH3","CH4","REF"):
            for net in ("FFC_"+ch,ch+"_LIMIT",ch+"_PLUS"):
                pts=by_net[net]
                spans[net]=round(max(math.dist(a,b) for a in pts for b in pts),3)
        info["protected_input_max_pad_center_span_mm"]=spans
    (audit/"board-checks.json").write_text(json.dumps(info,indent=2)+"\n")
    print({k:v for k,v in info.items() if k!="nearest_nonoverlap_moves"})


if __name__=="__main__":
    main()

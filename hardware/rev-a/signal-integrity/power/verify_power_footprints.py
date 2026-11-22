"""Run under Ubuntu-24.04's KiCad pcbnew, validating actual parsed geometry."""
from pathlib import Path
import hashlib
import itertools
import json
import math
import pcbnew

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
LIB=ROOT/"hardware/rev-a/pcb/footprints/CuraLink.pretty"
audit=json.loads((BASE/"footprint-audit.json").read_text())
results={"kicad_version":pcbnew.GetBuildVersion(),"date_local":"2026-10-02","footprints":[]}

def close(a,b):
    assert math.isclose(a,b,abs_tol=.000002), (a,b)

for s in audit["footprints"]:
    f=pcbnew.FootprintLoad(str(LIB),s["name"])
    assert f is not None,s["name"]
    records=[]
    for p in f.Pads():
        record={"number":p.GetNumber(),"xy_mm":[p.GetPosition().x/1e6,p.GetPosition().y/1e6],
                "copper_size_mm":[p.GetSize().x/1e6,p.GetSize().y/1e6],
                "mask_margin_mm":p.GetLocalSolderMaskMargin()/1e6 if p.GetLocalSolderMaskMargin() is not None else None,
                "layers":[pcbnew.LayerName(i) for i in p.GetLayerSet().Seq()]}
        records.append(record)
    numbered=[p for p in records if p["number"]]
    pastes=[p for p in records if not p["number"]]
    assert len(numbered)==len(s["pads"])
    assert set(p["number"] for p in numbered)==set(s["pin_functions"])
    assert len(pastes)==len(s.get("paste_apertures",[]))
    for expected in s["pads"]:
        p=next(p for p in numbered if p["number"]==expected["number"])
        for a,b in zip(p["xy_mm"]+p["copper_size_mm"],expected["xy_mm"]+expected["copper_size_mm"]):
            close(a,b)
        close(p["mask_margin_mm"],expected["mask_margin_mm"])
        assert "F.Cu" in p["layers"] and "F.Mask" in p["layers"]
        assert ("F.Paste" in p["layers"])==expected["paste_is_copper"]
    for e,p in zip(s.get("paste_apertures",[]),pastes):
        for a,b in zip(p["xy_mm"]+p["copper_size_mm"],e["xy_mm"]+e["size_mm"]):
            close(a,b)
        assert p["layers"]==["F.Paste"],p
    gaps=[]
    maskgaps=[]
    for a,b in itertools.combinations(numbered,2):
        dx=abs(a["xy_mm"][0]-b["xy_mm"][0])-(a["copper_size_mm"][0]+b["copper_size_mm"][0])/2
        dy=abs(a["xy_mm"][1]-b["xy_mm"][1])-(a["copper_size_mm"][1]+b["copper_size_mm"][1])/2
        d=math.hypot(max(0,dx),max(0,dy))
        gaps.append({"pads":[a["number"],b["number"]],"distance_lower_bound_mm":round(d,6)})
        m=a["mask_margin_mm"]+b["mask_margin_mm"]
        dm=math.hypot(max(0,dx-m),max(0,dy-m))
        maskgaps.append({"pads":[a["number"],b["number"]],"distance_lower_bound_mm":round(dm,6)})
    mingap=min(gaps,key=lambda r:r["distance_lower_bound_mm"])
    minmask=min(maskgaps,key=lambda r:r["distance_lower_bound_mm"])
    assert mingap["distance_lower_bound_mm"]>=.15-1e-6
    assert minmask["distance_lower_bound_mm"]>=.1-1e-6
    results["footprints"].append({"name":s["name"],"load_status":"PASS","geometry_status":"PASS",
         "physical_electrical_pad_count":len(numbered),"separate_paste_count":len(pastes),
         "numbered_pads":numbered,"separate_paste_apertures":pastes,
         "minimum_rectangular_copper_gap":mingap,"minimum_rectangular_mask_bridge":minmask,
         "sha256":hashlib.sha256((LIB/(s["name"]+".kicad_mod")).read_bytes()).hexdigest()})
(BASE/"footprint-loader-verification.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps({"kicad":results["kicad_version"],"checked":[{"name":r["name"],"pads":r["physical_electrical_pad_count"],"min_copper_gap_mm":r["minimum_rectangular_copper_gap"]["distance_lower_bound_mm"],"min_mask_bridge_mm":r["minimum_rectangular_mask_bridge"]["distance_lower_bound_mm"]} for r in results["footprints"]]},indent=2))

"""Create the three power footprints from TI package/land/stencil drawings.

The generated footprint coordinate system is the PCB top view, with pin 1 at
upper left. Millimetres throughout. This is not a board placement generator.
"""
from pathlib import Path
import hashlib
import json
import math
import uuid

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
DEST = ROOT / "hardware/rev-a/pcb/footprints/CuraLink.pretty"
DEST.mkdir(parents=True, exist_ok=True)

def uid():
    return str(uuid.uuid4())

def pad(number, x, y, w, h, layers, radius=0.05, mask=None):
    s = (f'  (pad "{number}" smd roundrect (at {x:g} {y:g}) '
         f'(size {w:g} {h:g}) (layers {" ".join(chr(34)+a+chr(34) for a in layers)}) '
         f'(roundrect_rratio {radius/min(w,h):.9f})')
    if mask is not None:
        s += f' (solder_mask_margin {mask:g})'
    return s + f' (uuid "{uid()}"))'

def graphic_line(a, b, layer, width):
    return (f'  (fp_line (start {a[0]:g} {a[1]:g}) (end {b[0]:g} {b[1]:g}) '
            f'(stroke (width {width:g}) (type solid)) (layer "{layer}") (uuid "{uid()}"))')

def make_footprint(spec):
    name = spec["name"]
    bw, bh = spec["body_nominal_mm"]
    cx, cy = spec["courtyard_half_mm"]
    lines = [f'(footprint "{name}"',
             '  (version 20241229) (generator "pcbnew") (generator_version "9.0")',
             '  (layer "F.Cu")',
             f'  (descr "{spec["description"]}")',
             '  (tags "CuraLink TI manufacturer reference land pattern")',
             f'  (property "Reference" "REF**" (at 0 {-cy-.55:g}) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.12))))',
             f'  (property "Value" "{name}" (at 0 {cy+.55:g}) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1))))',
             f'  (property "Datasheet" "{spec["source_url"]}" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1))))',
             '  (attr smd)']
    bevel=.25
    points=[(-bw/2,-bh/2+bevel),(-bw/2+bevel,-bh/2),(bw/2,-bh/2),(bw/2,bh/2),(-bw/2,bh/2)]
    for a,b in zip(points,points[1:]+points[:1]):
        lines.append(graphic_line(a,b,"F.Fab",.1))
    lines.append(f'  (fp_rect (start {-cx:g} {-cy:g}) (end {cx:g} {cy:g}) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd") (uuid "{uid()}"))')
    sy=spec["silk_y_mm"]
    lines.append(graphic_line((-bw/2+.2,-sy),(bw/2,-sy),"F.SilkS",.12))
    lines.append(graphic_line((-bw/2,sy),(bw/2,sy),"F.SilkS",.12))
    tx,ty=spec["pin1_marker_xy_mm"]
    lines.append(f'  (fp_poly (pts (xy {tx:g} {ty:g}) (xy {tx+.2:g} {ty:g}) (xy {tx:g} {ty+.16:g})) (stroke (width 0.08) (type solid)) (fill yes) (layer "F.SilkS") (uuid "{uid()}"))')
    for p in spec["pads"]:
        # Dedicated paste aperture on SMD lands and exposed pads avoids relying
        # on a blanket paste shrink across package-specific shapes.
        layers=["F.Cu","F.Mask"]
        if p.get("paste_is_copper",True):
            layers.append("F.Paste")
        lines.append(pad(p["number"],*p["xy_mm"],*p["copper_size_mm"],layers,p.get("copper_corner_radius_mm",.05),p["mask_margin_mm"]))
    for p in spec.get("paste_apertures",[]):
        lines.append(pad("",*p["xy_mm"],*p["size_mm"],["F.Paste"],p.get("corner_radius_mm",.05)))
    lines.append('  (embedded_fonts no)')
    lines.append(')')
    out=DEST/(name+".kicad_mod")
    out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    spec["file"] = str(out.relative_to(ROOT)).replace("\\","/")
    spec["footprint_sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
    return spec

def make_pad(n,x,y,w,h,mask=.05,paste=True,corner=.05):
    return {"number":str(n),"xy_mm":[x,y],"copper_size_mm":[w,h],
            "mask_margin_mm":mask,"paste_is_copper":paste,"copper_corner_radius_mm":corner}

specs=[]
dlh={"name":"BQ25185DLH_WSON10_2.2x2mm","manufacturer":"Texas Instruments",
     "mpn":"BQ25185DLHR","lcsc":"C19725033","refs":["U501"],
     "package":"DLH0010A","drawing":"4226298/A 10/2020",
     "description":"TI DLH0010A, exact example land and stencil geometry; 10 leads plus grounded EP11; top-view pin1 upper-left",
     "source_url":"https://www.ti.com/lit/ds/symlink/bq25185.pdf",
     "source_pdf":"hardware/rev-a/ltspice/power/sources/bq25185-datasheet.pdf",
     "pdf_pages_1based":{"outline":29,"land":30,"stencil":31},
     "body_nominal_mm":[2.2,2.0],"body_max_mm":[2.3,2.1],"height_max_mm":.8,
     "pitch_mm":.4,"courtyard_half_mm":[1.55,1.3],"silk_y_mm":1.2,
     "pin1_marker_xy_mm":[-1.4,-1.2],"pads":[],
     "pin_functions":{"1":"SYS","2":"BAT","3":"STAT2","4":"CE_N","5":"GND","6":"TS/MR","7":"ILIM/VSET","8":"ISET","9":"STAT1","10":"IN","11":"EP_GND"},
     "paste_apertures":[{"xy_mm":[0,0],"size_mm":[.85,1.38]}],
     "stencil_thickness_example_mm":.125,
     "thermal_vias":"TI optional 0.2 mm finished holes at x=0,y=+/-0.5 mm; no vias embedded in footprint. Assembly shop must approve filled/plugged/tented construction and paste before adding vias.",
     "mask_notes":"Non-solder-mask-defined, 0.05 mm positive mask expansion on all pads.",
     "official_library_comparison":"KiCad9.0.9 Texas_DLH0010A_WSON-10-1EP_2.2x2mm_P0.4mm_EP0.9x1.5mm uses 0.75x0.2 mm lands at x=+/-1.1 mm; this custom uses TI example 0.5x0.2 mm at +/-1.05 mm instead."}
for n in range(1,11):
    x=-1.05 if n<=5 else 1.05
    y=-.8+.4*(n-1) if n<=5 else .8-.4*(n-6)
    dlh["pads"].append(make_pad(n,x,round(y,4),.5,.2))
dlh["pads"].append(make_pad(11,0,0,.9,1.5,paste=False))
specs.append(dlh)

drv={"name":"TPS25200DRV_WSON6_2x2mm","manufacturer":"Texas Instruments",
     "mpn":"TPS25200DRVR","lcsc":"C128401","refs":["U502","U511"],
     "package":"DRV0006A","drawing":"4222173/C 11/2025",
     "description":"TI DRV0006A, exact example land and split-stencil geometry; 6 leads plus grounded EP7; top-view pin1 upper-left",
     "source_url":"https://www.ti.com/lit/ds/symlink/tps25200.pdf",
     "source_pdf":"hardware/rev-a/ltspice/power/sources/tps25200-datasheet.pdf",
     "pdf_pages_1based":{"outline":28,"land":29,"stencil":30},
     "body_nominal_mm":[2,2],"body_max_mm":[2.1,2.1],"height_max_mm":.8,
     "pitch_mm":.65,"courtyard_half_mm":[1.45,1.3],"silk_y_mm":1.2,
     "pin1_marker_xy_mm":[-1.3,-1.2],"pads":[],
     "pin_functions":{"1":"OUT","2":"ILIM","3":"FAULT_N","4":"EN","5":"GND","6":"IN","7":"EP_GND"},
     "paste_apertures":[{"xy_mm":[0,-.45],"size_mm":[1,.7]},{"xy_mm":[0,.45],"size_mm":[1,.7]}],
     "stencil_thickness_example_mm":.125,
     "thermal_vias":"TI optional 0.2 mm finished holes at x=0,y=+/-0.55 mm; not embedded. Confirm via-in-pad process and stencil with assembly shop first.",
     "mask_notes":"Non-solder-mask-defined, 0.07 mm positive mask expansion per drawing.",
     "official_library_comparison":"KiCad9.0.9 DFN-6-1EP_2x2mm_P0.65mm_EP1x1.6mm is described for Microchip and uses 0.65x0.35 mm lands at +/-1.05 mm; TI example is 0.45x0.30 mm at +/-0.975 mm. A generic DFN-6 was not copied."}
for n in range(1,7):
    x=-.975 if n<=3 else .975
    y=-.65+.65*(n-1) if n<=3 else .65-.65*(n-4)
    drv["pads"].append(make_pad(n,x,round(y,4),.45,.3,mask=.07))
drv["pads"].append(make_pad(7,0,0,1,1.6,mask=.07,paste=False))
specs.append(drv)

dse={"name":"BQ29737DSE_WSON6_1.5x1.5mm","manufacturer":"Texas Instruments",
     "mpn":"BQ29737DSER","lcsc":"C3681751","refs":["U514"],
     "package":"DSE0006A","drawing":"4220552/B 01/2024",
     "description":"TI DSE0006A, asymmetric 6-lead example lands, solder-mask-defined pads1-3, NO exposed pad; pin1 upper-left",
     "source_url":"https://www.ti.com/lit/ds/symlink/bq2973.pdf",
     "source_pdf":"hardware/rev-a/ltspice/sources/bq2973.pdf",
     "pdf_pages_1based":{"outline":32,"land":33,"stencil":34},
     "body_nominal_mm":[1.5,1.5],"body_max_mm":[1.55,1.55],"height_max_mm":.8,
     "pitch_mm":.5,"courtyard_half_mm":[1.25,1.05],"silk_y_mm":.95,
     "pin1_marker_xy_mm":[-1.1,-.95],"pads":[],
     "pin_functions":{"1":"NC","2":"COUT","3":"DOUT","4":"VSS","5":"BAT","6":"V-"},
     "paste_apertures":[],"stencil_thickness_example_mm":.125,
     "thermal_vias":"No exposed pad and no thermal via array. Do not add a phantom pad7.",
     "mask_notes":"TI requires SMD pads1-3 with at least 0.05 mm copper under mask. The specified exposed lands are 0.8x0.25 mm at pin1 and 0.7x0.25 mm at pins2/3, implemented using copper enlarged 0.05 mm on each edge and mask_margin=-0.05 mm. Pads4-6 are NSMD 0.7x0.25 mm copper with +0.05 mm mask margin (drawing says 0.05 mm maximum). All six paste openings follow TI example exposed-land dimensions, separate from enlarged SMD copper.",
     "pin1_asymmetry":"Pin1 shares the x=-0.95 mm outer exposed-land edge with pins2/3; it extends 0.10 mm farther inward, so its exposed-land center is -0.55 mm versus -0.60 mm for pins2/3.",
     "population_status":"Optional DNP protection remains electrically unqualified for selected cell. Correct footprint does not approve populating it."}
for n in range(1,7):
    left=n<=3
    x=(-.55 if n==1 else -.6) if left else .6
    y=-.5+.5*(n-1) if left else .5-.5*(n-4)
    w=.8 if n==1 else .7
    dse["pads"].append(make_pad(n,x,round(y,4),w+.1 if left else w,.35 if left else .25,mask=-.05 if left else .05,paste=False,corner=.1 if left else .05))
    dse["paste_apertures"].append({"xy_mm":[x,round(y,4)],"size_mm":[w,.25]})
specs.append(dse)

for s in specs:
    source=ROOT/s["source_pdf"]
    s["source_pdf_sha256"]=hashlib.sha256(source.read_bytes()).hexdigest()
    make_footprint(s)

# Confirm canonical functions and exposed-pad count without changing netlists.
components=json.loads((ROOT/"hardware/rev-a/power/power-components.json").read_text(encoding="utf-8"))["components"]
byref={c["ref"]:c for c in components}
for s in specs:
    s["canonical_pin_checks"]={}
    for ref in s["refs"]:
        c=byref[ref]
        assert c["pin_names"]==s["pin_functions"], (ref,c["pin_names"])
        assert set(c["pins"])==set(s["pin_functions"]),ref
        s["canonical_pin_checks"][ref]={"functions_match":True,"pins":c["pins"]}

audit={"date_local":"2026-10-02","timezone":"America/New_York",
       "status":"Manufacturer drawing transcription; KiCad loader verification separately recorded; no assembly or PCB qualification implied.",
       "coordinate_system":"mm, top-view unrotated footprint; +x right and +y down; pin1 upper-left.",
       "courtyard_rule":"Chosen 0.25 mm clearance from maximum package body or copper extents, rounded outward to 0.05 mm. Courtyard and silkscreen are project choices, not TI dimensions.",
       "assembly_limitations":["No manufacturer's 3D model included.","Confirm assembly orientation against pin1 mark on actual reel and JLC preview; footprint orientation alone does not establish pick-and-place rotation.","0.125 mm stencil thickness is the TI drawing example, not an approved JLC process.","EP11/EP7 must connect to ground with short low-impedance copper; thermal dissipation and solder voiding require board-level review.","Do not automatically add through thermal vias beneath full paste apertures without assembly approval."],
       "footprints":specs}
(BASE/"footprint-audit.json").write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"created":[s["file"] for s in specs],"canonical_pin_functions":"PASS"},indent=2))

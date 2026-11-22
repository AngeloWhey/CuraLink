"""Derive the four-generator schematic from Rev A and verify native KiCad output."""
from pathlib import Path
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
sys.path.insert(0, str(BASE.parents[1] / "tools" / "hardware"))
import build_reva as cad
sys.path.insert(0, str(BASE / "telemetry-variant"))
import apply_telemetry

PROJECT = "curalink-rev-a"
ROOT_UUID = "8301eba8-fab0-5bcb-b414-f69e384483ab"
INPUT_UUID = cad.uid("four-generator-input-sheet")
STATUS_UUID = cad.uid("four-generator-status-sheet")
def sequence(prefix, first, last):
    return {f"{prefix}{n}" for n in range(first, last + 1)}


REMOVED = ({"J301", "U102", "U104", "U106", "U108", "U111",
            "C1060", "C1062", "C1064", "C1066"}
           | sequence("R", 1073, 1144) | sequence("C", 1029, 1056)
           | sequence("TP", 113, 124) | sequence("TP", 414, 417)
           | sequence("R", 405, 408) | sequence("C", 417, 420))
CH_UNUSED = {f"afe_ch{n}_1.kicad_sch" for n in range(5, 9)}
ADC_UNUSED = {f"ADC_IN_{n}" for n in range(5, 9)}
RF_REFS = {"C423":"R612","L401":"C613","L402":"C614"}


def apply_stock_choices(parts):
    """November sourcing substitutions for the unrouted four-input board only."""
    lookup = {
        "C19626860": ("STM32WBA52CEU6", "C7543271", "https://www.st.com/resource/en/datasheet/stm32wba52ce.pdf"),
        "C7836": ("74LVC1G17GV,125","C6076","https://assets.nexperia.com/documents/data-sheet/74LVC1G17.pdf"),
        "C7666": ("74LVC1G08GV,125","C282347","https://assets.nexperia.com/documents/data-sheet/74LVC1G08.pdf"),
        "C2057826": ("TLV9054IPWR","C2057744","https://www.ti.com/lit/ds/symlink/tlv9054.pdf"),
        "C108342": ("GRM188Z71A475KE15D","C913474","https://psearch.en.murata.com/capacitor/product/GRM188Z71A475KE15%23.html"),
        "C3014193": ("ARG03BTC9103","C2686431","https://www.lcsc.com/product-detail/C2686431.html"),
        "C17430588": ("2450AT18D0100001E","C7450310","https://www.johansontechnology.com/docs/3791/Antenna-2450AT18D0100001E-Rev5.0.pdf"),
    }
    by_ref={p["ref"]:p for p in parts}
    for p in parts:
        if p.get("lcsc") not in lookup:
            continue
        mpn,code,source=lookup[p["lcsc"]]
        if p["value"]==p["mpn"]:
            p["value"]=mpn
        p.update(mpn=mpn,lcsc=code,source=source)
        p.pop("stock",None)
        p.pop("stock_checked",None)
        if p["ref"]=="U107":
            # TI Table 4-5: each physical RUC pin moves +1 modulo 14 in PW.
            pw={str(n):str(n%14+1) for n in range(1,15)}
            for field in ("pins","pin_names","pinfunctiontypes"):
                p[field]={pw[k]:v for k,v in p[field].items()}
            for block in p["unit_blocks"]:
                block["pins"]=[pw[n] for n in block["pins"]]
            p.update(package="TSSOP-14 PW",footprint="CuraLinkFour:TSSOP-14_4.4x5mm_P0.65mm",
                     notes="TI TLV9054 PW pin-function table controls all four units and supply pins.")
        elif p["ref"]=="AE401":
            p.update(package="1206 four-terminal chip",footprint="CuraLinkFour:Johanson_2450AT18D0100001E",
                     pins={"1":"ANT_FEED","2":"GND","3":"GND","4":"GND"},
                     pin_names={"1":"FEED","2":"GND","3":"GND","4":"GND"},
                     notes="Manufacturer Rev 5 pp. 2–3. Pin 1 feed, 2/3/4 ground externally; place at edge midpoint with all-layer ground clearance.")
        elif p["ref"]=="U610":
            p["pin_names"].update({"1":"B","2":"A"})
        elif p["ref"]=="U401":
            p["notes"]="WBA52CEU6 UFQFPN48, 512 KiB flash and 96 KiB SRAM. Pin-compatible WBA52CG package; firmware link and RAM/OTA budget pending."
        elif p["lcsc"]=="C2686431":
            p.update(value="910k", notes="Two equal 910 kΩ, 0.1% parts in each of both ratio arms: 1.820 MΩ total.")
    for old,newref in RF_REFS.items():
        p=by_ref[old]
        fit = newref=="R612"
        template = by_ref["R417"] if fit else by_ref["C410"]
        p.update(ref=newref,mpn=template["mpn"],lcsc=template["lcsc"],package="0402",
                 value="0ohm antenna initial" if fit else "DNP antenna shunt",
                 populated=fit,populate=fit,dnp=not fit,
                 footprint="CuraLink:"+("R" if fit else "C")+"_0402_1005Metric",
                 notes="Tune assembled RF path; Johanson evaluation board starts with a through link and empty shunts.")
        if not fit:
            # These are empty tune pads. No purchasable placeholder component.
            p.update(mpn="",lcsc="")
        p["pins"]={"R612":{"1":"ANT_T_IN","2":"ANT_FEED"},
                   "C613":{"1":"ANT_T_IN","2":"GND"},
                   "C614":{"1":"ANT_FEED","2":"GND"}}[newref]


def new_components():
    parts = []
    for n in range(1, 5):
        parts.append(dict(ref=f"J{600+n}", value=f"CH{n} U.FL",
                          mpn="U.FL-R-SMT-1(80)", lcsc="C88374",
                          footprint="CuraLink:UFL_Hirose_1SIG_2GND_3GND",
                          pins={"1": f"COAX_CH{n}", "2": "GND", "3": "GND"},
                          pin_names={"1": "CONTACT", "2": "SHELL", "3": "SHELL"}))
    for n in range(1, 6):
        parts.append(dict(ref=f"R{600+n}", value="47k 1%", mpn="0402WGF4702TCE",
                          lcsc="C25792", footprint="CuraLink:R_0402_1005Metric",
                          pins={"1": f"COAX_CH{n}" if n < 5 else "GND",
                                "2": f"FFC_CH{n}" if n < 5 else "FFC_REF"}))
    return parts


def input_sheet(parts):
    """Draw a physical wire on the signal side of each independently shielded input."""
    defs = []
    for part in (parts[0], parts[4]):
        sym = cad.make_lib(part)
        defs.append(sym.replace('(symbol "', '(symbol "CuraLink:', 1))
    s = [f'(kicad_sch (version 20230121) (generator eeschema) '
         f'(uuid {cad.uid("four-coax-file")}) (paper "A4")',
         '(title_block (title "Four coaxial generator inputs") (date "2026-11-22") (rev "Bench A"))',
         '(lib_symbols ' + "\n".join(defs) + ')',
         cad.text_line("Four independent benchtop waveform inputs", 24, 24, 2.4),
         cad.text_line("Board-edge coax  /  local 47 k source model  /  protected AFE input", 24, 32)]
    def instance(part, x, y, angle):
        ref = part["ref"]
        fields = [f'(symbol (lib_id "CuraLink:{cad.lib_key(part)}") (at {x} {y} {angle}) '
                  f'(unit 1) (in_bom yes) (on_board yes) (uuid {cad.uid(ref+"-unit")})']
        for key, value, dy, hidden in [
                ("Reference",ref,-6.7,False), ("Value",part["value"],-5,False),
                ("Footprint",part["footprint"],0,True), ("MPN",part["mpn"],0,True),
                ("LCSC",part["lcsc"],0,True)]:
            fields.append(cad.prop(key,value,x,y+dy,hidden))
        fields.extend(f'(pin "{pin}" (uuid {cad.uid(ref+"-pin-"+pin)}))' for pin in part["pins"])
        fields.append(f'(instances (project "{PROJECT}" (path "/{ROOT_UUID}/{INPUT_UUID}" '
                      f'(reference "{ref}") (unit 1)))))')
        return "\n".join(fields)
    for n in range(1, 6):
        y = 27.94 + n * 25.4
        if n < 5:
            s.append(instance(parts[n-1], 48.26, y-1.27, 180))
            s.append(cad.wire(36.83,y-1.27,31.75,y-1.27,f"J{n}-ground-left"))
            s.append(cad.label("GND",31.75,y-1.27,180,f"J{n}-left-label"))
            s.append(cad.wire(59.69,y-2.54,67.31,y-2.54,f"J{n}-ground-right"))
            s.append(cad.label("GND",67.31,y-2.54,0,f"J{n}-right-label"))
            s.append(cad.wire(59.69,y,82.55,y,f"J{n}-center"))
            s.append(f'(label "COAX_CH{n}" (at 82.55 {cad.num(y)} 0) '
                     f'(effects (font (size 1 1)) (justify left bottom)) (uuid {cad.uid("coax-net"+str(n))}))')
            s.append(cad.wire(82.55,y,109.22,y,f"J{n}-source"))
        else:
            s.append(cad.label("GND",82.55,y,180,"quiet-reference-label"))
            s.append(cad.wire(82.55,y,109.22,y,"quiet-reference-R"))
        s.append(instance(parts[3+n],114.30,y,0))
        s.append(cad.wire(119.38,y,144.78,y,f"R{n}-afe"))
        output = f"FFC_CH{n}" if n < 5 else "FFC_REF"
        s.append(cad.label(output,144.78,y,0,f"R{n}-afe-label"))
    s.append(cad.text_line("Place each series resistor beside the protected AFE input. Keep all coax shields on local GND.", 24, 171))
    s.append(cad.text_line("Existing FFC_* net names identify the AFE boundary. There is no FFC connector in this variant.", 24, 177))
    s.append(f'(sheet_instances (path "/{ROOT_UUID}/{INPUT_UUID}" (page "14")))\n)')
    return "\n".join(s) + "\n"


def trim_sheet(src, by_ref, changed):
    # Each symbol from the canonical generator owns the wire/label and NC records
    # immediately following it. Stop at sheet_instances so the sheet end is preserved.
    head, body = src.split("\n(symbol (lib_id ", 1)
    body, end = body.rsplit("\n(sheet_instances", 1)
    keep = []
    for unit in body.split("\n(symbol (lib_id "):
        ref = re.search(r'\(property "Reference" "([^"]+)"',unit)[1]
        ref = RF_REFS.get(ref,ref)
        if ref not in by_ref:
            continue
        if ref in changed:
            loc = re.search(r'^"[^"]+"\) \(at ([-.\d]+) ([-.\d]+) 0\)',unit)
            path = re.search(r'\(instances \(project "[^"]+" \(path "([^"]+)"',unit)[1]
            block = int(re.search(r'\(unit (\d+)\)',unit)[1])
            comp = by_ref[ref]
            key = cad.lib_key(comp)
            if f'(symbol "CuraLink:{key}"' not in head:
                section, rest = head.split('\n(text ',1)
                definition=cad.make_lib(comp).replace(f'(symbol "{key}"',f'(symbol "CuraLink:{key}"',1)
                head=section[:-1]+"\n"+definition+")\n(text "+rest
            geom = next(b for b in cad.blocks(comp) if b["unit"]==block)
            unit = cad.instance(comp,geom,float(loc[1]),float(loc[2]),path).removeprefix("(symbol (lib_id ")
        if by_ref[ref].get("populated") is False:
            unit=unit.replace("(on_board yes)","(on_board yes) (dnp yes)",1)
        keep.append("\n(symbol (lib_id " + unit)
    return head + "".join(keep) + "\n(sheet_instances" + end


def emit_telemetry(parts,all_parts):
    libs={cad.lib_key(p):cad.make_lib(p) for p in parts}
    project_lib=(BASE/"CuraLink.kicad_sym").read_text(encoding="utf-8").rstrip()
    for key,definition in {cad.lib_key(p):cad.make_lib(p) for p in all_parts}.items():
        if f'(symbol "{key}"' not in project_lib:
            project_lib=project_lib[:-1]+"\n"+definition+"\n)"
    (OUT/"CuraLink.kicad_sym").write_text(project_lib+"\n",encoding="utf-8")
    sheet=[f'(kicad_sch (version 20230121) (generator eeschema) (uuid {cad.uid("four-status-file")}) (paper "A4")',
           '(title_block (title "Radio power and charger status") (date "2026-11-22") (rev "Bench A"))',
           '(lib_symbols '+"\n".join(v.replace(f'(symbol "{k}"', f'(symbol "CuraLink:{k}"',1) for k,v in libs.items())+')',
           cad.text_line("MCU supply during charging and AFE interlock",20,16,2),
           cad.text_line("Full net labels connect to the power, MCU and control sheets.",20,24)]
    for idx,p in enumerate(parts):
        x=53.34+91.44*(idx%3)
        y=48.26+43.18*(idx//3)
        sheet.append(cad.instance(p,cad.blocks(p)[0],x,y,f"/{ROOT_UUID}/{STATUS_UUID}"))
    sheet.append(f'(sheet_instances (path "/{ROOT_UUID}/{STATUS_UUID}" (page "15")))\n)')
    (OUT/"charge-telemetry.kicad_sch").write_text("\n".join(sheet)+"\n",encoding="utf-8")


def derive(input_variant=None):
    from copy import deepcopy
    old=json.loads((BASE/"components-merged.json").read_text(encoding="utf-8"))["components"]
    old_by_ref={p["ref"]:p for p in old}
    new=deepcopy([p for p in old if p["ref"] not in REMOVED])
    mcu=next(p for p in new if p["ref"]=="U401")
    for pin,net in list(mcu["pins"].items()):
        if net in ADC_UNUSED:
            mcu["pins"][pin]=None
    apply_telemetry.apply(new)
    telemetry=[p for p in new if p["ref"] not in old_by_ref]
    charge_link=next(p for p in new if p["ref"]=="R501")
    charge_link.update(populated=False,populate=False,dnp=True,
                       notes="Leave open for the lab-pack fallback. Fit only for an approved emulator or qualified pack charge test.")
    apply_stock_choices(new)
    parts=new_components()
    new.extend(parts)
    if input_variant:
        input_variant.modify(new)
    by_ref={p["ref"]:p for p in new}
    changed={r for r,p in by_ref.items() if r not in old_by_ref or any(
        old_by_ref[r].get(k)!=p.get(k) for k in ("pins","mpn","value","lcsc","footprint","populated"))}
    emit_telemetry(telemetry,new)
    (OUT/"four-inputs.kicad_sch").write_text(input_sheet(parts), encoding="utf-8")
    root = (BASE/f"{PROJECT}.kicad_sch").read_text(encoding="utf-8")
    root = root.replace("CuraLink Rev A schematic draft","CuraLink four-channel generator variant")
    root = root.replace("2026-10-02 | ADC acquisition recommendation | NOT A PCB RELEASE",
                        "2026-11-22 | Four independent coax inputs | Engineering schematic")
    root = root.replace("See README, pin-net CSV and verification report before import/order.",
                        "See README and verified native XML for assembly and pin mapping.")
    def sheet(match):
        record, name = match.group(), match[1]
        if name in CH_UNUSED:
            return ""
        data = (BASE/name).read_text(encoding="utf-8")
        filtered = trim_sheet(data,by_ref,changed)
        old_page=int(re.search(r'\(page "(\d+)"',record)[1])
        if old_page>=14:
            record=record.replace(f'(page "{old_page}")',f'(page "{old_page-4}")')
            filtered=filtered.replace(f'(page "{old_page}")',f'(page "{old_page-4}")')
        (OUT/name).write_text(filtered,encoding="utf-8")
        return record
    root = re.sub(r'(?ms)^\(sheet \(at .*?\(property "Sheetfile" "([^"]+)".*?^ +\(instances[^\n]+\n',
                  sheet,root)
    new_sheet = (f'(sheet (at 25 152) (size 110 25) (stroke (width 0) (type default)) '
                 f'(fill (color 0 0 0 0)) (uuid {INPUT_UUID}) '
                 '(property "Sheetname" "Four coax inputs" (at 27 154 0) (effects (font (size 1 1)))) '
                 '(property "Sheetfile" "four-inputs.kicad_sch" (at 27 174 0) (effects (font (size 1 1)))) '
                 f'(instances (project "{PROJECT}" (path "/{ROOT_UUID}" (page "14")))))\n')
    status_sheet = new_sheet.replace(INPUT_UUID,STATUS_UUID).replace("Four coax inputs","Charge telemetry").replace(
        "four-inputs.kicad_sch","charge-telemetry.kicad_sch").replace('(page "14")','(page "15")').replace(
        '(at 25 152)','(at 150 152)').replace('(at 27 ','(at 152 ')
    root=root.replace('(sheet_instances (path "/"',new_sheet+status_sheet+'(sheet_instances (path "/"')
    if input_variant:
        root=input_variant.add_page(root)
    (OUT/f"{PROJECT}.kicad_sch").write_text(root, encoding="utf-8")
    (OUT/"sym-lib-table").write_text((BASE/"sym-lib-table").read_text())
    fp=(BASE/"fp-lib-table").read_text().replace("${KIPRJMOD}/","${KIPRJMOD}/../").rstrip()
    fp=fp[:-1]+'  (lib (name "CuraLinkFour")(type "KiCad")(uri "${KIPRJMOD}/CuraLinkFour.pretty")(options "")(descr "Four-input variant land patterns"))\n)'
    (OUT/"fp-lib-table").write_text(fp+"\n")
    (OUT/f"{PROJECT}.kicad_pro").write_text((BASE/f"{PROJECT}.kicad_pro").read_text())
    with (OUT/"removed-from-rev-a.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f)
        w.writerow(["Canonical reference","Reason"])
        for ref in sorted(old_by_ref.keys()-by_ref.keys()):
            reason="Four direct coax feeds replace FFC" if ref=="J301" else ("Replaced by "+RF_REFS[ref]+" in antenna matching network" if ref in RF_REFS else (
                "CH5 to CH8 hardware omitted" if ref in REMOVED else "Charger telemetry supply revision"))
            w.writerow([ref,reason])
    (OUT/"components-merged.json").write_text(json.dumps({"components":new},indent=2)+"\n",encoding="utf-8")
    with (OUT/"assembly-bom.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f)
        w.writerow(["References","Quantity","Value","MPN","LCSC","Populate","Assembly"])
        groups=defaultdict(list)
        for part in new:
            if part.get("kind") not in ("flag","pad","copper_field"):
                groups[(part["value"],part.get("mpn") or "",part.get("lcsc") or "",
                        "DNP" if part.get("populated") is False else "FIT",part.get("assembly","PCB_SMT"))].append(part["ref"])
        for identity,refs in sorted(groups.items()):
            w.writerow([",".join(refs),len(refs),*identity])
    return by_ref


def verify(expected_parts, cli):
    src = OUT/f"{PROJECT}.kicad_sch"
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)/"native.xml"
        subprocess.run([cli,"sch","export","netlist","--format","kicadxml","-o",str(dest),str(src)],check=True)
        old = ET.parse(BASE/"curalink-rev-a.net.xml")
        new = ET.parse(dest)
        def pinmap(xml):
            return {(n.get("ref"),n.get("pin")):net.get("name")
                    for net in xml.findall("./nets/net") for n in net.findall("node")}
        old_pins, new_pins = pinmap(old), pinmap(new)
        old_refs={c.get("ref") for c in old.findall("./components/comp")}
        new_refs={c.get("ref") for c in new.findall("./components/comp")}
        assert REMOVED.issubset(old_refs)
        expected={r:p for r,p in expected_parts.items() if p.get("kind")!="flag"}
        assert new_refs==expected.keys(),new_refs^expected.keys()
        checks=[]
        changes=[]
        total=0
        for ref,part in expected.items():
            for pin,net in part["pins"].items():
                actual=new_pins.get((ref,pin))
                if net is None:
                    assert actual is None or actual.startswith("unconnected-"),(ref,pin,net,actual)
                else:
                    assert actual and actual.split("/")[-1]==net,(ref,pin,net,actual)
                if ref not in old_refs:
                    checks.append([ref,pin,actual])
                elif net and net!=old_pins.get((ref,pin)):
                    changes.append([ref,pin,old_pins.get((ref,pin)),net])
                total+=1
        # Compare every physical landing pad to the symbol's pin set.
        allpads=0
        for comp in new.findall("./components/comp"):
            ref=comp.get("ref")
            lib,name=comp.findtext("footprint").split(":")
            library=(OUT/"CuraLinkFour.pretty") if lib=="CuraLinkFour" else (BASE/"pcb"/"footprints"/"CuraLink.pretty")
            pad_ids=set(re.findall(r'\(pad\s+"([^"]+)"', (library/(name+".kicad_mod")).read_text(encoding="utf-8")))
            assert pad_ids==set(expected[ref]["pins"]),(ref,pad_ids,expected[ref]["pins"].keys())
            allpads+=len(pad_ids)
        shutil.copyfile(dest,OUT/"curalink-four-coax.net.xml")
        erc = Path(tmp)/"erc.json"
        subprocess.run([cli,"sch","erc","--format","json","-o",str(erc),str(src)],check=True)
        data=json.loads(erc.read_text(encoding="utf-8"))
        issues=[v for s in data["sheets"] for v in s["violations"]]
        report=dict(kicad=data.get("kicad_version"), retained_components=len(old_refs&new_refs),
                    removed_components=len(old_refs-new_refs), new_components=len(new_refs-old_refs),
                    compared_design_pin_nets=total, compared_unique_footprint_pads=allpads, changed_pins=changes, new_pins=checks,
                    errors=[v for v in issues if v.get("severity")=="error"],
                    other_erc=[(v.get("type"),v.get("description")) for v in issues if v.get("severity")!="error"])
        (OUT/"native-verification.json").write_text(json.dumps(report,indent=2)+"\n")
        assert not report["errors"], report["errors"]


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli",default=os.getenv("KICAD_CLI") or shutil.which("kicad-cli") or
                        r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
    args=parser.parse_args()
    verify(derive(),args.cli)
    subprocess.run([args.cli,"sch","export","pdf","--exclude-pdf-property-popups","-o",
                    str(OUT/"schematic.pdf"),str(OUT/f"{PROJECT}.kicad_sch")],check=True)

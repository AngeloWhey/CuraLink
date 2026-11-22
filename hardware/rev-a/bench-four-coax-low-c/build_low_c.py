"""Build the separate low-capacitance candidate using the tested four-coax generator."""
from copy import deepcopy
from pathlib import Path
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys

OUT=Path(__file__).resolve().parent
BASELINE=OUT.parent/"bench-four-coax"
sys.path.insert(0,str(BASELINE))
import build_variant as base
import check_stock

schem=base.cad
PAGE=schem.uid("max44280-candidate-preamps")


class LowC:
    def modify(self,parts):
        part={p["ref"]:p for p in parts}
        parts.remove(part["U101"])
        for ref in ("R1002","R1020","R1038","R1056","R1146"):
            p=part[ref]
            assert p["pins"]["2"]=="VMID"
            p["pins"]["2"]="VMID_RAW"
            p["notes"]="22 MΩ return to the bypassed midpoint divider (10k/10k, 2.2 uF)."
        spare=part["U109"]
        spare["pins"].update({"2":"VMID_RAW","1":"AFE_SPARE_A","14":"AFE_SPARE_A"})
        spare["units"][0].update(positive="VMID_RAW",negative="AFE_SPARE_A",output="AFE_SPARE_A",
                                 role="Spare unity-stable U109 A, local negative feedback")
        self.new=[]
        part["C1059"]["notes"]="Local 100 nF bypass for U631, AVDD to GND."
        for idx,channel in enumerate(("CH1","CH2","CH3","CH4","REF"),631):
            amp=dict(ref=f"U{idx}",value="MAX44280AXT+T",mpn="MAX44280AXT+T",lcsc="C2058813",
                     footprint="CuraLinkFour:SOT-363_SC-70-6",package="SC70-6",
                     pins={"1":channel+"_PLUS","2":"GND","3":channel+"_MINUS",
                           "4":channel+"_PRE","5":"AVDD_3V0","6":"AVDD_3V0"},
                     pin_names={"1":"IN+","2":"VSS","3":"IN-","4":"OUT","5":"SHDN_N","6":"VDD"},
                     pin_types={"1":"input","2":"power_in","3":"input","4":"output","5":"input","6":"power_in"},
                     source="https://www.analog.com/media/en/technical-documentation/data-sheets/MAX44280.pdf",
                     notes="Gain 11. SHDN_N tied to switched AVDD. Minimum stable gain 5. Use dedicated 100 nF bypass.",
                     assembly="PCB_SMT",populated=True)
            self.new.append(amp)
            if idx!=631:
                c=deepcopy(part["C610"])
                c.update(ref=f"C{idx}",pins={"1":"AVDD_3V0","2":"GND"},
                         footprint="CuraLink:C_0402_1005Metric",notes=f"U{idx} local 100 nF bypass.")
                self.new.append(c)
        parts.extend(self.new)

    def add_page(self,root):
        root=root.replace("CuraLink four-channel generator variant","CuraLink four-channel low-capacitance candidate")
        tag='(sheet_instances (path "/"'
        desc=(f'(sheet (at 275 152) (size 110 25) (stroke (width 0) (type default)) '
              f'(fill (color 0 0 0 0)) (uuid {PAGE}) '
              '(property "Sheetname" "Low-capacitance preamps" (at 277 154 0) (effects (font (size 1 1)))) '
              '(property "Sheetfile" "low-c-preamps.kicad_sch" (at 277 174 0) (effects (font (size 1 1)))) '
              f'(instances (project "{base.PROJECT}" (path "/{base.ROOT_UUID}" (page "16")))))\n')
        libs={schem.lib_key(p):schem.make_lib(p) for p in self.new}
        page=[f'(kicad_sch (version 20230121) (generator eeschema) (uuid {schem.uid("low-c-file")}) (paper "A3")',
              '(title_block (title "Protected input preamps") (date "2026-11-22") (rev "Bench candidate"))',
              '(lib_symbols '+"\n".join(v.replace(f'(symbol "{k}"',f'(symbol "CuraLink:{k}"',1) for k,v in libs.items())+')',
              schem.text_line("Four signal preamps and shared REF   /   gain 11",20,16,2),
              schem.text_line("Each stage uses its channel-sheet 10 k / 1 k feedback. SHDN_N follows AVDD. C1059 serves U631.",20,23),
              schem.text_line("All five 22 M input bias returns land at VMID_RAW. The filter and gain networks retain VMID beyond R1149.",20,30)]
        for p in self.new:
            idx=int(p["ref"][1:])-631
            x=58.42+(idx%3)*119.38
            y=60.96+(idx//3)*76.2+(30.48 if p["ref"].startswith("C") else 0)
            page.append(schem.instance(p,schem.blocks(p)[0],x,y,f"/{base.ROOT_UUID}/{PAGE}"))
        page.append(f'(sheet_instances (path "/{base.ROOT_UUID}/{PAGE}" (page "16")))\n)')
        (OUT/"low-c-preamps.kicad_sch").write_text("\n".join(page)+"\n",encoding="utf8")
        return root.replace(tag,desc+tag)


def delta():
    def read(folder):
        return {p["ref"]:p for p in json.loads((folder/"components-merged.json").read_text(encoding="utf8"))["components"]}
    old,new=read(BASELINE),read(OUT)
    with (OUT/"low-c-delta.csv").open("w",newline="") as h:
        w=csv.writer(h)
        w.writerow(["Reference","Change","MPN","LCSC","Existing nets","Candidate nets"])
        for ref in sorted(old.keys()|new.keys()):
            a,b=old.get(ref,{}),new.get(ref,{})
            if a==b: continue
            w.writerow([ref,"Added" if not a else "Removed" if not b else "Modified",
                        (b or a)["mpn"], (b or a)["lcsc"],json.dumps(a.get("pins")),json.dumps(b.get("pins"))])


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli",default=os.getenv("KICAD_CLI") or shutil.which("kicad-cli") or r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
    parser.add_argument("--refresh-stock",action="store_true")
    args=parser.parse_args()
    base.OUT=OUT
    dest=OUT/"CuraLinkFour.pretty"
    dest.mkdir(exist_ok=True)
    for f in (BASELINE/"CuraLinkFour.pretty").glob("*.kicad_mod"):
        shutil.copyfile(f,dest/f.name)
    base.verify(base.derive(LowC()),args.cli)
    subprocess.run([args.cli,"sch","export","pdf","--exclude-pdf-property-popups","-o",str(OUT/"schematic.pdf"),
                    str(OUT/(base.PROJECT+".kicad_sch"))],check=True)
    delta()
    if args.refresh_stock:
        check_stock.OUT=OUT
        check_stock.main()

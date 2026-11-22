"""Emit the two bench RF circuit sheets and check every pin against KiCad XML."""
from pathlib import Path
import csv
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools/hardware"))
import build_reva as cad

DATA = HERE / "population.csv"


def main():
    with DATA.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    checks = {}
    for board in ("tx", "rx"):
        name = board + "-matching"
        cad.PROJECT = name
        design_id = cad.uid("bench-rf:" + name)
        folder = HERE / board
        folder.mkdir(exist_ok=True)
        parts = []
        for row in (r for r in rows if r["board"] == board):
            nets = row["pins"].split("|")
            part = dict(ref=row["ref"], value=row["value"], mpn=row["mpn"], lcsc=row["lcsc"],
                        footprint=row["footprint"], pins={str(i): n or None for i, n in enumerate(nets, 1)},
                        pin_names=dict(zip(map(str, range(1, len(nets)+1)), row["names"].split("|"))))
            part["populated"] = row["population"] != "DNP"
            if len(nets) == 1:
                part["kind"] = "pad"
            parts.append((part, float(row["x"]), float(row["y"])))
        symbols = {cad.lib_key(c):cad.make_lib(c) for c, _, _ in parts}
        embedded = [symbol.replace('"' + key + '"', '"CuraLink:' + key + '"', 1)
                    for key, symbol in symbols.items()]
        lines = [f'(kicad_sch (version 20230121) (generator curalink_generator) (uuid {design_id}) (paper "A4")',
                 '(lib_symbols ' + "\n".join(embedded) + ')',
                 cad.text_line(name.upper() + " | CuraLink fixed-coil bench receiver study", 12.7, 12.7, 2.2),
                 cad.text_line("Assembly trial values. Check capacitor RF current, tuning and thermal rise on the assembled fixture.", 12.7, 19.05),
                 cad.text_line("Coil terminals are copper landings for the published spiral. Keep both leads short.", 12.7, 24.13),
                 cad.text_line("TX return and receiver ground are galvanically separate. Both RX AC terminals float relative to DC ground.", 12.7, 29.21)]
        for part,x,y in parts:
            symbol = cad.instance(part,cad.blocks(part)[0],x,y,"/"+design_id)
            if not part["populated"]:
                symbol = symbol.replace("(on_board yes)", "(on_board yes) (dnp yes)", 1)
            lines.append(symbol)
        lines += ['(sheet_instances (path "/" (page "1")))', ')']
        source = folder / (name+".kicad_sch")
        source.write_text("\n".join(lines)+"\n", encoding="utf-8")
        (folder / (name+".kicad_pro")).write_text(json.dumps({"meta":{"filename":name+".kicad_pro","version":1}},indent=2)+"\n")
        library = '(kicad_symbol_lib (version 20220914) (generator curalink_generator)\n' + "\n".join(symbols.values()) + '\n)\n'
        (folder / "CuraLink.kicad_sym").write_text(library, encoding="utf-8")
        (folder / "sym-lib-table").write_text('(sym_lib_table (version 7) (lib (name "CuraLink")(type "KiCad")(uri "${KIPRJMOD}/CuraLink.kicad_sym")(options "")(descr "")))\n')
        cli = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli") or r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
        xml = folder / (name+".xml")
        subprocess.run([cli, "sch","export","netlist","--format","kicadxml","-o",str(xml),str(source)], check=True)
        subprocess.run([cli, "sch","erc","--format","json","--exit-code-violations","-o",str(folder/"erc.json"),str(source)],check=True)
        root = ET.parse(xml)
        actual = {(node.get("ref"),node.get("pin")):net.get("name")
                  for net in root.findall("./nets/net") for node in net.findall("node")}
        expected = {(c["ref"],p):n for c,_,_ in parts for p,n in c["pins"].items()}
        for key, wanted in expected.items():
            if wanted is None:
                assert actual.get(key, "unconnected").startswith("unconnected"), (key,actual.get(key))
            else:
                assert actual.get(key)==wanted, (key, wanted, actual.get(key))
        assert not set(actual).difference(expected)
        dnp = {c["ref"] for c, _, _ in parts if not c["populated"]}
        exported_dnp = {c.get("ref") for c in root.findall("./components/comp")
                        if c.find("./property[@name='dnp']") is not None}
        assert dnp == exported_dnp, (dnp, exported_dnp)
        checks[board] = dict(references=len(parts), physical_pins=len(expected),
                             unpopulated_trim=sorted(dnp), verified=True)
    (HERE/"verification.json").write_text(json.dumps(checks,indent=2)+"\n")


if __name__ == "__main__":
    main()

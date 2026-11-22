"""Snapshot real MCU/interface nets and primary-source provenance; no CAD edits."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIMARY = {
    "mlpf-wb-04d3": ("https://www.st.com/resource/en/datasheet/mlpf-wb-04d3.pdf", "DS14446 Rev6, section3.1/Figures13-14"),
    "an6335": ("https://www.st.com/resource/en/application_note/an6335-mlpfwb-and-mlpfnrg-pcb-design-guidelines-and-reference-hardware-stmicroelectronics.pdf", "Rev1, section6/Figure13"),
    "an5948": ("https://www.st.com/resource/en/application_note/an5948-how-to-develop-rf-hardware-using-stm32wba-mcus-stmicroelectronics.pdf", "Rev4, sections7.1-7.9/Figure29"),
    "an2834": ("https://www.st.com/resource/en/application_note/an2834-how-to-optimize-the-adc-accuracy-in-the-stm32-mcus-stmicroelectronics.pdf", "Rev10, sections3.2.11/4.2.11-4.2.14"),
    "an2867": ("https://www.st.com/resource/en/application_note/an2867-guidelines-for-oscillator-design-on-stm8afals-and-stm32-mcusmpus-stmicroelectronics.pdf", "Rev24, section7.1"),
    "stm32wba52cg": ("https://www.st.com/resource/en/datasheet/stm32wba52cg.pdf", "DS14127 Rev10, Table24/Figure14/sections3.12.1 and5.3.20"),
    "johanson-antenna-rev4": ("https://www.johansontechnology.com/docs/3827/Antenna-2450AT18A0100001E-Rev4.0.pdf", "36S0021A Rev4.0, pages2-3"),
    "jti-antenna-mounting": ("https://www.johansontechnology.com/docs/2/jti-antenna-mounting.pdf", "January2006, page7 matching topology")}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fetch(item):
    name, (url, sections) = item
    target = HERE / (name + ".pdf")
    row = {"url": url, "sections": sections, "primary_web_read": True}
    old = ROOT / "hardware/rev-a/mcu/sources/johanson-antenna-rev4.pdf"
    try:
        if name == "johanson-antenna-rev4" and old.exists():
            shutil.copyfile(old, target)
            row["cached_copy_from"] = old.relative_to(ROOT).as_posix()
        else:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            body = urllib.request.urlopen(req, timeout=20).read()
            if not body.startswith(b"%PDF"):
                raise ValueError("not a PDF response")
            target.write_bytes(body)
        row.update({"local_file": target.relative_to(ROOT).as_posix(), "sha256": digest(target), "bytes": target.stat().st_size})
    except Exception as exc:
        row["download_limitation"] = str(exc)
    return row

paths = [ROOT / name for name in ["hardware/rev-a/mcu/mcu-components.json",
    "hardware/rev-a/interface/interface-components.json", "hardware/rev-a/power/power-components.json",
    "hardware/rev-a/afe/afe-pin-nets.json"]]
with ThreadPoolExecutor(max_workers=8) as pool:
    sources = list(pool.map(fetch, PRIMARY.items()))
manifest = {"checked_date": "2026-10-02", "timezone": "America/New_York",
    "evidence_scope": "Schematic/component review; no routed-PCB SI extraction or measured crosstalk",
    "canonical_snapshots": [{"file": p.relative_to(ROOT).as_posix(), "sha256": digest(p)} for p in paths],
    "sources": sources,
    "workspace_pcb_files_found": [p.relative_to(ROOT).as_posix() for pattern in ["*.kicad_pcb", "*.PcbDoc"] for p in ROOT.rglob(pattern)]}
(HERE / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
selected = []
for path in paths[:2]:
    content = json.loads(path.read_text())
    selected.extend({k: c.get(k) for k in ["ref", "value", "mpn", "package", "pins", "pin_names", "populated", "notes"]}
        for c in content["components"])
(HERE / "reviewed-net-snapshot.json").write_text(json.dumps({"checked_date": "2026-10-02", "components": selected}, indent=2) + "\n")
print("Primary sources:", len(sources), "local PDFs:", sum("local_file" in s for s in sources), "MCU/interface parts:", len(selected))

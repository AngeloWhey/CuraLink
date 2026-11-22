"""Hash the local manufacturer evidence and canonical records for the audit."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
URLS = {
    "tps25200": "https://www.ti.com/lit/ds/symlink/tps25200.pdf",
    "bq25185": "https://www.ti.com/lit/ds/symlink/bq25185.pdf",
    "tps7a20": "https://www.ti.com/lit/ds/symlink/tps7a20.pdf",
    "tlv3011b": "https://www.ti.com/lit/ds/symlink/tlv3011b.pdf",
    "sn74lvc1g17": "https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf",
    "sn74lvc1g04": "https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf",
    "dmp2035u": "https://www.diodes.com/datasheet/download/DMP2035U.pdf",
    "ao3400a": "https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf",
    "bat54": "https://www.diodes.com/datasheet/download/BAT54.pdf",
    "bq2973": "https://www.ti.com/lit/ds/symlink/bq2973.pdf",
    "tlv9004": "https://www.ti.com/lit/ds/symlink/tlv9004.pdf",
    "tlv9054": "https://www.ti.com/lit/ds/symlink/tlv9054.pdf",
    "tpd4e05u06": "https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf",
    "stm32wba52cg": "https://www.st.com/resource/en/datasheet/stm32wba52cg.pdf",
}
def record(path):
    return {"file": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

manifest = {"checked_date": "2026-10-02", "timezone": "America/New_York",
    "scope": "Independent physical-pad and fault-boundary review; no canonical edits",
    "manufacturer_sources": [{"url": url, **record(HERE / (name + ".pdf"))}
        for name, url in URLS.items() if (HERE / (name + ".pdf")).is_file()],
    "canonical_snapshots": [record(ROOT / name) for name in [
        "hardware/rev-a/power/power-components.json", "hardware/rev-a/afe/afe-pin-nets.json",
        "hardware/rev-a/mcu/mcu-components.json"]],
    "remote_only_sources": [
        {"url": "https://www.onsemi.com/download/data-sheet/pdf/ss19-d.pdf",
         "evidence": "Primary web PDF read succeeds; shell download HTTP403"},
        {"url": "https://www.st.com/resource/en/datasheet/stm32wba52cg.pdf",
         "evidence": "Primary web PDF read, DS14127 Rev10; Table1 includes selected STM32WBA52CG. Replaces variant-ambiguous WBA55UE alias."},
        {"url": "https://www.st.com/resource/en/application_note/an4899-stm32-microcontroller-gpio-configuration-for-hardware-settings-and-lowpower-consumption-stmicroelectronics.pdf",
         "evidence": "Previously verified primary source and MCU constraints; download retry timed out"}],
    "caution": "eFuse/D501 physical-pad and R511 resistor-range repairs happened during the review; snapshots are post-repair. Manufacturer SPICE pin order is not physical pad numbering."}
(HERE / "protection-audit-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(len(manifest["manufacturer_sources"]), "manufacturer PDFs hashed")

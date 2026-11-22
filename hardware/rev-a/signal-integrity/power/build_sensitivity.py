"""Focused AFE supply/reference sensitivities; no canonical source is modified."""
from pathlib import Path
import hashlib
import json
import re

base = Path(__file__).resolve().parent
root = base.parents[3]
source_dir = root / "hardware/rev-a/ltspice/afe"
canonical = source_dir / "canonical-afe.lib"
original = canonical.read_text(encoding="utf-8")
derived, count = re.subn(r"(?m)^C1058 VMID 0 4\.7e-06$", "C1058 VMID 0 {CMID_F}", original)
assert count == 1, count
target = base / "canonical-afe-sensitivity.lib"
target.write_text("* Canonical circuit copied; only C1058 is parameterized for 4.7uF/2uF sensitivity.\n" + derived, encoding="utf-8")
afe = json.loads((root / "hardware/rev-a/afe/afe-pin-nets.json").read_text(encoding="utf-8"))
amp_outputs = sorted({unit["output"] for part in afe["components"] for unit in part.get("units", [])})
traces = sorted(set(amp_outputs) | {"ADC_IN_1", "ADC_IN_2", "VMID_RAW", "VMID_BUF", "VMID", "AVDD_3V0"})
common = '''* Normalized small-signal transfer, not a physical 1V/1A neural input.
* Original TI family equations; nominal passives except C1058 effective-capacitance cases.
.include "../../ltspice/afe/models/tlv9002-namespaced.lib"
.include "../../ltspice/afe/models/tlv9052-namespaced.lib"
.include "canonical-afe-sensitivity.lib"
.options numdgt=7 plotwinsize=0
.temp 27
.step param CMID_F list 4.7u 2u
'''
inputs = "".join(f"VCH{n} SRC_CH{n} 0 DC 0 AC 0\n" for n in range(1, 9)) + "VREF SRC_REF 0 DC 0 AC 0\n"
save = ".save " + " ".join("V(" + t + ")" for t in traces) + " I(VDD)\n"
for name, excitation in [
    ("afe-avdd-ripple", "VDD AVDD_3V0 0 DC 3 AC 1\n"),
    ("afe-vmid-current", "VDD AVDD_3V0 0 DC 3 AC 0\nIVMID 0 VMID DC 0 AC 1\n"),
]:
    (base / (name + ".cir")).write_text(common + excitation + inputs + save + ".ac dec 80 1 1Meg\n.end\n", encoding="utf-8")
manifest = {
    "date_local": "2026-10-02", "timezone": "America/New_York",
    "canonical_file": "hardware/rev-a/ltspice/afe/canonical-afe.lib",
    "canonical_sha256": hashlib.sha256(canonical.read_bytes()).hexdigest(),
    "derived_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    "only_circuit_change": "C1058 from fixed4.7uF to CMID_F parameter, cases4.7uF and assumed minimum2uF.",
    "model_provenance": "../../ltspice/afe/models/model-provenance.json",
    "limitations": "No PCB parasitics, digital/BLE currents, real ADC core, regulator loop, mismatch, RF rectification or ground impedances. AC is linearized nominal family behavior, not hardware immunity.",
}
(base / "provenance.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("Generated two focused normalized AC sensitivity decks; canonical circuit unchanged.")

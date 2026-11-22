"""Minimal, documented PSpice boolean-XOR compatibility repair for LTspice."""
from pathlib import Path
import hashlib
import json
import re

BASE = Path(__file__).resolve().parent
ORIGINAL = BASE / "sources/tps25200-spice/SLVMA73/tps25200_trans.lib"
MODELS = BASE / "models"
MODELS.mkdir(exist_ok=True)
text = ORIGINAL.read_bytes().decode("cp1252", errors="replace")
pattern = r"V\(A\)\s*>\s*\{VTHRESH\}\s*\^\s*\+\s*V\(B\)\s*>\s*\{VTHRESH\}"
replacement = "((V(A) > {VTHRESH}) != (V(B) > {VTHRESH}))"
changed, count = re.subn(pattern, replacement, text)
assert count == 2, count
target = MODELS / "tps25200-ltspice-compat.lib"
target.write_text(
    "* LTspice compatibility copy of TI's TPS25200_TRANS macro.\n"
    "* Only two PSpice boolean XOR caret expressions changed to parenthesized !=.\n"
    "* No transistor, threshold, delay, component or current values changed.\n"
    "* Original manufacturer model and copyright follow; keep source ZIP for provenance.\n"
    + changed,
    encoding="utf-8",
)
manifest = {
    "original": str(ORIGINAL.relative_to(BASE)).replace("\\", "/"),
    "original_sha256": hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
    "compatibility_copy": str(target.relative_to(BASE)).replace("\\", "/"),
    "compatibility_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    "changes": ["Two boolean XOR expressions in XOR2_BASIC_GEN/XNOR2_BASIC_GEN: PSpice ^ becomes parenthesized inequality !=; LTspice otherwise interprets ^ as exponentiation."],
    "number_expressions_changed": count,
    "unchanged": "All electrical numerical parameters and all other model expressions.",
    "limits": "This port is a vendor-derived macro, not manufacturer validation of LTspice behavior or guaranteed device safety. Thermal and statistical limits require datasheet/bench verification.",
}
(MODELS / "tps25200-provenance.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest, indent=2))

# Vendor libraries reuse a generic helper name. Isolate that symbol for a
# coupled TPS25200/TPS7A20 deck; this is a name change, not an electrical edit.
ldo_source = BASE / "sources/tps7a20-spice/tps7a20-adj_trans.lib"
ldo_text = ldo_source.read_bytes().decode("cp1252", errors="replace")
ldo_changed, ldo_count = re.subn(r"\bCOMPHYS_BASIC_GEN\b", "TPS7A20_COMPHYS_BASIC_GEN", ldo_text)
ldo_target = MODELS / "tps7a20-namespaced.lib"
ldo_target.write_text("* TI TPS7A20 macro: generic COMPHYS helper renamed to avoid a library collision.\n" + ldo_changed, encoding="utf-8")
(MODELS / "tps7a20-namespace-provenance.json").write_text(json.dumps({
    "original": str(ldo_source.relative_to(BASE)).replace("\\", "/"),
    "original_sha256": hashlib.sha256(ldo_source.read_bytes()).hexdigest(),
    "namespaced_copy": str(ldo_target.relative_to(BASE)).replace("\\", "/"),
    "namespaced_sha256": hashlib.sha256(ldo_target.read_bytes()).hexdigest(),
    "change": "All four COMPHYS_BASIC_GEN references/definition/end statements renamed TPS7A20_COMPHYS_BASIC_GEN; no electrical parameters or expressions changed.",
    "names_changed": ldo_count,
    "limits": "Generic voltage-programmed TI PSpice macro with no temperature or ground/quiescent-current model; coupled LTspice operation has not been validated by TI.",
}, indent=2), encoding="utf-8")

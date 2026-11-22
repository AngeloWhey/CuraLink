"""Read-only source pin/value audit of the ADS translation."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
ORIGINAL = ROOT / "hardware/rev-a/ltspice/afe/canonical-afe.lib"


def number(value):
    match = re.fullmatch(r"([+-]?[0-9.]+(?:[eE][+-]?[0-9]+)?)([kMGTmunpf]?)", value)
    if not match:
        raise ValueError(value)
    return float(match[1]) * {"": 1, "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}[match[2]]


def main():
    original = ORIGINAL.read_text(encoding="utf-8")
    native = (HERE / "afe-full-op.net").read_text(encoding="utf-8")
    original_passives, original_units = {}, {}
    for line in original.splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0][0] in "RC":
            original_passives[fields[0].lower()] = ([s.lower() for s in fields[1:3]], number(fields[3]))
        elif fields[0].startswith("XU"):
            original_units[fields[0].lower()] = ([s.lower() for s in fields[1:6]], fields[6].lower())
    native_passives, native_units = {}, {}
    for line in native.splitlines():
        match = re.match(r"(?:R|Cap_L):([^ ]+) +([^ ]+) +([^ ]+) +[RC]=([^ ]+)", line)
        if match and match[1].lower() in original_passives:
            native_passives[match[1].lower()] = ([match[2].lower(), match[3].lower()], number(match[4]))
        match = re.match(r"(tlv(?:9002|9052)_tlv(?:9002|9052)):(xu[^ ]+) +(.+)$", line)
        if match:
            native_units[match[2].lower()] = ([s.lower() for s in match[3].split()], match[1].lower())
    errors = []
    for key, value in original_passives.items():
        found = native_passives.get(key)
        if found is None or found[0] != value[0] or abs(found[1] - value[1]) > max(1e-20, abs(value[1]) * 1e-12):
            errors.append({"component": key, "source": value, "translated": found})
    for key, value in original_units.items():
        if native_units.get(key) != value:
            errors.append({"unit": key, "source": value, "translated": native_units.get(key)})
    report = {"date": "2026-11-22", "status": "PASS" if not errors else "FAIL", "source_sha256": hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(), "passives_checked": len(original_passives), "amplifier_pin_orders_checked": len(original_units), "mismatches": errors, "scope": "Exact top-level canonical passive nodes/values and five-pin family-macro mapping; does not itself validate nonlinear translation or physics", "noise_not_qualified": "Nettrans drops R model T_ABS=-273.15, so noise analyses are excluded"}
    (HERE / "translation-topology-check.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

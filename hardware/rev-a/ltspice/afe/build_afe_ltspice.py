"""Actual LTspice AFE decks generated from canonical physical pin/net records.

Pure name prefixes separate identical TI helper names. Original models remain
byte-for-byte copied; this generator does not change noise helpers or equations.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
MODELS = OUT / "models"
MODELS.mkdir(parents=True, exist_ok=True)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def library():
    pieces = []
    provenance = []
    sources = json.loads((ROOT / "hardware/rev-a/afe/vendor/sources.json").read_text())
    for part in ["tlv9002", "tlv9052"]:
        original = ROOT / f"hardware/rev-a/afe/vendor/{part}/{part}.lib"
        copied = MODELS / f"{part}-original.lib"
        shutil.copyfile(original, copied)
        body = original.read_text()
        identifiers = set(re.findall(r"(?im)^\s*\.(?:subckt|model)\s+(\S+)", body))
        prefixed = body
        for name in sorted(identifiers, key=len, reverse=True):
            prefixed = re.sub(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])",
                part.upper() + "_" + name, prefixed, flags=re.I)
        path = MODELS / f"{part}-namespaced.lib"
        path.write_text("* LTspice import: identifier prefixes only, original equations unchanged\n" + prefixed)
        pieces.append(path.name)
        src = next(s for s in sources if s["label"] == part)
        provenance.append({"part": part, "primary_url": src["url"], "archive_sha256": src["sha256"],
            "original_path": copied.relative_to(ROOT).as_posix(), "original_lib_sha256": digest(copied),
            "derived_path": path.relative_to(ROOT).as_posix(), "derived_lib_sha256": digest(path),
            "transformation": "Prefix every subcircuit/model identifier and reference only; no model equation, noise source, or temperature edits"})
    (MODELS / "model-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

def base():
    return ["* CuraLink Rev A: actual LTspice run with original TI family macro-model equations",
        ".include models/tlv9002-namespaced.lib", ".include models/tlv9052-namespaced.lib",
        ".options numdgt=7 plotwinsize=0", ".temp 27"]

def main():
    library()
    # Establish import/model validity before running an interconnected circuit.
    for part in ["tlv9002", "tlv9052"]:
        deck = base() + ["VDD avdd 0 3", "VIN plus 0 1.5", "RF out minus 10k", "RG minus 0 10k",
            f"XTEST plus minus avdd 0 out {part.upper()}_{part.upper()}", "RLOAD out 0 100k",
            ".op", ".save V(plus) V(minus) V(out) I(VDD)", ".end"]
        # Gain 2, expected output clips near 3V: use follower instead for OP gate.
        deck = [line for line in deck if not line.startswith(("RF ", "RG "))]
        deck = [line.replace("plus minus avdd 0 out", "plus out avdd 0 out") for line in deck]
        (OUT / f"import-{part}-op.cir").write_text("\n".join(deck) + "\n")
    components = json.loads((ROOT / "hardware/rev-a/afe/afe-pin-nets.json").read_text())["components"]
    mcu = json.loads((ROOT / "hardware/rev-a/mcu/mcu-components.json").read_text())["components"]
    power = json.loads((ROOT / "hardware/rev-a/power/power-components.json").read_text())["components"]
    def numeric(value):
        match = re.match(r"^([0-9.]+)(Meg|M|[pnumk]?)(?:ohm|[FVhH]|$|\s)", value)
        if not match:
            raise ValueError(f"Unrecognized canonical passive value: {value}")
        number, suffix = match.groups()
        return float(number) * {"": 1, "p": 1e-12, "n": 1e-9, "u": 1e-6,
            "m": 1e-3, "k": 1e3, "M": 1e6, "Meg": 1e6}[suffix]
    def net(name):
        return "0" if name == "GND" else name
    canonical = []
    all_amp_nodes = set()
    included = []
    for comp in components:
        ref = comp["ref"]
        if ref[0] in "RC" and ref[1:].isdigit():
            canonical.append(f"{ref} {net(comp['pins']['1'])} {net(comp['pins']['2'])} {numeric(comp['value']):.12g}")
            included.append(ref)
        elif comp.get("mpn") in ["TLV9004IRUCR", "TLV9054IRUCR"]:
            family = "TLV9002" if comp["mpn"] == "TLV9004IRUCR" else "TLV9052"
            for unit in comp["unit_blocks"]:
                if unit["unit"] == 5:
                    continue
                opins = unit["pins"]
                o, m, p = [net(comp["pins"][pin]) for pin in opins]
                all_amp_nodes.update([o, m, p])
                canonical.append(f"X{ref}_{unit['unit']} {p} {m} {net(comp['pins']['3'])} {net(comp['pins']['10'])} {o} {family}_{family}")
            included.append(ref)
    for comp in power:
        if comp["ref"] in ["R540", "R541", "C529"]:
            canonical.append(f"{comp['ref']} {net(comp['pins']['1'])} {net(comp['pins']['2'])} {numeric(comp['value']):.12g}")
            included.append(comp["ref"])
    for comp in mcu:
        if re.match(r"^R40[1-8]$|^C41[3-9]$|^C420$", comp["ref"]):
            canonical.append(f"{comp['ref']} {net(comp['pins']['1'])} {net(comp['pins']['2'])} {numeric(comp['value']):.12g}")
            included.append(comp["ref"])
    canonical = ["* Exact canonical AFE passives/amplifier units + VMID divider/filter + MCU 150R/470pF interfaces"] + canonical
    canonical += ["* External ESD clamp is capacitance-only; does not establish overvoltage/fault clamp behavior"]
    for channel in [f"CH{i}" for i in range(1, 9)] + ["REF"]:
        canonical += [f"R_SOURCE_{channel} SRC_{channel} FFC_{channel} 47k",
            f"C_FFC_{channel} FFC_{channel} 0 20p", f"C_TRACE_{channel} FFC_{channel} 0 2p",
            f"C_ESD_{channel} FFC_{channel} 0 0.5p"]
    (OUT / "canonical-afe.lib").write_text("\n".join(canonical) + "\n")
    manifest = {"canonical_afe_path": "hardware/rev-a/afe/afe-pin-nets.json",
        "canonical_afe_sha256": digest(ROOT / "hardware/rev-a/afe/afe-pin-nets.json"),
        "included_physical_refs": included, "amplifier_instances": 36,
        "notes": "Entire eight-channel AFE, shared REF/VMID/unused units, nine input paths; passive M suffix serialized as numerical ohms so 22 MOhm cannot become SPICE 22 milliohm"}
    (OUT / "canonical-extraction.json").write_text(json.dumps(manifest, indent=2) + "\n")
    save = ["V(AVDD_3V0)", "V(VMID_RAW)", "V(VMID_BUF)", "V(VMID)", "V(REF_PLUS)", "V(REF_PRE)",
        "V(CH1_PLUS)", "V(CH1_MINUS)", "V(CH1_PRE)", "V(CH1_DIFF_PLUS)", "V(CH1_DIFF_MINUS)", "V(CH1_HP)",
        "V(CH1_LP1_OUT)", "V(AFE_OUT_1)", "V(ADC_IN_1)", "V(FFC_CH1)", "V(SRC_CH1)", "V(SRC_REF)", "I(VDD)"]
    save += [f"V(AFE_OUT_{i})" for i in range(2, 9)]
    def circuit(analysis, drive="dc", supply="DC 3"):
        lines = base() + [".include canonical-afe.lib", f"VDD AVDD_3V0 0 {supply}", "VCOMMON COMMON_SRC 0 DC 0 AC 0"]
        for channel in [f"CH{i}" for i in range(1, 9)] + ["REF"]:
            source = "DC 0 AC 0"
            if drive == "differential":
                source = "DC 0 AC 0.5 0" if channel == "CH1" else "DC 0 AC 0.5 180"
            elif drive == "common":
                source = "DC 0 AC 1 0"
            elif drive == "step" and channel == "CH1":
                source = "PWL(0 0 10m 0 10.001m 0.1 600m 0.1 600.001m 0 1.2 0 1.200001 -0.1 1.8 -0.1 1.800001 0 2.4 0)"
            lines.append(f"V{channel} SRC_{channel} COMMON_SRC {source}")
        return lines + [".save " + " ".join(save)] + analysis + [".end"]
    decks = {
        "afe-full-op": circuit([".op"]),
        "afe-dc-differential-offset": circuit([".dc VCH1 -0.1 0.1 0.005"]),
        "afe-dc-common-offset": circuit([".dc VCOMMON -0.3 0.3 0.01"]),
        "afe-ac-differential": circuit([".ac dec 80 0.01 10Meg"], "differential"),
        "afe-ac-common": circuit([".ac dec 80 0.01 10Meg"], "common"),
        "afe-offset-recovery": circuit([".tran 0 2.4 0 100u"], "step"),
        "afe-offset-recovery-long": circuit([".tran 0 4 0 100u"], "step"),
        "afe-startup": circuit([".tran 0 2.4 0 100u startup"], "dc", "PWL(0 0 1m 3)")}
    decks["afe-full-op"] = [line + " " + " ".join(f"V({node})" for node in sorted(all_amp_nodes))
        if line.startswith(".save ") else line for line in decks["afe-full-op"]]
    leak = [f"RLEAK_{c['ref']} {net(c['pins']['1'])} {net(c['pins']['2'])} {{RLEAK}}"
        for c in components if c["ref"].startswith("C") and c["value"] == "10nF"]
    decks["afe-dc-capacitor-leakage"] = circuit(["* KEMET C0G datasheet IR lower limit: 100 GOhm at 25C for 10nF; 10G post-environment limit",
        "* 1G/100Meg are deliberate board/leakage sensitivity cases, not capacitor specifications",
        *leak, ".param RLEAK=100G", ".step param RLEAK list 100G 10G 1G 100Meg",
        ".dc VCH1 -0.1 0.1 0.005"])
    decks["afe-dc-capacitor-leakage"] = [line.replace(".temp 27", ".temp 25") for line in decks["afe-dc-capacitor-leakage"]]
    decks["afe-dc-capacitor-leakage-qualified"] = [line.replace(".step param RLEAK list 100G 10G 1G 100Meg", ".step param RLEAK list 100G 10G")
        for line in decks["afe-dc-capacitor-leakage"]]
    for name, deck in decks.items():
        (OUT / f"{name}.cir").write_text("\n".join(deck) + "\n")
    print(f"Wrote {len(decks)} full-AFE analysis decks, 36 family-model amplifier instances")

if __name__ == "__main__":
    main()

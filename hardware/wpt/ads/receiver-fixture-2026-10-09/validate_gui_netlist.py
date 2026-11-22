"""Run the generated native ADS candidate deck without changing the workspace."""
import json
import argparse
from pathlib import Path
import shutil
import subprocess
import run_receiver as rr

source = rr.HERE.parent / "gui-setup" / "RX_BAT54_LoadSweep_20261009-fresh-readback.net"
target = rr.HERE / "runs" / "native_BAT54_candidate_validation"
target.mkdir(parents=True, exist_ok=True)
deck = target / "native_candidate.ckt"
parser = argparse.ArgumentParser()
parser.add_argument("--read-only", action="store_true")
args = parser.parse_args()
if not args.read_only:
    shutil.copy2(source, deck)
    sim = rr.ads.CircuitSimulator(hpeesof_dir=str(rr.ADS_ROOT))
    proc = subprocess.run([str(rr.ADS_ROOT / "bin" / "hpeesofsim.exe"), str(deck),
                           "--dataset-name=native_candidate", "-T4"], cwd=target,
                          env=sim._env, capture_output=True, text=True)
    (target / "simulator.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"ADS exit {proc.returncode}; see {target / 'simulator.log'}")
with rr.dataset.open(target / "native_candidate.ds") as ds:
    blocks = ds.varblock_names
    df = ds["HB1.HB"].to_dataframe().reset_index()
    equations = {}
    for name in blocks:
        if name == "HB1.HB":
            continue
        vb = ds[name].to_dataframe().reset_index()
        for column in vb.columns:
            if column in ("freq", "__i"):
                continue
            value = complex(vb[column].iloc[0])
            equations[column] = {"real": value.real, "imag": value.imag}
print("blocks", blocks)
print("columns", df.columns.tolist())
df["Vin0"] = df["Vin_src"]
df["TX_Probe.i"] = df["I_SRC.i"]
for number in range(1, 5):
    # ADS's native output stores zero current on the ground-side diode pins.
    # Use the non-ground cathode with reversed sign for the two lower diodes.
    if number in (1, 3):
        df[f"D{number}_Probe.i"] = -df[f"DIODE{number}.P2.pinCurrent.i"]
    else:
        df[f"D{number}_Probe.i"] = df[f"DIODE{number}.P1.pinCurrent.i"]
best = json.loads((rr.HERE / "bat54-joint-search-best.json").read_text())
caps = tuple(best[key] for key in rr.CAP_NAMES)
m = rr.metrics(df, 23.5, 208.333333, caps, diode="bat54")
m["evidence"] = "Actual ADS simulation of fresh OA readback netlist generated from copied native candidate cell"
m["source_netlist"] = str(source)
m["native_aele_equations"] = equations
(target / "metrics.json").write_text(json.dumps(m, indent=2))
print(json.dumps(m, indent=2))

"""ADS review of fixed published coils and the authored charger-load envelope.

No geometry/coil optimization, original workspace edits or hardware acceptance.
The SDD remains a static assumed input law, not a TI charger/cell macromodel.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("charger_review_reference", HERE.parent / "charger/run_charger_fixture.py")
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)
rr = cm.rr


def matrix_deck():
    deck = cm.hb_deck(3.7, 23.5)
    deck = deck.replace("IPHASE=0.02\n", "BASE_PHASE=0.020\nOVERHEAD=0\nIPHASE=BASE_PHASE*(1+OVERHEAD*0.06060606060606)\n")
    deck = deck.replace("IQACTIVE=0.00075\n", "IQACTIVE=0.00075+OVERHEAD*0.00025\n")
    deck = deck.replace("ICTRL=0.0008\n", "ICTRL=0.0008+OVERHEAD*0.0007\n")
    dimensions = (("VBAT", (3.2, 3.7, 4.0, 4.1)), ("BASE_PHASE", (0.020, 0.002, 0.0)), ("Pin_dBm", (23.0, 23.5)), ("OVERHEAD", (0, 1)))
    child = "HB1"
    for index, (variable, values) in enumerate(dimensions):
        plan = f"ReviewPlan{index}"
        deck += f'\nSweepPlan:{plan} ' + " ".join(f'SweepPlan[{i+1}]="{plan}_{i}"' for i in range(len(values))) + "\n"
        for i, value in enumerate(values):
            deck += f"SweepPlan:{plan}_{i} Pt={value:.12g}\n"
        deck += f'ParamSweep:ReviewSweep{index} SimInstanceName[1]="{child}" SweepVar="{variable}" SweepPlan="{plan}" StatusLevel=0\n'
        child = f"ReviewSweep{index}"
    return deck


def run_case(simulator, label, deck, preferred_block):
    directory = HERE / "power-runs" / label
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "power-review.ckt"
    source.write_text(deck, encoding="utf-8")
    started = time.monotonic()
    process = subprocess.run([str(rr.ADS_ROOT / "bin/hpeesofsim.exe"), str(source), "--dataset-name=power-review", "-T4"], cwd=directory, env=simulator._env, capture_output=True, text=True, timeout=240)
    (directory / "simulator.log").write_text(process.stdout + process.stderr, encoding="utf-8")
    status = {"exit_code": process.returncode, "elapsed_s": time.monotonic()-started, "deck_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "new_ADS_simulation": process.returncode == 0}
    (directory / "execution.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    if process.returncode:
        raise RuntimeError(f"ADS exit {process.returncode}: {directory}")
    with rr.dataset.open(directory / "power-review.ds") as data:
        names = list(data.varblock_names)
        print(label, "blocks", names, flush=True)
        name = preferred_block if preferred_block in names else next(n for n in names if n.endswith(preferred_block))
        frame = data[name].to_dataframe().reset_index()
    frame.to_csv(directory / "dataset.csv", index=False)
    return frame, directory, status


def main():
    simulator = rr.ads.CircuitSimulator(hpeesof_dir=str(rr.ADS_ROOT))
    rows = []
    frame, directory, status = run_case(simulator, "charger_matrix", matrix_deck(), "HB1.HB")
    keys = ["VBAT", "BASE_PHASE", "Pin_dBm", "OVERHEAD"]
    print("matrix columns", frame.columns.tolist(), flush=True)
    for group_values, group in frame.groupby(keys):
        vbat, base, pin, overhead = (float(v.real) if hasattr(v, "real") else float(v) for v in group_values)
        current = base*(1+overhead*0.06060606060606)
        iq, control = 0.00075+overhead*0.00025, 0.0008+overhead*0.0007
        metrics = cm.hb_metrics(group, vbat, pin, current, iq, control, .28, .15)
        metrics.update({"BASE_PHASE_A": base, "OVERHEAD_sensitivity": overhead, "new_ADS_simulation_date": "2026-11-22", "fixed_coils": True, "source_dataset": str(directory / "power-review.ds")})
        rows.append(metrics)
        print(f"VBAT={vbat:g}, phase={1000*current:.4f}mA, Pin={pin:g}, overhead={overhead:g}: RAW={metrics['Vdc_V']:.5f}V, CHGIN={metrics['CHG_IN_V']:.5f}V, Icharge={1000*metrics['derived_charge_current_mean_A']:.4f}mA, out-of-domain={metrics['out_of_model_domain']}", flush=True)
    rr.write_rows(HERE / "power-matrix.csv", rows)
    (HERE / "power-matrix.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    # This independent DC curve checks the static SDD's sign/compliance only.
    frame, directory, status = run_case(simulator, "sdd_dc_iv", cm.dc_deck(), "DC1.DC")
    frame.to_csv(HERE / "sdd-dc-iv.csv", index=False)
    print("DC columns", frame.columns.tolist(), flush=True)
    print("Completed fixed-coil matrix and SDD DC fixtures; no real charger/cell or raw OVP was modeled.", flush=True)


if __name__ == "__main__":
    main()

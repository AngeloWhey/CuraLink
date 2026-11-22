"""Focused receiver resistor operating-point and harmonic/stress confirmation."""
import json
from pathlib import Path
import run_receiver as rr

HERE = Path(__file__).resolve().parent
best = json.loads((HERE / "bat54-joint-search-best.json").read_text())
caps = tuple(best[key] for key in rr.CAP_NAMES)
sim = rr.ads.CircuitSimulator(hpeesof_dir=str(rr.ADS_ROOT))
rows = []
for pin in (23.5, 24.0, 25.0):
    for load in (208.333333333, 230.0):
        label = f"bat54_near_target_P{pin:g}_R{load:g}_H7"
        df, outdir, elapsed = rr.run_one(sim, pin, load, caps, 7, label=label, diode="bat54")
        m = rr.metrics(df, pin, load, caps, diode="bat54")
        m.update({"run_directory": str(outdir), "elapsed_s": elapsed})
        (outdir / "metrics.json").write_text(json.dumps(m, indent=2))
        rows.append(m)
        rr.write_rows(HERE / "bat54-near-target-matrix-H7.csv", rows)
        print(f"{label}: {m['Vdc_V']:.6f} V, {1e3*m['Pdc_W']:.6f} mW, reverse {m['diode_max_reverse_peak_V']:.6f} V", flush=True)
eligible = [row for row in rows if row["Rload_ohm"] < 209 and row["Pdc_W"] >= 0.120]
selected = min(eligible, key=lambda row: abs(row["Vdc_V"] - 5.0))
confirmed = []
for order in (15, 31, 63, 127):
    test_loads = (208.333333333, 1e6) if order <= 31 else (208.333333333,)
    for load in test_loads:
        pin = selected["Pin_dBm"]
        label = f"bat54_target_confirmation_P{pin:g}_R{load:g}_H{order}"
        df, outdir, elapsed = rr.run_one(sim, pin, load, caps, order, label=label, diode="bat54")
        m = rr.metrics(df, pin, load, caps, diode="bat54")
        m.update({"run_directory": str(outdir), "elapsed_s": elapsed})
        (outdir / "metrics.json").write_text(json.dumps(m, indent=2))
        confirmed.append(m)
        rr.write_rows(HERE / "bat54-target-confirmation.csv", confirmed)
        print(f"{label}: {m['Vdc_V']:.6f} V, {1e3*m['Pdc_W']:.6f} mW, reverse {m['diode_max_reverse_peak_V']:.6f} V", flush=True)
selected["evidence"] = "Near-5V resistor operating point selected for diagnostic confirmation; not hardware TX selection or charging validation"
(HERE / "bat54-near-target-selected.json").write_text(json.dumps(selected, indent=2))
print(json.dumps(selected, indent=2))

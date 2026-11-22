"""Summarize completed ADS runs without launching the simulator."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import run_receiver as rr

HERE = Path(__file__).resolve().parent
old = pd.read_csv(HERE / "baseline-matrix-H7.csv")
new = pd.read_csv(HERE / "bat54-joint-search-best-matrix-H7.csv")
old["fixture"] = "Current diode / current capacitors"
new["fixture"] = "BAT54 candidate / best searched capacitors"
combined = pd.concat([old, new], ignore_index=True)
combined.to_csv(HERE / "comparison-matrix-H7.csv", index=False)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), layout="constrained")
colors = {20: "#147d92", 23: "#8a58b4", 26: "#d67a20"}
for frame, style, name in ((old, "--", "current seed"), (new, "-", "BAT54 candidate + tuned")):
    for power in (20, 23, 26):
        data = frame[(frame.Pin_dBm == power) & (frame.Rload_ohm < 1e5)]
        axes[0].plot(data.Rload_ohm, 1e3 * data.Pdc_W, linestyle=style,
                     color=colors[power], marker="o", markersize=3,
                     label=f"{power} dBm, {name}")
        axes[1].plot(data.Rload_ohm, data.Vdc_V, linestyle=style,
                     color=colors[power], marker="o", markersize=3)
axes[0].axhline(120, color="#606770", linewidth=1, linestyle=":", label="120 mW modeled load target")
axes[1].axhline(5, color="#606770", linewidth=1, linestyle=":")
axes[0].set_ylabel("Delivered DC power (mW)")
axes[1].set_ylabel("Raw rectifier output (V)")
for ax in axes:
    ax.set_xlabel("Resistive load (Ω)")
    ax.grid(alpha=0.2)
axes[0].legend(fontsize=7.2, loc="best")
fig.suptitle("Actual ADS HB resistor-load study — ideal matching capacitors, nominal coil model", fontsize=11)
fig.savefig(HERE / "receiver-sweep-results.png", dpi=180)
plt.close(fig)

# Independent postprocessing of each retained dataset verifies the power balance,
# source boundary and stress calculations with the final analysis code.
checks = []
for _, row in new.iterrows():
    runpath = Path(row.run_directory)
    with rr.dataset.open(runpath / "receiver.ds") as ds:
        df = ds["HB1.HB"].to_dataframe().reset_index()
    caps = tuple(row[key] for key in rr.CAP_NAMES)
    values = rr.metrics(df, row.Pin_dBm, row.Rload_ohm, caps, diode="bat54")
    values["run_directory"] = str(runpath)
    checks.append(values)
rr.write_rows(HERE / "bat54-best-postprocess-check.csv", checks)
balance = max(abs(x["power_balance_error_W"]) for x in checks)
focused = []
for filename in ("bat54-near-target-matrix-H7.csv", "bat54-target-confirmation.csv"):
    if not (HERE / filename).exists():
        continue
    revised = []
    frame = pd.read_csv(HERE / filename)
    if filename == "bat54-target-confirmation.csv":
        known = set(frame["run_directory"])
        for order in (63, 127):
            extra = HERE / "runs" / f"bat54_target_confirmation_P23.5_R208.333_H{order}" / "metrics.json"
            if extra.exists():
                record = json.loads(extra.read_text())
                if record.get("run_directory", str(extra.parent)) not in known:
                    record["run_directory"] = str(extra.parent)
                    frame = pd.concat([frame, pd.DataFrame([record])], ignore_index=True)
    for _, row in frame.iterrows():
        runpath = Path(row.run_directory)
        with rr.dataset.open(runpath / "receiver.ds") as ds:
            df = ds["HB1.HB"].to_dataframe().reset_index()
        caps = tuple(row[key] for key in rr.CAP_NAMES)
        values = rr.metrics(df, row.Pin_dBm, row.Rload_ohm, caps, diode="bat54")
        values["run_directory"] = str(runpath)
        (runpath / "metrics.json").write_text(json.dumps(values, indent=2))
        revised.append(values)
    rr.write_rows(HERE / filename, revised)
    focused.extend(revised)
final_target = max((record for record in focused if record["Rload_ohm"] < 209), key=lambda record: record["HB_order"])
final_target["evidence"] = "Actual ADS resistor-point numerical confirmation; Candidate caps and diode; hardware charging unvalidated"
(HERE / "bat54-target-confirmation-final.json").write_text(json.dumps(final_target, indent=2))
summary = {
    "recorded_local_date": "2026-10-09",
    "evidence": "Completed standalone ADS HB runs; resistor fixture only",
    "old_baseline_points": len(old),
    "candidate_best_matrix_points": len(new),
    "maximum_absolute_candidate_power_balance_error_W": balance,
    "candidate_best": json.loads((HERE / "bat54-joint-search-best.json").read_text()),
    "candidate_harmonic_check": pd.read_csv(HERE / "bat54-joint-search-best-harmonic-check.csv").to_dict(orient="records"),
    "near_target_and_light_load_confirmation": focused,
    "final_resistor_target_point": final_target,
    "hardware_charger_validation": False,
}
(HERE / "simulation-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps({"points": len(combined), "power_balance_error_W": balance,
                  "best_caps_pF": [summary["candidate_best"][key] for key in rr.CAP_NAMES]}, indent=2))

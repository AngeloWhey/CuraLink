"""Check finite LTspice outputs, export CSVs and plot declared model-level results."""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"
RESULTS.mkdir(exist_ok=True)


def raw_ascii(name):
    path = BASE / (name + ".raw")
    raw = path.read_bytes()
    text = raw.decode("utf-16" if raw.startswith(b"\xff\xfe") else "utf-8", errors="replace").replace("\r\n", "\n")
    head, values = text.split("Values:\n", 1)
    n = int(re.search(r"No\. Variables:\s*(\d+)", head).group(1))
    count = int(re.search(r"No\. Points:\s*(\d+)", head).group(1))
    variables = [line.split()[1] for line in head.split("Variables:\n", 1)[1].splitlines() if line.strip()]
    complex_data = "complex" in re.search(r"Flags:\s*(.*)", head).group(1)
    rows = []
    lines = values.splitlines()
    assert len(lines) == count * n, (name, len(lines), n, count)
    for point in range(count):
        block = lines[point * n:(point + 1) * n]
        fields = [block[0].split()[-1]] + [x.strip() for x in block[1:]]
        row = []
        for v in fields:
            if "nan" in v.lower() or "ind" in v.lower():
                row.append(complex(np.nan, np.nan) if complex_data else np.nan)
            elif complex_data:
                a, b = v.split(",")
                row.append(complex(float(a), float(b)))
            else:
                row.append(float(v))
        rows.append(row)
    data = np.asarray(rows)
    return {"variables": variables, "data": data, "complex": complex_data, "raw_sha256": hashlib.sha256(raw).hexdigest()}


def log_values(name):
    text = (BASE / (name + ".log")).read_text(encoding="utf-8", errors="replace")
    deck = (BASE / (name + ".cir")).read_text(encoding="utf-8", errors="replace")
    declared = set(re.findall(r"^\.meas\s+\w+\s+(\w+)", deck, re.I | re.M))
    result = {}
    for line in text.splitlines():
        m = re.match(r"([a-z0-9_]+):.*?=\s*([-+0-9.e]+)\b", line, re.I)
        if m and m.group(1) in declared:
            result[m.group(1)] = float(m.group(2))
    return result


def stepped_log_values(name, parameter, values):
    content = (BASE / (name + ".log")).read_text(encoding="utf-8")
    measurements = {}
    for label, body in re.findall(r"Measurement: (\w+)\n(.*?)(?=\nMeasurement:|\Z)", content, re.S):
        measurements[label] = [float(m.group(2)) for m in re.finditer(r"^\s*(\d+)\s+([-+0-9.e]+)\s", body, re.M)]
    assert all(len(v) == len(values) for v in measurements.values()), name
    return [{parameter: value, **{k: v[index] for k, v in measurements.items()}}
            for index, value in enumerate(values)]


def write_csv(path, headers, matrix):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(matrix)


records = {}
cases = [p.stem for p in BASE.glob("*.raw") if not p.name.endswith((".op.raw", ".log.raw"))]
for name in sorted(cases):
    parsed = raw_ascii(name)
    valid = np.isfinite(parsed["data"]).all()
    records[name] = {
        "raw_file": name + ".raw", "log_file": name + ".log",
        "raw_sha256": parsed["raw_sha256"], "points": len(parsed["data"]),
        "circuit_sha256": hashlib.sha256((BASE / (name + ".cir")).read_bytes()).hexdigest(),
        "finite": bool(valid), "nonfinite_values": int((~np.isfinite(parsed["data"])).sum()),
        "measurements": log_values(name),
        "model_kind": "AUTHORED_STATIC_BOUND" if name.startswith("static") else "TI_VENDOR_MACRO_WITH_DOCUMENTED_XOR_PORT" if name.startswith("vendor-efuse") else "TI_MACROS_WITH_XOR_PORT_AND_LDO_NAMESPACE" if name.startswith("vendor-protected") else "TI_VENDOR_MACRO",
        "accepted_for_analysis": bool(valid and name != "vendor-efuse-dc"),
    }
    if name == "vendor-efuse-dc":
        records[name]["rejection_reason"] = "Transient macro cannot establish valid DC latch/charge-pump states; NaN data and zero-output measurements are not device results. Use independent startup runs and explicit static model instead."
    elif not valid:
        raise RuntimeError("Non-finite data in intended result: " + name)
    if name == "vendor-field-dc":
        records[name]["interpretation_limit"] = "The negative-RAW subrange can exceed the comparator's recommended common-mode range; finite values do not qualify its reverse-fault logic state."
    elif name == "vendor-ldo-psrr":
        records[name]["interpretation_limit"] = "Generic typical macro only; its high-frequency curve is not accepted as guaranteed exact-part PSRR."


def column(parsed, key):
    return parsed["data"][:, parsed["variables"].index(key)]


static_rows = []
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
colors = {"low": "#3274a1", "typ": "#26916b", "high": "#c65a33"}
for corner in ["low", "typ", "high"]:
    for load in ["charger", "short"]:
        name = f"static-ovp-{corner}-{load}"
        parsed = raw_ascii(name)
        x = column(parsed, "V(wpt_protected)")
        y = column(parsed, "V(chg_in)")
        current = column(parsed, "I(BPASS)")
        power = column(parsed, "V(efuse_dissipation_w)")
        static_rows.extend(zip([corner] * len(x), [load] * len(x), x, y, current, power))
        if load == "charger":
            axes[0].plot(x, y, label=corner, color=colors[corner])
        else:
            axes[1].plot(x, power, label=corner, color=colors[corner])
for ax in axes:
    ax.axvspan(6.5, 18, color="#ddaa99", alpha=.15)
    ax.set_xlabel("eFuse IN after D501 (V)")
    ax.grid(alpha=.25)
    ax.legend(title="Declared corner")
axes[0].axhline(5.55, linestyle="--", color="gray", lw=.8)
axes[0].set_ylabel("CHG_IN steady voltage (V)")
axes[0].set_title("220 Ω test load; static threshold model")
axes[1].set_ylabel("Calculated eFuse power (W)")
axes[1].set_title("1 Ω fault; thermal shutdown omitted")
fig.suptitle("Authored DC bounds: voltage clamp, cutoff and current fault\nShaded input is abnormal stress outside 2.5–6.5 V operation")
fig.tight_layout()
fig.savefig(RESULTS / "ovp-static-boundaries.png", dpi=180)
plt.close(fig)
write_csv(RESULTS / "static-ovp-curves.csv", ["corner", "load", "efuse_input_V", "charger_input_V", "current_A", "dissipation_W"], static_rows)

parsed = raw_ascii("vendor-efuse-transient")
time = parsed["data"][:, 0]
raw = column(parsed, "V(wpt_raw)")
protected = column(parsed, "V(wpt_protected)")
chg = column(parsed, "V(chg_in)")
write_csv(RESULTS / "vendor-supply-fault-waveform.csv", parsed["variables"], parsed["data"])
recovery = np.where((time > .1) & (chg > 3.0))[0]
records["vendor-efuse-transient"]["recovery_first_above3V_seconds"] = float(time[recovery[0]]) if len(recovery) else None
peak = int(np.argmax(chg))
records["vendor-efuse-transient"]["peak_time_seconds"] = float(time[peak])
fig, axes = plt.subplots(2, 1, figsize=(10, 6))
axes[0].plot(time * 1000, raw, label="WPT_RAW", color="#466b90")
axes[0].plot(time * 1000, protected, label="IN after D501/C501", color="#d08b2d")
axes[0].plot(time * 1000, chg, label="CHG_IN", color="#26916b")
axes[0].set_xlabel("Time (ms)")
axes[0].set_ylabel("Voltage (V)")
axes[0].set_title("TI-derived transient macro: capacitor holds IN after source falls")
axes[0].legend()
mask = (time >= .0249) & (time <= .026)
axes[1].plot(time[mask] * 1000, chg[mask], color="#26916b")
axes[1].axhline(5.55, linestyle="--", color="#a14b38", label="5.55 V static bound")
axes[1].set_xlabel("Time (ms)")
axes[1].set_ylabel("CHG_IN voltage (V)")
axes[1].set_title("5 → 6.5 V source transition: modeled overshoot requires bench check")
axes[1].legend()
for ax in axes:
    ax.grid(alpha=.25)
fig.tight_layout()
fig.savefig(RESULTS / "supply-fault-transient.png", dpi=180)
plt.close(fig)

independent = stepped_log_values("vendor-efuse-independent-faults", "raw_input_V", [5, 6.5, 8.5, 10, 18])
write_csv(RESULTS / "vendor-independent-faults.csv", independent[0].keys(), [r.values() for r in independent])

coupled = raw_ascii("vendor-protected-control-transient")
write_csv(RESULTS / "vendor-protected-control-waveform.csv", coupled["variables"], coupled["data"])
fig, axes = plt.subplots(2, 1, figsize=(10, 6))
coupled_time = coupled["data"][:, 0]
for net, label in [("V(chg_in)", "CHG_IN"), ("V(ctrl_input)", "U503 IN"), ("V(ctrl_3v0)", "CTRL_3V0")]:
    axes[0].plot(coupled_time * 1000, column(coupled, net), label=label)
axes[0].set_xlabel("Time (ms)")
axes[0].set_ylabel("Voltage (V)")
axes[0].set_title("Coupled vendor-derived eFuse / control LDO; approximate D501 / D502")
axes[0].legend()
fast = raw_ascii("vendor-protected-control-fast-fault")
fast_rows = stepped_log_values("vendor-protected-control-fast-fault", "source_slew_s", [1e-6, 10e-6, 1e-3])
write_csv(RESULTS / "vendor-fast-fault-peaks.csv", fast_rows[0].keys(), [r.values() for r in fast_rows])
resets = np.where(np.diff(fast["data"][:, 0]) < 0)[0] + 1
segments = np.split(fast["data"], resets)
assert len(segments) == 3
for segment, slew in zip(segments, [1e-6, 10e-6, 1e-3]):
    window = (segment[:, 0] > .02495) & (segment[:, 0] < .0261)
    axes[1].plot((segment[window, 0] - .025) * 1e6,
                 segment[window, fast["variables"].index("V(chg_in)")],
                 label=f"5→18 V over {slew * 1e6:g} μs")
axes[1].axhline(5.55, color="gray", ls="--", label="Specified static 5.55 V limit")
axes[1].set_xlabel("Time since ramp begins (μs)")
axes[1].set_ylabel("CHG_IN (V)")
axes[1].set_title("Assumed 1 μF effective C501/C502; typical macros, no thermal model")
axes[1].legend(fontsize=8)
for axis in axes:
    axis.grid(alpha=.25)
fig.tight_layout()
fig.savefig(RESULTS / "protected-control-faults.png", dpi=180)
plt.close(fig)

thresholds = []
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for kind, output, axis in [("field", "V(field_absent)", axes[0]), ("uvlo", "V(bat_ok)", axes[1])]:
    for direction in ["rise", "fall"]:
        name = f"vendor-{kind}-{direction}"
        parsed = raw_ascii(name)
        x = parsed["data"][:, 0]
        y = column(parsed, output)
        initial = y[0] > 1.5
        transitions = np.where((y > 1.5) != initial)[0]
        assert len(transitions), name
        at = int(transitions[0])
        threshold = float((x[at] + x[at - 1]) / 2)
        row = {"function": kind, "direction": direction, "nominal_vendor_threshold_V": threshold, "sweep_step_V": abs(float(x[1] - x[0]))}
        thresholds.append(row)
        axis.plot(x, y, label=direction)
    axis.grid(alpha=.25)
    axis.legend()
    axis.set_ylabel("Comparator output (V)")
axes[0].set_xlim(1.8, 3.1)
axes[0].set_xlabel("WPT_RAW (V)")
axes[0].set_title("FIELD_ABSENT; CTRL held at 3 V")
axes[1].set_xlim(3.2, 4.1)
axes[1].set_xlabel("PACK+ (V)")
axes[1].set_title("BAT_OK; CTRL held at 3 V")
fig.tight_layout()
fig.savefig(RESULTS / "comparator-thresholds.png", dpi=180)
plt.close(fig)
write_csv(RESULTS / "vendor-comparator-thresholds.csv", thresholds[0].keys(), [r.values() for r in thresholds])

ldo_dc = raw_ascii("vendor-ldo-dc")
write_csv(RESULTS / "vendor-ldo-dc.csv", ldo_dc["variables"], ldo_dc["data"])
ldo_ac = raw_ascii("vendor-ldo-psrr")
freq = ldo_ac["data"][:, 0].real
out = column(ldo_ac, "V(out)")
psrr = -20 * np.log10(np.abs(out))
write_csv(RESULTS / "vendor-ldo-psrr.csv", ["frequency_Hz", "output_real_V_per_V", "output_imag_V_per_V", "ripple_ratio_V_per_V", "psrr_dB"], zip(freq, out.real, out.imag, np.abs(out), psrr))
psrr_points = {str(f): float(np.interp(math.log10(f), np.log10(freq), psrr)) for f in [100, 1000, 10000, 100000, 1000000]}
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].plot(column(ldo_dc, "V(ldo_in)"), column(ldo_dc, "V(out)"), color="#26916b")
axes[0].axvline(3.3, linestyle="--", color="gray", label="Accuracy headroom criterion")
axes[0].set_xlabel("LDO input (V)")
axes[0].set_ylabel("LDO output (V)")
axes[0].set_title("TI voltage-programmed macro\n15 mA declared load", fontsize=10)
axes[0].legend(fontsize=8)
axes[1].semilogx(freq, psrr, color="#466b90")
axes[1].set_xlabel("Frequency (Hz)")
axes[1].set_ylabel("Model PSRR (dB)")
axes[1].set_title("4 V IN, 3 V OUT, 10 μF\nTypical macro; high-frequency result unqualified", fontsize=10)
for ax in axes:
    ax.grid(alpha=.25)
fig.tight_layout()
fig.savefig(RESULTS / "ldo-sweep-and-psrr.png", dpi=180)
plt.close(fig)

summary = {
    "date_local": "2026-10-02", "simulator": "LTspice 26.0.2 for Windows",
    "measurement_kind": "SIMULATED, not measured hardware",
    "current_design": {"R511_ohm": 1000000, "R511_tolerance": 0.01,
                       "historical_results_excluded": "historical-r511-1p1M/"},
    "fixtures": records, "independent_vendor_fault_cases": independent,
    "comparator_nominal_vendor_thresholds": thresholds,
    "ldo_macro_psrr_dB": psrr_points,
    "coupled_fast_fault_peaks": fast_rows,
    "qualification": {
        "vendor_efuse_dc_rejected": True,
        "independent_vendor_transients_finite": True,
        "static_model_not_manufacturer_transistor_model": True,
        "charger_and_battery_vendor_simulated": False,
        "raw_rf_receiver_protected_by_efuse": False,
        "battery_pcm_qualified": False,
        "fabrication_release_granted": False,
    },
}
(RESULTS / "power-results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps({"cases": len(records), "accepted": sum(v["accepted_for_analysis"] for v in records.values()), "rejected": [k for k, v in records.items() if not v["accepted_for_analysis"]], "independent_faults": independent, "thresholds": thresholds, "psrr": psrr_points}, indent=2))

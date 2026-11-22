"""Export focused nominal AFE sensitivities plus explicit passive/current assumptions."""
from pathlib import Path
import csv
import hashlib
import json
import re
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

base = Path(__file__).resolve().parent
root = base.parents[3]
sys.path.insert(0, str(root / "hardware/rev-a/ltspice/afe"))
from read_ltspice_raw import read_raw

caps = [4.7e-6, 2e-6]
outputs = {}
fixtures = {}
all_rows = []
for name in ["afe-avdd-ripple", "afe-vmid-current"]:
    raw_path = base / (name + ".raw")
    raw = read_raw(raw_path)
    log = (base / (name + ".log")).read_text(encoding="utf-8", errors="replace")
    assert "Total elapsed time" in log and "Fatal" not in log
    resets = np.flatnonzero(np.diff(raw.trace("frequency").real) < 0) + 1
    segments = np.split(raw.data, resets)
    assert len(segments) == 2, (name, len(segments))
    op = read_raw(base / (name + ".op.raw"))
    adc_dc = float(op.trace("V(ADC_IN_1)")[-1])
    assert 1.4 < adc_dc < 1.6, adc_dc
    for key in [n for n in op.names if n.startswith("V(") and n not in ["V(avdd_3v0)"]]:
        assert np.isfinite(op.trace(key)).all()
    fixtures[name] = {"raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                      "deck_sha256": hashlib.sha256((base / (name + ".cir")).read_bytes()).hexdigest(),
                      "finite_points": len(raw.data), "ADC1_DC_V": adc_dc,
                      "model_kind": "Original-equation TI family macros, nominal linearized AC"}
    actual_caps = [float(value) for value in re.findall(r"(?mi)^\.step cmid_f=([-+0-9.e]+)", log)]
    assert len(actual_caps) == len(segments) and set(actual_caps) == set(caps), actual_caps
    fixtures[name]["actual_step_capacitances_F"] = actual_caps
    for cap, segment in zip(actual_caps, segments):
        frequency = segment[:, 0].real
        traces = {net: segment[:, raw.names.index("V(" + net + ")")] for net in
                  ["avdd_3v0", "vmid_raw", "vmid_buf", "vmid", "adc_in_1", "adc_in_2"]}
        # First-order ADC code perturbation: reference is AVDD, DC output about1.503V.
        adc_equivalent = traces["adc_in_1"] - (adc_dc / 3) * traces["avdd_3v0"]
        key = f"{name}/{cap:g}F"
        outputs[key] = {"f": frequency, **traces, "adc_equivalent": adc_equivalent}
        for i, freq in enumerate(frequency):
            all_rows.append([name, cap, freq, abs(traces["vmid"][i]),
                             abs(traces["adc_in_1"][i]), abs(adc_equivalent[i])])

def point(data, net, frequency):
    axis = np.log(data["f"])
    value = np.interp(np.log(frequency), axis, data[net].real) + 1j*np.interp(np.log(frequency), axis, data[net].imag)
    return float(abs(value))

summary = {"date_local": "2026-10-02", "timezone": "America/New_York", "fixtures": fixtures,
           "frequency_point_method": "Complex log-frequency interpolation at300Hz/7kHz;1kHz is on the exactAC grid. Step labels follow recorded .step log order, not declaration order.",
           "calculation_kind": "Nominal model AC sensitivities, not noise, physical routing, or measured immunity",
           "frequency_points": [], "passive_examples": {}, "limitations": [
               "No PCB geometry, real shared ground impedance, real BLE load waveform, regulator loop or exact ADC switching model.",
               "AC1V/AC1A are normalization sources; no physical1V neural stimulus or1A reference-current test is claimed.",
               "C1058 minimum2uF is an accepted design assumption to check by MLCC DC-bias data, not a measured capacitance.",
               "ADC code perturbation uses first-order ideal12-bit ratiometry; no quantization, ENOB, drift or actual conversion result.",
               "All high-frequency model behavior and RF immunity remain unqualified."]}
for cap in caps:
    ripple = outputs[f"afe-avdd-ripple/{cap:g}F"]
    current = outputs[f"afe-vmid-current/{cap:g}F"]
    for frequency in [300, 1000, 7000]:
        summary["frequency_points"].append({
            "C1058_F": cap, "frequency_Hz": frequency,
            "VMID_per_AVDD_V_per_V": point(ripple, "vmid", frequency),
            "ADC1_per_AVDD_V_per_V": point(ripple, "adc_in_1", frequency),
            "ideal_code_LSB_per_1mV_AVDD": point(ripple, "adc_equivalent", frequency) * 4096 / 3 * .001,
            "VMID_impedance_ohm": point(current, "vmid", frequency),
            "ADC1_uV_per_1uA_VMID_injection": point(current, "adc_in_1", frequency),
        })
summary["passive_examples"] = {
    "ideal_VMIDs_divider_fc_Hz": 1 / (2*np.pi*5000*2.2e-6),
    "ideal_VMIDs_R47_C4p7u_fc_Hz": 1 / (2*np.pi*47*4.7e-6),
    "ideal_VMIDs_R47_C2u_fc_Hz": 1 / (2*np.pi*47*2e-6),
    "assumed_BLE_increment_A": .02,
    "shared_return_R_ohm": [.01, .1],
    "resulting_return_drop_V": [.02 * .01, .02 * .1],
    "capacitor_alone_20mA_10us_10uF_droop_V": .02*10e-6/10e-6,
    "capacitor_alone_20mA_10us_2uF_droop_V": .02*10e-6/2e-6,
    "assumption_warning": "Illustrative20mA increment and return resistances are not WBA52 measured values or extracted PCB parasitics; capacitor droop excludes regulator replenishment/ESR/ESL.",
}
with (base / "sensitivity.csv").open("w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["case", "C1058_F", "frequency_Hz", "VMID_normalized_magnitude", "ADC1_normalized_magnitude", "ADC_equivalent_normalized_magnitude"])
    writer.writerows(all_rows)
(base / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
for cap in caps:
    current = outputs[f"afe-vmid-current/{cap:g}F"]
    ripple = outputs[f"afe-avdd-ripple/{cap:g}F"]
    label = f"C1058={cap*1e6:g} μF"
    axes[0].semilogx(current["f"], np.abs(current["vmid"]), label=label)
    axes[1].semilogx(current["f"], np.abs(current["adc_in_1"]), label=label)
    axes[2].semilogx(ripple["f"], np.abs(ripple["adc_equivalent"])*4096/3*.001, label=label)
for ax in axes:
    ax.axvspan(300, 7000, color="#63a89f", alpha=.12)
    ax.set_xlim(1, 100000)
    ax.set_xlabel("Frequency (Hz)")
    ax.grid(alpha=.25)
    ax.legend(fontsize=8)
axes[0].set_ylabel("VMID impedance magnitude (Ω)")
axes[0].set_title("Shared-reference current sensitivity")
axes[1].set_ylabel("ADC perturbation (μV per 1 μA)")
axes[1].set_title("Quiet channel; injected VMID current")
axes[2].set_ylabel("Ideal ADC perturbation (LSB per 1 mV)")
axes[2].set_title("Imposed AVDD ripple; reference included")
fig.suptitle("Focused nominal TI-family AC models; shaded 300 Hz–7 kHz\nNo PCB, actual BLE waveform, regulator dynamics or RF-immunity proof", fontsize=11)
fig.tight_layout()
fig.savefig(base / "power-reference-sensitivity.png", dpi=180)
plt.close(fig)
print(json.dumps(summary["frequency_points"], indent=2))

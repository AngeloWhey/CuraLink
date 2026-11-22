"""Inspect actual ADS AFE datasets, bias points and normalized AC source vectors."""
from __future__ import annotations
from pathlib import Path
import json
import re
import numpy as np
from keysight.ads import dataset

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
FREQUENCIES = [0.01, 1, 50, 60, 100, 200, 300, 316, 500, 1000, 2000, 2900, 5000, 6880, 7000, 10000, 23000, 43000, 100000, 1e6]


def main():
    with dataset.open(HERE / "run/afe.ds") as data:
        dc = data["DC1.DC"].to_dataframe().reset_index()
        ac = data["SweepAC.AC1.AC"].to_dataframe().reset_index()
    row = dc.iloc[0]
    units = []
    for line in (ROOT / "hardware/rev-a/ltspice/afe/canonical-afe.lib").read_text().splitlines():
        fields = line.lower().split()
        if fields and fields[0].startswith("xu"):
            plus, minus, positive, negative, output = fields[1:6]
            vplus, vminus, vp, vn, vout = [0 if n == "0" else float(np.real(row[n])) for n in (plus, minus, positive, negative, output)]
            finite = bool(np.isfinite([vplus, vminus, vp, vn, vout]).all())
            units.append({"unit": fields[0], "model": fields[6], "plus_node": plus, "minus_node": minus, "output_node": output, "plus_V": vplus, "minus_V": vminus, "output_V": vout, "input_difference_V": vplus-vminus, "positive_rail_V": vp, "negative_rail_V": vn, "nominal_operating_point_check": bool(finite and vn+0.2 < vout < vp-0.2 and vn < vplus < vp and vn < vminus < vp and abs(vplus-vminus) < 0.001)})
    differential = ac[np.isclose(ac["AC_STIM"].astype(float), 0)].sort_values("freq").reset_index(drop=True)
    common = ac[np.isclose(ac["AC_STIM"].astype(float), 1)].sort_values("freq").reset_index(drop=True)
    freq = differential["freq"].to_numpy(float)
    if len(freq) != len(FREQUENCIES) or not np.allclose(freq, FREQUENCIES) or not np.allclose(common["freq"].to_numpy(float), FREQUENCIES):
        raise RuntimeError("Frequency array does not contain the declared native AC sweep")
    dv = differential["src_ch1"].to_numpy(complex)-differential["src_ref"].to_numpy(complex)
    cv = common["common_src"].to_numpy(complex)
    if not np.allclose(dv, 1) or not np.allclose(cv, 1):
        raise RuntimeError("Normalized differential/common stimulus is not unity")
    if not np.allclose(differential["src_ch1"], 0.5) or not all(np.allclose(differential[n], -0.5) for n in ["src_ref"]+[f"src_ch{i}" for i in range(2,9)]) or not all(np.allclose(common[n], 1) for n in ["src_ref"]+[f"src_ch{i}" for i in range(1,9)]):
        raise RuntimeError("Full source vectors do not support the declared superposition")
    output_d = np.column_stack([differential[f"adc_in_{i}"].to_numpy(complex) for i in range(1, 9)])
    output_c = np.column_stack([common[f"adc_in_{i}"].to_numpy(complex) for i in range(1, 9)])
    source_only = output_d + 0.5 * output_c
    vmid_source_only = differential["vmid"].to_numpy(complex) + 0.5*common["vmid"].to_numpy(complex)
    ffc_single = differential["ffc_ch1"].to_numpy(complex)+0.5*common["ffc_ch1"].to_numpy(complex)
    current_single = -(differential["vch1.i"].to_numpy(complex)+0.5*common["vch1.i"].to_numpy(complex))
    z_ffc = ffc_single/current_single
    gain_d = output_d[:, 0] / dv
    gain_c = output_c[:, 0] / cv
    quiet_ratio = np.max(np.abs(source_only[:, 1:]), axis=1)/np.abs(source_only[:, 0])
    finite_spectra = bool(np.isfinite(output_d).all() and np.isfinite(output_c).all() and np.isfinite(vmid_source_only).all())
    at1k = int(np.flatnonzero(np.isclose(freq, 1000))[0])
    old = json.loads((ROOT / "hardware/rev-a/ltspice/afe/results.json").read_text())
    old_adc = 1.503360
    old_i = 0.004474
    old_gain = 969.744
    rows=[]
    for i, value in enumerate(freq):
        rows.append({"frequency_Hz": float(value), "differential_gain_V_per_V": float(abs(gain_d[i])), "common_gain_V_per_V": float(abs(gain_c[i])), "differential_gain_real": float(gain_d[i].real), "differential_gain_imag": float(gain_d[i].imag), "derived_single_CH1_active_gain": float(abs(source_only[i, 0])), "derived_worst_quiet_gain": float(np.max(abs(source_only[i, 1:]))), "derived_single_CH1_crosstalk_dB": float(20*np.log10(quiet_ratio[i])), "derived_single_CH1_VMID_gain": float(abs(vmid_source_only[i])), "derived_FFC_CH1_input_Z_real_ohm": float(z_ffc[i].real), "derived_FFC_CH1_input_Z_imag_ohm": float(z_ffc[i].imag), "derived_FFC_CH1_input_Z_magnitude_ohm": float(abs(z_ffc[i]))})
    high1k = float(abs(gain_d[at1k]))
    i_supply = -float(np.real(row["vdd.i"]))
    report = {"recorded_date": "2026-11-22", "simulator": "Actual ADS 2026 Update 2, translated original TI family models", "status": "Nominal DC/AC model evidence; not clean-signal/build signoff", "model_and_topology_limits": ["TI dual-family macromodels stand in for quad units; no package/mismatch/PVT qualification", "Original passives and amplifier five-pin mapping independently checked", "ADS reports252internal-macro no-DC-path corrections; topologychecker default1e12ohm paths must be treated as model-port caveat", "T_ABS noiseless-resistor setting ignored by translator: noise analysis excluded", "No physical PCB returns/extracted coupling, power sequencing, real ADC switching or unpowered-input fault model"], "dc": {"all36_nominal_operating_points_valid": len(units)==36 and all(x["nominal_operating_point_check"] for x in units), "VMID_V": float(row["vmid"]), "ADC_outputs_V": [float(row[f"adc_in_{i}"]) for i in range(1,9)], "positive_rail_V": float(row["avdd_3v0"]), "positive_rail_current_A": i_supply, "ADC1_difference_from_rounded_LTspice_reference_uV": (float(row["adc_in_1"])-old_adc)*1e6, "supply_current_difference_from_rounded_LTspice_reference_percent": (i_supply/old_i-1)*100, "amplifiers": units}, "ac": {"frequency_points_per_stimulus": len(freq), "all_requested_frequencies_present": True, "all_examined_spectra_finite": finite_spectra, "unity_source_vectors_verified": True, "gain_at_1kHz": high1k, "gain_difference_from_LTspice_percent": (high1k/old_gain-1)*100, "CMRR_at_1kHz_dB": float(20*np.log10(abs(gain_d[at1k])/abs(gain_c[at1k]))), "derived_CH1_only_worst_crosstalk_at_1kHz_dB": rows[at1k]["derived_single_CH1_crosstalk_dB"], "single_channel_superposition": "S=D+0.5C exactly reproduces CH1=1,allotherCH/REF=0 from two verified source vectors in linear AC; not a separately driven dataset", "points": rows}}
    band_points = [p for p in rows if 300 <= p["frequency_Hz"] <= 7000]
    worst = max(band_points, key=lambda p:p["derived_single_CH1_crosstalk_dB"])
    report["ac"]["worst_sampled_CH1_only_crosstalk_in_300Hz_7kHz_dB"] = worst["derived_single_CH1_crosstalk_dB"]
    report["ac"]["worst_sampled_crosstalk_frequency_Hz"] = worst["frequency_Hz"]
    at7k = next(p for p in rows if p["frequency_Hz"] == 7000)
    report["input_loading"] = {"method": "Derived driving-point impedance at FFC_CH1, other electrode sources grounded through their47kohm branches; all sources from verified linear superposition", "formula": "ZFFC=VFFC_single/(-I_VCH1_single), single=D+0.5C", "fixture": "47kohm source,20pF FFC+2pF trace+0.5pF ESD per input, original TI family models", "frequency_Hz": 7000, "Z_real_ohm": at7k["derived_FFC_CH1_input_Z_real_ohm"], "Z_imag_ohm": at7k["derived_FFC_CH1_input_Z_imag_ohm"], "Z_magnitude_ohm": at7k["derived_FFC_CH1_input_Z_magnitude_ohm"], "existing_requirement_ohm": 1e7, "meets_existing_requirement": False}
    sensitivity_status = json.loads((HERE / "gmin-lower-initialized-run/execution.json").read_text()) if (HERE / "gmin-lower-initialized-run/execution.json").exists() else {}
    report["macro_port_qualification"] = {"nominal_DC_AC_completed": finite_spectra and report["dc"]["all36_nominal_operating_points_valid"], "topology_autocorrected_nodes": 252, "all_inside_36_TIfamily_macros": True, "external_CuraLink_nodes_autocorrected": 0, "gmin_parameter_loop": "Identical outputs do not independently qualify pre-sweep topology insertions", "fresh_literal_Gmin_1e_minus13": sensitivity_status.get("status", "not completed"), "noise_analysis": "Excluded because T_ABS noiseless-resistor setting was dropped", "full_model_port_qualified": False}
    (HERE / "results.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"dc_all36_valid": report["dc"]["all36_nominal_operating_points_valid"], "VMID_V": report["dc"]["VMID_V"], "ADC1_V": report["dc"]["ADC_outputs_V"][0], "Irail_A": i_supply, "AC_frequency_points": len(freq), "gain_1kHz": high1k, "gain_difference_LT_percent": report["ac"]["gain_difference_from_LTspice_percent"], "CMRR_1kHz_dB": report["ac"]["CMRR_at_1kHz_dB"], "derived_crosstalk_1kHz_dB": report["ac"]["derived_CH1_only_worst_crosstalk_at_1kHz_dB"]}, indent=2))


if __name__ == "__main__":
    main()

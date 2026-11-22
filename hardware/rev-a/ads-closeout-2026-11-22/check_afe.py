"""Run and export four-channel AFE DC, single/coherent AC and midpoint loop tests.

Use the Python interpreter supplied with ADS. Production CAD is unchanged.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np
from keysight.ads import dataset
from keysight.edatoolbox import ads


HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1] / "wpt/ads/review-2026-11-22/afe/afe-dc-ac.ckt"
ADS_ROOT = Path(os.environ.get("CURALINK_ADS_ROOT", os.environ.get("HPEESOF_DIR", r"C:\Program Files\Keysight\ADS2026_Update2")))
FREQUENCIES = np.unique(np.r_[300, 500, 1000, 2000, 5000, 7000, np.geomspace(1e2, 1e7, 91)])
CONFIGURATIONS = {
    "four-nominal": (47, 20),
    "four-low-isolation": (4.7, 20),
    "four-zero-cable": (47, 0),
    "coax-resistor-board-end": (47, 0),
    "coax-board-end-10ohm-bias": (10, 0),
    "four-coax-native": (47, 0),
    "coax-resistor-generator-end": (47, 0),
    "coax-direct-50ohm": (47, 0),
}


def four_channel_body(body):
    inactive = re.compile(r"\b(?:ch[5-8]_|(?:ffc_ch|src_ch|adc_in_|afe_out_)[5-8]\b)")
    omission = re.compile(r"^Cap_L:c(?:1060|1062|1064|1066) ")
    cleaned = [line for line in body.splitlines() if not (inactive.search(line) or omission.match(line))]
    units = [line.split()[0].split(":")[1] for line in cleaned if re.match(r"^tlv\d+_tlv\d+:xu", line)]
    assert set(units) == {f"xu{p}_{u}" for p in (101, 103, 105, 107, 109) for u in range(1, 5)}
    return "\n".join(cleaned) + "\n"


def make_deck(name, resistance, capacitance):
    source = BASE.read_text()
    body = source[source.index("Options ResourceUsage="):source.index("V_Source:vcommon")]
    assert body.count("R:r1149 vmid_buf vmid R=47\n") == 1
    body = body.replace("R:r1149 vmid_buf vmid R=47\n", f"R:r1149 vmid_buf vmid R={resistance}\n")
    assert body.count(" C=20p\n") == 9
    # A zero-cable fixture removes only the 20 pF cable assumptions.
    # Trace, clamp and amplifier input capacitance remain in circuit.
    if capacitance == 0:
        body = "\n".join(line for line in body.splitlines() if not line.startswith("Cap_L:c_ffc_")) + "\n"
    body = four_channel_body(body)
    if name == "four-coax-native":
        # Sixteen matched-value arms across the four difference stages.
        assert body.count(" R=909000\n") == 16
        body = body.replace(" R=909000\n", " R=910000\n")
    if name.startswith("coax-") or name == "four-coax-native":
        # Each center conductor has 100 pF to its grounded shield (assumed).
        # Equivalent generator/attenuator Thevenin R=50 ohm. Test REF is local.
        for electrode in ["ch1", "ch2", "ch3", "ch4", "ref"]:
            orig = f"R:r_source_{electrode} src_{electrode} ffc_{electrode} R=47k"
            assert body.count(orig) == 1
            if name == "four-coax-native" and electrode == "ref":
                # R605 in the new schematic goes directly to local GND.
                elements = [orig]
                cable_top = None
            elif name == "coax-direct-50ohm":
                elements = [f"R:r_gen_{electrode} src_{electrode} ffc_{electrode} R=50"]
                cable_top = f"ffc_{electrode}"
            else:
                elements = [f"R:r_gen_{electrode} src_{electrode} genout_{electrode} R=50",
                            f"R:r_source_{electrode} genout_{electrode} ffc_{electrode} R=47k"]
                board_end = name in ("coax-resistor-board-end", "coax-board-end-10ohm-bias", "four-coax-native")
                cable_top = f"genout_{electrode}" if board_end else f"ffc_{electrode}"
            if electrode != "ref":
                elements.append(f"Cap_L:c_coax_{electrode} {cable_top} 0 C=100p")
            body = body.replace(orig, "\n".join(elements))
    assert body.count("xu109_2 vmid_raw vmid_buf avdd_3v0 0 vmid_buf") == 1
    body = body.replace("xu109_2 vmid_raw vmid_buf avdd_3v0 0 vmid_buf",
                        "xu109_2 vmid_raw fb_sense avdd_3v0 0 vmid_buf")
    body += "SINGLE=-(AC_STIM-1)*(AC_STIM-2)*(AC_STIM-3)/6\n"
    body += "MULTI=AC_STIM*(AC_STIM-2)*(AC_STIM-3)/2\n"
    body += "INJECT=-AC_STIM*(AC_STIM-1)*(AC_STIM-3)/2\n"
    body += "COMMON=AC_STIM*(AC_STIM-1)*(AC_STIM-2)/6\n"
    body += "V_Source:vinj fb_sense vmid_buf Vdc=0 Vac=polar(INJECT,0)\n"
    body += "V_Source:vref src_ref 0 Vdc=0 Vac=polar(COMMON,0)\n"
    for index in range(1, 5):
        amplitude = "SINGLE+COMMON" if index == 1 else "MULTI+COMMON"
        body += f"V_Source:vch{index} src_ch{index} 0 Vdc=0 Vac=polar({amplitude},0)\n"
    body += '''
OutputPlan:Out Type="Output" UseNodeNestLevel=yes NodeNestLevel=1 UseCurrentNestLevel=yes CurrentNestLevel=1
DC:DC1 MaxIters=200 StatusLevel=1 OutputPlan="Out"
AC:AC1 SweepVar="freq" SweepPlan="Freq" CalcNoise=no StatusLevel=1 OutputPlan="Out"
SweepPlan:Stim Start=0 Stop=3 Step=1
ParamSweep:Case SimInstanceName[1]="AC1" StatusLevel=1 SweepVar="AC_STIM" SweepPlan="Stim"
'''
    plans = [f'SweepPlan[{i}]="p{i}"' for i in range(1, len(FREQUENCIES) + 1)]
    body += 'SweepPlan:Freq ' + ' \\\n'.join(plans) + '\n'
    body += ''.join(f"SweepPlan:p{i} Pt={f:.14g}\n" for i, f in enumerate(FREQUENCIES, 1))
    return body


def analyze(data_file, outdir):
    with dataset.open(data_file) as data:
        table = data["Case.AC1.AC"].to_dataframe().reset_index()
        dc = data["DC1.DC"].to_dataframe().iloc[0]
    source_lines = (outdir / "afe.ckt").read_text().splitlines()
    dc_node = lambda n: 0 if n == "0" else float(dc[n])
    units = []
    for line in source_lines:
        if re.match(r"^tlv\d+_tlv\d+:xu", line):
            name, p, n, avdd, gnd, out = line.split()
            vp, vn, vhi, vlo, vo = map(dc_node, [p, n, avdd, gnd, out])
            units.append(dict(unit=name, plus_V=vp, minus_V=vn, output_V=vo,
                              inside_nominal_limits=vlo+.2 < vo < vhi-.2 and vlo < vp < vhi
                              and vlo < vn < vhi and abs(vp-vn)<.001))
    assert len(units) == 20
    (outdir / "operating-points.json").write_text(json.dumps(units, indent=2)+"\n")
    # Keep excitation and measurement phasors so the next laptop can audit
    # every derived metric without proprietary dataset readers.
    columns = ["AC_STIM", "freq", "src_ref", *[f"src_ch{i}" for i in range(1, 5)],
               "ffc_ch1", "vch1.i", "fb_sense", "vmid_buf",
               *[f"adc_in_{i}" for i in range(1, 5)]]
    if "genout_ch1" in table.columns:
        columns.append("genout_ch1")
    table[columns].to_csv(outdir / "phasors.csv", index=False)
    subsets = [table[table.AC_STIM == i].sort_values("freq") for i in range(4)]
    for group in subsets:
        assert np.allclose(group.freq, FREQUENCIES)
    single, three, loop, common = subsets
    for group, ref, amplitude_ch1, amplitude_other, injection in zip(subsets, [0,0,0,1], [1, 0, 0,1], [0, 1, 0,1], [0, 0, 1,0]):
        assert np.allclose(group.src_ref, ref) and np.allclose(group.src_ch1, amplitude_ch1)
        assert all(np.allclose(group[f"src_ch{i}"], amplitude_other) for i in range(2, 5))
        assert np.allclose(group.fb_sense - group.vmid_buf, injection)
    direct = single.adc_in_1.to_numpy()
    victim = np.max(np.abs(np.stack([single[f"adc_in_{i}"].to_numpy() for i in range(2, 5)])), axis=0)
    cross_one = victim / np.abs(direct)
    cross_multi = np.abs(three.adc_in_1.to_numpy() / direct)
    i_port = -single["vch1.i"].to_numpy()
    if "genout_ch1" in single.columns:
        i_port = (single.genout_ch1.to_numpy() - single.ffc_ch1.to_numpy())/47e3
    zin = single.ffc_ch1.to_numpy() / i_port
    return_ratio = -loop.vmid_buf.to_numpy() / loop.fb_sense.to_numpy()
    phase = np.rad2deg(np.unwrap(np.angle(return_ratio)))
    db = 20 * np.log10(np.abs(return_ratio))
    crossings = []
    for i in range(len(db) - 1):
        if np.signbit(db[i]) != np.signbit(db[i + 1]):
            mix = -db[i] / (db[i + 1] - db[i])
            f_i, f_end = np.log10(FREQUENCIES[i:i + 2])
            crossings.append({"frequency_Hz": float(10**(f_i + mix * (f_end - f_i))),
                              "phase_margin_estimate_deg": float(180 + phase[i] + mix * (phase[i + 1] - phase[i]))})
    spectral_rows = list(zip(FREQUENCIES, np.abs(direct), 20*np.log10(cross_one),
                             20*np.log10(cross_multi), zin.real, zin.imag,
                             np.abs(zin), db, phase))
    if not np.isfinite(spectral_rows).all():
        raise ValueError("Nonfinite result")
    with (outdir / "spectra.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frequency_Hz", "CH1_to_ADC1_gain_magnitude", "single_to_quiet_dB",
                         "three_coherent_to_quiet_dB", "input_Z_real_ohm", "input_Z_imag_ohm",
                         "input_Z_magnitude_ohm", "midpoint_return_ratio_dB", "midpoint_return_ratio_deg"])
        writer.writerows(spectral_rows)
    band = (FREQUENCIES >= 300) & (FREQUENCIES <= 7000)
    i7 = np.flatnonzero(FREQUENCIES == 7000)[0]
    i1 = np.flatnonzero(FREQUENCIES == 1000)[0]
    diff_gain_1k = abs((direct - .5 * common.adc_in_1.to_numpy())[i1])
    result = {
        "AC_rows": len(table), "frequencies_per_source_vector": len(single),
        "adc_bias_V": [float(dc[f"adc_in_{i}"]) for i in range(1,5)],
        "vmid_V": float(dc["vmid"]), "analog_current_mA": -float(dc["vdd.i"])*1000,
        "nominal_operating_points_passed": sum(u["inside_nominal_limits"] for u in units),
        "differential_gain_1kHz": float(diff_gain_1k),
        "single_input_source_to_ADC_gain_at_7kHz": float(abs(direct[i7])),
        "source_to_board_input_7kHz_magnitude": float(abs(single.ffc_ch1.to_numpy()[i7])),
        "source_to_board_input_7kHz_phase_deg": float(np.angle(single.ffc_ch1.to_numpy()[i7], deg=True)),
        "CMRR_1kHz_dB": float(20*np.log10(diff_gain_1k/abs(common.adc_in_1.to_numpy()[i1]))),
        "coherent_three_max_equiv_uVpp_per_aggressor_1mVpp": float(1000*np.max(cross_multi[band])),
        "coherent_three_worst_frequency_Hz": float(FREQUENCIES[band][np.argmax(cross_multi[band])]),
        "single_worst_dB": float(20*np.log10(np.max(cross_one[band]))),
        "coherent_three_worst_dB": float(20*np.log10(np.max(cross_multi[band]))),
        "Z_7k_magnitude_ohm": float(abs(zin[i7])),
        "Z_7k_real_ohm": float(zin[i7].real), "Z_7k_imag_ohm": float(zin[i7].imag),
        "unity_loop_crossings": crossings,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("configuration", choices=CONFIGURATIONS)
    args = parser.parse_args()
    name = args.configuration
    outdir = HERE / name
    outdir.mkdir(exist_ok=True)
    res, cap = CONFIGURATIONS[name]
    circuit = make_deck(name, res, cap)
    simulator = ads.CircuitSimulator(hpeesof_dir=str(ADS_ROOT))
    with tempfile.TemporaryDirectory(prefix="curalink_ads_signal_") as temp:
        staging = Path(temp) / "outputs"
        staging.mkdir()
        deck = staging / "afe.ckt"
        deck.write_bytes(circuit.encode())
        proc = subprocess.run([str(ADS_ROOT/"bin/hpeesofsim.exe"), str(deck), "--dataset-name=afe", "-T4"],
                              cwd=temp, env=simulator._env, capture_output=True, text=True, timeout=500)
        if proc.returncode:
            print(proc.stdout + proc.stderr)
        proc.check_returncode()
        (staging / "simulator.log").write_text(proc.stdout + proc.stderr)
        results = analyze(Path(temp) / "afe.ds", staging)
        results.update(configuration=name, R1149_ohm=res, cable_pF=cap,
                       source_sha256=hashlib.sha256(BASE.read_bytes()).hexdigest(),
                       deck_sha256=hashlib.sha256(deck.read_bytes()).hexdigest())
        if name.startswith("coax-") or name == "four-coax-native":
            results.update(cable_pF=100, connector="U.FL", local_REF_shunt_cable_pF=0)
        (staging / "results.json").write_text(json.dumps(results, indent=2)+"\n")
        for file in staging.iterdir():
            shutil.copy2(file, outdir / file.name)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

"""Standalone ADS HB receiver fixture; source workspace is never changed.

Run using ADS's bundled Python.  The retained diode is diagnostic only.
This resistor fixture is not a model or validation of BQ25185 charging.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
from keysight.edatoolbox import ads
from keysight.ads import dataset

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
ADS_ROOT = Path(os.environ.get("CURALINK_ADS_ROOT", os.environ.get("HPEESOF_DIR", r"C:\Program Files\Keysight\ADS2026_Update2")))
WORKSPACE = Path(os.environ.get("CURALINK_ADS_WORKSPACE", str(PROJECT_ROOT / "ads" / "MyWorkspace_wrk")))
SOURCE = WORKSPACE / "netlist.log"
BASE_CAPS = (61.3, 438.0, 673.3, 1050.0)
LOADS = (208.333333333, 220.0, 230.0, 240.0, 270.0, 470.0, 1e6)
POWERS = (20.0, 23.0, 26.0)
CAP_NAMES = ("C_tx_series_pF", "C_tx_shunt_pF", "C_rx_series_pF", "C_rx_shunt_pF")
DIODES = {
    "existing": {
        "parameters": "Is=74 nA Rs=5 N=1.07 Tt=3 ps Cjo=138.5 fF Vj=0.224 V M=0.138 Fc=0.5 Bv=4.2 V Ibv=100 uA AllowScaling=0 Xti=1.5",
        "rated_reverse_V": 4.0, "model_BV_V": 4.2,
    },
    "bat54": {
        # Complete manufacturer model; the model's BV50 fit is NOT the 30V rating.
        # IkModel=1 explicitly chooses ADS/Libra/Pspice high-injection equation.
        # No Tt was provided; no reverse-recovery time has been invented.
        "parameters": "Is=649e-9 N=1.04 Rs=2.09 Ikf=20e-3 Xti=2 Eg=0.58 Cjo=12.4e-12 M=0.381 Vj=0.391 Bv=50 Ibv=100e-6 Isr=431e-9 Nr=4.99 Nbv=1.04 Tnom=27 IkModel=1 Imax=1000 Trs1=0 Trs2=0",
        "rated_reverse_V": 30.0, "model_BV_V": 50.0,
    },
}


def netlist(pin=10.0, rload=1e6, caps=(61.3, 438.0, 673.3, 1050.0), order=7, coupling=0.0662, diode="existing"):
    tx_series, tx_shunt, rx_series, rx_shunt = caps
    return f'''\
; CuraLink isolated corrected floating full-bridge receiver, 2026-10-09
; Four ideal tuning capacitors; resistive DC load; current diode diagnostic only.
Options ResourceUsage=yes UseNutmegFormat=no EnableOptim=no TopDesignName="CuraLink:receiver_resistor_fixture:schematic" DcopOutputNodeVoltages=yes DcopOutputPinCurrents=yes
Pin_dBm={pin:.12g}
Rload={rload:.12g}
F0=13.56 MHz
Port:PORT1 Vin0 0 Num=1 Z=50 Ohm P[1]=polar(dbmtow(Pin_dBm),0) Freq[1]=F0 Noise=no
Short:TX_Probe Vin0 Vin Mode=0 SaveCurrent=yes
C:C5 Vin 0 C={tx_shunt:.12g} pF
C:C3 Vin VinMatched C={tx_series:.12g} pF
L:L1 VinMatched 0 L=2.49 uH R=1.8 Noise=no
L:L2 IMPin Vout L=0.33 uH R=0.399 Noise=no
Mutual:Mutual1 K={coupling:.12g} Inductor1="L1" Inductor2="L2"
C:C1 Vout VoutMatched C={rx_series:.12g} pF
C:C6 VoutMatched IMPin C={rx_shunt:.12g} pF
model DIODEM1 Diode {DIODES[diode]['parameters']}
Short:D1_Probe 0 D1_A Mode=0 SaveCurrent=yes
"DIODEM1":DIODE1 D1_A VoutMatched Mode=1 Noise=no
Short:D2_Probe VoutMatched D2_A Mode=0 SaveCurrent=yes
"DIODEM1":DIODE2 D2_A DCout Mode=1 Noise=no
Short:D3_Probe 0 D3_A Mode=0 SaveCurrent=yes
"DIODEM1":DIODE3 D3_A IMPin Mode=1 Noise=no
Short:D4_Probe IMPin D4_A Mode=0 SaveCurrent=yes
"DIODEM1":DIODE4 D4_A DCout Mode=1 Noise=no
C:Cdc DCout 0 C=1 uF
Short:DC_Probe DCout LoadIn Mode=0 SaveCurrent=yes
R:Rload LoadIn 0 R=Rload Noise=no
HB:HB1 MaxOrder={order} Freq[1]=F0 Order[1]={order} StatusLevel=0 OutputPlan="HB1_Output"
OutputPlan:HB1_Output Type="Output" UseNodeNestLevel=yes NodeNestLevel=2 UseEquationNestLevel=yes EquationNestLevel=2 UseSavedEquationNestLevel=yes SavedEquationNestLevel=2 UseDeviceCurrentNestLevel=yes DeviceCurrentNestLevel=2 DeviceCurrentDeviceType="All" DeviceCurrentSymSyntax=yes UseCurrentNestLevel=yes CurrentNestLevel=999 UseDeviceVoltageNestLevel=yes DeviceVoltageNestLevel=2 DeviceVoltageDeviceType="All"
'''


def run_one(simulator, pin=10.0, rload=1e6, caps=(61.3, 438.0, 673.3, 1050.0), order=7, coupling=0.0662, label="single", diode="existing"):
    outdir = HERE / "runs" / label
    outdir.mkdir(parents=True, exist_ok=True)
    deck = netlist(pin, rload, caps, order, coupling, diode)
    start = time.monotonic()
    deck_path = outdir / "receiver.ckt"
    deck_path.write_text(deck, encoding="utf-8")
    # Use the documented CLI through the environment configured by Keysight's API.
    # Direct subprocess also preserves the real error instead of the installed
    # edatoolbox wrapper's IndexError for this version's license error text.
    proc = subprocess.run([str(ADS_ROOT / "bin" / "hpeesofsim.exe"), str(deck_path),
                           "--dataset-name=receiver", "-T4"], cwd=outdir,
                          env=simulator._env, capture_output=True, text=True)
    log = proc.stdout + proc.stderr
    (outdir / "simulator.log").write_text(log, encoding="utf-8")
    if proc.returncode:
        if "Licensed number of users already reached" in log:
            raise RuntimeError(f"ADS license occupied; no new result. See {outdir / 'simulator.log'}")
        raise RuntimeError(f"ADS exit {proc.returncode}; see {outdir / 'simulator.log'}")
    with dataset.open(outdir / "receiver.ds") as ds:
        df = ds["HB1.HB"].to_dataframe().reset_index()
    elapsed = time.monotonic() - start
    return df, outdir, elapsed


def waveform(coeff, harmonic, samples=8192):
    """ADS HB peak phasors: v(t)=v0+Re(sum(Vn*exp(j*n*w*t)))."""
    theta = np.arange(samples) * (2 * np.pi / samples)
    result = np.zeros(samples)
    for value, n in zip(np.asarray(coeff, complex), harmonic):
        if n == 0:
            result += value.real
        else:
            result += np.real(value * np.exp(1j * int(n) * theta))
    return result


def average_power(voltage, current, harmonic):
    weight = np.where(np.asarray(harmonic) == 0, 1.0, 0.5)
    return float(np.sum(weight * np.real(np.asarray(voltage) * np.conj(current))))


def metrics(df, pin, rload, caps=BASE_CAPS, coupling=0.0662, diode="existing"):
    df = df.sort_values("freq").reset_index(drop=True)
    freqs = df["freq"].to_numpy(float)
    harmonic = np.rint(freqs / 13.56e6).astype(int)
    avail = 1e-3 * 10 ** (pin / 10)
    v = {name: df[name].to_numpy(complex) for name in df.columns if name not in ("freq", "Mix[1]")}
    vin = v["Vin0"] if "Vin0" in v else v["Vin"]
    if "TX_Probe.i" in v:
        iin = v["TX_Probe.i"]
        current_origin = "saved TX_Probe current"
    else:
        vs = np.zeros_like(vin)
        vs[harmonic == 1] = 2 * np.sqrt(2 * avail * 50)
        iin = (vs - vin) / 50
        current_origin = "derived from saved source voltage and declared 50-ohm Thevenin port"
    dc = v["DCout"]
    vdc = float(dc[harmonic == 0][0].real)
    pdc = vdc * vdc / rload
    paccept = average_power(vin, iin, harmonic)
    dcwave = waveform(dc, harmonic)
    result = {"diode_model": diode, "Pin_dBm": pin, "P_available_W": avail, "Rload_ohm": rload,
              **dict(zip(CAP_NAMES, map(float, caps))), "k": coupling,
              "HB_order": int(harmonic.max()), "Vdc_V": vdc,
              "Idc_A": vdc / rload, "Pdc_W": pdc,
              "P_load_total_W": average_power(dc, dc / rload, harmonic),
              "P_accepted_W": paccept, "P_accepted_origin": current_origin,
              "eta_available_to_dc": pdc / avail,
              "eta_accepted_to_dc": pdc / paccept if paccept > 0 else None,
              "Vdc_ripple_pp_V": float(np.ptp(dcwave)),
              "Vdc_max_V": float(dcwave.max()), "Vdc_min_V": float(dcwave.min())}
    fidx = np.flatnonzero(harmonic == 1)[0]
    z = vin[fidx] / iin[fidx]
    gamma = (z - 50) / (z + 50)
    result.update({"Zin_fundamental_real_ohm": float(z.real),
                   "Zin_fundamental_imag_ohm": float(z.imag),
                   "return_loss_fundamental_dB": float(-20 * np.log10(abs(gamma))),
                   "bridge_ac_fundamental_peak_V": float(abs((v["VoutMatched"] - v["IMPin"])[fidx]))})
    # Voltage across each actual diode, anode minus cathode; bridge AC nodes float.
    diode_voltages = (-v["VoutMatched"], v["VoutMatched"] - dc,
                      -v["IMPin"], v["IMPin"] - dc)
    for idx, dv in enumerate(diode_voltages, start=1):
        w = waveform(dv, harmonic)
        result[f"D{idx}_reverse_peak_V"] = float(max(0, -w.min()))
        result[f"D{idx}_forward_peak_V"] = float(max(0, w.max()))
        key = f"D{idx}_Probe.i"
        if key in v:
            iw = waveform(v[key], harmonic)
            result[f"D{idx}_forward_current_peak_A"] = float(max(0, iw.max()))
            result[f"D{idx}_reverse_current_peak_A"] = float(max(0, -iw.min()))
            result[f"D{idx}_current_rms_A"] = float(np.sqrt(np.mean(iw * iw)))
            result[f"D{idx}_average_dissipation_W"] = average_power(dv, v[key], harmonic)
    max_reverse = max(result[f"D{x}_reverse_peak_V"] for x in range(1, 5))
    result["diode_max_reverse_peak_V"] = max_reverse
    result["diode_rated_reverse_V"] = DIODES[diode]["rated_reverse_V"]
    result["diode_rated_reverse_limit_exceeded"] = bool(max_reverse > DIODES[diode]["rated_reverse_V"])
    result["diode_model_BV_V"] = DIODES[diode]["model_BV_V"]
    result["diode_model_BV_exceeded"] = bool(max_reverse > DIODES[diode]["model_BV_V"])
    result["charging_hardware_validated"] = False
    cap_observables = (("tx_series_cap", v["Vin"] - v["VinMatched"], caps[0] * 1e-12),
                       ("tx_shunt_cap", v["Vin"], caps[1] * 1e-12),
                       ("rx_series_cap", v["Vout"] - v["VoutMatched"], caps[2] * 1e-12),
                       ("rx_shunt_cap", v["VoutMatched"] - v["IMPin"], caps[3] * 1e-12),
                       ("reservoir_cap", dc, 1e-6))
    for name, coeff, capacitance in cap_observables:
        result[name + "_voltage_peak_V"] = float(np.max(np.abs(waveform(coeff, harmonic))))
        iw = waveform(1j * 2 * np.pi * freqs * capacitance * coeff, harmonic)
        result[name + "_current_peak_A"] = float(np.max(np.abs(iw)))
        result[name + "_current_rms_A"] = float(np.sqrt(np.mean(iw * iw)))
    # Recover series coil currents from the declared narrowband R-L-M matrix.
    # This is a calculated observable using saved nodal spectra, not extra measured data.
    mutual = coupling * np.sqrt(2.49e-6 * 0.33e-6)
    coil_currents = []
    for f, txv, rxv in zip(freqs, v["VinMatched"], v["IMPin"] - v["Vout"]):
        omega = 2 * np.pi * f
        zm = np.array([[1.8 + 1j * omega * 2.49e-6, 1j * omega * mutual],
                       [1j * omega * mutual, 0.399 + 1j * omega * 0.33e-6]])
        coil_currents.append(np.linalg.solve(zm, [txv, rxv]))
    coil_currents = np.asarray(coil_currents)
    for i, (name, resistance) in enumerate((("tx_coil", 1.8), ("rx_coil", 0.399))):
        saved_key = f"L{i+1}.P1.pinCurrent.i"
        if saved_key in v:
            coil_currents[:, i] = v[saved_key]
            result[name + "_current_origin"] = "saved ADS device pin current"
        else:
            result[name + "_current_origin"] = "derived from nodal spectra and declared R-L-M equations"
        cw = waveform(coil_currents[:, i], harmonic)
        result[name + "_current_peak_A"] = float(np.max(np.abs(cw)))
        result[name + "_current_rms_A"] = float(np.sqrt(np.mean(cw * cw)))
        result[name + "_resistor_loss_W"] = average_power(resistance * coil_currents[:, i], coil_currents[:, i], harmonic)
    result["remaining_rectifier_loss_W"] = paccept - result["P_load_total_W"] - result["tx_coil_resistor_loss_W"] - result["rx_coil_resistor_loss_W"]
    if all(f"D{x}_average_dissipation_W" in result for x in range(1, 5)):
        result["power_balance_error_W"] = result["remaining_rectifier_loss_W"] - sum(result[f"D{x}_average_dissipation_W"] for x in range(1, 5))
    return result


def write_rows(path, rows):
    if not rows:
        return
    names = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=names)
        w.writeheader()
        w.writerows(rows)


def record_source():
    destination = HERE / "source-snapshot"
    destination.mkdir(exist_ok=True)
    files = [SOURCE, SOURCE.parent / "data" / "cell_1.ds", SOURCE.parent / "data" / "cell_1_data" / "logFile.txt"]
    metadata = []
    for src in files:
        dst = destination / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
        metadata.append({"source": str(src), "snapshot": str(dst),
                         "source_mtime_local": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(dst.stat().st_mtime)),
                         "sha256": hashlib.sha256(dst.read_bytes()).hexdigest()})
    (destination / "provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return destination


def prepare():
    target = HERE / "input-decks"
    target.mkdir(exist_ok=True)
    for pin in POWERS:
        for rload in LOADS:
            label = f"baseline_P{pin:g}dBm_R{rload:g}ohm"
            (target / (label + ".ckt")).write_text(netlist(pin, rload, BASE_CAPS), encoding="utf-8")
    (target / "baseline_P10dBm_R1e6ohm.ckt").write_text(netlist(), encoding="utf-8")
    with dataset.open(record_source() / "cell_1.ds") as ds:
        df = ds["HB1.HB"].to_dataframe().reset_index()
    m = metrics(df, 10.0, 1e6)
    m["evidence"] = "saved original ADS run; not a newly completed fixture simulation"
    (HERE / "saved-baseline-metrics.json").write_text(json.dumps(m, indent=2), encoding="utf-8")
    write_rows(HERE / "saved-baseline-metrics.csv", [m])
    # Export complex spectra explicitly, preserving units and phase.
    exported = {"freq_Hz": df["freq"].to_numpy(float)}
    for col in df.columns:
        if col not in ("freq", "Mix[1]"):
            exported[col + "_real"] = np.real(df[col].to_numpy(complex))
            exported[col + "_imag"] = np.imag(df[col].to_numpy(complex))
    import pandas as pd
    pd.DataFrame(exported).to_csv(HERE / "saved-baseline-spectra.csv", index=False)
    print(json.dumps(m, indent=2))


def sweep(simulator, caps=BASE_CAPS, label_prefix="baseline", order=7, diode="existing"):
    rows = []
    for pin in POWERS:
        for rload in LOADS:
            label = f"{label_prefix}_P{pin:g}dBm_R{rload:g}ohm_H{order}"
            df, outdir, elapsed = run_one(simulator, pin, rload, caps, order, label=label, diode=diode)
            row = metrics(df, pin, rload, caps, diode=diode)
            row.update({"elapsed_s": elapsed, "run_directory": str(outdir)})
            rows.append(row)
            write_rows(HERE / f"{label_prefix}-matrix-H{order}.csv", rows)
            print(f"{label}: Vdc={row['Vdc_V']:.5g}V Pdc={1e3*row['Pdc_W']:.5g}mW reverse={row['diode_max_reverse_peak_V']:.5g}V", flush=True)
    return rows


def optimize(simulator, maxiter=3, diode="bat54", pin=26.0, rload=230.0):
    """Bounded joint search, never a global optimum or final component choice."""
    from scipy.optimize import differential_evolution
    # Broad positive-capacitance search; log coordinates avoid overweighting the
    # large values. Bounds are exploratory ranges, not PCB component selections.
    bounds_pf = ((20, 200), (50, 2000), (100, 5000), (100, 10000))
    bounds = [(np.log10(lo), np.log10(hi)) for lo, hi in bounds_pf]
    if diode == "existing":
        raise RuntimeError("Do not optimize the avalanche-limited 4V diagnostic seed for charging. Use a separately sourced candidate model.")
    rows = []
    evaluation = 0
    def objective(log_caps):
        nonlocal evaluation
        evaluation += 1
        caps = tuple(10 ** np.asarray(log_caps))
        df, outdir, elapsed = run_one(simulator, pin, rload, caps, 7, label=f"{diode}_joint_search_{evaluation:04d}", diode=diode)
        row = metrics(df, pin, rload, caps, diode=diode)
        row.update({"evaluation": evaluation, "elapsed_s": elapsed, "run_directory": str(outdir)})
        rows.append(row)
        write_rows(HERE / f"{diode}-joint-search.csv", rows)
        # Maximize delivered DC. Stress is reported, not hidden by an S11-only
        # objective or used to claim the diagnostic 4V diode can power a charger.
        return -row["Pdc_W"]
    # Local joint population around the established resonant starting network.
    # Very broad random starts mostly discard resonance and waste simulator runs.
    rng = np.random.default_rng(20261009)
    initial = np.tile(np.log10(BASE_CAPS), (16, 1)) + rng.normal(0, 0.075, (16, 4))
    initial = np.clip(initial, np.array(bounds)[:, 0], np.array(bounds)[:, 1])
    initial[0] = np.log10(BASE_CAPS)
    result = differential_evolution(objective, bounds, maxiter=maxiter, popsize=4,
                                    seed=20261009, polish=False, workers=1,
                                    init=initial, mutation=(0.3, 0.7), recombination=0.9,
                                    x0=np.log10(BASE_CAPS), tol=0.005)
    best = min(rows, key=lambda r: -r["Pdc_W"])
    best["search_status"] = str(result.message)
    best["search_bounds_pF"] = bounds_pf
    best["evidence"] = f"ADS HB finite local joint search at{pin:g}dBm{rload:g}ohm; candidate diode only; no global optimum claim"
    (HERE / f"{diode}-joint-search-best.json").write_text(json.dumps(best, indent=2), encoding="utf-8")
    caps = tuple(best[key] for key in CAP_NAMES)
    (HERE / "input-decks" / f"{diode}-joint-search-best.ckt").write_text(netlist(pin, rload, caps, diode=diode), encoding="utf-8")
    sweep(simulator, caps, f"{diode}-joint-search-best", 7, diode=diode)
    # Check Fourier truncation where reverse stress and current spikes matter.
    checks = []
    for order in (15, 31):
        for test_load in (208.333333333, 230.0, 1e6):
            df, outdir, elapsed = run_one(simulator, pin, test_load, caps, order, label=f"{diode}_best_convergence_R{test_load:g}_H{order}", diode=diode)
            row = metrics(df, pin, test_load, caps, diode=diode)
            row.update({"elapsed_s": elapsed, "run_directory": str(outdir)})
            checks.append(row)
            write_rows(HERE / f"{diode}-joint-search-best-harmonic-check.csv", checks)
    print(json.dumps(best, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pin", type=float, default=10)
    p.add_argument("--load", type=float, default=1e6)
    p.add_argument("--caps", type=float, nargs=4, default=(61.3, 438.0, 673.3, 1050.0))
    p.add_argument("--order", type=int, default=7)
    p.add_argument("--label", default="single")
    p.add_argument("--mode", choices=("single", "prepare", "sweep", "optimize"), default="single")
    p.add_argument("--maxiter", type=int, default=3)
    p.add_argument("--diode", choices=DIODES, default="existing")
    a = p.parse_args()
    if a.mode == "prepare":
        prepare()
        return
    prepare()
    simulator = ads.CircuitSimulator(hpeesof_dir=str(ADS_ROOT))
    if a.mode == "sweep":
        sweep(simulator, a.caps, a.label, a.order, diode=a.diode)
        return
    if a.mode == "optimize":
        optimize(simulator, a.maxiter, a.diode, a.pin, a.load)
        return
    df, outdir, elapsed = run_one(simulator, a.pin, a.load, a.caps, a.order, label=a.label, diode=a.diode)
    print("seconds", elapsed, "output", outdir)
    m = metrics(df, a.pin, a.load, a.caps, diode=a.diode)
    (outdir / "metrics.json").write_text(json.dumps(m, indent=2), encoding="utf-8")
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()

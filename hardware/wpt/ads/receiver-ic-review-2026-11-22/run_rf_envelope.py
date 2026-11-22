"""Exercise the fixed coil and a two-terminal RF load in actual ADS.

This is a passive carrier-frequency feasibility study. R and C are independent
test loads at the proposed IC pins. DC output and IC behavior are not modeled.
Run with ADS bundled Python; the exported CSV needs no ADS license to read.
"""
import csv
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

import numpy as np
from keysight.ads import dataset
from keysight.edatoolbox import ads

HERE = Path(__file__).resolve().parent
ADS_ROOT = Path(os.environ.get("CURALINK_ADS_ROOT", os.environ.get("HPEESOF_DIR", r"C:\Program Files\Keysight\ADS2026_Update2")))
FREQ = 13.56e6
W = 2 * math.pi * FREQ
PIN_DBM = 23.5
AVAILABLE_W = 1e-3 * 10**(PIN_DBM / 10)
NOMINAL_K = 0.0662
LTX, LRX = 2.49e-6, .330e-6
RTX, RRX = 1.80, .399
MATCHES = [("paper_50ohm", 673.3, 1050.0)]


def sweep_plan(index, var, values, child):
    name = f"Plan{index}"
    points = " ".join(f'SweepPlan[{i+1}]="{name}_{i}"' for i in range(len(values)))
    lines = [f"SweepPlan:{name} {points}"]
    lines.extend(f"SweepPlan:{name}_{i} Pt={v:.12g}" for i, v in enumerate(values))
    lines.append(f'ParamSweep:Sweep{index} SimInstanceName[1]="{child}" SweepVar="{var}" SweepPlan="{name}" StatusLevel=0')
    return "\n".join(lines)


def deck(series_pf, shunt_pf):
    # A first-order HB solve is exact for the fundamental of this linear network.
    netlist = f"""Options ResourceUsage=yes UseNutmegFormat=no EnableOptim=no
RIN=50
CINPF=25
COUPLING={NOMINAL_K}
Port:PORT1 TX 0 Num=1 Z=50 Ohm P[1]=polar(dbmtow({PIN_DBM}),0) Freq[1]=13.56 MHz Noise=no
C:TXSH TX 0 C=438 pF
C:TXSER TX TXCOIL C=61.3 pF
L:L1 TXCOIL 0 L=2.49 uH R=1.8 Noise=no
L:L2 0 RXCOIL L=0.330 uH R=0.399 Noise=no
Mutual:LINK K=COUPLING Inductor1="L1" Inductor2="L2"
C:RXSER RXCOIL RFIC C={series_pf:.12g} pF
C:RXSH RFIC 0 C={shunt_pf:.12g} pF
C:PIN_C RFIC 0 C=(CINPF*1e-12)
R:PIN_R RFIC 0 R=RIN Noise=no
HB:HB1 MaxOrder=1 Freq[1]=13.56 MHz Order[1]=1 StatusLevel=0 OutputPlan="OUT"
OutputPlan:OUT Type="Output" UseNodeNestLevel=yes NodeNestLevel=1
"""
    child = "HB1"
    for i, (variable, values) in enumerate([
        ("RIN", (25, 50, 100, 200, 400, 1000)),
        ("CINPF", (0, 25, 100)),
        ("COUPLING", (.0331, .04965, .0662)),
    ]):
        netlist += sweep_plan(i, variable, values, child) + "\n"
        child = f"Sweep{i}"
    return netlist


def validate(case, r, c, k, vtx_ads, vrx_ads):
    series_pf, shunt_pf = case[1:]
    load = 1/(1/r + 1j*W*(c+shunt_pf)*1e-12)
    z_seen = load + 1/(1j*W*series_pf*1e-12)
    jm = 1j*W*k*math.sqrt(LTX*LRX)
    z_coil_in = RTX+1j*W*LTX - jm**2/(RRX+1j*W*LRX+z_seen)
    z_branch = z_coil_in + 1/(1j*W*61.3e-12)
    z_tx = 1/(1/z_branch + 1j*W*438e-12)
    source_vpk = 2*math.sqrt(2*AVAILABLE_W*50)
    vtx = source_vpk*z_tx/(50+z_tx)
    itx_coil = vtx/z_branch
    irx = -jm*itx_coil/(RRX+1j*W*LRX+z_seen)
    vrx = irx*load
    power_in = .5*(vtx_ads*((source_vpk-vtx_ads)/50).conjugate()).real
    power_rf = abs(vrx_ads)**2/(2*r)
    loss_tx = abs(itx_coil)**2*RTX/2
    loss_rx = abs(irx)**2*RRX/2
    voltage_err = max(abs(vtx-vtx_ads), abs(abs(vrx)-abs(vrx_ads)))
    assert voltage_err < 2e-6, (case, r, c, k, voltage_err)
    residual = power_in - power_rf - loss_tx - loss_rx
    assert abs(residual) < 3e-8, residual
    return {
        "network": case[0], "k_assumed": k, "rf_parallel_R_ohm": r, "rf_parallel_C_pF": c,
        "tx_series_pF": 61.3, "tx_shunt_pF": 438.0, "rx_series_pF": series_pf,
        "rx_shunt_pF": shunt_pf, "available_source_dBm": PIN_DBM,
        "rf_ic_diff_peak_V": abs(vrx_ads), "accepted_TX_mW": 1000*power_in,
        "absorbed_RF_at_ic_mW": 1000*power_rf, "available_to_RF_fraction": power_rf/AVAILABLE_W,
        "min_RF_to_board_efficiency_for_120mW": .120/power_rf,
        "tx_coil_loss_mW": 1000*loss_tx, "rx_coil_loss_mW": 1000*loss_rx,
        "source_return_loss_dB": -20*math.log10(abs((z_tx-50)/(z_tx+50))),
        "rx_coil_load_re_ohm": z_seen.real, "rx_coil_load_im_ohm": z_seen.imag,
        "power_residual_W": residual, "analytical_voltage_crosscheck_error_V": voltage_err,
    }


def main(existing):
    sim = ads.CircuitSimulator(hpeesof_dir=str(ADS_ROOT))
    rows, runs = [], []
    for case in MATCHES:
        directory = HERE / "passive-runs" / case[0]
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "envelope.ckt"
        if existing:
            assert path.read_text(encoding="ascii") == deck(*case[1:])
        else:
            path.write_text(deck(*case[1:]), encoding="ascii")
            proc = subprocess.run([str(ADS_ROOT/"bin/hpeesofsim.exe"), str(path), "--dataset-name=envelope", "-T4"],
                                  cwd=directory, env=sim._env, capture_output=True, text=True, timeout=90)
            (directory/"simulator.log").write_text(proc.stdout+proc.stderr, encoding="utf-8")
            if proc.returncode:
                raise RuntimeError(f"ADS exit {proc.returncode}: see {directory / 'simulator.log'}")
        result = directory / "envelope.ds"
        with dataset.open(result) as data:
            block = next(n for n in data.varblock_names if n.endswith("HB1.HB"))
            frame = data[block].to_dataframe().reset_index()
        carrier = frame[np.isclose(frame["freq"], FREQ, rtol=0, atol=1)]
        assert len(carrier) == 54
        for _, x in carrier.iterrows():
            rows.append(validate(case, float(x.RIN.real), float(x.CINPF.real), float(x.COUPLING.real),
                                 complex(x.TX), complex(x.RFIC)))
        runs.append({"deck": path.relative_to(HERE).as_posix(), "dataset": result.relative_to(HERE).as_posix(),
                     "dataset_sha256": hashlib.sha256(result.read_bytes()).hexdigest(),
                     "carrier_points": len(carrier), "completed_log": "Simulation finished" in (directory/"simulator.log").read_text(encoding="utf-8")})
    with (HERE/"rf-envelope.csv").open("w", newline="", encoding="ascii") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    summary = {"runs": runs, "carrier_points": len(rows), "source_dBm": PIN_DBM,
               "load_boundary": "Linear differential R parallel C at the receiver IC RF pins; independent test loads, not silicon models",
               "design_target_board_mW": 120, "frequency_Hz": FREQ,
               "max_power_residual_W": max(abs(x["power_residual_W"]) for x in rows),
               "max_crosscheck_error_V": max(x["analytical_voltage_crosscheck_error_V"] for x in rows)}
    (HERE/"rf-envelope-execution.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="ascii")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--existing",action="store_true")
    main(parser.parse_args().existing)

"""Run the assembled low-capacitance AFE's small-signal AC checks in ADS."""
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
BASE = HERE.parents[1] / "ads-closeout-2026-11-22/four-coax-native/afe.ckt"
ADS = Path(os.environ.get("CURALINK_ADS_ROOT", r"C:\Program Files\Keysight\ADS2026_Update2"))
NODES = ["ch1", "ch2", "ch3", "ch4", "ref"]


def circuit():
    result = ['#uselib "ckt", "S3P"']
    for line in BASE.read_text().splitlines():
        if re.match(r"tlv9002_tlv9002:xu(101_[1-4]|109_1) ", line):
            continue
        if re.match(r"R:r\d+ (\w+_minus vmid R=1000|\w+_pre \w+_minus R=10000)$", line):
            continue
        if re.match(r"R:r\d+ \w+_plus vmid R=22000000", line):
            line = line.replace("vmid R=22000000", "vmid_raw R=21780000")
        if line.startswith("Cap_L:c_trace_"):
            line = line.replace("C=2p", "C=LAY_P*1e-12")
        if line.startswith("Cap_L:c_esd_"):
            line = line.replace("C=0.5p", "C=0.65p")
        if line.startswith("SINGLE="):
            result.extend(['LAY_P=.60', 'V_Source:Voper OPER 0 Vdc=1.5'])
            result.append("tlv9002_tlv9002:xu109_1 vmid_raw afe_spare_a avdd_3v0 0 afe_spare_a")
            result.extend(f"Cap_L:c{n} avdd_3v0 0 C=100n" for n in range(632,636))
            for n in NODES:
                result.extend([f'S3P:X_{n} a_{n} b_{n} c_{n} 0 File="max44280-gain11.s3p"',
                               f'Cap_L:p1_{n} a_{n} {n}_plus C=1',
                               f'Cap_L:p2_{n} b_{n} vmid C=1',
                               f'Cap_L:p3_{n} c_{n} {n}_pre C=1',
                               f'L:op_{n} {n}_pre OPER L=1e9',
                               f'Cap_L:c_extra_{n} {n}_plus 0 C=.2p'])
        if re.match(r'V_Source:v(ch[1-4]|ref) ', line):
            name = line.split()[0].split(":v")[1]
            idx = NODES.index(name)
            line = f'V_Source:v{name} src_{name} 0 Vdc=0 Vac=polar(max(0,1-abs(AC_STIM-{idx})),0)'
        if line.startswith("V_Source:vinj"):
            line = line.replace("polar(INJECT,0)", "0")
        if line.startswith("SweepPlan:Stim"):
            line = line.replace("Stop=3", "Stop=4")
        result.append(line)
    return "\n".join(result) + "\n"


def main():
    result = []
    simulator = ads.CircuitSimulator(hpeesof_dir=str(ADS))
    for pf in (.60, .75, 1.0):
        content = circuit().replace("LAY_P=.60", f"LAY_P={pf:g}")
        with tempfile.TemporaryDirectory() as folder:
            tmp = Path(folder)
            (tmp / "afe.ckt").write_text(content)
            shutil.copyfile(HERE / "max44280-gain11.s3p", tmp / "max44280-gain11.s3p")
            cmd = [str(ADS/"bin/hpeesofsim.exe"), "afe.ckt", "--dataset-name=afe", "-T4"]
            run = subprocess.run(cmd, cwd=tmp, env=simulator._env, capture_output=True, timeout=240)
            log = run.stdout + run.stderr
            (HERE / f"ads-{pf:g}pF.log").write_bytes(log)
            if run.returncode:
                raise RuntimeError(log.decode(errors="replace")[-1800:])
            with dataset.open(tmp/"afe.ds") as ds:
                df = ds["Case.AC1.AC"].to_dataframe().reset_index()
            if pf == .6:
                shutil.copyfile(tmp/"afe.ds", HERE/"stressed.ds")
            for i, n in enumerate(NODES):
                data = df[(df["AC_STIM"] == i) & (df["freq"] >= 300) & (df["freq"] <= 7000)]
                f = data.freq.to_numpy()
                v = data["ffc_"+n].to_numpy()
                drive = data["src_ref" if n == "ref" else "genout_"+n].to_numpy()
                z = 47000*v/(drive-v)
                gain = data["adc_in_"+(n[-1] if n != "ref" else "1")].to_numpy()
                result.append(dict(layout_pF=pf, driven=n, min_Z_Mohm=float(min(abs(z))/1e6),
                                   at_Hz=float(f[np.argmin(abs(z))]),
                                   gain_1k_V_per_V=float(abs(gain[np.argmin(abs(f-1000))]))))
        if pf == .6:
            (HERE/"stressed.ckt").write_text(content)
    (HERE/"results.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result[::5],indent=2))


if __name__ == "__main__":
    main()

from pathlib import Path
import os, subprocess, json, csv
import numpy as np
from keysight.edatoolbox import ads
from keysight.ads import dataset
here = Path(__file__).resolve().parent
root = Path(os.environ.get("CURALINK_ADS_ROOT", os.environ.get("HPEESOF_DIR", r"C:\Program Files\Keysight\ADS2026_Update2")))
engine = ads.CircuitSimulator(hpeesof_dir=str(root))
process = subprocess.run([str(root/"bin/hpeesofsim.exe"), "regulator.ckt", "--dataset-name=regulator"], cwd=here, env=engine._env, capture_output=True, timeout=120)
(here/"simulation.log").write_bytes(process.stdout + process.stderr)
if process.returncode:
    raise RuntimeError((process.stdout+process.stderr).decode(errors="replace")[-1800:])
with dataset.open(here/"regulator.ds") as data:
    frame = data["T1.TRAN"].to_dataframe().reset_index()
print(frame.columns.tolist())
table = frame[["time","src","rect_n","wpt","cmd"]].copy()
table["load_mA"] = table.wpt * (0.4 + 4.4 * table.cmd)
table.to_csv(here/"waveforms.csv", index=False)
times = np.array([0.0025,0.0038,0.0058,0.0078,0.0108,0.0199])
summary = {
    "tool":"ADS 2026 Update 2", "vendor_source":"https://www.ti.com/lit/zip/SBVM527",
    "regulator":"TPS70950DBVR", "stimulus":"stiff raw voltage source + 0.2 ohm, 2/24 mA conductance at 5 V",
    "samples": [{key:float(value) for key, value in table.iloc[(table.time-t).abs().argmin()].items()} for t in times],
    "output_peak_V":float(table.wpt.max()),
    "load_step_min_3_to_4ms_V":float(table.loc[(table.time>=.003)&(table.time<.004),"wpt"].min())
}
(here/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary, indent=2))
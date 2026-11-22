"""Drive the fixed coils, fitted package and TI LDO together in ADS transient."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import run_bridge as bridge

HERE = Path(__file__).resolve().parent


def main(caps, duration_us, step_ns, existing=False):
    target=HERE/"bridge-runs"/"startup"
    target.mkdir(parents=True,exist_ok=True)
    # The ADS-translated original vendor subcircuit is shared with the independent
    # low-frequency regulator test. Refer to that file to keep one source of truth.
    regulator="../../../regulator-2026-11-22/tps70950.net"
    assert (target/regulator).is_file()
    source=bridge.make_deck([bridge.case("startup",pin=26,caps=caps)],31)
    source=source.split("SDD:LOAD")[0].replace("SaveCurrent=yes","SaveCurrent=no")
    source+=f"""
#include "{regulator}"
V_Source:ENABLE EN 0 Vdc=2
tps70950:REG OUT 0 EN WPT
R:RESR WPT OCAP R=.02
C:COUT OCAP 0 C=4.7 uF
; Three current increments use a positive conductance, valid through startup.
; Full demand 24mA at 5V; add 5 and then 15mA for radio/control sensitivities.
V_Source:COMMAND CMD 0 V_Tran=pwl(time,0,24,.000349,24,.00035,29,.000599,29,.0006,39,.000849,39,.00085,3.74,.002,3.74)
SDD:DEMAND WPT 0 CMD 0 I[1,0]=_v1*_v2*.0002 I[2,0]=0
Tran:T1 StopTime={duration_us} usec MaxTimeStep={step_ns} nsec StatusLevel=0 OutputPlan="TSAVE"
OutputPlan:TSAVE Type="Output" UseNodeNestLevel=no NodeName[1]="RAW" NodeName[2]="WPT" NodeName[3]="CMD" UseCurrentNestLevel=no
"""
    path=target/"startup.ckt"
    if existing:
        if path.read_text(encoding="ascii")!=source:
            raise ValueError("existing transient deck does not match these parameters")
    else:
        path.write_text(source,encoding="ascii")
    sim=bridge.ads.CircuitSimulator(hpeesof_dir=str(bridge.ADS))
    for attempt in range(0 if existing else 6):
        proc=subprocess.run([str(bridge.ADS/"bin/hpeesofsim.exe"),str(path),"--dataset-name=startup","-T4"],
                            cwd=target,env=sim._env,capture_output=True,text=True,timeout=1200)
        log=proc.stdout+proc.stderr
        (target/"simulator.log").write_text(log,encoding="utf-8")
        if not proc.returncode:
            break
        if "Licensed number of users already reached" not in log or attempt>=5:
            raise RuntimeError(log[-3000:])
        time.sleep(12)
    with bridge.dataset.open(target/"startup.ds") as d:
        name=next(n for n in d.varblock_names if n.upper().endswith(".TRAN"))
        frame=d[name].to_dataframe().reset_index()
    print(frame.columns.tolist(),flush=True)
    t=frame.time.to_numpy(float)
    raw=frame.RAW.to_numpy(float)
    out=frame.WPT.to_numpy(float)
    demand=frame.CMD.to_numpy(float)
    assert np.all(np.isfinite(out)) and t[-1]>=duration_us*1e-6*.99999
    windows=[]
    for lower in range(0,int(duration_us),10):
        use=(t>=lower*1e-6)&(t<=(lower+10)*1e-6)
        if not use.any():
            continue
        def avg(x):
            return float(np.trapezoid(x[use],t[use])/(t[use][-1]-t[use][0]))
        windows.append(dict(t_start_us=lower,t_stop_us=lower+10,raw_min_V=raw[use].min(),
                            raw_mean_V=avg(raw),raw_max_V=raw[use].max(),
                            WPT_min_V=out[use].min(),WPT_mean_V=avg(out),WPT_max_V=out[use].max(),
                            load_mean_mA=avg(demand*out/5)))
    with (target/"time-windows.csv").open("w",newline="",encoding="ascii") as f:
        w=csv.DictWriter(f,fieldnames=windows[0])
        w.writeheader()
        w.writerows(windows)
    first=np.flatnonzero(out>=4.75)
    summary={"points":len(t),"stop_us":float(t[-1]*1e6),"source_dBm":26,
             "raw_min_V":raw.min(),"raw_max_V":raw.max(),"WPT_max_V":out.max(),
             "first_4p75V_us":float(t[first[0]]*1e6) if len(first) else None,
             "assumptions":"nominal 25C fit, assumed Q500 and pin L=1nH, fixed k=0.0662, ideal 50-ohm source, TI typical LDO transient model, output conductance fixture, static 2V enable, no cell/mode/status controller dynamics",
             "last_windows": [windows[x] for x in (33,58,83,-1) if x<len(windows)]}
    (target/"results.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="ascii")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--caps",type=float,nargs=4,default=(60.,375.,1000.,680.))
    p.add_argument("--duration-us",type=int,default=1050)
    p.add_argument("--step-ns",type=float,default=2.)
    p.add_argument("--existing",action="store_true")
    a=p.parse_args()
    main(a.caps,a.duration_us,a.step_ns,a.existing)

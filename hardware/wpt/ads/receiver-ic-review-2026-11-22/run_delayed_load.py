"""ADS baseband transient driven by fixed-coil HB DC output characteristics."""
import csv
import json
from pathlib import Path
import subprocess

import numpy as np
import run_bridge as bridge

HERE=Path(__file__).resolve().parent


def source_curve(pin):
    with (HERE/"bridge-runs/iv/results.csv").open(encoding="ascii",newline="") as f:
        measured={round(float(r["load_mA_actual"]),5):(float(r["RAW_mean_V"]),float(r["load_mA_actual"])*1e-3)
                  for r in csv.DictReader(f) if float(r["pin"])==pin}
    with (HERE/"bridge-runs/matrix/results.csv").open(encoding="ascii",newline="") as f:
        for r in csv.DictReader(f):
            if r["label"].startswith(f"demand_{pin}_"):
                measured.setdefault(round(float(r["load_mA_actual"]),5),
                                    (float(r["RAW_mean_V"]),float(r["load_mA_actual"])*1e-3))
    points=sorted(measured.values())
    if len(points)<18 or points[0][0]>.25 or points[-1][1]>1.1e-6:
        raise ValueError(f"insufficient native HB I-V coverage at {pin} dBm")
    assert all(points[i][0]<points[i+1][0] and points[i][1]>=points[i+1][1]-1e-7 for i in range(len(points)-1))
    # Hold the lowest-voltage simulated current constant for the sub-0.25V
    # startup interval. Extend near-open point by 10mV to smooth current to zero.
    points=[(0.,points[0][1])]+points+[(points[-1][0]+.01,0.)]
    return points


def main():
    root=HERE/"bridge-runs"/"delayed_load"
    root.mkdir(parents=True,exist_ok=True)
    assert (root/"../../../regulator-2026-11-22/tps70950.net").is_file()
    source=["Options ResourceUsage=yes UseNutmegFormat=no EnableOptim=no",
            '#include "../../../regulator-2026-11-22/tps70950.net"',
            'V_Source:ENABLE EN 0 Vdc=2',
            'V_Source:FIELD FIELD 0 V_Tran=pwl(time,0,0,.00005,1,.026,1,.02605,0,.04,0)',
            'V_Source:CMD CMD 0 V_Tran=pwl(time,0,1.74,.0049,1.74,.005,24,.0099,24,.01,29,.0149,29,.015,39,.0199,39,.020,3.74,.0239,3.74,.024,1.74,.04,1.74)']
    curves={}
    for pin in (25,26,27):
        curve=source_curve(pin)
        increments = [f"{curve[0][1]:.13g}"]
        for (v0,i0),(v1,i1) in zip(curve,curve[1:]):
            if i1!=i0:
                increments.append(f"({i1-i0:.13g})*max(0,min(1,(_v1-{v0:.13g})/{v1-v0:.13g}))")
        crv="+".join(increments)
        curves[pin]=curve
        source+= [
            f'SDD:RF{pin} RAW{pin} 0 FIELD 0 I[1,0]=-(_v2*max(0,{crv})) I[2,0]=0',
            f'R:RESR{pin} RAW{pin} CAP{pin} R=.05',
            f'C:CIN{pin} CAP{pin} 0 C=1 uF',
            f'tps70950:REG{pin} RAW{pin} 0 EN WPT{pin}',
            f'R:CESR{pin} WPT{pin} CO{pin} R=.02',
            f'C:COUT{pin} CO{pin} 0 C=4.7 uF',
            f'SDD:LOAD{pin} WPT{pin} 0 CMD 0 I[1,0]=_v1*_v2*.0002 I[2,0]=0']
    source+='Tran:T1 StopTime=40 msec MaxTimeStep=5 usec OutputAllPoints=no StatusLevel=0'.splitlines()
    deck=root/"delayed.ckt"
    deck.write_text("\n".join(source)+"\n",encoding="ascii")
    (root/"source-IV.json").write_text(json.dumps(curves,indent=2)+"\n",encoding="ascii")
    sim=bridge.ads.CircuitSimulator(hpeesof_dir=str(bridge.ADS))
    proc=subprocess.run([str(bridge.ADS/"bin/hpeesofsim.exe"),str(deck),"--dataset-name=delayed","-T4"],
                        cwd=root,env=sim._env,capture_output=True,text=True,timeout=180)
    (root/"simulator.log").write_text(proc.stdout+proc.stderr,encoding="utf-8")
    assert not proc.returncode,proc.stderr
    with bridge.dataset.open(root/"delayed.ds") as d:
        frame=d["T1.TRAN"].to_dataframe().reset_index()
    cols=["time","FIELD","CMD"]+[f"{key}{p}" for p in (25,26,27) for key in ("RAW","WPT")]
    frame[cols].to_csv(root/"waveforms.csv",index=False)
    t=frame.time.to_numpy(float)
    assert np.isclose(t[-1],.040)
    data=[]
    for p in (25,26,27):
        v=frame[f"WPT{p}"].to_numpy(float)
        raw=frame[f"RAW{p}"].to_numpy(float)
        assert np.isfinite(raw).all() and np.isfinite(v).all()
        first=np.flatnonzero(v>=4.75)
        fall=np.flatnonzero((t>=.02605)&(v<4.75))
        for label,start,stop,ma in (("settled_before_full",.0047,.0049,1.74),("full",.0097,.0099,24),
                                    ("full_radio5",.0147,.0149,29),("full_radio15",.0197,.0199,39),
                                    ("taper",.0237,.0239,3.74),("complete",.0257,.0259,1.74),
                                    ("field_removed_4ms",.0298,.030,1.74),("field_removed_14ms",.0398,.040,1.74)):
            sl=(t>=start)&(t<=stop)
            def avg(a):
                return float(np.trapezoid(a[sl],t[sl])/(t[sl][-1]-t[sl][0]))
            data.append(dict(pin_dBm=p,stage=label,cmd_mA_at_5V=ma,mean_RECT_DC_V=avg(raw),
                             min_WPT_V=min(v[sl]),mean_WPT_V=avg(v),mean_load_mA=ma*avg(v)/5,
                             first_4p75V_ms=float(t[first[0]]*1e3) if len(first) else None,
                             fall_4p75V_delay_after_field_zero_ms=1000*(t[fall[0]]-.02605) if len(fall) else None))
    with (root/"results.csv").open("w",encoding="ascii",newline="") as f:
        w=csv.DictWriter(f,fieldnames=data[0])
        w.writeheader()
        w.writerows(data)
    print(json.dumps(data,indent=2))


if __name__=="__main__":
    main()

"""Actual 13.56 MHz ADS HB of the four terminals of one BAS4002A-RPP.

Each internal junction uses an authored fit to Infineon's published per-diode
curves. This program does not supply a vendor macromodel or a thermal model.
ADS Python executes the deck. Use the exported table on an unlicensed computer.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

import numpy as np
from keysight.ads import dataset
from keysight.edatoolbox import ads

HERE = Path(__file__).resolve().parent
ADS = Path(os.environ.get("CURALINK_ADS_ROOT", os.environ.get("HPEESOF_DIR", r"C:\Program Files\Keysight\ADS2026_Update2")))
F = 13.56e6
W = 2 * math.pi * F
VT25 = 8.617333262e-5 * 298.15
CAPS = (59.3, 375, 826.8, 772)
LOADS = {"full_120mW": 24.0, "nominal_CC": 21.74, "2mA_taper": 3.74, "complete_field_on": 1.74, "regulator_only": .001}
for _phase, _base in (("full",24.),("taper",3.74),("complete",1.74)):
    for _radio in (5.,15.):
        LOADS[f"{_phase}_plus_{int(_radio)}mA_status"] = _base+_radio
SOURCE = "https://www.infineon.com/assets/row/public/documents/24/49/infineon-bas4002aseries-ds-en.pdf"


def fit_models():
    amps = np.array([.01, .06, .1, .2])
    result = []
    for label, volts, c5 in (("typical", [.39, .49, .55, .69], 2), ("p2_max_sensitivity", [.44, .55, .62, .79], 5)):
        design = np.stack([np.ones_like(amps), np.log(amps), amps], axis=1)
        offset, slope, resistance = np.linalg.lstsq(design, volts, rcond=None)[0]
        saturation = np.exp(-offset/slope)
        prediction = slope*np.log1p(amps/saturation)+amps*resistance
        # C(5V) is tabulated. The 0.65V junction potential and .50 exponent
        # approximate the curvature on p.3. No package extraction is available.
        c0 = c5*(1+5/.65)**.5
        result.append(dict(label=label, Is=saturation, n=slope/VT25, Rs=resistance,
                           Cj0_pF=c0, Vj=.65, M=.5, C5_pF=c5, datasheet_p2_V=volts,
                           reproduced_V=prediction.tolist(), max_fit_error_V=max(abs(prediction-volts))))
    return result


MODELS = fit_models()


def case(label, pin=25., k=.0662, load="full_120mW", caps=CAPS, model=0, q=500., lead=1., winding=1., res_cap=1.):
    return dict(label=label, pin=pin, k=k, load=load, mA=LOADS[load], caps=list(caps),
                model=model, q=q, lead_nH=lead, winding_R_factor=winding, res_cap_uF=res_cap)


def cases(stage, selected):
    if stage=="iv":
        out=[]
        for p in (25,26,27):
            for ma in (.001,.5,1,2,3,5,7,10,15,20,24,29,32,35,39,42,45,50,55,60,70,90,120):
                point=case(f"iv_{p}_{ma}",pin=p,caps=selected)
                point.update(mA=ma,load="voltage_compliant_DC_load")
                out.append(point)
        return out
    if stage=="tx_trim":
        out=[]
        for p,k,load in ((25,.04965,"full_120mW"),(26,.0662,"full_plus_15mA_status")):
            for ts in (56,58,60,62,64):
                for th in (300,375,450,525):
                    out.append(case(f"txtrim_{p}_{k}_{ts}_{th}",pin=p,k=k,load=load,
                                    caps=(ts,th,selected[2],selected[3])))
        return out
    if stage=="tvs":
        out=[]
        for p in (25,26,27):
            for k in (.0662,.10,.13):
                for br in (16.7,18.5,100.0):
                    row=case(f"TVS_{br}_{p}_{k}",pin=p,k=k,load="regulator_only",caps=selected)
                    row["Vbr1mA"]=br
                    out.append(row)
        return out
    if stage=="search":
        # Finite grid of straightforward populated E-series single/parallel values.
        return [case(f"tune_{cts}_{cth}_{crs}_{crh}",caps=(cts,cth,crs,crh))
                for cts in (58.2,59.3,60.4) for cth in (330,375,420)
                for crs in (820,910,1000) for crh in (680,750,820)]
    if stage == "matrix":
        out = [case(f"demand_{p}_{l}", pin=p, load=l, caps=selected)
               for p in (20,23,23.5,24,25,26,27) for l in LOADS]
        for k in (.0331,.04965,.08275):
            for p in (23.5,25,26):
                for l in ("full_120mW", "regulator_only"):
                    out.append(case(f"coupling_{k}_{p}_{l}", pin=p, k=k, load=l, caps=selected))
        for p in (23.5,25,26):
            for mdl,q,lead,wr in ((1,500,1,1),(0,250,2,1.25),(1,250,2,1.25)):
                out.append(case(f"loss_fit_{p}_{mdl}_{q}", pin=p,caps=selected, model=mdl,q=q,lead=lead,winding=wr))
        for tol in (.02,.05):
            for bits in range(16):
                cap = [x*(1+(tol if bits & (1<<i) else -tol)) for i,x in enumerate(selected)]
                out.append(case(f"cap_{int(100*tol)}pct_{bits:04b}",caps=cap))
        out.append(case("small_reservoir", caps=selected, res_cap=.47))
        out.append(case("paper_network_50ohm_reference", caps=(61.3,438,673.3,1050)))
        return out
    if stage=="pilot":
        return [case("loaded",caps=selected),case("near_open",caps=selected,load="regulator_only"),
                case("weak",caps=selected,k=.04965, model=1,q=250,lead=2,winding=1.25)]
    if stage in ("order15","order63"):
        wanted={"demand_25_full_120mW","demand_26_full_plus_5mA_status",
                "demand_27_full_plus_15mA_status","demand_27_regulator_only","cap_5pct_1110"}
        return [r for r in cases("matrix",selected) if r["label"] in wanted]
    raise ValueError(stage)


def indexed(values):
    # ADS expressions are compact for blocks of identical samples.
    chunks = []
    first = 0
    while first < len(values):
        last = first
        while last+1 < len(values) and values[last+1] == values[first]:
            last += 1
        chunks.append((first,last,values[first]))
        first = last+1
    if len(chunks) == 1:
        return f"{values[0]:.13g}"
    common = max(set(values), key=values.count)
    terms = [f"{common:.13g}"]
    for first,last,v in chunks:
        if v == common:
            continue
        if first == last:
            window=f"max(0,1-abs(IDX-{first}))"
        else:
            window=f"max(0,min(1,min(IDX-{first}+1,{last}+1-IDX)))"
        terms.append(f"({v-common:.13g})*{window}")
    return "+".join(terms)


def make_deck(rows, order):
    field_map = {"PinR": "pin", "LinkK": "k", "ILOADmA": "mA", "QCAP": "q", "LEADnH": "lead_nH",
                 "RWIND": "winding_R_factor", "CUF":"res_cap_uF"}
    params = {name:[r[key] for r in rows] for name,key in field_map.items()}
    for i,key in enumerate(("CTS","CTH","CRS","CRH")):
        params[key] = [r["caps"][i] for r in rows]
    for field,key in (("ISFIT","Is"),("NFIT","n"),("RSFIT","Rs"),("C0FIT","Cj0_pF")):
        params[field] = [MODELS[r["model"]][key] for r in rows]
    clamp=""
    if "Vbr1mA" in rows[0]:
        params["VBRK"]=[r["Vbr1mA"] for r in rows]
        # Piecewise extrapolation through three data points, not a measured
        # low-current DC curve or a qualification of steady-state dissipation.
        clamp="""Short:CTVS RAW TVS Mode=0 SaveCurrent=yes
SDD:CLAMP TVS 0 I[1,0]=(min(1, max(0, (100-VBRK)))*(5e-6*min(1,max(0,_v1/15))+.000995*min(1,max(0,(_v1-15)/(VBRK-15)))+max(0,_v1-VBRK)*16.399/max(1,24.4-VBRK)))
"""
    p = "\n".join(f"{name}={indexed(values)}" for name, values in params.items())
    return f"""Options Temp=25 ResourceUsage=yes UseNutmegFormat=no EnableOptim=no
IDX=0
{p}
OMEGA={W:.15g}
Port:PORT1 GEN 0 Num=1 Z=50 Ohm P[1]=polar(dbmtow(PinR),0) Freq[1]=13.56 MHz Noise=no
Short:PTX GEN TX Mode=0 SaveCurrent=yes
R:RTH TX TH R=(1/(OMEGA*CTH*1e-12*QCAP)) Noise=no
C:CTH TH 0 C=(CTH*1e-12)
R:RTS TX TS R=(1/(OMEGA*CTS*1e-12*QCAP)) Noise=no
C:CTS TS TXCOIL C=(CTS*1e-12)
L:L1 TXCOIL 0 L=2.49 uH R=(1.8*RWIND) Noise=no
L:L2 AC2 RXPLUS L=.330 uH R=(.399*RWIND) Noise=no
Mutual:LINK K=LinkK Inductor1="L1" Inductor2="L2"
Short:PRX RXPLUS RX Mode=0 SaveCurrent=yes
R:RRS RX RS R=(1/(OMEGA*CRS*1e-12*QCAP)) Noise=no
C:CRS RS AC1 C=(CRS*1e-12)
R:RRH AC1 RH R=(1/(OMEGA*CRH*1e-12*QCAP)) Noise=no
C:CRH RH AC2 C=(CRH*1e-12)
; Package pin 1 DC-, pins 2,3 AC, pin 4 DC+. No RF input pin is grounded.
Short:PACKAGE_I AC1 AC1A Mode=0 SaveCurrent=yes
L:lead2 AC1A P2 L=(LEADnH*1e-9) R=.008 Noise=no
L:lead3 AC2 P3 L=(LEADnH*1e-9) R=.008 Noise=no
L:lead4 P4 RAW L=(LEADnH*1e-9) R=.008 Noise=no
L:lead1 0 P1 L=(LEADnH*1e-9) R=.008 Noise=no
model BASFIT Diode Is=ISFIT N=NFIT Rs=RSFIT Cjo=(C0FIT*1e-12) Vj=.65 M=.5 Fc=.5 Tnom=25 Imax=100
Short:ID1 P1 A1 Mode=0 SaveCurrent=yes
Short:ID2 P2 A2 Mode=0 SaveCurrent=yes
Short:ID3 P1 A3 Mode=0 SaveCurrent=yes
Short:ID4 P3 A4 Mode=0 SaveCurrent=yes
"BASFIT":D1 A1 P2 Mode=1 Noise=no
"BASFIT":D2 A2 P4 Mode=1 Noise=no
"BASFIT":D3 A3 P3 Mode=1 Noise=no
"BASFIT":D4 A4 P4 Mode=1 Noise=no
; Assumed reservoir ESR/ESL; RF lead estimates and Q explain the sensitivity.
L:LRES RAW RR L=.7 nH R=.05 Noise=no
C:CRES RR 0 C=(CUF*1e-6)
Short:IDC RAW OUT Mode=0 SaveCurrent=yes
; Smooth compliance eliminates unphysical negative-voltage current demand.
; Above 2 V the current demand equals the named load to better than 5e-9 relative.
SDD:LOAD OUT 0 I[1,0]=(ILOADmA*1e-3*tanh(_v1/.2))
{clamp}\
HB:HB1 MaxOrder={order} Freq[1]=13.56 MHz Order[1]={order} StatusLevel=0 OutputPlan="OUTP"
OutputPlan:OUTP Type="Output" UseNodeNestLevel=yes NodeNestLevel=1 UseCurrentNestLevel=yes CurrentNestLevel=1
SweepPlan:CASES Start=0 Stop={len(rows)-1} Step=1
ParamSweep:Batch SimInstanceName[1]="HB1" SweepVar="IDX" SweepPlan="CASES" StatusLevel=0
"""


def analyze(x, group):
    group = group.sort_values("freq")
    freq = group.freq.to_numpy(float)
    n = np.rint(freq/F).astype(int)
    assert (n == np.arange(len(n))).all()
    v = {c:group[c].to_numpy(complex) for c in group.columns if c not in ("IDX","Mix[1]","freq")}
    def power(a,b):
        return float((a[0]*np.conj(b[0])).real+.5*np.dot(a[1:],np.conj(b[1:])).real)
    def wave(a):
        fft = np.zeros(2049, complex)
        fft[:len(a)] = a/2
        fft[0] = a[0]
        return np.fft.irfft(fft,n=4096)*4096
    def peak(a):
        return np.max(abs(wave(a)))
    def rms(a):
        return math.sqrt(power(a,a))
    def z_fields(name,z):
        return {name+"_R_ohm":z.real, name+"_X_ohm":z.imag}
    vraw = v["RAW"].real[0]
    iraw = v["IDC.i"].real[0]
    vin,iin = v["TX"],v["PTX.i"]
    zcoil=(v["RXPLUS"][1]-v["AC2"][1])/v["PRX.i"][1]
    zbridge=(v["AC1"][1]-v["AC2"][1])/v["PACKAGE_I.i"][1]
    ztx=vin[1]/iin[1]
    raw_spectrum=v["RAW"]
    raw_wave=wave(raw_spectrum)
    caps=x["caps"]
    cap_voltages=[v["TS"]-v["TXCOIL"],v["TH"],v["RS"]-v["AC1"],v["RH"]-v["AC2"]]
    icaps=[volts*1j*2*np.pi*freq*pf*1e-12 for volts,pf in zip(cap_voltages,caps)]
    itx=icaps[0]
    irx=v["PRX.i"]
    loss_coils=x["winding_R_factor"]*(1.8*power(itx,itx)+.399*power(irx,irx))
    loss_caps=sum(power(i,i)/(W*pf*1e-12*x["q"]) for i,pf in zip(icaps,caps))
    dv=[v["P1"]-v["P2"],v["P2"]-v["P4"],v["P1"]-v["P3"],v["P3"]-v["P4"]]
    di=[v[f"ID{i}.i"] for i in range(1,5)]
    loss_junctions=sum(power(a,b) for a,b in zip(dv,di))
    ileads=[di[0]+di[2],di[1]-di[0],di[3]-di[2],di[1]+di[3]]
    loss_leads=sum(.008*power(i,i) for i in ileads)
    ires=v["RR"]*1j*2*np.pi*freq*x["res_cap_uF"]*1e-6
    loss_res=.05*power(ires,ires)
    paccept=power(vin,iin)
    loadp=power(v["RAW"],v["IDC.i"])
    clampp=power(v["RAW"],v["CTVS.i"]) if "CTVS.i" in v else 0
    residual=paccept-loadp-loss_coils-loss_caps-loss_junctions-loss_leads-loss_res-clampp
    assert abs(residual)<2e-5, (x["label"],residual)
    avail=1e-3*10**(x["pin"]/10)
    return {**{k:v for k,v in x.items() if k != "caps"},**dict(zip(("CTS_pF","CTH_pF","CRS_pF","CRH_pF"),caps)),
            "RAW_mean_V":vraw,"RAW_min_V":min(raw_wave),"RAW_max_V":max(raw_wave),"RAW_ripple_mVpp":np.ptp(raw_wave)*1000,
            "load_mA_actual":iraw*1000,"raw_load_mW":1000*loadp,"available_mW":1000*avail,
            "accepted_mW":1000*paccept,"available_to_raw_fraction":loadp/avail,
            "TVS_mean_mW":clampp*1000,"TVS_mean_mA":(1000*v["CTVS.i"][0].real if "CTVS.i" in v else 0),
            "headroom_min_ge_6V":min(raw_wave)>=6, "headroom_min_ge_5p1V":min(raw_wave)>=5.1,
            "return_loss_dB":-20*math.log10(abs((ztx-50)/(ztx+50))),
            **z_fields("transform_at_RX",zcoil),**z_fields("package_AC",zbridge),
            "bridge_reverse_peak_V":max(-min(wave(a)) for a in dv),
            "junction_forward_peak_mA":1000*max(max(wave(i)) for i in di),
            "junction_avg_max_mA":1000*max(i[0].real for i in di),
            "junctions_sum_mW":loss_junctions*1000,"capacitor_ESR_mW":loss_caps*1000,
            "winding_TX_mW":1000*1.8*x["winding_R_factor"]*power(itx,itx),
            "winding_RX_mW":1000*.399*x["winding_R_factor"]*power(irx,irx),
            "RX_series_Arms":rms(icaps[2]),"RX_shunt_Arms":rms(icaps[3]),
            "TX_series_Vpk":peak(cap_voltages[0]), "RX_series_Vpk":peak(cap_voltages[2]),
            "reconstructed_power_residual_W":residual}


def run(stage, selected, retries, existing=False):
    rows=cases(stage,selected)
    order={"order15":15,"order63":63}.get(stage,31)
    target=HERE/"bridge-runs"/stage
    target.mkdir(parents=True,exist_ok=True)
    src=target/"bas4002a.ckt"
    source_text = make_deck(rows,order)
    if existing and src.read_text(encoding="ascii") != source_text:
        raise ValueError("existing deck differs from requested sweep")
    src.write_text(source_text,encoding="ascii")
    (target/"cases.json").write_text(json.dumps(rows,indent=2)+"\n",encoding="ascii")
    sim=ads.CircuitSimulator(hpeesof_dir=str(ADS))
    for attempt in range(0 if existing else retries+1):
        proc=subprocess.run([str(ADS/"bin/hpeesofsim.exe"),str(src),"--dataset-name=bas4002a","-T4"],
                            cwd=target,env=sim._env,capture_output=True,text=True,timeout=600)
        log=proc.stdout+proc.stderr
        (target/"simulator.log").write_text(log,encoding="utf-8")
        if not proc.returncode:
            break
        if "Licensed number of users already reached" not in log or attempt == retries:
            raise RuntimeError(f"ADS exit {proc.returncode}: {target / 'simulator.log'}")
        print("Waiting for local ADS license",stage,attempt+1,flush=True)
        time.sleep(12)
    ds=target/"bas4002a.ds"
    with dataset.open(ds) as d:
        b=next(n for n in d.varblock_names if n.endswith("HB1.HB"))
        df=d[b].to_dataframe().reset_index()
    results=[]
    rejected=[]
    for ix,frame in df.groupby("IDX"):
        assert len(frame)==order+1,(ix,len(frame))
        if not np.isfinite(frame["RAW"].to_numpy(complex)).all():
            rejected.append(rows[int(ix)]["label"])
            continue
        results.append(analyze(rows[int(ix)],frame))
    assert len(results)+len(rejected)==len(rows)
    with (target/"results.csv").open("w",newline="",encoding="ascii") as f:
        writer=csv.DictWriter(f,fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    status={"source":SOURCE,"junction_model_provenance":"CuraLink fit, no supplier SPICE",
            "fit_parameters":MODELS,"ADS_log_complete": "Simulation finished" in (target/"simulator.log").read_text(encoding="utf-8"),
            "points":len(results),"invalid_ADS_cases_omitted":rejected,
            "highest_harmonic":order,"deck_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
            "dataset_sha256":hashlib.sha256(ds.read_bytes()).hexdigest(),
            "max_power_residual_W":max(abs(r["reconstructed_power_residual_W"]) for r in results)}
    (target/"execution.json").write_text(json.dumps(status,indent=2)+"\n",encoding="ascii")
    best=max(results,key=lambda r:r["RAW_min_V"])
    print(stage,len(results),"complete; highest minimum RAW",best["label"],best["RAW_min_V"],flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("stage", choices=("pilot","search","matrix","order15","order63","tvs","tx_trim","iv"))
    parser.add_argument("--caps",nargs=4,type=float,default=CAPS)
    parser.add_argument("--retries",type=int,default=5)
    parser.add_argument("--existing",action="store_true")
    args=parser.parse_args()
    run(args.stage,args.caps,args.retries,args.existing)

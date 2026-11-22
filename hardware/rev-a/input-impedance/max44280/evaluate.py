"""Evaluate five MAX44280 gain-11 stages with the original four-channel AFE in LTspice."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import numpy as np

OUT = Path(__file__).resolve().parent
REVA = OUT.parents[1]
sys.path.insert(0,str(REVA/"ltspice/afe"))
from read_ltspice_raw import read_raw

EXE = os.getenv("CURALINK_LTSPICE_EXE") or str(Path(os.environ["LOCALAPPDATA"])/"Programs/ADI/LTspice/LTspice.exe")


def run(name,deck):
    path=OUT/(name+".cir")
    if name in ("isolated","candidate-ac-ch1","noise-candidate-electronics","op-candidate-mixed-plus"):
        path.write_text(deck,encoding="ascii")
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td)
        text=re.sub(r"(?m)^\.include (\.\./\.\./ltspice/\S+)",lambda m:'.include "'+
                    (OUT/m[1]).resolve().as_posix()+'"',deck)
        (temp/path.name).write_text(text,encoding="ascii")
        subprocess.run([EXE,"-b","-ascii",path.name],cwd=temp,check=True,timeout=160)
        log=(temp/(name+".log")).read_bytes().decode("utf8",errors="replace")
        if "Total elapsed time:" not in log or re.search("fatal error|unknown subcircuit|time step too small",log,re.I):
            raise RuntimeError(log[-4000:])
        rawfile=temp/(name+".raw")
        rawfile.write_bytes(rawfile.read_bytes().decode("cp1252").encode("utf8"))
        return read_raw(rawfile)


def full(trace_pf,fixture_noise=False,all_ti=False,extra_cin_pf=0):
    original=REVA/"ads-closeout-2026-11-22/ltspice-noise"/("with-emulator.cir" if fixture_noise else "electronics.cir")
    deck=original.read_text().split(".noise V(adc_in_1)")[0]
    deck=deck.replace("* CuraLink four-channel fixture; original TI-family equations.",
                      "* Unfitted four-channel gain-11 MAX44280 candidate; four coax inputs, shared reference.")
    if not all_ti:
        deck,n=re.subn(r"(?m)^(xu(?:101_[1-4]|109_1) .+) tlv9002_tlv9002$",
                       r"\1 avdd_3v0 MAX44280",deck)
        assert n==5
        deck+=".lib MAX44280.sub\n"
    deck,n=re.subn(r"(?m)^(c_trace_\w+ \S+ 0) 2p$",rf"\g<1> {trace_pf}p",deck)
    assert n==5
    deck=deck.replace("r_source_ch1 genout_ch1 ffc_ch1","r_source_ch1 genout_ch1 sense_ch1")
    deck+="Vplane sense_ch1 ffc_ch1 0\n"
    if extra_cin_pf:
        for node in ("ch1","ch2","ch3","ch4","ref"):
            deck+=f"C_extra_{node} {node}_plus 0 {extra_cin_pf}p\n"
    return deck


def candidate(trace_pf,stress=False,fixtures=False,drive="ch1"):
    body=full(trace_pf,fixture_noise=fixtures,extra_cin_pf=.2 if stress else 0)
    body,n=re.subn(r"(?m)^(r(?:1002|1020|1038|1056|1146) \S+) vmid 22000000",r"\1 vmid_raw 22000000",body)
    assert n==5
    if stress:
        body=body.replace("22000000","21780000")
        body=re.sub(r"(?m)^(c_esd_\w+ \S+ 0) 0.5p$",r"\g<1> 0.65p",body)
    # U109 stays populated. Its former REF amplifier is now a powered spare.
    body+="Xspare_a vmid_raw spare_a avdd_3v0 0 spare_a tlv9002_tlv9002\n"
    for i in range(4):
        body+=f"C_local_{i} avdd_3v0 0 100n\n"
    if drive!="ch1":
        body=body.replace("sense_ch1","ffc_ch1").replace("Vplane ffc_ch1 ffc_ch1 0\n","")
        body=body.replace("VCH1 src_ch1 0 DC 0 AC 1","VCH1 src_ch1 0 0")
        body,n=re.subn(rf"(?m)^(r_source_{drive} \S+) ffc_{drive} ",rf"\1 sense_{drive} ",body)
        assert n==1
        body,n=re.subn(rf"(?m)^(V{drive.upper()} src_{drive} 0 0)$",r"\1 AC 1",body)
        assert n==1
        body+=f"Vplane sense_{drive} ffc_{drive} 0\n"
    return body


def ac(name,body,drive="ch1"):
    probes=" ".join(f"V(adc_in_{n})" for n in range(1,5))
    result=run(name,body+f".ac dec 80 7 70Meg\n.save V(ffc_{drive}) I(Vplane) {probes} V({drive}_pre)\n.end\n")
    freq=result.trace("frequency").real
    i=result.trace("I(Vplane)")
    zin=result.trace(f"V(ffc_{drive})")/i
    k=int(np.argmin(abs(freq-7000)))
    assert abs(freq[k]-7000)<1e-4
    band=(freq>=300)&(freq<=7000.001)
    # Include 300 Hz explicitly using the samples on either side. 7000 Hz lies
    # exactly on this logarithmic grid.
    zmin=min(float(np.interp(300,freq,abs(zin))),float(np.min(abs(zin[band]))))
    gain=[abs(result.trace(f"V(adc_in_{n})")) for n in range(1,5)]
    output={"Zin_7k_Mohm":abs(zin[k])/1e6,"min_Zin_300_7k_Mohm":zmin/1e6,
            "Yin_equiv_pF_7k":(1/zin[k]).imag/(2*np.pi*freq[k])*1e12,
            "gain_1k_all_four":[float(np.interp(1000,freq,x)) for x in gain],
            "peak_ADC_V_per_V_in_band":[float(np.max(x[band])) for x in gain],
            "gain_1k":float(np.interp(1000,freq,gain[0]))}
    if drive!="ref":
        ch=int(drive[-1])-1
        output["max_quiet_over_active_dB"]=max(float(np.max(20*np.log10(g[band]/gain[ch][band]))) for n,g in enumerate(gain) if n!=ch)
    return output


def noise(name,body):
    data=run(name,body+".noise V(adc_in_1) VCH1 dec 100 300 7000\n.save V(inoise) V(onoise)\n.end\n")
    f=data.trace("frequency").real
    return {"input_uVrms":float(1e6*np.sqrt(np.trapezoid(data.trace("V(inoise)").real**2,f))),
            "output_mVrms":float(1e3*np.sqrt(np.trapezoid(data.trace("V(onoise)").real**2,f)))}


def model_input_checks():
    # The large inductor closes the DC loop. The blocking capacitor forces the
    # inverting input's small-signal voltage independently of the DC servo.
    cases={}
    for mode,inverting_ac in (("both_inputs_driven",1),("inverting_ac_ground",0)):
        body=f"""* Extract input admittance at 1.5 V bias on both inputs, 3 V rail.
.lib MAX44280.sub
.options numdgt=8 plotwinsize=0
.temp 27
Vdd vdd 0 3
Vdrive plus 0 DC 1.5 AC 1
Vminus stimulus 0 DC 1.5 AC {inverting_ac}
Cforce stimulus minus 1
Lservo minus out 1G
XU plus minus vdd 0 out vdd MAX44280
.ac lin 2 7000 7001
.save I(Vdrive) V(minus)
.end
"""
        r=run(mode,body)
        y=-r.trace("I(Vdrive)")[0]
        cases[mode]=(y.imag/(2*np.pi*7000))*1e12
        assert abs(r.trace("V(minus)")[0]-inverting_ac)<1e-4
    cases["difference_pF"]=cases["inverting_ac_ground"]-cases["both_inputs_driven"]
    body="""* Isolated gain-11 equivalent input noise; noiseless feedback resistor pair.
.lib MAX44280.sub
.options numdgt=8 plotwinsize=0
.temp 27
Vrail vdd 0 3
Vmid mid 0 1.5
Vin plus 0 DC 1.5 AC 1
Rf out minus 10k noiseless
Rg minus mid 1k noiseless
XU plus minus vdd 0 out vdd MAX44280
.noise V(out) Vin dec 100 300 10000
.save V(inoise)
.end
"""
    r=run("model-noise",body)
    f=r.trace("frequency").real
    n=r.trace("V(inoise)").real
    return cases,{str(at):float(np.interp(at,f,n))*1e9 for at in (300,1000,2000,7000,10000)}


def main():
    isolated="""* Driven gain-11 MAX44280 input with ideal midrail, de-embedded from trace, ESD and bias.
.lib MAX44280.sub
.options numdgt=8 plotwinsize=0
.temp 27
Vdd vdd 0 3
Vmid mid 0 1.5
Vdrive inp 0 DC 1.5 AC 1
Rf out minus 10k
Rg minus mid 1k
Xu inp minus vdd 0 out vdd MAX44280
.ac dec 80 7 70Meg
.save V(out) I(Vdrive)
.end
"""
    bare=run("isolated",isolated)
    f=bare.trace("frequency").real
    k=np.argmin(abs(f-7000))
    y=-bare.trace("I(Vdrive)")[k]
    results={"model":"LTspice installed MAX44280.sub; gain 11, supply 3.0 V, enabled, 27 C",
             "isolated":{"gain_7k":abs(bare.trace("V(out)")[k]),
                         "Ceff_pF_7k":y.imag/(2*np.pi*f[k])*1e12,"G_nS_7k":y.real*1e9},
             "ac":{},"noise":{},"op":{}}
    assert 10<results["isolated"]["gain_7k"]<12
    for layout in (.75,1,2):
        results["ac"][str(layout)]=ac("ac-"+str(layout),full(layout))
    results["model_C_pF"],results["model_en_nV_rtHz"]=model_input_checks()
    for layout in (.75,1):
        # Explicit allowances, because neither Ccm nor the ESD capacitance has a
        # guaranteed manufacturer maximum at the actual zero-volt fixture bias.
        body=full(layout,extra_cin_pf=.2).replace("22000000","21780000")
        body=re.sub(r"(?m)^(c_esd_\w+ \S+ 0) 0.5p$",r"\g<1> 0.65p",body)
        results["ac"]["stressed_"+str(layout)]=ac("ac-stress-"+str(layout),body)
    # Place the four CH clamps at the input side of the physical grid resistors.
    # REF has no external jack; leave its protection on the existing node.
    body=full(2)
    body,n=re.subn(r"(?m)^(c_esd_ch([1-4])) ffc_ch[1-4]",r"\1 genout_ch\2",body)
    assert n==4
    results["ac"]["relocated_ESD_2pF"]=ac("ac-esd-before-source",body)
    for fixtures in (False,True):
        name="with-emulator" if fixtures else "electronics"
        results["noise"][name]=noise("noise-"+name,full(1,fixtures))
    for family in ("TI","MAX"):
        body=full(1,all_ti=(family=="TI"))
        data=run("op-"+family,body+".op\n.save V(ch1_pre) V(ref_pre) V(adc_in_1) V(vmid) I(Vdd)\n.end\n")
        results["op"][family]={n:float(data.trace(n)[0].real) for n in ("V(ch1_pre)","V(ref_pre)","V(adc_in_1)","V(vmid)","I(Vdd)")}
    ca={"bias_node":"VMID_RAW, filtered 10k/10k divider with 2.2 uF; other stage returns retain VMID.",
        "stressed_layout_pf":.75,"FE_bias_R_Mohm":21.78,"assumed_IC_C_extra_pF":.2,
        "assumed_ESD_C_pF":.65,"board_end_ESD":True,"all_excitation":{},"layout_sweep":{},"noise":{},"op":{}}
    for node in ("ch1","ch2","ch3","ch4","ref"):
        ca["all_excitation"][node]=ac("candidate-ac-"+node,candidate(.75,True,drive=node),node)
    for load in (.6,.75,1,2):
        for stress in (False,True):
            ca["layout_sweep"][f"{load}pF_stress_{stress}"]=ac("candidate-lay-"+str(load)+"-"+str(stress),
                                                             candidate(load,stress))
    for bool_noise in (False,True):
        lab="with-emulator" if bool_noise else "electronics"
        ca["noise"][lab]=noise("noise-candidate-"+lab,candidate(.75,True,bool_noise))
    # Native operating points after settling, with zero and opposite sign
    # connector-side electrode offsets. VMID_RAW has finite source resistance.
    for name,vals in {"zero":(0,0,0,0,0),"mixed-plus":(.1,-.1,.1,-.1,.1),
                      "mixed-minus":(-.1,.1,-.1,.1,-.1)}.items():
        body=candidate(.75,True)
        for node,value in zip(("ch1","ch2","ch3","ch4","ref"),vals):
            body,n=re.subn(rf"(?im)^V{node} src_{node} 0[^\n]*$",f"V{node} src_{node} 0 {value}",body)
            assert n==1
        ns=["V(vmid_raw)","V(vmid)","V(ref_pre)","I(Vdd)"]+[f"V(adc_in_{i})" for i in range(1,5)]+[f"V(ch{i}_pre)" for i in range(1,5)]
        data=run("op-candidate-"+name,body+".op\n.save "+" ".join(ns)+"\n.end\n")
        ca["op"][name]={n:float(data.trace(n)[0].real) for n in ns}
    results["low_C_candidate"]=ca
    (OUT/"results.json").write_text(json.dumps(results,indent=2)+"\n",encoding="utf8")
    print(json.dumps(results,indent=2))


if __name__=="__main__":
    main()

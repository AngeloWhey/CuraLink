"""Candidate AFE linear MNA: explicit bootstrapped differential input capacitance.

Not a manufacturer nonlinear model. No rail clipping, recovery, output impedance,
ADC charge injection, nonlinear leakage or bias-node source impedance. Results
are calculations, not measured performance. Uses the prior study's topology.
"""
from pathlib import Path
import sys, json
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'/'analysis'))
from afe_study import Circuit as OldCircuit
OUT=Path(__file__).resolve().parent
KB=1.380649e-23; TEMP=300.; A0=1e5
GAIN=11*(1.818e6/51.1e3)*1.15*2.24

class Circuit(OldCircuit):
    def __init__(self,seed=None,source=47e3,ffc=20e-12,trace=2e-12,asym=0.,fast_final=True):
        super().__init__(source=source,cap=0,seed=seed)
        self.fast_final=fast_final
        new=[]
        for typ,name,a,b,val,group in self.parts:
            if name in ('chcin','refcin'):continue
            if name.endswith('protect'):val*=5.1
            if name in ('rin','rref'):val*=51.1/53.6
            if name in ('rfd','rbald'):continue # explicitly model independently varying series pair below
            if name=='adciso':val=150.
            if name=='adcreservoir':val=470e-12
            new.append((typ,name,a,b,val,group))
        self.parts=new
        self.part('R','rfd_1','do','rfd_mid',909e3)
        self.part('R','rfd_2','rfd_mid','dm',909e3)
        self.part('R','rbald_1','dp','rbald_mid',909e3)
        self.part('R','rbald_2','rbald_mid','0',909e3)
        for prefix in ['ch','ref']:
            self.part('C',prefix+'cincommon',prefix+'p','0',5e-12,vary=False)
            self.part('C',prefix+'cincommonminus',prefix+'m','0',5e-12,vary=False)
            self.part('C',prefix+'cindiff',prefix+'p',prefix+'m',1.5e-12,vary=False)
            self.part('C',prefix+'esdtraceffc',prefix+'elec','0',.5e-12+trace+ffc+(asym if prefix=='ch' else 0),vary=False)

    def solve(self,freq,noise=False):
        freq=np.atleast_1d(freq).astype(float); n=len(self.nodes); size=n+2+len(self.amps)
        mat=np.zeros((len(freq),size,size),complex); cols=[]; labels=[('signal','signal'),('reference','reference')]
        def col():return np.zeros((len(freq),size),complex)
        def inject(v,a,b,i):
            if a!='0':v[:,self.nodes[a]]+=i
            if b!='0':v[:,self.nodes[b]]-=i
        for typ,name,a,b,val,group in self.parts:
            y=np.full(len(freq),1/val) if typ=='R' else 2j*np.pi*freq*val
            ai,bi=self.nodes.get(a),self.nodes.get(b)
            if ai is not None:mat[:,ai,ai]+=y
            if bi is not None:mat[:,bi,bi]+=y
            if ai is not None and bi is not None:mat[:,ai,bi]-=y;mat[:,bi,ai]-=y
        for j,src in enumerate(['src','refsrc']):
            row=n+j; idx=self.nodes[src];mat[:,row,idx]=1;mat[:,idx,row]=1
            v=col();v[:,row]=1;cols.append(v)
        avs=[]
        for j,(name,p,m,o) in enumerate(self.amps):
            gbw=5e6 if name=='lp2' and self.fast_final else 1e6
            av=A0/(1+1j*freq/(gbw/A0));avs.append(av);row=n+2+j
            mat[:,self.nodes[o],row]=1;mat[:,row,self.nodes[o]]=1
            mat[:,row,self.nodes[p]]-=av;mat[:,row,self.nodes[m]]+=av
        if noise:
            for typ,name,a,b,val,group in self.parts:
                if typ!='R':continue
                v=col();inject(v,a,b,np.sqrt(4*KB*TEMP/val));cols.append(v);labels.append((name,group))
            for j,(name,p,m,o) in enumerate(self.amps):
                # Typical density fits: TLV9004 30 nV @1k / 27 nV @10k;
                # TLV9054 20 nV @1k / 15 nV @10k; not guaranteed 3V values.
                white,knee=(15e-9,777.78) if name=='lp2' and self.fast_final else (26.65e-9,267.32)
                en=white*np.sqrt(1+knee/np.maximum(freq,.01))
                v=col();v[:,n+2+j]=avs[j]*en;cols.append(v);labels.append((name+'_en','electronics'))
                for node in [p,m]:
                    v=col();inject(v,node,'0',23e-15);cols.append(v);labels.append((name+'_'+node+'_in','electronics'))
        return np.linalg.solve(mat,np.stack(cols,axis=2)),labels

def main():
    f=np.unique(np.r_[np.geomspace(100,400e3,500),300,1000,7000,15000,23000,43000])
    c=Circuit();y,lab=c.solve(f,True);out=y[:,c.nodes['adc'],:];h=out[:,0]
    idx=lambda ff:int(np.argmin(abs(f-ff)))
    band=(f>=300)&(f<=7000);g1=abs(h[idx(1000)])
    noises={}
    for group in ['electronics','source']:
        ids=[i for i,(_,g) in enumerate(lab) if g==group]
        psd=np.sum(abs(out[:,ids])**2,axis=1)
        noises[group]=dict(output_div_nominal_uVrms=float(np.sqrt(np.trapezoid(psd[band],f[band]))/GAIN*1e6),
            output_div_1k_gain_uVrms=float(np.sqrt(np.trapezoid(psd[band],f[band]))/g1*1e6),
            frequency_referred_uVrms=float(np.sqrt(np.trapezoid(psd[band]/abs(h[band])**2,f[band]))*1e6))
    loading=[]
    for ffcp in [0,10,20,50,100]:
        for rs in [47e3,100e3]:
            cc=Circuit(source=rs,ffc=ffcp*1e-12);yy,_=cc.solve([300,1000,7000]);v=yy[:,cc.nodes['chelec'],0]
            z=v*rs/(1-v)
            vv=yy[:,cc.nodes['chp'],0]
            loading.append(dict(ffc_pF=ffcp,source_kohm=rs/1e3,
                freq_Hz=[300,1000,7000],input_impedance_Mohm=[float(x/1e6) for x in abs(z)],
                input_voltage_ratio=[float(x) for x in abs(vv)],input_phase_deg=[float(x) for x in np.angle(vv,deg=True)]))
    mc=[]
    for seed in range(300):
        cc=Circuit(seed=seed); yy,_=cc.solve([300,1000,7000]);a=yy[:,cc.nodes['adc'],0];b=yy[:,cc.nodes['adc'],1]
        cmrr=-20*np.log10(np.maximum(abs((a+b)/a),1e-15))
        mc.append(dict(gain=[float(x) for x in abs(a)],cmrr_dB=[float(x) for x in cmrr]))
    asym=[]
    for mismatch in [1,2,5,10]:
        cc=Circuit(asym=mismatch*1e-12);yy,_=cc.solve([300,1000,7000]);a=yy[:,cc.nodes['adc'],0];b=yy[:,cc.nodes['adc'],1]
        asym.append(dict(extra_ch_cap_pF=mismatch,cmrr_dB=[float(x) for x in -20*np.log10(abs((a+b)/a))]))
    allslow=Circuit(fast_final=False);ys,_=allslow.solve(f)
    result=dict(status='Calculated linear candidate, not vendor SPICE or measured',
        nominal_gain_VV=GAIN,gain_1kHz_VV=float(g1),hp_Hz=1/(2*np.pi*51.1e3*10e-9),
        lp_pole_Hz=1/(2*np.pi*22.6e3*1e-9),noise_300_to_7000_Hz=noises,
        gain_dB_vs_nominal={str(ff):float(20*np.log10(abs(h[idx(ff)])/GAIN)) for ff in [300,1000,7000,15000,23000,43000]},
        relative_filter_attenuation_vs1k_dB={str(ff):float(20*np.log10(abs(h[idx(ff)])/g1)) for ff in [15000,23000,43000]},
        slow_final_gain_1k_VV=float(abs(ys[idx(1000),allslow.nodes['adc'],0])),
        loading=loading,mc_assumptions='300 independent uniform tolerance samples; gain/diff resistors 0.1%, other R 1%, all filtering C 1%; no parasitic mismatch or amplifier mismatch',
        mc_gain_minmax={str(ff):[float(np.min([v['gain'][j] for v in mc])),float(np.max([v['gain'][j] for v in mc]))] for j,ff in enumerate([300,1000,7000])},
        mc_cmrr_minmedian={str(ff):[float(np.min([v['cmrr_dB'][j] for v in mc])),float(np.median([v['cmrr_dB'][j] for v in mc]))] for j,ff in enumerate([300,1000,7000])},
        parasitic_mismatch=asym,
        amplifier_Iq_typ_mA=28*.060+8*.330,
        amplifier_Iq_datasheet_max25_mA=28*.075+8*.450,
        amplifier_Iq_datasheet_max_temperature_mA=28*.085+8*.475,
        limitations=['VMID ideal/noiseless','Dominant-pole amplifiers, zero output impedance',
            'Density fits typical at manufacturer 5V test conditions','No rail clipping, nonlinear recovery, ADC SC model, bias-current statistics or PCB leakage',
            'ESD/FFC/trace capacitance assumptions, not measurements'])
    (OUT/'afe-calculations.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['loading','parasitic_mismatch','limitations']},indent=2))
    lines=['* Candidate small-signal relative to ideal VMID; not a vendor nonlinear model',
        'Vsig src 0 AC 1','Vref refsrc 0 AC 0']
    for typ,name,a,b,val,group in c.parts:lines.append(f'{typ}{name} {a} {b} {val:.12g}')
    for name,p,m,o in c.amps:lines.append(f'X{name} {p} {m} {o} OP_'+('FAST' if name=='lp2' else 'SLOW'))
    for mode,cap in [('SLOW',15.9154943092e-6),('FAST',3.18309886184e-6)]:
        lines += [f'.subckt OP_{mode} p m o','Eol internal 0 p m 100000','Rdom internal pole 1k',
            f'Cdom pole 0 {cap:.12g}','Ebuf o 0 pole 0 1',f'.ends OP_{mode}']
    lines+=['.ac dec 100 100 400k','.end']
    (OUT/'afe-channel-linear.cir').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':main()

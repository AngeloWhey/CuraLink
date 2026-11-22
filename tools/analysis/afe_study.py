"""CuraLink candidate AFE: reproducible linear circuit/noise and waveform study.

Not a manufacturer SPICE model. Small-signal op amps use A0=1e5 and a single
dominant pole at GBW/A0; output impedance, overload recovery and rail clipping
are NOT modeled. VMID is ideal. Every resistor is noisy at 300 K. Source
resistors are separated from electronics noise. See the generated report.
"""
from pathlib import Path
import json
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/calculations/afe-study'
OUT.mkdir(parents=True, exist_ok=True)
KB, TEMP, GBW, A0 = 1.380649e-23, 300., 10e6, 1e5
GAIN = 11 * (1.87e6 / 53.6e3) * 1.15 * 2.24

class Circuit:
    def __init__(self, corner=7000., source=47e3, cap=7e-12, seed=None):
        self.nodes, self.parts, self.amps = {}, [], []
        self.rng = np.random.default_rng(seed) if seed is not None else None
        for name in ('src', 'refsrc'):
            self.node(name)
        for prefix, src in [('ch', 'src'), ('ref', 'refsrc')]:
            self.part('R', prefix+'source', src, prefix+'elec', source, 'source')
            self.part('R', prefix+'protect', prefix+'elec', prefix+'cap', 1e3)
            self.part('C', prefix+'ac', prefix+'cap', prefix+'p', 10e-9)
            self.part('R', prefix+'bias', prefix+'p', '0', 22e6)
            self.part('C', prefix+'cin', prefix+'p', '0', cap, vary=False)
            self.part('R', prefix+'rg', prefix+'m', '0', 1e3)
            self.part('R', prefix+'rf', prefix+'o', prefix+'m', 10e3)
            self.amp(prefix, prefix+'p', prefix+'m', prefix+'o')
        # Matched AC-coupled difference amplifier; channel path is inverting.
        self.part('C', 'hpch', 'cho', 'hpc', 10e-9)
        self.part('R', 'rin', 'hpc', 'dm', 53.6e3)
        self.part('R', 'rfd', 'do', 'dm', 1.87e6)
        self.part('C', 'hpref', 'refo', 'hpr', 10e-9)
        self.part('R', 'rref', 'hpr', 'dp', 53.6e3)
        self.part('R', 'rbald', 'dp', '0', 1.87e6)
        self.amp('diff', 'dp', 'dm', 'do')
        prior = 'do'
        # Equal-R/equal-C Sallen-Key; C from intermediate node to OUTPUT.
        for j, rf in [(1, 1.5e3), (2, 12.4e3)]:
            p = 'lp'+str(j)
            resistance = 22.6e3 * 7000 / corner
            self.part('R', p+'r1', prior, p+'a', resistance)
            self.part('R', p+'r2', p+'a', p+'p', resistance)
            self.part('C', p+'c1', p+'a', p+'o', 1e-9)
            self.part('C', p+'c2', p+'p', '0', 1e-9)
            self.part('R', p+'rg', p+'m', '0', 10e3)
            self.part('R', p+'rf', p+'o', p+'m', rf)
            self.amp(p, p+'p', p+'m', p+'o')
            prior = p+'o'
        self.part('R', 'adciso', prior, 'adc', 100.)
        self.part('C', 'adcreservoir', 'adc', '0', 470e-12)

    def node(self, n):
        if n != '0' and n not in self.nodes:
            self.nodes[n] = len(self.nodes)
        return self.nodes.get(n)

    def part(self, typ, name, a, b, value, group='electronics', vary=True):
        self.node(a); self.node(b)
        if self.rng is not None and vary and group != 'source':
            # Independent UNIFORM bounds: gain/matching R 0.1%, other R 1%, C 1%.
            tol = 0.001 if typ == 'R' and any(k in name for k in ['rg','rf','rin','rref','rbald']) else 0.01
            value *= 1+self.rng.uniform(-tol, tol)
        self.parts.append((typ,name,a,b,value,group))

    def amp(self, name, p, m, o):
        for n in [p,m,o]: self.node(n)
        self.amps.append((name,p,m,o))

    def solve(self, freq, noise=False):
        freq = np.atleast_1d(freq).astype(float)
        n = len(self.nodes); size = n+2+len(self.amps)
        mat = np.zeros((len(freq),size,size),complex)
        sources = [('signal', 'signal'), ('reference', 'reference')]
        columns = []
        def col(): return np.zeros((len(freq),size),complex)
        def inject(v,a,b,current):
            if a != '0': v[:,self.nodes[a]] += current
            if b != '0': v[:,self.nodes[b]] -= current
        for typ,name,a,b,value,group in self.parts:
            y = np.full(len(freq),1/value) if typ=='R' else 2j*np.pi*freq*value
            ai,bi = self.nodes.get(a),self.nodes.get(b)
            if ai is not None: mat[:,ai,ai] += y
            if bi is not None: mat[:,bi,bi] += y
            if ai is not None and bi is not None:
                mat[:,ai,bi] -= y; mat[:,bi,ai] -= y
        for j,name in enumerate(['src','refsrc']):
            row = n+j; ni=self.nodes[name]
            mat[:,row,ni]=1; mat[:,ni,row]=1
            v=col();v[:,row]=1;columns.append(v)
        av = A0/(1+1j*freq/(GBW/A0))
        for j,(name,p,m,o) in enumerate(self.amps):
            row=n+2+j
            mat[:,self.nodes[o],row]=1;mat[:,row,self.nodes[o]]=1
            mat[:,row,self.nodes[p]]-=av;mat[:,row,self.nodes[m]]+=av
        if noise:
            for typ,name,a,b,value,group in self.parts:
                if typ!='R':continue
                v=col();inject(v,a,b,np.sqrt(4*KB*TEMP/value))
                columns.append(v);sources.append((name,group))
            for j,(name,p,m,o) in enumerate(self.amps):
                # Fit to typical 16 nV/sqrtHz @1k and ~10 nV/sqrtHz high-f.
                en=10e-9*np.sqrt(1+1560/np.maximum(freq,0.01))
                v=col();v[:,n+2+j]=av*en
                columns.append(v);sources.append((name+'_en','electronics'))
                for node in [p,m]:
                    v=col();inject(v,node,'0',23e-15)
                    columns.append(v);sources.append((name+'_'+node+'_in','electronics'))
        result=np.linalg.solve(mat,np.stack(columns,axis=2))
        return result,sources

def integrate_psd(freq, psd, low, high):
    use=(freq>=low)&(freq<=high)
    return float(np.sqrt(np.trapezoid(psd[use],freq[use])))

def main():
    c=Circuit(); f=np.unique(np.r_[np.geomspace(.05,2e6,2200),300.,7000.,1000.,32000.,57000.,71000.])
    y, labels=c.solve(f,True); out=y[:,c.nodes['adc'],:]; h=out[:,0]
    adc_sigma_in=.5*(3/4096)/GAIN
    psds={}
    for group in ['electronics','source']:
        ids=[i for i,(_,g) in enumerate(labels) if g==group]
        psds[group]=np.sum(abs(out[:,ids])**2,axis=1)/GAIN**2
    # Conventional band-limited output noise / nominal gain, AND frequency-referred.
    noise={g:integrate_psd(f,p,300,7000)*1e6 for g,p in psds.items()}
    noise_all={g:integrate_psd(f,p,.05,2e6)*1e6 for g,p in psds.items()}
    gain1k=float(abs(h[np.argmin(abs(f-1000))]))
    zin={}
    for cap in [4e-12,7e-12,15e-12,30e-12]:
        z=1e3+1/(2j*np.pi*7000*10e-9)+1/(1/22e6+2j*np.pi*7000*cap)
        zin[str(cap)]={'magnitude_Mohm':abs(z)/1e6,'loss_at_100kohm_percent':100*(1-abs(z/(z+100e3)))}
    # Independent tolerance samples; response, peak, and common-mode rejection.
    mf=np.geomspace(100,30000,100); mc=[]
    for seed in range(100):
        cc=Circuit(seed=seed); yy,_=cc.solve(mf); a=yy[:,cc.nodes['adc'],0];b=yy[:,cc.nodes['adc'],1]
        idx=np.argmin(abs(mf-1000)); mc.append([abs(a[idx]), -20*np.log10(abs((a[idx]+b[idx])/a[idx]))])
    # Synthetic spikes, not biological validation. Duration denotes six sigma.
    fs=256000.; t=np.arange(-.01,.02,1/fs); spectra=np.fft.rfftfreq(len(t),1/fs)
    fig,ax=plt.subplots(2,2,figsize=(12,8)); comparisons=[]
    for corner,color in [(5000,'#5b6bb2'),(7000,'#117b73'),(10000,'#c37a26')]:
        cc=Circuit(corner=corner); yf,_=cc.solve(f); hf=yf[:,cc.nodes['adc'],0]
        ax[0,0].semilogx(f,20*np.log10(np.maximum(abs(hf)/GAIN,1e-10)),label=f'{corner/1000:g} kHz',color=color)
        yt,_=cc.solve(spectra); ht=yt[:,cc.nodes['adc'],0]
        for duration in [.0005,.001,.002]:
            sigma=duration/6; x=-(t/sigma)*np.exp(-.5*(t/sigma)**2); x*=200e-6/np.ptp(x)
            filtered=np.fft.irfft(np.fft.rfft(x)*ht,n=len(t))/GAIN
            comparisons.append({'corner_Hz':corner,'duration_ms':duration*1000,'retained_pp_percent':100*np.ptp(filtered)/np.ptp(x)})
            if duration==.001:
                ax[0,1].plot(t*1000,-filtered*1e6,label=f'{corner/1000:g} kHz',color=color)
    ax[0,0].set(xlim=(30,200000),ylim=(-95,5),xlabel='Frequency (Hz)',ylabel='Gain / nominal gain (dB)',title='Finite-GBW linear circuit response')
    ax[0,0].legend(); ax[0,1].set(xlim=(-2,4),xlabel='Time (ms)',ylabel='Input-equivalent signal (uV)',title='200 uVpp synthetic biphasic spike, 1 ms')
    ax[0,1].legend()
    for g,p in psds.items():ax[1,0].loglog(f,np.sqrt(p)*1e9,label=g)
    ax[1,0].set(xlim=(100,100000),ylim=(.01,200),xlabel='Frequency (Hz)',ylabel='Output noise / nominal gain (nV/sqrtHz)',title='Source includes CH and shared REF, both 47 kohm')
    ax[1,0].legend();ax[1,1].scatter(np.array(mc)[:,0],np.array(mc)[:,1],s=12,color='#117b73')
    ax[1,1].set(xlabel='1 kHz channel gain (V/V)',ylabel='1 kHz CMRR (dB)',title='100 tolerance samples; no layout parasitic mismatch')
    for a in ax.flat:a.grid(True,alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'afe-response.png',dpi=160);plt.close(fig)
    # Conservative pointwise ADC-noise allocation, not inferred from ENOB conditions.
    report={'model':'linear MNA, finite dominant-pole op amps; no clipping/recovery or measured data',
        'nominal_gain_VV':GAIN,'gain_at_1kHz_VV':gain1k,'hp_Hz':1/(2*np.pi*53.6e3*10e-9),'lp_pole_Hz':1/(2*np.pi*22.6e3*1e-9),
        'noise_300_7000_uVrms_output_div_nominal_gain':noise,'noise_0p05_2MHz_uVrms_output_div_nominal_gain':noise_all,
        'ADC_allocation_uVrms_input':adc_sigma_in*1e6,
        'total_300_7000_with_ADC_allocation_uVrms':float(np.sqrt(sum(v*v for v in noise.values())+(adc_sigma_in*1e6)**2)),
        'input_impedance_at_7kHz':zin,'template_comparisons':comparisons,
        'mc_1kHz_gain_min_max': [float(np.min(np.array(mc)[:,0])),float(np.max(np.array(mc)[:,0]))],
        'mc_CMRR_dB_min_median':[float(np.min(np.array(mc)[:,1])),float(np.median(np.array(mc)[:,1]))],
        'attenuation_dB_vs_nominal':{str(ff):float(20*np.log10(abs(h[np.argmin(abs(f-ff))])/GAIN)) for ff in [1000,32000,57000,71000]}}
    # Sampling at 64k/channel: sum image-band noise folding into 300Hz..7kHz.
    fb=np.linspace(300,7000,350); alias_e=np.zeros_like(fb);alias_s=np.zeros_like(fb)
    for k in range(1,11):
        for freq in [k*64000-fb,k*64000+fb]:
            yy,ll=c.solve(freq,True);oo=yy[:,c.nodes['adc'],:]
            for group,arr in [('electronics',alias_e),('source',alias_s)]:
                ids=[i for i,(_,g) in enumerate(ll) if g==group]
                arr+=np.sum(abs(oo[:,ids])**2,axis=1)/GAIN**2
    report['aliased_noise_into_300_7000_uVrms_10_images']={g:float(np.sqrt(np.trapezoid(arr,fb))*1e6) for g,arr in [('electronics',alias_e),('source',alias_s)]}
    report['noise_300_7000_uVrms_output_div_1kHz_gain']={g:v*GAIN/gain1k for g,v in noise.items()}
    # Independent consistency check against ideal analytic cascade, at 1 kHz.
    s=2j*np.pi*1000; w=1/(22.6e3*1e-9)
    ideal=11*(1.87e6/53.6e3)*s/(s+1/(53.6e3*10e-9))
    for k in [1.15,2.24]: ideal*=k*w*w/(s*s+(3-k)*w*s+w*w)
    assert abs(gain1k/abs(ideal)-1)<.03, 'Circuit differs from analytic cascade by >3%'
    common=np.abs(out[:,0]+out[:,1])
    assert np.max(common)<1e-6, 'Nominal matching no longer rejects common mode'
    report['analytic_1kHz_gain_VV']=abs(ideal)
    # Repeatable illustrative detector trial: 100 separated, known synthetic spikes.
    # No LFP/artifacts, source drift, overload, tissue noise, or multi-unit overlap.
    rng=np.random.default_rng(20260921); fsd=64000; N=fsd*10
    tt=np.arange(N)/fsd; event_t=np.arange(.05,9.95,.1)+rng.uniform(-.01,.01,99)
    sos=np.vstack([signal.butter(1,297,fs=fsd,btype='highpass',output='sos'),signal.butter(4,7042,fs=fsd,output='sos')])
    base_noise=signal.sosfilt(sos,rng.normal(size=N))
    base_noise*=3.5e-6/np.std(base_noise[fsd:])
    detection=[]
    for duration in [.0005,.001,.002]:
        clean=np.zeros(N)
        for et in event_t:
            tau=(tt-et)/(duration/6);clean+=-tau*np.exp(-tau*tau/2)/(2*np.exp(-.5))
        clean=signal.sosfilt(sos,clean)
        for amp in [20,50,100,200,500]:
            trace=base_noise+clean*amp*1e-6
            threshold=5*3.5e-6; refractory=int(.0015*fsd); hits=[]; last=-refractory
            for i in np.flatnonzero(abs(trace)>threshold):
                if i-last>=refractory:
                    hits.append(i/fsd);last=i
            def score(hits):
                matched=set(); false=0
                for hit in hits:
                    j=int(np.argmin(abs(event_t-hit)))
                    if abs(event_t[j]-hit)<.003 and j not in matched:matched.add(j)
                    else:false+=1
                return len(matched),false
            naive_detected,naive_false=score(hits)
            # Revised state machine: 2 ms minimum lockout and 250 us continuously
            # below 2 sigma to rearm. Counter runs throughout lockout.
            hits=[];armed=True;last=-fsd;quiet=0
            for i,value in enumerate(abs(trace)):
                if armed:
                    if value>threshold:
                        hits.append(i/fsd);last=i;armed=False;quiet=0
                else:
                    quiet=quiet+1 if value<2*3.5e-6 else 0
                    if i-last>=int(.002*fsd) and quiet>=int(.00025*fsd):armed=True
            detected,false=score(hits)
            detection.append({'duration_ms':duration*1000,'amplitude_uVpp':amp,'injected':len(event_t),'detected':detected,'unmatched_or_duplicate':false,'naive_unmatched_or_duplicate':naive_false,'seconds':10})
    report['illustrative_detector_trials']=detection
    (OUT/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    # Portable nominal netlist for later ngspice/LTspice adaptation/verification.
    lines=['* CuraLink one channel + shared reference, all voltages relative to ideal VMID',
           '* Linear small-signal only. This exported netlist has NOT been run in SPICE.',
           'Vsig src 0 AC 1','Vref refsrc 0 AC 0']
    for typ,name,a,b,value,group in c.parts:lines.append(f'{typ}{name} {a} {b} {value:.12g}')
    for name,p,m,o in c.amps:lines.append(f'X{name} {p} {m} {o} OP_LINEAR')
    lines+=['.subckt OP_LINEAR p m o','Eol internal 0 p m 100000','Rdom internal pole 1k','Cdom pole 0 1.59154943092u','Ebuf o 0 pole 0 1','.ends OP_LINEAR',
            '* Output buffer preserves the Python model zero output impedance.',
            '* Replace OP_LINEAR with vendor macro-models before using this for release.','.ac dec 100 0.1 1Meg','.end']
    (ROOT/'hardware/design/afe-channel-linear.cir').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()

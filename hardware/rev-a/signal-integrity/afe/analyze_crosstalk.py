"""Validate actual LTspice files; calculate complex crosstalk and plot sensitivities."""
from pathlib import Path
import csv
import hashlib
import json
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter, FuncFormatter
from read_ltspice_raw import read_raw

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
FIG = OUT / 'figures'
FIG.mkdir(exist_ok=True)
REVIEW_RATIO = 0.001  # Parent-proposed review threshold, not an accepted requirement.

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(name):
    log = (OUT / (name+'.log')).read_text(errors='replace')
    if 'Total elapsed time:' not in log:
        raise ValueError(f'{name}: no completed log')
    if re.search(r'(?im)^.*(?:fatal error|time step too small|unknown subcircuit).*$', log):
        raise ValueError(f'{name}: failed simulation diagnostic')
    exitcode = int((OUT / (name+'.exitcode.txt')).read_text(encoding='utf-8-sig').strip())
    if exitcode:
        raise ValueError(f'{name}: exit {exitcode}')
    raw = read_raw(OUT / (name+'.raw'))
    return raw, log, {'case': name, 'exit_code': exitcode, 'points': len(raw.data),
        'plotname': raw.metadata['Plotname'], 'simulator_version_log': log.splitlines()[0],
        'completed_log': True, 'finite_results': True,
        'files': {s: {'path': (OUT/(name+s)).relative_to(ROOT).as_posix(),
                     'sha256': sha(OUT/(name+s))} for s in ['.cir', '.raw', '.log']}}

def at(f, values, target):
    # Interpolate real/imaginary to preserve complex subtraction/phase cancellation.
    return complex(np.interp(np.log(target), np.log(f), values.real),
                   np.interp(np.log(target), np.log(f), values.imag))

def magdb(value):
    return float(20*np.log10(max(abs(value), 1e-300)))

def main():
    op, _, op_record = load('valid-operating-point')
    amp_status = []
    for line in (OUT/'canonical-afe.lib').read_text().splitlines():
        if not line.startswith('XU'):
            continue
        ref, p, m, supply, ground, out, model = line.split()
        pv, mv, ov = [float(op.trace('V('+n+')')[0]) for n in [p,m,out]]
        valid = 0.05 < min(pv,mv,ov) <= max(pv,mv,ov) < 2.95 and abs(pv-mv)<0.001
        amp_status.append({'unit': ref, 'model': model, 'plus_V': pv,
                           'minus_V': mv, 'out_V': ov, 'valid': valid})
    if len(amp_status)!=36 or not all(x['valid'] for x in amp_status):
        raise ValueError('Full 36-amplifier OP failed criterion')

    baseline, _, base_record = load('ch1-only')
    freq = baseline.data[:,0].real
    if len(freq)!=138 or not np.isclose(freq[0],300) or not np.isclose(freq[-1],7000):
        raise ValueError('Wrong frequency span or incomplete baseline AC output')
    hself = baseline.trace('V(ADC_IN_1)')
    hv = baseline.trace('V(ADC_IN_2)')
    vmid = baseline.trace('V(VMID)')
    refpre = baseline.trace('V(REF_PRE)')
    base_rows = []
    for target in [300,1000,3000,7000]:
        a,b,v,r = [at(freq,x,target) for x in [hself,hv,vmid,refpre]]
        base_rows.append({'frequency_Hz': target, 'aggressor_ADC_V_per_V': abs(a),
            'victim_ADC_V_per_V': abs(b), 'VMID_V_per_V': abs(v), 'REF_PRE_V_per_V': abs(r),
            'victim_crosstalk_dB': magdb(b/a),
            'victim_source_equivalent_uVpp_for_200uVpp': abs(b/a)*200,
            'victim_source_equivalent_uVpp_for_1mVpp': abs(b/a)*1000,
            'victim_ADC_mVpp_for_200uVpp': abs(b)*0.2,
            'victim_ADC_mVpp_for_1mVpp': abs(b)})
    base_peak = int(np.argmax(abs(hv/hself)))
    other_delta = max(float(np.max(abs(baseline.trace('V(ADC_IN_'+str(i)+')')-hv))) for i in range(3,9))
    manifest = [op_record,base_record]
    sensitivities = {}
    all_csv = []
    for name, expected_caps in [('input-input',[0,.02,.05,.1,.2,.5,1]),
                                 ('output-input',[0,.01,.02,.05,.1,.2,.5,1])]:
        raw, log, record = load(name)
        x = raw.data[:,0].real
        cuts = np.r_[0,np.flatnonzero(np.diff(x)<0)+1,len(x)]
        if len(cuts)-1!=len(expected_caps):
            raise ValueError(name+': incomplete stepped sweep')
        manifest.append(record)
        rows=[]
        for cap,a,b in zip(expected_caps,cuts[:-1],cuts[1:]):
            f = x[a:b]
            if len(f)!=len(freq) or not np.allclose(f,freq):
                raise ValueError(name+': step frequency differs')
            vs = raw.trace('V(ADC_IN_1)')[a:b]
            vv = raw.trace('V(ADC_IN_2)')[a:b]
            vc3 = raw.trace('V(ADC_IN_3)')[a:b]
            delta = vv-hv  # Complex incremental perturbation; magnitudes are not subtracted.
            ratio=vv/vs
            equiv = abs(vv/hself)*1000
            increment_equiv = abs(delta/hself)*1000
            peak=int(np.argmax(equiv))
            item={'assumed_capacitance_pF':cap,
                'maximum_total_victim_equiv_uVpp_for_1mVpp':float(equiv.max()),
                'maximum_total_victim_equiv_uVpp_for_200uVpp':float(equiv.max()/5),
                'maximum_incremental_victim_equiv_uVpp_for_1mVpp':float(increment_equiv.max()),
                'maximum_incremental_victim_equiv_uVpp_for_200uVpp':float(increment_equiv.max()/5),
                'maximum_total_equiv_frequency_Hz':float(f[peak]),
                'worst_total_victim_output_ratio_dB':float(20*np.log10(max(abs(ratio)))),
                'maximum_aggressor_gain_relative_change_percent':float(max(abs(vs/hself-1))*100),
                'maximum_other_channel_equiv_uVpp_for_1mVpp':float(max(abs(vc3/hself))*1000),
                'passes_proposed_total_1uVpp_for_1mVpp':bool(max(abs(vv/hself))<=REVIEW_RATIO),
                'at':[]}
            for target in [300,1000,3000,7000]:
                ss,vv_at,dd = [at(f,v,target) for v in [vs,vv,delta]]
                self_nom=at(freq,hself,target)
                item['at'].append({'frequency_Hz':target,'total_victim_output_ratio_dB':magdb(vv_at/ss),
                    'total_victim_equiv_uVpp_for_1mVpp':abs(vv_at/self_nom)*1000,
                    'increment_victim_equiv_uVpp_for_1mVpp':abs(dd/self_nom)*1000,
                    'victim_ADC_mVpp_for_1mVpp':abs(vv_at)})
            rows.append(item)
            for i in range(len(f)):
                all_csv.append([name,cap,f[i],vs[i].real,vs[i].imag,vv[i].real,vv[i].imag,
                    float(20*np.log10(max(abs(ratio[i]),1e-300))),equiv[i],increment_equiv[i]])
        sensitivities[name]=rows

    result={'date':'2026-10-02','status':'Completed nominal actual LTspice sensitivity study; no PCB extraction',
        'simulator':'LTspice26.0.2 for Windows, file26.0.2.1 product26.0.1.1',
        'definition':'Victim source-input-equivalent = |V(ADC_IN_victim)/Hself_nominal|; Hself measured by isolated CH1 excitation in identical channel; crosstalk dB uses victim/aggressor ADC outputs',
        'amplitude_note':'AC1 is normalization only. Scaled sine amplitudes200uVpp and1mVpp apply in linear small-signal region, not claims for arbitrary spike spectral content.',
        'criterion':{'status':'Review-only parent-proposed criterion, not accepted project requirement',
                     'single_aggressor_Vpp':.001,'allowed_victim_source_equivalent_Vpp':1e-6,
                     'ratio_dB':-60,'simultaneous_aggressor_budget':'Open; coherent sum may exceed single-aggressor case'},
        'operating_point':{'passed_all36':True,'units':amp_status},
        'nominal':{'at':base_rows,'worst_ratio':float(abs(hv[base_peak]/hself[base_peak])),
            'worst_ratio_dB':magdb(hv[base_peak]/hself[base_peak]),
            'worst_frequency_Hz':float(freq[base_peak]),
            'max_equivalent_uVpp_for_1mVpp':float(max(abs(hv/hself))*1000),
            'max_equivalent_uVpp_for_200uVpp':float(max(abs(hv/hself))*200),
            'largest_victims_3_to_8_difference_V_per_V':other_delta,
            'passes_proposed_single_aggressor_criterion':bool(max(abs(hv/hself))<=REVIEW_RATIO)},
        'sensitivity':sensitivities, 'completed_cases':manifest,
        'provenance':'source-provenance.json and models/model-provenance.json',
        'assumptions':json.loads((OUT/'source-provenance.json').read_text())['fixture'],
        'limitations':json.loads((OUT/'source-provenance.json').read_text())['limits']}
    result['assumptions']['late_output_added_coupling_pF']=[0,.01,.02,.05,.1,.2,.5,1]
    (OUT/'results.json').write_text(json.dumps(result,indent=2))
    with (OUT/'frequency-sensitivity.csv').open('w',newline='') as fh:
        writer=csv.writer(fh)
        writer.writerow(['study','assumed_C_pF','frequency_Hz','aggressor_ADC_real_V_per_V',
            'aggressor_ADC_imag_V_per_V','victim_ADC_real_V_per_V','victim_ADC_imag_V_per_V',
            'total_crosstalk_dB','total_victim_equiv_uVpp_for_1mVpp','incremental_victim_equiv_uVpp_for_1mVpp'])
        writer.writerows(all_csv)

    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
    axes[0].semilogx(freq,20*np.log10(abs(hv/hself)),label='Quiet CH2–CH8 outputs')
    axes[0].axhline(-60,color='k',ls='--',label='Proposed review threshold')
    axes[0].set(xlabel='Frequency (Hz)',ylabel='Victim / aggressor ADC output (dB)',
                title='Nominal shared-circuit crosstalk',ylim=(-80,-40))
    for v,label in [(vmid,'VMID'),(refpre,'REF_PRE'),(hv,'ADC_IN_2')]:
        axes[1].semilogx(freq,abs(v),label=label)
    axes[1].set(xlabel='Frequency (Hz)',ylabel='AC node voltage / external CH1 source (V/V)',
                title='Shared-node disturbance from CH1')
    for ax in axes:
        ax.set_xticks([300,1000,3000,7000])
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x:g}'))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.grid(True,which='both',alpha=.3);ax.legend(fontsize=8)
    fig.savefig(FIG/'nominal-shared-crosstalk.png',dpi=180);plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    for ax,name,title in zip(axes,['input-input','output-input'],
                ['Assumed FFC_CH1 ↔ FFC_CH2 coupling','Assumed AFE_OUT_1 ↔ CH2_PLUS coupling']):
        for cap in [0,.01,.02,.1,1]:
            subset=[x for x in all_csv if x[0]==name and x[1]==cap]
            if subset:
                ax.semilogx([x[2]for x in subset],[x[8]for x in subset],label=f'{cap:g} pF')
        ax.set_yscale('log')
        ax.axhline(1,color='k',ls='--',label='Proposed total limit')
        ax.set(xlabel='Frequency (Hz)',ylabel='Victim equivalent (µVpp), 1 mVpp aggressor',title=title)
        ax.set_xticks([300,1000,3000,7000])
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x:g}'))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.grid(True,which='both',alpha=.3);ax.legend(fontsize=8)
    fig.suptitle('Sensitivity assumptions only — no extracted PCB/package/FFC capacitance',fontsize=11)
    fig.savefig(FIG/'assumed-capacitance-sensitivity.png',dpi=180);plt.close(fig)
    print(json.dumps({'nominal':result['nominal'],
        'summary':{k:[{key:val for key,val in x.items()if key!='at'}for x in v]for k,v in sensitivities.items()}},indent=2))

if __name__=='__main__':main()

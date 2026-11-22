"""Validate full operating points and quantify single-aggressor bias crosstalk."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from read_ltspice_raw import read_raw

OUT=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(name):
    log=(OUT/(name+'.log')).read_text(errors='replace')
    code=int((OUT/(name+'.exitcode.txt')).read_text(encoding='utf-8-sig').strip())
    if code or 'Total elapsed time:'not in log or re.search(r'(?im)^.*(?:fatal error|time step too small|unknown subcircuit).*$',log):
        raise ValueError(name+' incomplete or failed actual run')
    raw=read_raw(OUT/(name+'.raw'))
    if not np.isfinite(raw.data).all():raise ValueError(name+' has nonfinite outputs')
    return raw,{'name':name,'exit_code':code,'plotname':raw.metadata['Plotname'],
        'points':len(raw.data),'completed_log':True,'finite_results':True,
        'simulator':log.splitlines()[0],
        'source_hashes':{s:sha(OUT/(name+s))for s in ['.cir','.raw','.log']}}
def interp(f,x,target):
    return np.interp(np.log(target),np.log(f),x.real)+1j*np.interp(np.log(target),np.log(f),x.imag)
def db(x):return float(20*np.log10(max(abs(x),1e-300)))

results={}
fig,axes=plt.subplots(2,1,figsize=(8.3,6.5),sharex=True,constrained_layout=True)
for case,label in [('shared47','Original shared 47 Ω'),('shared4R7','Shared 4.7 Ω candidate'),
                   ('split47','Three 47 Ω bias domains candidate'),
                   ('split4R7','Quiet 47 Ω; LP1/LP2 4.7 Ω candidate')]:
    op,op_record=load(case+'-op')
    units=[]
    for line in (OUT/(case+'.lib')).read_text().splitlines():
        if not line.startswith('XU'):continue
        ref,p,m,supply,ground,out,model=line.split()
        pv,mv,ov=[float(op.trace('V('+n+')')[0])for n in [p,m,out]]
        passed=.05<min(pv,mv,ov)<=max(pv,mv,ov)<2.95 and abs(pv-mv)<.001
        units.append({'unit':ref,'plus_V':pv,'minus_V':mv,'out_V':ov,'valid':passed})
    if len(units)!=36 or not all(x['valid']for x in units):raise ValueError(case+' full36 OP invalid')
    ac,ac_record=load(case+'-ac')
    f=ac.data[:,0].real
    if len(f)!=138 or not np.isclose(f[0],300)or not np.isclose(f[-1],7000):raise ValueError(case+' AC span incomplete')
    aggressor=ac.trace('V(ADC_IN_1)')
    victim=ac.trace('V(ADC_IN_2)')
    quiet=ac.trace('V(VMID)')
    ratio=victim/aggressor
    k=int(np.argmax(abs(ratio)))
    rows=[]
    for target in [300,1000,3000,7000]:
        a,v,q=[interp(f,x,target)for x in [aggressor,victim,quiet]]
        row={'frequency_Hz':target,'aggressor_V_per_V':abs(a),'victim_V_per_V':abs(v),
            'quiet_VMID_V_per_V':abs(q),'ratio_dB':db(v/a),
            'victim_input_equivalent_uVpp_for_1mVpp':float(abs(v/a)*1000),
            'victim_input_equivalent_uVpp_for_200uVpp':float(abs(v/a)*200)}
        if case.startswith('split'):
            row.update({n+'_V_per_V':float(abs(interp(f,ac.trace('V('+n+')'),target)))for n in ['VMID_LP1','VMID_LP2']})
        rows.append(row)
    results[case]={'description':label,'op':op_record,'op_units':units,
        'op_supply_current_mA':float(-op.trace('I(VDD)')[0]*1000),'ac':ac_record,
        'table':rows,'worst_case':{'frequency_Hz':float(f[k]),'ratio_dB':db(ratio[k]),
            'victim_input_equivalent_uVpp_for_1mVpp':float(abs(ratio[k])*1000),
            'victim_input_equivalent_uVpp_for_200uVpp':float(abs(ratio[k])*200),
            'passes_proposed_single_aggressor_minus60dB_review':bool(abs(ratio[k])<=.001)},
        'other_victim_symmetry_max_V_per_V_delta':max(float(np.max(abs(ac.trace('V(ADC_IN_'+str(i)+')')-victim)))for i in range(3,9))}
    axes[0].semilogx(f,20*np.log10(abs(ratio)),label=label)
    axes[1].semilogx(f,abs(quiet),label=label)
axes[0].axhline(-60,color='k',linestyle='--',linewidth=.9,label='Proposed single-aggressor review level')
axes[0].set_ylabel('Victim / aggressor ADC magnitude (dB)')
axes[1].set_ylabel('Quiet VMID transfer (V/V)')
axes[1].set_xlabel('Frequency (Hz)')
for ax in axes:ax.grid(True,which='both',alpha=.25);ax.set_xlim(300,7000)
axes[0].legend(fontsize=8)
fig.savefig(OUT/'bias-ac-comparison.png',dpi=170)
payload={'status':'Nominal actual LTspice comparison; isolated candidates, no canonical change',
    'review_level':'Parent-proposed <=1uVpp input-equivalent victim for 1mVpp aggressor; not an accepted system requirement',
    'cases':results,'limits':['AC + verified OP only at this stage; no stability, startup, offset, PVT or package-coupling guarantee']}
(OUT/'ac-results.json').write_text(json.dumps(payload,indent=2))
print(json.dumps({name:{'OP36_valid':all(x['valid']for x in r['op_units']),
    'op_supply_mA':r['op_supply_current_mA'],'worst':r['worst_case']}for name,r in results.items()},indent=2))

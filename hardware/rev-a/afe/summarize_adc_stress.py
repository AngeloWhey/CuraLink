from pathlib import Path
import json,numpy as np
OUT=Path(__file__).resolve().parent;D=OUT/'adc-stress'
results=[]
for c in json.loads((D/'cases.json').read_text()):
    data=np.loadtxt(D/(c['name']+'.csv'),skiprows=1)
    if c['type']=='step':
        t,out,adc,held=data.T;baseline=float(np.median(adc[t<.8e-6]))
        c['baseline_V']=baseline
        c['residual_1p656_us_uV']=float((np.interp(2.656e-6,t,held)-baseline)*1e6)
        w=(t>=2.5e-6)&(t<=2.8e-6)
        c['worst_1p5_to_1p8_us_uV']=float(np.max(abs(held[w]-baseline))*1e6)
    else:
        t,out,adc,held,outq,adcq,heldq=data.T
        sampled=[];raw=[]
        for k in range(3,12):
            end=(1.1+1.656+k*33.333333)*1e-6
            sampled.append(float((np.interp(end,t,held)-np.interp(end,t,heldq))*1e6))
            raw.append(float((np.interp(end,t,held)-np.interp(end,t,adcq))*1e6))
        c['worst_settling_increment_uV']=max(map(abs,sampled))
        c['worst_instantaneous_error_including_track_delay_uV']=max(map(abs,raw))
    results.append(c)
(D/'results.json').write_text(json.dumps(results,indent=2)+'\n')
for cnom in [470,1000]:
    s=[r for r in results if r['type']=='step' and r['Cnom_pF']==cnom]
    print('Cnom',cnom,'worst1.656us',max(abs(r['residual_1p656_us_uV']) for r in s),'worsttimewindow',max(r['worst_1p5_to_1p8_us_uV'] for r in s))
print(json.dumps([r for r in results if r['type']=='track'],indent=2))

from pathlib import Path
import numpy as np,json,re
OUT=Path(__file__).resolve().parent
SWEEP=OUT/'adc-sweep'
cases=[]
for name in json.loads((SWEEP/'cases.json').read_text()):
    d=np.loadtxt(SWEEP/(name+'.csv'),skiprows=1)
    t,out,adc,held=d.T
    baseline=float(np.median(adc[t<.8e-6]))
    r,c,cap=map(int,re.match(r'r(\d+)_c(\d+)_adc(\d+)p',name).groups())
    cases.append(dict(R_ohm=r,C_pF=c,ADC_pF=cap,baseline_V=baseline,
        residual_uV={str(acq):float((np.interp((1+acq)*1e-6,t,held)-baseline)*1e6) for acq in [1.2,1.656,2.47]},
        LSB={str(acq):float((np.interp((1+acq)*1e-6,t,held)-baseline)/(3/4096)) for acq in [1.2,1.656,2.47]}))
(SWEEP/'results.json').write_text(json.dumps(cases,indent=2)+'\n')
print(json.dumps(sorted(cases,key=lambda v:abs(v['LSB']['1.656'])),indent=2))

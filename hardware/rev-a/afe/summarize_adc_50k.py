from pathlib import Path
import json,numpy as np
OUT=Path(__file__).resolve().parent;D=OUT/'adc-stress-50k'
cases=json.loads((D/'cases.json').read_text())
for c in cases:
    data=np.loadtxt(D/(c['name']+'.csv'),skiprows=1)
    t,out,adc,held,outq,adcq,heldq=data.T
    if not np.all(np.isfinite(data)):raise ValueError(c['name']+' contains non-finite values')
    if not (1.4 < out[0] < 1.6):raise ValueError(c['name']+' invalid DC operating point')
    incremental=[];raw=[];sampled=[]
    for k in range(15,100):
        end=(1.1+1.656+k*20)*1e-6
        incremental.append(float((np.interp(end,t,held)-np.interp(end,t,heldq))*1e6))
        raw.append(float((np.interp(end,t,held)-np.interp(end,t,adcq))*1e6))
        sampled.append(float(np.interp(end,t,held)))
    c.update(samples_after_settling=len(incremental),
        worst_settling_increment_uV=max(map(abs,incremental)),
        worst_instantaneous_error_including_track_delay_uV=max(map(abs,raw)),
        worst_settling_increment_12bit_LSB=max(map(abs,incremental))/(3e6/4096),
        worst_instantaneous_error_including_track_delay_12bit_LSB=max(map(abs,raw))/(3e6/4096),
        min_sample_V=min(sampled),max_sample_V=max(sampled))
result=dict(status='Simulated typical adapted TLV9052-family final-stage model; not hardware or complete AFE validation',
    assumptions='150 ohm / 470 pF, 1.656 us tracking, 1 kohm SAR switch, 5/10 pF sampling capacitor; previous-channel hold recharged to 2.8 V every 20 us; filter-input sine 0.15 V peak around 1.5 V; noiseless ideal 3 V supply; no real SAR conversion kickback, amplifier process corners or package coupling',
    interpretation='Incremental error compares sampled channel with duplicate continuously tracked quiet reference. Instantaneous error additionally includes normal switch-capacitor track delay.',
    cases=cases)
(D/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

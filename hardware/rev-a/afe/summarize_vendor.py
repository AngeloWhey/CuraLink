from pathlib import Path
import numpy as np,json
OUT=Path(__file__).resolve().parent
result={'status':'Partial vendor-model checks only; full TLV9002-family ngspice operating point invalid pending compatibility repair','adapter':'Helper names prefixed; resistor syntax reordered; noiseless R at 0.01 K; diode noise helper ports disabled. Original PSpice libraries preserved. No vendor-model noise result.'}
for cap in [5,10]:
    d=np.loadtxt(OUT/f'vendor-adc-{cap}p.csv',skiprows=1)
    t,out,adc,held=d.T
    baseline=float(np.median(adc[t<.8e-6]))
    end=2.2e-6
    value=float(np.interp(end,t,held))
    after=(t>=1e-6)&(t<=end)
    result[f'ADC_{cap}pF']=dict(baseline_V=baseline,sample_end_V=value,
        residual_uV=(value-baseline)*1e6,residual_12bit_LSB=(value-baseline)/(3/4096),
        worst_pin_kick_mV=float(np.max(abs(adc[after]-baseline))*1e3),
        output_pin_kick_mV=float(np.max(abs(out[after]-baseline))*1e3),
        assumption='Adjacent hold 2.8 V; final SK output ≈0.2 V; 1 kΩ sample switch; 47 Ω/1 nF reservoir; 1.2 µs track')
(OUT/'vendor-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

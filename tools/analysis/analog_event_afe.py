"""2026-09-22 candidate linear AFE, with no waveform ADC.

Reuses the documented finite-GBW MNA model; adds a passive output DC reset.
No clipping, comparator dynamics, PCB/cable coupling, or VMID noise model.
This is a calculation, not a hardware or vendor-SPICE validation.
"""
from pathlib import Path
import json
import numpy as np
from afe_study import Circuit, integrate_psd, KB, TEMP

OUT = Path(__file__).resolve().parents[2] / 'docs/calculations/analog-event-afe'


def circuit(rf=1.87e6, corner=7000):
    c = Circuit(corner=corner)
    # Remove the former ADC load and its now-unused node before solving.
    c.parts = [p for p in c.parts if p[1] not in ('adciso', 'adcreservoir')]
    del c.nodes['adc']
    c.parts = [(t, n, a, b, rf if n in ('rfd', 'rbald') else v, g)
               for t, n, a, b, v, g in c.parts]
    # EGRA-inspired connector-side ESD candidate, adapted to the spike band.
    # The 0.5 pF value is typical, not a worst-case cable/input capacitance.
    c.parts = [(t, n, a, b, 5.1e3 if n in ('chprotect', 'refprotect') else v, g)
               for t, n, a, b, v, g in c.parts]
    c.part('C', 'chesd', 'chelec', '0', .5e-12)
    c.part('C', 'refesd', 'refelec', '0', .5e-12)
    c.part('R', 'outiso', 'lp2o', 'couple', 100.)
    c.part('C', 'outdc', 'couple', 'det', 100e-9)
    c.part('R', 'detbias', 'det', '0', 100e3)
    c.part('C', 'detcap', 'det', '0', 10e-12)  # assumed total comparator/trace load
    return c


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f = np.unique(np.r_[np.geomspace(.05, 2e6, 1800), 3., 300., 1000., 7000., 10000.])
    results = {'date': '2026-09-22', 'evidence': 'linear calculations, not measured',
               'models': [], 'template_trials': []}
    for rf in (936e3, 1.87e6):
        c = circuit(rf)
        y, labels = c.solve(f, True)
        out = y[:, c.nodes['det'], :]
        gain = float(abs(out[np.where(f == 1000)[0][0], 0]))
        row = {'feedback_ohm': rf, 'gain_1kHz_VV': gain,
               'gain_nominal_VV': 11 * rf / 53600 * 1.15 * 2.24}
        for lo, hi in ((300, 7000), (3, 10000), (.05, 2e6)):
            values = {}
            for group in ('electronics', 'source'):
                ids = [i for i, (_, g) in enumerate(labels) if g == group]
                psd = np.sum(abs(out[:, ids])**2, axis=1) / gain**2
                values[group] = integrate_psd(f, psd, lo, hi) * 1e6
            values['quadrature_total'] = float(np.hypot(*values.values()))
            row[f'noise_{lo}_{hi}_uVrms_output_div_1kHz_gain'] = values
        row['response_dB_relative_1kHz'] = {str(hz): float(20*np.log10(
            abs(out[np.where(f == hz)[0][0], 0])/gain)) for hz in (3., 300., 7000., 10000.)}
        results['models'].append(row)
    # Noise-free derivative-Gaussian examples; duration defined as six sigma.
    fs = 256000
    t = np.arange(-.03, .05, 1/fs)
    frequencies = np.fft.rfftfreq(len(t), 1/fs)
    for corner in (5000, 7000, 10000):
        c = circuit(corner=corner)
        y, _ = c.solve(frequencies)
        h = y[:, c.nodes['det'], 0]
        for width in (.0005, .001, .002):
            sigma = width/6
            wave = -(t/sigma)*np.exp(-.5*(t/sigma)**2)
            wave *= 200e-6 / np.ptp(wave)
            vout = np.fft.irfft(np.fft.rfft(wave)*h, n=len(t))
            results['template_trials'].append({'corner_Hz': corner, 'width_ms': width*1000,
                'input_uVpp': 200, 'output_mVpp': float(np.ptp(vout)*1000),
                'min_output_mV_relative_bias': float(vout.min()*1000),
                'max_output_mV_relative_bias': float(vout.max()*1000)})
    ratio = 49.9/(49900+49.9)
    results['fixture'] = {'unloaded_attenuation': ratio,
        'DAC_2p5V_16bit_step_after_attenuator_uV': 2.5/65536*ratio*1e6,
        'DAC_Vpp_for_200uVpp': 200e-6/ratio,
        'source_R_noise_single_47k_300_7000_uVrms': float(np.sqrt(4*KB*TEMP*47000*6700)*1e6)}
    results['input_C_budget_pF_for_10Mohm_7kHz_with_22Mohm_bias'] = float(
        np.sqrt((1/10e6)**2-(1/22e6)**2)/(2*np.pi*7000)*1e12)
    (OUT/'results.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()

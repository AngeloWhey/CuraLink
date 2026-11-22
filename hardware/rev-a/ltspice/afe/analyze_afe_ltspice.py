"""Validate and summarize the completed actual LTspice AFE runs."""
import csv
import hashlib
import json
from pathlib import Path
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from read_ltspice_raw import read_raw

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
FIG = OUT / 'figures'
FIG.mkdir(exist_ok=True)
LSB = 3 / 4096

def load(name):
    log = (OUT / (name + '.log')).read_text(errors='replace')
    if 'Total elapsed time:' not in log:
        raise ValueError(f'{name}: LTspice log has no completion record')
    if re.search(r'(?im)^.*(?:fatal error|time step too small|unknown subcircuit).*$', log):
        raise ValueError(f'{name}: simulator failure diagnostic')
    raw = read_raw(OUT / (name + '.raw'))
    return raw

def at(f, values, target):
    """Log-frequency interpolation of magnitude and unwrapped phase."""
    mag = np.exp(np.interp(np.log(target), np.log(f), np.log(np.maximum(abs(values), 1e-300))))
    phase = np.interp(np.log(target), np.log(f), np.unwrap(np.angle(values)))
    return complex(mag * np.cos(phase), mag * np.sin(phase))

def settle(t, y, baseline, tolerance, after=0):
    bad = np.flatnonzero((t >= after) & (abs(y-baseline) > tolerance))
    if not len(bad):
        return float(after)
    last = bad[-1]
    return None if last == len(t)-1 else float(t[last+1])

def manifest(names):
    records = []
    for name in names:
        raw = load(name)
        log = (OUT / (name+'.log')).read_text(errors='replace')
        exitfile = OUT / (name+'.exitcode.txt')
        records.append({'name': name, 'status': 'COMPLETED_FINITE_RESULT_WITH_LOG',
            'plotname': raw.metadata['Plotname'], 'points': len(raw.data),
            'simulator_version_log': log.splitlines()[0],
            'simulator_exit_code': int(exitfile.read_text(encoding='utf-8-sig').strip()) if exitfile.exists() else None,
            'exit_code_note': 'Captured when present; other runs are qualified from completed logs and independently inspected finite raw results',
            'files': {suffix: {'path': (OUT / (name+suffix)).relative_to(ROOT).as_posix(),
                'sha256': hashlib.sha256((OUT / (name+suffix)).read_bytes()).hexdigest()}
                for suffix in ['.cir', '.log', '.raw']}})
    return records

def main():
    op = load('afe-full-op')
    components = json.loads((ROOT / 'hardware/rev-a/afe/afe-pin-nets.json').read_text())['components']
    amps = []
    for c in components:
        if c.get('mpn') not in ['TLV9004IRUCR', 'TLV9054IRUCR']:
            continue
        for u in c['unit_blocks']:
            if u['unit'] == 5:
                continue
            o, m, p = [float(op.trace('V('+c['pins'][pin]+')')[0]) for pin in u['pins']]
            amps.append({'ref': c['ref'], 'unit': u['unit'], 'output_V': o,
                'inverting_V': m, 'noninverting_V': p, 'input_difference_V': p-m,
                'op_valid': 0.05 < min(o,m,p) < max(o,m,p) < 2.95 and abs(p-m) < 0.001})
    op_values = {name: float(op.trace(name)[0]) for name in ['V(AVDD_3V0)', 'V(VMID_RAW)',
        'V(VMID_BUF)', 'V(VMID)', 'V(CH1_PRE)', 'V(REF_PRE)', 'V(CH1_HP)', 'V(CH1_LP1_OUT)',
        'V(AFE_OUT_1)', 'V(ADC_IN_1)', 'I(VDD)']}
    baseline = op_values['V(ADC_IN_1)']
    dc = {}
    for name, key in [('afe-dc-differential-offset', 'differential'), ('afe-dc-common-offset', 'common')]:
        raw = load(name)
        source, y = raw.data[:,0], raw.trace('V(ADC_IN_1)')
        dc[key] = {'input_min_V': float(source.min()), 'input_max_V': float(source.max()),
            'adc_mean_V': float(y.mean()), 'adc_span_V': float(np.ptp(y)),
            'preamp_min_V': float(raw.trace('V(CH1_PRE)').min()), 'preamp_max_V': float(raw.trace('V(CH1_PRE)').max()),
            'criterion': 'Completed sweep, preamp/ADC not saturated, ADC variation <0.25 ideal LSB',
            'passed': bool(np.ptp(y) < LSB/4 and raw.trace('V(CH1_PRE)').min() > 0.05 and raw.trace('V(CH1_PRE)').max() < 2.95)}
    leakraw = load('afe-dc-capacitor-leakage-qualified')
    x = leakraw.data[:,0]
    cuts = np.r_[0, np.flatnonzero(np.diff(x)<0)+1, len(x)]
    leakage = []
    for resistance, a, b in zip([1e11, 1e10], cuts[:-1], cuts[1:]):
        y, pre = leakraw.trace('V(ADC_IN_1)')[a:b], leakraw.trace('V(CH1_PRE)')[a:b]
        leakage.append({'parallel_resistance_per_10nF_ohm': resistance, 'temperature_C': 25,
            'input_offset_span_V': float(np.ptp(x[a:b])), 'adc_mean_V': float(y.mean()),
            'adc_span_uV': float(np.ptp(y)*1e6), 'adc_span_ideal_LSB': float(np.ptp(y)/LSB),
            'preamp_min_V': float(pre.min()), 'preamp_max_V': float(pre.max()),
            'passed_quarter_LSB_offset_variation': bool(np.ptp(y)<LSB/4 and pre.min()>0.05 and pre.max()<2.95)})
    ar = load('afe-ac-differential')
    cr = load('afe-ac-common')
    f, h, cm = ar.data[:,0].real, ar.trace('V(ADC_IN_1)'), cr.trace('V(ADC_IN_1)')
    g1 = abs(at(f,h,1000))
    peakidx = int(np.argmax(abs(h)))
    targets = [.01, .1, 1, 10, 50, 60, 300, 1000, 7000, 15000, 23000, 43000, 1e5, 1e6, 1e7]
    acpoints = []
    for freq in targets:
        hs, hc = at(f,h,freq), at(f,cm,freq)
        acpoints.append({'frequency_Hz': freq, 'gain_VV': abs(hs), 'phase_deg': float(np.angle(hs,deg=True)),
            'gain_dB_vs1k': float(20*np.log10(abs(hs)/g1)), 'common_gain_VV': abs(hc),
            'nominal_CM_rejection_dB': float(20*np.log10(abs(hs/hc)))})
    peak3 = abs(h) >= abs(h[peakidx])/np.sqrt(2)
    with (OUT/'frequency-response.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['frequency_Hz','differential_gain_real','differential_gain_imag', 'differential_gain_VV',
            'differential_gain_dB','phase_deg','common_gain_real','common_gain_imag','common_gain_VV','nominal_CM_rejection_dB'])
        writer.writerows(zip(f,h.real,h.imag,abs(h),20*np.log10(abs(h)),np.unwrap(np.angle(h))*180/np.pi,
            cm.real,cm.imag,abs(cm),20*np.log10(abs(h/cm))))
    tr = load('afe-offset-recovery-long')
    t, y = tr.data[:,0], tr.trace('V(ADC_IN_1)')
    last_event = 1.800001
    recovery = {'source_case': 'CH1: 0,+100mV,0,-100mV,0; 1us edges at 10ms/600ms/1.2s/1.8s; others 0V; final quiet interval 2.2s',
        'adc_min_V': float(y.min()), 'adc_max_V': float(y.max()),
        'outside_0p2_to_2p8_V': bool(y.min()<.2 or y.max()>2.8),
        'all_samples_within_0_to_3V': bool(y.min()>=0 and y.max()<=3),
        'shared_vmid_min_V': float(tr.trace('V(VMID)').min()), 'shared_vmid_max_V': float(tr.trace('V(VMID)').max()),
        'unexcited_channel2_min_V': float(tr.trace('V(AFE_OUT_2)').min()),
        'unexcited_channel2_max_V': float(tr.trace('V(AFE_OUT_2)').max()),
        'settling_after_last_event_to_1mV_s': settle(t,y,baseline,.001,last_event)-last_event,
        'settling_after_last_event_to_quarter_LSB_s': settle(t,y,baseline,LSB/4,last_event)-last_event,
        'residual_at_0p6s_after_last_event_mV': float((np.interp(last_event+.6,t,y)-baseline)*1e3),
        'residual_at_2s_after_last_event_uV': float((np.interp(last_event+2,t,y)-baseline)*1e6),
        'residual_at_end_uV': float((y[-1]-baseline)*1e6),
        'provisional_2s_quarter_LSB_recovery_passed_this_nominal_case': bool(abs(np.interp(last_event+2,t,y)-baseline)<LSB/4)}
    sr = load('afe-startup')
    st, sy = sr.data[:,0], sr.trace('V(ADC_IN_1)')
    startup = {'source_case': 'Grounded external CH/REF, 0-to-3V AFE supply ramp in1ms, LTspice startup initializes sources at0',
        'dc_equilibrium_reference_V': baseline,
        'adc_residual_at_2s_uV': float((np.interp(2,st,sy)-baseline)*1e6),
        'adc_residual_at_2p4s_uV': float((sy[-1]-baseline)*1e6),
        'settling_to_1mV_s': settle(st,sy,baseline,.001),
        'settling_to_quarter_LSB_s': settle(st,sy,baseline,LSB/4),
        'provisional_2s_quarter_LSB_startup_passed_this_nominal_case': bool(abs(np.interp(2,st,sy)-baseline)<LSB/4),
        'preamp_last_time_below_0p2V_s': float(st[np.flatnonzero(sr.trace('V(CH1_PRE)')<.2)[-1]]),
        'VMID_at_0p3s_V': float(np.interp(.3,st,sr.trace('V(VMID)'))),
        'limits': 'Family-model behavior below1.8V is not guaranteed; no regulator/interlock/MCU sequencing, process corners, or measured startup included'}
    names = ['import-tlv9002-op', 'import-tlv9052-op', 'afe-full-op', 'afe-dc-differential-offset',
        'afe-dc-common-offset', 'afe-ac-differential', 'afe-ac-common', 'afe-offset-recovery',
        'afe-offset-recovery-long', 'afe-startup', 'afe-dc-capacitor-leakage-qualified']
    result = {'date': '2026-10-02', 'timezone': 'America/New_York',
        'status': 'ACTUAL LTSPICE NOMINAL FAMILY-MODEL ANALYSIS; NOT HARDWARE QUALIFICATION',
        'simulator': {'executable': r'C:\Users\angel\AppData\Local\Programs\ADI\LTspice\LTspice.exe',
            'log_version': '26.0.2 for Windows', 'file_version': '26.0.2.1', 'product_version': '26.0.1.1',
            'command': 'Start-Process -WindowStyle Hidden -Wait with -b -ascii'},
        'model_provenance_file': 'models/model-provenance.json', 'canonical_extraction_file': 'canonical-extraction.json',
        'assumptions': ['Original TI TLV9002 and TLV9052 single-amplifier family macro-models represent each TLV9004/TLV9054 unit',
            'Only identifiers are prefixed; no disabled noise helpers, temperature, resistor ordering or equation edits',
            'Exact nominal physical net topology for36 amplifiers/eight channels/sharedREF/sharedVMID, power-divider10k/10k/2.2uF, MCU150R/470pF',
            '3V ideal rail, nine47k source branches, 20pF FFC+2pF trace+0.5pF ESD perinput; no cable measurement',
            'TPD4E05U06 external ESD is modeled as capacitance only; no qualified fault clamp/ESD waveform model',
            'Passives nominal;27C except25C capacitor-leakage cases; model parameters typical with no mismatch/PVT/package crosstalk',
            'No PCB leakage except explicit coupling-capacitor IR scenario; no real ADC sample/hold, rail regulator, RF coupling or digital activity'],
        'operating_point': {'passed_all36_units': all(a['op_valid'] for a in amps), 'amplifiers': amps,
            'values': op_values, 'supply_current_mA': -op_values['I(VDD)']*1e3,
            'max_amplifier_input_difference_uV': max(abs(a['input_difference_V']) for a in amps)*1e6},
        'steady_dc_sweeps_ideal_capacitors': dc, 'steady_dc_with_capacitor_IR': leakage,
        'capacitor_IR_primary_source': 'https://content.kemet.com/datasheets/kem_c1003_c0g_smd.pdf page4',
        'ac': {'gain_at_1k_VV': g1, 'peak_gain_VV': float(abs(h[peakidx])), 'peak_frequency_Hz': float(f[peakidx]),
            'sampled_peak_relative_minus3dB_band_Hz': [float(f[peak3][0]),float(f[peak3][-1])],
            'target_frequency_values_log_interpolated': acpoints,
            'limitation': 'CMRR is nominal matched family model; tolerance/source/parasitic mismatch results from previous study still apply. Audio-band model cannot establish GHz RF immunity.'},
        'offset_recovery': recovery, 'startup': startup,
        'AFE_OVP_status': 'NO DEDICATED PRECISION OVP CLAMP; nominal output rail-bounding in this model is not input-ESD, unpowered fault, MCU injection, or power-path OVP proof',
        'release_findings': ['Steady DC rejection passes stated ideal/IR scenarios; DC steps still rail amplifier stages and require shared recovery blanking',
            '2s step-recovery delay covers this nominal case, but2s cold startup fails quarter-LSB baseline criterion; use longer Candidate delay plus rail/baseline/clipping checks and qualify hardware',
            'VMID moves and unexcited channels respond during an offset artifact; count validity must account for the shared reference/bias',
            '50/60Hz differential interference is only about14-16dB below1k gain; this is not a mains notch or blanket low-frequency rejection claim',
            'Unchanged >=10MOhm full-band input requirement and actual power/ESD/ADC release gates remain open'],
        'invalid_diagnostics': [{'deck': 'afe-dc-capacitor-leakage.cir', 'status': 'ABORTED_INVALID',
            'reason': 'Additional deliberately poor1GOhm leakage step did not converge directly and stalled in Gmin stepping; agent stopped only this named process.100G/10G scenarios completed separately. No circuit performance conclusion from incomplete diagnostic.'}],
        'runs': manifest(names)}
    (OUT/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    # Scientific figures retain measured raw simulation axes and units.
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.25})
    fig, axes = plt.subplots(2,1,figsize=(9,7),sharex=True)
    axes[0].semilogx(f,20*np.log10(abs(h)),label='Differential, original TI models')
    axes[0].semilogx(f,20*np.log10(abs(cm)),label='Common mode, nominal matched circuit')
    axes[0].set_ylabel('Gain (dB V/V)'); axes[0].legend(loc='lower left')
    axes[1].semilogx(f,np.unwrap(np.angle(h))*180/np.pi)
    axes[1].set_ylabel('Differential phase (degrees)'); axes[1].set_xlabel('Frequency (Hz)')
    for ax in axes: ax.axvspan(300,7000,color='green',alpha=.08); ax.set_xlim(.01,1e7)
    fig.suptitle('CuraLink AFE: actual LTspice nominal family-model frequency response')
    fig.tight_layout(); fig.savefig(FIG/'frequency-response.png',dpi=180); plt.close(fig)
    fig, axes = plt.subplots(2,1,figsize=(9,6),sharex=True)
    for resistance, a, b in zip([100,10],cuts[:-1],cuts[1:]):
        vals=leakraw.trace('V(ADC_IN_1)')[a:b]
        axes[0].plot(x[a:b]*1e3,vals,label=f'{resistance} GOhm per 10 nF capacitor')
        axes[1].plot(x[a:b]*1e3,(vals-vals[len(vals)//2])*1e6,label=f'{resistance} GOhm')
    axes[0].set_ylabel('ADC DC baseline (V)'); axes[0].legend()
    axes[1].set_ylabel('Change from zero-offset (uV)'); axes[1].set_xlabel('CH1 DC offset (mV)')
    fig.suptitle('Steady DC rejection with KEMET insulation-resistance scenarios at 25 C')
    fig.tight_layout(); fig.savefig(FIG/'dc-rejection-leakage.png',dpi=180); plt.close(fig)
    fig, axes = plt.subplots(3,1,figsize=(9,8),sharex=True)
    axes[0].plot(t,tr.trace('V(SRC_CH1)')*1e3); axes[0].set_ylabel('Source offset (mV)')
    axes[1].plot(t,y,label='ADC channel 1'); axes[1].axhline(baseline,color='black',ls='--',lw=.8,label='DC equilibrium')
    axes[1].set_ylabel('ADC voltage (V)'); axes[1].legend()
    axes[2].plot(t,(tr.trace('V(VMID)')-op_values['V(VMID)'])*1e3,label='Shared VMID')
    axes[2].plot(t,(tr.trace('V(AFE_OUT_2)')-baseline)*1e3,label='Unexcited channel 2')
    axes[2].set_ylabel('Artifact (mV)'); axes[2].set_xlabel('Time (s)'); axes[2].legend()
    fig.suptitle('Offset steps: temporary clipping and shared-bias recovery in actual LTspice')
    fig.tight_layout(); fig.savefig(FIG/'offset-recovery.png',dpi=180); plt.close(fig)
    fig, axes = plt.subplots(2,1,figsize=(9,6),sharex=True)
    for node in ['V(VMID)','V(CH1_PRE)','V(ADC_IN_1)']:
        axes[0].plot(st,sr.trace(node),label=node)
    axes[0].set_ylabel('Voltage (V)'); axes[0].legend()
    axes[1].semilogy(st,np.maximum(abs(sy-baseline)*1e6,.01),label='ADC baseline error')
    axes[1].axhline(LSB/4*1e6,color='red',ls='--',label='Quarter ideal LSB (engineering check)')
    axes[1].axvline(2,color='gray',ls=':',label='Prior provisional 2 s delay')
    axes[1].set_ylabel('Absolute baseline error (uV)'); axes[1].set_xlabel('Time (s)'); axes[1].legend()
    fig.suptitle('Cold startup: 1 ms AFE supply ramp, grounded external inputs')
    fig.tight_layout(); fig.savefig(FIG/'startup.png',dpi=180); plt.close(fig)
    print(json.dumps({'results': str(OUT/'results.json'),'op_pass': result['operating_point']['passed_all36_units'],
        'gain_1k':g1,'startup':startup,'recovery':recovery,'leakage':leakage},indent=2))

if __name__ == '__main__':
    main()

"""Actual standalone ADS checks of authored static charger-load approximation.

Run with ADS bundled Python. No workspace edits. Receiver helper imported read-only.
The fixed 0.28 V path loss excludes real protection/charger dynamic behavior.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
RECEIVER_SCRIPT = HERE.parent / "receiver-fixture-2026-10-09" / "run_receiver.py"
spec = importlib.util.spec_from_file_location("receiver_fixture_readonly", RECEIVER_SCRIPT)
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)
CAPS = (59.30046343474315, 374.73956378774636, 826.2058518327118, 773.5931919048533)
OUTPUT_PLAN = 'Type="Output" UseNodeNestLevel=yes NodeNestLevel=2 UseEquationNestLevel=yes EquationNestLevel=2 UseSavedEquationNestLevel=yes SavedEquationNestLevel=2 UseDeviceCurrentNestLevel=yes DeviceCurrentNestLevel=2 DeviceCurrentDeviceType="All" DeviceCurrentSymSyntax=yes UseCurrentNestLevel=yes CurrentNestLevel=999 UseDeviceVoltageNestLevel=yes DeviceVoltageNestLevel=2 DeviceVoltageDeviceType="All"'
CHARGE_LAW = "IQSLEEP*max(0,min(1,_v1/3.6))+(IQACTIVE-IQSLEEP)*max(0,min(1,(_v1-VWAKE)/WNUM))+CHARGE_ALLOWED*IPHASE*max(0,min(1,(_v1-VSTART)/WNUM))*max(0,min(1,(_v1-VDPM)/WDPM))"
CTRL_LAW = "ICTRL*max(0,min(1,(_v1-VBAT)/WOR))"

def parameters(vbat=3.7, iphase=.020, iq=.00075, control=.0008, path=.28, wdpm=.15):
    return f'''VBAT={vbat:.12g}
IPHASE={iphase:.12g}
IQACTIVE={iq:.12g}
IQSLEEP=0.00003
CHARGE_ALLOWED=1
VWAKE=max(3.0,VBAT+0.152)
VSTART=max(3.15,VBAT+0.188)
VDPM=max(3.6,VBAT+0.330)
WNUM=0.020
WDPM={wdpm:.12g}
ICTRL={control:.12g}
WOR=0.100
VPATH={path:.12g}
'''

def dc_deck():
    return f'''Options ResourceUsage=yes UseNutmegFormat=no EnableOptim=no TopDesignName="CuraLink:charger_SDD_DC:schematic" DcopOutputNodeVoltages=yes DcopOutputPinCurrents=yes
VIN_SWEEP=0
{parameters()}
V_Source:VTEST VIN 0 Vdc=VIN_SWEEP
Short:Charger_Probe VIN CHG_IN Mode=0 SaveCurrent=yes
SDD:Charger CHG_IN 0 I[1,0]={CHARGE_LAW}
Short:Control_Probe VIN CTRL_LOAD Mode=0 SaveCurrent=yes
SDD:Control CTRL_LOAD 0 I[1,0]={CTRL_LAW}
DC:DC1 SweepVar="VIN_SWEEP" SweepPlan="DCSweep" StatusLevel=0 OutputPlan="DC_Output"
SweepPlan:DCSweep Start=0 Stop=5.5 Step=0.025
OutputPlan:DC_Output {OUTPUT_PLAN}
'''

def hb_deck(vbat, pin, iphase=.020, iq=.00075, control=.0008, path=.28, wdpm=.15):
    original = rr.netlist(pin=pin, rload=230, caps=CAPS, order=31, diode="bat54")
    original = original.replace('; Four ideal tuning capacitors; resistive DC load; current diode diagnostic only.',
        '; Four ideal capacitors; full BAT54 model; authored static charger/control approximation.\n; VPATH is a fixed voltage-drop fixture, not real SS14/TPS25200 behavior.')
    original = original.replace('R:Rload LoadIn 0 R=Rload Noise=no', f'''{parameters(vbat,iphase,iq,control,path,wdpm)}
R:RawFieldDivider LoadIn 0 R=110000 Noise=no
SDD:EfuseIQ LoadIn 0 I[1,0]=0.000143*max(0,min(1,_v1/2.5))
V_Source:FixedPathDrop LoadIn CHG_IN Vdc=VPATH
C:ChargerCin CHG_IN 0 C=2.2 uF
Short:Charger_Probe CHG_IN CHARGER_LOAD Mode=0 SaveCurrent=yes
SDD:Charger CHARGER_LOAD 0 I[1,0]={CHARGE_LAW}
Short:Control_Probe CHG_IN CTRL_LOAD Mode=0 SaveCurrent=yes
SDD:Control CTRL_LOAD 0 I[1,0]={CTRL_LAW}''')
    return original

def run(simulator, label, deck, block):
    outdir = HERE / "runs" / label
    outdir.mkdir(parents=True, exist_ok=True)
    deck_path = outdir / "charger.ckt"
    if (outdir / 'simulator.log').exists():
        attempt = len(list(outdir.glob('prior-simulator-*.log'))) + 1
        (outdir / f'prior-simulator-{attempt}.log').write_text((outdir / 'simulator.log').read_text(encoding='utf-8'), encoding='utf-8')
        if deck_path.exists():
            (outdir / f'prior-deck-{attempt}.ckt').write_text(deck_path.read_text(encoding='utf-8'), encoding='utf-8')
    deck_path.write_text(deck, encoding="utf-8")
    started = time.monotonic()
    proc = subprocess.run([str(rr.ADS_ROOT / "bin" / "hpeesofsim.exe"), str(deck_path), '--dataset-name=charger', '-T4'],
        cwd=outdir, env=simulator._env, capture_output=True, text=True)
    (outdir / "simulator.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f'ADS exit {proc.returncode}: {outdir / "simulator.log"}')
    with rr.dataset.open(outdir / "charger.ds") as ds:
        df = ds[block].to_dataframe().reset_index()
    df.to_csv(outdir / "dataset.csv", index=False)
    return df, outdir, time.monotonic() - started

def dc_check(simulator):
    df, outdir, elapsed = run(simulator, "SDD_DC_IV", dc_deck(), "DC1.DC")
    df.to_csv(HERE / "SDD-DC-IV.csv", index=False)
    df = df.sort_values('VIN_SWEEP')
    volts = df['CHG_IN'].to_numpy(complex).real
    amps = df['Charger_Probe.i'].to_numpy(complex).real
    control = df['Control_Probe.i'].to_numpy(complex).real
    nearest = lambda voltage: int(np.argmin(abs(volts-voltage)))
    zero, full, weak = nearest(0), nearest(5), nearest(3)
    checks = {
        'actual_ADS_simulation': True, 'source_current_into_load_is_positive': bool(amps[full] > 0),
        'zero_voltage_charger_A': float(amps[zero]), 'zero_voltage_control_A': float(control[zero]),
        'zero_voltage_sink_abs_below_1nA': bool(abs(amps[zero]) < 1e-9 and abs(control[zero]) < 1e-9),
        '5V_charger_A': float(amps[full]), '5V_control_A': float(control[full]),
        'charger_5V_matches_20mA_plus_750uA': bool(abs(amps[full]-.02075) < 1e-8),
        'weak_3V_charger_A': float(amps[weak]),
        'weak_3V_no_fast_charge': bool(amps[weak] < 30e-6),
        'all_charger_currents_nonnegative': bool(amps.min() >= -1e-12),
        'monotone_current_curve': bool(np.diff(amps).min() >= -1e-10),
        'run_directory': str(outdir), 'elapsed_s': elapsed,
        'limits': 'Static I-V/Syntax only; no validation of real BQ25185 loop/thresholds or startup dynamics',
    }
    (HERE / 'SDD-DC-checks.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
    if not all(checks[k] for k in ('source_current_into_load_is_positive', 'zero_voltage_sink_abs_below_1nA',
         'charger_5V_matches_20mA_plus_750uA', 'weak_3V_no_fast_charge', 'all_charger_currents_nonnegative', 'monotone_current_curve')):
        raise RuntimeError('SDD DC physical checks failed')
    print(json.dumps(checks, indent=2), flush=True)

def hb_metrics(df, vbat, pin, iphase, iq, control, path, wdpm):
    df = df.sort_values('freq').reset_index(drop=True)
    harmonic = np.rint(df['freq'].to_numpy(float)/13.56e6).astype(int)
    vraw = df['DCout'].to_numpy(complex)
    vchg = df['CHG_IN'].to_numpy(complex)
    iraw = df['DC_Probe.i'].to_numpy(complex)
    icharger = df['Charger_Probe.i'].to_numpy(complex)
    icontrol = df['Control_Probe.i'].to_numpy(complex)
    zero = int(np.flatnonzero(harmonic==0)[0])
    raw_dc, chg_dc, raw_amps = float(vraw[zero].real), float(vchg[zero].real), float(iraw[zero].real)
    equivalent_r = raw_dc / raw_amps
    m = rr.metrics(df, pin, equivalent_r, CAPS, diode='bat54')
    for key in ('Rload_ohm', 'Pdc_W', 'Idc_A', 'P_load_total_W', 'remaining_rectifier_loss_W', 'power_balance_error_W',
                'eta_available_to_dc', 'eta_accepted_to_dc'):
        m.pop(key, None)
    raw_power = rr.average_power(vraw,iraw,harmonic)
    charger_power = rr.average_power(vchg,icharger,harmonic)
    ctrl_power = rr.average_power(vchg,icontrol,harmonic)
    chg_wave = rr.waveform(vchg,harmonic)
    charger_wave = rr.waveform(icharger,harmonic)
    iq_wave = .00003*np.clip(chg_wave/3.6,0,1)+(iq-.00003)*np.clip((chg_wave-max(3.0,vbat+.152))/.020,0,1)
    ibattery_wave = charger_wave-iq_wave
    battery_mean = float(np.mean(ibattery_wave))
    diode_dissipation = sum(m[f'D{x}_average_dissipation_W'] for x in range(1,5))
    winding_loss = m['tx_coil_resistor_loss_W']+m['rx_coil_resistor_loss_W']
    residual = m['P_accepted_W']-raw_power-winding_loss-diode_dissipation
    m.update({
        'load_model': 'Authored static SDD charger plus control; fixed path drop; actual ADS HB',
        'battery_voltage_V': vbat, 'commanded_charge_current_A': iphase, 'IQACTIVE_A': iq,
        'ICTRL_A': control, 'path_drop_assumption_V': path, 'DPM_full_current_band_assumption_V': wdpm,
        'CHG_IN_V': chg_dc, 'CHG_IN_min_V': float(chg_wave.min()), 'CHG_IN_max_V': float(chg_wave.max()),
        'model_voltage_domain_V': [0,5.5], 'out_of_model_domain': bool(chg_wave.min()<0 or chg_wave.max()>5.5),
        'raw_current_A': raw_amps, 'raw_average_power_W': raw_power,
        'charger_input_current_A': float(icharger[zero].real), 'control_current_A': float(icontrol[zero].real),
        'derived_charge_current_mean_A': battery_mean, 'derived_charge_current_min_A': float(ibattery_wave.min()),
        'derived_charge_current_max_A': float(ibattery_wave.max()), 'derived_battery_charge_power_W': vbat*battery_mean,
        'charger_average_input_power_W': charger_power, 'control_average_input_power_W': ctrl_power,
        'fixed_path_average_loss_W': path*float((icharger[zero]+icontrol[zero]).real),
        'raw_divider_average_power_W': rr.average_power(vraw,vraw/110000,harmonic),
        'efuse_supply_power_fixture_W': raw_dc*.000143,
        'operating_point_equivalent_resistance_ohm': equivalent_r,
        'RF_accepted_to_raw_DC_efficiency': raw_power/m['P_accepted_W'],
        'RF_available_to_raw_DC_efficiency': raw_power/m['P_available_W'],
        'RF_power_balance_residual_W': residual,
        'full_commanded_charge_current_reached': bool(battery_mean>=iphase*(1-1e-5)),
        'receiver_raw_OVP_modeled': False, 'actual_protection_or_charger_dynamics_modeled': False,
    })
    return m

def hb_cases():
    return [
        ('CC_VBAT3p2_P23p5',3.2,23.5,.020,.00075,.0008,.28,.15),
        ('CC_VBAT3p7_P23p5',3.7,23.5,.020,.00075,.0008,.28,.15),
        ('CC_VBAT4p0_P23p5',4.0,23.5,.020,.00075,.0008,.28,.15),
        ('CC_high_VBAT4p0_P23p5',4.0,23.5,.021212121212121215,.001,.0015,.28,.15),
        ('CC_VBAT4p0_P23',4.0,23.0,.020,.00075,.0008,.28,.15),
        ('CC_VBAT4p0_path0p40_P23p5',4.0,23.5,.020,.00075,.0008,.40,.15),
        ('CC_VBAT4p0_ctrl1p5mA_P23p5',4.0,23.5,.020,.00075,.0015,.28,.15),
    ]

def prepare():
    target = HERE / 'input-decks'
    target.mkdir(exist_ok=True)
    (target / 'SDD_DC_IV.ckt').write_text(dc_deck(), encoding='utf-8')
    for label,vbat,pin,iphase,iq,control,path,wdpm in hb_cases():
        (target / f'{label}.ckt').write_text(hb_deck(vbat,pin,iphase,iq,control,path,wdpm), encoding='utf-8')
    raw_law = CHARGE_LAW.replace('_v1', '(_v1-VPATH)')+'+ICTRL*max(0,min(1,(_v1-VPATH-VBAT)/WOR))+0.000143*max(0,min(1,_v1/2.5))+_v1/110000'
    (HERE/'native-raw-SDD-I-1-0.txt').write_text(raw_law+'\n',encoding='utf-8')
    (HERE/'native-raw-SDD-parameters.txt').write_text(parameters(),encoding='utf-8')
    print(f'Prepared DC and {len(hb_cases())} HB decks in {target}', flush=True)

def hb_runs(simulator):
    cases = hb_cases()
    rows=[]
    for label,vbat,pin,iphase,iq,control,path,wdpm in cases:
        df,outdir,elapsed = run(simulator,label,hb_deck(vbat,pin,iphase,iq,control,path,wdpm),'HB1.HB')
        m=hb_metrics(df,vbat,pin,iphase,iq,control,path,wdpm)
        m.update({'run_directory': str(outdir),'elapsed_s': elapsed})
        (outdir/'metrics.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
        rows.append(m)
        rr.write_rows(HERE/'SDD-receiver-results.csv',rows)
        (HERE/'SDD-receiver-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        print(f'{label}: RAW {m["Vdc_V"]:.6f} V, CHG_IN {m["CHG_IN_V"]:.6f} V, charge {1e3*m["derived_charge_current_mean_A"]:.6f} mA, RAW {1e3*m["raw_average_power_W"]:.6f} mW, out_of_domain {m["out_of_model_domain"]}, balance {1e6*m["RF_power_balance_residual_W"]:.3f} uW',flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=('prepare','dc','hb','all'),default='all')
    args=parser.parse_args()
    if args.mode=='prepare':
        prepare()
        return
    simulator=rr.ads.CircuitSimulator(hpeesof_dir=str(rr.ADS_ROOT))
    if args.mode in ('dc','all'): dc_check(simulator)
    if args.mode in ('hb','all'): hb_runs(simulator)

if __name__=='__main__': main()

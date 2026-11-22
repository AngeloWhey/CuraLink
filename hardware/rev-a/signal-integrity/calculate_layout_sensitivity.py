"""Explicit schematic-based sensitivities; no PCB geometry or EM extraction."""
from pathlib import Path
import datetime
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def main():
    input_bias = 1.5
    return_resistance = 22e6
    preamp_gain = 11
    feedback_resistance = 1.818e6
    leak = []
    for resistance in [1e9, 10e9, 100e9]:
        node_shift = -input_bias * return_resistance / (resistance + return_resistance)
        leak.append({'hypothetical_input_to_ground_leakage_ohm': resistance,
                     'input_bias_shift_mV': 1e3 * node_shift,
                     'gain11_preamp_shift_mV': 1e3 * preamp_gain * node_shift})
    feedback = []
    for cap_pf in [.05, .1, .5, 1.0]:
        cap = cap_pf * 1e-12
        x = 2 * math.pi * 7000 * feedback_resistance * cap
        feedback.append({'assumed_parallel_feedback_capacitance_pF': cap_pf,
                         'simple_feedback_impedance_pole_Hz': 1 / (2 * math.pi * feedback_resistance * cap),
                         'feedback_impedance_phase_at_7k_deg': -math.degrees(math.atan(x)),
                         'feedback_impedance_magnitude_ratio_at_7k': 1 / math.sqrt(1 + x*x)})
    root_paths = [ROOT, Path('C:/Users/angel/OneDrive/Documents/projects/curalink')]
    extensions = {'.kicad_pcb', '.pcbdoc', '.brd', '.pcb', '.gbr', '.gerber'}
    layout_search = []
    for folder in root_paths:
        found = sorted(str(p) for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in extensions) if folder.exists() else []
        layout_search.append({'folder': str(folder.resolve()), 'exists': folder.exists(), 'matching_files': found})
    source = ROOT / 'hardware/rev-a/components-merged.json'
    result = {
        'recorded_local_date': '2026-10-02',
        'timezone': 'America/New_York',
        'status': 'CALCULATED SENSITIVITY; NO PLACED OR ROUTED PCB REVIEW',
        'source': str(source.relative_to(ROOT)),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'layout_file_extensions_searched': sorted(extensions),
        'project_folder_search': layout_search,
        'leakage_assumptions': 'Steady state; input coupling capacitor open; VMID held at 1.5 V; an added ohmic path from preamp + input to GND; no bias current or amplifier offset. This is surface leakage sensitivity, not a measured capacitor-insulation result.',
        'input_leakage_sensitivity': leak,
        'feedback_assumptions': 'One capacitance directly across total 1.818 MOhm feedback resistance. Values describe only its impedance, not complete filter gain, stability, distributed pad capacitance or CMRR.',
        'feedback_impedance_sensitivity': feedback,
        'common_return_example': {'assumed_step_current_mA': 20,
                                  'assumed_shared_impedance_mohm': 1,
                                  'calculated_ground_difference_uV': 20,
                                  'qualification': 'Illustrative V=IZ. Only a portion may convert to differential error; actual current path, frequency-dependent impedance and rejection require geometry/measurement.'},
        'candidate_crosstalk_review_check': {
            'single_aggressor_input_uVpp': 1000,
            'victim_input_equivalent_ceiling_uVpp': 1,
            'ratio_ceiling_dB': -60,
            'status': 'PROPOSED REVIEW CHECK; NOT USER-ACCEPTED REQUIREMENT',
            'rationale': 'A 1 uVpp sine is 0.354 uVrms, small compared with the existing 3.44 uVrms calculated electronics-noise result. Coherent, broadband and multiple-aggressor cases need an aggregate criterion.',
            'qualification': 'Compute input equivalence using victim gain at the same frequency and source configuration, not a fixed 1 kHz gain.'}
    }
    (OUT / 'layout-sensitivities.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'PCB_files_found': sum(len(x['matching_files']) for x in layout_search),
                      'leakage': leak,
                      'feedback_1pF_7k': feedback[-1]}, indent=2))


if __name__ == '__main__':
    main()

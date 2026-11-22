"""Build a self-contained nominal circuit and assumed-parasitic SI study.

No canonical design or prior simulation file is modified. The parasitic values
are sensitivity assumptions, not extracted from a PCB, package, or FFC.
"""
from pathlib import Path
import hashlib
import json
import shutil

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
PREVIOUS = ROOT / 'hardware/rev-a/ltspice/afe'
MODEL = OUT / 'models'
MODEL.mkdir(parents=True, exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

copies = [PREVIOUS / 'canonical-afe.lib', PREVIOUS / 'read_ltspice_raw.py']
copies += list((PREVIOUS / 'models').glob('tlv*-*.lib'))
copies += [PREVIOUS / 'models/model-provenance.json']
copied = []
for src in copies:
    dst = MODEL / src.name if src.parent.name == 'models' else OUT / src.name
    shutil.copyfile(src, dst)
    copied.append({'source': src.relative_to(ROOT).as_posix(),
                   'snapshot': dst.relative_to(ROOT).as_posix(), 'sha256': sha(dst)})

header = '''* CuraLink: CH1-only circuit crosstalk; added Cx is an assumed sensitivity
.include models/tlv9002-namespaced.lib
.include models/tlv9052-namespaced.lib
.options numdgt=7 plotwinsize=0
.temp 27
.include canonical-afe.lib
VDD AVDD_3V0 0 DC 3
VCOMMON COMMON_SRC 0 DC 0 AC 0
VCH1 SRC_CH1 COMMON_SRC DC 0 AC 1
'''
header += ''.join(f'VCH{i} SRC_CH{i} COMMON_SRC DC 0 AC 0\n' for i in range(2, 9))
header += 'VREF SRC_REF COMMON_SRC DC 0 AC 0\n'
nodes = ['AVDD_3V0', 'VMID_RAW', 'VMID_BUF', 'VMID', 'REF_PLUS', 'REF_PRE',
         'SRC_CH1', 'FFC_CH1', 'FFC_CH2', 'CH1_PLUS', 'CH2_PLUS']
nodes += [f'AFE_OUT_{i}' for i in range(1, 9)]
nodes += [f'ADC_IN_{i}' for i in range(1, 9)]
save = '.save ' + ' '.join(f'V({n})' for n in nodes) + ' I(VDD)\n'
caps = [0, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
step = '.step param Cx list 0 20f 50f 100f 200f 500f 1p\n'
late_caps = [0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
late_step = '.step param Cx list 0 10f 20f 50f 100f 200f 500f 1p\n'
for name, added in [('ch1-only', ''),
                    ('input-input', 'C_ASSUMED FFC_CH1 FFC_CH2 {Cx}\n' + step),
                    ('output-input', 'C_ASSUMED AFE_OUT_1 CH2_PLUS {Cx}\n' + late_step)]:
    (OUT / (name + '.cir')).write_text(header + added + save + '.ac dec 100 300 7k\n.end\n')

# Independent direct OP qualification for every amplifier unit in the snapshot.
amp_nodes = set()
for line in (OUT / 'canonical-afe.lib').read_text().splitlines():
    if line.startswith('XU'):
        amp_nodes.update(line.split()[1:6])
amp_nodes.discard('0')
op_header = header.replace('DC 0 AC 1', 'DC 0 AC 0')
op_save = save + '.save ' + ' '.join(f'V({n})' for n in sorted(amp_nodes)) + '\n'
(OUT / 'valid-operating-point.cir').write_text(op_header + op_save + '.op\n.end\n')

(OUT / 'source-provenance.json').write_text(json.dumps({
    'date': '2026-10-02', 'status': 'Nominal sensitivity study, not routed-PCB extraction',
    'source_snapshots': copied,
    'canonical_source_current_sha256': sha(ROOT / 'hardware/rev-a/afe/afe-pin-nets.json'),
    'fixture': {'channels': 8, 'reference_channels': 1, 'source_resistance_ohm': 47000,
        'series_limit_ohm': 5100, 'assumed_FFC_shunt_capacitance_per_input_pF': 20,
        'assumed_trace_shunt_capacitance_per_input_pF': 2,
        'ESD_capacitance_only_per_input_pF': 0.5, 'rail_V': 3, 'temperature_C': 27,
        'frequency_Hz': [300, 7000], 'ac_points_per_decade': 100,
        'excitation': 'CH1 external source=AC1; other seven sources and REF=AC0 with all 47k series resistances preserved',
        'added_coupling_pF': caps,
        'late_output_added_coupling_pF': late_caps,
        'input_input_nodes': ['FFC_CH1', 'FFC_CH2'],
        'output_input_nodes': ['AFE_OUT_1', 'CH2_PLUS']},
    'limits': ['Family single-amplifier models do not model selected quad package crosstalk',
        'Rail and ground sources are ideal; no copper return impedance or shared supply impedance',
        'No ADC sampling switches, RF/BLE/13.56MHz excitation, or cable/package parasitic extraction',
        'Added capacitors are assumptions with no geometry-based justification; useful for sensitivity only',
        'No component-tolerance or worst-case statistical study in this fixture',
        'AC analysis is linearized at a verified OP; amplitudes are linear scaling estimates, not spike-template runs']
}, indent=2))

(OUT / 'run_crosstalk.ps1').write_text('''$ErrorActionPreference = 'Stop'
$siDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$siExecutable = if ($env:CURALINK_LTSPICE_EXE) { $env:CURALINK_LTSPICE_EXE } else { Join-Path $env:LOCALAPPDATA 'Programs/ADI/LTspice/LTspice.exe' }
foreach ($siCase in @('valid-operating-point','ch1-only','input-input','output-input')) {
    $siProcess = Start-Process -FilePath $siExecutable -ArgumentList '-b','-ascii',($siCase+'.cir') -WorkingDirectory $siDirectory -WindowStyle Hidden -Wait -PassThru
    $siProcess.ExitCode | Set-Content -Path (Join-Path $siDirectory ($siCase+'.exitcode.txt'))
    if ($siProcess.ExitCode -ne 0) { throw "LTspice returned $($siProcess.ExitCode) for $siCase" }
    Write-Output ($siCase + ': exit ' + $siProcess.ExitCode)
}
''')
print('Built four LTspice fixtures and immutable source snapshots in', OUT)

"""Isolated candidate VMID topology comparison; no canonical changes."""
from pathlib import Path
import hashlib
import json
import shutil

OUT=Path(__file__).resolve().parent
PRIOR=OUT.parent
ROOT=OUT.parents[4]
(OUT/'models').mkdir(parents=True,exist_ok=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
snapshots=[]
for src in [PRIOR/'canonical-afe.lib',PRIOR/'read_ltspice_raw.py']+list((PRIOR/'models').glob('*')):
    if not src.is_file():continue
    dest=OUT/'models'/src.name if src.parent.name=='models'else OUT/src.name
    shutil.copyfile(src,dest)
    snapshots.append({'source':src.relative_to(ROOT).as_posix(),
        'snapshot':dest.relative_to(ROOT).as_posix(),'sha256':sha(dest)})
base=(OUT/'canonical-afe.lib').read_text()
cases={}
for name,resistance in [('shared47',47),('shared4R7',4.7),('split47',47)]:
    lines=[]
    for line in base.splitlines():
        words=line.split()
        if words and words[0]=='R1149':words[-1]=str(resistance);line=' '.join(words)
        if name=='split47':
            if ' VMID 'in ' '+line+' ':
                if any('_LP1_'in x for x in words):
                    words=['VMID_LP1'if x=='VMID'else x for x in words];line=' '.join(words)
                elif any('_LP2_'in x for x in words):
                    words=['VMID_LP2'if x=='VMID'else x for x in words];line=' '.join(words)
            if words and words[0]=='XU109_3':line=line.replace('AFE_SPARE_C','VMID_LP1_BUF')
            if words and words[0]=='XU109_4':line=line.replace('AFE_SPARE_D','VMID_LP2_BUF')
        lines.append(line)
    if name=='split47':
        lines+=['* Study-only spare buffer loads; feedback stays before isolation resistor',
            'R_STUDY_LP1 VMID_LP1_BUF VMID_LP1 47',
            'C_STUDY_LP1 VMID_LP1 0 4.7u',
            'R_STUDY_LP2 VMID_LP2_BUF VMID_LP2 47',
            'C_STUDY_LP2 VMID_LP2 0 4.7u']
    library='\n'.join(lines)+'\n'
    (OUT/(name+'.lib')).write_text(library)
    amp_nodes=set()
    for line in lines:
        if line.startswith('XU'):amp_nodes.update(line.split()[1:6])
    amp_nodes.discard('0')
    nodes=sorted(amp_nodes|{'VMID','VMID_RAW'}|{f'ADC_IN_{i}'for i in range(1,9)})
    if name=='split47':nodes+=['VMID_LP1','VMID_LP2']
    save='.save '+' '.join('V('+n+')'for n in nodes)+' I(VDD)\n'
    header='''* CuraLink study-only VMID comparison; ideal supply, nominal TI family models
.include models/tlv9002-namespaced.lib
.include models/tlv9052-namespaced.lib
.options numdgt=7 plotwinsize=0
.temp 27
'''+'.include '+name+'.lib\n'+'VDD AVDD_3V0 0 DC 3\nVCOMMON COMMON_SRC 0 DC 0 AC 0\n'
    header+=''.join(f'VCH{i} SRC_CH{i} COMMON_SRC DC 0 AC '+('1'if i==1 else'0')+'\n'for i in range(1,9))
    header+='VREF SRC_REF COMMON_SRC DC 0 AC 0\n'
    (OUT/(name+'-ac.cir')).write_text(header+save+'.ac dec 100 300 7k\n.end\n')
    (OUT/(name+'-op.cir')).write_text(header.replace('DC 0 AC 1','DC 0 AC 0')+save+'.op\n.end\n')
    cases[name]={'isolation_resistor_ohm':resistance,'split':name=='split47',
        'library_sha256':sha(OUT/(name+'.lib'))}
(OUT/'provenance.json').write_text(json.dumps({'date':'2026-10-02','status':'Isolated proposal; canonical unchanged',
    'source_snapshots':snapshots,'cases':cases,
    'fixture':'Original 8-channel + REF, 36 amplifiers, 3V ideal supply, 27C; all source resistors47k, FFC20pF+trace2pF+ESD0.5pF assumptions; only CH1 AC1',
    'split_mapping':{'U109B':'VMID quiet preamp + REF + difference balance',
        'U109C':'VMID_LP1 first low-pass shunt capacitors and feedback-ground resistors',
        'U109D':'VMID_LP2 second low-pass shunt capacitors and feedback-ground resistors'},
    'limits':['Family models omit quad-package coupling and thermal interaction',
        'No PCB parasitic extraction; no tolerance/PVT/stability certification',
        'AC improvement alone does not qualify new isolation/load topology']},indent=2))
(OUT/'run_bias_ac.ps1').write_text('''$ErrorActionPreference = 'Stop'
$biasDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$biasExecutable = if ($env:CURALINK_LTSPICE_EXE) { $env:CURALINK_LTSPICE_EXE } else { Join-Path $env:LOCALAPPDATA 'Programs/ADI/LTspice/LTspice.exe' }
foreach ($biasCase in @('shared47-op','shared4R7-op','split47-op','shared47-ac','shared4R7-ac','split47-ac')) {
    $biasProcess = Start-Process -FilePath $biasExecutable -ArgumentList '-b','-ascii',($biasCase+'.cir') -WorkingDirectory $biasDirectory -WindowStyle Hidden -Wait -PassThru
    $biasProcess.ExitCode | Set-Content -Path (Join-Path $biasDirectory ($biasCase+'.exitcode.txt'))
    if ($biasProcess.ExitCode -ne 0) { throw "LTspice returned $($biasProcess.ExitCode) for $biasCase" }
    Write-Output ($biasCase + ': exit ' + $biasProcess.ExitCode)
}
''')
print('Built three isolated topology candidates, six actual LTspice runs')

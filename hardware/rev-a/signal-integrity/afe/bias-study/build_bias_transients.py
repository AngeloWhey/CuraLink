"""Extend isolated VMID study; no canonical or prior results are modified."""
from pathlib import Path
import re
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
old=(OUT/'split47.lib').read_text()
new=re.sub(r'(R_STUDY_LP[12] \S+ \S+) 47',r'\1 4.7',old)
(OUT/'split4R7.lib').write_text(new)
for suffix in ['ac','op']:
    text=(OUT/('split47-'+suffix+'.cir')).read_text().replace('split47.lib','split4R7.lib')
    (OUT/('split4R7-'+suffix+'.cir')).write_text(text)

names=['split4R7-op','split4R7-ac']
for case in ['shared4R7','split4R7']:
    prior=ROOT/'hardware/rev-a/ltspice/afe'
    for kind,source in [('startup',prior/'afe-startup.cir'),
                        ('offset-recovery',prior/'afe-offset-recovery-long.cir')]:
        deck=source.read_text().replace('.include canonical-afe.lib','.include '+case+'.lib')
        if case=='split4R7':
            deck=deck.replace('.tran ','.save V(VMID_LP1) V(VMID_LP2) V(VMID_LP1_BUF) V(VMID_LP2_BUF)\n.tran ')
        (OUT/(case+'-'+kind+'.cir')).write_text(deck)
        names.append(case+'-'+kind)

    # Actual full 36-unit load fixture, stepped only for nominal MLCC capacity
    # stress. Command steps challenge loop/capacitive load; load pulses challenge
    # output drive. These are bounded tests, not extracted loop phase margins.
    library=(OUT/(case+'.lib')).read_text()
    for ref in ['C1058','C_STUDY_LP1','C_STUDY_LP2']:
        library=re.sub(r'(?m)^('+ref+r' \S+ \S+) \S+$',r'\1 {4.7u*Cscale}',library)
    library=re.sub(r'(?m)^(XU109_[234]) VMID_RAW ',r'\1 VMID_COMMAND ',library)
    (OUT/(case+'-load.lib')).write_text(library)
    header=(OUT/(case+'-ac.cir')).read_text().split('.save')[0].replace('.include '+case+'.lib','.include '+case+'-load.lib')
    header=header.replace('DC 0 AC 1','DC 0 AC 0')
    header+='V_BIAS_COMMAND VMID_COMMAND VMID_RAW PULSE(0 5m 5u 20n 20n 50u 500u)\n'
    # A simultaneous 0.5mA pulse at each driven buffer output provides a separate
    # event after command recovery, with rise/fall20ns and width25us.
    nodes=['VMID_BUF']
    if case=='split4R7':nodes+=['VMID_LP1_BUF','VMID_LP2_BUF']
    for i,node in enumerate(nodes):header+=f'I_LOAD_{i} {node} 0 PULSE(0 500u 1m 20n 20n 25u 10m)\n'
    save_nodes=['VMID_COMMAND','VMID_RAW','VMID_BUF','VMID','AFE_OUT_1','AFE_OUT_2']
    if case=='split4R7':save_nodes+=['VMID_LP1_BUF','VMID_LP2_BUF','VMID_LP1','VMID_LP2']
    header+='.save '+' '.join('V('+n+')'for n in save_nodes)+' I(VDD)\n'
    header+='.step param Cscale list 0.8 1.2\n.tran 0 1.5m 0 100n\n.end\n'
    (OUT/(case+'-load-step.cir')).write_text(header)
    names.append(case+'-load-step')

script='''$ErrorActionPreference = 'Stop'
$biasDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$biasExecutable = if ($env:CURALINK_LTSPICE_EXE) { $env:CURALINK_LTSPICE_EXE } else { Join-Path $env:LOCALAPPDATA 'Programs/ADI/LTspice/LTspice.exe' }
foreach ($biasCase in @('''+','.join("'"+n+"'"for n in names)+''')) {
    $biasProcess = Start-Process -FilePath $biasExecutable -ArgumentList '-b','-ascii',($biasCase+'.cir') -WorkingDirectory $biasDirectory -WindowStyle Hidden -Wait -PassThru
    $biasProcess.ExitCode | Set-Content -Path (Join-Path $biasDirectory ($biasCase+'.exitcode.txt'))
    if ($biasProcess.ExitCode -ne 0) { throw "LTspice returned $($biasProcess.ExitCode) for $biasCase" }
    Write-Output ($biasCase + ': exit ' + $biasProcess.ExitCode)
}
'''
(OUT/'run_bias_transients.ps1').write_text(script)
print('Built extended candidate OP/AC + startup/recovery/load study:',names)

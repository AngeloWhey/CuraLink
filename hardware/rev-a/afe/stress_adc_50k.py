"""Final-driver periodic SAR tracking stress at 50 kS/s per channel.

Reads the existing validated 30 kS/s test decks and changes only the per-channel
sampling period and output filenames. Physical AFE/MCU connectivity is unchanged.
"""
from pathlib import Path
import subprocess,json,sys
from concurrent.futures import ThreadPoolExecutor
OUT=Path(__file__).resolve().parent
D=OUT/'adc-stress-50k';D.mkdir(exist_ok=True)
cases=[]
for freq in [1000,7000]:
    for cap in [5,10]:
        name=f'track_50k_{freq}Hz_adc{cap}'
        src=OUT/'adc-stress'/f'track_{freq}Hz_adc{cap}.cir'
        deck=src.read_text().replace('33.333333u','20u')
        deck=deck.replace('tran 5n 400u 0 10n','tran 10n 2m 0 20n')
        deck=deck.replace(f'adc-stress/track_{freq}Hz_adc{cap}.csv',
            f'adc-stress-50k/{name}.csv')
        (D/(name+'.cir')).write_text(deck)
        cases.append(dict(name=name,freq_Hz=freq,ADC_pF=cap,fs_Hz=50000,
            Riso_ohm=150,Creservoir_pF=470,acquisition_us=1.656))
(D/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
if '--run' in sys.argv:
    def run(case):
        n=case['name']
        p=subprocess.run(['ngspice','-b',str(D/(n+'.cir')),'-o',str(D/(n+'.log'))],
            cwd=OUT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return n,p.returncode
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n,code in pool.map(run,cases):print(n,code,flush=True)
else:print('Built',len(cases),'50 kS/s stress cases')

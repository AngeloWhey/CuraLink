"""Build ADC isolation RC damping sweep; run with --run inside Linux/ngspice cwd."""
from pathlib import Path
import re,subprocess,sys,json
from concurrent.futures import ThreadPoolExecutor
OUT=Path(__file__).resolve().parent
SWEEP=OUT/'adc-sweep';SWEEP.mkdir(exist_ok=True)
jobs=[]
for cap in [5,10]:
    template=(OUT/f'vendor-adc-{cap}p.cir').read_text()
    for r in [33,47,100,150]:
        for c in [330,470,1000]:
            name=f'r{r}_c{c}_adc{cap}p'
            deck=template.replace('RISO out adc 47',f'RISO out adc {r}').replace('CRES adc 0 1n',f'CRES adc 0 {c}p')
            # One acquisition stays on to 3.5 us, allowing evaluate 1.2, 1.656,
            # and 2.47 us from the same full transient, not interpolating hold.
            deck=deck.replace('2.2u 1 2.201u 0','3.5u 1 3.501u 0')
            deck=deck.replace('tran 1n 8u 0 2n','tran 1n 4u 0 2n')
            deck=re.sub(r'wrdata vendor-adc-\d+p.csv',f'wrdata adc-sweep/{name}.csv',deck)
            file=SWEEP/(name+'.cir');file.write_text(deck)
            jobs.append(name)
(SWEEP/'cases.json').write_text(json.dumps(jobs,indent=2))
if '--run' in sys.argv:
    def run(name):
        proc=subprocess.run(['ngspice','-b',str(SWEEP/(name+'.cir')),'-o',str(SWEEP/(name+'.log'))],cwd=OUT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return name,proc.returncode
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name,code in pool.map(run,jobs):print(name,code,flush=True)
else:print(f'Built {len(jobs)} sweep cases')

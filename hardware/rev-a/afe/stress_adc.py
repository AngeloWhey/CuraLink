"""ADC candidate polarity/tolerance and periodic tracking stress decks."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,sys,re
OUT=Path(__file__).resolve().parent;D=OUT/'adc-stress';D.mkdir(exist_ok=True)
cases=[]
for cnom in [470,1000]:
    for cap in [5,10]:
        base=(OUT/f'vendor-adc-{cap}p.cir').read_text()
        for direction in ['down','up']:
            for rt,ct in [(1,1),(.99,.95),(.99,1.05),(1.01,.95),(1.01,1.05)]:
                name=f'c{cnom}_adc{cap}_{direction}_r{rt}_c{ct}'
                deck=base.replace('RISO out adc 47',f'RISO out adc {150*rt}').replace('CRES adc 0 1n',f'CRES adc 0 {cnom*ct}p')
                deck=deck.replace('2.2u 1 2.201u 0','3.5u 1 3.501u 0').replace('tran 1n 8u 0 2n','tran 1n 4u 0 2n')
                if direction=='up':
                    deck=deck.replace('DC 0.919642857142857','DC 2.08035714285714').replace('VPREV prev 0 DC 2.8','VPREV prev 0 DC 0.2')
                deck=re.sub(r'wrdata vendor-adc-\d+p.csv',f'wrdata adc-stress/{name}.csv',deck)
                (D/(name+'.cir')).write_text(deck)
                cases.append(dict(name=name,Cnom_pF=cnom,ADC_pF=cap,direction=direction,Rfactor=rt,Cfactor=ct,type='step'))
# Periodic worst precharge to previous channel 2.8V, actual waveform centered1.5.
# A duplicate quiet final SK + RC + continuously tracking RADC/CSAMP reference
# distinguishes kickback/settling error from the SAR input's ordinary aperture delay.
for freq in [1000,7000]:
    for cap in [5,10]:
        name=f'track_{freq}Hz_adc{cap}'
        base=(OUT/f'vendor-adc-{cap}p.cir').read_text()
        base=base.replace('VIN prior 0 DC 0.919642857142857',f'VIN prior 0 SIN(1.5 0.15 {freq})')
        base=base.replace('RISO out adc 47','RISO out adc 150').replace('CRES adc 0 1n','CRES adc 0 470p')
        base=base.replace('VCP cp 0 PWL(0 1 0.9u 1 0.901u 0 8u 0)','VCP cp 0 PULSE(1 0 1u 1n 1n 1.856u 33.333333u)')
        base=base.replace('VCA ca 0 PWL(0 0 1u 0 1.001u 1 2.2u 1 2.201u 0 8u 0)','VCA ca 0 PULSE(0 1 1.1u 1n 1n 1.656u 33.333333u)')
        duplicate=['R1Q prior aq 22.6k','R2Q aq plusq 22.6k','C1Q aq outq 1n','C2Q plusq VMID 1n',
            'RGQ minusq VMID 10k','RFQ outq minusq 12.4k','Xquiet plusq minusq AVDD 0 outq TLV9052_TLV9052',
            'RISOQ outq adcq 150','CRESQ adcq 0 470p','RADCQ adcq heldq 1k',f'CSAMPQ heldq 0 {cap}p']
        base=base.replace('.control','\n'.join(duplicate)+'\n.control')
        base=base.replace('tran 1n 8u 0 2n','tran 5n 400u 0 10n')
        base=re.sub(r'wrdata vendor-adc-\d+p.csv v\(out\) v\(adc\) v\(held\)',
            f'wrdata adc-stress/{name}.csv v(out) v(adc) v(held) v(outq) v(adcq) v(heldq)',base)
        (D/(name+'.cir')).write_text(base)
        cases.append(dict(name=name,type='track',freq_Hz=freq,ADC_pF=cap))
(D/'cases.json').write_text(json.dumps(cases,indent=2))
if '--run' in sys.argv:
    def run(case):
        n=case['name'];p=subprocess.run(['ngspice','-b',str(D/(n+'.cir')),'-o',str(D/(n+'.log'))],cwd=OUT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return n,p.returncode
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n,code in pool.map(run,cases):print(n,code,flush=True)
else:print('Built',len(cases),'stress cases')

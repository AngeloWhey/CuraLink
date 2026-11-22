"""Namespace unmodified TI originals and build ngspice-compatible test decks.

Family-level macro-model use is a simulation assumption, not a characterization
of quad package cross-talk. All original model headers remain present.
"""
from pathlib import Path
import re, json
from calculate_afe import Circuit
OUT=Path(__file__).resolve().parent
sections=[]
for part in ['tlv9002','tlv9052']:
    raw=(OUT/'vendor'/part/(part+'.lib')).read_text()
    names=re.findall(r'^\s*\.(?:subckt|model)\s+(\S+)',raw,flags=re.I|re.M)
    for name in sorted(set(names),key=len,reverse=True):
        raw=re.sub(r'(?<!\S)'+re.escape(name)+r'(?!\S)',part.upper()+'_'+name,raw,flags=re.I)
    # PSpice uses absolute zero to suppress resistor noise; exact 0 K produces
    # NaNs in ngspice's temperature-dependent processing. 0.01 K preserves
    # DC/AC resistance while making residual resistor thermal noise negligible.
    raw=raw.replace('T_ABS=-273.15','T_ABS=-273.14')
    # PSpice's resistor model-before-value ordering is not ngspice's canonical
    # ordering. Put the resistance before the model name explicitly.
    raw=re.sub(r'(?im)^(R\S+\s+\S+\s+\S+\s+)('+part.upper()+r'_R_NOISELESS)\s+(\S+)',r'\1\3 \2',raw)
    # ngspice PSpice compatibility did not converge with the diode-driven
    # noise generators. For DC/AC/transient only, replace their zero-mean ports
    # by zero voltage/current. Do not use this adapter for .noise analyses.
    for name in names:
        if name.upper().startswith('VNSE') or name.upper().startswith('FEMT'):
            pref=part.upper()+'_'+name
            zero='VZERO 1 2 DC 0' if name.upper().startswith('VNSE') else 'IZERO 1 2 DC 0'
            raw=re.sub(r'(?im)^\s*\.subckt\s+'+re.escape(pref)+r'\s+1\s+2\s*\n.*?^\s*\.ends[^\n]*',
                '.SUBCKT '+pref+' 1 2\n* ngspice DC/AC/transient adapter: zero-mean noise port disabled\n'+zero+'\n.ENDS '+pref,
                raw,flags=re.I|re.M|re.S)
    sections.append('* Derived adapter: identifiers prefixed '+part.upper()+
        '; R_NOISELESS 0.01 K; noise port generators disabled for ngspice DC/AC/transient only\n'+raw)
(OUT/'vendor'/'combined-namespaced.lib').write_text('\n'.join(sections))
(OUT/'.spiceinit').write_text('set ngbehavior=ps\n')
c=Circuit()

def full(source, supply='DC 3', rawmid='DC 1.5'):
    lines=['* CuraLink candidate: real 3V supplies, one channel + shared REF + VMID',
        '* TI dual family macro-model represents one amplifier per instance; package cross-talk not modeled.',
        '.include vendor/combined-namespaced.lib',f'VS AVDD 0 {supply}',
        f'VMRAW VMID_RAW 0 {rawmid}',source,'Vref refsrc 0 DC 1.5 AC 0',
        'Xvmid VMID_RAW VMID_BUF AVDD 0 VMID_BUF TLV9002_TLV9002',
        'Rvmid VMID_BUF VMID 47','Cvmid VMID 0 4.7u',
        '.nodeset v(VMID_BUF)=1.5 v(VMID)=1.5 v(cho)=1.5 v(refo)=1.5 v(do)=1.5 v(lp1o)=1.5 v(lp2o)=1.5']
    for typ,name,a,b,val,group in c.parts:
        if 'cincommon' in name or 'cindiff' in name:continue # already represented inside TI macro-model
        a='VMID' if a=='0' else a;b='VMID' if b=='0' else b
        if name.endswith('esdtraceffc') or name=='adcreservoir':b='0'
        lines.append(f'{typ}{name} {a} {b} {val:.12g}')
    for name,p,m,o in c.amps:
        model='TLV9052_TLV9052' if name=='lp2' else 'TLV9002_TLV9002'
        lines.append(f'X{name} {p} {m} AVDD 0 {o} {model}')
    return lines

common=['.control','set wr_singlescale','set wr_vecnames']
ac=full('Vsig src 0 DC 1.5 AC 1')+common+[
    'ac dec 60 100 400k','wrdata vendor-ac.csv v(adc) v(cho) v(do) v(VMID)',
    'op','print v(adc) v(cho) v(refo) v(VMID) i(VS)','quit','.endc','.end']
(OUT/'vendor-ac.cir').write_text('\n'.join(ac)+'\n')

# Synthetic 1 mVpp bipolar pulse, source voltage around DC 1.5 V.
spike=full('Vsig src 0 PWL(0 1.5 5m 1.5 5.125m 1.5005 5.25m 1.5 5.375m 1.4995 5.5m 1.5 10m 1.5)')+common+[
    'tran 1u 10m 0 2u','wrdata vendor-spike.csv v(src) v(cho) v(adc) v(VMID)',
    'quit','.endc','.end']
(OUT/'vendor-spike.cir').write_text('\n'.join(spike)+'\n')

step=full('Vsig src 0 PWL(0 1.5 5m 1.5 5.001m 1.6 50m 1.6 50.001m 1.5 150m 1.5 150.001m 1.4 250m 1.4 250.001m 1.5 500m 1.5)')+common+[
    'tran 20u 500m 0 40u','wrdata vendor-offset.csv v(src) v(cho) v(adc) v(VMID)',
    'quit','.endc','.end']
(OUT/'vendor-offset.cir').write_text('\n'.join(step)+'\n')

startup=full('Vsig src 0 DC 1.25',supply='PWL(0 0 1m 3)',rawmid='PWL(0 0 1m 1.5)')
# Start source offset mismatched to reference to exercise DC return + clipping.
startup+=common+['tran 200u 2s 0 200u','wrdata vendor-startup.csv v(cho) v(adc) v(VMID) i(VS)',
    'quit','.endc','.end']
(OUT/'vendor-startup.cir').write_text('\n'.join(startup)+'\n')

for cap in [5,10]:
    lines=['* Final actual SK stage, worst adjacent sample 2.8V -> 0.2V',
        '* ADC simplified switch (1k on) + sample capacitor. Does not model actual SAR conversion kickback.',
        '.include vendor/combined-namespaced.lib','VS AVDD 0 DC 3','VMID VMID 0 DC 1.5',
        'VIN prior 0 DC 0.919642857142857','R1 prior a 22.6k','R2 a plus 22.6k',
        'C1 a out 1n','C2 plus VMID 1n','RG minus VMID 10k','RF out minus 12.4k',
        'Xfinal plus minus AVDD 0 out TLV9052_TLV9052',
        'RISO out adc 47','CRES adc 0 1n',f'CSAMP held 0 {cap}p',
        'VPREV prev 0 DC 2.8','Sprev held prev cp 0 SAMPSW','Sacq held adc ca 0 SAMPSW',
        'VCP cp 0 PWL(0 1 0.9u 1 0.901u 0 8u 0)',
        'VCA ca 0 PWL(0 0 1u 0 1.001u 1 2.2u 1 2.201u 0 8u 0)',
        '.model SAMPSW SW(Ron=1k Roff=1e12 Vt=0.5 Vh=0)',
        *common,'tran 1n 8u 0 2n',f'wrdata vendor-adc-{cap}p.csv v(out) v(adc) v(held)',
        'quit','.endc','.end']
    (OUT/f'vendor-adc-{cap}p.cir').write_text('\n'.join(lines)+'\n')
print('Wrote namespaced vendor library and six simulation decks')

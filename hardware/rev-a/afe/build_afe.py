"""Produce the CuraLink Rev-A candidate AFE connectivity (not a released BOM)."""
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent
components = []
counter = {'R': 1000, 'C': 1000, 'TP': 100}

def passive(kind, value, a, b, page, tol=None, notes='', populated=True):
    counter[kind] += 1
    ref = kind + str(counter[kind])
    components.append(dict(ref=ref, value=value, mpn=None, lcsc=None,
        package='0603' if kind == 'C' else '0402', pins={'1': a, '2': b},
        pinfunctiontypes={'1': 'passive', '2': 'passive'}, page=page,
        tolerance=tol, populated=populated, notes=notes))
    return ref

def diff_series(a,b,middle,page):
    for x,y in [(a,middle),(middle,b)]:
        ref=passive('R','909k',x,y,page,'0.1%',
            'Two 909 kΩ 0.1% in series provide 1.818 MΩ; intentional updated gain ratio.')
        components[-1].update(mpn='RT0603BRE07909KL',lcsc='C3014193',package='0603')

def tp(net, page):
    counter['TP'] += 1
    components.append(dict(ref='TP'+str(counter['TP']), value=net, mpn=None,
        lcsc=None, package='TestPoint_Pad_D1.0mm', pins={'1':net},
        pinfunctiontypes={'1':'passive'}, page=page, populated=False,
        notes='Bare pad. Low-C probe at high-impedance input; ordinary scope probe changes loading.'))

# RUC pin map, NOT the standard TSSOP/SOIC map. No exposed-pad pin.
units = [(2, 1, 14), (4, 5, 6), (9, 8, 7), (11, 12, 13)]
amps = {}
for ic in range(101, 110):
    fast = ic in (107, 108)
    pins = {'3':'AVDD_3V0','10':'GND'}
    typ = {'3':'power_in','10':'power_in'}
    amps[ic] = dict(ref=f'U{ic}', value='TLV9054IRUCR' if fast else 'TLV9004IRUCR',
        mpn='TLV9054IRUCR' if fast else 'TLV9004IRUCR',
        lcsc='C2057826' if fast else 'C2058192',
        package='X2QFN-14_RUC_2x2mm_P0.4mm_NoEP', pins=pins,
        pinfunctiontypes=typ, page='afe_shared', units=[], unit_blocks=[],
        pin_names={'1':'IN_A-', '2':'IN_A+', '3':'V+', '4':'IN_B+', '5':'IN_B-',
            '6':'OUT_B', '7':'OUT_C', '8':'IN_C-', '9':'IN_C+', '10':'V-',
            '11':'IN_D+', '12':'IN_D-', '13':'OUT_D', '14':'OUT_A'},
        notes='TI datasheet Table 6-5 RUC pin map; audit CAD footprint against TI RUC0014A.')

def amp(ic, unit, p, m, o, role, page):
    pi, mi, oi = units[unit]
    for pin, net, typ in [(pi,p,'input'),(mi,m,'input'),(oi,o,'output')]:
        amps[ic]['pins'][str(pin)] = net
        amps[ic]['pinfunctiontypes'][str(pin)] = typ
    amps[ic]['units'].append(dict(unit='ABCD'[unit], positive=p, negative=m,
        output=o, role=role, page=page))
    stage = ('preamp' if role.startswith('Input') else 'diff_hp' if role.startswith('Matched')
        else 'filter_lp1' if role.startswith('Sallen-Key section 1') else 'filter_lp2'
        if role.startswith('Sallen-Key') else 'vmid' if role.startswith('VMID') else 'unused')
    amps[ic]['unit_blocks'].append(dict(unit=unit+1,pins=[str(oi),str(mi),str(pi)],
        channel=int(page.split('ch')[-1]) if page.startswith('afe_ch') else None,
        stage=stage,page=page))

def preamp(name, inp, ic, unit, page):
    passive('R','5.1k',inp,name+'_LIMIT',page,'1%',
        'Input fault-current limiter. ESD shunt is ahead of this resistor.')
    passive('C','10nF',name+'_LIMIT',name+'_PLUS',page,'1%',
        'C0G, >=25 V. Input DC blocking; with 22 MΩ fc≈0.723 Hz.')
    passive('R','22M',name+'_PLUS','VMID',page,'1%',
        'Input bias return. Clean thoroughly; PCB leakage is a qualification gate.')
    passive('R','1k',name+'_MINUS','VMID',page,'0.1%')
    passive('R','10k',name+'_PRE',name+'_MINUS',page,'0.1%')
    amp(ic,unit,name+'_PLUS',name+'_MINUS',name+'_PRE','Input preamp, gain 11',page)
    tp(name+'_PRE',page)

for ch in range(1,9):
    name=f'CH{ch}'; page=f'afe_ch{ch}'; bank=(ch-1)//4; unit=(ch-1)%4
    preamp(name,f'FFC_CH{ch}',101+bank,unit,page)
    passive('C','10nF',name+'_PRE',name+'_HP_CH',page,'1%',
        'C0G, >=25 V. Pair with corresponding REF high-pass capacitor; mismatch limits CMRR.')
    passive('R','51.1k',name+'_HP_CH',name+'_DIFF_MINUS',page,'0.1%')
    diff_series(name+'_HP',name+'_DIFF_MINUS',name+'_DIFF_FB_MID',page)
    passive('C','10nF','REF_PRE',name+'_HP_REF',page,'1%',
        'C0G, >=25 V. Match CH/REF paths.')
    passive('R','51.1k',name+'_HP_REF',name+'_DIFF_PLUS',page,'0.1%')
    diff_series(name+'_DIFF_PLUS','VMID',name+'_DIFF_BAL_MID',page)
    amp(103+bank,unit,name+'_DIFF_PLUS',name+'_DIFF_MINUS',name+'_HP',
        'Matched differential HP: REF minus CH, gain 35.577, fc 311.46 Hz',page)
    tp(name+'_HP',page)
    prior=name+'_HP'
    for section, feedback in [(1,'1.5k'),(2,'12.4k')]:
        p=f'{name}_LP{section}'
        outnet=f'AFE_OUT_{ch}' if section==2 else p+'_OUT'
        passive('R','22.6k',prior,p+'_A',page,'1%')
        passive('R','22.6k',p+'_A',p+'_PLUS',page,'1%')
        passive('C','1nF',p+'_A',outnet,page,'1%',
            'C0G, >=25 V. Sallen-Key feedback capacitor connects to section OUTPUT.')
        passive('C','1nF',p+'_PLUS','VMID',page,'1%',
            'C0G, >=25 V. AC return is VMID, not a mismatched rail.')
        passive('R','10k',p+'_MINUS','VMID',page,'0.1%')
        passive('R',feedback,outnet,p+'_MINUS',page,'0.1%')
        amp(105+bank if section==1 else 107+bank,unit,p+'_PLUS',p+'_MINUS',outnet,
            f'Sallen-Key section {section}, gain {1.15 if section==1 else 2.24}, '+
            ('low Q' if section==1 else 'high Q; final ADC driver'),page)
        prior=outnet
    tp(prior,page)

preamp('REF','FFC_REF',109,0,'afe_shared')
amp(109,1,'VMID_RAW','VMID_BUF','VMID_BUF','VMID unity follower; feedback before isolation','afe_shared')
passive('R','47','VMID_BUF','VMID','afe_shared','1%',
    'Isolates VMID buffer from 4.7 µF; output feedback is VMID_BUF.')
passive('C','4.7uF','VMID','GND','afe_shared','20%',
    'X7R >=10 V; budget DC bias derating; do not use effective capacitance <2 µF.')
amp(109,2,'VMID_RAW','AFE_SPARE_C','AFE_SPARE_C','Unused unit, stable follower','afe_shared')
amp(109,3,'VMID_RAW','AFE_SPARE_D','AFE_SPARE_D','Unused unit, stable follower','afe_shared')
tp('VMID','afe_shared'); tp('REF_PRE','afe_shared')
for ic in range(101,110):
    components.append(amps[ic])
    amps[ic]['unit_blocks'].append(dict(unit=5,pins=['3','10'],channel=None,
        stage='power',page='afe_shared'))
    passive('C','100nF','AVDD_3V0','GND','afe_shared','10%',
        f'X7R >=10 V; local bypass adjacent to U{ic} V+ / GND pins.')
passive('C','4.7uF','AVDD_3V0','GND','afe_shared','20%',
    'Local analog-bank bypass; complements regulator output capacitors.')

for component in components:
    if component['ref'].startswith('C') and component['value']=='10nF':
        component.update(mpn='C0603C103F3GACTU',lcsc='C2167903',package='0603')

io=[f'FFC_CH{i}' for i in range(1,9)]+['FFC_REF']
for n in range(3):
    pins={'3':'GND','8':'GND'}
    for j,pin in enumerate([1,2,4,5]):
        idx=4*n+j
        pins[str(pin)] = io[idx] if idx<len(io) else f'NC_ESD_{n}_{j}'
    for pin in [6,7,9,10]:pins[str(pin)]=f'NC_ESD_{n}_PIN{pin}'
    components.append(dict(ref=f'U{110+n}',value='TPD4E05U06DQAR',
        mpn='TPD4E05U06DQAR',lcsc='C138714',package='USON-10_DQA_1x2.5mm_P0.5mm',
        pins=pins,pinfunctiontypes={p:('no_connect' if pins[p].startswith('NC_') else 'power_in' if p in ['3','8'] else 'passive') for p in pins},
        page='afe_shared',notes='Unidirectional connector ESD; 0.5 pF typical per line; not a 3 V precision rail clamp. Unused IO and NC pins remain unconnected.'))

allnets=sorted({net for c in components for net in c['pins'].values() if not net.startswith('NC_')})
data=dict(schema_version='1.0',status='Candidate for review and qualification; not fabrication released',
    date='2026-10-01',components=components,nets=allnets,
    interfaces={'power':['AVDD_3V0','GND','VMID_RAW'],
        'input':io,'output':[f'AFE_OUT_{i}' for i in range(1,9)]},
    electrical_conventions={'GND':'One common electrical net; analog placement/return partition, not disconnected AGND/DGND islands',
        'VMID':'1.5 V nominal, buffered from power-sheet VMID_RAW',
        'output_polarity':'Positive REF-minus-CH; software can invert samples'},
    sourcing_note='Active exact order codes verified on LCSC. Passive MPN/LCSC fields require root BOM sourcing before release; values/tolerances are circuit requirements.')
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'afe-pin-nets.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(f"Wrote {len(components)} components, {len(allnets)} nets")

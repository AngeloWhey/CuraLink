"""Create deterministic MCU-local placement overrides from a native snapshot.

This script plans placement only, using the actual footprint courtyard geometry
in board-placement-geometry.json. It never edits the canonical PCB or circuit.
The corresponding native board copy is made by apply_mcu_local.py.
"""
from pathlib import Path
import json
import math

HERE=Path(__file__).resolve().parent
REV=HERE.parent
data=json.loads((HERE/'figures/board-placement-geometry.json').read_text())
fps={x['ref']:x for x in data['footprints']}
canonical=json.loads((REV/'components-merged.json').read_text())['components']
movable={c['ref'] for c in canonical if c.get('page')=='MCU_ACQUISITION' and c.get('kind')!='flag'}|{'C410','C411'}
assert len(movable)==61,len(movable)  # 59 acquisition-page parts plus both RF supply bypasses.
placements={}
occupied=[]
GAP=.075

def rotate(point,angle):
    a=-math.radians(angle);x,y=point
    return (x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a))

def local(ref,p):
    fp=fps[ref];x,y=fp['position']
    return rotate((p[0]-x,p[1]-y),-fp['angle'])

def pad_local(ref,num):
    return local(ref,next(p for p in fps[ref]['pads'] if p['number']==str(num))['center'])

def pad_at(ref,num,x,y,angle):
    px,py=rotate(pad_local(ref,num),angle)
    return (x+px,y+py)

def actual_pad(ref,num):
    p=placements.get(ref)
    if p:return pad_at(ref,num,p['x_mm'],p['y_mm'],p['rotation_deg'])
    return next(x['center']for x in fps[ref]['pads']if x['number']==str(num))

local_courts={}
for ref,fp in fps.items():
    points=[local(ref,p)for g in fp['graphics']if g['layer']=='F.CrtYd'for p in g['points']]
    if not points:raise ValueError('Missing native courtyard '+ref)
    local_courts[ref]=points

def bounds(ref,x,y,a):
    pts=[rotate(p,a)for p in local_courts[ref]]
    # Cached outline vertices omit the native courtyard bounding-box stroke
    # envelope; add 0.05 mm per side before collision planning.
    return (x+min(p[0]for p in pts)-.05,y+min(p[1]for p in pts)-.05,
            x+max(p[0]for p in pts)+.05,y+max(p[1]for p in pts)+.05)

def clear(box):
    return all(box[2]+GAP<=b[0] or b[2]+GAP<=box[0] or
               box[3]+GAP<=b[1] or b[3]+GAP<=box[1]for _,b in occupied)

for ref,fp in fps.items():
    if ref not in movable:
        b=bounds(ref,*fp['position'],fp['angle'])
        if b[2]>=59 and b[0]<=80 and b[3]>=19 and b[1]<=50:
            occupied.append((ref,b))

def commit(ref,x,y,a,reason):
    b=bounds(ref,x,y,a)
    if not clear(b):raise ValueError('Collision '+ref)
    if not(60<=b[0] and b[2]<=79 and 20<=b[1] and b[3]<=49):
        raise ValueError('Outside authorized MCU placement region '+ref+str(b))
    occupied.append((ref,b))
    placements[ref]={'x_mm':round(x,6),'y_mm':round(y,6),'rotation_deg':a,
                     'reason':reason,'courtyard_bounds_mm':[round(v,6)for v in b]}

commit('U401',69,29,0,'MCU center moved to provide local bypass/filter space on every side')

def place(ref,targets,reason,region=(60,20,79,49),bias=None,angles=(0,90,180,270)):
    # Each target is (part pad number, desired global point, weight).
    candidates=[]
    l,t,r,b=region
    for angle in angles:
        offsets=[rotate(pad_local(ref,n),angle)for n,_,_ in targets]
        for xi in range(math.ceil(l*4),math.floor(r*4)+1):
            x=xi/4
            for yi in range(math.ceil(t*4),math.floor(b*4)+1):
                y=yi/4
                score=sum(w*math.dist((x+o[0],y+o[1]),p)for o,(_,p,w)in zip(offsets,targets))
                if bias:score+=bias(x,y,angle)
                candidates.append((score,x,y,angle))
    candidates.sort()
    for score,x,y,angle in candidates:
        bb=bounds(ref,x,y,angle)
        if bb[0]<l or bb[2]>r or bb[1]<t or bb[3]>b:continue
        if clear(bb):
            commit(ref,x,y,angle,reason)
            return
    raise RuntimeError('No legal placement '+ref)

# Closest signal-side pad comes first; all bypass ground pads still require
# short local copper/ground vias when the parent routes the new placement.
for ref,x,y,angle,pin in [('C410',71,24,90,39),('C411',69.5,24,90,42),
                         ('C404',68.25,24,90,43),('C408',66.75,23.25,90,44)]:
    commit(ref,x,y,angle,f'Local top-edge bypass/output capacitor at U401 physical pin {pin}')
for ref,pin in [('C409',38),('C406',6),('C401',11),('C402',22),('C403',35)]:
    place(ref,[('1',actual_pad('U401',pin),1)],f'Local bypass/output capacitor at U401 physical pin {pin}')

place('C407',[('1',actual_pad('U401',6),1)],'VDDA bulk capacitance after local100nF bypass')

# Put RC shunt capacitors first, then their test lands, then series isolation.
# The lower two ADC pins can fan out below the package as well as to its left.
adc_pins=[3,4,5,7,10,12,13,14]
for i,pin in enumerate(adc_pins):
    ref='C'+str(413+i)
    place(ref,[('1',actual_pad('U401',pin),1)],f'ADC{i+1} shunt capacitor localized to physical pin {pin}',
          region=(60,23,68 if i>=6 else 65.05,38))
for i in range(8):
    cap='C'+str(413+i);ref='TP'+str(410+i)
    place(ref,[('1',actual_pad(cap,1),1)],f'Local ADC{i+1} test land; keep branch at capacitor node',
          region=(60,23,69,40))
for i in range(8):
    cap='C'+str(413+i);ref='R'+str(401+i)
    place(ref,[('2',actual_pad(cap,1),1)],f'ADC{i+1} series resistor beside its shunt capacitor',
          region=(60,23,68,41),bias=lambda x,y,a:max(0,x-64)*.1)

# Oscillator geometry targets actual terminal pins, not body centers.
place('Y401',[('1',actual_pad('U401',41),1),('3',actual_pad('U401',40),1)],
      'HSE crystal loop close to top-edge oscillator pins',region=(63,20,73,25.05))
place('Y402',[('1',actual_pad('U401',17),1),('2',actual_pad('U401',16),1)],
      'LSE crystal below bottom-edge oscillator pins',region=(65,32.95,74,40))
place('C421',[('1',actual_pad('Y402',1),1)],'LSE input load capacitor at crystal terminal1',region=(65,32.95,75,41))
place('C422',[('1',actual_pad('Y402',2),1)],'LSE output load capacitor at crystal terminal2',region=(65,32.95,75,41))

# Bulk supplies and debug access are placed after sensitive analog/clock loops.
place('C405',[('1',actual_pad('C402',1),1)],'MCU supply bulk capacitor',region=(69,33,79,41))
place('C412',[('1',(71,44),1)],'Debug supply local capacitor',region=(64,40,79,49))
for ref,x,y,a in [('J402',70,42,0),('J401',70,44,0),('J403',70,46,0)]:
    if clear(bounds(ref,x,y,a)):
        commit(ref,x,y,a,'Bench debug pogo/wire pad access')
    else:place(ref,[('1',(x,y),1)],'Bench debug pogo/wire pad access',region=(63,40,79,49),angles=(0,))
for ref,point in [('R409',(74,45)),('R410',(71,47)),('R411',(68,47)),('R412',(74,47)),
                  ('R413',(65,46)),('R414',(71,48)),('R415',(77,46)),('R416',(63,42))]:
    place(ref,[('1',point,1)],'Debug/control passive; outside oscillator and ADC local loops',region=(60,40,79,49))
for ref in sorted(movable-set(placements)):
    old=fps[ref]['position']
    place(ref,[('1',old,1)],'Debug/control test access',region=(60,40,79,49),angles=(0,))

assert set(placements)==movable
measurements={}
for ref,pin in [('C410',39),('C411',42),('C408',44),('C409',38),('C406',6),
                ('C407',6),('C401',11),('C402',22),('C403',35),('C404',43)]:
    measurements[ref]={'U401_pin':pin,'signal_pad_to_pin_mm':round(math.dist(actual_pad(ref,1),actual_pad('U401',pin)),4)}
adc=[]
for i,pin in enumerate(adc_pins):
    cap='C'+str(413+i);res='R'+str(401+i);tp='TP'+str(410+i)
    adc.append({'channel':i+1,'mcu_pin':pin,'capacitor':cap,'resistor':res,'testpoint':tp,
        'capacitor_signal_pad_to_adc_pin_mm':round(math.dist(actual_pad(cap,1),actual_pad('U401',pin)),4),
        'resistor_output_pad_to_cap_signal_pad_mm':round(math.dist(actual_pad(res,2),actual_pad(cap,1)),4),
        'testpoint_pad_to_cap_signal_pad_mm':round(math.dist(actual_pad(tp,1),actual_pad(cap,1)),4)})
report={'status':'Engineering placement candidate, not fabrication release',
        'checked_date':'2026-10-02','timezone':'America/New_York',
        'source_snapshot_sha256':data['board_sha256'],'moved_reference_count':len(placements),
        'authorized_region_mm':[60,20,79,49],'courtyard_separation_margin_mm':GAP,
        'overrides':placements,'bypass_measurements':measurements,'adc_measurements':adc,
        'limits':['These are pad-center Euclidean distances, not routed lengths or measured electrical performance.',
                  'Copper/clearance/mask/oscillator RF rules require native DRC and manual routing review.',
                  'The original board and canonical circuit remain untouched.']}
(HERE/'mcu-placement-overrides.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'moved':len(placements),'bypasses':measurements,'adc':adc},indent=2))

"""Generate project footprints from retained manufacturer land drawings.

Source coordinates and assembly assumptions are documented in footprint-review.md.
This script writes only its five owned footprint files and a geometry manifest.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / 'hardware/rev-a/pcb/footprints/CuraLink.pretty'
OUT.mkdir(parents=True, exist_ok=True)
records = []

def fmt(value): return f'{value:.6f}'.rstrip('0').rstrip('.') if isinstance(value,float) else str(value)

def header(name, description, reference_y):
    return [f'(footprint "{name}" (version 20241229) (generator "curalink_verified_land_drawing") (layer "F.Cu")',
        f'  (descr "{description}")', '  (attr smd)',
        f'  (property "Reference" "REF**" (at 0 {reference_y}) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.1))))',
        f'  (property "Value" "{name}" (at 0 {-reference_y}) (layer "F.Fab") (hide yes) (effects (font (size 0.7 0.7) (thickness 0.1))))']

def rect(lines, x1,y1,x2,y2,layer='F.Fab',width=0.1):
    lines.append(f'  (fp_rect (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) (stroke (width {fmt(width)}) (type solid)) (fill none) (layer "{layer}"))')

def pad(lines, name,x,y,w,h,shape='rect',layers=('F.Cu','F.Paste','F.Mask'),mask=None):
    ls=' '.join('"'+s+'"' for s in layers)
    extra='' if mask is None else f' (solder_mask_margin {fmt(mask)})'
    lines.append(f'  (pad "{name}" smd {shape} (at {fmt(x)} {fmt(y)}) (size {fmt(w)} {fmt(h)}) (layers {ls}){extra})')

def finish(name,lines,pad_data,notes):
    lines.append(')'); target=OUT/(name+'.kicad_mod'); target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    records.append({'name':'CuraLink:'+name,'file':target.relative_to(ROOT).as_posix(),
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'physical_pads':pad_data,'notes':notes})

name='STM32WBA52CGU6'
lines=header(name,'ST A0B9_FP_V2: 7x7 UFQFPN48, 0.5 pitch, 0.55x0.30 lands, EP5.6. Paste windows are engineering assumption.',-4.2)
rect(lines,-3.5,-3.5,3.5,3.5)
rect(lines,-3.9,-3.9,3.9,3.9,'F.CrtYd',0.05)
lines.append('  (fp_circle (center -3.55 -3.55) (end -3.45 -3.55) (stroke (width 0.1) (type solid)) (fill solid) (layer "F.SilkS"))')
pads=[]
for i in range(12):
    for number,x,y,w,h in [(i+1,-3.375,-2.75+i*.5,.55,.3), (i+13,-2.75+i*.5,3.375,.3,.55),
            (i+25,3.375,2.75-i*.5,.55,.3),(i+37,2.75-i*.5,-3.375,.3,.55)]:
        pad(lines,str(number),x,y,w,h)
        pads.append({'pad':str(number),'x_mm':x,'y_mm':y,'w_mm':w,'h_mm':h})
pad(lines,'49',0,0,5.6,5.6,layers=('F.Cu','F.Mask'))
pads.append({'pad':'49','x_mm':0,'y_mm':0,'w_mm':5.6,'h_mm':5.6})
# Same 16-window paste choice as official KiCad generic EP5.6 package: about65% area.
for x in [-2.1,-.7,.7,2.1]:
    for y in [-2.1,-.7,.7,2.1]: pad(lines,'',x,y,1.13,1.13,layers=('F.Paste',))
finish(name,lines,pads,['Exact ST peripheral copper/EP drawing; paste-window and mask process require assembly approval.',
    'No drill pattern invented: add audited ground stitching/EP vias in PCB after paste/via-fill decision.'])

name='MLPF-WB-04D3'
lines=header(name,'ST CSPG6: x pitch0.500 y pitch0.577. Copper0.320, mask0.220, square paste0.220 per rendered Fig15; check3mil stencil process.',-1.25)
rect(lines,-.5,-.8,.5,.8)
rect(lines,-.75,-1.05,.75,1.05,'F.CrtYd',0.05)
lines.append('  (fp_circle (center -0.48 -0.89) (end -0.43 -0.89) (stroke (width 0.07) (type solid)) (fill solid) (layer "F.SilkS"))')
pads=[]
for col,x in [('A',-.25),('B',.25)]:
    for row,y in [(1,-.577),(2,0),(3,.577)]:
        number=f'{col}{row}'; pad(lines,number,x,y,.32,.32,'circle',('F.Cu','F.Mask'),mask=-.05)
        pad(lines,'',x,y,.22,.22,layers=('F.Paste',))
        pads.append({'pad':number,'x_mm':x,'y_mm':y,'copper_diameter_mm':.32,'mask_diameter_mm':.22,'paste_square_mm':.22})
finish(name,lines,pads,['A1IN,A2GND,A3OUT,B1/B2/B3GND top view; dot identifiesA1.',
    'Figure15 visual inspection supersedes misleading extracted label order.',
    'No guessed L2 exclusion: component-specific RF stack/ground adaptation remains OPEN.'])

name='Johanson_2450AT18A0100001E'
lines=header(name,'JohansonRev4p3 lands: innergap2.6 outerspan4.2 height1.6. Pad1FEED left, pad2isolatedNC anchor right. Antenna clearance belongs to board.',-1.4)
rect(lines,-1.6,-.8,1.6,.8)
rect(lines,-2.35,-1.05,2.35,1.05,'F.CrtYd',0.05)
lines.append('  (fp_circle (center -2.27 -0.97) (end -2.20 -0.97) (stroke (width 0.1) (type solid)) (fill solid) (layer "F.SilkS"))')
pad(lines,'1',-1.7,0,.8,1.6);pad(lines,'2',1.7,0,.8,1.6)
finish(name,lines,[{'pad':'1','x_mm':-1.7,'y_mm':0,'w_mm':.8,'h_mm':1.6,'function':'FEED'},
    {'pad':'2','x_mm':1.7,'y_mm':0,'w_mm':.8,'h_mm':1.6,'function':'ISOLATED_NC_ANCHOR'}],
    ['Pad2 must be physically soldered, neverGND.', 'Place board-corner6.5mm clearance explicitly at final rotation; no universal center-based keepout invented.'])

name='FFC18P_HYH2.0'
lines=header(name,'SHOUHAN exact18pin land drawing: pitch0.5 contact0.3x1.2 anchor1.8x2.0. Harness pin1 convention/actuator clearance and housing pose require final audit.',-1.15)
# Housing-envelope pose is only a placement envelope; authoritative geometry is solder lands.
rect(lines,-6.225,.38,6.225,5.70)
rect(lines,-7.05,-.85,7.05,6.2,'F.CrtYd',0.05)
lines.append('  (fp_text user "PIN1 / VERIFY CABLE" (at -3 -1.8) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))')
pads=[]
for i in range(18):
    x=-4.25+i*.5;pad(lines,str(i+1),x,0,.3,1.2)
    pads.append({'pad':str(i+1),'x_mm':x,'y_mm':0,'w_mm':.3,'h_mm':1.2})
for number,x in [('MP1',-5.9),('MP2',5.9)]:
    pad(lines,number,x,3.15,1.8,2.0)
    pads.append({'pad':number,'x_mm':x,'y_mm':3.15,'w_mm':1.8,'h_mm':2.0})
finish(name,lines,pads,['Center-span8.50mm follows18pins/pitch; sourcePCB usesB label ambiguously alongsideDIMA/DIMB table.',
    'Anchorx follows2.55mm fromanchorouteredge tofirstsignalcenter; anchory follows4.75mm fromsignallandtop toanchorbottom.',
    'Makerdrawing has no contactpin1number: left-right numbering is project harness convention and needs continuity test.',
    'F.Fab housing pose/courtyard are engineering placement envelope, not a fully dimensioned manufacturer model; actuator/cable clearance OPEN.'])

name='NDK_NX2016SA_2.0x1.6mm'
lines=header(name,'NDK1703C typicalland:0.85x0.75, centerpitch1.35x1.05;1bottomleft2bottomright3topright4topleft.',-1.35)
rect(lines,-1,-.8,1,.8)
rect(lines,-1.3,-1.15,1.3,1.15,'F.CrtYd',0.05)
pads=[]
for number,x,y in [('1',-.675,.525),('2',.675,.525),('3',.675,-.525),('4',-.675,-.525)]:
    pad(lines,number,x,y,.85,.75)
    pads.append({'pad':number,'x_mm':x,'y_mm':y,'w_mm':.85,'h_mm':.75})
finish(name,lines,pads,['Pins2/4arecaseGND;1/3crystal. Land dimensions exactmaker typical drawing; reflow/mask/paste finalaudit.'])

(HERE/'critical-footprint-manifest.json').write_text(json.dumps({'checked_date':'2026-10-02','coordinate_view':'PCBtop, mm, before placement rotation',
    'status':'Manufacturer-drawing-based lands; PCB RF adaptation, FFC orientation and assembly process qualification remain OPEN',
    'footprints':records},indent=2)+'\n',encoding='utf-8')
print('\n'.join(row['name'] for row in records))

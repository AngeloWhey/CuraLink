"""Create the two root-requested AFE footprints from verified TI reference lands.

TI reference lands are used deliberately, rather than the differently sized
IPC-generated RUC footprint or the generic USON footprint for another IC.
"""
from pathlib import Path
import hashlib
import json
import uuid
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Polygon

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
DEST=ROOT/'hardware/rev-a/pcb/footprints/CuraLink.pretty'
DEST.mkdir(parents=True,exist_ok=True)

def uid():return str(uuid.uuid4())
def fnum(x):return f'{x:g}'
def line(a,b,layer,width):
    return f'  (fp_line (start {a[0]:g} {a[1]:g}) (end {b[0]:g} {b[1]:g}) (stroke (width {width:g}) (type solid)) (layer "{layer}") (uuid "{uid()}"))\n'
def rect(a,b,layer,width):
    return f'  (fp_rect (start {a[0]:g} {a[1]:g}) (end {b[0]:g} {b[1]:g}) (stroke (width {width:g}) (type solid)) (fill none) (layer "{layer}") (uuid "{uid()}"))\n'
def header(name,descr,url,ref_y,value_y):
    return f'''(footprint "{name}"
  (version 20241229) (generator "pcbnew") (generator_version "9.0")
  (layer "F.Cu") (descr "{descr}") (tags "CuraLink TI manufacturer reference land pattern")
  (property "Reference" "REF**" (at 0 {ref_y:g}) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.12))))
  (property "Value" "{name}" (at 0 {value_y:g}) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1))))
  (property "Datasheet" "{url}" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1))))
  (attr smd)
'''
def pad(n,x,y,w,h,round_ratio=.25,layers='"F.Cu" "F.Paste" "F.Mask"'):
    return f'  (pad "{n}" smd roundrect (at {x:g} {y:g}) (size {w:g} {h:g}) (layers {layers}) (roundrect_rratio {round_ratio:g}) (solder_mask_margin 0.05) (uuid "{uid()}"))\n'
def poly(points,layer,width,fill='none'):
    return '  (fp_poly (pts '+''.join(f'(xy {x:g} {y:g}) 'for x,y in points)+f') (stroke (width {width:g}) (type solid)) (fill {fill}) (layer "{layer}") (uuid "{uid()}"))\n'

ruc=[]
for pin,y in zip(range(1,6),[-.8,-.4,0,.4,.8]):ruc.append({'number':pin,'x':-.9,'y':y,'w':.6,'h':.2})
for pin,x in [(6,-.2),(7,.2)]:ruc.append({'number':pin,'x':x,'y':.9,'w':.2,'h':.6})
for pin,y in zip(range(8,13),[.8,.4,0,-.4,-.8]):ruc.append({'number':pin,'x':.9,'y':y,'w':.6,'h':.2})
for pin,x in [(13,.2),(14,-.2)]:ruc.append({'number':pin,'x':x,'y':-.9,'w':.2,'h':.6})
name='TLV_RUC14_X2QFN_2x2mm_NoEP'
text=header(name,'TI RUC0014A, reference lands 0.6x0.2mm; no exposed thermal pad; top-view pin1 upper-left',
            'https://www.ti.com/lit/ds/symlink/tlv9004.pdf',-1.95,1.95)
text+=poly([(-1,-.7),(-.7,-1),(1,-1),(1,1),(-1,1),(-1,-.7)],'F.Fab',.1)
text+=rect((-1.5,-1.5),(1.5,1.5),'F.CrtYd',.05)
for y in [-1.42,1.42]:text+=line((-1.1,y),(1.1,y),'F.SilkS',.12)
for x in [-1.42,1.42]:text+=line((x,-1.1),(x,1.1),'F.SilkS',.12)
text+=poly([(-1.42,-1.42),(-1.16,-1.42),(-1.42,-1.16)],'F.SilkS',.1,'yes')
for d in ruc:text+=pad(d['number'],d['x'],d['y'],d['w'],d['h'])
text+=')\n'
(DEST/(name+'.kicad_mod')).write_text(text)

dqa=[]
for pin,y in zip(range(1,6),[-1,-.5,0,.5,1]):dqa.append({'number':pin,'x':-.4175,'y':y,'w':.565,'h':.4 if pin==3 else .2})
for pin,y in zip(range(6,11),[1,.5,0,-.5,-1]):dqa.append({'number':pin,'x':.4175,'y':y,'w':.565,'h':.4 if pin==8 else .2})
name='TPD4E05U06DQA_USON10_1x2.5mm'
text=header(name,'TI DQA0010A reference lands; signals0.565x0.2mm grounds3/8 0.565x0.4mm; DQA A/B variants manufacturer-compatible; all mechanical NC lands included',
            'https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf',-1.95,1.95)
text+=poly([(-.5,-1),(-.25,-1.25),(.5,-1.25),(.5,1.25),(-.5,1.25),(-.5,-1)],'F.Fab',.1)
text+=rect((-.95,-1.55),(.95,1.55),'F.CrtYd',.05)
text+=line((-.5,-1.44),(.5,-1.44),'F.SilkS',.12)
text+=line((-.5,1.44),(.5,1.44),'F.SilkS',.12)
text+=poly([(-.9,-1.44),(-.65,-1.44),(-.9,-1.2)],'F.SilkS',.1,'yes')
for d in dqa:
    ground=d['number']in[3,8]
    layers='"F.Cu" "F.Mask"'if ground else'"F.Cu" "F.Paste" "F.Mask"'
    text+=pad(d['number'],d['x'],d['y'],d['w'],d['h'],.125 if ground else.25,layers)
    if ground:
        # Separate unnumbered paste-only apertures implement TI's 0.36mm height.
        text+=pad('',d['x'],d['y'],.565,.36,.05/.36,'"F.Paste"')
text+=')\n'
(DEST/(name+'.kicad_mod')).write_text(text)

audit={'date':'2026-10-02','status':'Manufacturer reference-land geometry audited; actual pcbnew parsing/DRC recorded separately',
    'view':'Footprint is TOP view; TI package outline bottom view was mirrored appropriately; do not mirror top assembly placements again.',
    'units':'mm','mask_expansion_mm':.05,
    'mask_note':'NSMD openings; RUC expansion<=0.05mm and DQA<=0.07mm reference limits; actual board mask rules must retain webs.',
    'sources':[{'url':'https://www.ti.com/lit/ds/symlink/'+n+'.pdf',
        'local':f'hardware/rev-a/ltspice/sources/{n}.pdf',
        'sha256':hashlib.sha256((ROOT/f'hardware/rev-a/ltspice/sources/{n}.pdf').read_bytes()).hexdigest()}
        for n in ['tlv9004','tlv9054','tpd4e05u06']],
    'RUC':{'footprint':'CuraLink:TLV_RUC14_X2QFN_2x2mm_NoEP','drawing':'RUC0014A4220584/A05/2019',
        'TI_PDF_pages':[107,108,109],'TLV9054_PDF_pages':[85,86,87],
        'body_nominal_mm':[2,2],'body_max_mm':[2.1,2.1],
        'height_max_mm':.4,'exposed_pad':False,'numbered_Cu_pads':14,'pads':ruc,
        'courtyard_mm':[3,3],'courtyard_note':'0.3mm beyond land extent, chosen assembly clearance; not a TI package dimension',
        'paste':'Same as copper reference aperture,14x0.6x0.2mm, radius0.05mm',
        'pin_functions':{'1':'IN_A-','2':'IN_A+','3':'V+','4':'IN_B+','5':'IN_B-',
            '6':'OUT_B','7':'OUT_C','8':'IN_C-','9':'IN_C+','10':'V-',
            '11':'IN_D+','12':'IN_D-','13':'OUT_D','14':'OUT_A'},
        'official_KiCad_comparison':{'path':'Package_DFN_QFN:Texas_S-PX2QFN-14',
            'result':'Pin positions/order family correct, noEP; IPC-generated0.875x0.2mm lands atsidecenters±0.9375mm differ fromTI reference0.6x0.2at±0.9; custom usesTI reference'}},
    'DQA':{'footprint':'CuraLink:TPD4E05U06DQA_USON10_1x2.5mm','drawing':'DQA0010A4220328/A12/2015',
        'TI_PDF_pages':[28,29,30],'DQA_B_pages':[31,32,33],
        'body_nominal_mm':[1,2.5],'body_max_mm':[1.1,2.6],'height_max_mm':.55,
        'exposed_pad':False,'numbered_Cu_pads':10,'paste_only_unnumbered_pads':2,'pads':dqa,
        'courtyard_mm':[1.9,3.1],
        'paste':'Signals0.565x0.2mm; ground3/8 separate unnumbered F.Paste-only0.565x0.36mm, radius0.05mm, perTI stencil example',
        'pin_functions':{'1':'IO1','2':'IO2','3':'GND','4':'IO3','5':'IO4','6':'NC','7':'NC','8':'GND','9':'NC','10':'NC'},
        'NC_note':'6/7/9/10 have mechanical solder lands but are not signal vias or jumpers; preserve canonical NC nets/no connections.',
        'variant_compatibility':{'url':'https://e2e.ti.com/support/interface-group/interface/f/interface-forum/1384139/tpd4e05u06-what-is-the-correct-package-drawing',
            'manufacturer_statement_paraphrase':'Either DQA0010A or DQA0010B can ship underTPD4E05U06DQAR; TI testedandconfirms either device works on either landpattern. B joinsgroundmetal; Aseparate groundlands usedhere.',
            'note':'No stencil ground-via aperture added; use nearby GNDvias rather than unstated unfilled via-in-paste.'},
        'official_KiCad_comparison':{'path':'Package_SON:USON-10_2.5x1.0mm_P0.5mm',
            'result':'Generic sourcedfromTPD4E02B04, all0.55x0.30lands at±0.385; notsame as selectedpartTI distinct0.565x0.4ground and0.565x0.2signal recommendedlands'}},
    'assembly_gates':['Manufacturer geometry audit does not qualify stencil thickness, solder volume, reflow, exact assembler land acceptance or board solder-mask registration',
        'Root integration must skip unnumbered paste-only pads when mapping electrical pins',
        'No substituted stock SKU/package or unapproved exposed-pad variant is interchangeable solely because body dimensions match']}
(OUT/'footprint-audit.json').write_text(json.dumps(audit,indent=2))

for package,pads,body,court in [('RUC',ruc,(2,2),(3,3)),('DQA',dqa,(1,2.5),(1.9,3.1))]:
    fig,ax=plt.subplots(figsize=(5,5),layout='constrained')
    ax.add_patch(Rectangle((-body[0]/2,-body[1]/2),*body,fill=False,ls='--',ec='grey'))
    ax.add_patch(Rectangle((-court[0]/2,-court[1]/2),*court,fill=False,ls=':',ec='purple'))
    for d in pads:
        ax.add_patch(FancyBboxPatch((d['x']-d['w']/2,d['y']-d['h']/2),d['w'],d['h'],
            boxstyle='round,pad=0,rounding_size=0.05',fc='#dc9339',ec='black',lw=.7))
        ax.text(d['x'],d['y'],str(d['number']),ha='center',va='center',fontsize=10)
    ax.set_aspect('equal');ax.set_xlim(-1.8,1.8);ax.set_ylim(1.8,-1.8)
    ax.set(xlabel='X (mm)',ylabel='Y (mm; KiCad down-positive)',title=package+' reference lands — TOP view')
    ax.grid(alpha=.25)
    fig.savefig(OUT/(package.lower()+'-footprint.png'),dpi=180);plt.close(fig)
print('Created root-requested custom footprints in',DEST)

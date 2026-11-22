"""Run in WSL KiCad Python; prepare used footprints and physical assignments.

Canonical circuit JSON is read-only. Only used official standards are copied.
Critical maker-land customs belong to their audit scripts; they are not regenerated.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import pcbnew

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'hardware/rev-a/components-merged.json'
PCB=ROOT/'hardware/rev-a/pcb'
LIB=PCB/'footprints/CuraLink.pretty'
LIB.mkdir(parents=True,exist_ok=True)
STANDARD=Path(os.environ.get('CURALINK_KICAD_FOOTPRINT_DIR',
    os.environ.get('KICAD9_FOOTPRINT_DIR', os.environ.get('KICAD_FOOTPRINT_DIR',
        str(Path(os.environ.get('ProgramFiles', 'C:/Program Files'))/'KiCad/9.0/share/kicad/footprints')
        if os.name=='nt' else '/usr/share/kicad/footprints'))))
components=json.loads(SOURCE.read_text(encoding='utf-8'))['components']
physical=[c for c in components if c.get('kind')!='flag']
if len(physical)!=446: raise ValueError(f'Expected446 physical references; got{len(physical)}')
library_records={}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def copy_standard(folder,name,modified_name=None,modification=None):
    key=modified_name or name
    if key in library_records:return key
    src=STANDARD/(folder+'.pretty')/(name+'.kicad_mod')
    if not src.exists():raise FileNotFoundError(src)
    target=LIB/(key+'.kicad_mod')
    if modification:
        fp=pcbnew.FootprintLoad(str(src.parent),name)
        if key=='SS14_SMA_A1K2':
            for p in fp.Pads():
                if p.GetNumber()=='1':p.SetNumber('2')
                elif p.GetNumber()=='2':p.SetNumber('1')
        elif key=='UFL_Hirose_1SIG_2GND_3GND':
            grounds=sorted((p for p in fp.Pads() if p.GetNumber()=='2'),key=lambda p:p.GetPosition().y)
            if len(grounds)!=2:raise ValueError('Unexpected official U.FL shell pads')
            grounds[1].SetNumber('3')
            # Hirose permits insulation in the central no-conductive-trace
            # region. The extra mask opening in the official library joins
            # the signal and shell mask openings and produces two bridge
            # errors. Keep the three pad mask/paste openings and copper
            # keepout; remove only this independent mask rectangle.
            mask_rectangles=[g for g in fp.GraphicalItems()
                             if hasattr(g,'GetShape') and g.GetLayer()==pcbnew.F_Mask
                             and g.GetShape()==pcbnew.SHAPE_T_RECT]
            if len(mask_rectangles)!=1:raise ValueError('Unexpected official U.FL mask rectangle count')
            g=mask_rectangles[0]
            coordinates=tuple(round(v/1_000_000,3) for v in
                              [g.GetStart().x,g.GetStart().y,g.GetEnd().x,g.GetEnd().y])
            if coordinates!=(-.515,-.94,1.575,.94):
                raise ValueError('Unexpected official U.FL mask rectangle bounds '+str(coordinates))
            # Remove the corresponding serialized block after native save.
            # pcbnew 9 SWIG can invalidate its plugin proxy after deletion of
            # a standalone footprint graphic; avoid that ownership edge case.
        else:raise ValueError(key)
        fp.SetFPID(pcbnew.LIB_ID('CuraLink',key))
        pcbnew.FootprintSave(str(LIB),fp)
        if key=='UFL_Hirose_1SIG_2GND_3GND':
            text=target.read_text()
            removed=0
            cursor=0
            while True:
                start=text.find('(fp_rect',cursor)
                if start<0:break
                depth=0
                end=start
                for end in range(start,len(text)):
                    depth+=int(text[end]=='(')-int(text[end]==')')
                    if depth==0:break
                block=text[start:end+1]
                if '(layer "F.Mask")' in block:
                    text=text[:start]+text[end+1:]
                    removed+=1
                    cursor=start
                else:cursor=end+1
            if removed!=1:raise ValueError('Unexpected serialized U.FL mask rectangle count')
            target.write_text(text)
    else:shutil.copyfile(src,target)
    library_records[key]={'name':'CuraLink:'+key,'source_type':'official_kicad_standard_modified' if modification else 'official_kicad_standard',
        'source_library':folder+':'+name,'source_path':str(src),'source_sha256':sha(src),
        'source_url':'https://gitlab.com/kicad/libraries/kicad-footprints/-/tree/9.0.9/'+folder+'.pretty',
        'modification':modification,'file':target.relative_to(ROOT).as_posix(),'sha256':sha(target),
        'land_pattern_status':'Standard package lands; exact manufacturer assembly approval remains open'}
    if key=='UFL_Hirose_1SIG_2GND_3GND':
        library_records[key]['adaptation_evidence']={
            'manufacturer_url':'https://datasheet.lcsc.com/datasheet/pdf/ade8681cf25347ad817fa65440db6a2c.pdf?productCode=C88374',
            'manufacturer_page':3,
            'reason':'Hirose permits insulating material in its central no-conductive-trace area; a shared solder-mask opening is not required.',
            'removed_graphic':'Filled F.Mask rectangle (-0.515,-0.940) to (1.575,0.940) mm only.',
            'preserved':'All copper lands, pad F.Mask/F.Paste openings, Fab/courtyard and copper keepout.',
            'audit':'hardware/rev-a/signal-integrity/mcu-rf/placement-review.md'}
    return key

def custom(name,audit,notes):
    if name not in library_records:
        path=LIB/(name+'.kicad_mod')
        if not path.exists():raise FileNotFoundError(path)
        library_records[name]={'name':'CuraLink:'+name,'source_type':'manufacturer_drawing_custom',
            'source_audit':audit,'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'notes':notes,
            'land_pattern_status':'Maker drawing lands; remaining qualification limits documented in source audit'}
    return name

def bare_field(count):
    name=f'CopperField_{count}P_P2mm_D0.9mm'
    if name in library_records:return name
    half=(count-1)*1.0
    lines=[f'(footprint "{name}" (version 20241229) (generator "curalink_bench_copper") (layer "F.Cu")',
        '  (attr exclude_from_pos_files exclude_from_bom)',
        f'  (descr "Proposed bench pogo/wire solder pads,0.9mm copper on2mm pitch; no purchased connector")',
        '  (property "Reference" "REF**" (at 0 -1.2) (layer "F.SilkS") (effects (font (size 0.6 0.6) (thickness 0.1))))',
        f'  (property "Value" "{name}" (at 0 1.2) (layer "F.Fab") (hide yes) (effects (font (size 0.6 0.6) (thickness 0.1))))',
        f'  (fp_rect (start {-half-.7} -.7) (end {half+.7} .7) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))']
    for i in range(count):
        x=-half+i*2
        lines.append(f'  (pad "{i+1}" smd circle (at {x} 0) (size .9 .9) (layers "F.Cu" "F.Mask"))')
    lines.append(')');p=LIB/(name+'.kicad_mod');p.write_text('\n'.join(lines)+'\n')
    library_records[name]={'name':'CuraLink:'+name,'source_type':'proposed_board_copper_field',
        'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p),
        'land_pattern_status':'Engineering bench-pad dimensions; not an assembled connector footprint',
        'notes':'0.9mm round copper,2mm pitch; no paste, excluded PCB BOM/SMT position. External harness remains separately procured.'}
    return name

def testpoint(diameter):
    name=f'TestPoint_Pad_D{diameter:.1f}mm'
    src=STANDARD/'TestPoint.pretty'/(name+'.kicad_mod')
    if src.exists():return copy_standard('TestPoint',name)
    if name in library_records:return name
    radius=diameter/2+.25
    lines=[f'(footprint "{name}" (version 20241229) (generator "curalink_bench_copper") (layer "F.Cu")',
        '  (attr exclude_from_pos_files exclude_from_bom)',
        f'  (descr "Canonical testpoint copper diameter{diameter:.1f}mm; no assembled part or paste")',
        '  (property "Reference" "REF**" (at 0 -1) (layer "F.SilkS") (effects (font (size 0.5 0.5) (thickness 0.08))))',
        f'  (property "Value" "{name}" (at 0 1) (layer "F.Fab") (hide yes) (effects (font (size 0.5 0.5) (thickness 0.08))))',
        f'  (fp_circle (center 0 0) (end {radius} 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))',
        f'  (pad "1" smd circle (at 0 0) (size {diameter} {diameter}) (layers "F.Cu" "F.Mask"))',')']
    p=LIB/(name+'.kicad_mod');p.write_text('\n'.join(lines)+'\n')
    library_records[name]={'name':'CuraLink:'+name,'source_type':'canonical_testpoint_copper',
        'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'land_pattern_status':'No purchased part; diameter follows canonical pad requirement',
        'notes':'KiCad9 library has1.0mm minimum circular testpoint;0.6/0.8mm are project bare-copper implementations. No paste; excluded SMT position/BOM.'}
    return name

critical={
    'STM32WBA52CGU6':('STM32WBA52CGU6','hardware/rev-a/signal-integrity/mcu-rf/footprint-review.md'),
    'MLPF-WB-04D3':('MLPF-WB-04D3','hardware/rev-a/signal-integrity/mcu-rf/footprint-review.md'),
    '2450AT18A0100001E':('Johanson_2450AT18A0100001E','hardware/rev-a/signal-integrity/mcu-rf/footprint-review.md'),
    'NX2016SA-32MHZ-STD-CZS-5':('NDK_NX2016SA_2.0x1.6mm','hardware/rev-a/signal-integrity/mcu-rf/footprint-review.md'),
    'FPC 0.5-18P HYH2.0':('FFC18P_HYH2.0','hardware/rev-a/signal-integrity/mcu-rf/footprint-review.md'),
    'TLV9004IRUCR':('TLV_RUC14_X2QFN_2x2mm_NoEP','hardware/rev-a/signal-integrity/afe/package-audit/README.md'),
    'TLV9054IRUCR':('TLV_RUC14_X2QFN_2x2mm_NoEP','hardware/rev-a/signal-integrity/afe/package-audit/README.md'),
    'TPD4E05U06DQAR':('TPD4E05U06DQA_USON10_1x2.5mm','hardware/rev-a/signal-integrity/afe/package-audit/README.md'),
    'BQ25185DLHR':('BQ25185DLH_WSON10_2.2x2mm','hardware/rev-a/signal-integrity/power/footprint-audit.md'),
    'TPS25200DRVR':('TPS25200DRV_WSON6_2x2mm','hardware/rev-a/signal-integrity/power/footprint-audit.md'),
    'BQ29737DSER':('BQ29737DSE_WSON6_1.5x1.5mm','hardware/rev-a/signal-integrity/power/footprint-audit.md')}

def choose(c):
    ref,mpn,package=c['ref'],c.get('mpn'),c.get('package','')
    if c.get('kind')=='copper_field' or ref=='RT501':return bare_field(len(c['pins']))
    if c.get('kind')=='pad':
        m=re.search(r'D([0-9.]+)mm',package)
        if not m:raise ValueError('Unknown pad diameter '+ref)
        return testpoint(float(m.group(1)))
    if mpn in critical:
        name,audit=critical[mpn];return custom(name,audit,'Pad counts compared with canonical circuit; maker audit owns detailed geometry.')
    if mpn=='U.FL-R-SMT-1(80)':return copy_standard('Connector_Coaxial','U.FL_Hirose_U.FL-R-SMT-1_Vertical',
        'UFL_Hirose_1SIG_2GND_3GND','Rename lower duplicate shell pad2 to3; bothGND. Remove extra central F.Mask rectangle because Hirose permits insulation there; retain copper/pad-mask/paste/keepout geometry.')
    if mpn=='SS14':return copy_standard('Diode_SMD','D_SMA','SS14_SMA_A1K2',
        'Swap official cathode1/anode2 numbering to canonical cathode2/anode1. Keep cathode marking at physical cathode end.')
    if package=='SMD3215-2':return copy_standard('Crystal','Crystal_SMD_3215-2Pin_3.2x1.5mm')
    if package in ['SOT-23','SOT-23-5','SOT-23-6']:return copy_standard('Package_TO_SOT_SMD',package)
    codes={'0402':'1005','0603':'1608','0805':'2012','1206':'3216'}
    if package in codes:
        family=ref[0]
        folders={'R':'Resistor_SMD','C':'Capacitor_SMD','L':'Inductor_SMD'}
        if family not in folders:raise ValueError('Unrecognized passive '+ref)
        return copy_standard(folders[family],f'{family}_{package}_{codes[package]}Metric')
    raise ValueError('No footprint mapping for '+str((ref,mpn,package)))

assignments=[]
pad_sets={}
for c in physical:
    name=choose(c)
    if name not in pad_sets:
        try:
            fp=pcbnew.FootprintLoad(str(LIB),name)
        except Exception as exc:
            raise RuntimeError(f'Native footprint load failed for {c["ref"]}: {name}') from exc
        if fp is None:raise ValueError('Cannot load '+name)
        pad_sets[name]={p.GetNumber() for p in fp.Pads() if p.GetNumber()}
    expected=set(c['pins'])
    actual=pad_sets[name]
    if expected!=actual:raise ValueError(f'Physical pad mismatch {c["ref"]}:canonical{sorted(expected)} footprint{sorted(actual)}')
    excluded=c.get('kind') in ['copper_field','pad'] or c['ref']=='RT501'
    assignments.append({'ref':c['ref'],'footprint':'CuraLink:'+name,'mpn':c.get('mpn'),'package':c.get('package'),
        'physical_pad_names':sorted(actual),'pad_set_check':'PASS','source_audit':library_records[name].get('source_audit'),
        'exclude_from_smt_position':excluded,'exclude_from_pcb_assembly_bom':excluded,
        'notes':'External thermistor itself remains separately procured; footprint is its wire landing.' if c['ref']=='RT501' else None})

report={'checked_date':'2026-10-02','timezone':'America/New_York','kicad':pcbnew.Version(),
    'status':'Candidate PCB footprint assignments; exact pad-set PASS does not establish fabrication/assembly qualification',
    'source_circuit':SOURCE.relative_to(ROOT).as_posix(),'source_circuit_sha256':sha(SOURCE),
    'physical_reference_count':len(assignments),'excluded_schematic_flag_count':len(components)-len(physical),
    'library_name':'CuraLink','library_path':LIB.relative_to(ROOT).as_posix(),
    'by_reference':{row['ref']:row['footprint'] for row in assignments},'assignments':assignments,
    'footprints':list(library_records.values()),'pad_set_summary':'PASS: all446 physical reference pad sets match canonical physical pin keys, including NC and mounting pads.',
    'limits':['FFC pin1/harness convention, actuator envelope and sample fit remain open.',
        'Standard SOT/passive lands retain official KiCad geometry; exact suffix-specific mask/paste/assembly review remains open.',
        'MCU exposed-pad paste/vias, MLPF RF stack and stencil, antenna tuning remain qualification gates.',
        'Bare copper fields are proposed bench pads, not assembled headers. External thermistor/cell procurement is separate.']}
(PCB/'footprint-assignments.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'references':len(assignments),'footprint_types':len(library_records),
    'pad_sets':'PASS','manifest':str(PCB/'footprint-assignments.json')},indent=2))

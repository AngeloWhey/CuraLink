"""Run with KiCad's system Python in WSL; inspect actual parsed lands."""
from pathlib import Path
import hashlib
import json
import pcbnew

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
DEST=ROOT/'hardware/rev-a/pcb/footprints/CuraLink.pretty'
audit=json.loads((OUT/'footprint-audit.json').read_text())
components=json.loads((ROOT/'hardware/rev-a/afe/afe-pin-nets.json').read_text())['components']
records=[]
board=pcbnew.BOARD()
for kind,name,offset in [('RUC','TLV_RUC14_X2QFN_2x2mm_NoEP',10),
                         ('DQA','TPD4E05U06DQA_USON10_1x2.5mm',15)]:
    fp=pcbnew.FootprintLoad(str(DEST),name)
    if fp is None:raise ValueError('KiCad failed to load '+name)
    physical=[];paste=[]
    expected={str(d['number']):d for d in audit[kind]['pads']}
    for p in fp.Pads():
        row={'number':p.GetNumber(),'x':p.GetPosition().x/1e6,'y':p.GetPosition().y/1e6,
             'w':p.GetSize().x/1e6,'h':p.GetSize().y/1e6,
             'rotation_deg':p.GetOrientationDegrees(),
             'layers':[pcbnew.LayerName(int(x))for x in p.GetLayerSet().Seq()]}
        if p.GetLayerSet().Contains(pcbnew.F_Cu):
            if row['number']not in expected:raise ValueError('Unexpected Cu pad '+str(row))
            want=expected[row['number']]
            if any(abs(row[key]-want[key])>1e-6 for key in ['x','y','w','h']):
                raise ValueError('Parsed Cu geometry mismatch '+str(row))
            if p.GetLocalSolderMaskMargin()!=50000:raise ValueError('Wrong mask expansion')
            physical.append(row)
        else:
            if row['number']!=''or row['layers']!=['F.Paste']:raise ValueError('Unexpected non-Cu pad')
            if abs(row['w']-.565)>1e-6 or abs(row['h']-.36)>1e-6:raise ValueError('Wrong ground paste aperture')
            paste.append(row)
    if len(physical)!=audit[kind]['numbered_Cu_pads']:raise ValueError('Missing physical land')
    if len(paste)!=(2 if kind=='DQA' else 0):raise ValueError('Wrong paste-only count')
    for c in components:
        if c.get('mpn')not in(['TLV9004IRUCR','TLV9054IRUCR']if kind=='RUC'else['TPD4E05U06DQAR']):continue
        if set(c['pins'])!=set(expected):raise ValueError(c['ref']+' physical pin map mismatch')
        if kind=='RUC':
            if c['pins']['3']!='AVDD_3V0' or c['pins']['10']!='GND':raise ValueError('Quad rail pin mismatch')
        else:
            if c['pins']['3']!='GND'or c['pins']['8']!='GND':raise ValueError('ESD ground pin mismatch')
    records.append({'footprint':name,'status':'PASS_actual_KiCad_FootprintLoad_and_manufacturer_geometry_check',
        'sha256':hashlib.sha256((DEST/(name+'.kicad_mod')).read_bytes()).hexdigest(),
        'numbered_copper_pads':physical,'paste_only_unnumbered_pads':paste,
        'canonical_pin_set_matches':True})
    fp.SetReference('U1'if kind=='RUC'else'U2')
    fp.SetPosition(pcbnew.VECTOR2I(int(offset*1e6),int(10e6)))
    board.Add(fp)
pcbnew.SaveBoard(str(OUT/'footprint-validation.kicad_pcb'),board)
(OUT/'native-parse-validation.json').write_text(json.dumps({'kicad_version':pcbnew.GetBuildVersion(),
    'source':'Two manufacturer-geometry custom footprints', 'status':'Geometry/parsing only, not completed board DRC or assembler qualification',
    'records':records},indent=2))
print('PASS native KiCad parsing, Cu/Paste geometry and canonical pin counts')

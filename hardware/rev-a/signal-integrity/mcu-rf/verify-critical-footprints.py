"""Run with KiCad Python to verify the five owned project footprints."""
import hashlib
import json
import os
from pathlib import Path
import pcbnew

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
official_library_root = Path(
    os.environ.get('CURALINK_KICAD_FOOTPRINT_DIR')
    or os.environ.get('KICAD9_FOOTPRINT_DIR')
    or os.environ.get('KICAD_FOOTPRINT_DIR')
    or (str(Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'KiCad/9.0/share/kicad/footprints')
        if os.name == 'nt' else '/usr/share/kicad/footprints')
)
lib=ROOT/'hardware/rev-a/pcb/footprints/CuraLink.pretty'
manifest=json.loads((HERE/'critical-footprint-manifest.json').read_text())
results=[]
for entry in manifest['footprints']:
    name=entry['name'].split(':',1)[1]
    fp=pcbnew.FootprintLoad(str(lib),name)
    if fp is None: raise RuntimeError('KiCad failed to load '+name)
    physical={p.GetNumber():p for p in fp.Pads() if p.GetNumber()}
    expected={p['pad']:p for p in entry['physical_pads']}
    assert set(physical)==set(expected),(name,set(physical),set(expected))
    for number,data in expected.items():
        pad=physical[number]
        pos=[pcbnew.ToMM(pad.GetPosition().x),pcbnew.ToMM(pad.GetPosition().y)]
        size=[pcbnew.ToMM(pad.GetSize().x),pcbnew.ToMM(pad.GetSize().y)]
        exp_size=[data.get('w_mm',data.get('copper_diameter_mm')),data.get('h_mm',data.get('copper_diameter_mm'))]
        assert max(abs(a-b) for a,b in zip(pos,[data['x_mm'],data['y_mm']]))<1e-6
        assert max(abs(a-b) for a,b in zip(size,exp_size))<1e-6
        if 'mask_diameter_mm' in data:
            margin=pad.GetLocalSolderMaskMargin()
            assert abs(size[0]+2*pcbnew.ToMM(margin)-data['mask_diameter_mm'])<1e-6
    results.append({'footprint':entry['name'],'load':'PASS','physical_pad_set':'PASS',
        'coordinates_and_copper_sizes':'PASS','physical_pad_count':len(physical),
        'paste_only_pad_count':sum(not p.GetNumber() for p in fp.Pads())})

refs=[('Package_DFN_QFN','QFN-48-1EP_7x7mm_P0.5mm_EP5.6x5.6mm'),
    ('RF_Antenna','Johanson_2450AT18x100'),('Crystal','Crystal_SMD_2016-4Pin_2.0x1.6mm'),
    ('Crystal','Crystal_SMD_3215-2Pin_3.2x1.5mm'),
    ('Connector_Coaxial','U.FL_Hirose_U.FL-R-SMT-1_Vertical')]
official=[]
for folder,name in refs:
    path=official_library_root/(folder+'.pretty')/(name+'.kicad_mod')
    fp=pcbnew.FootprintLoad(str(path.parent),name)
    official.append({'footprint':folder+':'+name,'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'pads':[{'number':p.GetNumber(),'x_mm':pcbnew.ToMM(p.GetPosition().x),'y_mm':pcbnew.ToMM(p.GetPosition().y),
            'w_mm':pcbnew.ToMM(p.GetSize().x),'h_mm':pcbnew.ToMM(p.GetSize().y)} for p in fp.Pads() if p.GetNumber()]})
(HERE/'critical-footprint-verification.json').write_text(json.dumps({'date':'2026-10-02','kicad':pcbnew.Version(),
    'scope':'Syntax and generated geometry versus recorded maker dimensions; not fabrication/assembly approval',
    'results':results,'official_library_comparison':official},indent=2)+'\n')
print(json.dumps(results,indent=2))

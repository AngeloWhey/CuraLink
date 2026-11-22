"""Create CuraLink's reviewable, provisional PCB using KiCad 9 pcbnew in WSL.

The canonical pin map is authoritative. Footprints are audited separately.
Placement is a repeatable engineering starting point, not an assembly release.
Run with WSL's system Python (pcbnew); do not use the Windows Python runtime.
"""
from pathlib import Path
import json, math, re, hashlib, xml.etree.ElementTree as ET
import pcbnew as k

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'hardware/rev-a'
SUP = OUT / 'pcb'
LIB = SUP / 'footprints/CuraLink.pretty'
WIDTH, HEIGHT = 80., 74.
MM = k.FromMM
V = lambda x,y: k.VECTOR2I(MM(x),MM(y))
physical = [c for c in json.loads((OUT/'components-merged.json').read_text())['components'] if c.get('kind') != 'flag']
cs = {c['ref']:c for c in physical}
assignments = json.loads((SUP/'footprint-assignments.json').read_text())
if 'by_reference' in assignments: assignments = assignments['by_reference']
elif 'assignments' in assignments: assignments = assignments['assignments']

b = k.BOARD()
b.SetCopperLayerCount(4)
settings = b.GetDesignSettings()
settings.m_MinClearance = MM(.10)
settings.m_TrackMinWidth = MM(.10)
settings.m_ViasMinSize = MM(.45)
settings.m_MinThroughDrill = MM(.20)
settings.m_ViasMinAnnularWidth = MM(.10)
settings.m_MinSilkTextHeight = MM(.6)
settings.m_MinSilkTextThickness = MM(.10)
settings.m_HoleToHoleMin = MM(.25)
settings.m_SolderMaskMinWidth = MM(.10)
netnames = sorted({n for c in physical for n in c['pins'].values() if n})
nets = {}
for i,name in enumerate(netnames,1):
    n = k.NETINFO_ITEM(b,name,i); b.Add(n); nets[name]=n

xml = ET.parse(OUT/'curalink-rev-a.net.xml')
paths = {}
root_uuid=re.search(r'\(uuid\s+([0-9a-f-]+)\)',(OUT/'curalink-rev-a.kicad_sch').read_text()).group(1)
for comp in xml.findall('.//components/comp'):
    sh = comp.find('sheetpath')
    ts = comp.findtext('tstamps')
    if sh is not None and ts: paths[comp.attrib['ref']] = '/'+root_uuid+sh.attrib['tstamps'].rstrip('/')+'/'+ts.split()[0]

fps = {}; places = {}; occupied = []; templates={}
print('Loading checked footprints',flush=True)
for c in physical:
    ref=c['ref']; a=assignments[ref]
    name=a if isinstance(a,str) else a.get('footprint',a.get('name'))
    name=name.split(':')[-1]
    if name not in templates: templates[name]=k.FootprintLoad(str(LIB),name)
    fp=templates[name].Duplicate()
    if not fp: raise ValueError('Missing footprint '+name)
    fp.SetFPID(k.LIB_ID('CuraLink',name))
    fp.SetReference(ref); fp.SetValue(c['value'])
    fp.Value().SetVisible(False)
    fp.Reference().SetTextSize(V(.6,.6)); fp.Reference().SetTextThickness(MM(.10))
    fp.Reference().SetVisible(False)  # dense discretes: canonical assembly drawing has all refs
    if paths.get(ref): fp.SetPath(k.KIID_PATH(paths[ref]))
    fp.SetDNP(not c.get('populated',True))
    if c.get('kind') in ('pad','copper_field') or c.get('assembly')=='OFFBOARD_MANUAL':
        fp.SetAttributes(fp.GetAttributes() | k.FP_EXCLUDE_FROM_POS_FILES | k.FP_EXCLUDE_FROM_BOM)
    numbered = [p for p in fp.Pads() if p.GetNumber() and p.IsOnLayer(k.F_Cu)]
    numbers={p.GetNumber() for p in numbered}
    if numbers != set(c['pins']): raise ValueError((ref,name,numbers,set(c['pins'])))
    for p in numbered:
        net=c['pins'][p.GetNumber()]
        if net: p.SetNet(nets[net])
    b.Add(fp); fps[ref]=fp
    if len(fps)%100==0: print('Loaded',len(fps),flush=True)

def box(fp):
    bb=fp.GetBoundingBox(False,False)
    return tuple(k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()])

def overlap(a,c,gap=.08):
    return not (a[2]+gap<=c[0] or c[2]+gap<=a[0] or a[3]+gap<=c[1] or c[3]+gap<=a[1])

def fits(fp,region):
    bb=box(fp)
    return bb[0]>=region[0] and bb[1]>=region[1] and bb[2]<=region[2] and bb[3]<=region[3] and not any(overlap(bb,o[1]) for o in occupied)

def place(ref,x,y,angle=0,region=None,search=False,group=''):
    if ref in places: return
    fp=fps[ref]; fp.SetOrientationDegrees(angle); fp.SetPosition(V(x,y))
    region = region or (1,1,WIDTH-1,HEIGHT-1)
    if search and not fits(fp,region):
        candidates=[]
        for yy in range(math.ceil(region[1]*2),math.floor(region[3]*2)+1):
            for xx in range(math.ceil(region[0]*2),math.floor(region[2]*2)+1):
                candidates.append(((xx/2-x)**2+(yy/2-y)**2,xx/2,yy/2))
        original=box(fp)
        for _,xx,yy in sorted(candidates):
            dx,dy=xx-x,yy-y
            bb=(original[0]+dx,original[1]+dy,original[2]+dx,original[3]+dy)
            if bb[0]<region[0] or bb[1]<region[1] or bb[2]>region[2] or bb[3]>region[3]: continue
            if not any(overlap(bb,o[1]) for o in occupied):
                x,y=xx,yy; fp.SetPosition(V(x,y)); break
        else: raise ValueError('Cannot pack '+ref+' into '+str(region))
    if not fits(fp,region): raise ValueError(('Placement collision/bounds',ref,box(fp),[(r,bb) for r,bb in occupied if overlap(box(fp),bb)]))
    occupied.append((ref,box(fp)))
    places[ref]={'x_mm':x,'y_mm':y,'rotation_deg':angle,'group':group,'bounds_mm':box(fp)}
    if len(places)%50==0: print('Placed',len(places),flush=True)

# Four forward stages, two banks of four channels. Output nodes remain to the
# right of early inputs; routing constraints are assessed separately.
columns=[15.,28.,41.,54.]
bank_y=[14.,35.]
for bank,y in enumerate(bank_y):
    for stage,x in enumerate(columns):
        ref='U'+str(101+2*stage+bank)
        place(ref,x,y,group='AFE bank %d stage %d'%(bank+1,stage+1))
place('U109',14,48,group='Shared REF and VMID')
place('J301',2.,25,90,region=(1,1,10,50),group='Input FFC')
for ref,x,y in [('U110',10.5,19),('U111',10.5,29),('U112',10.5,42)]:
    place(ref,x,y,90,search=True,region=(8.5,2,13.5,44),group='Connector ESD')
place('U401',68,27,group='MCU ADC')
place('AE401',78.3,2.7,90,region=(.1,.1,WIDTH-.1,HEIGHT-.1),group='Corner antenna')
place('U402',71,19,group='RF filter — adaptation open')
place('J404',73.5,11.5,group='Optional RF coax')
place('Y401',66.5,20.5,group='HSE crystal')
place('Y402',68,34,group='LSE crystal')

# Place local amplifier bypass capacitors first, near each actual supply land.
for c in physical:
    ref=c['ref']
    if c.get('page')=='afe_shared' and ref.startswith('C') and set(c['pins'].values())=={'AVDD_3V0','GND'} and c['value'] in ['100nF','100n']:
        idx=int(re.search(r'\d+',ref).group())-1059
        # Net names alone cannot distinguish these interchangeable bypasses.
        chip='U'+str(101+max(0,min(8,idx)))
        x,y=places[chip]['x_mm'],places[chip]['y_mm']
        place(ref,x-2.8,y,90,search=True,region=(x-5.5,y-9,x+5.5,y+9),group='Local amplifier bypass')

quadrants=[(-3.5,-5),(-3.5,5),(3.5,5),(3.5,-5)]
for ch in range(1,9):
    bank=(ch-1)//4; unit=(ch-1)%4; y=bank_y[bank]
    rbase=1001+18*(ch-1); cbase=1001+7*(ch-1)
    groups=[[],[],[],[]]
    for c in physical:
        if c.get('page') != 'afe_ch'+str(ch): continue
        ref=c['ref']
        if ref.startswith('R'): off=int(ref[1:])-rbase; stage=0 if off<4 else 1 if off<10 else 2 if off<14 else 3
        elif ref.startswith('C'): off=int(ref[1:])-cbase; stage=0 if off<1 else 1 if off<3 else 2 if off<5 else 3
        else:
            net=next(iter(c['pins'].values()))
            stage=0 if net.endswith('_PRE') else 1 if net.endswith('_HP') else 3
        groups[stage].append(c)
    for stage,seq in enumerate(groups):
        x=columns[stage]; dx,dy=quadrants[unit]
        # Populated components before optional/test pads, then larger packages.
        seq.sort(key=lambda c:(c.get('kind')=='pad',not c.get('populated',True),c.get('package')=='0402',c['ref']))
        for i,c in enumerate(seq):
            tx=x+dx+((i%2)-.5)*2; ty=y+dy+((i//2)-1)*1.8
            place(c['ref'],tx,ty,0,region=(x-7,y-11,x+7,y+11),search=True,group='CH%d stage%d'%(ch,stage+1))

# Reserve local MCU components by actual pin connectivity; caps next to their
# rail/signal pin, ADC filters next to input pins, never back in early AFE bays.
def padxy(ref,pin):
    p=next(p for p in fps[ref].Pads() if p.GetNumber()==str(pin))
    v=p.GetPosition(); return k.ToMM(v.x),k.ToMM(v.y)

for idx,pin in enumerate([3,4,5,7,10,12,13,14],1):
    px,py=padxy('U401',pin)
    target=(px-2,py) if px<68 else (px,py+2)
    for ref,shift in [('C'+str(412+idx),0),('R'+str(400+idx),-2)]:
        place(ref,target[0]+shift,target[1],90,region=(60,21,78,39),search=True,group='ADC input filter')
for ref,pin in [('C401',11),('C402',22),('C403',35),('C404',39),('C405',42),('C406',6),('C407',6),('C408',44),('C409',38)]:
    px,py=padxy('U401',pin)
    dx,dy=px-68,py-27; norm=max(abs(dx),abs(dy),.1)
    place(ref,px+dx/norm*1.7,py+dy/norm*1.7,0,region=(60,20,79,40),search=True,group='MCU local bypass')

# Tight RF part placement remains unrouted until the filter stackup adaptation
# is reviewed. Intentional feed copper is distinct from antenna ground keepout.
for i,ref in enumerate(['R417','R418','C423','L401','L402']):
    place(ref,73+(i%2)*2,16-(i//2)*2,search=True,region=(67,7,79,20),group='RF tuning — unrouted')
for ref in ['C421','C422']:
    place(ref,65 if ref=='C421' else 71,34,search=True,region=(62,31,75,38),group='LSE load')

# Lower region carries charger, always-on control, battery isolation and LDOs.
power_path=SUP/'power-placement-groups.json'
pg=json.loads(power_path.read_text()) if power_path.exists() else {}
if 'assignments' in pg: pg=pg['assignments']
powerfixed={
 'U501':(13,59),'U502':(7,56),'U503':(30,56),'U504':(42,56),
 'U505':(30,64),'U506':(23,59),'U507':(23,65),'U508':(42,64),
 'U509':(48,64),'U510':(36,64),'U511':(57,61),'U512':(61,53),
 'U513':(71,53),'U514':(9,69),'U515':(67,62),
 'Q501':(51,55),'Q502':(56,55),'Q503':(51,60),
 'J501':(39,71),'J502':(4,52),'J503':(4,62),'J504':(4,69),
 'RT501':(23,71),'D501':(8,51)}
for ref,(x,y) in powerfixed.items():
    place(ref,x,y,search=True,region=(1,50,79,73),group='Power')
for c in sorted(physical,key=lambda c:(not c['ref'].startswith(('U','Q','D','J')),c.get('kind')=='pad',c['ref'])):
    ref=c['ref']
    if ref in places or c.get('page')!='power': continue
    related=[]
    for ic in powerfixed:
        common=set(c['pins'].values()) & set(cs[ic]['pins'].values()) - {None,'GND','CTRL_3V0','AVDD_3V0','DVDD_3V0'}
        if common: related.append((len(common),ic))
    if related:
        _,anchor=max(related)
        x,y=places[anchor]['x_mm'],places[anchor]['y_mm']
    else: x,y=34,59
    if ref.startswith('C'): x+=2.5
    else: y+=2.5
    place(ref,x,y,search=True,region=(1,50,79,73),group='Power')

# Shared reference/bias components and boundary test pads are kept away from
# the charge path; remaining digital access uses the MCU-side corridor.
for c in physical:
    ref=c['ref']
    if ref in places: continue
    page=c.get('page','')
    if page in ['afe_shared','INTERFACE']:
        shared='REF' in ' '.join(n or '' for n in c['pins'].values()) or 'VMID' in ' '.join(n or '' for n in c['pins'].values())
        x,y=(14,47) if shared else (23,47)
        place(ref,x,y,search=True,region=(1,44.7,58,50),group='Shared REF / bias / analog rail')
    elif page=='RF':
        place(ref,76,18,search=True,region=(64,7,79,20),group='RF access')
    else:
        place(ref,70,43,search=True,region=(60,39.5,79,49),group='MCU access / control')

# Optional independently checked local-placement correction from physical
# review. Apply as a group, then check against every unchanged courtyard.
for override_path in [SUP/'mcu-placement-overrides.json',SUP/'power-placement-overrides.json']:
  if override_path.exists():
    overrides=json.loads(override_path.read_text())
    if 'overrides' in overrides: overrides=overrides['overrides']
    elif 'placements' in overrides: overrides=overrides['placements']
    for ref,loc in overrides.items():
        fp=fps[ref]; fp.SetOrientationDegrees(loc['rotation_deg']); fp.SetPosition(V(loc['x_mm'],loc['y_mm']))
        places[ref].update(loc);places[ref]['bounds_mm']=box(fp)
for i,ref in enumerate(fps):
        for other in list(fps)[i+1:]:
            if overlap(box(fps[ref]),box(fps[other])): raise ValueError('Override collision '+ref+' / '+other)

for start,end in [((0,0),(WIDTH,0)),((WIDTH,0),(WIDTH,HEIGHT)),((WIDTH,HEIGHT),(0,HEIGHT)),((0,HEIGHT),(0,0))]:
    edge=k.PCB_SHAPE(); edge.SetShape(k.SHAPE_T_SEGMENT); edge.SetStart(V(*start)); edge.SetEnd(V(*end)); edge.SetLayer(k.Edge_Cuts); edge.SetWidth(MM(.05)); b.Add(edge)

def text(s,x,y,size=.8,layer=k.F_SilkS):
    t=k.PCB_TEXT(b); t.SetText(s); t.SetPosition(V(x,y)); t.SetTextSize(V(size,size)); t.SetTextThickness(MM(.12)); t.SetLayer(layer); b.Add(t)
text('CuraLink Rev A — CANDIDATE / DO NOT FABRICATE',39,72.8,.7,k.Dwgs_User)
text('INPUT',4,9,.7); text('PRE',15,1.8); text('DC REJECT',28,1.8); text('LP1',41,1.8); text('LP2',54,1.8)
text('CH1–4',15,25,.7,k.Dwgs_User); text('CH5–8',15,43,.7,k.Dwgs_User)
text('ADC / MCU',68,47.5,.7,k.Dwgs_User)
text('CELL EMULATOR ONLY — CELL QUALIFICATION OPEN',39,73,.6,k.F_SilkS)

# Ground-only keepout at the manufacturer-sized antenna corner. All-layer
# zones are forbidden; unrelated routes are also held out during routing.
ko=k.ZONE(b); ko.SetIsRuleArea(True); ko.SetZoneName('ANTENNA CORNER — ALL-LAYER GROUND EXCLUSION')
layers=k.LSET();
for ly in [k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu]: layers.AddLayer(ly)
ko.SetLayerSet(layers); ko.SetDoNotAllowCopperPour(True); ko.SetDoNotAllowTracks(False); ko.SetDoNotAllowVias(True); ko.SetDoNotAllowPads(False); ko.SetDoNotAllowFootprints(False)
poly=ko.Outline(); poly.NewOutline()
for xy in [(WIDTH-6.5,0),(WIDTH,0),(WIDTH,6.5),(WIDTH-6.5,6.5)]: poly.Append(MM(xy[0]),MM(xy[1]))
b.Add(ko)

for layer in [k.In1_Cu,k.In2_Cu]:
    zone=k.ZONE(b); zone.SetLayer(layer); zone.SetNet(nets['GND']); zone.SetLocalClearance(MM(.15)); zone.SetThermalReliefGap(MM(.2)); zone.SetThermalReliefSpokeWidth(MM(.25)); zone.SetPadConnection(k.ZONE_CONNECTION_FULL); zone.SetMinThickness(MM(.15))
    poly=zone.Outline(); poly.NewOutline()
    for xy in [( .5,.5),(WIDTH-.5,.5),(WIDTH-.5,HEIGHT-.5),(.5,HEIGHT-.5)]: poly.Append(MM(xy[0]),MM(xy[1]))
    b.Add(zone)

manifest={'status':'Candidate placement; routing/DRC qualification pending','date':'2026-10-02 America/New_York','board_dimensions_mm':[WIDTH,HEIGHT],'layers':['F.Cu','In1.Cu GND','In2.Cu GND','B.Cu'],'source_sha256':hashlib.sha256((OUT/'components-merged.json').read_bytes()).hexdigest(),'placements':places,'rf_route_status':'Open: MLPF ground/stackup adaptation; intentional RF nets are not qualified','antenna_corner_keepout_mm':[WIDTH-6.5,0,WIDTH,6.5],'manufacturing_status':'DO NOT FABRICATE: Candidate implementation and open electrical/assembly gates'}
(SUP/'placement-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
k.SaveBoard(str(OUT/'curalink-rev-a.kicad_pcb'),b)
print(json.dumps({'footprints':len(fps),'nets':len(nets),'dimensions_mm':[WIDTH,HEIGHT],'status':'placement created'}))

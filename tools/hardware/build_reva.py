"""Generate a self-contained KiCad schematic from audited physical pin maps.

The emitted schematic is the review/import artifact, not a PCB manufacturing
release. Its connectivity is checked independently against KiCad's netlist.
"""
from pathlib import Path
import collections
import csv
import json
import math
import re
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'hardware/rev-a'
PROJECT = 'curalink-rev-a'
FOOTPRINT_MAP_FILE = OUT / 'pcb/footprint-assignments.json'
FOOTPRINT_MAP = json.loads(FOOTPRINT_MAP_FILE.read_text()).get('by_reference', {}) if FOOTPRINT_MAP_FILE.exists() else {}
RECORD_DATE = '2026-10-02' # Client America/New_York date for latest handoff.
NS = uuid.UUID('c6d14f97-c052-4901-9f72-f1ee3905a101')

def uid(s):
    return str(uuid.uuid5(NS, str(s)))

def q(s):
    return json.dumps(str(s), ensure_ascii=False)

def num(x):
    return f'{x:.4f}'.rstrip('0').rstrip('.') if x else '0'

def eff(size=1.0, hide=False, justify=''):
    return f'(effects (font (size {size} {size})) {justify} {"hide" if hide else ""})'

def prop(name, value, x=0, y=0, hide=True):
    return f'(property {q(name)} {q(value)} (at {num(x)} {num(y)} 0) {eff(.9, hide)})'

def lib_key(c):
    if c.get('kind') == 'flag':
        return 'PWR_FLAG'
    if c['ref'].startswith('R') and len(c['pins']) == 2:
        return 'Resistor'
    if c['ref'].startswith('C') and len(c['pins']) == 2:
        return 'Capacitor'
    if len(c['pins']) == 1:
        return 'TestPad'
    key = re.sub(r'[^A-Za-z0-9_]', '_', c.get('mpn') or c['value'])
    # Copper pad fields and harnesses share a description, not a pin geometry.
    # Distinguish them to prevent a six-pin SWD symbol replacing four-pin UART.
    if c.get('mpn') in ('PCB copper', 'User harness', 'User_harness', 'Connector_1x02') or c['ref'].startswith('J'):
        key += '_' + str(len(c['pins']))
    return key

def ptypes(c):
    return c.get('pin_types') or c.get('pinfunctiontypes') or {}

def pin(number, name, typ, x, y, angle, length=2.54):
    return f'''(pin {typ} line (at {num(x)} {num(y)} {angle}) (length {length})
       (name {q(name)} {eff(.75)}) (number {q(number)} {eff(.75)}))'''

def blocks(c):
    if c.get('unit_blocks'):
        bs = list(c['unit_blocks'])
        represented = {str(p) for b in bs for p in b['pins']}
        remaining = [p for p in c['pins'] if p not in represented]
        if remaining:
            bs.append({'unit': 5, 'pins': remaining, 'page': 'AFE_SHARED', 'stage': 'power'})
        return bs
    return [{'unit': 1, 'pins': list(c['pins']), 'page': c.get('page', 'INTERFACE')}]

def geometry(c, b):
    ps = [str(p) for p in b['pins']]
    names = c.get('pin_names', {})
    stage = b.get('stage', '')
    if c.get('unit_blocks') and len(ps) == 3 and stage != 'power':
        # Agent supplies OUT, minus, plus in that order.
        op, mi, pl = ps
        return {op: (7.62, 0, 180), mi: (-7.62, 2.54, 0),
                pl: (-7.62, -2.54, 0)}, 12.7, 12.7, 'opamp'
    if len(ps) == 1:
        return {ps[0]: (-2.54, 0, 0)}, 0, 2.54, 'pad'
    if len(ps) == 2:
        return {ps[0]: (-5.08, 0, 0), ps[1]: (5.08, 0, 180)}, 5.08, 5.08, 'passive'
    left, right = ps[:math.ceil(len(ps)/2)], ps[math.ceil(len(ps)/2):]
    height = max(len(left), len(right)) * 2.54 + 2.54
    width = 25.4 if len(ps) > 20 else 17.78
    loc = {}
    for side, seq in ((-1, left), (1, right)):
        for i, p in enumerate(seq):
            loc[p] = (side*(width/2+2.54), (len(seq)-1)/2*2.54-i*2.54,
                      0 if side < 0 else 180)
    return loc, width, height, 'ic'

def make_lib(c):
    key = lib_key(c)
    s = [f'(symbol {q(key)} (pin_names (offset 0.508)) (in_bom yes) (on_board yes)',
         prop('Reference', re.sub(r'\d.*', '', c['ref'])), prop('Value', key)]
    types = ptypes(c)
    for b in blocks(c):
        loc, w, h, kind = geometry(c, b)
        unit = b['unit']
        s.append(f'(symbol {q(key+"_"+str(unit)+"_1")}')
        if kind == 'opamp':
            s.append('(polyline (pts (xy -5.08 5.08) (xy -5.08 -5.08) (xy 5.08 0) (xy -5.08 5.08)) (stroke (width 0.254) (type default)) (fill (type background)))')
        elif key == 'Resistor':
            s.append('(rectangle (start -2.54 1.016) (end 2.54 -1.016) (stroke (width 0.254) (type default)) (fill (type none)))')
        elif key == 'Capacitor':
            for x in (-.635, .635):
                s.append(f'(polyline (pts (xy {x} -1.778) (xy {x} 1.778)) (stroke (width .254) (type default)) (fill (type none)))')
            for a, z in ((-2.54,-.635),(.635,2.54)):
                s.append(f'(polyline (pts (xy {a} 0) (xy {z} 0)) (stroke (width .254) (type default)) (fill (type none)))')
        elif kind == 'pad':
            s.append('(circle (center 0 0) (radius 0.762) (stroke (width .254) (type default)) (fill (type none)))')
        else:
            s.append(f'(rectangle (start {-w/2} {h/2}) (end {w/2} {-h/2}) (stroke (width .254) (type default)) (fill (type background)))')
        for p, (x,y,a) in loc.items():
            typ = types.get(p, 'passive')
            if key == 'PWR_FLAG': typ = 'power_out'
            name = c.get('pin_names', {}).get(p, '~')
            s.append(pin(p, name, typ, x, y, a))
        s.append(')')
    s.append(')')
    return '\n'.join(s)

def label(net, x, y, angle, tag):
    return f'''(global_label {q(net)} (shape bidirectional) (at {num(x)} {num(y)} {angle})
      {eff(.8, False, '(justify left)' if angle == 0 else '(justify right)')}
      (uuid {uid(tag)}) {prop('Intersheetrefs', '${INTERSHEET_REFS}', x, y, True)})'''

def wire(x1,y1,x2,y2,tag):
    return f'(wire (pts (xy {num(x1)} {num(y1)}) (xy {num(x2)} {num(y2)})) (stroke (width 0.1524) (type default)) (uuid {uid(tag)}))'

def instance(c, b, x, y, path):
    key = lib_key(c)
    s = [f'''(symbol (lib_id {q('CuraLink:'+key)}) (at {num(x)} {num(y)} 0)
      (unit {b['unit']}) (in_bom {"no" if c.get('kind') in ('flag','pad','copper_field') else 'yes'}) (on_board yes)
      (uuid {uid('symbol:'+c['ref']+':'+str(b['unit']))})''']
    loc, w, h, kind = geometry(c, b)
    shown_value=c['value']+(' [DNP]' if c.get('populated') is False and 'DNP' not in c['value'] else '')
    s += [prop('Reference', c['ref'], x, y-h/2-3.0, False),
          prop('Value', shown_value, x, y-h/2-1.35, False),
          prop('Footprint', c.get('footprint') or FOOTPRINT_MAP.get(c['ref'],''), x,y,True),
          prop('Datasheet',c.get('source',''),x,y,True),
          prop('LCSC',c.get('lcsc') or '',x,y,True),
          prop('MPN',c.get('mpn') or '',x,y,True),
          prop('DNP','yes' if c.get('populated') is False else 'no',x,y,True),
          prop('Assembly',c.get('assembly','PCB_SMT'),x,y,True)]
    for p in b['pins']:
        s.append(f'(pin {q(p)} (uuid {uid("pin:"+c["ref"]+":"+str(b["unit"])+":"+p)}))')
    s.append(f'(instances (project {q(PROJECT)} (path {q(path)} (reference {q(c["ref"])}) (unit {b["unit"]})))) )')
    for p,(dx,dy,a) in loc.items():
        px,py = x+dx,y-dy
        n = c['pins'][p]
        if n is None:
            s.append(f'(no_connect (at {num(px)} {num(py)}) (uuid {uid(c["ref"]+p+"NC")}))')
        else:
            lx = px + (-3.81 if dx < 0 else 3.81)
            s.append(wire(px,py,lx,py,c['ref']+p+'wire'))
            s.append(label(n,lx,py,180 if dx < 0 else 0,c['ref']+p+'label'))
    return '\n'.join(s)

def text_line(s,x,y,size=1.3):
    return f'(text {q(s)} (at {num(x)} {num(y)} 0) {eff(size,False,"(justify left)")} (uuid {uid(s+str(x)+str(y))}))'

def read_parts():
    files = ['afe/afe-pin-nets.json','mcu/mcu-components.json','power/power-components.json','interface/interface-components.json']
    components=[]
    sources=[]
    for file in files:
        p=OUT/file
        if not p.exists():
            raise FileNotFoundError(p)
        data=json.loads(p.read_text(encoding='utf-8'))
        components.extend(data['components'])
        sources.append({'file':file,'sha256':__import__('hashlib').sha256(p.read_bytes()).hexdigest()})
    refs=[c['ref'] for c in components]
    if len(refs) != len(set(refs)): raise ValueError('Duplicate physical reference')
    return components,sources

def main():
    components,sources=read_parts()
    inventory_path=OUT/'procurement/stock-audit-2026-10-02.json'
    inventory={}
    if inventory_path.exists():
        inventory={r['lcsc']:r for r in json.loads(inventory_path.read_text(encoding='utf-8'))['records']}
        sources.append({'file':inventory_path.relative_to(OUT).as_posix(),'sha256':__import__('hashlib').sha256(inventory_path.read_bytes()).hexdigest()})
    catalog_path=OUT/'passive-catalog.json'
    catalog=json.loads(catalog_path.read_text()) if catalog_path.exists() else {}
    if catalog_path.exists():
        sources.append({'file':'passive-catalog.json','sha256':__import__('hashlib').sha256(catalog_path.read_bytes()).hexdigest()})
    for c in components:
        c['assembly']='OFFBOARD_MANUAL' if c['ref']=='RT501' else 'PCB_SMT'
        if c['ref'].startswith('J') and c['ref'] in ('J401','J402','J403','J501','J502','J503','J504'):
            c['kind']='copper_field'
            c['mpn']='PCB copper'
            c['lcsc']=None
            c['package']='Custom wire/pogo pad field; no assembled connector'
            c['notes']=str(c.get('notes',''))+' Implement as labelled solder/pogo pads; insulate and strain-relieve external wires.'
        if 'populated' not in c:
            c['populated']=c.get('populate', not c.get('dnp',False))
        for p in c['pins']:
            n=c['pins'][p]
            if n:
                if n.startswith('NC_'):
                    c['pins'][p]=None
                    continue
                n=re.sub(r'AFE_OUT_?(\d+)$',r'AFE_OUT_\1',n)
                c['pins'][p]=n
        if not c.get('mpn') and c['ref'][0] in 'RC':
            key=f'{c["ref"][0]}:{c["value"]}:{c.get("tolerance","1%")}:{c.get("package","")}'
            spec=catalog.get(key) or catalog.get(f'{c["ref"][0]}:{c["value"]}')
            if spec:
                functional_notes=c.get('notes','')
                c.update(spec)
                c['notes']=functional_notes+' '+spec.get('notes','')
        if len(c['pins'])==1: c['kind']='pad'
    # External supply/return declarations for ERC; these do not create hardware.
    flag_nets=['GND','PACK+','BENCH_CHG_5V']
    # These nodes are supplied through passive/isolation devices. ERC cannot
    # infer that path; declaring it here is not a functional safety waiver.
    for ref in ('U502','U503','U511','U512','U513','U514'):
        c=next(c for c in components if c['ref']==ref)
        for p,t in ptypes(c).items():
            if t=='power_in' and c['pins'].get(p) and c['pins'][p] not in flag_nets:
                flag_nets.append(c['pins'][p])
    for i,n in enumerate(flag_nets):
        components.append({'ref':f'#FLG{i+1:03}', 'value':'PWR_FLAG', 'mpn':None,
            'pins':{'1':n},'pin_types':{'1':'power_out'},'kind':'flag', 'page':'INTERFACE'})
    pages=collections.defaultdict(list)
    for c in components:
        for b in blocks(c):
            page=b.get('page') or (f'AFE_CH{b["channel"]}' if b.get('channel') else c.get('page','INTERFACE'))
            pages[page].append((c,b))
    # Shelf layout, preserving original page names while splitting long banks.
    laid=[]
    for name,items in sorted(pages.items()):
        partno=1; y=35.56; col=0; current=[]
        for c,b in items:
            _,_,h,_=geometry(c,b)
            card_h=math.ceil(max(17.78,h+10)/2.54)*2.54
            if y+card_h > 266:
                col+=1;y=35.56
            if col>3:
                laid.append((f'{name}_{partno}',current));current=[];partno+=1;col=0;y=35.56
            current.append((c,b,50.8+101.6*col,y+card_h/2))
            y+=card_h
        laid.append((f'{name}_{partno}',current))
    lib={}
    for c in components:
        if lib_key(c) not in lib: lib[lib_key(c)]=make_lib(c)
    (OUT/'CuraLink.kicad_sym').write_text('(kicad_symbol_lib (version 20220914) (generator curalink_generator)\n'+'\n'.join(lib.values())+'\n)\n',encoding='utf-8')
    (OUT/'sym-lib-table').write_text('(sym_lib_table (lib (name "CuraLink") (type "KiCad") (uri "${KIPRJMOD}/CuraLink.kicad_sym") (options "") (descr "Audited CuraLink pin-map symbols")))\n')
    rootid=uid(PROJECT)
    roots=[f'(kicad_sch (version 20230121) (generator curalink_generator) (uuid {rootid}) (paper "A3") (lib_symbols)']
    roots.append(text_line('CuraLink Rev A schematic draft',20,18,3))
    roots.append(text_line(RECORD_DATE+' | ADC acquisition recommendation | NOT A PCB RELEASE',20,25,1.6))
    roots.append(text_line('Global net names connect sheets. See README, pin-net CSV and verification report before import/order.',20,32))
    for i,(name,items) in enumerate(laid):
        sheetid=uid(name+'sheet');sheetpath='/'+rootid+'/'+sheetid
        sid=uid(name+'document')
        needed={lib_key(c) for c,b,x,y in items}
        ss=[f'(kicad_sch (version 20230121) (generator curalink_generator) (uuid {sid}) (paper "A3")',
            '(title_block (title '+q('CuraLink '+name)+') (date '+q(RECORD_DATE)+') (rev "A-DRAFT") (comment 1 "Engineering draft; no PCB release"))',
            '(lib_symbols '+'\n'.join(lib[k].replace('(symbol '+q(k), '(symbol '+q('CuraLink:'+k),1) for k in sorted(needed))+')',
            text_line(name.replace('_',' '),20,15,2),
            text_line('Exact physical pin numbers; global net labels define connections. NC crosses are intentional.',20,22,1.2)]
        for c,b,x,y in items: ss.append(instance(c,b,x,y,sheetpath))
        ss.append(f'(sheet_instances (path {q("/"+rootid+"/"+sheetid)} (page {q(str(i+2))})))')
        ss.append(')')
        (OUT/(name+'.kicad_sch')).write_text('\n'.join(ss)+'\n',encoding='utf-8')
        x=25+(i%3)*125;y=47+(i//3)*35
        roots.append(f'''(sheet (at {x} {y}) (size 110 25) (stroke (width 0) (type default)) (fill (color 0 0 0 0))
          (uuid {sheetid}) {prop('Sheetname',name,x+2,y+2,False)} {prop('Sheetfile',name+'.kicad_sch',x+2,y+22,False)}
          (instances (project {q(PROJECT)} (path {q('/'+rootid)} (page {q(str(i+2))})))))''')
    roots.append('(sheet_instances (path "/" (page "1")))\n)')
    (OUT/(PROJECT+'.kicad_sch')).write_text('\n'.join(roots)+'\n',encoding='utf-8')
    active={PROJECT+'.kicad_sch'}|{n+'.kicad_sch' for n,_ in laid}
    for p in OUT.glob('*.kicad_sch'):
        if p.name not in active and p.resolve().parent==OUT.resolve() and '(generator curalink_generator)' in p.read_text(encoding='utf-8'):
            p.unlink() # Only obsolete outputs from this generator in this folder.
    project_path = OUT / (PROJECT + '.kicad_pro')
    if not project_path.exists():
        project_path.write_text(json.dumps({'meta':{'filename':PROJECT+'.kicad_pro','version':1},'net_settings':{'classes':[{'name':'Default','description':'Layout rules must be set in Altium','clearance':.2,'track_width':.25}],'meta':{'version':3}}},indent=2)+'\n')
    (OUT/'components-merged.json').write_text(json.dumps({'components':components,'sources':sources,'schematic_pages':[n for n,_ in laid]},indent=2)+'\n',encoding='utf-8')
    rows=[]
    for c in components:
        if c.get('kind')=='flag': continue
        for p,n in c['pins'].items():
            rows.append({'Reference':c['ref'],'Pin':p,'Pin name':c.get('pin_names',{}).get(p,''),'Net':n or 'INTENTIONAL_NC','Value':c['value'],'MPN':c.get('mpn') or '', 'LCSC':c.get('lcsc') or '', 'Package':c.get('package',''),'Populate':'NO' if c.get('populated') is False else 'YES','Notes':c.get('notes','')})
    with (OUT/'pin-net-connections.csv').open('w',newline='',encoding='utf-8-sig') as f:
        dw=csv.DictWriter(f,fieldnames=list(rows[0]));dw.writeheader();dw.writerows(rows)
    groups=collections.defaultdict(list)
    for c in components:
        if c.get('kind') in ('pad','flag','copper_field'): continue
        groups[(c.get('mpn') or '',c.get('lcsc') or '',c['value'],c.get('package',''),c.get('tolerance',''),c.get('populated') is False)].append(c)
    with (OUT/'bom.csv').open('w',newline='',encoding='utf-8-sig') as f:
        dw=csv.DictWriter(f,fieldnames=['References','Quantity','Value','MPN','LCSC','Package','Tolerance','Populate','Assembly','Status','Stock checked','International immediate stock','MOQ','Order multiple','LCSC URL']);dw.writeheader()
        for (mpn,lcsc,v,pkg,tol,dnp),cs in sorted(groups.items()):
            stock=inventory.get(lcsc,{})
            if stock and stock.get('actual_mpn')!=mpn:
                raise ValueError('Inventory MPN does not match '+lcsc)
            dw.writerow({'References':','.join(c['ref'] for c in cs),'Quantity':len(cs),'Value':v,'MPN':mpn,'LCSC':lcsc,'Package':pkg,'Tolerance':tol,'Populate':'NO' if dnp else 'YES','Assembly':cs[0].get('assembly','PCB_SMT'),'Status':stock.get('status','SOURCING_OPEN' if not lcsc else 'VERIFY_AT_ORDER'),'Stock checked':stock.get('checked_date',''),'International immediate stock':stock.get('stock_international_immediate',''),'MOQ':stock.get('minimum_order',''),'Order multiple':stock.get('order_multiple',''),'LCSC URL':stock.get('source_url','')})
    audits=collections.defaultdict(list)
    for c in components:
        if c.get('kind')!='flag':
            audits[(c.get('mpn') or 'PCB copper',c.get('lcsc') or '',c.get('package') or 'Copper pad',tuple(c['pins']))].append(c)
    with (OUT/'footprint-audit.csv').open('w',newline='',encoding='utf-8-sig') as f:
        columns=['References','MPN','LCSC','Package','Assembly','Physical pad names','Assigned footprint','Symbol connectivity status','Land-pattern status','Required audit','Source']
        dw=csv.DictWriter(f,fieldnames=columns);dw.writeheader()
        for (mpn,code,pkg,pins),cs in sorted(audits.items()):
            c=cs[0]
            assembly=c.get('assembly','PCB_SMT')
            assigned=sorted({FOOTPRINT_MAP.get(x['ref'],'') for x in cs}-{''})
            land='ASSIGNED / PAD SET CHECKED; PROCESS QUALIFICATION OPEN' if assigned else 'OPEN - ASSIGN/AUDIT IN ALTIUM'
            notes='Compare exact-suffix manufacturer recommended land pattern, pad numbers, polarity, courtyard, mask/paste and assembly capability.'
            if assembly=='OFFBOARD_MANUAL':
                land='OFFBOARD NTC; PCB HAS WIRE LANDING ONLY'
                notes='Cell-mounted leaded NTC; verify thermal attachment, lead insulation, harness continuity and strain relief. Exclude from main-PCB pick-and-place.'
            elif mpn=='PCB copper' or c.get('kind') in ('pad','copper_field'):
                assembly='PCB_ARTWORK'
                notes='Define labelled copper-pad dimensions, access, parasitic capacitance, strain relief and insulation; no assembled connector. Debug voltage pad is target reference.'
            dw.writerow({'References':','.join(x['ref'] for x in cs),'MPN':mpn,'LCSC':code,'Package':pkg,'Assembly':assembly,'Physical pad names':','.join(pins),'Assigned footprint':';'.join(assigned),'Symbol connectivity status':'Compare CAD export; see verification-report.json','Land-pattern status':land,'Required audit':notes,'Source':c.get('source','')})
    print(json.dumps({'physical_components':len(components)-len(flag_nets),'pages':len(laid)+1,'symbols':len(lib),'pins':len(rows),'unresolved_bom_groups':sum(not k[1] and not k[-1] for k in groups)},indent=2))

if __name__=='__main__': main()

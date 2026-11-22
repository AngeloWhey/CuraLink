"""Independently inspect the generated CuraLink board using native KiCad pcbnew.

Run with KiCad's system Python, for example:
  wsl -d Ubuntu-24.04 -e python3 /mnt/c/Users/angel/OneDrive/Documents/ChatGPT/
      curalink/hardware/rev-a/pcb/check_board.py

The board and canonical component source are read-only. This checker compares
physical references and every numbered Cu pad, reports outline/layers and
conservative placement bounds, and counts the native ratsnest. It is not DRC,
an autorouter, a signal-integrity extractor, or a fabrication-release tool.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import re
import sys
import uuid
import xml.etree.ElementTree as ET
import pcbnew

HERE = Path(__file__).resolve().parent
REV = HERE.parent
ROOT = REV.parents[1]
NM_PER_MM = 1_000_000
UUID_RE = r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}'

def parse_sexpr(path):
    """Parse KiCad lists without interpreting quoted contents as shell/code."""
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', path.read_text(encoding='utf-8'))
    stack = []
    root = None
    for token in tokens:
        if token == '(':
            child = []
            if stack: stack[-1].append(child)
            elif root is not None: raise ValueError(f'Multiple roots in {path}')
            else: root = child
            stack.append(child)
        elif token == ')':
            if not stack: raise ValueError(f'Unbalanced closing parenthesis in {path}')
            stack.pop()
        else:
            if not stack: raise ValueError(f'Atom outside root in {path}')
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    if stack or root is None: raise ValueError(f'Unbalanced or empty S-expression in {path}')
    return root

def children(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]

def child_value(node, key, default=None):
    found=children(node,key)
    return found[0][1] if found and len(found[0])>1 else default

def normalized_uuid(value):
    return str(uuid.UUID(value))

def schematic_links(schematic, netlist, expected_refs):
    """Use both actual schematic instances and native XML component UUIDs.

    KiCad 9 COMPONENT::SetFootprint() chooses GetKIIDs().front(), while
    NETLIST::GetComponentByPath() accepts any component unit UUID under its
    base sheet path. The check reports a non-default valid unit as a warning,
    and rejects absent root UUIDs, combined UUID strings, stale paths or units.
    """
    root_node=parse_sexpr(schematic)
    root_uuid=normalized_uuid(child_value(root_node,'uuid'))
    root_route='/'+root_uuid
    project=schematic.stem
    sources={str(schematic.resolve()):sha(schematic)}
    symbol_records=defaultdict(list)
    instance_errors=[]
    def visit(path,node,route,ancestry):
        if str(path.resolve()) in ancestry: raise ValueError('Cyclic schematic sheet hierarchy')
        ancestry=set(ancestry)|{str(path.resolve())}
        for symbol in children(node,'symbol'):
            symbol_uuid=normalized_uuid(child_value(symbol,'uuid'))
            if child_value(symbol,'on_board','yes')!='yes': continue
            instances=children(symbol,'instances')
            for instance in instances:
                for proj in children(instance,'project'):
                    if len(proj)<2 or proj[1]!=project: continue
                    for entry in children(proj,'path'):
                        ref=child_value(entry,'reference')
                        if ref not in expected_refs: continue
                        if entry[1]!=route:
                            instance_errors.append({'ref':ref,'symbol_uuid':symbol_uuid,
                                'actual_instance_sheet_path':entry[1],'hierarchy_sheet_path':route,
                                'error':'Actual symbol instance path differs from root/sheet hierarchy'})
                        symbol_records[ref].append({'symbol_uuid':symbol_uuid,'unit':child_value(entry,'unit'),
                            'sheet_path':route,'full_path':route+'/'+symbol_uuid,
                            'schematic':relative(path)})
        for sheet in children(node,'sheet'):
            sheet_uuid=normalized_uuid(child_value(sheet,'uuid'))
            properties={x[1]:x[2] for x in children(sheet,'property') if len(x)>2}
            child_path=(path.parent/properties['Sheetfile']).resolve()
            child_node=parse_sexpr(child_path)
            sources[str(child_path)]=sha(child_path)
            visit(child_path,child_node,route+'/'+sheet_uuid,ancestry)
    visit(schematic.resolve(),root_node,root_route,set())
    xml=ET.parse(netlist)
    xml_rows={}
    source_errors=list(instance_errors)
    for component in xml.findall('.//components/comp'):
        ref=component.attrib['ref']
        if ref not in expected_refs: continue
        sheet=component.find('sheetpath')
        timestamps=(component.findtext('tstamps')or'').split()
        if sheet is None or not timestamps:
            source_errors.append({'ref':ref,'error':'XML lacks sheet path or component timestamps'})
            continue
        steps=[normalized_uuid(x)for x in sheet.attrib['tstamps'].split('/')if x]
        if not steps or steps[0]!=root_uuid: steps.insert(0,root_uuid)
        base='/'+'/'.join(steps)
        timestamps=[normalized_uuid(x)for x in timestamps]
        candidates=[base+'/'+x for x in timestamps]
        actual={x['full_path']for x in symbol_records[ref]}
        invalid=[x for x in candidates if x not in actual]
        if invalid:
            source_errors.append({'ref':ref,'error':'XML candidate does not identify actual schematic symbol instance',
                'invalid_xml_candidates':invalid,'actual_symbol_paths':sorted(actual)})
        xml_rows[ref]={'base_sheet_path':base,'default_path':candidates[0],
            'allowed_paths':[x for x in candidates if x in actual],
            'xml_symbol_uuids':timestamps,'actual_symbol_instances':symbol_records[ref]}
    for ref in sorted(expected_refs-set(xml_rows)):
        source_errors.append({'ref':ref,'error':'Physical component absent from exported XML'})
    return root_uuid,xml_rows,source_errors,sources

def audit_uuid_definitions(board_path,fps):
    # UUID references in (path ...) or group (members ...) are intentionally not
    # counted. Only object-defining (uuid ...) expressions are definitions.
    raw=board_path.read_text(encoding='utf-8')
    definitions=defaultdict(list)
    for match in re.finditer(r'\(uuid\s+"?('+UUID_RE+r')"?\s*\)',raw):
        definitions[match.group(1).lower()].append(raw.count('\n',0,match.start())+1)
    duplicates=[{'uuid':key,'definition_lines':lines}for key,lines in definitions.items()if len(lines)>1]
    nil_definitions=definitions.get('00000000-0000-0000-0000-000000000000',[])
    native=[]
    for fp in fps:
        native.append({'kind':'footprint','ref':fp.GetReference(),'uuid':fp.m_Uuid.AsString()})
        for pad in fp.Pads():
            native.append({'kind':'pad','ref':fp.GetReference(),'pin':pad.GetNumber(),'uuid':pad.m_Uuid.AsString()})
    native_groups=defaultdict(list)
    for item in native:native_groups[item['uuid']].append(item)
    native_duplicates=[{'uuid':key,'objects':items}for key,items in native_groups.items()if len(items)>1]
    absent=[x for x in native if x['uuid'].lower()not in definitions]
    return {'passed':not(duplicates or nil_definitions or native_duplicates or absent),
        'total_object_uuid_definitions':sum(map(len,definitions.values())),
        'unique_object_uuid_definitions':len(definitions),'duplicate_definitions':duplicates,
        'nil_uuid_definition_lines':nil_definitions,'native_footprint_and_pad_objects':len(native),
        'native_footprint_and_pad_duplicate_UUIDs':native_duplicates,
        'native_footprint_or_pad_UUIDs_absent_from_saved_definitions':absent,
        'method':'Global saved-board (uuid ...) definitions plus independent native footprint/pad UUID enumeration; legitimate UUID references excluded'}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def relative(path):
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)

def bbox_dict(box):
    return {'left_mm': box.GetLeft()/NM_PER_MM,
            'top_mm': box.GetTop()/NM_PER_MM,
            'right_mm': box.GetRight()/NM_PER_MM,
            'bottom_mm': box.GetBottom()/NM_PER_MM}

def overlaps(a, b):
    dx = min(a['right_mm'],b['right_mm'])-max(a['left_mm'],b['left_mm'])
    dy = min(a['bottom_mm'],b['bottom_mm'])-max(a['top_mm'],b['top_mm'])
    return dx,dy

def copper_pad(pad):
    return pad.GetAttribute()!=pcbnew.PAD_ATTRIB_NPTH and any(
        pcbnew.IsCopperLayer(int(layer)) for layer in pad.GetLayerSet().Seq())

def placement_bounds(fp):
    fp.BuildCourtyardCaches()
    polygons = []
    for layer in [pcbnew.F_CrtYd,pcbnew.B_CrtYd]:
        poly=fp.GetCourtyard(layer)
        if poly.OutlineCount():
            polygons.append((pcbnew.LayerName(layer),bbox_dict(poly.BBox())))
    if not polygons:
        # Include neither value/reference nor hidden text in the fallback.
        layer = pcbnew.LayerName(pcbnew.B_CrtYd if fp.GetLayer()==pcbnew.B_Cu else pcbnew.F_CrtYd)
        polygons=[(layer,bbox_dict(fp.GetBoundingBox(False,False)))]
        missing=True
    else:
        missing=False
    # Conservatively project a through-hole component's body onto both sides.
    if any(p.GetAttribute()==pcbnew.PAD_ATTRIB_PTH for p in fp.Pads()):
        present={layer for layer,_ in polygons}
        for layer in [pcbnew.LayerName(pcbnew.F_CrtYd),pcbnew.LayerName(pcbnew.B_CrtYd)]:
            if layer not in present:
                polygons.append((layer,dict(polygons[0][1])))
    return polygons,missing

def write_markdown(report, path):
    transfer=report.get('transfer',{})
    placement=report.get('placement',{})
    outline=report.get('outline',{})
    routing=report.get('routing',{})
    links=report.get('schematic_links',{})
    ids=report.get('uuid_audit',{})
    lines=['# Independent CuraLink PCB validation', '',
        f"Checked {report['checked_local']} with native KiCad {report.get('kicad_version','unavailable')}.", '',
        f"**Status: {report['status']}.** This is an inspection result; it is not a fabrication release or completed board DRC.", '',
        '| Check | Result |', '|---|---|',
        f"| Expected physical references | {transfer.get('expected_physical_refs','not checked')} (schematic-only flags excluded) |",
        f"| Board footprints | {transfer.get('board_footprints','not checked')} |",
        f"| Missing / extra / duplicate references | {len(transfer.get('missing_refs',[]))} / {len(transfer.get('unexpected_refs',[]))} / {len(transfer.get('duplicate_refs',[]))} |",
        f"| Connected / intentional NC pads checked | {transfer.get('connected_pads_checked','not checked')} / {transfer.get('NC_pads_checked','not checked')} |",
        f"| Pad-transfer errors | {len(transfer.get('pad_errors',[]))} |",
        f"| Schematic path / source-link errors | {len(links.get('path_errors',[]))} / {len(links.get('source_errors',[]))} |",
        f"| Duplicate saved-board UUID definitions | {len(ids.get('duplicate_definitions',[]))} |",
        f"| Copper layers | {report.get('layers',{}).get('copper_count','not checked')} |",
        f"| Native closed-outline conversion | {outline.get('native_conversion_ok','not checked')} |",
        f"| Same-side conservative courtyard-bound overlaps | {len(placement.get('conservative_overlap_pairs',[]))} |",
        f"| Footprints with missing courtyard | {len(placement.get('missing_courtyard_refs',[]))} |",
        f"| Native unconnected ratsnest edges | {routing.get('unconnected_ratsnest_edges','not checked')} |", '',
        'RT501 is the manually attached off-board thermistor. Its two PCB wire lands must map to pins 1 = REF_1V242 and 2 = CELL_TEMP; it is not counted as a PCB SMT thermistor.', '',
        'Courtyard overlap uses axis-aligned bounding boxes on the same surface. It deliberately errs toward reporting overlap for rotated or irregular courtyards; opposite-side non-through-hole components are not treated as same-side overlaps. Native KiCad DRC must decide actual courtyard, copper, solder-mask, edge and clearance violations. Missing-courtyard bounds are a fallback warning, not a proven courtyard.', '',
        'The connectivity count is the native ratsnest after rebuilding connectivity. It includes all saved physical pads/nets, including DNP footprint nets and may change after zone fill; it is not a count of schematic nets and is not evidence of routed continuity when nonzero.', '',
        'Schematic links must contain the actual root UUID, hierarchy sheet UUIDs and one valid symbol UUID. Multi-unit components may link to any exported unit under their exported base sheet; a first-symbol default difference is reported separately. XML identifiers are also checked against the actual schematic instances. Saved UUID definitions are checked globally, including footprint child objects. This structural check does not execute the GUI Update PCB from Schematic workflow.', '',
        'Detailed reference lists, per-pin errors, footprint bounds, pad centers outside the outline, source hashes and limits are preserved in validation.json. The board and canonical source were not modified.']
    if report.get('errors'):
        lines+=['','Material errors:','']+[f'- {x}'for x in report['errors']]
    path.write_text('\n'.join(lines)+'\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--board',type=Path,default=REV/'curalink-rev-a.kicad_pcb')
    parser.add_argument('--canonical',type=Path,default=REV/'components-merged.json')
    parser.add_argument('--schematic',type=Path,default=REV/'curalink-rev-a.kicad_sch')
    parser.add_argument('--netlist',type=Path,default=REV/'curalink-rev-a.net.xml')
    parser.add_argument('--output',type=Path,default=HERE/'validation.json')
    args=parser.parse_args()
    if not args.board.is_file():
        print('Board is not present; no validation has been run:',args.board)
        return 2
    components=json.loads(args.canonical.read_text())['components']
    expected=[c for c in components if c.get('kind')!='flag']
    canonical_duplicates=[x for x,n in Counter(c['ref']for c in expected).items()if n>1]
    if canonical_duplicates:
        raise ValueError('Canonical duplicate physical references: '+str(canonical_duplicates))
    expected_map={c['ref']:c for c in expected}
    before_hash=sha(args.board)
    board=pcbnew.LoadBoard(str(args.board))
    if board is None:
        raise ValueError('Native KiCad failed to load board')
    fps=list(board.GetFootprints())
    root_uuid,link_rows,link_source_errors,schematic_sources=schematic_links(
        args.schematic,args.netlist,set(expected_map))
    uuid_audit=audit_uuid_definitions(args.board,fps)
    path_errors=[]
    path_default_warnings=[]
    byref=defaultdict(list)
    for fp in fps:byref[fp.GetReference()].append(fp)
    refs=set(byref)
    duplicate_refs=sorted(ref for ref,items in byref.items()if len(items)>1)
    missing_refs=sorted(set(expected_map)-refs)
    extra_refs=sorted(refs-set(expected_map))
    errors=[]
    pad_errors=[]
    ignored=[]
    value_warnings=[]
    population_warnings=[]
    connected_count=nc_count=numbered_cu_count=0
    rt501=None
    perref=[]
    for ref in sorted(set(expected_map)&refs):
        c=expected_map[ref]
        if len(byref[ref])!=1:
            continue
        fp=byref[ref][0]
        actual_path=fp.GetPath().AsString()
        link=link_rows.get(ref)
        if link is None or actual_path not in link['allowed_paths']:
            path_errors.append({'ref':ref,'actual_path':actual_path,
                'default_expected_path':link['default_path']if link else None,
                'allowed_paths':link['allowed_paths']if link else [],
                'error':'Footprint path does not identify an exported actual symbol under the root and sheet hierarchy'})
        elif actual_path!=link['default_path']:
            path_default_warnings.append({'ref':ref,'actual_path':actual_path,
                'default_path':link['default_path'],
                'note':'Valid alternate unit UUID accepted by KiCad component-path lookup; new default footprint uses first XML UUID'})
        pads=defaultdict(list)
        for pad in fp.Pads():
            if not copper_pad(pad):
                ignored.append({'ref':ref,'number':pad.GetNumber(),
                    'reason':'NPTH or non-copper pad; includes unnumbered paste-only apertures',
                    'layers':[pcbnew.LayerName(int(layer))for layer in pad.GetLayerSet().Seq()]})
                continue
            number=pad.GetNumber()
            if not number:
                pad_errors.append({'ref':ref,'pin':'','error':'Unnumbered copper pad has no canonical physical pin'})
                continue
            pads[number].append(pad)
            numbered_cu_count+=1
        expected_pins=set(c['pins'])
        for pin in sorted(expected_pins-set(pads)):
            pad_errors.append({'ref':ref,'pin':pin,'error':'Missing numbered copper land','expected_net':c['pins'][pin]})
        for pin in sorted(set(pads)-expected_pins):
            pad_errors.append({'ref':ref,'pin':pin,'error':'Extra numbered copper land',
                'actual_nets':[p.GetNetname()for p in pads[pin]]})
        for pin in sorted(expected_pins&set(pads)):
            want=c['pins'][pin]
            for pad in pads[pin]:
                net=pad.GetNetname()
                if want is None:
                    nc_count+=1
                    if pad.GetNetCode()!=0 or net:
                        pad_errors.append({'ref':ref,'pin':pin,'error':'Intentional NC pad carries a net',
                            'expected_net':None,'actual_net':net,'actual_netcode':pad.GetNetCode()})
                else:
                    connected_count+=1
                    if net!=want:
                        pad_errors.append({'ref':ref,'pin':pin,'error':'Connected pad net differs from canonical',
                            'expected_net':want,'actual_net':net,'actual_netcode':pad.GetNetCode()})
        if fp.GetValue()!=str(c.get('value','')):
            value_warnings.append({'ref':ref,'canonical_value':c.get('value'),'board_value':fp.GetValue()})
        row={'ref':ref,'footprint_id':str(fp.GetFPID().GetLibItemName()),'value':fp.GetValue(),
            'side':pcbnew.LayerName(fp.GetLayer()),'x_mm':fp.GetPosition().x/NM_PER_MM,
            'y_mm':fp.GetPosition().y/NM_PER_MM,'rotation_deg':fp.GetOrientationDegrees(),
            'canonical_assembly':c.get('assembly'),'canonical_populated':c.get('populated',True),
            'numbered_Cu_pad_count':sum(len(v)for v in pads.values()),
            'distinct_numbered_Cu_pins':sorted(pads),'DNP_attribute':fp.IsDNP()}
        row['schematic_path']=actual_path
        row['footprint_uuid']=fp.m_Uuid.AsString()
        perref.append(row)
        if bool(fp.IsDNP())==bool(c.get('populated',True)):
            population_warnings.append({'ref':ref,'canonical_populated':c.get('populated',True),
                'board_DNP_attribute':bool(fp.IsDNP()),
                'note':'Review BOM/CPL exclusion and intended population before assembly'})
        if ref=='RT501':
            rt501={'canonical_assembly':c.get('assembly'),'canonical_pin_nets':c['pins'],
                'footprint':row['footprint_id'],
                'actual_pin_nets':{pin:[p.GetNetname()for p in group]for pin,group in pads.items()},
                'passed_two_wire_lands':set(pads)=={'1','2'}and c.get('assembly')=='OFFBOARD_MANUAL'
                    and all(p.GetNetname()==c['pins'][pin]for pin,group in pads.items()for p in group)}
    if missing_refs:errors.append(f'{len(missing_refs)} canonical physical references are missing')
    if extra_refs:errors.append(f'{len(extra_refs)} unexpected physical references are present')
    if duplicate_refs:errors.append(f'{len(duplicate_refs)} board references are duplicated')
    if pad_errors:errors.append(f'{len(pad_errors)} pad-to-net / physical land errors')
    if path_errors:errors.append(f'{len(path_errors)} footprint schematic paths are invalid or stale')
    if link_source_errors:errors.append(f'{len(link_source_errors)} actual schematic / exported XML linkage errors')
    if not uuid_audit['passed']:errors.append('Saved-board object UUID audit failed; duplicate/nil/missing definitions require correction')
    if rt501 is None or not rt501['passed_two_wire_lands']:
        errors.append('RT501 off-board thermistor wire-land mapping failed')

    layer_names=[board.GetLayerName(int(x))for x in board.GetEnabledLayers().CuStack()]
    copper_count=board.GetCopperLayerCount()
    if copper_count!=4:errors.append(f'Expected four copper layers; found {copper_count}')
    outline=pcbnew.SHAPE_POLY_SET()
    outline_ok=board.GetBoardPolygonOutlines(outline,None,False,False)
    outlines=[]
    if outline_ok:
        for i in range(outline.OutlineCount()):
            chain=outline.COutline(i)
            points=[chain.CPoint(j)for j in range(chain.PointCount())]
            outlines.append({'index':i,'closed':chain.IsClosed(),'vertices':chain.PointCount(),
                'area_mm2':abs(chain.Area())/(NM_PER_MM**2),'bounds':bbox_dict(chain.BBox()),
                'coordinates_mm':[[p.x/NM_PER_MM,p.y/NM_PER_MM]for p in points]})
        if not outlines or any(not row['closed']or row['area_mm2']<=0 for row in outlines):
            errors.append('Native outline has an open or zero-area contour')
        elif len(outlines)!=1:
            errors.append(f'Expected one main board outer contour; found {len(outlines)}')
    else:
        errors.append('Native KiCad closed-board-outline conversion failed')
    placement=[]
    missing_courtyards=[]
    outside=[]
    for fp in fps:
        boundaries,fallback=placement_bounds(fp)
        if fallback:missing_courtyards.append(fp.GetReference())
        if outline_ok:
            for p in fp.Pads():
                if copper_pad(p)and not outline.Contains(p.GetPosition()):
                    outside.append({'ref':fp.GetReference(),'pin':p.GetNumber(),
                        'x_mm':p.GetPosition().x/NM_PER_MM,'y_mm':p.GetPosition().y/NM_PER_MM})
        for layer,bounds in boundaries:
            placement.append({'ref':fp.GetReference(),'side':layer,'bounds':bounds,'fallback':fallback})
    overlap_pairs=[]
    for i,a in enumerate(placement):
        for b in placement[i+1:]:
            if a['ref']==b['ref']or a['side']!=b['side']:continue
            dx,dy=overlaps(a['bounds'],b['bounds'])
            if dx>1e-6 and dy>1e-6:
                overlap_pairs.append({'ref_a':a['ref'],'ref_b':b['ref'],'side':a['side'],
                    'overlap_x_mm':dx,'overlap_y_mm':dy,'bounds_overlap_area_mm2':dx*dy,
                    'uses_fallback':a['fallback']or b['fallback'],
                    'classification':'Conservative bounding-box warning; native DRC decides real courtyard violation'})
    if outside:errors.append(f'{len(outside)} copper-pad centers are outside the native board outline')

    connectivity_ok=board.BuildConnectivity()
    conn=board.GetConnectivity()
    conn.RecalculateRatsnest()
    unconnected=int(conn.GetUnconnectedCount(False))
    track_count=via_count=0
    for item in board.GetTracks():
        if isinstance(item,pcbnew.PCB_VIA):via_count+=1
        else:track_count+=1
    transfer_pass=not(missing_refs or extra_refs or duplicate_refs or pad_errors)and rt501 is not None and rt501['passed_two_wire_lands']
    warnings=[]
    if overlap_pairs:warnings.append(f'{len(overlap_pairs)} same-side conservative courtyard-bound overlap pairs require DRC review')
    if missing_courtyards:warnings.append(f'{len(missing_courtyards)} footprints have no parsed courtyard')
    if unconnected:warnings.append(f'{unconnected} native ratsnest edges are unconnected; routing is incomplete')
    if value_warnings:warnings.append(f'{len(value_warnings)} board value text differs from canonical')
    if population_warnings:warnings.append(f'{len(population_warnings)} board DNP attributes differ from canonical population')
    if path_default_warnings:warnings.append(f'{len(path_default_warnings)} valid multi-unit paths differ from the first-UUID KiCad default')
    if not connectivity_ok:errors.append('Native connectivity rebuild returned false')
    status='FAIL_TRANSFER_OR_STRUCTURE'if errors else'PASS_TRANSFER_AND_STRUCTURE_WITH_ROUTING_REVIEW_OPEN'
    report={'status':status,'checked_local':datetime.now(ZoneInfo('America/New_York')).isoformat(),
        'kicad_version':pcbnew.GetBuildVersion(),
        'sources':{'board':{'path':relative(args.board),'sha256':before_hash},
            'canonical':{'path':relative(args.canonical),'sha256':sha(args.canonical)},
            'schematic':{'path':relative(args.schematic),'sha256':sha(args.schematic)},
            'exported_netlist':{'path':relative(args.netlist),'sha256':sha(args.netlist)},
            'schematic_files':[{'path':relative(Path(path)),'sha256':digest}for path,digest in schematic_sources.items()],
            'checker':{'path':relative(Path(__file__).resolve()),'sha256':sha(Path(__file__).resolve())}},
        'transfer':{'passed':bool(transfer_pass),'canonical_total_entries':len(components),
            'excluded_schematic_flags':[c['ref']for c in components if c.get('kind')=='flag'],
            'expected_physical_refs':len(expected),'board_footprints':len(fps),
            'missing_refs':missing_refs,'unexpected_refs':extra_refs,'duplicate_refs':duplicate_refs,
            'numbered_Cu_pads_inspected':numbered_cu_count,'connected_pads_checked':connected_count,
            'NC_pads_checked':nc_count,'pad_errors':pad_errors,'ignored_non_copper_or_NPTH_pads':ignored,
            'value_text_warnings':value_warnings,'DNP_attribute_warnings':population_warnings,
            'RT501':rt501,'footprints':perref},
        'schematic_links':{'passed':not(path_errors or link_source_errors),'root_uuid':root_uuid,
            'physical_refs_checked':len(set(expected_map)&refs),'path_errors':path_errors,
            'source_errors':link_source_errors,'valid_alternate_unit_default_warnings':path_default_warnings,
            'expected_component_paths':link_rows,
            'primary_sources':[
                'https://dev-docs.kicad.org/en/file-formats/sexpr-schematic/',
                'https://raw.githubusercontent.com/KiCad/kicad-source-mirror/9.0.9/eeschema/sch_sheet_path.h',
                'https://raw.githubusercontent.com/KiCad/kicad-source-mirror/9.0.9/pcbnew/netlist_reader/pcb_netlist.cpp'],
            'note':'COMPONENT::SetFootprint uses first symbol UUID; NETLIST::GetComponentByPath accepts any listed unit UUID under the same base path. GUI schematic-to-board update was not executed.'},
        'uuid_audit':uuid_audit,
        'layers':{'copper_count':copper_count,'expected_copper_count':4,'enabled_copper_layer_names':layer_names},
        'outline':{'native_conversion_ok':bool(outline_ok),'contours':outlines,
            'hole_count':sum(outline.HoleCount(i)for i in range(outline.OutlineCount()))if outline_ok else None,
            'note':'Native outline chaining/conversion, not a replacement for DRC self-intersection or board-edge clearance checks'},
        'placement':{'missing_courtyard_refs':missing_courtyards,'bounds':placement,
            'conservative_overlap_pairs':overlap_pairs,'copper_pad_centers_outside_outline':outside},
        'routing':{'connectivity_build_ok':bool(connectivity_ok),'unconnected_ratsnest_edges':unconnected,
            'track_segments':track_count,'vias':via_count,'zones':len(list(board.Zones())),
            'note':'DNP pads included; counts reflect saved board and current zone connectivity. No zone fill or board save performed.'},
        'errors':errors,'warnings':warnings,
        'limits':['Native DRC is separate and authoritative for actual clearance/overlap errors',
            'Bounding-box overlaps may over-report rotated, concave or irregular courtyards',
            'Pad-center containment does not establish full pad/trace/courtyard edge clearance',
            'No routing capacitance/inductance, crosstalk, RF impedance, thermal or package extraction',
            'Physical pad-to-net transfer does not qualify component suffix, land-pattern assembly or analog behavior',
            'No fabrication or safety release; incomplete routing and existing schematic qualification gates remain open']}
    if sha(args.board)!=before_hash:raise ValueError('Board changed while checking; results are stale, rerun')
    for path,digest in schematic_sources.items():
        if sha(Path(path))!=digest:raise ValueError('Schematic changed while checking; results are stale, rerun')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2))
    write_markdown(report,args.output.with_suffix('.md'))
    print(json.dumps({'status':status,'physical_refs':len(fps),'expected_physical_refs':len(expected),
        'pad_errors':len(pad_errors),'NC_pads_checked':nc_count,'copper_layers':copper_count,
        'schematic_path_errors':len(path_errors),'schematic_source_errors':len(link_source_errors),
        'UUID_audit_passed':uuid_audit['passed'],'saved_UUID_definitions':uuid_audit['total_object_uuid_definitions'],
        'outline_conversion_ok':bool(outline_ok),'courtyard_bounds_overlap_pairs':len(overlap_pairs),
        'unconnected_ratsnest_edges':unconnected,'errors':errors,'warnings':warnings},indent=2))
    return 1 if errors else 0

if __name__=='__main__':sys.exit(main())

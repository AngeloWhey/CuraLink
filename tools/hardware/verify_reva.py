"""Compare CAD-exported connectivity with the independently maintained pin maps.

Also check consequential topology invariants. This is a schematic transfer
check, not a simulation, footprint audit or certification of hardware behavior.
"""
from pathlib import Path
from collections import Counter
import csv
import json
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'hardware/rev-a'

def main():
    source=json.loads((OUT/'components-merged.json').read_text())
    parts={c['ref']:c for c in source['components'] if c.get('kind')!='flag'}
    xml=ET.parse(OUT/'curalink-rev-a.net.xml').getroot()
    actual={}
    failures=[]
    for net in xml.findall('./nets/net'):
        for pin in net.findall('node'):
            key=(pin.attrib['ref'],pin.attrib['pin'])
            if key in actual:
                failures.append(f'Multiple nets for {key}')
            actual[key]=net.attrib['name']
    cadrefs={c.attrib['ref'] for c in xml.findall('./components/comp') if not c.attrib['ref'].startswith('#')}
    if cadrefs != set(parts):
        failures.append(f'Component set mismatch: {set(parts)^cadrefs}')
    library_pins={}
    for lib in xml.findall('./libparts/libpart'):
        library_pins[(lib.attrib['lib'],lib.attrib['part'])]={p.attrib['num'] for p in lib.findall('./pins/pin')}
    for comp in xml.findall('./components/comp'):
        ref=comp.attrib['ref']
        if ref not in parts: continue
        ls=comp.find('libsource')
        pins=library_pins[(ls.attrib['lib'],ls.attrib['part'])]
        if pins != set(parts[ref]['pins']):
            failures.append(f'{ref}: CAD symbol physical pin set {pins} != source {set(parts[ref]["pins"])}')
    nc=0
    connected=0
    for ref,c in parts.items():
        for pin,expected in c['pins'].items():
            got=actual.get((ref,pin))
            if expected is None:
                nc+=1
                if got and not got.startswith('unconnected-'):
                    failures.append(f'{ref}.{pin} intentional NC joined {got}')
            else:
                connected+=1
                if expected != got:
                    failures.append(f'{ref}.{pin}: expected {expected}, exported {got}')
    checks=[]
    def expect(label,condition):
        checks.append({'check':label,'passed':bool(condition)})
        if not condition: failures.append(label)
    def pin(ref,p): return actual.get((ref,str(p)))
    expect('MCU VCAP is a decoupled internal output, separate from supplied rails',
           pin('U401',44)=='VCAP_OUT' and pin('U401',44) not in ['AVDD_3V0','DVDD_3V0'])
    expect('MCU PA internal output is separate from supplied rails',pin('U401',38)=='VDDHPA_OUT')
    expect('Eight distinct ADC inputs receive eight AFE channels',
           [pin('U401',p) for p in [3,4,5,7,10,12,13,14]]==[f'ADC_IN_{i}' for i in range(1,9)])
    expect('RUN PMOS isolation has common sources, opposite outer drains and common gate',
           pin('Q501',2)==pin('Q502',2)=='PMOS_COMMON_SOURCE' and
           pin('Q501',3)=='BAT_RUN' and pin('Q502',3)=='SYS_PRE' and
           pin('Q501',1)==pin('Q502',1)=='SW_GATE')
    expect('Charge CE has all three required NMOS permissions in series',
           pin('Q504',1)=='CHARGE_READY' and pin('Q505',1)=='TEMP_COLD_OK' and
           pin('Q506',1)=='TEMP_HOT_OK' and pin('Q504',2)==pin('Q505',3) and
           pin('Q505',2)==pin('Q506',3) and pin('Q506',2)=='GND')
    expect('Analog regulator waits for digital good',pin('U512',3)=='DIGITAL_GOOD')
    expect('Optional RF receiver input is isolated in initial bench build',
           parts['R542']['populated'] is False and parts['R543']['populated'] is True)
    expect('Unqualified independent cell PCM is not populated',parts['U514']['populated'] is False)
    expect('Antenna second pad remains electrically isolated',parts['AE401']['pins'].get('2') is None)
    for ref,output,limit,enable,input_net in [
        ('U502','CHG_IN','WPT_EF_ILIM','WPT_EF_EN','WPT_PROTECTED'),
        ('U511','SYS_RAW','SYS_EF_ILIM','RUN_ENABLE','SYS_PRE')]:
        expect(ref+' TPS25200 pins match TI Rev F Table 4-1',
               pin(ref,1)==output and pin(ref,2)==limit and pin(ref,4)==enable
               and pin(ref,5)==pin(ref,7)=='GND' and pin(ref,6)==input_net)
    expect('SS14 manufacturer anode1/cathode2 sends cathode to protected input',pin('D501',1)=='WPT_RAW' and pin('D501',2)=='WPT_PROTECTED')
    expect('R511 tolerance stays below recommended TPS25200 1.1Meg upper limit',parts['R511']['value']=='1Meg')
    expect('RF tee uses series capacitor, shunt inductor, series inductor',
           set(parts['C423']['pins'].values())=={'ANT_T_IN','ANT_T_MID'} and
           set(parts['L401']['pins'].values())=={'ANT_T_MID','GND'} and
           set(parts['L402']['pins'].values())=={'ANT_T_MID','ANT_FEED'})
    for i in range(1,9):
        driven=[c for c in parts.values() if c['ref'].startswith('R') and
                set(c['pins'].values())=={f'AFE_OUT_{i}',f'ADC_IN_{i}'}]
        expect(f'ADC{i} uses qualified-model 150 ohm isolation candidate',len(driven)==1 and driven[0]['value'].startswith('150ohm'))
        caps=[c for c in parts.values() if c['ref'].startswith('C') and
              set(c['pins'].values())=={f'ADC_IN_{i}','GND'}]
        expect(f'ADC{i} has 470 pF local C0G reservoir',len(caps)==1 and caps[0]['value'].startswith('470pF'))
    for ref in ['U110','U111','U112']:
        expect(f'{ref} ESD grounds and mechanical NC pads follow DQA mapping',
               pin(ref,3)==pin(ref,8)=='GND' and all(parts[ref]['pins'][str(p)] is None for p in [6,7,9,10]))
    erc=json.loads((OUT/'erc-report.json').read_text())
    violations=[v for s in erc['sheets'] for v in s['violations']]
    expect('KiCad ERC has no errors, warnings or excluded findings',not violations)
    sourcing=[]
    for c in parts.values():
        if c.get('populated') is False or c.get('kind') in ['pad','copper_field']: continue
        if not re.fullmatch(r'C\d+',str(c.get('lcsc',''))): sourcing.append(c['ref'])
    inventory_report=json.loads((OUT/'procurement/stock-audit-2026-10-02.json').read_text(encoding='utf-8'))
    inventory={r['lcsc']:r for r in inventory_report['records']}
    purchased_parts=[c for c in parts.values() if c.get('kind') not in ['pad','copper_field']]
    expected_skus={c['lcsc'] for c in purchased_parts}
    inventory_failures=[]
    for sku in expected_skus:
        record=inventory.get(sku,{})
        components=[c for c in purchased_parts if c['lcsc']==sku]
        fitted=sum(c.get('populated') is not False for c in components)
        optional=len(components)-fitted
        if (record.get('status')!='STOCK_SUFFICIENT_ONE_BOARD' or
            record.get('populated_quantity')!=fitted or record.get('optional_quantity')!=optional or
            {c['mpn'] for c in components}!=set(record.get('expected_mpns',[]))):
            inventory_failures.append(sku)
    expect('All exact BOM SKUs and fitted/DNP quantities match dated sufficient LCSC inventory',not inventory_failures)
    report={
        'status':'PASS' if not failures else 'FAIL',
        'scope':'CAD transfer, topology invariants, ERC and saved BOM stock; excludes analog/nonlinear/PCB safety validation',
        'kicad_version':erc['kicad_version'],
        'physical_components':len(parts),'connected_pins_compared':connected,'intentional_NC_pins_compared':nc,
        'erc_violations':len(violations),'topology_checks':checks,'failures':failures,
        'populated_PCB_parts_without_LCSC':sourcing,
        'bom_LCSC_codes_complete':not sourcing,
        'inventory_date':inventory_report['checked_date'],'bom_unique_SKUs':len(expected_skus),
        'bom_stock_sufficient_one_board':not inventory_failures,
        'inventory_failures':inventory_failures,
        'external_unconfirmed_sourcing':inventory_report['summary']['unconfirmed_skus'],
        'release_status':'ENGINEERING REVIEW; NOT FABRICATION RELEASED',
        'release_gates':['Unchanged >=10 MOhm full-band loading requirement is not met by candidate',
                         'Shared VMID/package/PCB crosstalk and stability; proposed -60 dB criterion is unaccepted and unmet',
                         'ADC/BLE ownership and timing, measured signal/noise/RF/power qualification',
                         'Globally orderable cell and compatible independent protection or approved protected pack',
                         'Altium import connectivity, exact land patterns, assembly quote and PCB DRC',
                         'Qualified RF-to-DC receiver; initial build uses bench DC inputs']}
    (OUT/'verification-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['topology_checks','release_gates']},indent=2))
    if failures: raise SystemExit(1)

if __name__=='__main__': main()

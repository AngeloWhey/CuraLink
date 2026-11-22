"""Write schematic-net placement constraints; does not assign PCB coordinates."""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def main():
    parts = json.loads((ROOT / 'hardware/rev-a/components-merged.json').read_text())['components']
    regions = []
    def add(region, priority, refs, nets, rule, verify):
        regions.append({'region': region, 'priority': priority, 'references': ','.join(refs),
                        'nets': ','.join(nets), 'layout_constraint': rule, 'verification': verify,
                        'status': 'CANDIDATE PCB AVAILABLE; ROUTING/BEHAVIOR REVIEW OPEN' if (ROOT/'hardware/rev-a/curalink-rev-a.kicad_pcb').exists() else 'PROPOSED ROUTING CONSTRAINT; GEOMETRY NOT AVAILABLE'})
    add('Connector and input current limit', 'HIGH', ['J301', 'U110', 'U111', 'U112'],
        ['FFC_CH1..FFC_CH8', 'FFC_REF', 'GND'],
        'Put ESD at connector with short ground returns. Retain interleaved ground contacts; keep charger/debug current out of FFC ground routing. Audit cable contact face and pin 1 end to end.',
        'FFC continuity; cable impedance/capacitance and source mismatch; actual protection return loop.')
    add('Preamp input and bias returns', 'CRITICAL', ['U101', 'U102', 'U109', 'R1002', 'C1001'],
        ['CH1_PLUS..CH8_PLUS', 'REF_PLUS', 'CH1_LIMIT..CH8_LIMIT'],
        'Keep input capacitor, 22M bias return and amplifier input compact. Avoid parallel/overlapping late-output, RF or digital traces. Keep surfaces clean; any guard/copper opening needs leakage and capacitance evaluation.',
        'Added coupling, loading and leakage; parasitics include test pads and probes. No arbitrary spacing guarantees.')
    add('Shared input reference', 'CRITICAL', ['U109'], ['REF_PLUS', 'REF_PRE'],
        'REF is a ninth analog signal, not ground or VMID. Match CH/REF protection and source geometry. Shield it from RF, ADC and amplified outputs; distribute its low-impedance preamp output compactly.',
        'Common-mode rejection with actual cable; coherent artifacts across all channels; large REF offset recovery.')
    add('Difference stage feedback and balance', 'CRITICAL', ['U103', 'U104', 'R1006', 'R1007', 'R1009', 'R1010'],
        ['CHn_DIFF_MINUS', 'CHn_DIFF_PLUS', 'CHn_DIFF_FB_MID', 'CHn_DIFF_BAL_MID', 'CHn_HP'],
        'Keep 909k pairs and input arms compact and geometrically matched. Minimize unintended feedback capacitance and aggressor capacitance into the summing nodes. Do not route digital signals through these networks.',
        'Parasitic mismatch/CMRR and gain/phase; input current sensitivity is distinct from literal node impedance.')
    add('Filter and amplified outputs', 'HIGH', ['U105', 'U106', 'U107', 'U108'],
        ['CHn_LP1_A', 'CHn_LP1_PLUS', 'CHn_LP2_A', 'CHn_LP2_PLUS', 'AFE_OUT_1..AFE_OUT_8'],
        'Flow forward from preamp through difference/filter to ADC. Keep Sallen-Key loops compact and output routes separated from input/REF networks, including on adjacent layers.',
        'Filter corners/Q, output-to-input coupling and stability. Avoid vias/stubs within feedback loops where practical.')
    add('ADC charge reservoir and VDDA', 'HIGH', ['U401', 'R401..R408', 'C413..C420', 'C406', 'C407'],
        ['ADC_IN_1..ADC_IN_8', 'AVDD_3V0', 'GND'],
        'Put each 470pF reservoir at its ADC pad and the 150R isolation before it. Give reservoirs and local VDDA bypass short quiet returns. Route debug edges away from this group.',
        'Real channel-history/kickback under worst sequence and BLE activity; do not assume driver-only stress proves ADC accuracy.')
    vmid_refs = [c['ref'] for c in parts if c.get('kind') in ('R', 'C') and
                 any(n in ('VMID', 'VMID_BUF', 'VMID_RAW') for n in c.get('pins', {}).values())]
    # Canonical kinds may use words instead of letter prefixes: retain exact shared-support references from nets.
    vmid_refs += [c['ref'] for c in parts if c['ref'].startswith(('R','C')) and
                  set(c.get('pins', {}).values()) & {'VMID','VMID_BUF','VMID_RAW'}]
    add('Midpoint buffer and shared distribution', 'CRITICAL', sorted(set(['U109'] + vmid_refs)),
        ['VMID_RAW', 'VMID_BUF', 'VMID'],
        'Place divider/filter/buffer/isolation/reservoir together. Give channel returns low-impedance branches to a compact bias distribution; do not share a long narrow VMID trace with high stage currents.',
        'Shared-node AC current sensitivity and multi-channel saturation recovery; actual effective reservoir capacitance and buffer stability.')
    add('Analog and digital supply loops', 'HIGH', ['U512', 'U513', 'U401', 'U101..U109'],
        ['SYS_RAW', 'AVDD_3V0', 'DVDD_3V0', 'GND'],
        'Retain local bypass at every IC. Separate radio/digital and analog supply-current loops by placement over a continuous return plane. Do not isolate GND with a narrow neck or plane split under crossing signals.',
        'AVDD/VDDA ripple, ground impedance and BLE-correlated artifacts. Separate LDOs do not provide ground isolation.')
    add('Charger, eFuses, PMOS and discharge', 'HIGH', ['U501', 'U502', 'U511', 'Q501', 'Q502', 'Q507', 'Q508'],
        ['WPT_RAW', 'WPT_PROTECTED', 'CHG_IN', 'PACK+', 'SYS_PRE', 'SYS_RAW', 'AVDD_3V0', 'DVDD_3V0'],
        'Keep source/charger/reservoir and discharge currents in compact local loops away from input/REF/bias returns. Verify physical pin/EP maps and switch orientation. Keep RF receiver input DNP initially.',
        'Source fault peaks, simultaneous rails/CE, shutdown and debugger/DAC backfeed; no raw-RF or cell fault release.')
    add('Control comparators and thermistor harness', 'MEDIUM', ['U504..U507', 'U515', 'RT501'],
        ['BAT_SENSE', 'WPT_SENSE', 'CELL_TEMP', 'REF_1V242', 'CTRL_3V0'],
        'Keep high-resistance dividers/reference routes out of switching/discharge/RF loops. Use quiet returns and retain the cell-mounted NTC harness; review any added filtering against transition timing.',
        'Field/UVLO/temperature threshold chatter and mode exclusion during WPT ramps and brownout.')
    add('RF feed, balun/filter and antenna', 'CRITICAL', ['U401', 'U402', 'R417', 'R418', 'C423', 'L401', 'L402', 'AE401'],
        ['MCU_RF', 'RF_50OHM', 'ANT_T_IN', 'ANT_T_MID', 'ANT_FEED'],
        'Derive 63-ohm MCU-to-filter and 50-ohm output trace geometry for the actual stackup using ST guidance. Keep matching and ground vias compact, selection stubs minimal, antenna vendor all-layer clearance free of battery/coil/copper.',
        'Stackup/return continuity, RF assembly options and final mechanical antenna performance. Reference dimensions are not universal.')
    add('Oscillators and internal regulator outputs', 'HIGH', ['Y401', 'Y402', 'C408', 'C409'],
        ['HSE_IN', 'HSE_OUT', 'LSE_IN', 'LSE_OUT', 'VCAP_OUT', 'VDDHPA_OUT'],
        'Keep oscillator loops and required bypass connections compact and away from AFE. No unrelated signals beneath crystal network. VCAP/VDDHPA are internal outputs; retain exact local capacitors and do not use as supply rails.',
        'Crystal startup/load and supply-loop geometry; vendor ground/via requirements.')
    with (OUT / 'sensitive-regions.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(regions[0]))
        writer.writeheader()
        writer.writerows(regions)
    print(f'Wrote {len(regions)} schematic-based region constraints; no PCB placement implied.')


if __name__ == '__main__':
    main()

"""Classify the canonical power circuit for the proposed PCB floorplan.

No canonical schematic changes or board creation. Coordinates are suggestions
for the parent's 80x74 mm board, not a routing or signal-integrity result.
"""
from pathlib import Path
import hashlib
import json

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
SOURCE=ROOT/"hardware/rev-a/power/power-components.json"
canonical=json.loads(SOURCE.read_text(encoding="utf-8"))["components"]

bins={
    "input":"U502 D501 R510 R511 R512 C501 C502".split(),
    "charger":"U501 Q504 Q505 Q506 R501 R503 R504 R505 R506 R507 R508 R509 C503 C504 C505".split(),
    "ctrl":"U503 U504 U505 U508 U509 U510 U515 D502 D503 D504 D507 D508 D509 R513 R514 R515 R516 R517 R518 R519 R520 R526 R527 R528 R529 R530 R549 R550 R551 C506 C507 C508 C509 C512 C513 C514 C518 C519 C520 C521 C522 C531 C532".split(),
    "battery-switch":"U511 Q501 Q502 Q503 R502 R531 R532 R533 R534 R535 C523 C524".split(),
    "analog-ldo":"U512 Q507 R536 R538 R540 R541 R544 C525 C526 C529".split(),
    "digital-ldo":"U513 Q508 R537 R539 C527 C528".split(),
    "temperature":"U506 U507 R521 R522 R523 R524 R525 C510 C511 C515 C516 C517 RT501".split(),
    "pcm":"U514 Q509 Q510 R545 R546 R547 R548 C530".split(),
    "benchpads":"J501 J502 J503 J504 R542 R543".split()
}
mapping={ref:g for g,refs in bins.items() for ref in refs}
actual={c["ref"] for c in canonical}
assert len(mapping)==sum(map(len,bins.values())),"Duplicate assignment"
assert set(mapping)==actual,("missing",actual-set(mapping),"extra",set(mapping)-actual)

centers={"input":[70,59],"charger":[61,62],"ctrl":[40,62],
         "battery-switch":[24,64],"analog-ldo":[28,54.5],
         "digital-ldo":[49,54.5],"temperature":[54,68],
         "pcm":[13.5,66],"benchpads":[75,67]}

anchors={"U502":[69,59],"D501":[73,59],"U501":[61,61],
         "U503":[46,61],"U504":[36,61],"U505":[44,64],
         "U506":[53,67],"U507":[57,67],"U508":[36,67],
         "U509":[40,68],"U510":[44,68],"U511":[27,64],
         "U512":[28,54.5],"U513":[49,54.5],"U515":[38,55.5],
         "U514":[13.5,66],"Q501":[19,63],"Q502":[22,63],
         "Q503":[23,68],"Q504":[63,65],"Q505":[60.5,65],
         "Q506":[58,65],"Q507":[29,58],"Q508":[51,58],
         "Q509":[12,69.5],"Q510":[15,69.5],
         "J501":[6,61],"J504":[6,70],"J502":[75.5,64],
         "J503":[75.5,70],"R542":[72,64],"R543":[72,70]}

# Nets and values alone cannot distinguish otherwise identical local CTRL rail
# bypass capacitors. The design file assigns these explicitly to their host IC.
local={
    "C501":{"near_ref":"U502","near_pin":"6","purpose":"input bypass loop with EP7/GND5; post-D501 WPT_PROTECTED"},
    "C502":{"near_ref":"U502","near_pin":"1","purpose":"output reservoir at CHG_IN, also feed U501 IN10 directly"},
    "C503":{"near_ref":"U501","near_pin":"1","purpose":"charger-local SYS bypass; never merge CHG_SYS with SYS_RAW"},
    "C504":{"near_ref":"U501","near_pin":"2","purpose":"charger BAT bypass and short path to R501"},
    "C505":{"near_ref":"U501","near_pin":"8","purpose":"ISET compensation; R505/C505 close to ISET pin"},
    "R503":{"near_ref":"U501","near_pin":"7","purpose":"VSET precision return to local charger ground"},
    "R504":{"near_ref":"U501","near_pin":"8","purpose":"ISET precision ground return, not charger-current return segment"},
    "R505":{"near_ref":"U501","near_pin":"8","purpose":"ISET compensation resistor"},
    "R506":{"near_ref":"U501","near_pin":"6","purpose":"internal charger TS termination; external NTC comparators control CE separately"},
    "R507":{"near_ref":"U501","near_pin":"4","purpose":"default CE disable pull-up, Q504/Q505/Q506 series pull-down adjacent"},
    "C506":{"near_ref":"U503","near_pin":"1","purpose":"CTRL_INPUT local bypass after D502"},
    "C507":{"near_ref":"U503","near_pin":"5","purpose":"CTRL_3V0 LDO output reservoir"},
    "C508":{"near_ref":"U504","near_pin":"6","purpose":"BAT supervisor local supply bypass"},
    "C509":{"near_ref":"U505","near_pin":"6","purpose":"field detector local supply bypass"},
    "C510":{"near_ref":"U506","near_pin":"6","purpose":"cold comparator local supply bypass"},
    "C511":{"near_ref":"U507","near_pin":"6","purpose":"hot comparator local supply bypass"},
    "C512":{"near_ref":"U504","near_pin":"5","purpose":"shared reference output bypass; reference source is U504"},
    "C513":{"near_ref":"U504","near_pin":"3","purpose":"BAT_SENSE low-pass with R513/R514/R515 kept local"},
    "C514":{"near_ref":"U505","near_pin":"4","purpose":"WPT_SENSE low-pass; R516/R517/D509 adjacent, long route carries raw WPT not divided sense"},
    "C515":{"near_ref":"U506","near_pin":"3","purpose":"CELL_TEMP NTC harness filtering; U507 IN-4 samples same local node"},
    "C516":{"near_ref":"U506","near_pin":"4","purpose":"cold threshold bypass; R522/R523 adjacent"},
    "C517":{"near_ref":"U507","near_pin":"3","purpose":"hot threshold bypass; R524/R525 adjacent"},
    "C518":{"near_ref":"U508","near_pin":"2","purpose":"RUN_DELAY timing, R527/D507/R528 adjacent"},
    "C519":{"near_ref":"U510","near_pin":"2","purpose":"CHARGE_DELAY timing, R529/D508/R530 adjacent"},
    "C520":{"near_ref":"U508","near_pin":"5","purpose":"RUN delay Schmitt gate local bypass"},
    "C521":{"near_ref":"U509","near_pin":"5","purpose":"NOT_RUN inverter local bypass"},
    "C522":{"near_ref":"U510","near_pin":"5","purpose":"charge delay Schmitt gate local bypass"},
    "C523":{"near_ref":"U511","near_pin":"6","purpose":"SYS_PRE local input bypass; short loop through PMOS pair"},
    "C524":{"near_ref":"U511","near_pin":"1","purpose":"SYS_RAW reservoir before separate analog/digital branches"},
    "C525":{"near_ref":"U512","near_pin":"1","purpose":"analog LDO input bypass after R536"},
    "C526":{"near_ref":"U512","near_pin":"5","purpose":"AVDD LDO output bypass; feed quiet AFE rail from this node"},
    "C527":{"near_ref":"U513","near_pin":"1","purpose":"digital LDO input bypass after R537"},
    "C528":{"near_ref":"U513","near_pin":"5","purpose":"DVDD reservoir; local MCU bypass still mandatory"},
    "C529":{"near_ref":"R540","near_pin":"2","purpose":"VMID_RAW divider/filter; place at AFE U109B buffer input, prioritize AFE proximity over generic analog-LDO group center"},
    "C530":{"near_ref":"U514","near_pin":"5","purpose":"optional PCM local BAT/CELLN bypass; DNP qualification gate"},
    "C531":{"near_ref":"U515","near_pin":"3","purpose":"digital rail supervisor sense bypass; R549/R550/R551 adjacent"},
    "C532":{"near_ref":"U515","near_pin":"6","purpose":"digital supervisor local CTRL supply bypass"},
    "R511":{"near_ref":"U502","near_pin":"2","purpose":"eFuse ILIM programming; Kelvin ground to GND5/EP7"},
    "R534":{"near_ref":"U511","near_pin":"2","purpose":"run eFuse ILIM programming; Kelvin ground to GND5/EP7"},
    "R531":{"near_ref":"Q501","near_pin":"1","purpose":"PMOS source-to-gate off bias; keep common-source/gate loop short"},
    "R532":{"near_ref":"Q503","near_pin":"3","purpose":"PMOS gate pull-down path"},
    "R533":{"near_ref":"U511","near_pin":"4","purpose":"RUN_ENABLE default low at main switch/eFuse control"},
    "R536":{"near_ref":"U512","near_pin":"1","purpose":"separate SYS_RAW analog branch; tuning link next to local input capacitor"},
    "R537":{"near_ref":"U513","near_pin":"1","purpose":"separate SYS_RAW digital branch; do not daisy-chain digital feed through analog branch"},
    "R538":{"near_ref":"Q507","near_pin":"3","purpose":"analog discharge resistor and switch near analog output reservoir"},
    "R539":{"near_ref":"Q508","near_pin":"3","purpose":"digital discharge resistor and switch near digital output reservoir"},
    "R540":{"near_ref":"U109","near_pin":"4","purpose":"quiet VMID divider/filter adjacent to AFE buffer input"},
    "R541":{"near_ref":"R540","near_pin":"2","purpose":"VMID divider bottom resistor; same quiet local ground as C529"},
    "R544":{"near_ref":"U512","near_pin":"5","purpose":"DNP rail short option; keep at analog/digital boundary, not as default rail merger"},
    "R547":{"near_ref":"U514","near_pin":"5","purpose":"PCM BAT series filter at IC"},
    "R548":{"near_ref":"U514","near_pin":"6","purpose":"PCM V- input series resistor at IC"},
    "R546":{"near_ref":"Q510","near_pin":"2","purpose":"PCM current sense resistor: Kelvin sense trace to U514 V- through R548; isolate load copper from sense path"}
}

clusters=[
    {"name":"battery-threshold","anchor":"U504","refs":"U504 C508 C512 C513 R513 R514 R515".split(),"avoid":"WPT/raw power, gate/drain traces, clock/RF and discharge returns"},
    {"name":"field-threshold","anchor":"U505","refs":"U505 C509 C514 R516 R517 R518 R519 R520 D509".split(),"avoid":"Run WPT_RAW to R516, then keep WPT_SENSE short; sense input is not a long harness net"},
    {"name":"digital-sequence-threshold","anchor":"U515","refs":"U515 C531 C532 R549 R550 R551".split(),"avoid":"Long DIGITAL_SENSE routing and digital load ground returns"},
    {"name":"run-delay","anchor":"U508","refs":"U508 C518 C520 R526 R527 R528 D503 D504 D507".split(),"avoid":"Charging and SYS discharge current in timing capacitor return"},
    {"name":"charge-delay","anchor":"U510","refs":"U509 U510 C519 C521 C522 R529 R530 D508".split(),"avoid":"Timing network near WPT_RAW or power gate switching"},
    {"name":"cold-threshold","anchor":"U506","refs":"U506 C510 C515 C516 R521 R522 R523".split(),"avoid":"NTC harness coupling into reference or AFE; filter at comparator"},
    {"name":"hot-threshold","anchor":"U507","refs":"U507 C511 C517 R524 R525".split(),"avoid":"High-current ground drop in threshold resistors"},
    {"name":"charger-programming","anchor":"U501","refs":"U501 R503 R504 R505 R506 R507 C505".split(),"avoid":"STAT/CE routing through precision ISET node"},
    {"name":"ce-interlock","anchor":"Q504","refs":"Q504 Q505 Q506 R507".split(),"avoid":"Splitting the three series CE NMOS along distant temperature gates; carry digital gate nets instead"},
    {"name":"vmid-input-filter","anchor":"U109","refs":"R540 R541 C529".split(),"avoid":"BLE, charger, eFuse or discharge return in reference/filter ground"},
    {"name":"pmos-source-gate","anchor":"Q501","refs":"Q501 Q502 Q503 R531 R532".split(),"avoid":"Large shared-source/gate loops or single-FET substitution"},
    {"name":"optional-pcm","anchor":"U514","refs":"U514 Q509 Q510 R545 R546 R547 R548 C530".split(),"avoid":"CELLN copper stitched into GND, which would bypass the negative-side protector"}
]

components=[]
for c in canonical:
    ref=c["ref"]
    record={"ref":ref,"group":mapping[ref],"value":c["value"],"pins":c["pins"],
            "populate":bool(c.get("populate",not c.get("dnp",False))),
            "place_on_main_pcb":True,
            "catalog_component_on_main_pcb":ref!="RT501"}
    if ref in anchors:
        record["suggested_anchor_xy_mm"]=anchors[ref]
    if ref in local:
        record["local_proximity"]=local[ref]
    if ref=="RT501":
        record["placement_representation"]="Two manually soldered wire landings for the off-board NTC; no physical catalog thermistor mounted on main PCB."
        record["location_note"]="Off-board NTC bonded to cell, not board ambient; root PCB has explicit RT501 harness landing pads and alternate access through J501 REF_1V242 pin3/CELL_TEMP pin4. Exclude RT501 from SMT placement and assembled main-board BOM, while preserving its separately purchased catalog component."
    components.append(record)

out={"date_local":"2026-10-02","timezone":"America/New_York",
     "status":"Proposed placement constraints for unrouted candidate PCB; electrical circuit unchanged.",
     "source":"hardware/rev-a/power/power-components.json","source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
     "board_assumption":{"size_mm":[80,74],"bottom_power_region_mm":{"x":[6,76],"y":[53,71]}},
     "component_count":len(canonical),"main_board_component_count":sum(c["place_on_main_pcb"] for c in components),
     "external_catalog_component_refs":["RT501"],
     "coordinate_suggestions_status":"Initial agent floorplan proposal only. Root subsequently selected input/charger at left bottom and LDOs at right, below MCU/AFE output region; actual PCB coordinates take precedence. Groups and local-proximity constraints are independent of these provisional centers.",
     "ref_to_group":mapping,
     "groups":[{"name":g,"center_xy_mm":centers[g],"refs":refs,"count":len(refs)} for g,refs in bins.items()],
     "components":components,"critical_clusters":clusters,
     "routing_rules":[
         "Local bypass capacitor power pin connection: aim <=1 mm copper path, <=2 mm where package escape requires it; direct return to IC ground/EP with nearby plane connection. This is a layout objective, not a measured parasitic bound.",
         "Priority order: exact package escape and local bypass loops, precision sense/reference/timing networks, high-current power paths, control connectivity, then compact packing.",
         "Use a continuous ground return plane and physical zoning; do not route charging/eFuse/discharge current through threshold, VMID or AFE ground return segments.",
         "Keep high-current SYS and WPT loops in bottom power zone; distribute AVDD and DVDD from separate LDO output nodes. Long shared PACK/SYS copper must carry current independently of quiet sense taps.",
         "Carry low-impedance PACK+, WPT_RAW and DVDD toward local threshold dividers. Do not carry divided BAT_SENSE/WPT_SENSE/DIGITAL_SENSE across the board.",
         "Shared REF_1V242 source is U504 pin5 with C512 locally. Route reference branch to temperature/field/digital-supervisor thresholds away from raw WPT and digital load returns.",
         "Place R540/R541/C529 near AFE U109B VMID_RAW input even if outside nominal analog-LDO group center. Existing VMID crosstalk is a circuit issue and cannot be claimed fixed by this floorplan.",
         "External NTC pair should run together from J501 toward local CELL_TEMP filtering, away from raw WPT and ADC input runs. J501 RT501 is off-board; no ambient-temperature substitute.",
         "DNP protection components still need valid footprints, but CELLN remains distinct from GND. The bare-cell circuit must not be released solely because placement is complete.",
         "J501/J502/J503/J504 are manually soldered copper wire pads. Keep pad/silkscreen legends and isolation links accessible at board edges.",
         "RT501's main-board footprint represents wire landing pads only; the actual purchased thermistor is off-board on the cell and excluded from SMT placement/assembled main-board BOM."
     ]}
(BASE/"power-placement-groups.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"components":out["component_count"],"on_board":out["main_board_component_count"],"group_counts":{g:len(refs) for g,refs in bins.items()},"path":str(BASE/"power-placement-groups.json")},indent=2))

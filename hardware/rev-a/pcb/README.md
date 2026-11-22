# CuraLink Rev A candidate PCB

**Created 2026-10-02, America/New_York. Editable engineering candidate; DO NOT FABRICATE.**

**Saved-state audit, 2026-10-09:** Signal routing did not reach a saved/imported result. The native board has 142 GND segments, 167 GND vias and no filled plane polygons. There is no final DRC report or routing `.ses`. Its 446 footprint paths still require relinking to the corrected schematic UUIDs. The separately checked MCU placement overrides are not yet applied to the mainboard. Earlier routing descriptions below describe the intended workflow; they are not evidence of completed signal routing.

Open [curalink-rev-a.kicad_pro](../curalink-rev-a.kicad_pro) and [curalink-rev-a.kicad_pcb](../curalink-rev-a.kicad_pcb). The project includes its own `CuraLink.pretty` land patterns and footprint-library table. No native Altium conversion has been made. Test the conversion and verify net/land transfer; [Altium's importer documentation](https://www.altium.com/documentation/altium-designer/design-tools-interfacing) lists support through KiCad 8.x, so the KiCad 9 PCB cannot be presumed compatible. The separate DAC fixture and coil/rectifier receiver are outside this mainboard file; WPT enters through a DC interface.

## Geometry and functional placement

The provisional mainboard is **80 × 74 mm**, with four copper layers: top signals/components, internal GND, internal GND, bottom signals. All populated SMT components are on top. The larger size is a **Candidate implementation**, not acceptance of a relaxed 25–30 mm objective. It provides review and tuning space for the discrete AFE, power controls and first-board access; a smaller qualified placement is still open.

The left FFC/protection region feeds two banks of four channels. Each bank proceeds left-to-right through preamplification, differential DC rejection/high-pass, LP1 and LP2; local amplifier bypasses are placed beside their packages. Shared REF/VMID sits below the early stages. The MCU/ADC interfaces and crystals are to the right, and charging/control/isolation/regulators occupy the lower band. The antenna uses the top-right **6.5 × 6.5 mm** all-layer ground exclusion with pad 2 electrically isolated.

The planned internal GND planes are reserved from automatic signal routing and still require fill/continuity checks. Ordinary nets are intended to route on the two surfaces; **their routing is not completed**. RF filter and antenna feed nets remain **open** pending the MLPF ground/stackup adaptation. The native file is not a fabrication-complete layout. [validation.md](validation.md) is an earlier placement check; there is no final DRC report. Read the recorded board hashes to distinguish snapshots.

## Connectivity, footprints and assembly

[footprint-assignments.json](footprint-assignments.json) maps all **446 physical references** to 30 footprint types, excluding ten schematic-only power flags. All numbered copper-pad sets match the canonical source; intentional NC lands retain no net. Critical package lands use the checked manufacturer geometry, including MCU UFQFPN, RUC14 with no EP, DQA protection, MLPF CSP, Johanson antenna, FFC, BQ25185, TPS25200 and the optional no-EP BQ29737.

The initial independent placement check verified **1,089 connected and 48 intentional-NC lands**, one closed outline, four copper layers, all pad centers inside and no conservative courtyard overlaps. Routing changes require the final independent check and native DRC; an initial placement pass is not a final copper pass.

RT501 on the PCB is a **wire landing for an external cell-bonded NTC**. It is not an ambient thermistor populated on the mainboard. Test/pogo/harness copper fields and this landing are excluded from SMT placement and assembly BOM. J501 provides the corresponding battery/temperature harness access. DNP protection/RF links remain DNP as specified in the schematic.

Ground connections use 0.45/0.20 mm through vias where practical. MCU/charger/eFuse exposed-pad ground vias require a **qualified filled/capped or equivalent validated paste/via process**; their presence does not establish an assembly quote. Mask/paste compatibility for the tiny MLPF/DQA lands, FFC actuator/cable orientation, optional U.FL mask window and component rotation still require assembly review. The two-terminal Y402 crystal is nonpolar. [JLCPCB's capability table](https://jlcpcb.com/capabilities/pcb-capabilities) is a process reference; the order-specific stackup, impedance and assembly quote remain unverified.

## Remaining engineering gates

1. Resolve the existing full-band input-loading requirement and qualify protection/leakage. The current circuit does not meet ≥10 MΩ at 7 kHz in its declared fixture.
2. Review shared VMID coupling and aggregate channel interference. The actual nominal model gives −52.22 dB for one aggressor at 300 Hz; the proposed −60 dB criterion is not met.
3. Review routed feedback/input proximity, local bypass loops, ADC clock/sampling ownership and package crosstalk. Geometry checks alone do not prove signal integrity.
4. Complete RF routing using a defensible local ground/stackup implementation; qualify antenna tuning with nearby battery/coil/cable metal.
5. Close native DRC/connectivity and assembly process findings, inspect all pad polarity/rotation and the FFC convention, and define board mounting/strain relief.
6. Resolve globally orderable cell/independent protection and complete bench-emulator bring-up before using a cell. Existing charger OVP/OCP does not replace a qualified cell protector or all-system fault testing.

No manufacturing Gerbers, purchase or fabrication approval is provided. The [signal-integrity report](../signal-integrity/README.md) explains the electrical findings; the [handbook](../../../docs/engineering-handbook.md) preserves accepted baselines and candidate status.

## Reproducibility

`tools/hardware/prepare_pcb_footprints.py` creates the project library and assignment manifest using native KiCad 9 and retained source drawings. `build_pcb.py` creates a **fresh placement** from the canonical pin map and checked footprint assignments; running it replaces the PCB and must be an intentional rebuild. `route_pcb.py prepare` requires that fresh unrouted placement, adds ground connections and exports a two-surface DSN; `import` reads the retained SES into the four-layer native file and `fill` fills internal planes. The local FreeRouting exchange ignores the Ground and ReservedRF classes. The Java/tool binaries live in `tmp` and are not part of the handoff ZIP.

`check_board.py` independently checks native pad/net/NC transfer, board geometry and conservative courtyards. These scripts preserve the candidate electrical values and do not qualify the RF model or assembled behavior.

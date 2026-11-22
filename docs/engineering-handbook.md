# CuraLink Engineering Handbook

**Current design record · Created 2026-09-21 · Last updated 2026-11-22**  
Dates use America/New_York. Version 1.21 includes the four-coax bench configuration, fixed-coil receiver and a low-capacitance AFE candidate for the retained 10 MΩ release requirement.

**Current bench build, 2026-11-22.** The user selected four generator inputs on the electronics PCB, one U.FL per channel, with BLE to the laptop. Wireless charging uses the fixed published coils and a 13.56 MHz generator. Acquisition stops during charging while the MCU reports status. A compatible externally charged 1S pack provides an independent signal-test path. The available lab cell and keyed connector await identification. Use the [plain-text builder handoff](BUILD-NEXT.txt) and D-025 through D-028 for current configuration. Earlier eight-channel, FFC, four-discrete-diode and all-electronics-off results below are dated engineering history.

**Recommended layout candidate.** The [four-coax low-capacitance board](../hardware/rev-a/bench-four-coax-low-c/README.md) has a separately verified schematic and placement. With 0.60 pF additional board capacitance per input, ADS and LTspice both predict a stressed full-band minimum of 10.70 MΩ. At 1.00 pF both predict 9.16 MΩ. Silicon, routed geometry and measured charging remain unqualified. Open the new ADS workspace cell **CuraLink_RX_BAS4002A_HB** for the packaged rectifier. At 25 dBm and 24 mA its 7.31 V minimum raw output reproduces the standalone HB deck. A 26 dBm staged-load transient sustains about 5.0 V at 29 mA and drops to 4.67 V with the 39 mA-at-5 V load. [Native ADS verification](../hardware/wpt/ads/native-packaged-bridge/) · [Receiver study](../hardware/wpt/ads/receiver-ic-review-2026-11-22/)

**Earlier eight-channel / discrete-bridge ADS review, 2026-11-22:** The user reaffirmed the published coils as a fixed constraint and requested power/signal bias/return verification before another agent builds the design. No coil, part or electrical value changed. Fresh ADS reproduces **71.87346% passive two-port transfer** and **2.38008 − j28.07827 Ω** transformed RX load at 13.56 MHz. A fresh BAT54 resistor fixture reproduces 5.08871 V / 124.2959 mW. The authored charger-demand law now passes a new DC sign/compliance check and **48 HB cases**: nominal 20 mA demand at 23 dBm gives RAW/CHG_IN 5.09684/4.81684 V, while 23.5 dBm raises RAW to 5.75144 V. All 32 taper/complete fixtures exceed the authored voltage domain, reinforcing the raw OVP/regulation gate for that discrete-bridge fixture. Equivalent standalone fixtures were run; a real BQ25185/cell/protection control loop was not. Fresh translated TI-family ADS AFE DC/AC checks give 36 valid nominal operating points, ADC bias approximately 1.50319 V, 969.742 V/V at 1 kHz, sampled shared-VMID coupling approximately −52.22 dB and input impedance approximately 0.823 MΩ at 7 kHz with declared cable parasitics. Internal macro-model DC-path corrections and excluded noise analysis remain explicit limits. See [the complete review](../hardware/wpt/ads/review-2026-11-22/README.md). The ≥10 MΩ requirement remains unmet; no fabrication release or buffer selection is implied.

**Computer migration, 2026-11-22:** The user requested all CuraLink files and a context README on GitHub. The consolidated repository keeps the mainboard under `hardware/rev-a` and packages the five-cell native ADS workspace under `ads/MyWorkspace_wrk`. The two large original ADS datasets are losslessly compressed with source/transport SHA256 records and a restore script; Git LFS also carries large simulation results and the historical handoff ZIP. Unique secondary-folder CSVs, recovered scratch archives and supplied context texts are retained separately from current specifications. [The migration guide](moving-computers.md) records tool versions, clone/restore steps, active path overrides and unresolved dependencies; [the CAD/dependency audit](../migration/cad-audit.json) and [source consolidation manifest](../migration/consolidation-manifest.json) record coverage. Old application locks/downloaded runtimes and credentials are not design dependencies. This is a saved-file handoff: no Altium conversion, new electrical simulation, stock refresh, hardware validation or fabrication release is implied. Historical absolute source paths remain provenance; the repository-relative paths are the migration entry points.

The migration batch was published as [a1193c4](https://github.com/AngeloWhey/CuraLink/commit/a1193c42201dd7d52925ad7259a69e111141fb81). A fresh GitHub clone re-downloaded all 218 LFS objects, passed Git/LFS checks and decoded both large ADS datasets to their original hashes. [Publication verification](../migration/github-publication-verification.json) is separate from the subsequent electrical review above.

**ADS receiver study, 2026-10-09:** Three new native test cells were saved in the recovered `MyWorkspace_wrk` / `MyLibrary_lib`; both original cells' OA files remain hash-identical. The BAT54 **Candidate** cell, `RX_BAT54_LoadSweep_20261009`, was actually simulated from fresh saved-OA netlist readback: at 13.56 MHz, 23.5 dBm available RF, 208.333333 Ω and HB order 31, it gives **5.08853 V / 124.287 mW / 55.517% available-RF-to-DC efficiency**. Four ideal capacitor values came from a finite joint search, not a global optimum or sourced hardware selection. The old 4.2 V breakdown seed exceeds its reverse bound and cannot qualify a 5 V receiver. The same-power near-open-load fixture reaches **11.915 V** and approximately **132 mW RX winding loss**, making raw overvoltage control and thermal assessment explicit remaining gates. Updated charge-control accounting gives 108.7 mW nominal / 119.8 mW declared upper sensitivity at a 5 V board-input boundary; these are fixture calculations, not guaranteed maxima. The third cell, `RX_ChargerLoad_20261009`, contains an authored voltage-compliant input-load approximation, **not simulated** because further charger-fixture solver attempts met the ADS license user limit. See [the ADS study and next power steps](../hardware/wpt/ads/README.md). No cell, charger, final diode/capacitor, TX power or fabrication decision was newly accepted.

**ADS workspace recovery, 2026-10-09:** The working two-schematic WPT workspace is `C:\Users\angel\OneDrive\Documents\projects\curalink\MyWorkspace_wrk`, library `MyLibrary_lib`. `cell_1` is the coil/matching/rectifier simulation; `cell_2` is the passive coil/matching S-parameter test. Saved netlist evidence includes 13.56 MHz, 2.49/0.33 µH coils and k = 0.0662; it predates the latest OA save, so it is identification evidence, not final topology/performance verification. No neural AFE cell was found there. Two earlier scratch folders named `Curalink_wrk` are absent from their original home/OneDrive-Code locations and have matching Recycle Bin entries. Verified ZIP backups preserve their unique early AFE/MOSFET scratch work in [the recovery manifest](../archives/ads-cleanup-2026-10-09/recovery-manifest.json), subsequently bundled in the migration. The working workspace and both project repositories were preserved; no design values or simulation results were changed.

**Restart audit, 2026-10-09:** Native Altium `.SchDoc`, `.PcbDoc` and `.PrjPcb` files were not found in either CuraLink folder. The saved KiCad project has 17 schematic pages and an 80 × 74 mm placement, but the main PCB contains only 142 GND track segments and 167 GND vias, no filled plane polygons and no saved imported signal-routing session. It is **not a routed or fabrication-ready board**. The schematic UUID generator was corrected on 2026-10-02, but the saved PCB still lacks the root schematic UUID in all 446 footprint paths; relinking and independently checking the board remains pending. MCU local-placement corrections exist separately and have not been merged into that board. The older ZIP/PDF also predate the PCB/SI work and are historical snapshots. Altium conversion must be tested, especially because the native PCB is KiCad 9 and [Altium's documented importer support](https://www.altium.com/documentation/altium-designer/design-tools-interfacing) lists KiCad through 8.x. Nominal bias AC studies are complete: shared 47 Ω gives −52.22 dB and shared 4.7 Ω gives −64.48 dB; split 47 Ω / split 4.7 Ω give −50.46 / −53.84 dB. The shared-4.7 Ω startup raw file is empty and its log does not complete; recovery/load-step runs have no saved completion evidence. Retain canonical R1149 = 47 Ω until the alternative has qualified stability/recovery evidence. The proposed −60 dB criterion is unaccepted. The last stock check remains 2026-10-02, not a current inventory guarantee.

**PCB and signal-integrity review, 2026-10-02:** The user requested board/crosstalk checks and then authorized creating a board. The new [editable Rev A mainboard](../hardware/rev-a/curalink-rev-a.kicad_pcb) uses a provisional 80 × 74 mm, four-layer placement of the existing schematic, with two internal ground planes, forward AFE stages, corner antenna exclusion and debug access. This larger geometry is a **Candidate**, not acceptance of a relaxed size objective or fabrication release. All 446 physical references have assigned, pad-set-checked footprints; initial independent placement validation found no pin/net/NC transfer errors or conservative courtyard overlaps. Final copper status is maintained in the [PCB review](../hardware/rev-a/pcb/README.md). Actual nominal LTspice CH1-only excitation gives worst quiet-channel coupling **−52.22 dB**, equivalent 0.490 µVpp / 2.449 µVpp for 200 µVpp / 1 mVpp aggressors, through shared VMID. An assumed 0.01 pF late-output-to-input path gives about 17.25 µVpp equivalent for 1 mVpp. These are model/sensitivity results, not extracted PCB capacitances or measurements. A proposed −60 dB single-aggressor criterion is unaccepted and unmet; bias stability/recovery/power and aggregate-crosstalk evaluation remain open. See the [signal-integrity report](../hardware/rev-a/signal-integrity/README.md).

**LTspice verification completed, 2026-10-02:** Actual LTspice 26.0.2 runs using original-equation TI amplifier family models validated all 36 amplifier operating points, approximately 970 V/V at 1 kHz and steady DC rejection. Across the -100 to +100 mV input sweep, a declared 10 GOhm coupling-capacitor leakage case changes the ADC baseline by 18.36 uV. Offset steps still rail the AFE and disturb shared VMID; nominal startup reaches a quarter ideal ADC LSB after 2.336 s, so 3 s startup blanking plus rail/baseline/clipping checks is a **Candidate** mitigation. Power-model tests confirm eFuse clamp/cutoff behavior, with a tested 5.868 V peak for a fast fault and minimum-capacitance fixture; actual control-LDO input peaks are checked separately. This is simulation evidence, not hardware or whole-board OVP qualification. Manufacturer audits corrected both TPS25200 pin maps and SS14 numbering, and changed R511 from 1.1 MOhm to stocked 1.0 MOhm so its tolerance stays within TI limits. The refreshed CAD/PDF/ZIP supersedes those earlier connections. See the [LTspice analysis](../hardware/rev-a/ltspice/README.md).

**Latest sourcing review, 2026-10-02:** The user reaffirmed that all parts must be stocked and sourced from LCSC. All **80 unique Rev A BOM SKUs**, including optional DNP parts and the off-board cell NTC, match their exact manufacturer numbers and have enough immediate overseas stock for one board with order-minimum rounding. The external FFC cable is also available. The accepted Taisko cell C19632326 is **not confirmed globally orderable**: its global detail API returns no record, its product page returns 404 and exact-code search has no result. No compatible stocked global replacement was verified; the accepted cell baseline is retained with an explicit sourcing/protection gate. Minimum-order component purchases total approximately US$103.55 excluding the cell, PCB, assembly, shipping and tax, so the US$150 assembled budget is not proven. MCU inventory is nine units; stock is not reserved. See the [dated inventory audit](../hardware/rev-a/procurement/stock-audit-2026-10-02.csv), D-020 and D-024.

**Latest schematic review, 2026-10-01:** The user authorized detailed schematic work and explicitly requested evaluation of ADC and comparator detection with a recommendation. The new [Rev A handoff](../hardware/rev-a/README.md) recommends STM32WBA52CGU6 ADC acquisition, mixed TLV9004/TLV9054 amplification, approximately 1008 V/V nominal / 969 V/V at 1 kHz, and a 150 Ω / 470 pF ADC interface. These are **Candidate implementation choices**, not silent acceptance of a replacement for D-012 or a relaxation of the ≥10 MΩ requirement. Calculated electronics noise is about 3.44 µVrms over 300 Hz–7 kHz and amplifier current 4.32 mA typical; they are not measurements. The editable schematic has passed CAD pin-transfer and ERC checks. The power circuit includes explicit mode isolation, sequencing and temperature control, but the selected bare cell's independent protector remains unqualified. Initial power configuration uses current-limited emulators and bench DC; wireless receiver and optional PCM links are DNP. See D-024 and linked subsystem evidence.

**Latest review, 2026-10-01:** The user requested evaluation of an external agent's STM32WBA55CGU6 / eight-channel ADC proposal. It is a **Candidate**, not an accepted replacement for D-012/D-013. Primary-source checks confirm WBA52 lacks SMPS and WBA55 includes it; both proposed packages offer eight external ADC inputs. The claimed system power advantage remains unproven. ST's default BLE temperature-calibration code also uses the ADC, creating a firmware integration/continuity gate. A qualified ADC output driver, acquisition-time budget and anti-alias specification would be required before adopting this alternative. The existing AFE input-capacitance/loading problem remains open. See the review note in D-012; no MCU, acquisition, amplifier, gain or filter selection changed.

**Latest update, 2026-09-25:** The user accepted D-023: retain BQ25185DLHR and use Taisko 401020-55mah (catalog C19632326; 55 mAh typical / 50 mAh minimum) as the working cell, with a provisional 20 mA room-temperature charge target and 4.1 V regulation pending cell voltage-tolerance clarification. Target approximately 5 V / 21 mA (105 mW) delivered DC before extra loads and tolerance margin; sweep 20/23/26 dBm in ADS rather than fixing TX power at 10 dBm. Stock/export, protected-pack details, temperature limits and usable runtime remain unverified. PGEB201212 is superseded as the working cell. The power architecture is established enough to resume AFE design, but rectifier grounding/stress, receiver OVP, independent battery protection, charger settings, PMOS interlock and delivered-power tests remain release gates. BQ25185 internal OVP/OCP do not close those gates. Existing 13.56 MHz published-coil baseline and no-VNA verification approach remain unchanged. See D-021 through D-023 and the [cell/charger/isolation review](design/2026-09-24-cell-charger-isolation-review.md).

**Historical cell assessment, 2026-09-24 (superseded as the working choice by D-023):** User selected TI BQ25185DLHR (LCSC C19725033) as the charger IC and identified PGEB201212 as the intended cell candidate. A supplier listing describes PGEB201212 as 8 mAh, 3.7 V, 4.2 V charge, recommended 0.2C (1.6 mA), and unprotected; it supplies no manufacturer datasheet and its discharge-current notation is ambiguous. TI specifies BQ25185 charge-current programming from 5 mA upward, so 1.6 mA cannot be selected as its programmed CC rate. A recommended rate is not a proven maximum; compatibility remains unqualified pending the exact cell limits. This tiny cell also cannot meet the one-hour runtime objective at the current 25–35 mA system estimate. Do not treat this cell/charger pair as validated or the 40 mA ADS case as valid for it. A prior 40 mA transient plot showed `DOut=-0.513 V`; if RF source remains 10 dBm, the 40 mA case exceeds source power by over an order of magnitude. See D-021, D-022 and the [battery/charger ADS model study](design/2026-09-24-battery-charger-ads-model.md).

**Historical compatibility review, 2026-09-24 (acceptance updated by D-023):** BQ25185 remains selected; Taisko 401020-55mah (catalog C19632326) and 302020-100mah (C19632322) are proposed qualification candidates, with global orderability/pack details still open. Verified BQ25185 enabled-input overhead (0.75 mA typical / 1 mA max under stated conditions) and its six-hour safety timer materially constrain weak-source charging. A typical 330 mV VINDPM offset is not a guaranteed full-current input threshold. The latest rectifier screenshot appears to ground an AC bridge midpoint and DC-negative together; confirm/correct the netlist before treating it as a full bridge. The PMOS must open during WPT, using hardware detection independent of charge-complete status. See the [cell/charger/isolation review](design/2026-09-24-cell-charger-isolation-review.md); no alternative parts or charge rates are accepted yet.

**RF source constraint, 2026-09-25:** The user confirms TX input power can be increased. The previous 10 dBm ADS setting is therefore a starting case, not a fixed system limit. Actual generator/PA capability, permissible voltage/current/thermal stress and delivered DC power remain to be established. This does not select a new battery, charge current or final TX setting.

**Manufacturing constraint, 2026-09-24:** User requires electronic parts for future board BOM selections to be available and orderable from LCSC for pick-and-place assembly. Check the exact LCSC listing/order code and assembly eligibility when selecting each part because inventory and availability change. See D-020.

This handbook explains what CuraLink is intended to do, which important decisions have been made, why they were made, and what remains to be demonstrated. It is the central engineering record for a new engineer joining the project.

The initial entries were imported from the user's project handoff on **2026-09-21**. Their original decision dates were not supplied. Recording a decision here does not imply it was made that day, independently verified, simulated, or measured.

## 1. Purpose and governing objectives

CuraLink is a compact, four-channel **benchtop** prototype reproducing electrical and architectural challenges of intracortical extracellular neural acquisition. It is not intended for human or animal implantation. Its normal output is per-channel spike counts, with analog test access for waveform debugging and characterization using external instruments.

The design must balance low input-referred noise, useful multichannel complexity, power, PCB area, manufacturability, and quantitative verification. A nominal 25–30 mm footprint is a design objective, subordinate to electrical feasibility and first-board reliability.

Assume Rev A may be the only main PCB revision. Problems must be observable and isolatable; a future PCB revision is not the primary mitigation. The completed project should support a defensible explanation of each consequential engineering tradeoff.

### Status vocabulary

| Status | Meaning |
|---|---|
| Locked | Accepted project scope or requirement; reopen explicitly if evidence warrants it. |
| Baseline | Current working approach; further calculations or validation may change it. |
| Objective | Desired performance; not a guarantee or measured result. |
| Candidate | Under consideration; not selected. |
| Open | A decision has not been made. |
| Superseded | Previously considered or used; replaced by a stated decision. |

**Evidence is separate from decision status.** A locked requirement can remain unverified. Label evidence as imported rationale, primary-source verified, calculated, simulated, or measured. No hardware measurement or completed simulation is established by the initial handoff.

## 2. Current system at a glance

```text
Signal generator + calibrated attenuation → four U.FLs on the electronics PCB
    → four local 47 kΩ source emulators + shared quiet reference
    → matched input protection, AC coupling, amplification and filtering
    → STM32WBA52 acquisition/event path → BLE → laptop

13.56 MHz generator → TX matching → fixed 40 mm TX / 10 mm RX coil pair
    → RX matching → single packaged bridge → reservoir → 5 V regulation
    → protected charger input → BQ25185 → compatible protected 1S pack

RECORD: field absent, valid battery → AFE and MCU/BLE on.
CHARGE: receiver DC detected, AFE off, powered MCU/BLE reports charger state.
SIGNAL-ONLY: externally charged pack or cell emulator, RX disconnected, field off.
```

D-024 still identifies MCU ADC acquisition as a Candidate. Signal tests can use the battery-only path independently of receiver debugging.

### Requirements and working values

| Item | Current value or approach | Status / qualification | Record |
|---|---|---|---|
| Channels | 4 recording channels + local shared reference | Locked for current bench board | D-025 |
| Modality | Intracortical extracellular-like acquisition | Locked; electrical bench model | D-001 |
| Spike amplitude | 200 µVpp nominal; 100–300 µVpp primary region | Locked input baseline | D-002 |
| Characterization envelope | 50–500 µVpp; approximately 0.5–2 ms | Locked input baseline; not a detection guarantee | D-002 |
| Additional input tests | 20 µVpp stretch; 1 mVpp headroom; approximately 1 ms nominal duration | Stretch detection not guaranteed | D-002 |
| Source model | 47 kΩ nominal series resistance; 30–70 kΩ normal, 20–100 kΩ extended characterization | Locked first-order model, not a complete electrode model | D-002 |
| AFE input impedance | At least 10 MΩ over 300 Hz–7 kHz at the protected AFE, after the board-side source emulator | Locked release requirement. TLV baseline gives 2.962 MΩ. Low-capacitance candidate predicts 10.70 MΩ at 0.60 pF of layout capacitance. Hardware verification open | D-003, D-025, D-028 |
| Signal band | Approximately 300 Hz–7 kHz | Baseline; compare 5/7/10 kHz upper corners | D-003 |
| Electronics noise | ≤6 µV RMS input-referred over approximately 300 Hz–7 kHz | Objective; source noise reported separately | D-003 |
| Electrode offset | Approximately ±100 mV | Proposed robustness target; tolerance and recovery criteria open | D-003 |
| Acquisition | Earlier analog-event baseline; four-channel schematic uses the proposed STM32WBA52 ADC | Pending firmware/ADC/BLE continuity | D-012, D-024, D-025 |
| Event capture / acquisition timing | Accepted analog-event implementation open; ADC candidate prefers 50 kS/s/channel, 48 MHz kernel / 79.5-cycle acquisition | Candidate timing arithmetic, not firmware or continuity result; explicit BLE calibration service required | D-012, D-024 |
| Total analog gain | Rev A candidate approximately 1008 V/V nominal (60.1 dB), 969 V/V at 1 kHz | Calculated and nominal TI-family LTspice gain/recovery checks; real signal/noise/PCB behavior unmeasured | D-003, D-024 |
| Spike output | Four indexed counts in recording mode and charger status during the charge test | Bin period remains configurable; packet implementation open | D-005, D-025, D-026 |
| Bin period | 25 ms reference/default | Baseline, configurable | D-005 |
| Telemetry | BLE in STM32WBA52; ceramic chip antenna | Working baseline; matching/layout and package still open | D-006, D-013 |
| Operating modes | Battery recording or RF charge with AFE disabled and MCU/BLE status enabled | Locked test behavior; rail implementation and operation under a weak field need validation | D-026 |
| Power path | BQ25185, protected 1S pack or emulator, independent battery-powered RUN | Lab pack and connector TBD. Historical 20 mA/4.1 V are emulator settings. Include radio load in WPT budget | D-021, D-023, D-026 |
| Rails and bias | Separate 3.0 V TPS7A20 LDO candidates, analog enabled by digital-good supervisor; 1.5 V buffered midpoint | Partition baseline retained; nominal 1.53/1.43 V sequencer and 3.50/3.80 V battery UVLO are calculations; timing/injection/shutdown must be qualified | D-016, D-024 |
| WPT simulation | Fixed R/L/k → carrier matching and packaged-bridge harmonic balance plus regulator transient | Review exported results and load/coupling limits in builder handoff | D-017, D-018, D-027 |
| WPT coil geometry | 13.56 MHz square planar pair; 40 mm TX / 10 mm RX; 10 mm nominal coaxial separation; paper geometry in D-018 | Selected Rev A baseline; current constant-R/L/k model predicts useful loaded DC and consequential no-load heating; physical reproduction and thermal envelope unverified | D-018 / DEC-WPT-003 |
| Rectifier diode model | Infineon BAS4002A-RPP packaged bridge and TPS70950 5 V regulator | Selected engineering implementation, qualification pending | D-027 |
| Footprint | Approximately 25–30 mm in XY | Objective, not a hard limit | D-008 |
| Bench input | Calibrated generator → four U.FLs on electronics PCB → local source emulation | Selected; shielding, attenuation and loading require validation | D-025 |
| Input protection | Matched protection, series limiting and AC coupling on CH1–4 and REF | Same full-band input-impedance requirement; emulator resistor on PCB after coax | D-015, D-025 |
| PCB electronic-part sourcing | 73 distinct fitted low-capacitance electronics-board SKUs and 10 RF-board SKUs had LCSC stock for one assembly at the 2026-11-22 check | Main-board JLC availability checked separately. Cell unidentified, stock unreserved, delivered cost unverified | D-020, D-025, D-027 |

## 3. Decision register

D-001 through D-009 were **recorded 2026-09-21** from the supplied handoff; **original decision dates are unknown**. Later entries state their actual decision dates. Evidence is imported engineering rationale unless an entry explicitly identifies another source or calculation. External research numbers in the handoff have not yet been checked against primary publications in this project.

| ID | Decision | Status |
|---|---|---|
| D-001 | Original eight-channel extracellular-like bench system | Channel count superseded by D-025 |
| D-002 | Neural signal envelope and first-order source model | Locked baseline |
| D-003 | High-impedance spike-band AFE with substantial analog gain | Function selected; implementation open |
| D-004 | Internal ADC and DMA for digital detection | Superseded by D-012 |
| D-005 | Per-channel spike counts with configurable bins | Selected representation; algorithm open |
| D-006 | BLE telemetry with wired debug and host tooling | Baseline |
| D-007 | Original all-off CHARGE and battery RUN | Recording exclusion retained. Live status revises MCU/BLE policy under D-026 |
| D-008 | Design for first-board success within a compact footprint | Selected design policy |
| D-009 | Passive AWG-driven neural input fixture | Source generation superseded by D-014; source model and FFC preserved |
| D-010 | Budget, runtime and scheduling constraints | User-confirmed 2026-09-21 |
| D-011 | Reopen MCU vendor; evaluate gain and parts | MCU choice resolved by D-013; ADC assumptions corrected by D-012 |
| D-012 | Remove waveform ADC; detect analog events and count in MCU | Baseline direction; implementation open |
| D-013 | STM32WBA52 BLE controller and ceramic chip antenna | User-selected baseline; exact package/RF implementation open |
| D-014 | Original eight-way DAC/FFC fixture | Test interface superseded by D-025 |
| D-015 | Adapt EGRA/Meower references for CuraLink protection and manual layout | Reference method accepted; values and qualification open |
| D-016 | 1S charge path, hardware system isolation and split rails | Architecture baseline; implementation and coil-board partition open |
| D-017 | WPT modeling and DC-power/efficiency evaluation method | DEC-WPT-002 revised by DEC-WPT-003; nominal ADS receiver study completed, charger/hardware qualification open |
| D-018 | Reuse Luo et al. 13.56 MHz 40 mm TX / 10 mm RX planar pair for Rev A | Selected baseline (DEC-WPT-003); nominal resistor power modeled, physical reproduction and stress envelope unverified |
| D-019 | Proceed without VNA; rely on published coil model, tuning provisions and end-to-end DC tests | User-confirmed verification constraint |
| D-020 | Source PCB-mounted electronic BOM parts through LCSC for pick-and-place | Locked sourcing requirement; verify exact listing and stock at selection |
| D-021 | Select TI BQ25185DLHR (LCSC C19725033) as the 1S charger baseline | Charger IC selected; cell, configuration, and receiver OVP open |
| D-022 | Assess PGEB201212 as the intended 1S cell candidate | Superseded as working cell by D-023; historical qualification unresolved |
| D-023 | 55 mAh cell and provisional charging baseline; resume AFE | Baseline accepted; power circuit verification open |
| D-024 | Rev A schematic recommendation after ADC/comparator comparison | Candidate implementation; reviewable CAD and sourcing checks passed; no fabrication release |
| D-025 | Four U.FL generator inputs and shared reference | Locked bench interface; supersedes the eight-channel/FFC portions of D-001/D-014 |
| D-026 | Live charge-status BLE and independent battery-only signal tests | Locked functions; supersedes the MCU-off portion of D-007/D-016 |
| D-027 | Packaged bridge with separate 5 V regulator on the fixed-coil receiver | Baseline; CAD and simulation qualify an engineering candidate |
| D-028 | Lower-capacitance gain stages and bypassed bias return | Engineering candidate for the locked full-band input impedance, pending extracted layout and bench verification |

### D-001 — Eight-channel extracellular-like bench system

**Historical baseline.** See D-025 and D-026 for the current bench configuration.

**Choice and status.** Use eight intracortical extracellular-like recording channels and one shared reference. Scope is locked.

**Objective.** Exercise multichannel acquisition, shared references, channel variation, crosstalk, calibration, and telemetry scaling within a manageable power, area, and validation budget.

**Alternatives and tradeoffs.** One or two channels reduce assembly and test effort but provide limited multichannel learning. Sixteen or more channels increase analog area, routing, power, and test burden without a proportional benefit to this prototype's objectives. Eight channels retain meaningful integration challenges at a tractable scale.

**Rationale.** Channel count is driven by useful engineering complexity, not maximum channel density. The selected input modality requires microvolt-scale analog acquisition; it is not EEG, ECoG, intracellular recording, or an already-digital event stream.

**Risks and mitigation.** Shared reference paths can introduce correlated interference. Design REF and grounding explicitly; retain per-channel test access and calibration.

**Verification / reopen when.** Demonstrate acquisition and independent channel indexing on all eight channels, quantify matching and coupling, and complete power/area budgets. Reopen only if demonstrated feasibility constraints defeat the intended scope.

### D-002 — Input envelope and first-order electrode model

**Choice and status.** Adopt the input values in Section 2 and a nominal 47 kΩ source resistor per channel as the locked first-order bench model. Canonical test waveforms are bipolar, biphasic or multiphasic extracellular-like action potentials.

**Objective.** Make signal amplitude, source loading, noise, bandwidth, and headroom calculations representative of the intended acquisition problem and reproducible on the bench.

**Evidence and assumptions.** The handoff cites published electrode impedances near 37 kΩ and 56 kΩ at 1 kHz as motivation for the 47 kΩ model. Those publication values require source verification before use as formal research evidence. A physical resistor is approximately resistive across the band; specifying 47 kΩ does not recreate a frequency-dependent electrochemical interface.

**Alternatives and tradeoffs.** A near-zero-impedance generator simplifies stimulus delivery but underrepresents loading and current-noise effects. An R/C or constant-phase-element model can better represent an electrode but introduces parameters that must be justified. Start with the resistor model and extend it when a design question requires that fidelity.

**Risks and mitigation.** Peak-to-peak voltage is not the same as a threshold excursion, and spike spectra depend on waveform shape. Retain actual templates and report amplitude conventions. Treat 20 µVpp as a stretch characterization point, not a promised sensitivity.

**Verification / reopen when.** Measure applied amplitude and source impedance, sweep the stated amplitude/source ranges, and use representative 0.5–2 ms waveforms. Revisit the source model if input loading, noise, or recovery depends materially on its missing frequency dependence.

### D-003 — High-impedance spike-band analog front end

**Choice and status.** Provide high input impedance, rejection of electrode DC before excessive gain, low-noise amplification, nominal 300 Hz–7 kHz signal conditioning, and comparator-compatible bias/output levels. Required functions are selected; topology, rails, components, filter order, and gain remain open.

**Objective.** Preserve useful action potentials while reducing slow drift/LFP content and out-of-band noise, avoiding saturation, and resolving analog detection thresholds with a defensible error budget.

**Constraints and calculations.** The user reconfirmed ≥10 MΩ across 300 Hz–7 kHz as a release requirement for the four-coax board on 2026-11-22. Measure the complete protected AFE looking in immediately after the local source emulator. Include input protection, bias and layout parasitics. Report source-to-input voltage transfer separately. The electronics-noise objective is ≤6 µV RMS input-referred over approximately 300 Hz–7 kHz. Report source-resistor noise separately and also report total input-referred system noise; do not silently include source noise in an electronics-only limit.

The earlier ADC-code gain calculation is superseded by D-012. Gain must now satisfy detector accuracy and analog headroom constraints. Illustrative relations are:

```text
Input-referred detector error = output-domain detector error / gain
Gain lower bound = detector error budget / allowed input-referred error
Gain upper bound = usable output swing pp / maximum input pp
```

These bounds require explicit offset, threshold, hysteresis, noise, waveform, and artifact assumptions. At 1000 V/V, 50 µVpp becomes 50 mVpp and 1 mVpp becomes 1 Vpp; these remain voltage-scaling examples, not a gain selection. See the [current AFE calculation](design/2026-09-22-two-board-analog-afe.md).

**Alternatives and tradeoffs.** Broadband acquisition preserves LFP and more high-frequency content, but demands additional dynamic range and increases integrated noise/data burden. A spike-focused band matches the selected output. Lower upper corners may reduce noise while attenuating spike peaks; higher corners retain more signal but increase integrated noise and detector bandwidth demands. Compare 5, 7, and 10 kHz with realistic templates before finalizing.

**Rationale.** Analog gain makes microvolt signals usable by the analog detector; the custom AFE remains central without a waveform ADC. DC rejection must occur before enough gain accumulates to saturate a stage; placing a high-pass function somewhere in the chain is insufficient unless every preceding stage has adequate headroom.

**Risks and mitigation.** Large bias resistors, input capacitance, protection leakage, amplifier current noise, shared-reference noise, and offset transients can defeat the targets. Analyze the complete input network and each stage's noise, bandwidth, stability, swing, and recovery. Keep filter/gain tuning provisions where justified.

**Verification / reopen when.** Calculate signal/noise/headroom budgets; simulate transfer functions and transient recovery; then measure gain, impedance, noise spectra, integrated noise, and detection performance. Choose filter order using peak retention, integrated noise, ringing, and comparator chatter/recovery. Reopen corners or gain when those results show a better sensitivity/power/headroom tradeoff.

### D-004 — Internal ADC plus DMA instead of analog comparator detection

**Choice and status: Superseded by D-012 on 2026-09-22.** The following rationale documents the earlier ADC/DMA proposal, not the current architecture. The 2026-09-21 study favored an internal ADC and considered EFR32BG22; the user subsequently clarified that the aim is to remove the waveform ADC. ADC-specific checks below are historical only.

**Objective.** Enable waveform visibility, calibration, configurable thresholds, and reliable first-board diagnosis while limiting discrete analog circuitry.

**Alternatives and tradeoffs.** Dual-polarity analog detection can require 16 comparator elements for eight channels plus threshold and hysteresis circuitry. It may reduce continuous acquisition/processing power, but limits waveform observability and adds analog calibration/distribution concerns. ADC acquisition consumes conversion and processing power but enables raw captures and flexible algorithms.

**Calculation.** At the candidate rate of 30 kS/s/channel, eight channels require 240 kSamples/s aggregate. That number is a throughput requirement, not proof that a particular part or scan configuration is suitable.

**Rationale.** Integrated acquisition offers strong diagnostic value for a board that may not get a second revision. Any comparator power advantage must be evaluated at the complete system level.

**Risks and mitigation.** Check accessible ADC pins, conversion and sampling times, input settling after mux changes, channel timing skew, DMA behavior, CPU utilization, and BLE coexistence on the exact part. Multiplexed acquisition does not imply simultaneous sampling. Do not finalize 25–30 kS/s/channel solely from Nyquist; account for analog attenuation and aliasing.

**Verification / reopen when.** Verify the selected device against its datasheet/reference manual, then measure timing, missed samples, settling, processing load, and acquisition power. Reconsider comparator-based detection if measured ADC/CPU power is incompatible with the final budget.

### D-005 — Spike-count vectors with configurable binning

**Historical baseline.** See D-025 and D-026 for the current bench configuration.

**Choice and status.** Normal telemetry carries eight per-channel spike counts over a configurable bin interval. A 25 ms interval is the current reference/default, not a fixed requirement. Threshold method, adaptation, polarity logic, refractory interval, and count width remain open.

**Objective.** Deliver useful low-rate activity summaries while retaining software control over detection behavior.

**Alternatives and tradeoffs.** Continuous raw telemetry preserves waveforms but increases radio/data handling demand. Individual event timestamps preserve more timing information but increase and vary the payload. Count vectors yield a small predictable normal payload, sacrificing timing and waveform detail within each bin. Waveform characterization uses analog test points and external instruments; onboard raw capture is no longer assumed.

**Calculation.** Assuming eight 8-bit counts and 25 ms bins:

```text
payload rate = 8 channels × 8 bits × 40 bins/s = 2560 bit/s
```

This excludes framing and link overhead. Eight-bit counters are an example, not finalized sizing.

**Risks and mitigation.** Biphasic lobes can be counted twice; refractory logic must suppress duplicates without unnecessarily merging distinct spikes. Bin transitions can lose or double-count events unless counter ownership and handover are explicit. Define overflow behavior and sequence/timing metadata before implementation.

**Verification / reopen when.** Use labeled synthetic or replayed spikes to quantify missed events, false positives, duplicate counts, and timing/bin-boundary behavior. Set acceptance thresholds before declaring detection performance achieved. Reopen the representation if the intended analysis requires timing information that bins discard.

### D-006 — BLE, wired debug, and a Python verification host

**Choice and status.** BLE is the telemetry baseline. Retain SWD and UART. Include a Python host for configuration, count reception, event diagnostics, logging, and automated tests. A ceramic chip antenna is the working baseline (D-013); matching, exact part, connection settings, and packet format remain open.

**Objective.** Provide direct laptop connectivity, bidirectional configuration, and observability at the small normal payload rate, with manageable integration risk and board area.

**Alternatives and tradeoffs.** Ultrasonic backscatter offers potentially low device-side telemetry power but requires acoustic coupling, piezo integration, and an external receiver chain. WPT-coil load modulation can reuse the power link but couples telemetry to that link and requires custom reception. BLE brings radio current peaks and antenna/layout constraints but integrates naturally with an MCU and conventional host tools.

**Rationale.** Host connectivity and diagnostics are part of the verification architecture. Small payloads create an opportunity for low duty cycle; actual average power still depends on connection behavior and firmware. SWD and UART preserve access when the wireless path fails.

**Risks and mitigation.** BLE bursts can disturb the analog supply or couple into inputs. Antenna keep-out and nearby coil/battery structures constrain layout. Consider a selectable onboard antenna/external RF test path; it is a candidate mitigation until layout and matching are designed.

**Verification / reopen when.** Measure radio peak/average current, packet loss, latency, range, and neural noise with BLE active. Verify host decoding and dropped-packet visibility. Verify event diagnostics without assuming onboard waveform capture.

### D-007 — Mutually exclusive CHARGE and RUN

**Historical baseline.** See D-025 and D-026 for the current bench configuration.

**Decision date: original battery-charge choice unknown; exclusive-mode revision 2026-09-22. Recorded: 2026-09-21; last revised: 2026-09-22. Status: Locked operating policy, circuit implementation open.**

**Choice.** Wireless power charges the battery only while CuraLink's main system is off. In **CHARGE**, WPT reception/rectification and the battery charger may be active, but the AFE, STM32WBA52 and BLE are off. In **RUN**, WPT is absent, charging is inactive, and the battery supplies the system. **WPT present implies system disabled**, including after charge termination; the detector must implement this rule over a defined supported field/coupling envelope. On field removal, RUN may start automatically once battery and rails are valid. The earlier secondary charge-and-run option is **superseded**; it is no longer a supported mode.

**Objective / constraints and evidence.** Preserve microvolt-scale signal integrity without a nearby resonant field, rectifier pulses, charger current or charge-related rail/common-mode interference during recording. This operating rule comes from the user's 2026-09-22 power-architecture summary; the interference rationale has not yet been quantified on CuraLink hardware.

**Alternatives and tradeoffs.** Simultaneous charge-and-record and continuous WPT-only operation would permit operation without a charged battery but increase power-path complexity and the burden of proving quiet neural inputs under an active field. Exclusive modes simplify charger/system interaction and verification, while interrupting sensing during charging. A full load-sharing power-path charger is not a functional requirement under this policy.

**Rationale.** The project does not require recording while charging. Enforcing the separation in hardware is more robust than relying on firmware that may be unpowered, resetting or late to respond. Charge completion is not an enable condition; WPT presence governs the mode.

**Risks and mitigation.** A rectified-voltage detector can miss weak or intermittent coupling; WPT_RAW may lag actual field presence during startup and removal. Define the supported field/coupling envelope and detector threshold, hysteresis, hold time, default state, brownout behavior and switch timing so RUN cannot overlap detectable WPT activity. Provide battery undervoltage and charger-temperature protection; avoid back-power through signal, debug or charger paths. Battery size and regulation still govern one-hour runtime.

**Verification / reopen when.** Test field application/removal, charge termination with field retained, intermittent coupling, coil misalignment, empty battery, reset and rapid cycling. Confirm the system rails, AFE and BLE are off throughout CHARGE and that startup after field removal occurs only with valid battery/rails. Measure RUN noise and runtime, usable WPT DC power and end-to-end efficiency with boundaries stated. Reopen exclusive operation only by explicit decision supported by a new use case and measured interference evidence.

### D-008 — First-board reliability within a compact footprint

**Choice and status.** Prioritize electrical suitability, availability, assembly reliability, and debug access ahead of marginal size savings. Aim for 25–30 mm XY. A single board versus a stack remains open.

**Objective.** Maximize the probability that Rev A can be assembled, brought up, characterized, and repaired without a redesign.

**Alternatives and tradeoffs.** Aggressive miniature packages and dense layouts can save area but reduce inspectability and rework access. Moderate QFN/DFN and accessible leaded packages with 0402/0603 passives are preferred when electrically suitable. A stack may save XY area and separate subsystems, but introduces height, connectors, grounding, parasitics, and mechanical constraints.

**Rationale.** The footprint is an objective that supports compact-system learning. It must not override antenna performance, analog integrity, manufacturability, or access to critical nodes.

**Risks and mitigation.** Reserve necessary SWD/UART/reset access, rail isolation/injection, AFE and detector test points, and tuning/bypass footprints. Use these provisions selectively where failure isolation or uncertain component values justify their cost. Audit exact footprints, pinouts, contact orientation, and power sequencing before fabrication.

**Verification / reopen when.** Perform pin/footprint and assembly reviews, floorplanning, and subsystem bring-up planning before layout release. Choose stacking only after comparing concrete layouts and their power, noise, WPT, RF, and assembly consequences.

### D-009 — Passive AWG-driven input fixture

**Choice and status: superseded in source generation by D-014 on 2026-09-22.** The original handoff used one AWG feeding a passive SMA/attenuator/fanout fixture, eight replaceable source resistors, and an FFC connection. The source model, per-channel resistors and FFC strategy remain useful. The user now wants laptop-controlled DAC generation on a separate fixture board.

**Objective.** Provide controlled microvolt-scale signals and representative source resistance without developing a second active acquisition/emulation system.

**Alternatives and tradeoffs.** A custom eight-channel DAC emulator enables independent waveforms but adds firmware, noise, calibration, and another board to validate. A common AWG waveform supports initial channel gain, matching, and acquisition checks with fewer dependencies, but cannot by itself establish independent-channel or crosstalk performance.

**Working implementation.** The handoff proposes approximately 49.9 kΩ series and 49.9 Ω shunt attenuation, bypass/selectable attenuation, nominal 47 kΩ replaceable resistors per channel, test pads, and an 18-pin approximately 0.5 mm-pitch FFC.

```text
Provisional FFC pin assignment:
1 GND   2 CH1   3 GND   4 CH2   5 GND   6 CH3
7 GND   8 CH4   9 GND  10 CH5  11 GND  12 CH6
13 GND 14 CH7  15 GND  16 CH8  17 REF  18 GND
```

**Calculation boundaries.** A nominal 1000:1 divider maps 200 mVpp to about 200 µVpp. Calculate the actual ratio using the AWG output impedance and the complete connected circuit, then verify it. The eight series 47 kΩ resistors are not eight shunt loads to ground: each branch includes the AFE input impedance and bias network. The handoff's simple 47 kΩ/8 loading statement must not be used as the final fixture model.

**Risks and mitigation.** Common drive masks some coupling effects. Crosstalk tests require selective drive and appropriately terminated quiet channels; provide a means to isolate channels when designing the fixture. Large electrode offsets require a separate injection method because the normal attenuator also attenuates DC. Shared REF behavior and ground paths must be specified with the AFE.

**Verification / reopen when.** Verify attenuation, noise floor, source resistance, pin mapping, cable/contact orientation, and input amplitude with the fixture connected. Add independent stimulus capability only when required by a defined test objective.

### D-010 — Budget, runtime and deadline

**Decision and recorded date: 2026-09-21. Status: user-confirmed constraints.** Keep the first assembled prototype under US$150 excluding lab equipment; use one hour as the initial runtime target and show capacity/runtime tradeoffs. There is no hard completion deadline. These supersede the older one-month schedule. Verify with actual procurement quotes and measured current/discharge data; current cost and runtime tables are allocations and estimates.

### D-011 — MCU alternatives and initial gain study

**Decision and recorded date: 2026-09-21. Last revised: 2026-09-22. Status: MCU alternative study superseded by D-013; gain choices remain candidates.** The user permits non-STM MCUs while retaining the custom AFE as central to CuraLink, and narrowed work to gain calculations and high-level parts. The assistant previously interpreted this as permission to evaluate a separate waveform ADC; the user corrected that interpretation in D-012.

**Objective and rationale.** Compare complete event-capture/radio subsystem area, power, cost, and debug access rather than MCU package alone. The prior 12-bit ADC example supporting approximately 1000 V/V is historical and no longer justifies a selected gain.

**Candidates / tradeoffs.** The prior BG22 ranking and ESP32-C3 disadvantage based on ADC channel count are withdrawn. The user subsequently selected STM32WBA52 as the MCU working baseline in D-013. Verify event GPIO/timing resources, power, package, development support, and RF integration. TLV9064S and TPS7A20 remain provisional AFE/regulator candidates. BQ25185DLHR is now the selected charger IC baseline under D-021; its SYS behavior must not violate the exclusive CHARGE/RUN policy. None is procurement- or fabrication-locked. The external ADS7951 fallback is outside the current direction.

**Evidence / risks.** The [calculation record](calculations/afe-study/report.md) contains a linear noise/transfer model and limited synthetic detection tests. The model predicts approximately 1.68 µV RMS electronics noise over 300 Hz–7 kHz using its 1 kHz gain, but does not cover layout or overload behavior. Its input capacitance fails the original 10 MΩ band target; a source-loading-based alternative is proposed, not accepted. Exact package availability, programmer support, RF/WPT integration, and actual budget remain open.

**Verification / reopen when.** Review the [gain/parts note](design/gain-and-parts-shortlist.md), then validate the chosen acquisition and AFE on the bench before locking parts. The broader ADC-based system study is preserved as history. The current two-board analog proposal is linked in D-014; detailed component values remain provisional.

### D-012 — Remove waveform ADC; detect and count analog events

**Decision date: 2026-09-22. Recorded: 2026-09-22. Last reviewed: 2026-10-01. Status: Baseline direction; implementation open.**

**Choice.** Remove waveform digitization from the main signal path. Use the custom AFE, analog threshold detection, MCU event capture/counting, and BLE. D-004 is superseded. An unused ADC peripheral inside an otherwise suitable MCU does not require using it; no external waveform ADC or onboard debug ADC is assumed.

**Objective / evidence.** Follow the user's explicit correction, “we are trying to remove the ADC.” This is design intent, not a demonstrated circuit or measured power saving. Existing channel/input requirements, budget, runtime target, and narrow gain/parts scope remain in force.

**Alternatives and tradeoffs.** ADC/software detection offered waveform observability and flexible algorithms. Analog detection removes conversion and waveform-processing requirements but adds comparator, threshold, hysteresis, calibration, and event-capture requirements. System power and area must be compared including these circuits.

**Rationale.** The normal output is event counts. The AFE must still reject DC, control bandwidth/noise, and amplify electrode-level signals. Select gain against detector errors and headroom, not ADC code counts. The STM32WBA52 was selected for BLE and event handling; its ADC remains unused.

**Risks and mitigation.** Comparator noise/chatter, threshold drift, and biphasic lobes can cause false or duplicate events. Specify polarity handling, hysteresis, refractory/rearm logic, and simultaneous-event capture. Preserve analog test points and external-instrument characterization for first-board diagnosis. Comparator topology, threshold generation, exact gain, and MCU remain open.

**Verification / reopen when.** Budget detector offset/noise and threshold errors at the electrode; test missed/false/duplicate events over the input envelope, pulse capture during BLE activity, overload recovery, total power, and runtime. Reopen only if demonstrated tradeoffs defeat the objectives; do not silently reintroduce an ADC.

**Candidate review, recorded 2026-10-01; no replacement decision accepted.** WBA55CGU6 with ADC/DMA and digital detection is a plausible alternative, but is primarily an acquisition proposal rather than a complete AFE. [ST DS14127 Rev. 10, Tables 2–3 and 83–85](https://www.st.com/resource/en/datasheet/stm32wba52ce.pdf) confirms WBA55 SMPS capability, WBA52's lack of SMPS, sufficient ADC inputs on both proposed packages, and characterized 10.9-bit typical / 9.9-bit minimum ENOB. At 3.0 V reference and hypothetical 1000 V/V gain, 50 µVpp occupies 68.3 ideal codes; this is a calculation, not a sensitivity or noise result. Eight channels at 30 kS/s require 240 kS/s aggregate, leaving only 4.17 µs average per complete conversion. Source settling, sequence overhead and actual clocks must fit that budget.

ST's default WBA55 BLE example enables temperature-based radio calibration; its [temperature module](https://github.com/STMicroelectronics/STM32CubeWBA/blob/main/Projects/Common/WPAN/Modules/temp_measurement.c#L69) requests ADC measurements. The current [ADC controller helper](https://github.com/STMicroelectronics/STM32CubeWBA/blob/main/Projects/Common/WPAN/Modules/adc_ctrl.c#L39) allows seven user ranks plus VREFINT and reconfigures ADC requests; that is a software-helper restriction, not a hardware channel limit. An eight-channel circular-DMA implementation must integrate calibration and demonstrate continuity/channel indexing. The existing passive DET recentering was modeled for comparator loading and needs ADC charge-sharing/recovery qualification or a revised driver. Gain, anti-alias attenuation, offset/artifact recovery, shared-REF performance and whole-system power must be evaluated together; SMPS capability alone does not establish a runtime advantage. Preserve D-012/D-013 until the user selects a replacement.

### D-013 — STM32WBA52 BLE MCU and ceramic chip antenna

**Decision date: 2026-09-22. Recorded: 2026-09-22. Status: User-selected working baseline; exact ordering part/package and RF design open.**

**Choice.** Use STM32WBA52 for event counting, binning and BLE; leave waveform ADC unused. Use a ceramic chip antenna on the CuraLink PCB, with RF matching/tuning and a board keep-out. The earlier EM9304 plus ceramic antenna preference was briefly accepted on 2026-09-22, then explicitly replaced by the user's statement, “we are using the STM32WBA52.” Preserve it only as design history.

**Objective and evidence.** The workload is eight digital events plus low-rate BLE telemetry; the ADC is not a selection benefit. ST lists a BLE radio, programmable output up to +10 dBm, integrated balun, and an ADC peripheral. External ceramic antenna/matching remain necessary. [ST product specification](https://www.st.com/en/microcontrollers-microprocessors/stm32wba52kg.html). The selected device has not been pin-mapped or tested in this project.

**Alternatives and tradeoffs.** EM9304 offered a 4 × 4 mm QFN without a general-purpose sensor ADC and a more specialized development path; its smallest WLCSP exposes only six GPIO, insufficient for eight direct event lines ([manufacturer datasheet](https://www.emmicroelectronic.com/sites/default/files/products/datasheets/9304-DS%20%28updated%20Oct%202024%29.pdf)). STM32WBA52 has an unused ADC and potentially larger package but matches the user's development and radio preference. A ceramic chip antenna is compact as a component but still consumes board clearance and matching effort; board-level area must be compared with a trace design.

**Rationale.** Preserve a single-chip BLE/controller architecture and familiar SWD workflow while supporting analog event detection. TX output-power headroom is a capability to measure against the final RF environment, not proof of tissue-link success. CuraLink is a benchtop analog prototype, not a qualified implant.

**Risks and mitigation.** Select an antenna against the actual board, ground, battery and coil geometry; reserve tuning components/test access. Audit eight event pins alongside SWD, UART, RF, clocks and power. Verify GPIO interrupt capture during BLE and compare full-system current. The 5 × 5 mm UFQFPN32 is a package candidate, not a completed pinout.

**Verification / reopen when.** Measure link reliability/current over programmable TX settings and the intended environment; complete the pin map, RF layout and packet/event tests before fabrication. Reopen the MCU only if concrete implementation or measured constraints defeat the accepted baseline.

### D-014 — Separate USB/DAC stimulus and CuraLink boards

**Historical baseline.** See D-025 and D-026 for the current bench configuration.

**Decision date: 2026-09-22. Recorded: 2026-09-22. Status: User-selected architecture; implementation values proposed.**

**Choice.** Use board 1 for laptop-controlled analog stimulus generation with one DAC waveform split eight ways through individually replaceable nominal 47 kΩ source resistors and an FFC. Board 2 is the battery-powered eight-channel AFE, analog detector, STM32WBA52 and BLE board. The user's “laptop → ADC” was explicitly clarified as **DAC** for waveform generation. D-009's AWG input is now a possible bring-up bypass, not the normal source.

**Objective and evidence.** Preserve the established CH1–CH8/REF signal model while making test templates reproducible from the laptop. One shared waveform tests gain, matching and simultaneous events; channel select/quiet termination permits selective-drive crosstalk tests. It cannot reproduce independent overlapping waveforms. Detailed [AFE and fixture proposal](design/2026-09-22-two-board-analog-afe.md) and [linear calculations](calculations/analog-event-afe/results.json) are candidate evidence only.

**Alternatives and tradeoffs.** An AWG/passive fixture requires no active stimulus board but limits automated playback. Eight DAC channels would allow independent test waveforms but add cost, firmware and validation; the user selected a single source. The proposed USB controller/DAC/filter/divider and exact FFC part remain under review.

**Rationale.** The DAC belongs to the external test fixture. CuraLink's neural signal path remains ADC-free, as required by D-012. Keep the initial 18-contact CH/REF/ground FFC assignment as a candidate; confirm cable orientation and the common ground/reference scheme before release.

**Risks and mitigation.** USB ground noise, DAC steps, attenuator error, cable capacitance, and reference loading can exceed microvolt test levels. Include fixture calibration, quiet branch selection, analog test points, and isolation checks. Cost and electrical limits of both boards must be considered against D-010.

**Verification / reopen when.** Calibrate voltage at the attached FFC/AFE, test quiet-channel coupling and simultaneous events, measure source noise/capacitance, and verify exact connector pinout and contact orientation. Reopen stimulus source count only if the selected tests require independent waveforms.

### D-015 — Adapt source-board protection concepts to CuraLink

**Decision date: 2026-09-22. Recorded: 2026-09-22. Status: User-selected reference method; schematic values are candidates.**

**Choice.** Use the specified [EGRA PCB checkpoint](https://github.com/zanebeeai/egra-og/blob/b915129b144de0e52f8daf5e31ab55e3a1aaabc2/egra-OG_1.before-routeplan-20260601_181915.kicad_pcb) and [Meower hardware](https://github.com/nikki-uwu/Meower/blob/c6f410268a16cf4e0ecb313ea7b957a4a2afa690/hardware/README.md) as *references* for repeated electrode nets, connector treatment, functional grouping and test access. Create a CuraLink-specific eight-channel schematic and protection network; the user will route the PCB manually. Do not transfer the EGRA 34-contact connector, ADS1299 circuit, or electrode shunt capacitor as CuraLink selections.

**Objective / constraints and evidence.** Protect and make observable CH1–CH8 and REF while preserving the 47 kΩ source model, 300 Hz–7 kHz band, and high input impedance. The [source audit](design/2026-09-22-egra-meower-reference-audit.md) traced EGRA's 4.7 nF shunt to the electrode connector side of its 4.7 kΩ series resistor. With CuraLink's nominal source, it calculates a 720 Hz input pole and about −19.8 dB at 7 kHz. EGRA's TPD4E05U06 protects USB data, not electrode pins. The named PCB checkpoint has placement/net data but no routed tracks or board outline. Meower demonstrates accessible input/output probe points and a test fixture. These are inspected source facts and circuit calculations, not CuraLink hardware measurements.

**Alternatives and tradeoffs.** Directly duplicating EGRA would save schematic effort but severely attenuate the spike band and import ADS1299/EEG design assumptions. A connector-side nanofarad filter improves RF suppression but is incompatible with the current source/band objective. A low-capacitance ESD path plus series current limiting and AC coupling is the current *candidate* for each CH/REF line; its fault clamp, leakage, capacitance, resistor stress and input-noise effects require validation. TI's [TPD4E05U06](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf) and [TLV9064](https://www.ti.com/lit/ds/symlink/tlv9064.pdf) data inform the candidate but do not qualify the assembly.

**Rationale.** Matching signal and REF treatment and providing test access serve first-board diagnosis. Adapting the reference layout concepts preserves their useful organization while making the electrical values respond to CuraLink's different input model. The proposed low-C ESD device, 5.1 kΩ resistor and 10 nF series coupling capacitor are provisional schematic values, not accepted final components. No source hardware files were copied.

**Risks and mitigation.** ESD or incorrect-voltage energy may still reach the preamp; cable capacitance and leakage can dominate loading; REF and fixture grounds can inject correlated noise. The ≥10 MΩ across-band input-impedance target is already inconsistent with the assumed amplifier input capacitance. Keep source-side shunt capacitors DNP, match CH/REF, audit connector orientation, expose analog nodes, and define surge/hot-plug/overload cases before routing. Bench-only use does not establish human/animal safety.

**Verification / reopen when.** Resolve the input-impedance target or redesign the input; check full-cable capacitance and ESD/fault currents with worst-case tolerances; validate transient recovery, leakage and channel/reference noise; complete symbol/footprint/pin audits and KiCad ERC before manual layout, then DRC and assembled-board tests. Reopen the protection topology if those checks fail.

### D-016 — 1S charging path, hardware isolation and split rails

**Historical baseline.** See D-025 and D-026 for the current bench configuration.

**Decision date: 2026-09-22. Recorded: 2026-09-22; charger selection revised 2026-09-24 under D-021. Status: Architecture baseline; selected charger IC, other parts/electrical limits and board partition open.**

**Choice.** Use a single-cell rechargeable Li-ion/LiPo battery. The working receiver path is RX PCB coil → resonant tuning → rectifier → reservoir/overvoltage protection → `WPT_RAW` (approximately 5 V **target**, not a locked rating) → 1S CC/CV charger → battery. `WPT_RAW` also feeds a `WPT_PRESENT` detector. A hardware-controlled high-side battery-to-`SYS_RAW` switch opens whenever supported WPT is present and closes after WPT is removed, subject to valid battery and rails. Separate approximately 3.0 V analog and digital LDO rails power the AFE/comparators/bias and STM32WBA52/BLE respectively; approximately 1.5 V analog common-mode is a working candidate. BQ25185DLHR is the selected charger IC baseline under D-021; its settings, SYS treatment, LDOs, cell and common-mode generator remain unselected.

| WPT present | Battery/rail validity | System switch | Main system |
|---|---|---|---|
| Yes | Any | Open | Off |
| No | Valid | Closed after controlled startup | RUN |
| No | Invalid or depleted | Open | Off |

**Objective / evidence.** Implement D-007 without relying on powered firmware for disable, keep BLE load steps off the quiet analog rail, and allow automatic charge-to-run transition. These topology preferences and nominal voltages came from the user's 2026-09-22 decision summary. No part-level power budget, thermal calculation or hardware verification establishes the voltages or switch arrangement yet.

**Alternatives and tradeoffs.** A PMOS is simple, but its body diode and gate drive require analysis; a dedicated load switch can provide controlled slew and, if required, reverse-current blocking. Back-to-back FETs are a candidate if `SYS_RAW` can be externally driven above BAT. BQ25185 includes a regulated SYS power-path output; keep the main system disconnected during CHARGE to preserve the exclusive-mode requirement. Separate LDOs improve rail partitioning at a cost in area and quiescent current. A single LDO might be simpler, but must meet measured BLE/AFE coupling limits.

**Rationale.** For a PMOS concept, connect source to BAT and drain to `SYS_RAW`; pull its gate toward source to turn it off and low relative to source to turn it on. Derive control relative to the source rather than directly applying the nominal 5 V WPT node to the gate. The switch state follows WPT presence, not charger termination. If a separate coil/receiver PCB is used, placing resonant tuning, rectifier, reservoir and input protection beside the coil and carrying **DC WPT_RAW** to the main board is the preferred *partition candidate*, reducing resonant-loop connector parasitics. Main-board charger, battery, switch and regulators are the matching candidate placement. The separate RX board itself is not yet selected.

**Risks and mitigation.** A fixed 3.0 V LDO needs BAT at its input above 3.0 V **plus dropout and switch/interconnect loss**; calculate the usable capacity and one-hour runtime over discharge, or revise the rail/regulator strategy. Verify switch default state, detector operation with no/weak WPT, startup sequencing, gate-source ratings, body-diode/back-feed routes, charger input range/OVP, battery temperature sensing, overcurrent and undervoltage protection. `WPT_RAW≈5 V` is a target at the defined load/alignment, not proof of adequate charger input under all conditions. The analog common-mode generator must be quiet and stable across mode transitions.

**Verification / reopen when.** Complete a worst-case source-to-load voltage/current/thermal budget, including battery discharge and BLE peaks; check charger CC/CV/termination and protection; demonstrate hardware switch truth table, field-present charge-complete holdoff and automatic removal transition. Scope `WPT_RAW`, BAT, `SYS_RAW`, both rails and common-mode during startup/brownout. Select the coil-board partition only after mechanical, noise and WPT efficiency comparison. Reopen rail values, switch technology or physical partition when calculations or bench data show a constraint violation.

### D-017 — WPT simulation workflow (user alias DEC-WPT-002)

**Decision date: 2026-09-22. Recorded: 2026-09-22; last revised: 2026-11-22. Status: Selected method as revised by D-018; actual nominal ADS receiver/demand evidence, real charger and hardware qualification open.**

**Choice.** DEC-WPT-002 originally selected HFSS physical-coil modeling → Touchstone `.s2p` → ADS resonant tuning, nonlinear rectifier, reservoir and initial resistive DC load. D-018 / DEC-WPT-003 narrows the Rev A implementation: reproduce the published coil geometry and begin ADS circuit design from the paper's measured L/R/k coupled-inductor model, without rerunning coil optimization in HFSS. Retain HFSS → `.s2p` for geometry correlation and require it when RX/TX size, materials, separation, nearby copper/battery/ferrite or another physical condition changes materially. In either route, optimize delivered DC power and explicitly defined RF-to-DC efficiency; use L, R, Q, M, k, SRF and S21 as diagnostics.

**Objective / constraints and evidence.** Separate the measured coil baseline from CuraLink-specific tuning and RF-to-DC conversion, and evaluate whether the receiver can deliver useful, bounded DC power under realistic alignment and load. The workflow comes from DEC-WPT-002 and its Rev A shortcut from DEC-WPT-003. [Ansys documents Touchstone export](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v251/en/Subsystems/HFSS/Subsystems/HFSS%20Scripting/Content/ExportNetworkDataPlanarEM.htm?TocPath=Design+Object+Script+Commands%7C_____46); [Keysight documents harmonic-balance treatment of a nonlinear rectifier](https://www.keysight.com/in/en/assets/7018-05801/case-studies/5992-2395.pdf). The 2026-10-09 actual ADS study below supersedes the earlier no-simulation state; no CuraLink hardware measurement is recorded.

**Simulated evidence, 2026-10-09.** The [reproducible receiver study](../hardware/wpt/ads/receiver-fixture-2026-10-09/README.md) includes decks, datasets, logs, load/power matrices, a finite 64-evaluation four-capacitor search, harmonic/stress checks and fresh native-OA validation. The separate BAT54 manufacturer-model Candidate at 23.5 dBm / 208.333333 Ω / HB31 gives 5.08853 V, 124.287 mW and 55.517% available-RF-to-DC efficiency; its fundamental RX load is 1.611 − j28.880 Ω. The isolated variant's DC power changes by about 0.015% from order 31 to 127; numerical convergence does not establish broadband coil/model fidelity. The old diode seed produces about 58 mW at 23 dBm / 240 Ω while exceeding its reverse bound. Corrected floating-secondary connectivity and current-probe signs were independently netlisted/simulated; the original saved OA grounded the secondary differently from its latest generated netlist, so only new copies were corrected. Main system load is excluded in CHARGE.

**Candidate rationale and remaining risk.** BAT54-7-F / LCSC C106920 provides a genuine manufacturer card and 30 V physical reverse rating; its model's BV=50 V is only a fitted parameter. LCSC showed 87,360 units on 2026-10-09; this is neither a reservation nor assembly qualification. Greater junction capacitance requires retuning, four SOT23 packages consume area, and package/recovery/PVT behavior remains unqualified. Retain it as a simulation candidate, not an accepted final diode. The same-power 1 MΩ fixture reaches 11.915 V, about 574 mA RMS RX winding current and 132 mW winding loss; raw OVP/control and thermal limits are unresolved. The loaded TX-series capacitor sees about 36.1 V peak. Qualify practical component values/losses and all load/protection states before hardware selection; see [criteria, comparisons and reopening conditions](../hardware/wpt/ads/README.md).

**Additional actual ADS evidence, 2026-11-22.** [The fixed-coil review](../hardware/wpt/ads/review-2026-11-22/README.md) verifies the original 50-ohm matching transformation (RX 2.38008 − j28.07827 Ω) and 71.87346% modeled passive S21 power, consistent with the published nominal limit. The newly executed authored SDD DC curve has zero draw at zero volts, 20.75 mA charger / 0.8 mA control at 5 V and reduced weak-input draw. Forty-eight HB cases keep coils fixed and sweep explicit input demand, battery voltage, source power and overhead. All 32 low-demand cases leave the law's 0–5.5 V CHG_IN domain; reject their charger outputs and use them only to expose missing raw regulation. RF model energy balance closes to <6.8e-16 W. No converter/charger-loop, actual eFuse cutoff, cell chemistry, PVT, capacitor ESR or fabricated-coil qualification is implied. The buffer suggestion remains a proposal: high-impedance voltage sensing cannot extract arbitrary charging power without accounting for its supply and reflected real load.

**Alternatives and tradeoffs.** A coil-only Q/k/S21 study is faster but cannot establish rectified output under nonlinear loading. Starting directly with a charger model adds control behavior before the coil and rectifier are understood. A resistive load yields an interpretable first RF-to-DC comparison; later charger/load-state models must replace it before battery-charge claims. A passive `.s2p` cannot capture nonlinear rectifier, WPT controller or thermal behavior itself.

**Rationale.** The original division uses each tool for the quantities it represents well. DEC-WPT-003 saves Rev A time by using fabricated-coil measurements as the initial circuit model and reserves new EM work for changes that make those measurements nonrepresentative. For the first load, report `P_DC = V_DC²/R_LOAD` and `η_RF→DC = P_DC/P_RF,accepted at the TX coil-model input port`, recording source impedance and port planes. Report other efficiency boundaries under distinct names. The detailed [simulation method](design/2026-09-22-wpt-simulation-method.md) defines sweeps and reproducibility.

**Risks and mitigation.** A fixed L/R/k model does not directly represent frequency-dependent parasitics, SRF, offset, tilt or environmental changes. Sweep k only as a labeled sensitivity estimate until geometry-dependent data exist. Nearby copper/battery/ferrite, tuning-capacitor double counting, inadequate harmonic order or incorrect power boundaries can invalidate results. Verify ADS convergence and treat simulated results as predictions until measured on fabricated CuraLink coils.

**Verification / reopen when.** Archive the published coil-model source/values, ADS schematic/models, parameter sweeps, power-boundary definitions and derived DC voltage/power/efficiency. Under D-019, compare end-to-end hardware DC behavior across load and alignment without claiming independent coil-parameter validation. Add the HFSS geometry, convergence and `.s2p` record when D-018's reopening conditions apply. Reopen the workflow if model fidelity or hardware correlation is inadequate.

### D-018 — Reuse published 13.56 MHz planar coils for Rev A (DEC-WPT-003)

**Decision date: 2026-09-22. Recorded: 2026-09-22; evidence updated: 2026-11-22. Status: Selected Rev A baseline; fixed-coil nominal ADS link/receiver modeled, CuraLink physical reproduction and thermal envelope unverified.**

**Choice.** For CuraLink Rev A, reuse the square planar spiral pair published by Luo et al. at 13.56 MHz and 10 mm nominal coaxial separation instead of re-optimizing the coils. On approximately 0.8 mm FR4 with 1 oz copper, the paper specifies TX outer/inner diameters of 40/14.60 mm, 8 turns, 1.3 mm trace width and 0.15 mm spacing; RX outer/inner diameters of 10/5.55 mm, 5 turns, 0.3 mm trace width and 0.15 mm spacing. Begin ADS work with coupled inductors using the measured L/R/k values. Design CuraLink-specific matching, rectifier, reservoir and charger interface; do not copy the paper's matching capacitors because they transformed a 50 Ω measurement load. This is not a claim that CuraLink will reproduce the paper's performance or safely transfer a particular power.

**Objective / constraints and evidence.** Fit the receive coil comfortably within CuraLink's approximate 25–30 mm main-board envelope while using a published 13.56 MHz link intended for a compact neural-recording receiver. The paper reports measured values at the nominal geometry of approximately `L_TX = 2.49 µH`, `R_TX = 1.80 Ω`, `Q_TX = 118`, `L_RX = 0.330 µH`, `R_RX = 0.399 Ω`, `Q_RX = 70.4`, `M = 60.0 nH` and `k = 0.0662`. Its measured `S21 = -1.55 dB`, or approximately 70%, used primary and secondary matching networks between 50 Ω VNA ports. That result is RF coil-link efficiency and excludes rectification, reservoir, regulation and battery charging. [Luo et al., “Design and Optimization of Planar Spiral Coils for Powering Implantable Neural Recording Microsystem,” 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10302922/).

**Published-file availability.** No public GitHub repository or Touchstone/supplementary dataset was found on 2026-09-22. The paper states “Data Availability Statement: Not applicable,” and its archived full-text record exposes no supplementary-material entry. Therefore Rev A begins with the paper's single-frequency lumped measurements using the [ADS setup](design/2026-09-22-ads-wpt-model-setup.md), not an original measured `.s2p`. This search result is evidence of current public availability, not proof that the authors have no private VNA data.

**Alternatives and tradeoffs.** A custom coil optimized around CuraLink's nonlinear rectifier, charger, enclosure and alignment envelope could outperform or package better, but needs more EM optimization. A larger RX could improve coupling but consume main-board area. Adopting the paper geometry saves initial design time and supplies measured correlation targets, while its 50 Ω matched test condition does not represent CuraLink's rectifier load.

**Rationale.** The pair has already been optimized, fabricated and VNA-measured for a compact neural-recording application. Using measured coil parameters gives Rev A a stronger and faster initial basis than repeating the same optimization. For rectifier selection, treat the reference RX as a two-terminal source and compare the low-capacitance Schottky full-wave bridge against a two-diode doubler after independently retuning each matching network. Do not infer available charging power from the 70% number without a defined accepted TX power and rectified load.

**Receiver evidence, 2026-10-09.** D-017 now records actual 13.56 MHz R-L-M/full-bridge HB predictions, including a near-5 V / 124 mW resistor-load point and 11.9 V near-open-load stress. These use ideal capacitors and carrier-frequency constant coil parameters. The paper's optimal complex RX load is a starting diagnostic, not an exact requirement for nonlinear charging. No new geometry or measured-coil acceptance is implied; environmental/parasitic changes still reopen HFSS.

**Constraint reaffirmed / evidence updated, 2026-11-22.** The user explicitly requires matching the system to these coils. The fresh passive ADS check returns 71.87346% modeled transfer with the original network; nonlinear and signal reviews do not alter the coil baseline. Changes to surrounding metal/stackup still require model review even when the spiral dimensions remain fixed.

**Risks and mitigation.** PCB stackup, copper roughness/thickness, solder mask, feed routing, nearby ground/battery/ferrite and manufacturing tolerances may shift L, Q, SRF and matching. The 10 mm coaxial air/FR4 condition may not represent CuraLink's final surroundings or offset/tilt. Preserve tuning access and test coupons; sweep L/R/k and component tolerances in ADS, provide tuning options and use end-to-end DC testing. Reopen HFSS if the published physical conditions change.

**Verification / reopen when.** D-019 supersedes the planned VNA gate because no VNA is available. Measure delivered DC voltage/power at nominal, offset, tilted and separation extremes with candidate rectifiers and charger-like loads; exercise tuning options and compare trends with ADS predictions. Reopen HFSS if RX/TX size, separation, stackup/materials, nearby copper/battery/ferrite or another physical condition changes materially; reopen the geometry if it cannot meet required charge power, voltage, thermal, area or alignment limits.

### D-019 — Rev A WPT verification without a VNA

**Decision date: 2026-09-22. Recorded: 2026-09-22. Status: User-confirmed verification constraint.**

**Choice.** CuraLink will not obtain or use a VNA for Rev A. Trust the published nominal coil measurements for the reproduced geometry and design the CuraLink matching network in ADS around the nonlinear rectifier/reservoir/charger load. Provide replaceable or selectable tuning components and validate the assembled link through rectified voltage, delivered DC power, behavior across representative loads/alignment and component stress. Do not describe this as independent confirmation of the paper's coil efficiency or S-parameters.

**Derived import artifact.** A calculated 50 ohm [Touchstone file](../hardware/wpt/models/luo2023_coupled_coils_lumped_50ohm.s2p) is retained for ADS linear import checks. It is generated solely from the paper's nominal L/R/k values over 1–30 MHz and explicitly labeled as a constant-R ideal coupled-inductor model, not measured data. Rectifier harmonic-balance work should use the explicit R-L-M schematic because the paper does not provide broadband coil behavior at rectifier harmonics.

**Objective / constraints and evidence.** Complete Rev A within available equipment and time. The user stated that a VNA is unavailable and cannot be obtained. The Luo et al. pair supplies measured nominal L/R/Q/M/k values, while the charger creates a different nonlinear load from the paper's 50 Ω VNA setup.

**Alternatives and tradeoffs.** A calibrated VNA would separate coil, matching and rectifier faults and provide broadband `.s2p` data, but is unavailable. Re-running HFSS is unnecessary while the published physical conditions are reproduced and would still not measure fabrication error. End-to-end DC tests answer whether CuraLink charges, but provide less diagnostic evidence when measured performance differs from ADS.

**Rationale.** The required engineering work is to transform the rectifier's RF input behavior into a suitable load for the published secondary coil, while separately matching the transmitter source to the primary. At the nominal measured link, the paper reports an optimal secondary load near `2.4 - j28.12 Ω`; use this as a consistency target, then optimize delivered DC power and RF-to-DC efficiency because a nonlinear rectifier does not behave like a fixed resistor.

**Risks and mitigation.** Stackup, copper, solder mask, nearby structures and alignment may shift resonance or coupling without being observable directly. Use the specified geometry/materials, minimize unmodeled metal near the RX coil, provide capacitor banks/DNP footprints and rectifier test access, sweep L/R/k and component tolerances in ADS, and avoid a design that works only at a sharp nominal optimum. Maintain no-load OVP and component-voltage margin.

**Verification / reopen when.** Before committing the charger, test the rectifier into several known resistive loads and record gap/alignment, TX setting, `V_DC`, ripple, estimated `P_DC`, temperatures and tuning population. Then test charger states including low cell, constant current, constant voltage, termination/full battery and no battery where allowed. Reopen the coil/matching design if no tuning population meets the required voltage/power and stress limits over the intended envelope. Reopen the verification plan if VNA or equivalent calibrated RF measurement access later becomes available.

### D-020 — LCSC sourcing for pick-and-place components

**Decision date: 2026-09-24. Recorded: 2026-09-24; last reaffirmed/reviewed: 2026-10-02. Status: Locked sourcing requirement.**

**Choice.** Select PCB-mounted electronic BOM components from LCSC's orderable catalog for CuraLink pick-and-place assembly. For each chosen part, record the LCSC order code and manufacturer part number, and verify that the exact package/variant is available for the intended assembly process when the part is selected and again at BOM release. This is a sourcing constraint, not a requirement to use LCSC-listed components as evidence of electrical suitability.

**Objective / constraints and evidence.** Reduce split sourcing and make the design compatible with the user's planned LCSC-based pick-and-place workflow. The user explicitly set this requirement on 2026-09-24. LCSC stock and assembly eligibility are time-dependent and must be checked at the time of design freeze.

**Latest verified inventory, 2026-10-02.** [The saved primary LCSC audit](../hardware/rev-a/procurement/stock-audit-2026-10-02.json) confirms all 80 unique BOM SKUs plus the external FFC cable have sufficient immediate overseas inventory for one board, exact MPNs and overseas sale/display flags. It includes DNP variants and the manually mounted NTC. The MCU has nine units available; 32 required 909 kΩ resistors round to a 40-piece purchase against stock 140. Cell C19632326 has no usable global product record, and no compatible stocked replacement was verified; its JLCPCB catalog listing cannot establish standalone global LCSC shipment. Minimum-order purchases are approximately US$103.55 excluding the cell and manufacture/logistics, leaving the under-US$150 assembled objective unresolved. These inventory checks do not establish assembly eligibility or cell electrical/protection suitability. No parts were purchased or reserved.

**Alternatives and tradeoffs.** Searching all distributors may expose more technically optimal parts, but can force manual procurement or substitutions that complicate assembly. Restricting the electronic BOM to LCSC narrows the candidate set and may require a different package or topology when a suitable stocked component is unavailable.

**Rationale.** A manufacturable first-board BOM is more useful than a theoretically optimal design whose parts cannot be included in the chosen assembly flow. Electrical ratings, lifecycle, package and datasheet suitability remain mandatory selection criteria.

**Risks and mitigation.** Listings, inventory and part-number suffixes change; similar-looking LCSC listings can have different pinouts, packages, voltage ratings or assembly service eligibility. Check the datasheet against the exact listing, inspect package orientation/land pattern, retain the LCSC code in the BOM, and recheck stock at release. Do not silently substitute unavailable parts.

**Verification / reopen when.** At each part selection and PCB BOM release, verify the LCSC listing, stock, exact manufacturer code, package, footprint, lifecycle and pick-and-place availability. Reopen a selection if the listing becomes unavailable or any listing/datasheet/footprint mismatch appears.

### D-021 — BQ25185DLHR 1S charger selection

**Decision date: 2026-09-24. Recorded: 2026-09-24; last revised: 2026-09-25. Status: Baseline; cell and provisional configuration now specified by D-023.**

**Choice.** Use TI BQ25185DLHR as the Rev A 1S Li-ion/LiPo charger IC baseline. Exact LCSC listing: C19725033, WSON-10-EP. The user selected it because it was listed in stock; stock is time-sensitive and must be checked again at BOM release.

**Objective / constraints and evidence.** Provide a compact, LCSC-orderable 1S CC/CV charger that can be modeled against the WPT rectifier. TI's current Rev. B datasheet specifies resistor-programmable 4.2 V regulation and charge current, input-current limiting, VINDPM, thermal regulation, temperature-sense input and an integrated SYS power path. The exact listing and package were checked against LCSC on 2026-09-24. See the [charger and ADS model study](design/2026-09-24-battery-charger-ads-model.md).

**Alternatives and tradeoffs.** BQ25100 was considered for a smaller package but is not selected: its DSBGA is less convenient for assembly and its input range/OVP is a tighter fit. BQ25185 is larger but is available in a WSON package on the selected assembly source and offers adjustable limits. The integrated SYS pin is not permission to run the AFE/MCU during charging; D-007 still requires system-off during CHARGE.

**Rationale.** Availability through the intended LCSC pick-and-place flow is a user requirement. This selection resolves the charger IC only; it does not establish that the received WPT voltage/power, cell, charging rate, thermal behavior or receiver protection are adequate.

**Risks and mitigation.** BQ25185 input OVP is approximately 18.5 V nominal and disconnects its internal charging path; it does not clamp the approximately 5 V-target `WPT_RAW` node. Maintain independent receiver overvoltage control as required by the rectifier/no-load envelope. The PGEB201212 candidate identified in D-022 has not been qualified against the minimum programmed charge-current setting; the prior 40 mA ADS setting is superseded for it. A user-supplied 40 mA ideal-sink transient run showed a negative output node; do not treat that as a passed charge test. Confirm bridge polarity and source power, then use HB load/power sweeps. Do not let SYS power the system during CHARGE. Include enabled input overhead and the six-hour safety timer; slow charging under VINDPM does not establish complete charging. The 55/100 mAh alternatives and hardware PMOS gate-control proposal remain candidates in the [cell/charger/isolation review](design/2026-09-24-cell-charger-isolation-review.md). NTC, charge-current configuration, charger thermal rise, cell protection and LDO dropout remain open.

**Verification / reopen when.** Confirm exact stock/orderability, symbol/footprint/pin mapping, 4.2 V and charge-current resistor settings, cell charge-rate and NTC compatibility, input voltage under ripple/no-load/fault conditions, thermal dissipation, and mode isolation. Reopen if the listing is unavailable, WPT source cannot satisfy the input envelope, or the cell/system requirements do not fit the part.

### D-022 — PGEB201212 battery candidate assessment

**Decision date: 2026-09-24. Recorded: 2026-09-24; last revised: 2026-09-25. Status: Superseded as working cell by D-023; historical assessment retained.**

**Choice.** Assess the user's identified PGEB201212 1S pouch cell as the intended compact battery candidate. This records the part to evaluate, not a verified final battery selection.

**Objective / constraints and evidence.** The retailer listing reports 8 mAh, 3.7 V nominal, 4.2 V charge voltage, recommended 0.2C charge, no built-in protection, and no specification sheet. The listed recommendation converts to 1.6 mA. Discharge-current notation is ambiguous, so the listing cannot establish a verified continuous-discharge limit. The earlier interpretation of a 1 CmA entry as 1 mA is withdrawn. TI specifies BQ25185's minimum programmable charge current as 5 mA, above the listed 1.6 mA recommendation. An available GEB201212C datasheet describes a different suffix/model and is not evidence for PGEB201212 limits. See the [charger/battery study](design/2026-09-24-battery-charger-ads-model.md).

**Alternatives and tradeoffs.** A larger protected 1S pack or a lower-current charger could meet runtime/charge-rate constraints more readily but increases area or changes the selected charger. The BQ25185 remains the selected charger IC; the battery candidate does not override D-021 or lower the required runtime. The [cell/charger/isolation review](design/2026-09-24-cell-charger-isolation-review.md) compares the manufacturer-specified 55 mAh alternative, a 100 mAh catalog lead, and the distinct GEB201212C; the subsequent D-023 accepts the 55 mAh cell as a working baseline, with qualification still open.

**Rationale.** Record the user's nominated cell and check the actual product against the under-US$150, one-hour-runtime and LCSC sourcing constraints before treating it as the power-system battery.

**Risks and mitigation.** At the estimated 25–35 mA system current, 8 mAh yields only about 14–19 minutes ideal runtime, before usable-capacity and regulator losses. The vendor listing's 0.5C discharge figure would imply only 4 mA continuous, but that retailer notation is not a manufacturer-qualified maximum. The cell has no reported protection and the BQ25185 minimum 5 mA charge setting exceeds the listed recommended 1.6 mA. Do not charge this exact cell from the selected IC until the cell manufacturer confirms that current, temperature sensing and required protection. The prior 40 mA charge setting is superseded for this candidate.

**Verification / reopen when.** Obtain the exact manufacturer datasheet and written maximum/minimum charge and discharge limits, protection/PCM and NTC details. Reopen the cell selection or charger selection if 5 mA cannot be safely supported, runtime is insufficient, or the LDO/system peak-current needs exceed the cell rating.

### D-023 — 55 mAh cell and provisional charging baseline; resume AFE

**Historical baseline.** See D-025 and D-026 for the current bench configuration.

**Decision date: 2026-09-25. Recorded: 2026-09-25; evidence updated: 2026-11-22. Status: Baseline; hardware and sourcing qualification open.**

**Choice.** Retain BQ25185DLHR / C19725033; adopt Taisko 401020-55mah / catalog C19632326 as the working cell (55 mAh typical, 50 mAh minimum, nominal 20 × 10 × 4 mm cell body). Use provisional 20 mA charging at qualified room temperature and 4.1 V regulation pending supplier clarification of the cell's 4.2 V upper-limit tolerance. Target approximately 5 V at 21 mA receiver output, or 105 mW before extra loads and tolerance margin. Evaluate 20, 23 and 26 dBm available RF input in ADS; these are sweep points, not a selected hardware operating power. Resume AFE design while retaining explicit power verification gates. Exact PMOS/detector parts remain candidates.

**Objective.** Meet compact packaging and one-hour runtime without changing the selected charger; establish a concrete receiver load case and preserve exclusive CHARGE/RUN.

**Constraints / evidence.** User accepted the preceding recommendation. Manufacturer cell specification, TI BQ25185 Rev B and calculations are linked in the [cell/charger/isolation review](design/2026-09-24-cell-charger-isolation-review.md). A 20 mA setting is below the cell's room-temperature charge limit, but its cold-temperature limit is lower. At 50% assumed available-RF-to-DC efficiency, 105 mW DC requires about 23.2 dBm; efficiency is not measured. Capacity/current gives 2.75 h plus taper at 20 mA, with completion still subject to the six-hour charger timer. Reduced 4.1 V charging and early termination may reduce usable capacity.

**Load refinement, 2026-10-09.** The earlier 105 mW estimate is historical nominal guidance before full external-control accounting. Existing CHARGE pull-ups alone consume substantially more than the previous 300 µA control estimate. At the 5 V WPT_RAW boundary, a declared nominal fixture uses 20 mA charge + 0.75 mA charger overhead + 0.8 mA control + 143 µA eFuse + 45.45 µA field divider, giving 108.69 mW / about 230 Ω. The declared high-setting/control sensitivity gives 119.79 mW / 208.70 Ω. These are calculated fixtures, not guaranteed current limits; actual mode/output drops, path loss and eFuse conditions must be qualified. D-017's 208.333333 Ω test approximates 120 mW at 5 V but does not prove 20 mA charging or cell behavior. The [charger-load model](../hardware/wpt/ads/charger/recommended-load-model.md) distinguishes a resistor, voltage-compliant authored SDD demand, and slow charge/control modeling; it preserves the accepted BQ25185/cell/settings.

**Charger-fixture execution limit, 2026-10-09.** Authored SDD source parsed/flattened in ADS, but two DC attempts exited 120 because the Linear Simulator license user limit was reached. DC sign/compliance checks and seven prepared HB charge-load cases remain unexecuted; no BQ25185 macro or actual charging result is claimed. [Guidance, assumptions and retained logs](../hardware/wpt/ads/charger/SDD-execution-guidance.md) separate these pending tests from the completed resistor study. A fixed 0.28 V path-drop fixture omits real eFuse/diode/charger dynamics and raw OVP.

**Subsequent execution, 2026-11-22.** The historical license-blocked state above is superseded for equivalent standalone demand fixtures by a new successful DC curve and 48 HB cases. Nominal full-current operation is energy-feasible, but source/load changes produce out-of-range raw voltage or compliance reduction. This resolves the lack of executed SDD evidence, not raw regulation, actual BQ25185/cell behavior or charging qualification. The native October source cell is retained; fresh review data and assumptions are linked under D-017.

**Alternatives / rationale.** Supersedes the tiny PGEB201212 working candidate because the 55 mAh class provides substantially more runtime margin at the unmeasured 25–35 mA system estimate. The 100 mAh catalog alternative remains available for reconsideration if runtime is inadequate; it consumes more area and lacks a fully verified specification in this record.

**Risks / mitigation.** Confirm protected-pack dimensions, actual orderability and assembly handling; match NTC/current settings to temperature limits. A 4.1 V BQ25185 setting does not retain the previous 4.2 V / 100 mA ILIM configuration: TI Table 6-1 maps 130 kΩ to 4.1 V / nominal 500 mA input limit. Audit both coupled settings; that input limit is not a 20 mA battery charge limit. BQ25185 input OVP trips around 18.5 V and does not clamp the receiver rail. Its approximately 3.13 A battery OCP senses its internal BAT-to-SYS FET path; a separate battery-to-PMOS-to-system path bypasses it. Independent cell protection and appropriate system current/undervoltage protection remain necessary. Rectifier bridge reference, diode reverse rating, no-load voltage, receiver protection and PMOS field-detection/interlock remain unresolved.

**Verification / reopen when.** Demonstrate loaded DC power, ripple and component stresses over coupling/load extremes; verify current/CV settings, temperature control, charge completion, cell protection, mode transitions including retained field after termination, and one-hour runtime with LDO dropout. Reopen cell/current/rail choices if these fail. Power is not marked complete or fabrication-ready.

### D-024 — Rev A schematic recommendation and explicit qualification boundaries

**Decision/evaluation authorization date: 2026-10-01. Recorded: 2026-10-01; last revised: 2026-11-22. Status: Candidate implementation; dated CAD/ERC/inventory checks and nominal LTspice/ADS evidence; hardware performance unmeasured.**

**Choice.** Following the user's authorization to compare ADC/comparator detection and build the schematic, recommend STM32WBA52CGU6 with eight conditioned ADC inputs and digital detection/count bins. The [Rev A package](../hardware/rev-a/README.md) contains the editable schematic, physical pin/net tables, LCSC BOM, subsystem derivations and verification record. It retains the WBA52 family, ceramic antenna, eight-channel/shared-REF fixture and exclusive CHARGE/RUN policy. D-012 remains the prior accepted baseline until this recommendation is adopted; the full-band ≥10 MΩ input requirement is unchanged.

**Objective.** Provide a concrete, reviewable first-board design with waveform observability, noise/headroom justification, low analog current, practical protection/isolation, and exact sourceable component suffixes for the user's Altium implementation.

**Constraints / evidence.** The candidate uses seven TLV9004IRUCR and two TLV9054IRUCR quad amplifiers, matched low-C ESD / 5.1 kΩ / 10 nF CH and REF inputs, gain-11 preamps, 311 Hz differential high-pass/gain and two 7.04 kHz Sallen-Key sections. Two sourced 909 kΩ ±0.1% resistors implement each 1.818 MΩ feedback/balance branch. Linear calculations predict approximately 1008 V/V nominal, 969 V/V at 1 kHz, 3.44 µVrms electronics / 3.17 µVrms source noise over 300 Hz–7 kHz and 4.32 mA typical amplifier current. These exclude real ADC, VMID, leakage and interference; see [AFE evidence](../hardware/rev-a/afe/AFE-design-review.md).

The separate adapted final-driver macro-model supports a 150 Ω / 470 pF candidate at about 1.656 µs acquisition, with worst 24.3 µV tested residual across stated polarity/passive/SAR-load cases. The earlier interconnected ngspice adapter did not validate its operating point and remains invalid diagnostic evidence. The 2026-10-02 original-equation TI-family LTspice run now validates all 36 nominal operating points and the stated DC/AC/startup/offset fixtures; it does not establish hardware or PVT performance. Prefer 50 kS/s/channel as a qualification target: at 48 MHz, eight neural conversions require 15.33 µs in a 20 µs frame, while the first alias into the 7 kHz band moves to 43 kHz with approximately 69.4 dB rejection. This costs more conversion/processing activity than 30 kS/s and must be measured. WBA52 ADC4 long sample time is 814.5 cycles; its 17.23 µs temperature conversion requires separate service. Even at 30 kS/s, eight neural plus temperature conversions leave only 0.771 µs before overhead. ADC/BLE service and clock/power constraints remain gates, detailed in the [MCU audit](../hardware/rev-a/mcu/power-and-acquisition-constraints.md).

The preferred 50 kS/s periodic driver tests give ≤4.30 µV additional settling, but total instantaneous 7 kHz / 10 pF error including modeled tracking delay reaches 196.83 µV (0.269 LSB), exceeding the quarter-LSB total-error engineering target. Retain that limitation: approximately 0.20 µV input-equivalent is small versus modeled analog noise, but neither this model nor the static test proves actual ADC accuracy.

**Alternatives and tradeoffs.** Comparator capture could avoid continuous conversions but requires threshold/hysteresis/polarity/recovery circuitry with less waveform visibility; no lower whole-system power is established. Mixed amplifiers improve final ADC settling at much less current than all-TLV9054. All-TLV9004 is a later power experiment, not the driver-qualified draft. Preserving WBA52 avoids changing the MCU family based on an unmeasured WBA55 SMPS benefit. ADC diagnostic visibility motivates the recommendation.

**Power refinement.** The candidate adds opposed PMOS RUN isolation, hardware field/UVLO/charge-temperature logic, delayed mode exclusion, input/system fault limiters, independent 3 V LDOs and digital-good analog sequencing. Nominal UVLO is 3.50 V cutoff / 3.80 V restart; cell charge window is approximately 21.9–35.9 °C. A new board-input calculation allocates ≥120 mW at qualified 5 V, including control/protection margin above D-023's earlier 105 mW estimate. The selected cell's protection limits do not match the guaranteed optional BQ29737 thresholds/current corners; that PCM and WPT input are DNP in the initial emulator/bench configuration. See [power evidence](../hardware/rev-a/power/power-design.md). This does not mark power complete.

**Independent ADS/source checks, 2026-11-22.** The [signal return/source audit](reviews/2026-11-22-signal-return-review.md) checks DC feedback/returns for all 36 units and finds no mismatch in 236 canonical passives, 36 amplifier pin maps and 598 targeted native schematic pins. A translated original-equation TI-family full AFE now gives approximately 1.50319 V ADC bias / 4.4718 mA supply / 969.742 V/V at 1 kHz in fresh ADS. Derived linear spectra reproduce sampled −52.22 dB quiet-channel coupling and approximately 0.823 MΩ input impedance at 7 kHz with the stated FFC model, reinforcing the existing loading failure. All external circuit nodes have intended DC returns; ADS adds paths inside the vendor macros, and noise analysis is excluded after translation. This is nominal model evidence, not ADC/BLE, transient recovery, package/PVT, unpowered injection, physical ground-plane or assembly signoff. See [fresh test sources/results and limits](../hardware/wpt/ads/review-2026-11-22/afe).

**Physical-pin and tolerance corrections, 2026-10-02.** Independent manufacturer audits corrected both TPS25200 maps to OUT1 / ILIM2 / FAULT3 / EN4 / GND5 / IN6 / EP GND, and onsemi SS14 to A1 / K2. R511 changed to stocked 1.0 MOhm +/-1%; its 1.01 MOhm maximum stays below the allowed 1.1 MOhm ceiling. Refreshed source/CAD pin tables, zero-finding ERC and exact manufacturer-pin invariants pass. The previous transfer/ERC check could not catch incorrect source maps; preserve it as historical transfer evidence only. Earlier eFuse/SS14 handoffs are superseded.



**LTspice evidence, 2026-10-02.** The nominal original-equation family-model AFE gives ADC equilibrium 1.503360 V, VMID 1.500596 V and 4.474 mA including the midpoint divider. Gain is 969.744 V/V at 1 kHz; sampled peak-relative -3 dB band is 316 Hz-6.88 kHz. Declared 100/10 GOhm capacitor insulation scenarios give 2.05/18.36 uV total ADC-baseline change over -100 to +100 mV input offset. Fast offset changes saturate later stages and produce about 8 mVpp in an unexcited channel through shared bias. Tested recovery reaches a quarter ideal LSB after 1.585 s; cold startup requires 2.336 s and fails that check at 2 s. Recommend a provisional 3 s startup blank plus whole-AFE validity checks; no universal delay is qualified. 50/60 Hz differential attenuation is only 15.7/14.1 dB versus 1 kHz. Power macros demonstrate clamp/cutoff, but transient peaks exceed the static 5.55 V clamp limit: tested CHG_IN peak 5.868 V, while the separately checked control-LDO input stays below 6 V in those fixtures. Raw RF nodes, upstream PACK+ branches, external AFE drive and LDO-failure rail OVP remain outside the demonstrated protection boundary. Invalid TPS25200 macro DC sweeps were rejected. See [analysis and model limits](../hardware/rev-a/ltspice/README.md).

**Risks and mitigation.** The input model gives about 3 MΩ at 7 kHz with no FFC and approximately 0.826 MΩ with the 20 pF FFC example, so it fails ≥10 MΩ. Proposed source-loading amplitude/phase limits remain pending user acceptance. Cable/source asymmetry can reduce CMRR substantially. Cell global sourcing, independent protection, actual usable capacity, nonlinear recovery, ADC/BLE continuity, RF match, footprint/FFC mapping and assembly cost remain open. All 80 BOM SKUs have verified LCSC inventory on 2026-10-02, but stock is not reserved and the assembly-service quote/eligibility is not established. The cell is the separately recorded procurement exception in D-020. The user authorized PCB creation on 2026-10-02; the linked native mainboard is a Candidate placement/routing artifact. No firmware or fabrication release is delivered.

**PCB and crosstalk evidence, 2026-10-02.** Following the user's explicit “make one” reply, the new native mainboard uses 80 × 74 mm provisional geometry and four copper layers with two internal ground planes. All 446 physical references have assigned footprints, including manufacturer-land custom patterns for the critical ICs/RF/FFC parts; the initial independent placement check matches 1,089 connected and 48 NC lands and finds no conservative courtyard overlap. The dimension is a Candidate and leaves D-008's smaller objective open. RF routing is held open because ST's MLPF reference ground/stack arrangement is not reproduced by a generic L2 microstrip; footprint geometry verification does not close that adaptation. Actual LTspice one-channel excitation confirms a shared-VMID path at −52.22 dB worst in 300 Hz–7 kHz, equivalent 2.449 µVpp for a 1 mVpp aggressor. An assumed 0.01 pF amplified-output-to-early-input coupling gives approximately 17.25 µVpp total equivalent. The proposed −60 dB review criterion is not accepted and is unmet. Preserve the tested 47 Ω / 4.7 µF canonical bias while evaluating a separately qualified quiet-bias/late-return arrangement; layout alone cannot eliminate the modeled path. Family macro-models omit intra-quad package coupling. See [SI evidence](../hardware/rev-a/signal-integrity/README.md) and [native PCB checks](../hardware/rev-a/pcb/README.md) for current routing, DRC and assembly gates.

**Verification / reopen when.** The final CAD export contains 446 physical components; 1,089 connected and 48 intentional-NC pins match the source tables, with zero KiCad 9.0.9 ERC findings. This is a transfer check, not a behavioral or manufacturing release. Close loading and cell-protection requirements, audit Altium connectivity/land patterns, qualify nonlinear behavior across hardware/PVT conditions, complete PCB DRC and bring-up measurements, then prove detection/noise/aliasing/CMRR, BLE capture, rails/interlock, RF and one-hour runtime. Reopen topology/clock/parts when these checks fail. Detailed files remain linked rather than duplicating their specification here.

### D-025 — Four-channel generator interface

**Choice and status.** Locked 2026-11-22. Use CH1–CH4 on four U.FL inputs, with the generator as the test source and BLE as the laptop link. The design omits physical threads. The earlier eight-channel DAC/FFC configuration remains a comparison fixture.
**Variant implementation.** The refreshed BOM uses STM32WBA52CEU6 in UFQFPN48 (512 KiB flash / 96 KiB SRAM), TLV9054IPWR in TSSOP-14, 910 kΩ feedback parts and a four-pad Johanson 2450AT18D0100001E antenna. These replace unavailable BOM items. Check the firmware memory map and retune the redesigned RF layout. [ST memory/package table](https://www.st.com/resource/en/application_note/an6159-migrating-from-the-stm32wba5xxx-to-the-stm32wba6xxx-mcus-stmicroelectronics.pdf).

**Objective and tradeoff.** Four real channels retain indexing, gain and crosstalk tests while removing four analog channels and their connector wiring. Shared REF remains inside the board. Terminate the four coax shields at board ground. Feed REF through a matched quiet-source path and retain its coupling capacitor and VMID bias.
**Verification and reopening.** Calibrate stimulus at the board and place the 47 kΩ emulator near the AFE. Exercise one channel, all four, and a quiet victim with three active neighbors. Meet the user-reconfirmed ≥10 MΩ magnitude from 300 Hz to 7 kHz at the protected AFE on all four channels. The final 910 kΩ-arm ADS fixture gives 2.962 MΩ at 7 kHz, 970.78 V/V at 1 kHz, a 1.50315 V ADC bias and −41.52 dB worst coherent coupling in its three-aggressor test. LTspice gives 3.467 µV RMS electronics noise over the band. The 99.82% voltage transfer with the local 47 kΩ resistor leaves the loading requirement open. See the [four-channel simulations](../hardware/rev-a/ads-closeout-2026-11-22/) and [impedance study](../hardware/rev-a/input-impedance/). Check ADC reference noise, protection and physical returns after routing.

### D-026 — Live charge status and independent signal testing

**Choice and status.** Locked test functions, 2026-11-22. The user will bring a generator-driven TX near the RX and read charging status over BLE. Keep recording disabled while charging. With the field off and receiver disconnected, the board must also record from a compatible externally charged pack or battery emulator. A lab LiPo is a candidate pending identification. D-023's historical 55 mAh pack and 20 mA / 4.1 V example do not set the limits for that pack.
**Objective and tradeoff.** Live status costs power and requires independent digital and analog power enables. In the candidate circuit, protected RUN and charge inputs diode-OR into the digital regulator. MCU VDDA remains powered with VDD. Open-drain status uses digital-domain pull-ups. Under a weak or failed input the radio may lose power. The laptop needs a stale/disconnected indication.
**Verification and reopening.** Exercise field arrival/removal, taper, faults, RF bursts and battery-only RUN with a current-limited emulator. Observe both rails, status pins and signed pack current. Confirm pack MPN, protection, connector polarity, current, CV and temperature limits before fitting charge links for a cell. Record pack identity, heat and usable runtime.

### D-027 — Single packaged receiver bridge and separate regulation

**Choice and status.** The user accepted a single packaged Schottky bridge with separate regulation on 2026-11-22. The engineering baseline is Infineon BAS4002ARPPE6327HTSA1 (C3589694) and TI TPS70950DBVR (C96028). Retain BQ25185 and the fixed Luo coil pair. Historical BAT54 runs remain simulation fixtures.
**Objective and tradeoff.** A self-starting bridge accepts a 13.56 MHz generator without a charging protocol. Two junction drops and a subsequent linear regulator consume headroom. Label the pre-regulator reservoir RECT_DC and the regulated receiver output WPT_RX_DC. The LDO controls its output; input fault stress and sustained heating are separate checks. [Infineon](https://www.infineon.com/part/BAS4002A-RPP) · [TI](https://www.ti.com/lit/ds/symlink/tps709.pdf).
**Verification and reopening.** Check matching and delivered power under charger and radio demand. Sweep coupling, tuning, light load and weak field. Measure reverse stress, capacitor currents, temperature, input transients and available generator power. Select final trim values after testing the assembled coils at the intended spacing and metal clearances. See the [builder handoff](BUILD-NEXT.txt) for data and release gates.

### D-028 — Lower-capacitance input stages and quiet bias return

**Choice and status.** Engineering Candidate, recorded 2026-11-22. The user kept the ≥10 MΩ magnitude requirement for all four inputs over 300 Hz–7 kHz. Recommend five MAX44280AXT+T gain-11 stages for CH1–4 and REF. Return their five 22 MΩ bias resistors to the bypassed VMID_RAW divider. Retain the 47 Ω isolator on the shared VMID follower. The separate low-capacitance native design is the proposed layout starting point.

**Objective and alternatives.** Reduce AC input current while preserving DC rejection, the useful signal gain and the 6 µV RMS electronics noise objective. The existing TLV input loads the generator with 2.96 MΩ at 7 kHz. Sub-picofarad positive feedback can recover impedance at that frequency while still failing elsewhere and introducing negative input conductance. A lower-capacitance amplifier and a quieter bias return address the two observed causes independently. [Candidate comparison](../hardware/rev-a/input-impedance/README.md) · [ADI datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX44280.pdf)

**Evidence and tradeoffs.** With 0.60 pF added board capacitance, −1% bias resistance, 0.65 pF ESD and 0.20 pF above modeled amplifier capacitance, the independently excited inputs present at least 10.70 MΩ in ADS and LTspice. At 0.75 pF the minimum is 10.08 MΩ, and at 1.00 pF it falls to 9.16 MΩ. LTspice gives 2.983 µV RMS electronics noise, 4.400 µV RMS including the emulator, approximately 971 V/V at 1 kHz and 6.016 mA modeled analog-rail draw versus 2.432 mA for the TLV input configuration. Ten units of C2058813 were available for five locations per PCB. [Vendor-model runs](../hardware/rev-a/input-impedance/max44280/) · [ADS corroboration](../hardware/rev-a/input-impedance/ads-low-c/)

**Verification and reopening.** Keep the protection and high-impedance nodes close to each amplifier. Extract layout capacitance, include test lands, and measure the protected input plane without a shunting scope probe. Check all four channels across the whole band, the reference path, hot-plug recovery, noise, crosstalk, enabled current, rail stability and ADC/BLE continuity. Reopen placement or the input network if the measured minimum misses 10 MΩ or margins are inadequate. [Editable implementation and layout gates](../hardware/rev-a/bench-four-coax-low-c/README.md)

## 4. Open work and next design sequence

The current release sequence is in [BUILD-NEXT.txt](BUILD-NEXT.txt). The following earlier engineering tasks remain applicable where their interfaces agree with D-025 through D-027.

| Order | Work item | Required outcome before selection |
|---|---|---|
| 1 | Analog supply, detector interface, STM32WBA52 feasibility | Comparator common-mode/output compatibility, threshold range, event GPIO/timing resources, and rail options |
| 2 | Detector accuracy and required swing | Input-referred offset/noise, threshold accuracy, hysteresis, and minimum detectable excursion |
| 3 | Total gain and gain distribution | Per-stage signal/noise/headroom budget spanning 20 µVpp to 1 mVpp and offset/LFP/artifact cases |
| 4 | Input and shared REF topology | DC paths, biasing, connector ESD/fault protection, leakage and capacitance, impedance across frequency, common-mode rejection, startup/recovery; [reference audit](design/2026-09-22-egra-meower-reference-audit.md) |
| 5 | Filters and detection | HP/LP topology/order; 5/7/10 kHz comparison; peak retention, noise, ringing, and chatter |
| 6 | Amplifier and comparator selection | Noise, current noise, bias, input/output range, GBW/stability, power, package, and availability comparison |
| 7 | Simulation and detection evaluation | Realistic spikes plus noise/LFP/offsets; peak retention, recovery, misses, false positives, and component tolerance effects |
| 8 | Exclusive-mode power path and runtime | Supported WPT-present detector envelope/latency, cell protection separate from charging, NTC and charge limits, switch backfeed/short/inrush behavior, rail sequencing, 1S discharge-to-3.0 V LDO dropout and one-hour usable-capacity budget; [review](design/2026-09-22-power-path-architecture-review.md) |
| 9 | WPT and mechanical integration | Build on [actual nominal ADS receiver evidence](../hardware/wpt/ads/README.md), replace resistor fixtures with charge-state/protection demand, and retune practical values across tolerances/coupling. Resolve demonstrated 11.9 V near-open-load behavior, RX heating and TX-capacitor stress; reopen HFSS after material physical changes. Assess RF floorplan/stacking and tuning/test access without a VNA |
| 10 | Qualify D-023 power baseline | Verify Taisko 55 mAh sourcing/pack, BQ25185 20 mA and provisional 4.1 V settings, receiver power and bridge stress, temperature/CV/timer behavior, independent protection and PMOS interlock; power architecture accepted, hardware incomplete |
| Current candidate | Rev A schematic and PCB / D-024 | Review ADC recommendation; resolve input loading, shared VMID and package/PCB crosstalk, compatible cell protection and RF ground/stack adaptation; close routed DRC/connectivity and assembly/FFC gates; qualify ADC/BLE continuity and actual power before adoption/release |

The proposal fails the existing ≥10 MΩ input-impedance target at 7 kHz due to input capacitance even before FFC loading. Fix this design problem or explicitly reopen the requirement before fabrication. Input ESD and fault protection remain candidates, not qualified provisions. The event-capture implementation, detector thresholds/refractory behavior, count width, BLE packet format, host interfaces, exact FFC part, antenna match, and acceptance limits remain open. Define them when their governing constraints are available.

### Schedule and available equipment recovered from GitHub

The 2026-09-18 repository notes used **2026-10-18 as a working planning deadline**. On 2026-09-21 the user explicitly removed the hard deadline and prioritized a defensible design. Retain the old schedule only as historical context.

Those notes also report access to extensive lab equipment and ownership of an STM32 ST-LINK. A suitable STM32 development board was unconfirmed. Exact instrument inventory, budget, and ADS/HFSS access remain unresolved. These are historical project-context statements, not a fresh inventory check.

## 5. Verification record

**Fresh ADS verification, 2026-11-22:** The [fixed-coil review](../hardware/wpt/ads/review-2026-11-22/README.md) records completed passive S-parameters, 48 nonlinear authored-load HB cases, a DC load-law check and translated original-equation AFE DC/AC. It preserves rejected/out-of-domain diagnostics and all decks/datasets/logs. Physical coils, actual charging, noise, transients, extracted PCB returns and hardware remain unqualified. All 252 added AFE DC paths are internal vendor-macro nodes; none is an external CuraLink node. A lower-GMIN initialization timed out, so do not claim that sensitivity is qualified. Source/netlist consistency and the existing input-loading/shared-bias gates are linked under D-024.

**Actual ADS receiver verification, 2026-10-09:** [Native copied-cell simulation](../hardware/wpt/ads/receiver-fixture-2026-10-09/runs/native_BAT54_candidate_validation/metrics.json) verifies a 5.08853 V / 124.287 mW resistor-load point, positive probe power signs and large-signal impedances. [Standalone decks/results](../hardware/wpt/ads/receiver-fixture-2026-10-09/README.md) record the old diode's reverse-bound failure, finite Candidate matching search, order convergence, near-open-load 11.915 V / 132 mW RX winding loss, and loaded capacitor/diode pulse stress. Nominal constant-R/L/k coils, ideal capacitors and manufacturer diode fit do not establish PCB RF parasitics, charging, temperature, tolerance margin or safe raw regulation. No hardware measurement was made.

No hardware measurements are recorded. An initial [linear AFE model and limited synthetic detector trial](calculations/afe-study/report.md) were completed on 2026-09-21. Their assumptions and limitations prevent treating them as hardware verification. The sampled software detector trial does not validate the new analog comparator architecture; ADC-specific results are historical. The revised [analog-event linear model](calculations/analog-event-afe/results.json), using candidate 5.1 kΩ CH/REF series protection and 0.5 pF typical connector ESD capacitance, predicts approximately 944.2 V/V at 1 kHz, 1.92 µV RMS electronics noise and 3.72 µV RMS electronics-plus-source noise over 300 Hz–7 kHz. These are calculations, not measurements; the model omits comparator, cable, leakage, layout, VMID, overload and measured device behavior. The following are planned evidence categories; they are not passed tests.

| Area | Evidence required |
|---|---|
| Analog | Gain and corners; input impedance versus frequency including FFC; noise spectra and integrated input-referred noise; channel matching; crosstalk; saturation and recovery |
| Input protection | Connector ESD/fault pulse behavior, DC leakage, series-resistor pulse stress, unpowered input injection, FFC hot-plug recovery, and matched CH/REF parasitics |
| Stimulus fixture | Attached-output calibration, source resistance, DAC/reconstruction noise, common and quiet channel behavior, cable parasitics, connector orientation |
| Acquisition | Event pulse capture, simultaneous channels, missed pulses during BLE activity, timing, CPU load, and detector/capture power |
| Detection | Measured positive/negative trip and release thresholds, comparator error/noise/hysteresis, labeled waveform misses/false positives/duplicates, refractory behavior, and bin boundaries |
| Telemetry | Peak/average current, packet loss, latency, range, configuration, and event diagnostic limits |
| Power and WPT | One-hour battery runtime and LDO dropout margin across discharge; charge current/termination/thermal limits; published coil-model provenance; ADS load/coupling/tolerance sweeps of WPT_RAW, delivered DC power and RF-to-DC efficiency with explicit port boundary; end-to-end DC tests across tuning/load/alignment. HFSS artifacts are required only if D-018 physical conditions change; no VNA validation is planned under D-019 |
| Mode isolation | WPT application/removal, charge-complete-with-field-present, weak/intermittent coupling, battery undervoltage and rapid cycling; verify main rails/AFE/BLE off in CHARGE and automatic valid RUN |
| Interference | Comparable recordings in battery RUN with BLE off/on; measure WPT field, rectifier and charger coupling during CHARGE only to confirm system isolation |

For every future result, retain the date, hardware/firmware revision, schematic/configuration, stimulus, instruments/settings, bandwidth, procedure, raw-data location, uncertainty or limitations, and applicable acceptance criterion. Separate predictions from observations.

## 6. Evidence and references

**S-001 — User-supplied CuraLink handoff**, imported 2026-09-21. Archived verbatim at [references/2026-09-21-project-handoff.txt](references/2026-09-21-project-handoff.txt). This is a record of prior project intent and rationale, not independent experimental evidence.

**S-002 — Existing GitHub project record**, inspected 2026-09-21: [AngeloWhey/CuraLink](https://github.com/AngeloWhey/CuraLink), default branch `main`, at commit [`54fe0ca`](https://github.com/AngeloWhey/CuraLink/commit/54fe0ca0efbffd01c9e530dc9e83d9c6c300244a), dated 2026-09-18. The repository contains a project brief, requirements, planning notes, a passive-fixture note, the original neural-input specification, and an engineering review under `outputs/`. These establish earlier documented states; their commit dates do not establish the original dates of every decision.

**S-003 — EGRA hardware checkpoint**, inspected 2026-09-22: [specified KiCad PCB at commit `b915129`](https://github.com/zanebeeai/egra-og/blob/b915129b144de0e52f8daf5e31ab55e3a1aaabc2/egra-OG_1.before-routeplan-20260601_181915.kicad_pcb), its [HD-EMG schematic](https://github.com/zanebeeai/egra-og/blob/b915129b144de0e52f8daf5e31ab55e3a1aaabc2/HD-EMG-interface.kicad_sch), and [Comms schematic](https://github.com/zanebeeai/egra-og/blob/b915129b144de0e52f8daf5e31ab55e3a1aaabc2/Comms.kicad_sch). Exact component/net findings and transfer limits are in the [source audit](design/2026-09-22-egra-meower-reference-audit.md).

**S-004 — Meower hardware**, inspected 2026-09-22: [hardware README at commit `c6f4102`](https://github.com/nikki-uwu/Meower/blob/c6f410268a16cf4e0ecb313ea7b957a4a2afa690/hardware/README.md) and [active-electrode test note](https://github.com/nikki-uwu/Meower/blob/c6f410268a16cf4e0ecb313ea7b957a4a2afa690/hardware/Active_electrodes_testing_2025_10_17.md). Used for measurement access and test-method ideas; its EEG values are not CuraLink requirements.

**S-005 — User-supplied power-architecture decision summary**, received and recorded 2026-09-22. This explicitly selects exclusive CHARGE/RUN, a 1S rechargeable cell, hardware system isolation, separate nominal 3.0 V analog/digital rails, and a conditional DC-linked RX-board partition. It is project intent, not a measured charger, WPT, battery or rail result.

**S-006 — User DEC-WPT-002**, received and recorded 2026-09-22. Selects the HFSS → `.s2p` → ADS WPT study, with a 13.56 MHz physical coil-pair starting model, initial resistive DC load and delivered DC power/RF-to-DC efficiency as primary metrics. This is a simulation plan, not a performance result or final frequency selection. Tool capability cross-checked against [Ansys Touchstone export](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v251/en/Subsystems/HFSS/Subsystems/HFSS%20Scripting/Content/ExportNetworkDataPlanarEM.htm?TocPath=Design+Object+Script+Commands%7C_____46) and [Keysight nonlinear-rectifier co-simulation example](https://www.keysight.com/in/en/assets/7018-05801/case-studies/5992-2395.pdf).

**S-007 — User DEC-WPT-003 and Luo et al. coil paper**, received, checked and recorded 2026-09-22. Selects reuse of the published 13.56 MHz 40 mm TX / 10 mm RX planar pair for Rev A, ADS startup from measured L/R/k, new CuraLink-specific matching and VNA verification; it requires reopening HFSS after material physical changes. Paper geometry, measured coil parameters and the matched 50 Ω `S21` basis of the approximately 70% result were verified in the [open-access publication](https://pmc.ncbi.nlm.nih.gov/articles/PMC10302922/). This is a selected design shortcut and literature result, not CuraLink simulation or measurement.

**S-008 — User no-VNA constraint**, received and recorded 2026-09-22. States that CuraLink has no VNA access and cannot obtain one, and directs the design to trust the published coil work and perform CuraLink-specific rectifier/charger impedance transformation. This supersedes D-018's VNA verification gate but does not convert the literature's 70% result into a CuraLink measurement.

### Reconciliation with the older repository

The 2026-09-21 handoff superseded conflicting 2026-09-18 documents; the explicit 2026-09-22 user corrections now supersede its ADC acquisition and AWG source direction through D-012 and D-014. Preserve the older documents as historical references rather than silently treating them as current requirements.

| Topic | GitHub record on 2026-09-18 | Historical 2026-09-21 handoff baseline | Current record |
|---|---|---|---|
| Detection | Analog threshold/hysteresis events; ADC optional for debug | Internal ADC + DMA and software detection | D-012 selects analog detection with STM32WBA52 ADC unused; D-004 superseded |
| Telemetry | Ultrasonic backscatter | BLE | D-006/D-013: STM32WBA52 with ceramic antenna |
| Power | Continuous inductive supply for operation | Exclusive WPT CHARGE/system OFF and battery RUN; no simultaneous charge-and-record | D-007, D-016 |
| Nominal signal band | 300 Hz–6 kHz | Approximately 300 Hz–7 kHz, with corner comparison still required | D-003 |
| Electronics noise | ≤5 µV RMS goal, with ≤3 µV RMS preferred in the review | ≤6 µV RMS objective over approximately 300 Hz–7 kHz | D-003 |
| Binning and packets | 20 ms, 16-bit counts, and a 30-byte packet proposed in planning | 25 ms configurable reference; count width and packet format open | D-005 |
| Stimulus | Passive AWG fixture | One AWG and passive fanout | D-014: USB/DAC fixture with one waveform split eight ways; D-009 source superseded |

The older review also repeats the incomplete fixture-loading model that treats the eight series source resistors as shunt loads. D-009 records the correction; archival status does not make that calculation authoritative.

At the time of inspection, this local workspace had no configured Git remote and no commits. The handbook and project instructions were local, uncommitted files; they had not been published to GitHub. The remote `AGENTS.md` still described the older architecture. Any future repository integration must reconcile those instructions and preserve the existing `outputs/` references.

Historical sources: [requirements](https://github.com/AngeloWhey/CuraLink/blob/54fe0ca0efbffd01c9e530dc9e83d9c6c300244a/outputs/CuraLink-requirements-v0.1.md), [planning](https://github.com/AngeloWhey/CuraLink/blob/54fe0ca0efbffd01c9e530dc9e83d9c6c300244a/outputs/CuraLink-planning-v0.1.md), and [neural input review](https://github.com/AngeloWhey/CuraLink/blob/54fe0ca0efbffd01c9e530dc9e83d9c6c300244a/outputs/CuraLink-neural-input-signal-spec-review-v0.1.md).

The handoff references Neuralink's 2019 hardware publication, work attributed to Xilin Liu, and Neuropixels/AP-band conventions. Bibliographic details and exact operating conditions must be verified before using their numbers to finalize a new choice. In particular, integrated noise numbers measured over different bandwidths are not directly equivalent performance specifications.

When external evidence is added, link the primary paper or manufacturer document and record the relevant section, device variant, revision/date, and measurement conditions. Avoid copying unverified research comparisons into requirements.

## 7. Maintenance and decision format

Update this record during normal project work when a significant decision is accepted or a result changes the design. This is an ongoing project workflow, not a scheduled background process. Routine questions, unselected part ideas, and implementation details do not need new decision entries.

For each new decision use:

```text
D-### — Descriptive decision title
Decision date: YYYY-MM-DD (or unknown for historical imports)
Recorded: YYYY-MM-DD | Last revised: YYYY-MM-DD
Status: Locked / Baseline / Objective / Candidate / Open / Superseded

Choice: What is selected, and what remains open?
Objective: Which functional objectives and constraints drive it?
Evidence: Sources, calculations, assumptions, and uncertainty.
Alternatives and tradeoffs: Real candidates and why they won/lost.
Rationale: Why this choice best serves the stated objectives.
Risks and mitigation: Consequences and practical controls.
Verification / reopen when: How to test it and what would change it.
```

Scale detail to consequence. Update Section 2 whenever a current value changes. Keep decision IDs stable and link supporting derivations rather than expanding every entry into a lab notebook. Preserve the prior choice and reason for replacement when superseding a decision.

### Revision history

| Recorded date | Change | Basis |
|---|---|---|
| 2026-09-21 | Created v0.1; imported D-001 through D-009; separated locked scope, working baselines, objectives, and open work | User requested a dated, maintained engineering handbook; source S-001 |
| 2026-09-21 | Flagged fixture-loading and common-stimulus crosstalk limitations for design review | Complete-circuit reasoning; does not change the selected passive-fixture strategy |
| 2026-09-21 | Compared existing GitHub documentation with the newer handoff; recorded superseded architecture/values and recovered schedule/equipment context | User requested GitHub inspection; source S-002; no remote files changed |
| 2026-09-21 | Added D-010/D-011: under-US$150 budget, one-hour runtime target, no hard deadline, reopened MCU/ADC choice, and gain/parts-only current scope | Explicit user instructions; provisional calculations and parts linked separately |
| 2026-09-22 | Added D-012; removed waveform ADC from current architecture and verification plan; withdrew ADC-based gain justification and MCU ranking; marked prior studies historical | Explicit user correction; comparator design and gain remain open |
| 2026-09-22 | Added D-013/D-014: selected STM32WBA52 with unused ADC, ceramic antenna, and separate one-DAC/eight-branch fixture; superseded brief EM9304 selection and AWG source. Linked new AFE/fixture calculation; flagged unmet input impedance and low-amplitude threshold margin | Explicit user choices, primary manufacturer references, and candidate linear model |
| 2026-09-22 | Added D-015 and the EGRA/Meower source audit; ruled out copying EGRA's electrode shunt; proposed matched low-C ESD, current limiting and AC coupling for CH/REF. Revised candidate linear model to include 5.1 kΩ and 0.5 pF; retained unmet input-impedance and protection-qualification gates | User-selected reference workflow, inspected KiCad nets, manufacturer data and recalculation |
| 2026-09-22 | Revised D-007 to lock mutually exclusive CHARGE and RUN, superseding secondary charge-and-run; added D-016 for 1S charging, hardware battery isolation, split rails and conditional DC-linked coil-board partition. Flagged WPT detection and 3.0 V LDO dropout as release gates | User power-architecture summary S-005; no parts or measurements finalized |
| 2026-09-22 | Linked a power-path architecture review; expanded open gates for WPT voltage regulation/envelope, independent cell protection, charger temperature/current limits, mode-detector latency, backfeed, inrush and sequencing. No new design selection | Requested practical protection review; manufacturer documentation and circuit reasoning |
| 2026-09-22 | Added D-017 (user alias DEC-WPT-002) for HFSS → S2P → ADS WPT simulation and DC-power/efficiency evaluation; linked a proposed functional-block power design without finalizing parts, coil geometry or operating frequency | Explicit user method decision S-006 and request to design today's power functions; Ansys/Keysight documentation |
| 2026-09-22 | Added D-018 / DEC-WPT-003 selecting the published 13.56 MHz 40 mm TX / 10 mm RX planar pair for Rev A; revised D-017 to start ADS from measured L/R/k and reserve HFSS for material physical changes. Kept the paper's 70% RF-link result separate from CuraLink RF-to-DC performance | Explicit user decision S-007; published geometry and measurements verified in Luo et al. |
| 2026-09-22 | Verified that no public repository or supplementary Touchstone file is linked or discoverable for the Luo et al. paper; added a concrete ADS mutual-inductor setup and retained fabricated-coil VNA measurement as the source of final broadband `.s2p` data | Paper data-availability/full-text record, public repository search and Keysight Mutual component documentation |
| 2026-09-22 | Added D-019: proceed without VNA, trust the published nominal coil model, transform the nonlinear rectifier/charger load in ADS, provide tuning options and verify delivered DC behavior. Superseded the earlier VNA gate without claiming independent coil validation | Explicit user constraint S-008 |
| 2026-09-22 | Generated a clearly labeled nominal 50 ohm `.s2p` from the paper's L/R/k values for ADS linear checks; added an accepted-TX-power/load sweep and battery-selection equation. Kept nonlinear rectifier work on the explicit R-L-M model and did not represent the file as measured | User request; reproducible coupled-inductor calculation with reciprocity/passivity checks |
| 2026-09-22 | Added BAT15-03W as a provisional ADS diode model seed, not a hardware selection; flagged its 4 V reverse rating and model/package uncertainty for harmonic-balance stress checks | User-requested changeable part candidate; Infineon datasheet and public SPICE parameter sets |
| 2026-09-24 | Added a non-selected BQ25100/BQ25185 charger comparison, compact protected 100 mAh cell candidate, datasheet-derived CC/CV starting values, and separate-timescale ADS model guidance; retained cell discharge, NTC, input clamp, 3.0 V LDO dropout and assembly capability as open gates | User requested compact 1S cell/charger with OVP and an ADS model; TI and Adafruit primary product/datasheet sources; no design acceptance inferred |
| 2026-09-24 | Added D-020: require future PCB electronic BOM selections to be LCSC-orderable and verify exact package and pick-and-place eligibility at selection/BOM release | Explicit user manufacturing constraint; no technical parts selected in this update |
| 2026-09-24 | Added D-021 selecting BQ25185DLHR (LCSC C19725033) as the 1S charger IC; revised current design summary, D-016 and charger open work. Documented a 40 mA CC / 100 mA input-limit ADS starting case, separated RF rectifier loading from slow CC/CV battery behavior, and retained cell, receiver OVP and SYS isolation as open verification gates | Explicit user selection; TI BQ25185 Rev. B datasheet and LCSC listing; configuration values remain provisional |
| 2026-09-24 | Recorded the user's report that the published lumped coil model with two matching networks and terminal ports reproduces the paper's matching effects; kept quantitative performance and rectifier/DC charging results open pending saved ADS setup and numeric results | User-reported ADS progress; no deck or plots independently reviewed |
| 2026-09-24 | Recorded preliminary 40 mA current-sink transient plot showing `DOut=-0.513 V` at 68.8 µs; flagged as unresolved rather than charging evidence and added the RF-to-DC power budget check for a possible 10 dBm source | User-supplied plot; ADS model interpretation and current source setting require confirmation |
| 2026-09-24 | Added D-022 for the user-nominated PGEB201212 cell; found a charge-current conflict with BQ25185's 5 mA minimum versus a retailer-listed 1.6 mA recommendation, no reported protection, inconsistent discharge data and inadequate capacity for the one-hour current estimate. Superseded the earlier 40 mA cell-load starting assumption and updated conditional ADS cases | User-provided intended part; retailer listing and TI BQ25185 datasheet; exact PGEB manufacturer specification unavailable |
| 2026-09-24 | Corrected recommended-versus-maximum charge-rate and ambiguous PGEB discharge interpretation; documented BQ25185 input overhead/six-hour timer and bridge grounding concern; compared 55/100 mAh cells and LCSC chargers, with PMOS OFF-during-WPT interlock proposal | User requested alternatives and a PMOS mode switch; manufacturer specifications and screenshot inspection. Existing charger retained; alternatives, exact cell, current and detector remain unselected |
| 2026-09-25 | Recorded that TX source power may increase beyond the previous 10 dBm simulation setting; retained cell/charger and receiver-stress qualification gates | Explicit user clarification; no higher-power hardware capability or DC result measured |
| 2026-09-25 | Added D-023 accepting the 55 mAh working cell, provisional 20 mA / 4.1 V charging, 5 V / 21 mA DC target and RF power sweep; superseded PGEB working choice and resumed AFE. Clarified 18.5 V OVP, internal-path 3.13 A OCP and coupled 4.1 V/ILIM settings | Explicit user acceptance and request; TI Rev B protections and configuration table. Power validation remains open |
| 2026-10-01 | Reviewed external WBA55 ADC/software-detection proposal as Candidate; verified WBA52/WBA55 SMPS distinction and ADC capability; flagged BLE calibration sharing the ADC, driver/settling, alias rejection and whole-system power gates. Retained D-012/D-013 and existing AFE requirements | User-requested evaluation; ST DS14127 Rev. 10 and official STM32CubeWBA source. No replacement architecture or parts accepted |
| 2026-10-01 | Added D-024 and Rev A schematic/BOM: recommend WBA52 ADC, mixed quad amplifiers and modeled 150 Ω / 470 pF interface; record gain/noise/current, CAD pin/ERC pass, explicit failed nonlinear-model diagnostics, stock/tolerance substitutions and power sequencing/interlock circuit. Retain unmet input target and unqualified independent cell protection; raise candidate board-input power allocation to ≥120 mW | User authorized full schematic and ADC/comparator recommendation; manufacturer evidence, reproducible calculations and actual KiCad export. Candidate choices are not accepted requirements or fabrication release |
| 2026-10-02 | Reaffirmed D-020; live-audited all 81 Rev A BOM SKUs plus cell/cable, added exact stock/MOQ/date to BOM and saved primary response evidence. All BOM parts and cable are stocked for one board; accepted cell global catalog entry is unavailable. Retained cell baseline with sourcing/protection gate and recorded US$103.65 minimum-order purchase subtotal, excluding manufacture/logistics | Explicit user stock requirement; LCSC public product-detail responses and independent exact-code search. No component substitution, purchase, architecture acceptance or fabrication release |
| 2026-10-02 | Corrected U502/U511 TPS25200 physical pin maps and added exact-pin CAD invariants; superseded the previous eFuse symbol/pin-table handoff. Started actual LTspice DC/AC/protection verification | User requested LTspice analysis and OVP/DC-rejection checks; independently verified TI Rev F Table 4-1 revealed a source-map error that transfer/ERC alone cannot detect |
| 2026-10-02 | Completed real LTspice DC/AC and offset/startup analyses using original-equation TI family models; recorded DC rejection with capacitor insulation scenarios, 970 V/V gain, shared saturation artifacts and failure of the 2 s startup check. Added a Candidate 3 s startup blank with validity checks. Corrected SS14 numbering and changed R511 to stocked 1 MOhm +/-1%; refreshed CAD/ERC, 80-SKU BOM and US$103.55 purchase subtotal | User requested component DC/frequency/protection analysis. Simulation and independent manufacturer audit replace invalid adapter conclusions and incorrect source pin maps; tested eFuse OVP remains bounded, and cell/receiver/loading/PCB gates stay open |

| 2026-10-02 | Created user-authorized candidate native mainboard, 80 × 74 mm with four layers/two internal grounds; assigned all 446 physical footprints and checked manufacturer lands, exact connected/NC pad transfer, outline and initial non-overlapping placement. Added actual LTspice crosstalk and declared parasitic/ripple sensitivities; identified shared VMID coupling at −52.22 dB and severe late-output-to-input sensitivity. Retained bias, size objective and ADC Candidate status; RF ground adaptation and fabrication gates remain open | User asked for SI/crosstalk review and explicitly replied “make one”; native CAD and original-equation TI-family model evidence. Geometry and nominal models do not qualify hardware, aggregate crosstalk or assembly |
| 2026-10-02 | Corrected schematic object identity namespaces after an independent native audit found unit/pin UUID collisions; separated symbol and per-unit pin IDs, regenerated the netlist and linked PCB footprints through the root/sheet/symbol path. Electrical values and connectivity remain unchanged | ERC/pin transfer did not detect identity collisions; correct native links are required for reliable schematic-to-PCB updates |
| 2026-10-09 | Audited actual restart state: native CAD remains KiCad; Altium conversion, signal routing, plane fill, schematic-to-PCB relinking and merged placement corrections are incomplete. Recorded completed bias AC alternatives and rejected empty/incomplete startup evidence; retained R1149 = 47 Ω and Candidate status. Flagged older PDF/ZIP and 2026-10-02 inventory as historical snapshots | User requested restart status and test priorities; saved-file inspection corrected overly broad workflow/completion wording without changing circuit values or accepted requirements |
| 2026-10-09 | Recovered the actual ADS WPT workspace path and distinguished its two coil schematics from earlier Curalink-named scratch workspaces. Created hash/CRC-verified recovery ZIPs; verified old paths absent with Recycle Bin entries, preserving the early AFE/MOSFET work and the real workspace | User requested workspace identification and deletion of misleading workspaces; saved netlist/OA/library evidence identifies the working folder. No circuit acceptance, model edits or new performance claim |
| 2026-10-09 | Added v1.17: corrected floating RX only in new native ADS test cells and verified original OA preservation. Ran actual HB load/power and finite joint-capacitor studies; recorded a 5.08853 V / 124.287 mW BAT54 Candidate point, native impedance/probe verification and harmonic convergence. Rejected the old diode's reverse-bound failure; quantified 11.915 V / 132 mW RX winding loss near no load and corrected external-control loading to 108.7/119.8 mW declared fixtures. Saved a third authored SDD load cell and standalone decks; their electrical checks remain unsolved after two license-limit failures | User requested ADS matching and remaining power work. Genuine manufacturer model, dated LCSC stock and saved ADS datasets/logs support simulation findings; raw OVP, real charging, cell protection/sourcing, thermal/tolerance and mode/runtime qualification remain open. No hardware part or tuning acceptance inferred |
| 2026-11-22 | Added v1.18 migration entry points and full context README; consolidated mainboard/ADS/source evidence from both project folders, preserved unique captures and historical references, added Git LFS dataset restoration and portable runner-path configuration | User requested GitHub publication for moving computers. File/hash/dependency checks qualify the saved-file transfer only; design status, prior test dates, unqualified charger/cell/PCB gates and source provenance are retained |
| 2026-11-22 | Added v1.19: user reaffirmed fixed published coils; fresh ADS passive check gives 71.873% / RX 2.380 − j28.078 Ω, new resistor point reproduces 124.296 mW, and authored-load DC plus 48 HB cases expose missing raw regulation. Translated AFE DC/AC and source/return checks reproduce nominal bias/gain, shared-bias coupling and failed input impedance. Preserve rejected first AC diagnostic and model-port/noise limits | User requested ADS power/signal verification before build-out and proposed a buffer. Coils and hardware values are unchanged; a buffer is not selected. Build gates remain open; a verified fresh GitHub/LFS recovery covers the separate migration batch |
| 2026-11-22 | v1.20 adopts four on-board coax inputs, packaged rectifier, BLE charge telemetry and the externally charged pack fallback. Retains ≥10 MΩ across 300 Hz–7 kHz as a release requirement. Earlier eight-channel and all-off configurations are historical. | User changed the bench test interface and operating modes. Hardware release requires identified cell, board measurements and verified routing. |
| 2026-11-22 | v1.21 records the full-band high-impedance recommendation, separate native schematic, ADS/LTspice stress results and remaining physical limits. | The user retained ≥10 MΩ. The original input fails, while the low-capacitance candidate passes only within a quantified layout budget. |

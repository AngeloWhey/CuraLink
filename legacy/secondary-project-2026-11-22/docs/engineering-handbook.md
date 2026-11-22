# CuraLink Engineering Handbook

**Current design record · Created 2026-09-21 · Last updated 2026-09-22**  
Dates use America/New_York. Version: 1.1 — derived ADS coil model and power-feasibility sweep.

**Latest update, 2026-09-22:** CHARGE and RUN are mutually exclusive. The working power path is a 1S rechargeable cell, hardware-controlled battery-to-system isolation, and separate approximately 3.0 V analog/digital LDO rails. For Rev A, reuse the experimentally validated 13.56 MHz Luo et al. square planar pair: 40 mm TX, 10 mm RX and 10 mm nominal coaxial separation. Start circuit design in ADS with the published measured L/R/k coupled-inductor model; do not re-optimize in HFSS or copy the paper's 50 Ω matching network. No public source `.s2p` or supplementary repository was found, and CuraLink will not have VNA access. The design therefore relies on the published nominal parameters, tolerance/coupling sweeps, replaceable tuning components and end-to-end rectified-DC tests; this cannot independently verify coil Q, k or S-parameters. Reopen HFSS if geometry, materials, separation or nearby structures change materially. Delivered DC power and defined RF-to-DC efficiency govern the CuraLink comparison; the paper's approximately 70% result is matched RF coil-link efficiency, not rectified charging efficiency. See the [functional power-block design](design/2026-09-22-power-functional-blocks.md), [simulation method](design/2026-09-22-wpt-simulation-method.md), [ADS setup](design/2026-09-22-ads-wpt-model-setup.md) and [rectifier comparison](design/2026-09-22-rectifier-options.md). Exact rectifier/charger parts, CuraLink WPT power, WPT detection limits, RX-board partition and ≥10 MΩ AFE input-impedance resolution remain open.

**ADS check, 2026-09-22:** The user-provided `data/daa.csv` is an ADS S11 sweep. Assuming a 50 Ω port reference at the TX input, its rounded value near 13.56 MHz (`|S11|≈0.977∠26.47°`) implies `Zin≈11.1+j212 Ω` and only about 4.5% incident power accepted at that plane. This is simulated, not measured, and confirms the current TX input is not matched to 50 Ω. Provenance/configuration should be confirmed before comparing it with transient waveforms; add and optimize TX matching before interpreting source-to-load power. Supporting calculation and caveats are in the [ADS setup note](design/2026-09-22-ads-wpt-model-setup.md#user-ads-export-tx-input-s11).

This handbook explains what CuraLink is intended to do, which important decisions have been made, why they were made, and what remains to be demonstrated. It is the central engineering record for a new engineer joining the project.

The initial entries were imported from the user's project handoff on **2026-09-21**. Their original decision dates were not supplied. Recording a decision here does not imply it was made that day, independently verified, simulated, or measured.

## 1. Purpose and governing objectives

CuraLink is a compact, eight-channel **benchtop** prototype reproducing electrical and architectural challenges of intracortical extracellular neural acquisition. It is not intended for human or animal implantation. Its normal output is per-channel spike counts, with analog test access for waveform debugging and characterization using external instruments.

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
Laptop → USB/DAC fixture → one attenuated waveform → eight 47 kΩ branches
    → FFC (CH1–CH8, REF, grounds)
    → matched CH/REF connector ESD, current limiting, high-impedance AFE with DC rejection
    → gain and nominal 300 Hz–7 kHz conditioning
    → analog thresholds/comparators → per-channel event signals
    → STM32WBA52 event capture and refractory/rearm handling (ADC unused)
    → configurable spike-count bins → BLE → ceramic chip antenna → Python host

Wireless power transmitter → RX coil/tuning/rectifier/reservoir/protection
    → WPT_RAW (~5 V target) → 1S charger → battery
                        └→ WPT_PRESENT detector → hardware system disable
Battery → high-side isolation switch → SYS_RAW
    → separate ~3.0 V analog and digital LDOs → AFE + MCU/BLE

CHARGE: WPT present, charger enabled, main system OFF.
RUN: WPT absent, battery powers main system, charger inactive.
Charging complete while WPT remains present does not start RUN.
```

The USB/DAC fixture is a separate bench board; its DAC does not digitize neural signals on CuraLink. This is a functional diagram, not a finalized circuit. Stages may combine functions. The REF topology and its relation to circuit ground and bias remain open.

### Requirements and working values

| Item | Current value or approach | Status / qualification | Record |
|---|---|---|---|
| Channels | 8 recording channels + shared reference | Locked | D-001 |
| Modality | Intracortical extracellular-like acquisition | Locked; electrical bench model | D-001 |
| Spike amplitude | 200 µVpp nominal; 100–300 µVpp primary region | Locked input baseline | D-002 |
| Characterization envelope | 50–500 µVpp; approximately 0.5–2 ms | Locked input baseline; not a detection guarantee | D-002 |
| Additional input tests | 20 µVpp stretch; 1 mVpp headroom; approximately 1 ms nominal duration | Stretch detection not guaranteed | D-002 |
| Source model | 47 kΩ nominal series resistance; 30–70 kΩ normal, 20–100 kΩ extended characterization | Locked first-order model, not a complete electrode model | D-002 |
| AFE input impedance | At least 10 MΩ across the useful band | Baseline target; includes the complete input network | D-003 |
| Signal band | Approximately 300 Hz–7 kHz | Baseline; compare 5/7/10 kHz upper corners | D-003 |
| Electronics noise | ≤6 µV RMS input-referred over approximately 300 Hz–7 kHz | Objective; source noise reported separately | D-003 |
| Electrode offset | Approximately ±100 mV | Proposed robustness target; tolerance and recovery criteria open | D-003 |
| Acquisition | Analog detection → STM32WBA52 event capture; waveform ADC unused | MCU baseline accepted; analog detector implementation open | D-012, D-013 |
| Event capture | Eight channels; timing and minimum pulse width to be specified | No waveform sample-rate requirement | D-012 |
| Total analog gain | Approximately 50–60 dB discussed | Candidate; derive from detector error/noise/headroom | D-003 |
| Spike output | Eight-element count vector, configurable bin period | Selected normal-mode representation | D-005 |
| Bin period | 25 ms reference/default | Baseline, configurable | D-005 |
| Telemetry | BLE in STM32WBA52; ceramic chip antenna | Working baseline; matching/layout and package still open | D-006, D-013 |
| Operating modes | CHARGE with WPT and system OFF; RUN from battery with WPT absent; no charge-and-run | Locked operating policy; transition and detection circuit open | D-007 |
| Power path | 1S rechargeable cell, hardware-controlled battery-to-system isolation, charger fed from nominal ~5 V WPT_RAW | Architecture baseline; cell, charger, switch and WPT voltage unselected | D-016 |
| Rails and bias | Separate approximately 3.0 V analog/digital LDO rails; approximately 1.5 V analog common-mode | Rail partition baseline; exact voltage regulation and bias generation open | D-016 |
| WPT simulation | Rev A ADS coupled-inductor model from published measured L/R/k → CuraLink matching, rectifier, reservoir and load; HFSS → `.s2p` required after material geometry/environment changes | Selected method as revised by DEC-WPT-003; system performance unverified | D-017, D-018 |
| WPT coil geometry | 13.56 MHz square planar pair; 40 mm TX / 10 mm RX; 10 mm nominal coaxial separation; paper geometry in D-018 | Selected Rev A baseline; CuraLink reproduction and delivered DC performance unverified | D-018 / DEC-WPT-003 |
| Footprint | Approximately 25–30 mm in XY | Objective, not a hard limit | D-008 |
| Bench input | USB/DAC fixture board; one waveform split through eight 47 kΩ branches and FFC | User-confirmed two-board baseline; DAC/attenuator implementation proposed | D-014 |
| Input protection | Match CH1–CH8 and REF; candidate low-C connector ESD, 5.1 kΩ series limit and AC coupling; no populated 4.7 nF electrode shunt | Reference-adapted proposal, not a verified fault/ESD design; input-impedance target still unmet | D-015 |

## 3. Decision register

D-001 through D-009 were **recorded 2026-09-21** from the supplied handoff; **original decision dates are unknown**. Later entries state their actual decision dates. Evidence is imported engineering rationale unless an entry explicitly identifies another source or calculation. External research numbers in the handoff have not yet been checked against primary publications in this project.

| ID | Decision | Status |
|---|---|---|
| D-001 | Eight-channel extracellular-like bench system | Locked |
| D-002 | Neural signal envelope and first-order source model | Locked baseline |
| D-003 | High-impedance spike-band AFE with substantial analog gain | Function selected; implementation open |
| D-004 | Internal ADC and DMA for digital detection | Superseded by D-012 |
| D-005 | Per-channel spike counts with configurable bins | Selected representation; algorithm open |
| D-006 | BLE telemetry with wired debug and host tooling | Baseline |
| D-007 | Mutually exclusive wireless CHARGE and battery RUN | Locked operating policy; implementation open |
| D-008 | Design for first-board success within a compact footprint | Selected design policy |
| D-009 | Passive AWG-driven neural input fixture | Source generation superseded by D-014; source model and FFC preserved |
| D-010 | Budget, runtime and scheduling constraints | User-confirmed 2026-09-21 |
| D-011 | Reopen MCU vendor; evaluate gain and parts | MCU choice resolved by D-013; ADC assumptions corrected by D-012 |
| D-012 | Remove waveform ADC; detect analog events and count in MCU | Baseline direction; implementation open |
| D-013 | STM32WBA52 BLE controller and ceramic chip antenna | User-selected baseline; exact package/RF implementation open |
| D-014 | Two-board DAC fixture with one waveform split eight ways | User-selected baseline; circuit and FFC implementation provisional |
| D-015 | Adapt EGRA/Meower references for CuraLink protection and manual layout | Reference method accepted; values and qualification open |
| D-016 | 1S charge path, hardware system isolation and split rails | Architecture baseline; implementation and coil-board partition open |
| D-017 | WPT modeling and DC-power/efficiency evaluation method | DEC-WPT-002 revised by DEC-WPT-003; results pending |
| D-018 | Reuse Luo et al. 13.56 MHz 40 mm TX / 10 mm RX planar pair for Rev A | Selected baseline (DEC-WPT-003); reproduction and system performance unverified |
| D-019 | Proceed without VNA; rely on published coil model, tuning provisions and end-to-end DC tests | User-confirmed verification constraint |

### D-001 — Eight-channel extracellular-like bench system

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

**Constraints and calculations.** The working input-impedance target is ≥10 MΩ across the useful band. The electronics-noise objective is ≤6 µV RMS input-referred over approximately 300 Hz–7 kHz. Report source-resistor noise separately and also report total input-referred system noise; do not silently include source noise in an electronics-only limit.

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

**Candidates / tradeoffs.** The prior BG22 ranking and ESP32-C3 disadvantage based on ADC channel count are withdrawn. The user subsequently selected STM32WBA52 as the MCU working baseline in D-013. Verify event GPIO/timing resources, power, package, development support, and RF integration. TLV9064S and TPS7A20 remain provisional AFE/regulator candidates. BQ25185 is a historical power-path charger candidate, but load sharing is no longer required under D-007/D-016; reassess it against simpler 1S CC/CV chargers. None is procurement- or fabrication-locked. The external ADS7951 fallback is outside the current direction.

**Evidence / risks.** The [calculation record](calculations/afe-study/report.md) contains a linear noise/transfer model and limited synthetic detection tests. The model predicts approximately 1.68 µV RMS electronics noise over 300 Hz–7 kHz using its 1 kHz gain, but does not cover layout or overload behavior. Its input capacitance fails the original 10 MΩ band target; a source-loading-based alternative is proposed, not accepted. Exact package availability, programmer support, RF/WPT integration, and actual budget remain open.

**Verification / reopen when.** Review the [gain/parts note](design/gain-and-parts-shortlist.md), then validate the chosen acquisition and AFE on the bench before locking parts. The broader ADC-based system study is preserved as history. The current two-board analog proposal is linked in D-014; detailed component values remain provisional.

### D-012 — Remove waveform ADC; detect and count analog events

**Decision date: 2026-09-22. Recorded: 2026-09-22. Status: Baseline direction; implementation open.**

**Choice.** Remove waveform digitization from the main signal path. Use the custom AFE, analog threshold detection, MCU event capture/counting, and BLE. D-004 is superseded. An unused ADC peripheral inside an otherwise suitable MCU does not require using it; no external waveform ADC or onboard debug ADC is assumed.

**Objective / evidence.** Follow the user's explicit correction, “we are trying to remove the ADC.” This is design intent, not a demonstrated circuit or measured power saving. Existing channel/input requirements, budget, runtime target, and narrow gain/parts scope remain in force.

**Alternatives and tradeoffs.** ADC/software detection offered waveform observability and flexible algorithms. Analog detection removes conversion and waveform-processing requirements but adds comparator, threshold, hysteresis, calibration, and event-capture requirements. System power and area must be compared including these circuits.

**Rationale.** The normal output is event counts. The AFE must still reject DC, control bandwidth/noise, and amplify electrode-level signals. Select gain against detector errors and headroom, not ADC code counts. The STM32WBA52 was selected for BLE and event handling; its ADC remains unused.

**Risks and mitigation.** Comparator noise/chatter, threshold drift, and biphasic lobes can cause false or duplicate events. Specify polarity handling, hysteresis, refractory/rearm logic, and simultaneous-event capture. Preserve analog test points and external-instrument characterization for first-board diagnosis. Comparator topology, threshold generation, exact gain, and MCU remain open.

**Verification / reopen when.** Budget detector offset/noise and threshold errors at the electrode; test missed/false/duplicate events over the input envelope, pulse capture during BLE activity, overload recovery, total power, and runtime. Reopen only if demonstrated tradeoffs defeat the objectives; do not silently reintroduce an ADC.

### D-013 — STM32WBA52 BLE MCU and ceramic chip antenna

**Decision date: 2026-09-22. Recorded: 2026-09-22. Status: User-selected working baseline; exact ordering part/package and RF design open.**

**Choice.** Use STM32WBA52 for event counting, binning and BLE; leave waveform ADC unused. Use a ceramic chip antenna on the CuraLink PCB, with RF matching/tuning and a board keep-out. The earlier EM9304 plus ceramic antenna preference was briefly accepted on 2026-09-22, then explicitly replaced by the user's statement, “we are using the STM32WBA52.” Preserve it only as design history.

**Objective and evidence.** The workload is eight digital events plus low-rate BLE telemetry; the ADC is not a selection benefit. ST lists a BLE radio, programmable output up to +10 dBm, integrated balun, and an ADC peripheral. External ceramic antenna/matching remain necessary. [ST product specification](https://www.st.com/en/microcontrollers-microprocessors/stm32wba52kg.html). The selected device has not been pin-mapped or tested in this project.

**Alternatives and tradeoffs.** EM9304 offered a 4 × 4 mm QFN without a general-purpose sensor ADC and a more specialized development path; its smallest WLCSP exposes only six GPIO, insufficient for eight direct event lines ([manufacturer datasheet](https://www.emmicroelectronic.com/sites/default/files/products/datasheets/9304-DS%20%28updated%20Oct%202024%29.pdf)). STM32WBA52 has an unused ADC and potentially larger package but matches the user's development and radio preference. A ceramic chip antenna is compact as a component but still consumes board clearance and matching effort; board-level area must be compared with a trace design.

**Rationale.** Preserve a single-chip BLE/controller architecture and familiar SWD workflow while supporting analog event detection. TX output-power headroom is a capability to measure against the final RF environment, not proof of tissue-link success. CuraLink is a benchtop analog prototype, not a qualified implant.

**Risks and mitigation.** Select an antenna against the actual board, ground, battery and coil geometry; reserve tuning components/test access. Audit eight event pins alongside SWD, UART, RF, clocks and power. Verify GPIO interrupt capture during BLE and compare full-system current. The 5 × 5 mm UFQFPN32 is a package candidate, not a completed pinout.

**Verification / reopen when.** Measure link reliability/current over programmable TX settings and the intended environment; complete the pin map, RF layout and packet/event tests before fabrication. Reopen the MCU only if concrete implementation or measured constraints defeat the accepted baseline.

### D-014 — Separate USB/DAC stimulus and CuraLink boards

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

**Decision date: 2026-09-22. Recorded: 2026-09-22. Status: Architecture baseline; parts, electrical limits and board partition open.**

**Choice.** Use a single-cell rechargeable Li-ion/LiPo battery. The working receiver path is RX PCB coil → resonant tuning → rectifier → reservoir/overvoltage protection → `WPT_RAW` (approximately 5 V **target**, not a locked rating) → 1S CC/CV charger → battery. `WPT_RAW` also feeds a `WPT_PRESENT` detector. A hardware-controlled high-side battery-to-`SYS_RAW` switch opens whenever supported WPT is present and closes after WPT is removed, subject to valid battery and rails. Separate approximately 3.0 V analog and digital LDO rails power the AFE/comparators/bias and STM32WBA52/BLE respectively; approximately 1.5 V analog common-mode is a working candidate. A discrete high-side PMOS or load-switch IC, exact charger, LDOs, cell and common-mode generator remain unselected.

| WPT present | Battery/rail validity | System switch | Main system |
|---|---|---|---|
| Yes | Any | Open | Off |
| No | Valid | Closed after controlled startup | RUN |
| No | Invalid or depleted | Open | Off |

**Objective / evidence.** Implement D-007 without relying on powered firmware for disable, keep BLE load steps off the quiet analog rail, and allow automatic charge-to-run transition. These topology preferences and nominal voltages came from the user's 2026-09-22 decision summary. No part-level power budget, thermal calculation or hardware verification establishes the voltages or switch arrangement yet.

**Alternatives and tradeoffs.** A PMOS is simple, but its body diode and gate drive require analysis; a dedicated load switch can provide controlled slew and, if required, reverse-current blocking. Back-to-back FETs are a candidate if `SYS_RAW` can be externally driven above BAT. A power-path charger with load sharing is permissible but unnecessary for the exclusive-mode requirement. Separate LDOs improve rail partitioning at a cost in area and quiescent current. A single LDO might be simpler, but must meet measured BLE/AFE coupling limits.

**Rationale.** For a PMOS concept, connect source to BAT and drain to `SYS_RAW`; pull its gate toward source to turn it off and low relative to source to turn it on. Derive control relative to the source rather than directly applying the nominal 5 V WPT node to the gate. The switch state follows WPT presence, not charger termination. If a separate coil/receiver PCB is used, placing resonant tuning, rectifier, reservoir and input protection beside the coil and carrying **DC WPT_RAW** to the main board is the preferred *partition candidate*, reducing resonant-loop connector parasitics. Main-board charger, battery, switch and regulators are the matching candidate placement. The separate RX board itself is not yet selected.

**Risks and mitigation.** A fixed 3.0 V LDO needs BAT at its input above 3.0 V **plus dropout and switch/interconnect loss**; calculate the usable capacity and one-hour runtime over discharge, or revise the rail/regulator strategy. Verify switch default state, detector operation with no/weak WPT, startup sequencing, gate-source ratings, body-diode/back-feed routes, charger input range/OVP, battery temperature sensing, overcurrent and undervoltage protection. `WPT_RAW≈5 V` is a target at the defined load/alignment, not proof of adequate charger input under all conditions. The analog common-mode generator must be quiet and stable across mode transitions.

**Verification / reopen when.** Complete a worst-case source-to-load voltage/current/thermal budget, including battery discharge and BLE peaks; check charger CC/CV/termination and protection; demonstrate hardware switch truth table, field-present charge-complete holdoff and automatic removal transition. Scope `WPT_RAW`, BAT, `SYS_RAW`, both rails and common-mode during startup/brownout. Select the coil-board partition only after mechanical, noise and WPT efficiency comparison. Reopen rail values, switch technology or physical partition when calculations or bench data show a constraint violation.

### D-017 — WPT simulation workflow (user alias DEC-WPT-002)

**Decision date: 2026-09-22. Recorded: 2026-09-22; last revised: 2026-09-22. Status: Selected method as revised by D-018; no simulation result.**

**Choice.** DEC-WPT-002 originally selected HFSS physical-coil modeling → Touchstone `.s2p` → ADS resonant tuning, nonlinear rectifier, reservoir and initial resistive DC load. D-018 / DEC-WPT-003 narrows the Rev A implementation: reproduce the published coil geometry and begin ADS circuit design from the paper's measured L/R/k coupled-inductor model, without rerunning coil optimization in HFSS. Retain HFSS → `.s2p` for geometry correlation and require it when RX/TX size, materials, separation, nearby copper/battery/ferrite or another physical condition changes materially. In either route, optimize delivered DC power and explicitly defined RF-to-DC efficiency; use L, R, Q, M, k, SRF and S21 as diagnostics.

**Objective / constraints and evidence.** Separate the measured coil baseline from CuraLink-specific tuning and RF-to-DC conversion, and evaluate whether the receiver can deliver useful, bounded DC power under realistic alignment and load. The workflow comes from DEC-WPT-002 and its Rev A shortcut from DEC-WPT-003. [Ansys documents Touchstone export](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v251/en/Subsystems/HFSS/Subsystems/HFSS%20Scripting/Content/ExportNetworkDataPlanarEM.htm?TocPath=Design+Object+Script+Commands%7C_____46); [Keysight documents harmonic-balance treatment of a nonlinear rectifier](https://www.keysight.com/in/en/assets/7018-05801/case-studies/5992-2395.pdf). No ADS or CuraLink bench result has yet been recorded.

**Alternatives and tradeoffs.** A coil-only Q/k/S21 study is faster but cannot establish rectified output under nonlinear loading. Starting directly with a charger model adds control behavior before the coil and rectifier are understood. A resistive load yields an interpretable first RF-to-DC comparison; later charger/load-state models must replace it before battery-charge claims. A passive `.s2p` cannot capture nonlinear rectifier, WPT controller or thermal behavior itself.

**Rationale.** The original division uses each tool for the quantities it represents well. DEC-WPT-003 saves Rev A time by using fabricated-coil measurements as the initial circuit model and reserves new EM work for changes that make those measurements nonrepresentative. For the first load, report `P_DC = V_DC²/R_LOAD` and `η_RF→DC = P_DC/P_RF,accepted at the TX coil-model input port`, recording source impedance and port planes. Report other efficiency boundaries under distinct names. The detailed [simulation method](design/2026-09-22-wpt-simulation-method.md) defines sweeps and reproducibility.

**Risks and mitigation.** A fixed L/R/k model does not directly represent frequency-dependent parasitics, SRF, offset, tilt or environmental changes. Sweep k only as a labeled sensitivity estimate until geometry-dependent data exist. Nearby copper/battery/ferrite, tuning-capacitor double counting, inadequate harmonic order or incorrect power boundaries can invalidate results. Verify ADS convergence and treat simulated results as predictions until measured on fabricated CuraLink coils.

**Verification / reopen when.** Archive the published coil-model source/values, ADS schematic/models, parameter sweeps, power-boundary definitions and derived DC voltage/power/efficiency. Under D-019, compare end-to-end hardware DC behavior across load and alignment without claiming independent coil-parameter validation. Add the HFSS geometry, convergence and `.s2p` record when D-018's reopening conditions apply. Reopen the workflow if model fidelity or hardware correlation is inadequate.

### D-018 — Reuse published 13.56 MHz planar coils for Rev A (DEC-WPT-003)

**Decision date: 2026-09-22. Recorded: 2026-09-22. Status: Selected Rev A baseline; CuraLink reproduction and power performance unverified.**

**Choice.** For CuraLink Rev A, reuse the square planar spiral pair published by Luo et al. at 13.56 MHz and 10 mm nominal coaxial separation instead of re-optimizing the coils. On approximately 0.8 mm FR4 with 1 oz copper, the paper specifies TX outer/inner diameters of 40/14.60 mm, 8 turns, 1.3 mm trace width and 0.15 mm spacing; RX outer/inner diameters of 10/5.55 mm, 5 turns, 0.3 mm trace width and 0.15 mm spacing. Begin ADS work with coupled inductors using the measured L/R/k values. Design CuraLink-specific matching, rectifier, reservoir and charger interface; do not copy the paper's matching capacitors because they transformed a 50 Ω measurement load. This is not a claim that CuraLink will reproduce the paper's performance or safely transfer a particular power.

**Objective / constraints and evidence.** Fit the receive coil comfortably within CuraLink's approximate 25–30 mm main-board envelope while using a published 13.56 MHz link intended for a compact neural-recording receiver. The paper reports measured values at the nominal geometry of approximately `L_TX = 2.49 µH`, `R_TX = 1.80 Ω`, `Q_TX = 118`, `L_RX = 0.330 µH`, `R_RX = 0.399 Ω`, `Q_RX = 70.4`, `M = 60.0 nH` and `k = 0.0662`. Its measured `S21 = -1.55 dB`, or approximately 70%, used primary and secondary matching networks between 50 Ω VNA ports. That result is RF coil-link efficiency and excludes rectification, reservoir, regulation and battery charging. [Luo et al., “Design and Optimization of Planar Spiral Coils for Powering Implantable Neural Recording Microsystem,” 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10302922/).

**Published-file availability.** No public GitHub repository or Touchstone/supplementary dataset was found on 2026-09-22. The paper states “Data Availability Statement: Not applicable,” and its archived full-text record exposes no supplementary-material entry. Therefore Rev A begins with the paper's single-frequency lumped measurements using the [ADS setup](design/2026-09-22-ads-wpt-model-setup.md), not an original measured `.s2p`. This search result is evidence of current public availability, not proof that the authors have no private VNA data.

**Alternatives and tradeoffs.** A custom coil optimized around CuraLink's nonlinear rectifier, charger, enclosure and alignment envelope could outperform or package better, but needs more EM optimization. A larger RX could improve coupling but consume main-board area. Adopting the paper geometry saves initial design time and supplies measured correlation targets, while its 50 Ω matched test condition does not represent CuraLink's rectifier load.

**Rationale.** The pair has already been optimized, fabricated and VNA-measured for a compact neural-recording application. Using measured coil parameters gives Rev A a stronger and faster initial basis than repeating the same optimization. For rectifier selection, treat the reference RX as a two-terminal source and compare the low-capacitance Schottky full-wave bridge against a two-diode doubler after independently retuning each matching network. Do not infer available charging power from the 70% number without a defined accepted TX power and rectified load.

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

## 4. Open work and next design sequence

The next major task is to **review and validate the [two-board AFE proposal](design/2026-09-22-two-board-analog-afe.md)**. This is a calculation/design study, not a PCB release. The steps below are work to perform or complete, not decisions already made.

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
| 9 | WPT and mechanical integration | Execute D-018 in ADS from the published measured L/R/k model, designing CuraLink-specific matching and comparing delivered DC power/efficiency and peak stress across rectifier/load/coupling assumptions. Reopen HFSS if the published physical conditions change. Bound WPT_RAW under full-to-empty cell and no-load cases; assess RX-board DC partition, RF floorplan and stacking with the [functional-block design](design/2026-09-22-power-functional-blocks.md) |

The proposal fails the existing ≥10 MΩ input-impedance target at 7 kHz due to input capacitance even before FFC loading. Fix this design problem or explicitly reopen the requirement before fabrication. Input ESD and fault protection remain candidates, not qualified provisions. The event-capture implementation, detector thresholds/refractory behavior, count width, BLE packet format, host interfaces, exact FFC part, antenna match, and acceptance limits remain open. Define them when their governing constraints are available.

### Schedule and available equipment recovered from GitHub

The 2026-09-18 repository notes used **2026-10-18 as a working planning deadline**. On 2026-09-21 the user explicitly removed the hard deadline and prioritized a defensible design. Retain the old schedule only as historical context.

Those notes also report access to extensive lab equipment and ownership of an STM32 ST-LINK. A suitable STM32 development board was unconfirmed. Exact instrument inventory, budget, and ADS/HFSS access remain unresolved. These are historical project-context statements, not a fresh inventory check.

## 5. Verification record

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
| 2026-09-22 | Logged user-provided ADS TX-input S11 export: approximately 0.977∠26.47° at 13.56 MHz, corresponding to 11.1+j212 Ω on a 50 Ω reference and a severe simulated TX-side mismatch. Recorded configuration-provenance and transient-comparison caveats; no new matching values selected | ADS CSV `data/daa.csv`; complex S11-to-impedance and reflected/accepted-power calculation |

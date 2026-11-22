# AFE signal-integrity review — 2026-10-02

The existing circuit has an observable shared-VMID crosstalk path even before PCB parasitics. Actual LTspice CH1-only excitation predicts a worst quiet-channel equivalent of **0.490 µVpp for a 200 µVpp aggressor**, or **2.449 µVpp for a 1 mVpp aggressor**, at 300 Hz. An assumed capacitance of only **0.01 pF between AFE_OUT_1 and CH2_PLUS** increases the worst total to **3.45 / 17.25 µVpp**, respectively. These are nominal circuit-model/sensitivity results; they are not measurements, package crosstalk guarantees or extracted PCB capacitances.

## Fixture and evidence

Four hidden actual LTspice 26.0.2 runs completed with exit 0, completed logs and finite raw data: an independent full operating-point check, CH1-only nominal AC, an input-to-input capacitance sweep, and an amplified-output-to-input capacitance sweep. All 36 amplifier units have outputs and inputs inside 0.05–2.95 V and differential inputs below 1 mV at the quiescent operating point. Each AC case covers 300 Hz–7 kHz at 100 points/decade, including both endpoints (138 points per step).

`canonical-afe.lib` is an unedited snapshot of the previously verified full AFE, midpoint divider/buffer and MCU 150 Ω / 470 pF interfaces. CH1 has AC1 normalization; CH2–CH8 and REF are AC0, each still connected through its own declared 47 kΩ source resistor. Each input retains the fixture's **assumed** 20 pF FFC shunt, 2 pF trace shunt, 0.5 pF capacitance-only ESD model and amplifier-family input behavior. Added mutual coupling capacitors are independent assumptions, not measurements of that FFC.

The amplifier models retain the original equations of TI's [TLV9002 PSpice model](https://www.ti.com/lit/zip/SBOMAL2) and [TLV9052 PSpice model](https://www.ti.com/lit/zip/SBOMAO0), with only model/subcircuit identifiers prefixed to avoid collisions. These single-amplifier family models represent each section of the selected TLV9004/TLV9054 quads. They do **not** represent intra-package channel coupling. Model/source SHA-256 hashes, provenance and fixture assumptions are in `source-provenance.json` and `models/model-provenance.json`; deck/log/raw hashes and explicit criteria are in `results.json`. All added parts use the `C_ASSUMED` simulation reference and do not change the design BOM.

## Definitions and nominal result

For the isolated CH1 fixture, let `H11 = V(ADC_IN_1)/V(SRC_CH1)` and `H21 = V(ADC_IN_2)/V(SRC_CH1)`. Crosstalk is `20 log10(|H21/H11|)`. Victim source-input-equivalent amplitude is `|H21/H11_nominal| × aggressor source amplitude`; identical nominal channel transfer functions justify this source-input reference. This accounts for the frequency-dependent AFE gain rather than dividing everything by 1000. Voltages below are peak-to-peak sine scaling; arbitrary spike templates and overrange artifacts require separate transient tests.

| Frequency | Aggressor ADC gain, V/V | Quiet-channel crosstalk | Equivalent for 200 µVpp | Equivalent for 1 mVpp |
|---|---:|---:|---:|---:|
| 300 Hz | 702.51 | −52.22 dB | 0.490 µVpp | 2.449 µVpp |
| 1 kHz | 969.57 | −55.53 dB | 0.335 µVpp | 1.674 µVpp |
| 7 kHz | 704.79 | −68.88 dB | 0.072 µVpp | 0.360 µVpp |

CH2–CH8 have the same nominal correlated disturbance within model numerical precision. At approximately 1 kHz, the VMID disturbance is about 1.89 V/V per external CH1 source voltage and REF_PRE about 18.9 V/V. These large intermediate normalized gains do not imply actual 1 V stimuli are supported; the AC source is a linearization normalization. At the actual 200 µVpp nominal stimulus, the modeled VMID disturbance is approximately 378 µVpp.

The late amplifier feedback dividers return amplified signal current into VMID: for CH1, R1017/R1018 are 10 kΩ / 12.4 kΩ around U107A, and R1013/R1014 return LP1 current as well. Equivalent dividers exist on every channel. VMID is buffered by U109B **before** R1149 = 47 Ω; C1058 = 4.7 µF shunts VMID to GND. This shared impedance lets aggressor current modulate the common midpoint. REF_PRE then responds to the same midpoint through the REF preamplifier. Ideal 3 V supply and ground eliminate copper and rail impedances from this study, so physical routing can add paths rather than validate their absence.

The proposed review criterion of **≤1 µVpp source-equivalent victim for one 1 mVpp aggressor (−60 dB)** is a new review threshold, **not an accepted requirement**. The nominal model fails it in the lower band. The existing 200 µVpp nominal input produces less than 0.5 µVpp equivalent in this model, but that does not establish a total crosstalk budget or package/PCB pass. Seven coherent equal aggressors can sum their complex transfers; the single-aggressor number is not the eight-channel aggregate limit.

## Assumed capacitance sensitivities

The ordinary input-to-input sweep connects FFC_CH1 and FFC_CH2. The late-to-early sweep connects AFE_OUT_1 directly to CH2_PLUS, after CH2's coupling capacitor C1008 and current-limit resistor R1019. The late output carries roughly 700–1000 times the input voltage, so this second path is much more damaging.

| Assumed path and capacitance | Worst **incremental** equivalent, 200 µVpp aggressor | Worst incremental equivalent, 1 mVpp aggressor | Worst **total** equivalent, 1 mVpp aggressor |
|---|---:|---:|---:|
| FFC_CH1 ↔ FFC_CH2, 0.1 pF | 0.041 µVpp | 0.206 µVpp | 2.446 µVpp |
| FFC_CH1 ↔ FFC_CH2, 1 pF | 0.412 µVpp | 2.059 µVpp | 2.423 µVpp |
| AFE_OUT_1 ↔ CH2_PLUS, 0.01 pF | 3.471 µVpp | 17.354 µVpp | 17.246 µVpp |
| AFE_OUT_1 ↔ CH2_PLUS, 0.02 pF | 6.942 µVpp | 34.708 µVpp | 34.599 µVpp |
| AFE_OUT_1 ↔ CH2_PLUS, 0.1 pF | 34.708 µVpp | 173.539 µVpp | 173.428 µVpp |

The late-output sensitivity peaks near 6.125 kHz. The full sweep extends to 1 pF, where the 1 mVpp linear estimate can approach output headroom; it is a sensitivity stress, not proof of large-signal operation. Complex increments are computed as `H21(C) − H21(0)` before taking magnitudes. A smaller total at one frequency/capacitance can result from phase cancellation and is not evidence that added capacitance helps.

For small capacitance, the ordinary coupling ratio scales approximately as `ω Cx × 47 kΩ`. Late-to-input coupling has an additional aggressor gain: approximately `|H11(f)| × ω Cx × (47 kΩ + 5.1 kΩ)`, with actual model transfer/phase modifying that estimate. The 0.01 pF run implies an incremental-only 1 µVpp/1 mVpp allowance near **0.00058 pF = 0.58 fF**, under this fixture. This is a sensitivity-derived budget, **not** a geometry-to-spacing requirement or evidence it is achievable. The shared-circuit path already exceeds the proposed total budget, so reducing parasitic capacitance alone cannot pass that total criterion.

Coupling into **FFC_REF / REF_PLUS / REF_PRE** is a separate risk. A signal injected into shared REF is subtracted by all eight differential stages, producing correlated interference. To first order an assumed 0.1 pF external-input-to-REF coupling through 47 kΩ is about `2π × 7 kHz × 0.1 pF × 47 kΩ = 0.000207` before the subsequent shared transfer, about 0.207 µVpp for a 1 mVpp aggressor. This is an analytical warning, not an additional LTspice run; amplified-output-to-REF coupling inherits the large late-stage voltage ratio and can affect every channel.

## Layout actions and reopening conditions

1. Keep **FFC_CH1–8, FFC_REF, CH1–8_PLUS and REF_PLUS** confined to the connector/protection/preamp region. For CH1/CH2 the critical nodes are between C1001/C1008 and U101 pins2/4, with R1002/R1020 = 22 MΩ bias resistors. Route no AFE_OUT_1–8, ADC_IN_1–8, amplified CHx_HP/LP1_OUT, digital clocks, RF or charger lines alongside or above/below these inputs. A crossing should be brief and screened by a continuous reference layer where possible.
2. Place **U110/U111/U112** by the FFC connector. Route their GND pins3 and8 into short ground connections with nearby vias; avoid sending ESD return current through the preamp reference/bias paths. Ground-interleaved FFC pins help return control but do not establish a mutual-capacitance value.
3. Keep **REF_PLUS** especially compact around C1057, R1146 and U109A. Route the low-impedance REF_PRE distribution to C1003/C1010/… symmetrically and away from late outputs. Shared REF should not become a long high-impedance bus.
4. Keep each amplifier/filter feedback loop local: the two 909 kΩ feedback/balance chains around U103/U104 and the Sallen–Key feedback capacitors are sensitive to unintended capacitance. Preserve clean solder mask, inspection access and flux removal around the 22 MΩ nodes. Do not add large test pads or long stubs to CHx_PLUS/REF_PLUS merely for convenience; use existing buffered-output access for routine scope tests.
5. Place U109B, R1149 and C1058 tightly together; distribute VMID without shared narrow traces carrying large stage-return currents. The nominal 47 Ω midpoint architecture remains an open circuit-level crosstalk issue. A lower-impedance or separated quiet-bias/feedback-return solution must be evaluated for stability, load, startup and noise before changing the design. PCB placement alone cannot eliminate the observed nominal shared-network transfer.
6. Maintain a continuous ground reference beneath ordinary AFE/ADC routing and keep noisy power/RF return loops away from the input section. Do not create an AGND/DGND split that forces a signal return across a gap. Ground screening trades reduced mutual electric coupling for increased input-to-ground capacitance; the **≥10 MΩ full-band input target is already unmet** in the candidate circuit and remains unresolved. No guard or shield should silently relax that target.
7. On the bench, excite **one channel only**, keep all other inputs and REF terminated through representative 47 kΩ sources, and sweep the full band plus representative spikes. The accepted one-DAC/split-eight fixture needs channel isolation to perform this test; driving all eight together cannot measure channel isolation. Repeat with BLE activity, changed source resistances and the final FFC/battery/coil arrangement. Capture both output ratios and input-equivalent errors, and separate clipping/recovery artifacts from small-signal crosstalk.

No routed-board extraction, impedance-controlled geometry, numerical spacing clearance, intra-quad crosstalk, GHz/RF rectification, switched ADC sampling or ground-bounce result is established here. Local/package tolerances and simultaneous aggressors remain separate verification gates. Figures `nominal-shared-crosstalk.png` and `assumed-capacitance-sensitivity.png` were visually inspected; raw frequency-domain data are preserved in `frequency-sensitivity.csv`.

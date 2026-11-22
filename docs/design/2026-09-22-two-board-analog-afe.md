# CuraLink — two-board stimulus and analog-event AFE design

**2026-09-22 · P1 engineering proposal; not a fabrication release.**

The [handbook](../engineering-handbook.md) controls requirements and accepted decisions. The user selected STM32WBA52 with its ADC unused, retained a ceramic chip antenna, and confirmed one DAC waveform split eight ways. Component values below are a reviewable proposed circuit, not accepted final parts or measured performance.

For the specified EGRA KiCad checkpoint, Meower comparison, CH/REF connector protection, and handoff to manual layout, see the [reference audit](2026-09-22-egra-meower-reference-audit.md).

## 1. Architecture and input

```text
BOARD 1 — USB-powered stimulus fixture
Laptop → USB controller with buffered playback → one DAC → reconstruction LPF
       → ~1000:1 attenuation → eight individually selectable 47 kΩ branches
       → 18-contact FFC: CH1–CH8 + REF + grounds

BOARD 2 — battery-powered CuraLink
FFC → low-capacitance input ESD + current limiting → eight input preamps + shared REF preamp
    → eight differential HP/gain stages → eight fourth-order LP filters
    → DC recentering → dual-polarity comparators → one event line/channel
    → STM32WBA52: refractory/rearm, counts, bins → BLE → ceramic antenna

External scope/DAQ connects to analog test points for characterization.
There is no neural waveform ADC or waveform sample stream on board 2.
```

The laptop output requires a **DAC**, not an ADC; the user confirmed this interpretation. Board 1 produces a shared waveform, not eight independent sources. Provide per-branch selection between stimulus and quiet reference for selective-drive tests.

| Input condition | Established value |
|---|---|
| Nominal / primary region | 200 µVpp / 100–300 µVpp |
| Characterization | 50–500 µVpp; approximately 0.5–2 ms |
| Extra tests | 20 µVpp stretch; 1 mVpp headroom |
| Source resistance | 47 kΩ nominal; 30–70 kΩ normal, 20–100 kΩ extended |
| Signal type | Biphasic/multiphasic, defined relative to shared REF |
| Band / noise objective | Approximately 300 Hz–7 kHz; electronics ≤6 µV RMS in that band |

Do not equate peak-to-peak amplitude with comparator threshold excursion. Preserve a DC-offset injection provision for later ±100 mV recovery testing; the normal attenuator cannot generate that range.

## 2. Neuralink comparison and the limit of the claim

Neuralink's **2019** paper reports 42.9–59.4 dB programmable gain, 5.9 µV RMS input-referred noise over 3 Hz–10 kHz, 7.2 mVpp maximum differential input range, 10-bit conversion, and 5.2 µW per analog pixel. These are historical published values, not specifications for its current product. [Paper, Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC6914248/)

Our proposal targets comparable microvolt signal conditioning and approximately 60 dB gain, with a deliberately narrower spike band and analog event output. It does **not** match the published input range at full gain, raw-waveform capability, channel density, or per-channel power. Integrating noise over the same reporting interval does not equalize different transfer functions. Report gain/noise spectra and filtering alongside every comparison. The paper's 3 Hz–27 kHz front-end bandwidth does not set CuraLink's narrower spike-band corners.

## 3. Board 1: create a credible electrode-like signal

**Candidate DAC: TI DAC80501**, using its 2.5 V full-scale configuration. It provides one 16-bit buffered output and SPI; the datasheet lists 5 µs typical settling. Proposed playback is **100 kS/s**, paced locally with buffered data, not timed directly by laptop USB transactions. Allow at least 24 serial clocks plus required framing and settling per update. At 10 MHz SPI, serial transfer alone is 2.4 µs; validate actual settling, waveform steps, and underflow handling. The USB controller part is open; a small USB MCU/module can perform this function without changing the board-2 controller. [TI product](https://www.ti.com/product/DAC80501), [datasheet](https://www.ti.com/lit/ds/symlink/dac80501.pdf)

Use a buffered 1.25 V stimulus reference, derived from the DAC reference with a matched divider, as the zero of the waveform. This is **VSTIM_REF**, not board-2 VMID and not ground. DAC output swings around it. A proposed unity-gain Sallen–Key reconstruction filter uses R1=R2=5.62 kΩ, C1=2 nF from the R junction to the buffer output, and C2=1 nF from the buffer input to VSTIM_REF. Ideal f0≈20.0 kHz and Q≈0.707. Buffer loading/stability and reference noise need verification.

After the filter, use **49.9 kΩ series / 49.9 Ω shunt to VSTIM_REF**:

`a = 49.9 / (49,900 + 49.9) = 1/1001`.

| Desired unloaded signal | DAC/filter excursion around 1.25 V |
|---|---:|
| 20 µVpp | 20.02 mVpp |
| 50 µVpp | 50.05 mVpp |
| 200 µVpp | 200.2 mVpp |
| 500 µVpp | 500.5 mVpp |
| 1 mVpp | 1.001 Vpp |

One ideal DAC code becomes `2.5/65536/1001 = 0.0381 µV` after attenuation. This is resolution, not accuracy or noise performance. Reconstruction-filter gain, resistor tolerances, output impedance, source resistance, and the connected AFE must be included in measured calibration.

Split the attenuated node into eight branches. Each branch has a stimulus/quiet selector, then its own replaceable 47 kΩ resistor, then its FFC channel. Quiet connects to VSTIM_REF **through the same source resistance**, not to an open circuit. Feed REF from VSTIM_REF through a selectable 47 kΩ/low-resistance path; the calculations below assume 47 kΩ. The branch resistors are series source impedances, not eight shunt 47 kΩ loads.

FFC candidate mapping (carry no DAC clock, USB, or main-board supply on this cable):

```text
1 GND   2 CH1   3 GND   4 CH2   5 GND   6 CH3
7 GND   8 CH4   9 GND  10 CH5  11 GND  12 CH6
13 GND 14 CH7  15 GND  16 CH8  17 REF  18 GND
```

The two boards need a defined ground connection; REF is a measured analog reference, not the power return. Board 2 remains battery powered. USB ground noise may enter through the fixture; compare quiet-source noise with USB traffic active and paused. Use the shortest practical FFC and measure its capacitance. Confirm connector contact side, cable orientation, pin-1 markings and assembled end-to-end continuity. Retain an external AWG input as a candidate bring-up bypass, not the normal source.

## 4. Board 2: concrete AFE proposal

The power baseline now uses separate **approximately 3.0 V analog and digital LDO rails**, with **VMID≈1.5 V** a candidate derived from the analog rail. Exact regulator and bias circuits remain open. Keep the digital/radio supply separately decoupled and allow rail current measurement. Never connect VSTIM_REF directly to VMID: the input capacitors translate common-mode levels. Use a quiet divider/buffer for VMID and analyze its noise and capacitive-load stability; the calculations currently assume an ideal VMID. D-007 requires the AFE and BLE off throughout WPT charging.

**Amplifier candidate: TLV9064S.** TI specifies typical 10 MHz GBW, 10 nV/√Hz voltage noise at 10 kHz, 16 nV/√Hz at 1 kHz, and 538 µA per amplifier under its stated test conditions. Its input capacitance is a significant constraint, addressed below. Nine quad packages provide 33 signal/reference amplifiers, one VMID buffer, and two threshold buffers. Do not tie unused amplifiers open. [TI datasheet, electrical characteristics](https://www.ti.com/lit/ds/symlink/tlv9064.pdf)

### A. Input preamplifier: CH1–CH8 and REF

```text
FFC input → 5.1 kΩ → 10 nF C0G → op-amp +
                                │
                              22 MΩ
                                │
                               VMID
op-amp − → 1 kΩ → VMID
output   → 10 kΩ → op-amp −
```

Fit a low-capacitance ESD diode from the FFC input node to AGND before the 5.1 kΩ resistor. The TPD4E05U06 footprint is a candidate for CH1–CH8 and REF, not copied from EGRA's electrode nets: EGRA uses this part on USB. TI quotes 0.5 pF typical line capacitance, 10 nA maximum leakage, 5.5 V working standoff and about 10 V clamping at 1 A. This is transient ESD protection, not a 3 V precision clamp; test the TLV9064 input clamp current, capacitor pulse behavior, and resistor pulse rating for specified fault cases. [TI ESD part](https://www.ti.com/product/TPD4E05U06)

Gain `GA=1+10k/1k=11`. The input DC-blocking pole is approximately 0.72 Hz; this stage does not establish the spike-band high-pass. At an abrupt ±100 mV offset step, its ideal initial excursion is ±1.1 V about VMID. Keep the remaining gain after stronger DC rejection. Connecting a 1.25 V-biased fixture can nevertheless overload the preamp temporarily; startup blanking and measured recovery are mandatory. The 5.1 kΩ is candidate input-current limiting following the connector ESD clamp. TI limits TLV9064 overdrive current to 10 mA; internal op-amp ESD structures alone do not establish system-level connector protection. [TI op-amp datasheet](https://www.ti.com/lit/ds/symlink/tlv9064.pdf)

### B. Differential high-pass and gain: eight copies

```text
CH_PRE  → 10 nF → 53.6 kΩ → op-amp −
output  → 1.87 MΩ         → op-amp −
REF_PRE → 10 nF → 53.6 kΩ → op-amp +
op-amp + → 1.87 MΩ → VMID
```

With matched ratios, `VB = (REF_PRE−CH_PRE) × (Rf/R) × sRC/(1+sRC)` relative to VMID. Thus **GB=34.888** and **fHP=296.93 Hz**. The signal polarity is inverted; the detector handles both signs. Use 0.1% paired resistors and 1% C0G capacitors as initial values. Matching, including capacitor mismatch, controls system common-mode rejection; this is not a precision instrumentation amplifier with guaranteed CMRR.

Provide paired resistor substitutions to **936 kΩ** for approximately half gain. Both 1.87 MΩ resistors must change together. Keep REF preamp fanout physically short and characterize correlated reference noise and crosstalk.

### C/D. Fourth-order low-pass: two sections per channel

For each section: prior output → R1 → node A → R2 → op-amp +; C1 connects node A to **that section's output**; C2 connects op-amp + to VMID. Noninverting feedback uses Rg to VMID and Rf to output.

| Parameter | First section | Second section |
|---|---:|---:|
| R1=R2 | 22.6 kΩ | 22.6 kΩ |
| C1=C2 | 1 nF C0G | 1 nF C0G |
| Rg | 10 kΩ | 10 kΩ |
| Rf | 1.50 kΩ | 12.4 kΩ |
| K=1+Rf/Rg | 1.15 | 2.24 |
| Q=1/(3−K) | 0.5405 | 1.3158 |
| f0=1/(2πRC) | 7042 Hz | 7042 Hz |

This approximates a fourth-order Butterworth response; low-Q section first limits intermediate peaking. Filtering controls noise and spike shape even without an ADC. It is not an ADC anti-alias requirement. Retain alternate R values for 5/7/10 kHz comparison.

### E. DC recentering before comparators

Final filter output → **100 Ω → 100 nF → DET**; DET → **100 kΩ → VMID**. This adds an approximately 15.9 Hz high-pass well below the main corner and prevents accumulated downstream amplifier DC offsets from becoming detector thresholds. Use a low-leakage, low-microphonic capacitor; exact C0G/film package availability and space need checking. The model assumes 10 pF detector/trace loading. Comparator bias/leakage and startup charging still create baseline error; this circuit is not an active DC servo.

### F. Gain, swing and noise results

`Gnom = 11 × 34.888 × 1.15 × 2.24 = 988.6 V/V = 59.90 dB`.

The new finite-GBW model including connector ESD, 5.1 kΩ current limiting, and recentering gives **944.2 V/V at 1 kHz**. A 1 kHz sine therefore scales as follows; spike peaks require their actual waveform response.

| Input | Predicted detector swing at 1 kHz |
|---|---:|
| 20 µVpp | 18.9 mVpp |
| 50 µVpp | 47.2 mVpp |
| 200 µVpp | 188.8 mVpp |
| 500 µVpp | 472.1 mVpp |
| 1 mVpp | 944.2 mVpp |

Assuming a conservative usable 0.3–2.7 V window, 1 mVpp has useful nominal headroom. This does not establish saturation recovery. The 7.2 mVpp Neuralink maximum input would clip at this gain; matching it would need a much lower gain mode (at most about 333 V/V for 2.4 Vpp ideal swing), with a new detector accuracy tradeoff.

| Noise calculation, output RMS divided by 1 kHz gain | 300 Hz–7 kHz | 3 Hz–10 kHz |
|---|---:|---:|
| Modeled electronics | 1.92 µV | 2.05 µV |
| CH and REF source resistors combined | 3.19 µV | 3.37 µV |
| Quadrature total | 3.72 µV | 3.95 µV |

These predictions exclude comparator/threshold noise, VMID noise, DAC/reference noise, interference, cable coupling, and overload. Typical amplifier noise figures are extrapolated from datasheet test conditions; they are not a guaranteed 3 V worst-case model. The model uses 300 K, an assumed 7 pF effective amplifier input capacitance, and 0.5 pF connector-side ESD capacitance; it omits FFC capacitance. All-band modeled output noise, integrated 0.05 Hz–2 MHz and divided by 1 kHz gain, is about 3.97 µV including source noise. The 6 µV electronics requirement remains unchanged; ≤2 µV is a useful proposed design-margin goal, not a new accepted specification.

One 47 kΩ source alone produces 2.28 µV RMS over a rectangular 300 Hz–7 kHz band at 300 K. Include REF noise as well. A low-noise amplifier cannot remove electrode/source thermal noise.

Noise-free derivative-Gaussian input trials at 200 µVpp produce approximately 192, 183, and 161 mVpp for 0.5, 1, and 2 ms widths with the 7 kHz option. The two lobes are asymmetric after filtering. These are example templates, not measured biological spikes or detection-rate validation.

**Unresolved impedance constraint:** with 22 MΩ bias, ≥10 MΩ at 7 kHz allows only approximately **2.03 pF** shunt capacitance, before series-network corrections. The earlier 7 pF amplifier assumption gives only about 3.22 MΩ even before connector ESD or FFC capacitance. This candidate does not pass D-003. Measure cable/input loading and either redesign the input device/topology or explicitly agree a frequency-dependent loading requirement. Do not silently relax the specification. Cable capacitance and mismatch can degrade both attenuation and common-mode rejection.

## 5. Analog detector and MCU interface

Propose **one TLV3202 dual comparator per channel**, supplied from a compatible 3 V rail, with upper and lower thresholds around VMID. Combine its two active-high event outputs through logic OR into one EVENT input; never wire push-pull outputs together. This requires eight dual comparators and eight OR functions. Exact logic part and footprints remain open.

TI lists 5 mV maximum offset at 25°C and 6 mV over temperature for TLV3202 under the table conditions, approximately 1.2 mV typical built-in hysteresis, and 40 µA typical current per comparator. Recheck at the selected rail and operating temperature. [Datasheet, sections 6.6/6.7 and 8.1](https://www.ti.com/lit/ds/symlink/tlv3202.pdf)

At measured/model gain 944, 5 mV comparator offset equals **5.3 µV input-referred**, or **10.6 µV at half gain**. This provides a detector-based reason to start near 1000× rather than 500×. It does not make low-amplitude detection guaranteed.

Proposed initial thresholds are **VMID ±25 mV**, adjustable roughly ±10–100 mV. At 944×, 25 mV is a 26.5 µV input excursion. A candidate global threshold generator uses buffered divider nodes: 59 kΩ to 3 V and 1 kΩ to VMID for the upper level; 1 kΩ to VMID and 59 kΩ to ground for the lower level. Both ideally give ±25 mV. Provide resistor/trim substitutions and per-channel threshold trim footprints; actual trip voltages must be calibrated including comparator offset, hysteresis, input bias, and resistor errors. Global threshold settings alone cannot correct sixteen independent offsets.

For initial hysteresis evaluation, a 1 kΩ signal/reference feed and 1 MΩ positive-feedback path gives approximately 3 mV external hysteresis for a 3 V output swing, in addition to internal hysteresis. Upper and lower comparator connections differ; use TI's respective noninverting/inverting equations and calibrate both trip/release points. Do not drive hysteresis feedback directly into the shared analog output or global threshold buffer.

At 50 µVpp, the modeled large lobe for a 2 ms test spike is only about **25.7 mV**. A 25 mV threshold leaves almost no margin before noise and offset. Reliable 50 µVpp detection needs calibrated lower thresholds and false-positive testing; 20 µVpp remains stretch. A reasonable next experiment targets calibrated residual threshold error ≤2 µV referred to input, but this is an unverified objective.

Firmware sees only events: count on assertion, suppress the second lobe, and rearm after the event signal has returned inactive. Begin evaluation with **2 ms minimum refractory and 250 µs continuously inactive before rearm**; these values require spike-pair testing. Unlike the old sampled algorithm, inactive now means inside the comparator release window, not below a separately measured noise threshold. This logic can merge closely spaced spikes; report that limit. Test all eight simultaneous inputs during BLE activity and determine minimum captured pulse width. Provide footprints for pulse capture/holding if MCU latency testing requires them.

STM32WBA52 is the user-selected controller. **5 × 5 mm UFQFPN32 is a package candidate**, pending exact event/EXTI/timer, SWD, UART and RF pin audit. Keep its waveform ADC disabled. Retain a 2.4 GHz ceramic antenna, matching/tuning footprints, required antenna keep-out, clock and supply components per ST's reference design. The EM9304's 48 MHz crystal and JTAG requirements do not apply to this STM32 design. [ST product](https://www.st.com/en/microcontrollers-microprocessors/stm32wba52kg.html), [datasheet](https://www.st.com/resource/en/datasheet/stm32wba52ce.pdf)

## 6. Power, area and prototype limits

With all 36 proposed amplifier sections active, `36 × 538 µA ≈ 19.4 mA`, or approximately 58 mW at 3 V before output loads. Sixteen comparators add approximately 0.64 mA typical, before output switching. These extrapolated typical estimates are not worst-case current guarantees. The per-channel AFE allocation is in milliwatts, far above Neuralink's analog-pixel figure. Removing waveform conversion does not remove continuous analog power.

Illustrative battery sizing for a **25–35 mA battery-side average** and 80% usable capacity:

| Cell | Estimated runtime |
|---|---:|
| 30 mAh | 0.69–0.96 h |
| 50 mAh | 1.14–1.60 h |
| 100 mAh | 2.29–3.20 h |

This current range is an allocation for AFE, MCU/BLE, regulation and support; it has not been measured. Verify dropout, usable discharge capacity, radio bursts and recharge behavior. In particular, a 3.0 V LDO cannot remain regulated once its battery-derived input falls below 3.0 V plus dropout and switch loss; this may reduce usable 1S-cell capacity. Board 1 is USB powered and is outside this battery runtime calculation. Existing under-US$150 assembled-prototype constraint remains; use it as the working combined two-board budget until clarified, and obtain quotes before claiming it is met. No new procurement is authorized or performed here.

The 25–30 mm XY objective applies to CuraLink, not the fixture. Thirty-six amplifiers, sixteen comparators, passives, FFC, antenna keep-out, battery/WPT and debug access need an actual floorplan; fitting them has not been demonstrated.

## 7. Verification and release gates

1. Calibrate fixture amplitude with all branches attached; measure source resistance, noise and cable capacitance. Use a suitable low-noise measurement path for microvolt nodes.
2. Measure input impedance/loading and common-mode rejection. Resolve the unmet impedance target before layout release.
3. Measure each gain/filter stage, both gain options, noise spectra and integrated noise with quiet CH/REF sources. Keep source and electronics noise separate.
4. Exercise startup and ±100 mV steps; measure clipping duration and time until valid event counting resumes. Include DC-reset capacitor leakage and threshold settling.
5. Calibrate sixteen trip/release levels. Sweep amplitude, polarity, width, refractory spacing, noise and interference; report misses, false positives and duplicates.
6. Exercise selective stimulus/quiet channels and eight simultaneous events. Shared fanout is useful for matching and stress tests, but cannot emulate independent overlapping neural activity.
7. Verify event capture during BLE traffic, SWD/UART access, rail isolation, and battery current. Scope analog output and digital events together. Test exclusive CHARGE/RUN switching and keep AFE/BLE off while WPT remains present, including after charger termination.
8. Check input ESD/leakage, 5.1 kΩ fault-current and pulse rating, unpowered-input injection, and FFC hot-plug recovery using the complete cable/fixture.
9. Audit exact footprints and FFC orientation, antenna layout, power sequencing, and vendor amplifier/comparator transient models before a fabrication decision.

No firmware, PCB routing, manufacturer SPICE simulation, or hardware measurement was completed in this task. Reproducible linear analysis: [script](../../tools/analysis/analog_event_afe.py), [results](../calculations/analog-event-afe/results.json). The prior model is reused only for the documented linear amplifier/noise equations; no ADC quantization term or old software detection pass is included.

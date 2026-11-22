# EGRA and Meower reference audit for CuraLink

**2026-09-22 · Schematic and manual-layout handoff.** This records what the supplied files actually contain and how to adapt their useful ideas. It does not declare a finished KiCad schematic, electrical-rule check, routed board, or qualified protection level. CuraLink's current circuit proposal is [the two-board analog AFE design](2026-09-22-two-board-analog-afe.md).

## Sources and what they show

| Source | Verified observation | CuraLink use |
|---|---|---|
| [EGRA checkpoint PCB](https://github.com/zanebeeai/egra-og/blob/b915129b144de0e52f8daf5e31ab55e3a1aaabc2/egra-OG_1.before-routeplan-20260601_181915.kicad_pcb), commit `b915129`, and [HD-EMG interface schematic](https://github.com/zanebeeai/egra-og/blob/b915129b144de0e52f8daf5e31ab55e3a1aaabc2/HD-EMG-interface.kicad_sch) | The named PCB has 187 footprints, 217 net declarations, **zero routed segments/vias/zones and no Edge.Cuts objects**. FPC1 is a 34-contact footprint with 32 sensing pins and two unconnected contacts. `J_REF_BIAS1` separately carries reference, analog ground and bias. | Use its functional placement groupings and repeated input-net structure as an organization guide. Create a new eight-channel schematic and board outline rather than treating the checkpoint as a routable CuraLink PCB. |
| EGRA `R_TRODE_1`/`C_TRODE_1` and `R_TRODE_33`/`C_TRODE_33` PCB nets, cross-checked against its [README](https://github.com/zanebeeai/egra-og/blob/b915129b144de0e52f8daf5e31ab55e3a1aaabc2/README.md) | Each electrode has **4.7 nF from the FPC-side electrode net to AGND**, and then **4.7 kΩ series to ADS1299 input**. REF has the same pattern into `SRB1_BUS`; the bias output is separate through 100 kΩ. | Repeat the *matched CH/REF treatment* and source-isolation idea. Do not copy the 4.7 nF shunt or active bias-drive electrode into this 47 kΩ-source, 300 Hz–7 kHz system. |
| EGRA `D2` in the named PCB and [Comms schematic](https://github.com/zanebeeai/egra-og/blob/b915129b144de0e52f8daf5e31ab55e3a1aaabc2/Comms.kicad_sch) | TPD4E05U06 is wired to `USB_DP`, `USB_DN`, and DGND. It is **not** on an electrode line. | Evaluate the *part family* separately for low-capacitance connector ESD protection; do not claim EGRA already protected its electrode pins with this device. |
| [Meower hardware README](https://github.com/nikki-uwu/Meower/blob/c6f410268a16cf4e0ecb313ea7b957a4a2afa690/hardware/README.md) and [test note](https://github.com/nikki-uwu/Meower/blob/c6f410268a16cf4e0ecb313ea7b957a4a2afa690/hardware/Active_electrodes_testing_2025_10_17.md) | Meower uses an ADS1299-based EEG/BCI board, four-layer main PCB, accessible test points/pogo fixture, and explicitly probes both the applied electrode stimulus and amplifier output in frequency-response tests. | Provide equivalent test access and separate stimulus/AFE measurement. Its active-electrode and ADS1299 analog values do not set CuraLink's intracortical spike AFE. |

These are source design observations, not evidence that the EGRA or Meower boards satisfy CuraLink requirements. No source KiCad/EasyEDA files or footprints were copied into CuraLink. Meower's hardware is marked CERN-OHL-S-2.0 in its repository; a direct derivative would require a separate license review. The EGRA repository does not report a GitHub license in the inspected metadata.

## Why EGRA's input RC cannot be transferred unchanged

The EGRA capacitor is on the **connector side** of its series resistor. With CuraLink's 47 kΩ nominal source, assuming the downstream input is high impedance and ignoring cable capacitance, its 4.7 nF shunt creates:

```text
f ≈ 1 / (2π × 47 kΩ × 4.7 nF) = 720 Hz
|H(7 kHz)| ≈ 0.102, or −19.8 dB
```

At 200 µVpp, only about 20 µVpp of a 7 kHz sine would reach the AFE before its intended spike filter. This result is specific to CuraLink's 47 kΩ source model and the source-side shunt. The 4.7 kΩ EGRA resistor follows that node, so including it does not repair the attenuation. A 100 pF shunt on the same connector node would produce about 3.2% attenuation at 7 kHz with 47 kΩ; even that capacitance would violate the presently stated ≥10 MΩ input-impedance target. The current candidate therefore has **no nanofarad shunt on CH/REF at the connector**.

The old 10 MΩ-at-7 kHz target permits roughly 2 pF total input shunt capacitance with a 22 MΩ bias path. The proposed amplifier already exceeds that. FFC, ESD, contamination, and PCB capacitance make the target more difficult. Treat the target as an unresolved release gate, rather than crediting an ESD diode's low typical capacitance as a solution.

## CuraLink electrode-interface schematic specification

Draw one identical chain for each of **CH1–CH8 and REF**. Use separate `CHx_CONNECTOR` / `CHx_PROTECTED` / `CHx_AC` / `CHx_PRE` net names; give REF analogous names. The exact KiCad symbols, pin numbers, cable-facing connector and approved BOM still need capture and pin audit.

The updated [single-channel plus shared-REF linear netlist](../../hardware/design/afe-channel-linear.cir) gives element-level connections for the proposed input, gain, filters and detector coupling. It is a circuit representation for review, not an ERC-checked KiCad schematic or a vendor-model simulation; replicate the CH path eight times only after resolving the protection and loading gates below.

```text
18-contact FFC CHx
  ├─ low-C ESD path directly to local AGND at connector
  └─ 5.1 kΩ series current-limit candidate → 10 nF C0G AC coupling
                                        → preamp + input
                                               │
                                             22 MΩ
                                               │
                                             VMID

preamp gain: 1 kΩ to VMID, 10 kΩ feedback; GA = 11

REF: same ESD, series resistor, AC capacitor, bias and preamp values.
Later: matched differential HP/gain → two LP sections → DC reset
       → positive and negative threshold comparators → logic OR → EVENTx.
```

The proposed [TPD4E05U06](https://www.ti.com/product/TPD4E05U06) provides four low-capacitance ESD paths per package; **three packages** cover nine CH/REF lines with unused inputs handled per datasheet. Its published 0.5 pF capacitance is typical, leakage maximum is 10 nA, working standoff is 5.5 V, and the specified clamp is about 10 V at 1 A. This is a **candidate**, not a selected medical/electrode safety barrier or a 3 V precision clamp. Verify actual clamping waveform, return impedance, leakage at the operating bias/temperature, FFC capacitance and system-level ESD on the assembled fixture. [TI datasheet](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf)

The 5.1 kΩ candidate follows the clamp, helping limit input current on fast or incorrect-voltage events. [TI's TLV9064 datasheet](https://www.ti.com/lit/ds/symlink/tlv9064.pdf) states that its internal input protection needs current limited to 10 mA. Demonstrate the selected fault envelope and resistor pulse rating; do not treat 5.1 kΩ as a universal protection guarantee. It adds approximately **0.75 µV RMS** own thermal noise over an ideal rectangular 300 Hz–7 kHz band at 300 K, before transfer weighting. The revised linear model, including 5.1 kΩ and **0.5 pF typical** connector-side ESD capacitance on CH and REF, predicts **944.2 V/V at 1 kHz**, **1.92 µV RMS electronics noise** and **3.72 µV RMS electronics-plus-source noise** over 300 Hz–7 kHz. [Calculation output](../calculations/analog-event-afe/results.json). It still omits FFC capacitance, clamp nonlinearity, leakage, VMID noise, comparator noise, board parasitics and overload.

The FFC pin map remains the [proposed 18-contact assignment](2026-09-22-two-board-analog-afe.md) with ground between channel conductors and REF on pin 17. On the fixture board, each source branch terminates through its own nominal 47 kΩ resistor; quiet branches connect to the same quiet reference through the same source impedance. There is **no actively driven bias electrode** in the current CuraLink bench stimulus model. Wire grounds and REF distinctly. Place a source-node test point on the fixture *after attenuation and before each 47 kΩ resistor* and a suitable high-impedance probe point near the CuraLink connector to expose actual stimulus loading.

## Protection and manual-layout handoff

| Path / failure mode | Candidate provision to draw and check |
|---|---|
| FFC handling, ESD, miswiring | Place the low-C ESD array at the connector and give it a short, low-inductance AGND return. Follow with per-line current limiting and DC coupling, including REF. Mark pin 1/contact side on **both** boards and the cable. Check connector symbol–footprint mapping and mating geometry against exact vendor drawings. |
| High-frequency input loading | Leave shunt filter footprints available but normally DNP pending measured impedance/noise response; do not populate EGRA's 4.7 nF. Keep input traces short, clean and separated from LED/USB/BLE/WPT switching. Do not credit a guard trace until capacitance is calculated or measured. |
| Large DC step, hot plug, unpowered board | The coupling capacitor blocks steady DC but passes initial steps. Gate fixture output until board-2 rails and VMID are valid, blank event counts until all stages and thresholds settle, and test both plug orders. Review back-power paths through clamps and regulator outputs. |
| Battery, WPT and rails | Retain battery protection/charging, a hardware-controlled power disconnect, current-measurement points, local regulator decoupling and separate analog/digital rails. Under D-007, WPT CHARGE disables the AFE and BLE; validate mode transitions rather than charge-and-record. Ground return from ESD must not share a long path through the high-gain input region. Do not copy EGRA's ±2.5 V ADS1299 rails into CuraLink's nominal 3 V/VMID chain. |
| USB stimulus board | Use appropriate USB VBUS overcurrent and data-line ESD, plus its own digital/analog decoupling. USB shielding/ground strategy and injection of PC noise into the battery board require measurement. EGRA's D2 is a useful *USB protection example*. |
| BLE antenna / RF | Reserve ceramic-antenna keep-out and π-match/tuning footprints; test RF with actual battery, FFC and coil present. Keep RF and WPT switching currents away from the input and VMID area. No antenna performance is established by using a ceramic component alone. |
| First-board observability | Expose FFC-side stimulus, after-current-limit node, CH/REF preamp outputs, one node after differential HP, one after LP, comparator inputs/outputs, EVENT[7:0], VMID and rail test points or accessible pads. Provide SWD/reset/UART access, while avoiding long unterminated analog stubs. Meower's two-point electrode/output probe method is the measurement pattern. |

The two boards are **bench-only**. USB-connected stimulation is not a patient-connection safety architecture. No human/animal connection, stimulation safety, IEC qualification, or wireless-through-tissue reliability is claimed from this design.

## Review gates before manual routing or assembly

1. Redraw the CuraLink schematic with the nine protected CH/REF chains, input-value options, detector logic and named test nodes; annotate identical channel groups. Run ERC in KiCad and inspect net names/ground returns.
2. Resolve the ≥10 MΩ input-impedance conflict or explicitly revise the requirement based on measured cable/loading impact. Current values do not pass it.
3. Calculate worst-case surge/incorrect-voltage current, series resistor pulse stress, op-amp input injection, protection leakage and clamp capacitance. Keep ESD and continuous-fault ratings distinct.
4. Check exact 18-contact FFC part, cable face/orientation and mechanical keep-out using vendor drawings. EGRA's 34-contact connector is a topology reference, not a footprint substitute.
5. Simulate or bench-check the input, full gain/filter chain, comparator chatter/recovery and REF-common-mode behavior using manufacturer models where available. The current MNA result is linear only.
6. Draw placement regions for FFC/ESD, nine preamps, REF fanout, HP/LP sections, comparator/threshold group, VMID/rails, STM32WBA52, antenna, battery/WPT, and debug access. Include antenna keep-out and assembly/test access in the size estimate.
7. After manual routing, run DRC/ERC and measure the specified tests on the complete two-board setup. This reference audit alone is not a fabrication approval.

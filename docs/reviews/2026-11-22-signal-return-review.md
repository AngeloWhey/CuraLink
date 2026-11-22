# CuraLink signal-path bias and return review

Reviewed **2026-11-22, America/New_York**. Read-only examination of the current D-024 **Candidate ADC schematic**, canonical component/net sources and retained LTspice evidence. **No new ADS or LTspice electrical simulation was completed by this review.** The original accepted analog-event baseline is not silently replaced. The ADS workspace's `cell_2` is a coil/matching study, not the neural AFE.

## Result for the engineer building the next version

The modeled, powered AFE has intentional DC input returns and negative feedback; no amplifier input was found floating in the DC topology. Existing manufacturer-family LTspice runs support a valid nominal operating point and the intended gain/band. This is **not a clean-signal or fabrication signoff**: the unchanged input-impedance requirement is unmet, shared VMID coupling/recovery remains consequential, unpowered interfaces are outside the demonstrated protection boundary, and the PCB return geometry is unfinished.

The [machine-readable check](2026-11-22-signal-return-review.json) records the 36 amplifier paths, eight matched input/ADC interfaces, REF/VMID connections, source hash and dated results. The companion [netlist consistency check](2026-11-22-netlist-consistency.json) compares those models against the current CAD sources.

That independent static consistency check passed **236 physical passives**, **36 amplifier units** and **598/598 targeted physical schematic pins** against the canonical source/XML/native schematic. The full source-to-XML transfer has **1,137 matching pin states** across 446 physical references, including 48 intentional NC pins. Source/extraction, seven retained snapshot and four model-file hashes also match. The source's 41 DNP display suffixes and 15 ESD NC placeholder translations are intentional representation changes, not net/value mismatches. This verifies which saved circuit the earlier simulations describe; it does not revalidate the manufacturer's pin definitions or perform new ERC, DC/AC analysis or PCB extraction.

## DC paths that are present

| Region | Checked connection | Conclusion / boundary |
|---|---|---|
| Eight CH inputs | FFC → 5.1 kΩ → 10 nF → CHx_PLUS; each CHx_PLUS has its own 22 MΩ return to VMID. | The series capacitor blocks settled external DC while the bias resistor establishes the amplifier input's DC voltage. The approximate bias-only RC is 0.22 s, not an instant startup. |
| Shared REF input | R1145 / C1057 / R1146 repeat the channel's 5.1 kΩ / 10 nF / 22 MΩ topology; REF_PRE has its own gain-11 preamp. | REF is not an unbuffered common electrode wire directly joining all CH inputs. Its loading/noise is nevertheless shared by all channels. |
| Gain-11 preamps | 1 kΩ from the negative input to VMID and 10 kΩ output feedback. | Powered nominal bias and feedback paths exist for all nine preamps. |
| Differential high-pass stage | Every channel has separate CH and REF 10 nF / 51.1 kΩ branches, 1.818 MΩ output feedback and a matched 1.818 MΩ positive-input return to VMID. | With capacitors open at DC, the positive input remains biased and the negative input retains feedback. Its DC noise gain is one; the signal gain of about 35.6 is not its settled-DC offset gain. |
| Two low-pass stages | Each positive input has a resistive path to the preceding stage; feedback gain networks return to VMID. | Their DC operating points are defined. The capacitor connections form the intended Sallen-Key network rather than arbitrary shunts to GND. |
| VMID reference | R540/R541 = 10 kΩ/10 kΩ from AVDD to GND; C529 = 2.2 µF. U109B follows VMID_RAW. Feedback senses VMID_BUF before R1149 = 47 Ω; C1058 = 4.7 µF bypasses VMID to GND. | The divider has 5 kΩ Thevenin resistance, 11 ms nominal raw-reference RC and 150 µA rail draw at 3 V. The 47 Ω isolates the buffer's direct capacitive load but creates signal-band common impedance. |
| Spare amplifier sections | U109C and U109D are followers of VMID_RAW with output tied to their negative input. | The two powered unused sections are not left open-loop or with floating inputs. |
| MCU ADC interface | All eight AFE outputs drive ADC_IN through 150 Ω; each ADC_IN has 470 pF to GND. | These are single-ended MCU ADC nodes centered near VMID; their capacitors intentionally return to ADC ground, not VMID. Actual SAR sampling, reference noise and power-off injection are separate tests. |

The resistor-only graph check opens all capacitors, treats powered amplifier outputs/supply nodes as DC anchors and verifies each amplifier input's return plus output-to-negative-input feedback. It is a topology check, not a proof of loop stability, output drive or operation with a missing rail.

Source examples: [canonical AFE netlist](../../hardware/rev-a/ltspice/afe/canonical-afe.lib) lines 2–6 (CH1), 202–208 (REF/VMID), 249–257 (U109/divider), 258–273 (ADC interfaces). [AFE source explanation](../../hardware/rev-a/afe/AFE-design-review.md) documents the exact topology and source/model assumptions.

## Existing simulation evidence, with its original date

The [2026-10-02 actual LTspice result](../../hardware/rev-a/ltspice/afe/results.json) uses original-equation TI dual-family models for each selected quad amplifier unit. It reports all **36 amplifier units valid**, AVDD = 3 V, VMID = **1.500596 V**, ADC equilibrium = **1.503360 V**, and **4.474 mA** modeled rail current including the divider. It excludes actual MCU sampling, control power, package coupling and RF interference.

The same dated runs give **969.744 V/V at 1 kHz** and a sampled peak-relative −3 dB band of **316 Hz–6.88 kHz**. A nominal 200 µVpp sine therefore produces approximately 194 mVpp at the ADC, and the 1 mVpp characterization sine produces approximately 970 mVpp around the 1.503 V center. That nominal sine headroom does not prove spike, blocker or offset-step behavior.

Steady −100…+100 mV external-offset sweeps remain centered after settling. Declared 100/10 GΩ coupling-capacitor insulation cases produce 2.05/18.36 µV total baseline changes. Those are model scenarios, not PCB-leakage limits. Offset steps pass through the capacitors initially and rail downstream stages; cold startup reaches a quarter ideal 3 V/12-bit LSB after **2.336 s**. A 2 s startup check failed. The proposed 3 s blank plus rail/baseline/clipping checks remains a Candidate mitigation, not a qualified universal delay.

## Open findings before a clean-signal release

| Priority | Finding | Required action |
|---|---|---|
| Requirement failure | The ≥10 MΩ across-band input requirement is unchanged. The declared 20 pF FFC fixture gives about **0.826 MΩ at 7 kHz**; even zero FFC is about 3 MΩ with the remaining modeled capacitance. | Resolve total input capacitance or explicitly reopen the requirement. Do not label a 22 MΩ bias resistor as the complete AC input impedance. At 7 kHz, 22 MΩ bias permits only about **2.03 pF** total effective shunt capacitance for a 10 MΩ magnitude target. |
| Shared-return qualification | The dated CH1-only study gives **−52.22 dB** worst quiet-channel coupling at 300 Hz, equivalent to **2.449 µVpp for a 1 mVpp aggressor**. The proposed −60 dB single-aggressor criterion is unaccepted. | Set an aggregate crosstalk acceptance criterion and qualify the midpoint's impedance, stability and simultaneous-channel/overload behavior. Keep canonical R1149 = 47 Ω until any alternative passes startup/recovery and stability checks. |
| Startup/artifact limitation | Offset steps clip and disturb quiet channels through VMID; the nominal full AFE needs much longer than the raw divider's 11 ms RC to settle. | Carry blanking/validity requirements and VMID/preamp/output test access into implementation. Test fast connection, large offsets and recovery before counting spikes. |
| Unpowered-interface protection | The AFE deck uses an ideal 3 V rail and capacitance-only ESD elements. FFC/debug interfaces can bypass the power switches/eFuses. The connector TVS is not a precision 3 V signal clamp. | Qualify off-state external drive, rail injection and enable/disable sequencing; restrict driven FFC/debug operation to the qualified powered conditions until then. |
| Physical return path | Schematic GND/VMID labels do not establish low-impedance copper returns. The recorded PCB lacks completed signal routing/filled planes and has unmerged/relinking work. | Complete the board connectivity/plane and sensitive-region review before fabrication. Keep low-level CH/REF/bias returns away from amplified outputs, clocks, BLE and charge currents. |
| ADC/model boundary | The 150 Ω / 470 pF interface has separate driver fixture evidence, but the full AFE operating-point/AC run has no actual multiplexed MCU SAR load or BLE/calibration activity. | Verify the chosen acquisition schedule, sampling charge, rail/reference disturbance, channel transitions and ADC/BLE continuity before adopting the ADC recommendation. |

See [signal-integrity evidence](../../hardware/rev-a/signal-integrity/README.md), [protection boundaries](../../hardware/rev-a/ltspice/protection-audit.md), [power sequencing](../../hardware/rev-a/power/power-design.md) and [PCB status](../../hardware/rev-a/pcb/README.md). Existing simulations and a schematic ERC pass do not qualify a routed return plane or package/board crosstalk.

## Buffer clarification

The neural-input path aims to sense a small voltage with minimal loading; the existing gain-11 preamp already performs that high-input-impedance function. Another buffer after the cable does not remove the cable's upstream shunt capacitance, nor eliminate the added buffer's own capacitance, noise, offset, current and drive limits.

The WPT path has a different objective: extract real energy from the fixed research-paper coil pair. A voltage buffer can obtain negligible input current while supplying an output from its **own power rail**. It cannot simultaneously make the coil see negligible real load and transfer the coil's received charging power to an arbitrary downstream circuit. A high-impedance sensing branch can monitor the receiver, while matching must still include the loaded rectifier and charging demand. This review selects no new buffer or topology.

## Handoff boundary

Retain the accepted fixed-coil constraint and CHARGE/RUN exclusion. The signal circuit has a defensible nominal powered DC/gain model, but the current evidence does not establish that the full CuraLink schematic is ready to build without the listed gates. Root's separate ADS power review owns fresh coil/matching/load simulation results; this report must not be described as new ADS validation of the AFE.

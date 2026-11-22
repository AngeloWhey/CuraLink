# MCU and RF placement review

Checked 2026-10-02 (client date, America/New_York). This is an engineering placement candidate; it is not a routed RF design, hardware measurement or fabrication release. The saved native board geometry and footprint source hashes are retained in the linked artifacts. The extractor also retains the observed host clock separately because it disagreed with the client date.

## Concrete result

An actual 80 × 74 mm four-layer PCB now exists. The initial layout separated the AFE rows, power area and MCU area, but put the two radio supply bypass capacitors about 8 mm from their respective MCU pins and put several ADC test points 11–22 mm away. The separate MCU candidate relocates all 59 acquisition-page parts plus C410/C411, retaining every net and physical pin. It leaves all original routing out of the candidate copy so the parent can regenerate copper after applying the deterministic overrides.

- Initial native rendering: [board-placement.png](../../pcb/figures/board-placement.png).
- Candidate native rendering: [mcu-local-placement.png](../../pcb/figures/mcu-local-placement.png).
- Editable candidate: [mcu-local-placement.kicad_pcb](../../pcb/mcu-local-placement.kicad_pcb).
- Deterministic placements and measurements: [mcu-placement-overrides.json](../../pcb/mcu-placement-overrides.json).
- Independent native inspection: [mcu-local-validation.json](../../pcb/mcu-local-validation.json).

All 61 override positions agree with the reloaded native candidate within 0.000000 mm and orientation differences modulo360� are 0.000000 degrees. Native inspection finds **0 conservative same-side courtyard-bound overlaps**, 0 pad-transfer errors, all 446 physical references, all 48 intentional NC pads and a closed outline. It reports **446 inherited stale schematic paths** from the original source snapshot; the parent must rebuild the candidate into the canonical board with the corrected hierarchy paths. It therefore does not report a whole-board validation PASS. The candidate has no tracks or vias; 818 native ratsnest edges remain.

## Bypass placement

Values below are **signal-pad-center to physical MCU pin-center straight-line distances**, not routed lengths or electrical guarantees. Closest possible placement must also leave routing room, mask/copper clearance and local ground returns. The capacitor ground side still needs a short connection into a ground plane through local vias.

| Capacitor | Physical host pin / function | Initial distance (mm) | Candidate distance (mm) |
|---|---|---:|---:|
| C410 | U401.39: VDDRF | 8.058 | 1.172 |
| C411 | U401.42: VDDRFPA | 8.359 | 1.172 |
| C408 | U401.44: VCAP regulator output | 5.711 | 2.193 |
| C409 | U401.38: VDDHPA regulator output | 3.277 | 2.030 |
| C406 | U401.6: VDDA 100 nF | 4.391 | 1.145 |
| C407 | U401.6: VDDA 1 µF | 9.758 | 2.193 |
| C401 | U401.11: VDD | 2.284 | 1.145 |
| C402 | U401.22: VDD | 1.747 | 1.145 |
| C403 | U401.35: VDD | 1.665 | 1.145 |
| C404 | U401.43: VDD | 2.942 | 1.249 |

C408 and C409 remain 2.193 mm and 2.030 mm respectively, so the proposed ~2 mm goal is not achieved strictly for every output capacitor. C407 is local bulk capacitance behind the closer C406. The candidate is a substantial improvement over the initial geometry; exact routed loops and hardware radio/ADC performance still need review. C408/VCAP and C409/VDDHPA are regulator outputs and must not be connected to the 3 V supply.

ST asks for close decoupling, short connections and careful RF ground returns. [AN5948 Rev4, §§7.1–7.9](https://www.st.com/resource/en/application_note/an5948-how-to-develop-rf-hardware-using-stm32wba-mcus-stmicroelectronics.pdf) and the exact [STM32WBA52CG datasheet](https://www.st.com/resource/en/datasheet/stm32wba52cg.pdf) support the pin functions and placement priorities. The approximately 2 mm planning goal is a project target, not a quoted ST pass/fail rule.

## Eight ADC channels

Every ADC test point is now next to its shunt capacitor node. Do not route a long branch back to the old debug-access location. Filter resistors, shunt capacitors and input pins should be connected as a direct path without high-speed digital or RF return currents crossing their local reference area.

| Channel | MCU pin | Cap-to-ADC distance (mm) | R output-to-cap (mm) | TP-to-cap branch distance (mm) |
|---|---:|---:|---:|
| 1 | 3 | 1.887 | 1.930 | 1.271 |
| 2 | 4 | 2.525 | 4.279 | 2.556 |
| 3 | 5 | 3.184 | 3.008 | 1.937 |
| 4 | 7 | 3.233 | 3.997 | 2.134 |
| 5 | 10 | 2.091 | 3.750 | 2.244 |
| 6 | 12 | 2.305 | 3.343 | 1.250 |
| 7 | 13 | 1.145 | 4.048 | 1.271 |
| 8 | 14 | 3.145 | 2.220 | 1.250 |

Shunt-to-input distances remain 1.145–3.233 mm; several channels exceed the initial ~2 mm objective because of the 0.5 mm MCU pin pitch, VDDA bypass space and the chosen 0402 courtyard clearances. All test branches are 1.250–2.556 mm by pad-center geometry. The 150 Ω / 470 pF network and acquisition timing are unchanged. A typical op-amp macro-model settling result does not establish rejection of 13.56 MHz pickup, BLE emissions or board crosstalk. [AN2834, §§3.2.11 and4.2.11–14](https://www.st.com/resource/en/application_note/an2834-how-to-optimize-the-adc-accuracy-in-the-stm32-mcus-stmicroelectronics.pdf) explains the input coupling/return risks.

## Clocks and RF still need manual attention

| Connection | Candidate pad-center distance (mm) |
|---|---:|
| HSE input: U401.41 → Y401.1 | 3.377 |
| HSE output: U401.40 → Y401.3 | 4.420 |
| LSE input: U401.17 → Y402.1 | 5.392 |
| LSE output: U401.16 → Y402.2 | 4.252 |
| LSE input load: Y402.1 → C421.1 | 1.500 |
| LSE output load: Y402.2 → C422.1 | 1.588 |

Route compact oscillator loops, keep their ground references local, and keep ADC and RF paths out of the crystal region. The HSE internal load-bank setting still requires an actual crystal/board-frequency check; there are no external HSE load capacitors in this design. LSE C421/C422 remain initial load values. [AN2867 Rev24, §7.1](https://www.st.com/resource/en/application_note/an2867-guidelines-for-oscillator-design-on-stm8afals-and-stm32-mcusmpus-stmicroelectronics.pdf) gives the routing and parasitic-capacitance guidance.

The MCU RF port requires a 63 Ω line to U402; its antenna-side interface uses 50 Ω. The provisional four-layer JLC stack does not reproduce the MLPF reference L3 ground geometry. The RF nets should remain unrouted until this adaptation is checked; no generic microstrip calculation qualifies the device pad/ground transition. The candidate also keeps the tuning network and optional coax branch in the RF area. The diode/charging audio-frequency simulations provide no RF-layout proof. [MLPF-WB-04D3 datasheet](https://www.st.com/resource/en/datasheet/mlpf-wb-04d3.pdf), [AN6335 §6](https://www.st.com/resource/en/application_note/an6335-mlpfwb-and-mlpfnrg-pcb-design-guidelines-and-reference-hardware-stmicroelectronics.pdf).

The saved antenna rule area is exactly x=73.5–80 mm, y=0–6.5 mm. AE401 is at (78.3,2.7) mm, +90°; pad1 faces inward at y=4.4 mm and isolated mechanical pad2 faces the edge at y=1.0 mm. Ground, buried copper, battery and WPT-coil intrusion into the antenna region remain explicit layout checks. The all-layer exclusion is a project interpretation of the manufacturer corner clearance; it does not prove final tuning. [Johanson Rev4, pp2–3](https://www.johansontechnology.com/docs/3827/Antenna-2450AT18A0100001E-Rev4.0.pdf).

## U.FL solder-mask adaptation

The initial native DRC identified exactly two solder-mask bridge errors at J404. The official KiCad footprint includes an extra filled F.Mask rectangle from (-0.515,-0.940) to (1.575,0.940) mm. It exposes the region between the signal and shell lands. Hirose specifies a central area without conductive traces and permits insulating material there; it does not demand a shared mask window. The project library therefore removes **only that independent rectangle**, preserving all copper lands, the individual pad mask/paste openings, the central copper keepout and the rest of the source geometry. This is a specific footprint correction, not a global DRC waiver.

The reproducible change is in [prepare_pcb_footprints.py](../../../../tools/hardware/prepare_pcb_footprints.py); the untouched official source hash and adapted library hash are recorded in [footprint-assignments.json](../../pcb/footprint-assignments.json). The parent applies the same removal to the canonical native board before rerunning DRC. [Hirose U.FL maker drawing, p3](https://datasheet.lcsc.com/datasheet/pdf/ade8681cf25347ad817fa65440db6a2c.pdf?productCode=C88374), also preserved in [source-page image](ufl-r-smt-lcsc-p3.png).

## Reproduction

Use the workspace Windows Python to run `hardware/rev-a/pcb/render_board.py --checked-date 2026-10-02` for a read-only native snapshot through WSL, or its `--board`, `--snapshot` and `--output` options for a separate candidate. `--extract-only` runs directly under KiCad Python; `--draw-only` redraws the retained JSON without reading a changing board. The renderer records the PCB SHA-256 and refuses extraction if the source changes during reading. `place_mcu_local.py` creates deterministic geometry overrides from the initial snapshot; `apply_mcu_local.py` saves only the separate candidate copy.

Handbook and canonical circuit decisions remain the parent’s responsibility. These placement and mask changes are engineering candidates; no new part choice, firmware, measured SI guarantee or fabrication release is implied.

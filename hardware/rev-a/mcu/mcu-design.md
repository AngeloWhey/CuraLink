# CuraLink Rev A acquisition, MCU and RF schematic handoff

**Engineering recommendation · recorded 2026-10-01, America/New_York · not fabrication released.** The user authorized evaluating ADC versus comparator acquisition and producing a schematic. This file supports the parent schematic package; it does not assert that a previously proposed ADC configuration or any RF performance has been measured or accepted independently.

## Functional objectives and decision criteria

The main board must acquire eight neural-like channels, preserve the custom high-impedance low-noise AFE, let an engineer inspect waveform/filter/clipping behavior, output spike counts over BLE, and shut down during charging. The comparison prioritizes detection flexibility, first-board observability, practical LCSC sourcing, acquisition continuity, analog noise, average system power, and PCB area. The earlier no-ADC preference is explicitly being reconsidered under the user's current authorization.

| Option | Description | Advantages | Costs / risks |
|---|---|---|---|
| **WBA52CGU6 + internal ADC — recommended working schematic** | Condition eight analog channels and scan the existing MCU ADC; extract counts later in firmware. | Retains the established MCU family; replaces eight external comparator paths; adjustable thresholds and waveform diagnostics; nine external ADC inputs leave one spare. | ADC/driver/anti-alias work and BLE ADC ownership must be proven; no internal SMPS; current draw and runtime unmeasured. |
| WBA55CGU6 + internal ADC | Same acquisition idea with a newer SMPS-capable device. | Internal core SMPS is a real possible power improvement; current ST BLE examples explicitly target this part. | Same 7 × 7 mm body, different pin assignment/support circuit; extra SMPS layout/BOM; only one unit was visible in the checked LCSC listing; system benefit unproven. |
| WBA52 + external comparators | Keep analog event thresholds and count edges, with ADC unused. | Avoids continuous ADC and associated ownership work; low BLE payload and potentially low acquisition power. | Eight external channels of thresholds/hysteresis need parts, offset/noise/tolerance work; limited waveform observability and threshold flexibility. MCU has two internal comparators, so they cannot replace all eight external channels. |

The **WBA52CGU6 ADC architecture is the recommendation for this draft**, conditional on a bench continuity/power test with the selected WBA52 BLE stack. If that gate fails, reopen acquisition architecture before ordering rather than silently permit missed events. WBA55 can be evaluated as a separate support-circuit variant; it is not a footprint-compatible substitution. The WBA52KGU6 5 × 5 mm option sacrifices spare pins and has no verified LCSC stock in this handoff. Device/package facts come from [ST DS14127, Tables 2–3 and 24](https://www.st.com/resource/en/datasheet/stm32wba55ue.pdf).

## Exact parts and sourcing snapshot

Inventory is a point-in-time catalog observation, not a reservation or confirmation of assembler eligibility. Recheck the exact MPN, stock, import availability, tray/reel handling, quantity minimum and assembly library at purchase.

| Ref / role | Exact MPN | LCSC code | Visible stock on 2026-10-01 | Package |
|---|---|---|---:|---|
| U401 MCU | STM32WBA52CGU6 | [C19626860](https://www.lcsc.com/product-detail/C19626860.html) | 9 | UFQFPN48, 7 × 7 mm |
| U402 RF filter | MLPF-WB-04D3 | [C22378853](https://www.lcsc.com/product-detail/C22378853.html) | 192 | CSPG6, 1.6 × 1.0 mm |
| Y401 HSE | NX2016SA-32MHZ-STD-CZS-5 | [C843260](https://www.lcsc.com/product-detail/C843260.html) | 10,115 | 2.0 × 1.6 mm, 4 pads |
| Y402 LSE | NX3215SA 32.768KHZ EXS00A-MU00525 | [C528987](https://www.lcsc.com/product-detail/C528987.html) | 6,095 | 3.2 × 1.5 mm, 2 pads |
| AE401 antenna | 2450AT18A0100001E | [C17430588](https://www.lcsc.com/product-detail/C17430588.html) | 656 | 1206 ceramic |
| J404 optional coax | U.FL-R-SMT-1(80) | [C88374](https://www.lcsc.com/product-detail/C88374.html) | 82,165 | SMT U.FL receptacle |
| L401 tee, initial | LQG15HS2N7S02D | [C77108](https://www.lcsc.com/product-detail/C77108.html) | 25,600 | 0402 |
| L402 tee, initial | LQG15HS3N9S02D | [C77109](https://www.lcsc.com/product-detail/C77109.html) | 55,350 | 0402 |
| C423 tee, initial | 0402CG1R0C500NT | [C1550](https://www.lcsc.com/product-detail/C1550.html) | 817,800 | 0402, 1 pF C0G |
| C421/C422 LSE load, initial | 0402CG4R7C500NT | [C1569](https://www.lcsc.com/product-detail/C1569.html) | 469,200 | 0402, 4.7 pF C0G |

Alternative MCU STM32WBA55CGU6 is [C22387557](https://www.lcsc.com/product-detail/C22387557.html), with only one visible unit in the audited snapshot. The antenna name in some supplier records says Johanson Dielectrics; the primary RF datasheet is from Johanson Technology and must govern its geometry and pinout.

Ordinary bypass/filter/resistor values are specified in [mcu-components.json](mcu-components.json) and sourced by the unified [passive catalog](../passive-catalog.json). The selected 1 µF X7R and 470 nF X7R regulator/rail capacitors use 0603 rather than the originally proposed 0402. Exact footprints must follow the final catalog MPN. PCB copper test pads and solder jumpers have no purchased electronic component and are BOM-excluded.

## Complete MCU physical pad map

This is the **UFQFPN48 non-SMPS** assignment from DS14127 Table 24 and the [MB1863-WBA52CGA-A03 reference schematic, sheets 3–4](https://www.st.com/resource/en/schematic_pack/mb1863-wba52cga-a03-schematic.pdf). It includes all 35 GPIOs, four main VDD pads, special supply outputs and the exposed ground pad.

| Physical pad | MCU function | Net / disposition |
|---:|---|---|
| 1 | PB12 | NC; configure unused GPIO analog |
| 2 | PB11 | NC; configure unused GPIO analog |
| 3 | PA8/ADC4_IN1 | ADC_IN_1 |
| 4 | PA7/ADC4_IN2 | ADC_IN_2 |
| 5 | PA6/ADC4_IN3 | ADC_IN_3 |
| 6 | VDDA | AVDD_3V0 |
| 7 | PA5/ADC4_IN4 | ADC_IN_4 |
| 8 | PA3/ADC4_IN6 | ADC_SPARE |
| 9 | PB10 | NC; configure unused GPIO analog |
| 10 | PA2/ADC4_IN7 | ADC_IN_5 |
| 11 | VDD | DVDD_3V0 |
| 12 | PA1/ADC4_IN8 | ADC_IN_6 |
| 13 | PA0/ADC4_IN9 | ADC_IN_7 |
| 14 | PB9/ADC4_IN10 | ADC_IN_8 |
| 15 | PB8 | NC; configure unused GPIO analog |
| 16 | PC15/OSC32_OUT | LSE_OUT |
| 17 | PC14/OSC32_IN | LSE_IN |
| 18 | PC13 | NC; configure unused GPIO analog |
| 19 | PB7 | GPIO_TEST |
| 20 | PB6 | ACQ_MARKER |
| 21 | PB5 | NC; configure unused GPIO analog |
| 22 | VDD | DVDD_3V0 |
| 23 | PB4/USART2_RX | UART_RX_MCU |
| 24 | PB3/SWO | SWO_MCU |
| 25 | PA15 | NC; configure unused GPIO analog |
| 26 | PA14/SWCLK | SWCLK_MCU |
| 27 | PA13/SWDIO | SWDIO_MCU |
| 28 | PA12/USART2_TX | UART_TX_MCU |
| 29 | PA11 | NC; configure unused GPIO analog |
| 30 | PB2 | NC; configure unused GPIO analog |
| 31 | PB1 | NC; configure unused GPIO analog |
| 32 | PB0 | NC; configure unused GPIO analog |
| 33 | PB15 | NC; configure unused GPIO analog |
| 34 | PH3/BOOT0 | BOOT0 |
| 35 | VDD | DVDD_3V0 |
| 36 | NRST | NRST |
| 37 | RF | MCU_RF |
| 38 | VDDHPA | VDDHPA_OUT |
| 39 | VDDRF | DVDD_3V0 |
| 40 | OSC_OUT | HSE_OUT |
| 41 | OSC_IN | HSE_IN |
| 42 | VDDRFPA | DVDD_3V0 |
| 43 | VDD | DVDD_3V0 |
| 44 | VCAP | VCAP_OUT |
| 45 | PA10 | NC; configure unused GPIO analog |
| 46 | PA9 | NC; configure unused GPIO analog |
| 47 | PB14 | NC; configure unused GPIO analog |
| 48 | PB13 | NC; configure unused GPIO analog |
| 49 | VSS/EP | GND |

A null net in JSON means a real no-connect marker, not an invented global NC net joining pins together. PA3 is an accessible ninth ADC input with a 1 MΩ pulldown and observation pad; it is excluded from the normal neural scan. Keep unused GPIOs in analog mode without unnecessary pull currents.

PA12 uses USART2_TX and PB4 uses USART2_RX (AF3). PB4 also has the NJTRST alternate function: use **SWD**, not full JTAG. PA13/PA14 are reserved for SWDIO/SWCLK and PB3 for optional SWO. The channel set uses distinct EXTI indices if an external comparator fixture is evaluated later; that is not a populated onboard comparator fallback.

## Power, reset and clock connections

The schematic uses separate AVDD_3V0 and DVDD_3V0 with common GND. U401 VDDA pin 6 uses the quiet analog supply, bypassed by 100 nF + 1 µF. Its ADC reference is internally VDDA/VSSA; there is no independently driven VREF+ pin. Do not mistake WBA55 VDDANA for the ADC supply: it is a radio analog domain.

Four VDD pads each have a local 100 nF bypass; add 10 µF bulk. VDDRF and VDDRFPA each use DVDD_3V0 and a local 100 nF. **VCAP pin 44 is an internal core regulator output: 4.7 µF to ground, no external supply or other load. VDDHPA pin 38 is an internal PA regulator output: 470 nF to ground, no external supply or other load.** These connections follow DS14127 Figure 14 and MB1863 sheet 4. Keep the small regulator-capacitor loops tight and choose MLCCs whose effective capacitance/ESR meet the ST requirement.

Split-rail startup remains a hardware gate: while VDD < 1 V, VDDA must not exceed VDD + 0.3 V; after VDD reaches 1 V the rails may be independent. The datasheet gives a shutdown-only energy allowance below 1 mJ. A shared enable signal does not by itself establish rise ordering. Measure both rails and AFE output/ADC injection during RUN/CHARGE transitions; reopen the VDDA feed or driver shutdown if ordering cannot meet the condition. See [DS14127 §3.12.1](https://www.st.com/resource/en/datasheet/stm32wba55ue.pdf).

NRST has 100 nF to GND, an additional 10 kΩ pullup to DVDD and reset observation access. The MCU already has a permanent internal pullup. BOOT0 uses a 100 kΩ pulldown and an open-by-default solder jumper to DVDD. Confirm boot option bytes before relying on this for recovery. The pad-field reset source must be target-referenced open-drain.

Y401 is a 32 MHz, 8 pF-load crystal. Pads 1/3 connect OSC_IN/OUT; case pads 2/4 go GND. **Do not add external HSE load capacitors**: use the MCU's adjustable internal banks and qualify frequency trim. The [NDK family datasheet](https://datasheet.lcsc.com/datasheet/pdf/7d295f64f7c44230fecd37b1086251f1.pdf?productCode=C843260) specifies ±10 ppm initial and ±25 ppm temperature for STD-CZS-5. ST requires total BLE HSE error, including aging and load pulling, within ±50 ppm after trim and specifies this NX2016SA family in DS14127 Table 60.

Y402 is a 32.768 kHz, 6 pF-load crystal. Initial external load capacitors are 4.7 pF each. The calculation is CL = C1*C2/(C1+C2) + Cstray ≈ 4.7/2 + 3.65 = 6.0 pF, using ST's 3 pF typical equivalent internal parasitic plus an **assumed**, unmeasured 0.65 pF equivalent PCB parasitic. These parts are tunable initial values, not validated on CuraLink. From the [NDK family bounds](https://www.ndk.com/images/products/catalog/c_NX3215SA_e.pdf), ESR ≤70 kΩ and C0 ≤1.5 pF give calculated critical transconductance 4*ESR*(2πf)^2*(C0+CL)^2 ≈ 0.668 µA/V. Compare with ST's maximum supported critical-Gm values, rather than assume an arbitrary oscillator drive setting. Medium-high drive (1.70 µA/V limit) is a practical initial setting pending startup and ≤0.5 µW crystal drive validation. No resistor may be placed across LSE IN/OUT. Measure cold startup, frequency and sleep-clock accuracy.

WBA52 has no internal SMPS. Changing to WBA55 requires a distinct MCU pinmap and regulator support circuit; when using an SMPS-capable part in LDO-only mode without the switching inductor, ST requires VDDSMPS and VLXSMPS grounded. Do not connect a WBA55 inductor to the WBA52 VCAP footprint or treat unused WBA52 GPIOs as SMPS pads.

## ADC interface and timing design basis

Each AFE_OUT_n drives a **150 Ω series resistor and 470 pF C0G capacitor** to ground at ADC_IN_n. R401–R408 are Yageo RT0402BRD07150RL, LCSC C852539, 0402, 0.1%; C413–C420 are FH 0402CG471J500NT, C75274, 0402, 5%, 50 V. This interface isolates the final amplifier from switched ADC loading and provides local charge. Its isolated RC corner is calculated as 2.26 MHz; it is not the main anti-alias filter.

The earlier 47 Ω / 1 nF / approximately 1.2 µs interface failed the final-driver model's quarter-LSB settling criterion. The revised interface was checked with the adapted TI TLV9052 family model used for the final TLV9054 stage, both 0.2 ↔ 2.8 V preceding-channel steps, ADC sampling capacitances of 5/10 pF, resistor variation ±1%, capacitor variation ±5%, and an internal switch-resistance assumption of 1 kΩ. At 1.656 µs track time the worst simulated settling error was 24.26 µV, or 0.0331 ideal LSB at 3 V. Across the tested 1.5–1.8 µs track-time window the worst was 107.18 µV, or 0.1463 LSB. These are **typical adapted-family-model results**, not process-corner or hardware qualification; full-AFE vendor operating-point validation remains open. See the AFE [validation status](../afe/validation-status.json) and [ADC stress results](../afe/adc-stress/results.json).

The proposed acquisition arithmetic uses a **48 MHz ADC kernel and 79.5 sampling cycles**: track 1.65625 µs plus 12.5 conversion cycles (0.26042 µs) gives 1.91667 µs per channel and 15.3333 µs for eight channels. A 30 kS/s per-channel candidate gives 33.3333 µs frame periods and 240 kS/s total throughput. An exact 30 kHz trigger divides a 48 MHz clock by 1600; timer support and clock relationships still require configuration validation. The channels are multiplexed, so channel eight is nominally 13.4167 µs after channel one. At 16-bit storage the internal neural stream is 480 kB/s; BLE normally sends count bins and selected diagnostic captures.

WBA's sample-time selections are **1.5, 3.5, 7.5, 12.5, 19.5, 39.5, 79.5 and 814.5 cycles**. There is no 639.5-cycle setting. The temperature sensor requires at least 13 µs track time; at 48 MHz this requires 814.5 cycles, giving 16.96875 µs track and 17.22917 µs including conversion. Eight neural conversions plus one temperature conversion total **32.5625 µs**, leaving only **0.77083 µs** at 30 kHz before sensor startup, sequencing, ADC ownership, optional VREFINT reads and software costs. Do not claim that background radio temperature sampling fits continuously. At 40 kS/s the 25 µs frame cannot accommodate that combined sequence. Schedule and mark bounded calibration gaps or prove a different qualified schedule before releasing continuous count claims. These calculations are anchored to [ST's sample-time definitions](https://github.com/STMicroelectronics/stm32wbaxx-hal-driver/blob/c36d9aabc6068051ed27a3a683a6b4f35f04d815/Inc/stm32wbaxx_hal_adc.h#L740) and [DS14127 Table 86](https://www.st.com/resource/en/datasheet/stm32wba55ue.pdf).

48 MHz is an allowed **PLL1P ADC source** in Run/Sleep, subject to a valid PLL and the 55 MHz ADC limit. It does not establish autonomous Stop0 operation. An HSI16 route at 39.5 sampling cycles gives 2.46875 µs track plus 0.78125 µs conversion, or 26 µs for eight samples; this can fit eight-channel 30 kS/s acquisition in arithmetic but its timer/DMA, longer track-time waveform error, low-power current and calibration service still need verification. A temperature conversion with 814.5 cycles at HSI16 takes 51.6875 µs, requiring a scheduled gap. See the detailed [power and acquisition constraints](power-and-acquisition-constraints.md).

Calibrate the ADC after each power-up and retain suitable baseline/gain calibration. The advertised 12 bits are code resolution; ST lists ENOB bounds separately. Rail/reference noise, gain tolerance, clipping and source noise must be included in the actual AFE budget. The 3 V ADC reference and 1.5 V signal midpoint are separate concepts; do not create a fictitious MCU VREF pin or short the midpoint to VDDA.

## BLE ownership and low-power release gates

The current official CubeWBA v1.10.0 source, pinned at commit e455b860ceb52aaa0332a98f1e7a10bbd7014fc9, shows the WBA55 p2pServer enabling temperature-based radio calibration and the common temperature module acquiring, reading and releasing the ADC:

- [WBA55 app_conf.h, calibration macro line 460](https://github.com/STMicroelectronics/STM32CubeWBA/blob/e455b860ceb52aaa0332a98f1e7a10bbd7014fc9/Projects/NUCLEO-WBA55CG/Applications/BLE/BLE_p2pServer/Core/Inc/app_conf.h#L460).
- [temp_measurement.c, ADC access lines 69–101](https://github.com/STMicroelectronics/STM32CubeWBA/blob/e455b860ceb52aaa0332a98f1e7a10bbd7014fc9/Projects/Common/WPAN/Modules/temp_measurement.c#L69).
- [adc_ctrl.c, seven user/eight total rank helper limits](https://github.com/STMicroelectronics/STM32CubeWBA/blob/e455b860ceb52aaa0332a98f1e7a10bbd7014fc9/Projects/Common/WPAN/Modules/adc_ctrl.c#L39), [configuration changes](https://github.com/STMicroelectronics/STM32CubeWBA/blob/e455b860ceb52aaa0332a98f1e7a10bbd7014fc9/Projects/Common/WPAN/Modules/adc_ctrl.c#L547).

The **seven user ranks are a default helper limit reserving VREFINT, not a seven-channel hardware limit**. Its existing polling/reconfiguration flow is not an eight-neural-channel DMA backend. Inspect the exact selected **WBA52** stack release: the verified WBA55 example does not establish that its macro is enabled in every WBA52 port. Where the ADC is shared, establish a single owner and a bounded calibration service; do not allow the BLE helper to power off or reconfigure an active neural DMA sequence. The temperature sensor requires at least 13 µs sampling plus startup/conversion, so a background read cannot be assumed to fit any chosen scan schedule.

Before release, demonstrate eight-channel capture under worst planned BLE traffic, calibration events and RUN/CHARGE transitions, with no unreported overrun, rank reordering or sample gaps. If a bounded gap is consciously allowed, report it in capture/count validity rather than present counts as continuous. Do not disable radio calibration solely to avoid the issue without verifying ST-supported temperature/RF behavior.

ST documents autonomous ADC/GPDMA clock requests in Stop0 in its [low-power guidance](https://wiki.st.com/stm32mcu/wiki/Connectivity%3ASTM32CubeWBA_Low_Power_Management). Stop0 shuts off PLL; therefore the proposed 48 MHz PLL acquisition uses Run/Sleep. The HSI16 autonomous alternative is distinct and subject to the selected silicon revision and [ES0592 §2.2.12](https://www.st.com/resource/en/errata_sheet/es0592-stm32wba5x-device-errata-stmicroelectronics.pdf). Hardware clock requests do not prove that continuous acquisition has idle Stop0 current. Demonstrate the ADC timer, GPDMA request/transfer and SRAM destination continue as intended while the CPU sleeps. Measure average system current with the complete AFE, acquisition rate, count processing, connection interval/payload and TX power before claiming one-hour runtime or an advantage over comparators.

## RF connection and practical layout requirements

The wired path is MCU_RF → MLPF-WB-04D3 → selection link → antenna tee → ceramic antenna. U402 ball A1 is IN, A3 OUT; A2/B1/B2/B3 are all GND. The [filter datasheet §3.1](https://www.st.com/resource/en/datasheet/mlpf-wb-04d3.pdf) requires a **63 Ω MCU-to-filter line** and a **50 Ω filter-output line** with prescribed adjacent ground and short via returns. Use that layout, not a generic 50 Ω line for both. Layer thickness and return plane determine actual trace width; this handoff deliberately gives no unsupported width.

Johanson specifies corner mounting with ground clearance and a **series–shunt–series tee**. From the 50 Ω source toward the antenna, initial values are **C423 1 pF series → L401 2.7 nH shunt to GND → L402 3.9 nH series → antenna**. This is the topology shown in its evaluation layout and explicitly described in the [manufacturer mounting guide p7](https://www.johansontechnology.com/docs/2/jti-antenna-mounting.pdf); the guide identifies the legacy 2450AT18A100 part, which the current antenna datasheet identifies as this part's legacy number. For a bypass assembly, replace C423 and L402 with 0 Ω and leave L401 DNP; never place 0 Ω in the shunt position. The manufacturer explicitly says a client's board may need different values. Its [datasheet p3](https://www.johansontechnology.com/docs/3827/Antenna-2450AT18A0100001E-Rev4.0.pdf) must govern the antenna placement/keepout. The 25–30 mm CuraLink outline, battery, 13.56 MHz coil and housing are not the evaluation board, so these values do not demonstrate a match. Keep copper, coil/battery metal and ground out of the specified antenna region on every layer, and keep RF return current away from electrode/REF inputs. Pad 2 is electrically NC but must be mechanically soldered; never ground it.

R417 selects antenna by default. J404/R418 are DNP; remove R417 and fit R418/J404 for a cabled radio test. These must be physically arranged as a minimal-stub selection; a long open branch undermines the matching. Coax supports fault isolation, an external antenna and conducted checks if equipment later becomes available. It does not magically tune the ceramic antenna. No VNA is currently available, so qualify BLE performance across the required distance/orientations, in the final battery/coil enclosure, and retain the antenna-match uncertainty explicitly. A successful connection alone is not a radiation-efficiency or regulatory measurement.

## Import and release checks

The authoritative component/pad connectivity file is [mcu-components.json](mcu-components.json). Every MCU pad and RF ball is explicit; component reference ranges are U401+, R401+, C401+, Y401+, J401+ and TP401+. Root may split support/ADC/RF across sheets while preserving these nets.

Before board order:

1. Compare every symbol pin and footprint pad against the exact suffix/package drawing; especially exposed pad 49, CSPG A/B ball orientation, oscillator case pads, isolated antenna anchor and the project-defined U.FL pad numbering.
2. Run ERC on the connected parent schematic; verify no unintended net joining NC pins, power outputs driven by external rails, or two enabled RF branches.
3. Close passive MPN/LCSC fields and assembler eligibility. Validate capacitor effective value, resistor tolerance and RF part S-parameter/parasitic suitability.
4. Confirm VDDA/VDD sequencing, no electrode/AFE/debug phantom powering, and the hardware RUN/CHARGE interlock with all external tools connected.
5. Prove analog settling/anti-alias, eight-channel timing/ADC ownership, clocks and measured power/runtime; evaluate RF performance with actual layout/enclosure.

These checks distinguish a fully specified reviewable schematic from a fabrication-released or measured design. No firmware, PCB routing or released RF tuning is delivered by this subassembly handoff.


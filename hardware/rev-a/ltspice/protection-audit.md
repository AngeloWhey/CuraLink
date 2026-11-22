# Independent protection and physical-pin audit

Recorded **2026-10-02, America/New_York**. Scope: canonical AFE, MCU and power wiring; manufacturer limits; what the accompanying LTspice tests can establish. This is an engineering review, not hardware qualification. Canonical files were not edited by this audit.

## Material correction

The original U502/U511 TPS25200 mapping was electrically wrong: GND1/IN2/ILIM5/OUT6 disagreed with the selected **TPS25200DRVR** package. The correct DRV mapping is **OUT1, ILIM2, FAULT3, EN4, GND5, IN6, exposed pad7 GND**. The root integration repaired both canonical records during this audit. See [TI Rev F, Table 4-1, page 3](https://www.ti.com/lit/ds/symlink/tps25200.pdf) and [rendered manufacturer drawing](sources/tps25200-pin.png).

An ERC or exported-netlist comparison to the same canonical record cannot find a consistently wrong manufacturer pin assignment. Regenerate the schematic/netlist after this repair and compare physical pad functions to the manufacturer drawing independently.

Two further repairs are now reflected in the canonical power record: **D501 uses manufacturer A1/K2**, with anode on WPT_RAW and cathode on WPT_PROTECTED; **R511 changed from 1.1 Mohm +/-1% to 1 Mohm +/-1%**, using stocked LCSC **C26083**. The former resistor could reach 1.111 Mohm, exceeding the specified 1.1 Mohm resistor ceiling; the replacement reaches at most 1.01 Mohm. This repairs the resistor-range violation and **does not guarantee a 50 mA cell-protection ceiling**.

## Other power active pin maps

The current power JSON agrees with these exact package functions. Pin numbers below are physical pads, not SPICE subcircuit argument order.

| Part and references | Verified physical map | Primary evidence |
|---|---|---|
| BQ25185DLHR, U501 | 1 SYS; 2 BAT; 3 STAT2; 4 /CE; 5 GND; 6 TS/MR; 7 ILIM/VSET; 8 ISET; 9 STAT1; 10 IN; 11 EP GND | [TI Rev B, section 4, Table 4-1](https://www.ti.com/lit/ds/symlink/bq25185.pdf) |
| TPS7A2030PDBVR, U503/U512/U513 | DBV: 1 IN; 2 GND; 3 EN; 4 NC; 5 OUT | [TI Rev H, Figure 4-4/table, page 4](https://www.ti.com/lit/ds/symlink/tps7a20.pdf); [drawing](sources/tps7a20-pin.png) |
| TLV3012BIDBVR, U504/U505/U506/U507/U515 | 1 OUT; 2 V-; 3 IN+; 4 IN-; 5 REF; 6 V+ | [TI Rev C, Table 5-1, page 3](https://www.ti.com/lit/ds/symlink/tlv3011.pdf) |
| SN74LVC1G17DBVR, U508/U510 | 1 NC; 2 A; 3 GND; 4 Y; 5 VCC | [TI Rev Y, section 4, page 3](https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf) |
| SN74LVC1G04DBVR, U509 | 1 NC; 2 A; 3 GND; 4 Y; 5 VCC | [TI Rev AF, section 4, page 3](https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf) |
| DMP2035U-7, Q501/Q502 | SOT23: 1 G; 2 S; 3 D, matching the top-view terminal locations | [Diodes Rev 11-2, page 1](https://www.diodes.com/datasheet/download/DMP2035U.pdf); [drawing](sources/dmp2035u-pin.png) |
| AO3400A, Q503-Q510 | SOT23: 1 G; 2 S; 3 D, matching the top-view terminal locations | [AOS Rev 3.1, page 1](https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf); [drawing](sources/ao3400a-pin.png) |
| BAT54-7-F, D503/D504/D507/D508/D509 | SOT23: 1 A; 2 unused; 3 K | [Diodes Rev 34-2, page 1](https://www.diodes.com/datasheet/download/BAT54.pdf); [drawing](sources/bat54-pin.png) |
| BAT54C-7-F, D502 | SOT23: 1 A1; 2 A2; 3 common K | Same family drawing as above |
| BQ29737DSER, optional DNP U514 | 1 NC; 2 COUT; 3 DOUT; 4 VSS; 5 BAT; 6 V- | [TI Rev I, Table 5-1, page 3](https://www.ti.com/lit/ds/symlink/bq2973.pdf); [drawing](sources/bq2973-pin.png) |
| SS14, D501 | **Repaired canonical A1/K2 matches the manufacturer:** A1 WPT_RAW; K2 WPT_PROTECTED. | [onsemi SS12-SS19 family, numbered terminals and cathode band, page 1](https://www.onsemi.com/download/data-sheet/pdf/ss19-d.pdf) |

The MOSFET and BAT54 drawings show terminal locations rather than printed pin numbers; confirm the PCB footprint's standard SOT23 numbering and top-view orientation. D501's former CAD K1/A2 convention was opposite the manufacturer A1/K2 and has been repaired. Preserve this map when selecting its SMA footprint, and confirm the cathode band faces WPT_PROTECTED in assembly. This audit does not certify every imported footprint dimension or pick-and-place rotation.

## OVP boundaries in the actual netlist

The intended receiver path is `WPT_RAW -> D501 -> WPT_PROTECTED -> U502 -> CHG_IN`. The name **WPT_PROTECTED is upstream of the eFuse**: D501 provides reverse blocking; this node is not the clamped charger input. The control source is `PACK+ OR CHG_IN -> D502 -> CTRL_INPUT -> U503 -> CTRL_3V0`. Its receiver feed is downstream of U502, but its battery feed bypasses the RUN eFuse.

The RUN path is `PACK+ -> BAT_RUN -> common-source Q501/Q502 -> SYS_PRE -> U511 -> SYS_RAW -> U512/U513 -> AVDD_3V0/DVDD_3V0`. Both PMOS body diodes point from the external drains toward their common source, providing opposed diode paths when off. The control LDO, pack dividers and PMOS lie upstream of U511. The eFuses do not cover externally driven FFC, debug, test-point or 3 V rail faults.

| Fault or operating condition | Covered behavior | Boundary that remains |
|---|---|---|
| Receiver DC rises above its normal 5 V | U502 clamps/disconnects CHG_IN when correctly wired | RAW reservoir, D501, upstream components and divider still see RAW stress; RF board no-load voltage/temperature remains separate work |
| Receiver step or fast ramp | Output capacitor and eFuse response reduce the peak | A steady-state clamp is not a guaranteed transient ceiling; inspect CHG_IN and CTRL_INPUT peak versus their downstream ratings |
| RUN downstream short | U511 limits current, with thermal behavior | Cell current rating and faults upstream of U511 require separate protection; current limit is not the 20 mA charging setting |
| Wrong-voltage source connected as PACK+ | Main U511 may limit its own downstream path | U503, dividers and PMOS receive the wrong voltage first. A current-limited, correctly polarized 1S cell/emulator is a bench constraint, not whole-board OVP |
| LDO output failure or an externally driven 3 V rail | No independent 3 V overvoltage disconnect in this design | Input-side eFuse OVP does not establish a safe MCU/AFE rail after a regulator failure |
| Driven FFC/debug during CHARGE/off | Some series impedances limit current | These interfaces bypass both power eFuses and can back-power an unpowered rail |

[TPS25200 Rev F sections 5.3-5.6, 7.3.1 and 8.2.2.2](https://www.ti.com/lit/ds/symlink/tps25200.pdf) specify normal input 2.5-6.5 V, 20 V absolute input limit, clamp 5.25-5.55 V under the specified test, and OVLO 6.8-8.45 V. The quoted 0.6 microsecond response is typical. During response delay OUT can follow IN; capacitor/ramp/load dependence must be tested. R510's 300 kohm EN pull-up is explicitly supported by the internal EN zener. R511's repaired 1 Mohm setting remains too coarse to guarantee a 50 mA limit.

[TPS7A20 Rev H sections 5.1/5.3](https://www.ti.com/lit/ds/symlink/tps7a20.pdf) limit IN to 6.0 V normal/6.5 V absolute; OUT must also remain below the lesser of 6.5 V and IN+0.3 V. Compare transient peaks at the actual regulator pins, including the battery-fed U503. [DMP2035U page 1](https://www.diodes.com/datasheet/download/DMP2035U.pdf) specifies VDS 20 V magnitude and VGS **10 V magnitude**; its gate ESD protection does not authorize continuous gate overvoltage.

The selected BQ25185 charge regulation, input current management and its internal protections do not replace an independent, cell-qualified protection circuit. Optional U514/Q509/Q510 are DNP and their pack current thresholds are not qualified for the small cell. Do not describe them as populated battery protection.

## AFE input protection and DC rejection

Each channel and REF reaches a ground-referenced TPD4E05U06 **before** the 5.1 kohm series resistor. The downstream path is `FFC -> 5.1k -> 10nF -> amplifier input`, with 22 Mohm from that input to VMID. The DC-blocking capacitor removes settled input DC; it does not remove an input step at the instant of connection.

[TPD4E05U06 Rev O, Table 4-2 and section 5.4](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf): DQA channels are pads1/2/4/5, grounds3/8, NC6/7/9/10. Standoff is 5.5 V; breakdown is 6.5-8.5 V at 1 mA. Its 10 V/14 V forward-direction clamps are typical TLP values at 1 A/5 A with a 100 ns pulse. This is an ESD component, not a precision clamp to the 3 V analog rail. Its connector-side current does **not** flow through the downstream 5.1 kohm resistor.

[TLV900x Rev R section 7.1](https://www.ti.com/lit/ds/symlink/tlv9004.pdf) and [TLV905x Rev J section 6.1](https://www.ti.com/lit/ds/symlink/tlv9054.pdf) describe input rail diodes and require input current limited to 10 mA or less beyond the rails by 0.5 V. A 5.1 kohm path provides useful secondary current limitation, but a calculation using an assumed TVS clamp does not qualify an IEC pulse, a low-impedance sustained input fault, rail back-power or component pulse stress.

The input time constant is approximately `22M * 10nF = 0.22 s`; source/series resistance changes it slightly. A differential or common-mode input step initially couples through and may clip gain/filter stages before recovering. For example, a 100 mV channel-only step initially requests about 1.1 V at a gain-11 preamplifier before the later gain. Count validity must be blanked until the whole chain recovers. A provisional two-second interval is not a universal recovery guarantee.

An ideal `.dc` sweep opens the capacitors and can correctly show essentially unchanged centered outputs. It establishes settled DC rejection in that model; it cannot prove transient input fault survival. The AFE LTspice deck represents the TVS as capacitance only and fixes AVDD with an ideal voltage source. It therefore cannot substantiate clamp current, TVS heating or unpowered rail voltage.

## ADC and unpowered interfaces

The selected MCU's ADC reference is VDDA, tied to AVDD_3V0. With the analog function enabled, respect the active analog ceiling `min(VDDA,VREF+) + 0.3 V = VDDA + 0.3 V`; valid conversions are within 0-VDDA. General FT digital tolerance and an injected-current table do not make the ADC input a qualified clamp. See [ST AN4899 sections 5.2.2, 5.3.6 and 6.3](https://www.st.com/resource/en/application_note/an4899-stm32-microcontroller-gpio-configuration-for-hardware-settings-and-lowpower-consumption-stmicroelectronics.pdf) and the existing [MCU constraints](../mcu/power-and-acquisition-constraints.md).

[DS14127 Rev 10 section 3.12.1, accessed using the exact WBA52CG primary URL](https://www.st.com/resource/en/datasheet/stm32wba52cg.pdf) requires VDDA no higher than VDD+0.3 V while VDD is below 1 V at power-up; above 1 V the supplies may be independent. The shutdown energy allowance below 1 mJ concerns supply sequencing and does not waive input-pin limits. U515's digital-good qualification and shared AFE/ADC analog rail address ordinary sequencing; still check ADC capacitor charge and amplifier shutdown transients. Use a target-referenced, non-powering debug probe and avoid driving an unpowered MCU. ST currently serves the same DS14127 Rev 10 family document through the former WBA55UE URL and the WBA52CG URL; Table 1 explicitly includes STM32WBA52CG. This audit uses the selected-part URL to avoid variant ambiguity.

## Minimal actions and evidence required

1. Preserve the repaired TPS25200 and D501 mappings and R511 1 Mohm value; regenerate and independently recheck physical pads. D501 now matches manufacturer A1/K2. No additional power IC pin mismatch was found.
2. For the intended receiver fault envelope, plot both CHG_IN and CTRL_INPUT, plus SYS_RAW and both 3 V rails where applicable. Include the selected capacitors, minimum effective capacitance, source slew and representative load. Compare **peaks**, not only plateau voltage.
3. Explicitly bound the battery/emulator connection to a correctly polarized, current-limited 1S source. If arbitrary pack overvoltage must be survived, add protection ahead of every PACK+ branch and re-evaluate PMOS gate stress; U511 alone cannot provide it.
4. Keep input sources within the defined bench interface, disconnect/disable driven FFC and debug during off, and measure input-step recovery before enabling counts. If sustained arbitrary connector faults or powered-off active electrodes become requirements, add a qualified input-isolation/clamp/current-limit design and assess its leakage/noise tradeoff.
5. Treat ordinary AC/DC sweeps, macro-model OVP runs and ERC as evidence for their modeled conditions. ESD survival, unpowered back-power, battery fault thresholds, thermal behavior and final hardware peak voltages remain qualification gates.

Manufacturer PDFs and selected rendered pin drawings are retained in [sources](sources/). No battery, hardware measurement, firmware ownership test or fabrication release is implied by this audit.

# CuraLink four-input generator bench schematic

**Engineering variant dated 2026-11-22.** Four independent signal generators connect directly to the electronics board through four coaxial receptacles. The reference is local. This variant is for electrical bench signals only. Routing, RF matching on the intended PCB, hardware characterization and assembly release are open.

Open [curalink-rev-a.kicad_pro](curalink-rev-a.kicad_pro) in KiCad. The [15-sheet PDF](schematic.pdf) can be read without CAD. Sheets 6–9 show the four AFE channels, sheet 10 their shared devices, sheet 14 the coax input wiring and sheet 15 the charger-status and power changes. For transfer to Altium, use the [native KiCad XML netlist](curalink-four-coax.net.xml) as the pin-by-pin comparison after import. Each package needs a verified Altium footprint and pin-to-pad mapping before layout.

The [native placement board](curalink-rev-a.kicad_pcb) matches the 326 schematic references. Routing remains open with 499 unconnected items and two antenna land-to-edge DRC findings. The separate [low-capacitance candidate](../bench-four-coax-low-c/README.md) changes the five input stages to address the protected-input impedance target.

## Bench hookup

| Generator | Board receptacle and source resistor | Protected AFE boundary | Historical J301 pin | Downstream series protection |
|---|---|---|---:|---|
| 1 | J601 pin 1 → R601, 47 kΩ | FFC_CH1 | 1 | R1001, 5.1 kΩ |
| 2 | J602 pin 1 → R602, 47 kΩ | FFC_CH2 | 3 | R1019, 5.1 kΩ |
| 3 | J603 pin 1 → R603, 47 kΩ | FFC_CH3 | 5 | R1037, 5.1 kΩ |
| 4 | J604 pin 1 → R604, 47 kΩ | FFC_CH4 | 7 | R1055, 5.1 kΩ |
| Local quiet ground | GND → R605, 47 kΩ | FFC_REF | 17 | R1145, 5.1 kΩ |

The board has four Hirose **U.FL-R-SMT-1(80)** receptacles, LCSC C88374. Pads 2 and 3 connect to local GND on each. Place the 47 kΩ parts at the AFE end of the four feed traces to keep the high-impedance segment short. The retained ESD clamps, 5.1 kΩ series elements, 10 nF DC-blocking capacitors and 22 MΩ bias returns serve the downstream channel/reference inputs. VMID is the AFE's internal DC bias. Connect generator and scope returns to GND. [Hirose receptacle](https://www.hirose.com/product/p/CL0331-0472-2-80)

Use four **BAT WIRELESS BWIPX1-SMA-1.13L100**, LCSC C784403, 100 mm pigtails. Each has a first-generation snap-on coax plug to a standard female SMA bulkhead. Use male SMA instrument cables or BNC-to-SMA leads as applicable. Secure the bulkheads so moving cables do not load the SMT receptacles. R601–R605 use **0402WGF4702TCE**, C25792. [Cable drawing](https://datasheet.lcsc.com/datasheet/pdf/003fe9c94d80cdbd3e01151eb6983bb2.pdf?productCode=C784403)

Start with a nominal **200 µVpp spike**, 100–300 µVpp for the primary test range. Specify the voltage at the low-impedance side of R601–R604 and verify gain end to end. A 50 Ω generator plus a board 47 kΩ resistor presents approximately **47.05 kΩ** to its input. There is no 50 Ω shunt on the board. An example fixture uses a verified 60 dB, 50 Ω external pad per channel and a matched-load generator setting of **100 mVpp**. An ideal high-impedance receiver sees approximately **200 µVpp** before its 47 kΩ resistor, because the open-circuit generator voltage is twice the matched setting. Generators with a Hi-Z amplitude display use the open-circuit convention directly. Calibrate at the connector under the actual cabling/load and account for divider tolerance, bandwidth and the scope's noise floor. In crosstalk measurements hold all quiet generator outputs at defined zero with their source impedance connected. The reference's 47 kΩ models the four signal source resistances to first order. The source model excludes electrode capacitance, imbalance and drift.

## Population changes

The [fitted/DNP BOM](assembly-bom.csv), [omitted package list](removed-from-rev-a.csv) and [merged component-to-pin table](components-merged.json) define this variant. The former J301 and CH5–8 parts are absent. Its odd pins 9/11/13/15 formerly served CH5–8, the even pins and shield mounts were ground. The retained quad packages U101/U103/U105/U107 each service CH1–4 and U109 provides the shared circuitry. The retained input ESD packages are U110 and U112. The separate on-board U.FL J404 is the optional BLE test port and ships DNP.

The default lab-pack assembly uses **R501 DNP, R502 fitted, R542 DNP, R543 fitted**. R501 is a deliberate charging opt-in for a battery emulator or a qualified pack. Check the actual pack, charger settings and temperature interface before fitting it.

Availability, pin/function fidelity, electrical behavior and the cost of PCB changes drove the dated substitutions below. [Machine-readable stock check](stock-2026-11-22.csv)

| Circuit | Fitted choice and LCSC code | Design impact |
|---|---|---|
| U401 | ST STM32WBA52CEU6, C7543271 | Same WBA52 UFQFPN48 covered by ST's common pin table. CE provides 512 KiB flash and 96 KiB SRAM. Verify the link map, stack high-water mark and update storage against those limits. [ST datasheet](https://www.st.com/resource/en/datasheet/stm32wba52ce.pdf) |
| U107 | TI TLV9054IPWR, C2057744 | Same TLV9054 analog family, new PW TSSOP-14. Each former RUC pin maps to the next PW pin, with RUC 14 → PW 1. Positive supply at 4, ground at 11, outputs at 1/7/8/14. Keep bypass, output and sensitive-feedback loops local to the larger package. [TI pin table](https://www.ti.com/lit/ds/symlink/tlv9054.pdf) |
| U508/U510 and U610 | Nexperia 74LVC1G17GV,125 C6076 and 74LVC1G08GV,125 C282347 | 1.65–5.5 V SC-74A/TSOP5. Schmitt pin 1 NC, 2 input, 3 GND, 4 output, 5 VCC. AND pins 1/2 are inputs, 3 GND, 4 output, 5 VCC. Check interlock timing over actual RC and gate threshold tolerances. [Schmitt buffer](https://assets.nexperia.com/documents/data-sheet/74LVC1G17.pdf) · [AND gate](https://assets.nexperia.com/documents/data-sheet/74LVC1G08.pdf) |
| Differential stage | Viking ARG03BTC9103, C2686431, 16 pieces | Both paired 0.1% thin-film arms in each channel now sum to 1.820 MΩ. The feedback ratio rises **0.110%** from 1.818 MΩ. Measure gain and common-mode rejection per channel. [Viking resistor listing](https://www.lcsc.com/product-detail/C2686431.html) |
| C1058/C1068/C526 | Murata GRM188Z71A475KE15D, C913474 | 4.7 µF ±10%, 10 V X7R in 0603. Check effective capacitance at installed bias, temperature and the regulator's required output load. [Murata part model](https://psearch.en.murata.com/capacitor/product/GRM188Z71A475KE15%23.html) |
| AE401 | Johanson 2450AT18D0100001E, C7450310 | Four-terminal chip with feed on 1 and GND on 2/3/4. The [local land pattern](CuraLinkFour.pretty/Johanson_2450AT18D0100001E.kicad_mod) implements the vendor land dimensions and a 4 × 6 mm copper-pour/via keepout. [Johanson drawing, pp. 2–3](https://www.johansontechnology.com/docs/3791/Antenna-2450AT18D0100001E-Rev5.0.pdf) |

Place AE401 midway along a clear board edge with the 6 mm dimension pointing inward. Route the intended short top-layer feed and three ground escapes to the prescribed counterpoise beside the clearance. Keep other tracks, metal and planes away on every layer. The footprint forbids pours and vias inside this zone and permits the explicit surface connections. Its initial pi network uses R612 = 0 Ω series with both shunts C613/C614 empty. R417 selects the antenna branch, R418 and connector J404 initially DNP. ST's device-side MLPF-WB-04D3 provides the nominal 50 Ω side of the transceiver interface. The manufacturer's published antenna measurements used a 40 × 20 mm board. Verify radiated performance with battery, WPT assembly, enclosure and generator leads in place on CuraLink. Operating range, repeatable RSSI and packet-error testing can flag poor performance when a VNA is unavailable. These tests do not measure return loss. [Johanson antenna reference](https://www.johansontechnology.com/docs/3791/Antenna-2450AT18D0100001E-Rev5.0.pdf) · [ST RF filter](https://www.st.com/resource/en/datasheet/mlpf-wb-04d3.pdf)

## Verification and ordering boundary

KiCad 10.0.7 exported **326 packages and 849 expected pin/net or NC states**. Their assigned footprint numbers also passed the pad-set comparison. The schematic ERC reported zero findings. These checks exercise file transfer and connectivity. Probe the reference and bias startup, run a four-channel simultaneous replay and aggressor/quiet-channel sweep, and check crosstalk and charge-mode rail isolation on the routed board. [Native ERC and pin checks](native-verification.json)

The [dated stock check](stock-2026-11-22.csv) covers **72 distinct fitted catalog codes**, five additional DNP-only codes and the separate pigtail SKU. All fitted codes covered one unit at LCSC. The first quantity limit was **28 TLV3012BIDBVR for five sites per board**, enough for five boards before assembly attrition. LCSC listed 12 MCUs. JLC stock and LCSC immediate-ship counts are separate columns. This check covers the merged board including its manually fitted off-board thermistor. Budget the external receiver/rectifier parts, cell, tools and shipping separately. Inventory can change before assembly.

Regenerate the variant and PDF with `python build_variant.py` from this directory. KiCad's CLI can be set through `--cli` or `KICAD_CLI`. The builder reads the canonical Rev A parent files and the neighboring [telemetry mutation](../telemetry-variant/apply_telemetry.py). Refresh the date-stamped source records with `python check_stock.py`. Archive this directory with the parent Rev A footprint library and generation inputs when moving computers.

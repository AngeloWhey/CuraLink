# Critical MCU/RF/interface land-pattern audit

Date: **2026-10-02, America/New_York**. Five custom footprints are available in [CuraLink.pretty](../../pcb/footprints/CuraLink.pretty/). They load in KiCad 9.0.9 and their numbered pads, copper sizes and coordinates match the recorded land drawing: [verification JSON](critical-footprint-verification.json), [geometry/hash manifest](critical-footprint-manifest.json), [generator](build-critical-footprints.py). This verifies the generated geometry, not the assembly process, RF match or final routed PCB.

The maker PDFs supplied for each exact LCSC SKU were retained with hashes in [footprint-source-manifest.json](footprint-source-manifest.json). ST's LCSC-hosted MCU PDF is DS14127 Rev 4 and the filter PDF is DS14446 Rev 5; the currently published official revisions are respectively Rev 10 and Rev 6. The old/new MCU footprint drawing uses the same **A0B9_FP_V2** identifier and dimensions. The filter revision history reports Rev 6's change to the absolute-ratings table; the retained drawing is therefore identified by its actual revision rather than relabeled as a new PDF.

## U401 — STM32WBA52CGU6

Use **`CuraLink:STM32WBA52CGU6`**. This is the **non-SMPS, 48-pin UFQFPN, 7 × 7 mm** package, with ground exposed pad **49**, not the smaller WLCSP/UFBGA variants. Numbering runs down the left side 1–12, across the bottom 13–24, up the right 25–36, and right-to-left across the top 37–48, viewed from the PCB top. The pin-1 indication is the upper-left corner. [ST DS14127 Rev 10 §6.4/Fig. 41](https://www.st.com/resource/en/datasheet/stm32wba52cg.pdf)

ST's land pattern has **0.55 × 0.30 mm** peripheral rectangles at **0.50 mm pitch**. Their radial centers are **±3.375 mm**: inner copper edge ±3.10, outer edge ±3.65. The exposed pad is **5.60 × 5.60 mm**. See the retained [manufacturer drawing](stm32wba52cg-lcsc-p128.png). The official generic KiCad EP5.6 footprint instead has 0.875 × 0.25 mm peripheral lands at ±3.4375 mm, so it was not copied as an exact ST land pattern.

**Assembly assumptions:** 16 separate 1.13 mm square EP paste windows use about 65% of the EP copper area. This is an engineering starting choice derived from the corresponding official KiCad package's paste subdivision; it is not specified by the ST drawing. The footprint does not invent thermal-via drill positions or a fill process. Add ground/EP vias in the board with the fabricator's via-fill/tenting and stencil agreement. Confirm mask/paste, solderable EP and lead alignment before assembly release.

## U402 — MLPF-WB-04D3

Use **`CuraLink:MLPF-WB-04D3`**. The CSPG part is **1.00 mm wide × 1.60 mm long**, with columns A/B separated by **0.500 mm** and three rows separated by **0.577 mm**. It is not a generic square 0.5 mm BGA grid. PCB-top coordinates, in mm:

| Pad | x | y | Function/net |
| --- | ---: | ---: | --- |
| A1 | −0.250 | −0.577 | IN, `MCU_RF` |
| A2 | −0.250 | 0 | GND |
| A3 | −0.250 | +0.577 | OUT, `RF_50OHM` |
| B1 | +0.250 | −0.577 | GND |
| B2 | +0.250 | 0 | GND |
| B3 | +0.250 | +0.577 | GND |

The maker's **rendered Figure 15** specifies **0.320 mm copper diameter, 0.220 mm solder-mask opening, 0.220 mm paste opening**, with a 3 mil stencil. PDF text extraction reverses the label order, so use [the visual drawing](mlpf-wb-04d3-lcsc-p9.png), not the flattened text. The custom footprint creates a −0.050 mm radial mask margin and separate 0.220 mm square paste apertures. [ST DS14446 §2.1/Figs. 9–11 and §3.2/Fig. 15](https://www.st.com/resource/en/datasheet/mlpf-wb-04d3.pdf)

**RF adaptation remains open.** Figure 13 labels the reference ground as **internal layer L3**; Figure 14 uses a 3 mil L1–L2 dielectric and approximately 50 mil core to L3. Its top copper/ground geometry is part of the implementation. The drawing does not dimension a complete L2 exclusion polygon. A generic L2-ground microstrip at a different height is therefore not a verified reproduction of this filter reference. No guessed internal-layer keepout was embedded in the footprint. Retain the **63 Ω** MCU-side and **50 Ω** antenna-side requirements, then review the actual pad/ground fields and stackup. Root's provisional JLC stack is a different RF implementation; leaving these nets unrouted pending that review is appropriate. See [rendered Fig. 13/14](mlpf-wb-04d3-lcsc-p8.png) and [ST AN6335 §6/Fig. 13](https://www.st.com/resource/en/application_note/an6335-mlpfwb-and-mlpfnrg-pcb-design-guidelines-and-reference-hardware-stmicroelectronics.pdf).

The small mask-defined openings and stencil thickness need explicit fabricator/assembler capability confirmation. A general PCB clearance pass cannot establish solder volume, placement accuracy or acceptable RF ground geometry.

## AE401 — Johanson 2450AT18A0100001E

Use **`CuraLink:Johanson_2450AT18A0100001E`**. Manufacturer Rev 4.0 identifies **pad 1 FEED** on the left and **pad 2 NC** on the right in top view. Pad 2 must be soldered for mechanical anchoring on an **isolated copper land**, with no GND/net attachment. The [maker mounting drawing](johanson-antenna-rev4-p3.png) gives a 2.60 mm inner gap, 4.20 mm outer span and 1.60 mm land height; the generated lands are consequently **0.80 × 1.60 mm at x = ±1.70 mm**. The older generic KiCad antenna footprint's 1.2 × 1.8 mm pads at ±1.45 do not reproduce this drawing. [Johanson Rev 4.0 pp. 2–3](https://www.johansontechnology.com/docs/3827/Antenna-2450AT18A0100001E-Rev4.0.pdf)

**Placement/rotation rule:** assign a board-corner antenna clearance, not merely a courtyard around the two lands. The maker example shows a **6.5 × 6.5 mm** ground-clearance corner. Implement the project's all-layer copper exclusion there, preserving only the antenna feed and its isolated anchor as needed; the antenna keepout must not block its intentional feed while allowing unrelated tracks to cross. No battery, coil copper or cable metal should occupy that region. Surrounding grounded PCB area and housing still affect the match; this clearance alone does not qualify antenna efficiency.

For a provisional **64 × 60 mm** board with the antenna at its **top-right corner**, the corner clearance rectangle is x = **57.5…64 mm**, y = **0…6.5 mm**. A candidate center **(62.3, 2.7) mm**, rotation **+90° in KiCad**, places pad 1 toward the board interior and pad 2 toward the top edge; the anchor's outer land edge is then 0.6 mm from the edge. That 0.6 mm clearance and along-edge center position are engineering placement choices, not manufacturer-required dimensions. Check the actual transformed pads in the editor. Rotate/translate the corner rectangle with the entire antenna region when moving it to another corner; do not keep a centered 6.5 mm box fixed around the body. Do not claim the provisional larger ground plane and different feed geometry reproduce Johanson's evaluation board.

C423/L401/L402 remain the evaluation-board tee starting values. Do not substitute a 0 Ω part for the shunt L401; bypass uses C423/L402 = 0 Ω and L401 unpopulated. Preserve RF selector access and mark antenna tuning as an open gate.

## J301 — SHOUHAN FPC 0.5-18P HYH2.0

Use **`CuraLink:FFC18P_HYH2.0`** as a **candidate** with the manufacturer solder-land dimensions, and retain the explicit pin-orientation/actuator audit. The [exact maker drawing](ffc18-hyh2-lcsc-p1.png) gives **18 × 0.5 mm pitch**, **0.30 × 1.20 mm** contact lands and **1.80 × 2.00 mm** mounting lands. The centered contact coordinates are x = **−4.25…+4.25 mm**, y = 0. A 2.55 mm dimension from the left mounting-land outer edge to the first contact center gives mounting-land x = **±5.90 mm**. A 4.75 mm dimension from contact-land top to mounting-land bottom gives y = **+3.15 mm**. See [the enlarged PCB-pattern detail](ffc18-pcb-crop.png). [Manufacturer drawing supplied for C6364663](https://datasheet.lcsc.com/datasheet/pdf/49aea12409976e716898b25cdae6481e.pdf?productCode=C6364663)

**Unresolved conventions:** the generic PCB illustration labels the contact-center span `B`, whereas the mechanical table uses `DIMA` and `DIMB`; 18 contacts at the specified pitch constrain this span to **8.50 mm**, not 9.52 mm. The maker drawing does not label a physical contact “pin 1.” Left-to-right contact numbering and MP1/MP2 names are therefore explicit project conventions. Use that convention consistently on both boards, mark pin 1, and verify the actual cable and mating orientation by continuity before powered use.

The 12.45 mm housing width and 5.32 mm closed depth are given; the footprint's housing pose and courtyard are conservative engineering placement envelopes rather than a completely dimensioned actuator model. Keep room for cable insertion and latch travel and audit the part/sample against those envelopes. Do not choose a similarly named generic FFC connector solely by pitch.

## Y401/Y402 and optional J404

**Y401:** use **`CuraLink:NDK_NX2016SA_2.0x1.6mm`**. NDK's typical lands are **0.85 × 0.75 mm**, center pitch **1.35 × 1.05 mm**. Top-view pad 1 is lower-left, 2 lower-right, 3 upper-right, 4 upper-left; 2/4 are case grounds and 1/3 the crystal. The generic KiCad 2016 pad map is correct but has slightly larger/different-position lands, so an exact typical-land custom copy was created. [NDK drawing](nx2016sa-lcsc-p1.png), [manufacturer PDF for the selected SKU](https://datasheet.lcsc.com/datasheet/pdf/7d295f64f7c44230fecd37b1086251f1.pdf?productCode=C843260)

**Y402:** **`Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm`** has **1.00 × 1.80 mm** lands at x = **±1.25 mm**, matching NDK's recommended copper dimensions. The generic library numbers pad 1 on the right, opposite the drawing's convention. The two-terminal crystal is nonpolar and its electrical function is unchanged, but reflect the actual convention in assembly documentation. [NDK drawing](nx3215sa-lcsc-p1.png), [manufacturer PDF](https://datasheet.lcsc.com/datasheet/pdf/524bac56b55e65eca5bbcc5105004c56.pdf?productCode=C528987)

**J404:** **`Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical`** uses the maker's signal/ground pattern: signal **1.05 × 1.00 mm**, two shell lands **2.20 × 1.05 mm**, with **1.90 mm inner shell gap**. Signal is pad 1; the official KiCad footprint calls both shell lands pad 2. Root should rename one shell to **3** in the project copy to match the canonical 1/2/3 pad convention, with 2/3 both GND. Preserve the maker's internal no-conductive-trace region and the footprint's keepout. [Hirose drawing](ufl-r-smt-lcsc-p3.png), [maker catalog for the selected (80) SKU](https://datasheet.lcsc.com/datasheet/pdf/ade8681cf25347ad817fa65440db6a2c.pdf?productCode=C88374)

## Review status

Land geometry and top-view numbering are documented above. Source drawings are rendered and retained; all five custom files parse and pass their recorded dimension/pad-set checks. Remaining release checks are FFC convention/actuator fit, the MCU EP via/paste process, filter mask/stencil capability and RF ground/stack adaptation, antenna keepout/nearby metal and tuning, and final routed-board inspection. No footprint audit result should be presented as a board-level RF or crosstalk measurement.

# Layout handoff for the four-channel MAX44280 candidate

Use the [MAX44280 PCB](../../bench-four-coax-low-c/curalink-rev-a.kicad_pcb) with its [sibling schematic and BOM](../../bench-four-coax-low-c/README.md). It has four U.FL inputs and five single SC70-6 preamps. U631–U634 serve CH1–CH4, U635 serves REF, and the five 22 MΩ input bias resistors return to VMID_RAW. The TLV9004 baseline has a different PCB in the adjacent project. The placement generator selects these variants explicitly and rejects a schematic population that disagrees with the selection.

The four-layer 80 × 74 mm PCB has **334 schematic-linked footprints, 873 named pad identities and zero routed tracks/vias**. Native readback verified all hierarchical component paths, each pin/net, all exported MPN/LCSC/DNP fields and the open R501 charge link. C1059 near U631 uses the original 0603 bypass; C632–635 use the 0402 C41851 for U632–635. Two unfilled inner GND plane outlines are present. KiCad reports **zero schematic-parity differences, 499 unconnected items and two copper-to-edge errors** at the grounded lands of the edge-mounted antenna. The antenna and fabrication clearance still need reconciliation. [Placement checks](board-checks.json) · [Full DRC](board-drc.json)

## High-impedance routing

For each input, keep the generator/coax side of the 47 kΩ low impedance and route the center conductor with a local return. Stitch each connector's two shell lands to ground at the connector. Route the sensitive chain from the receiving-board resistor through the ESD array, 5.1 kΩ limiter, coupling capacitor, 22 MΩ bias connection and preamp pin 1. U110 is downstream of the four 47 kΩ resistors. Its placement and connectivity require a separate resistor-pulse and transient-clamp check for connector ESD. REF has its own 47 kΩ return and protection array.

| Channel | After 47 kΩ, including ESD tap | Limiter to coupling capacitor | Coupling capacitor, bias and amp input |
|---|---:|---:|---:|
| CH1 | 1.98 mm | 1.81 mm | 2.19 mm |
| CH2 | 5.47 mm | 2.11 mm | 2.19 mm |
| CH3 | 3.82 mm | 1.56 mm | 4.68 mm |
| CH4 | 4.61 mm | 3.37 mm | 3.91 mm |
| REF | 3.64 mm | 2.10 mm | 2.97 mm |

Each distance is the largest straight-line separation between pad centers on that named net, taken from the saved PCB. A completed route can be longer, and a three-pad net needs a branch. CH2's post-resistor net, CH3's preamp input and CH4's complete chain merit placement refinement first. Keep fast digital nodes, the antenna, charger switching and amplified signals away from the five input paths. Budget **≤0.60 pF total additional protected-input board capacitance**. Pads, vias, optional probe lands, the stackup, nearby planes, package escape and coupled copper all contribute. Extract the complete input with the actual fabrication stackup, then measure the assembled impedance at the post-47 kΩ plane over 300 Hz–7 kHz. The geometric checks alone give no capacitance, isolation or noise guarantee. [Candidate signal model and acceptance](../../input-impedance/max44280/README.md)

For mechanical checks and initial routing, retain the inward-facing 4 × 6 mm antenna copper-pour exclusion along the right-hand edge. Check connector access, high-current loop placement, analog/MCU bypass loops and REF return against the board and fixture. Finish routing, plane fill, signal-integrity review, component rotation/land checks and clean fabrication DRC before assembly.

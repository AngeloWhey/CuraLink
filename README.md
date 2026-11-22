# CuraLink

Four-channel **benchtop neural-signal acquisition prototype** with a custom analog front end, STM32WBA52/BLE telemetry, and battery-buffered 13.56 MHz wireless charging. This repository is the engineering handoff for moving computers: editable schematics and PCB, ADS cells, circuit models, simulations, calculations, sourcing evidence and decision history belong together.

**Current build, 2026-11-22.** Use the [plain-text builder handoff](docs/BUILD-NEXT.txt), the [recommended low-capacitance electronics design](hardware/rev-a/bench-four-coax-low-c/README.md) and the [TX/RX matching schematics and parts](hardware/wpt/bench-rf/README.md). The revised bench board uses four U.FL inputs, a packaged rectifier and live BLE charger status. An externally charged qualified pack can power a signal-only test with WPT disconnected. The native designs and simulation evidence are engineering candidates. Routing, sourcing at order time, real-pack qualification, firmware and hardware validation govern release.

**Migration handoff and follow-up ADS review: 2026-11-22, America/New_York.** The complete migration batch was pushed and verified through a fresh GitHub/LFS download. A subsequent [fresh ADS review](hardware/wpt/ads/review-2026-11-22/README.md) checks the fixed paper coils, nonlinear power demand and translated AFE DC/AC behavior. That review used the earlier eight-channel hardware. The four-channel handoff above includes fresh KiCad checks, a dated BOM/stock audit and packaged-bridge power simulations. The design is an engineering **Candidate**, with no fabrication release, completed firmware or recorded CuraLink hardware measurements.

## Start here

1. Read the [engineering handbook](docs/engineering-handbook.md): accepted requirements, decision IDs, rationale and unresolved gates. Its status vocabulary governs the project.
2. Follow [moving to a new computer](docs/moving-computers.md) for Git LFS, tool setup, dataset restoration and file paths.
3. Open the [low-capacitance four-channel KiCad project](hardware/rev-a/bench-four-coax-low-c/curalink-rev-a.kicad_pro) to continue layout. Its [schematic PDF](hardware/rev-a/bench-four-coax-low-c/schematic.pdf) is readable without CAD. The TLV-only four-coax variant and original eight-channel board are comparison designs.
4. Open [ads/MyWorkspace_wrk](ads/MyWorkspace_wrk) and select **MyLibrary_lib → CuraLink_RX_BAS4002A_HB → schematic** for the packaged receiver. The [schematic PDF and HB results](hardware/wpt/ads/native-packaged-bridge/) and [full load/sensitivity study](hardware/wpt/ads/receiver-ic-review-2026-11-22/) can be read without ADS.

## Where the work stands

| Area | Current context |
|---|---|
| Signal specification | Four U.FL channels plus local shared REF. Drive each coax from a low-impedance calibrated generator and place its nominal 47 kΩ emulator at the board end. The retained input baseline is 200 µVpp over approximately 300 Hz–7 kHz. |
| Acquisition choice | The accepted historical baseline uses analog event detection with the MCU ADC unused. The current editable Rev A schematic **recommends ADC acquisition and digital detection** on the same STM32WBA52 family. That replacement remains Candidate under D-024; it is not a silently accepted requirement change. |
| AFE candidate | Five MAX44280 gain-11 preamps, four TLV-based filter chains and a separate high-value bias return. At 0.60 pF of added layout capacitance per input, the stressed model clears 10.70 MΩ across 300 Hz–7 kHz. At 1.00 pF it falls to 9.16 MΩ. Actual routed-board impedance is a release requirement. |
| Telemetry | STM32WBA52 with a ceramic BLE antenna; firmware, ADC/BLE continuity, antenna/RF implementation and measured power remain open. |
| Operating modes | RECORD powers the AFE and MCU from a qualified battery or emulator. During a wireless charge test, the AFE is off and the MCU reports charging status over BLE when the receiver can sustain it. |
| Charger/cell baseline | BQ25185 charger. The lab LiPo, connector and settings await identification. The historical 55 mAh cell and 20 mA/4.1 V example are separate from release limits. Battery-only tests can proceed independently. |
| Wireless receiver | Published Luo 13.56 MHz coil geometry and nominal 10 mm gap, Infineon packaged bridge and TPS70950 5 V LDO. Fixed-coil HB, nonlinear load and regulator transient results are available as tables. RF power capability, off-axis delivery, RF capacitor loss and heating remain to be verified. |
| Physical CAD | Separate four-channel KiCad schematic and 80 × 74 mm unrouted placement for the low-capacitance design, plus TX/RX matching/receiver sheets. Complete manual routing, RF and shield returns, antenna-edge clearance and assembly checks. |
| Manufacturing | The low-capacitance BOM had 73 fitted SKUs stocked at LCSC for one electronics board. The TX/RX parts and four cables were checked separately. Combined minimum-order parts cost US$102.85 on 2026-11-22. Cell, delivered assembly price and hardware verification remain open. |

## Files to open

| Path | Contents and role |
|---|---|
| [docs/engineering-handbook.md](docs/engineering-handbook.md) | Central decision record; read before changing the design. |
| [hardware/rev-a/](hardware/rev-a/README.md) | Editable KiCad project, all schematic sheets, PCB, project symbols/footprints, BOM and physical pin/net tables. |
| [hardware/rev-a/afe/](hardware/rev-a/afe/AFE-design-review.md) | AFE topology, gain/noise/loading calculations and model boundaries. |
| [hardware/rev-a/power/](hardware/rev-a/power/power-design.md) | Charging, hardware mode isolation, cell/temperature protection candidates, rails and power budget. |
| [hardware/rev-a/mcu/](hardware/rev-a/mcu/mcu-design.md) | MCU, ADC/BLE, clock, RF and antenna integration. |
| [hardware/rev-a/ltspice/](hardware/rev-a/ltspice/README.md) | Actual DC/AC/startup/recovery and bounded protection simulations, models, logs and result reports. |
| [hardware/rev-a/signal-integrity/](hardware/rev-a/signal-integrity/README.md) | Crosstalk/bias studies, sensitive regions and package/RF/layout audits. |
| [hardware/rev-a/pcb/](hardware/rev-a/pcb/README.md) | Footprints, placement, connectivity checks and incomplete routing status. |
| [ads/MyWorkspace_wrk/](ads/MyWorkspace_wrk) and [ADS migration notes](ads/README.md) | Native ADS workspace and `MyLibrary_lib`, large-dataset restoration and legacy model/display relocation. Open the whole workspace. |
| [hardware/wpt/ads/](hardware/wpt/ads/README.md) | ADS setup, model provenance, standalone fixtures, search/sweep results and charger-load guidance. |
| [2026-11-22 ADS verification](hardware/wpt/ads/review-2026-11-22/README.md) | Fresh 71.873% passive-link check, 48 authored-load HB cases, DC compliance and full AFE DC/AC evidence; explicit remaining build gates. |
| [hardware/wpt/models/](hardware/wpt/models/README.md) | Calculated Touchstone derived from published nominal coil parameters; not original measured S2P data. |
| [procurement/](procurement) and [Rev A procurement](hardware/rev-a/procurement) | Dated LCSC responses, sourcing checks and cost evidence. |
| [tools/](tools) | CAD generation/verification, analysis and packaging scripts. Read their output paths before running generators. |
| [output/](output) | Earlier handoff archive and checksum, preserved with Git LFS. Later source/report changes can supersede this historical snapshot. |
| [data/](data) | Eight historical ADS CSV captures from the secondary project folder, including `daa.csv`. |
| [archives/ads-cleanup-2026-10-09/](archives/ads-cleanup-2026-10-09) | Recovery ZIPs and manifest for earlier AFE/MOSFET scratch workspaces. They are historical backups, not the current ADS workspace. |
| [legacy/secondary-project-2026-11-22/](legacy/secondary-project-2026-11-22/HISTORICAL.md) | Older secondary-tree documentation kept separately from the current specification. Its former instructions are archived as `AGENTS.historical.md`. |
| [docs/context/](docs/context/README.md) | Four supplied chat handoff/rationale/power/proposal texts preserved as historical context. Their contents do not override current project instructions. |
| [migration/](migration) | File provenance/hash manifests and CAD, ADS and runner-portability audits. |

Large artifacts use **Git LFS**. Install it before cloning and follow the migration guide to fetch LFS objects and restore the compressed large ADS datasets. A GitHub source ZIP or a clone with missing LFS objects is not the complete handoff. Downloaded Java/FreeRouting runtimes are excluded; the project retains its routing workflow, source and evidence.

The [consolidation manifest](migration/consolidation-manifest.json) records imported artifacts and unavailable sources. All 14 explicitly referenced temporary CuraLink clipboard screenshots were already missing at migration; they could not be uploaded. The native schematics, circuit models, tables and saved project data are preserved separately. Historical vendor PSpice demonstration decks can still need simulator standard libraries; those dependencies are distinct from the authored LTspice fixtures and are recorded in the [CAD/dependency audit](migration/cad-audit.json).

The engineering record and subsystem reports distinguish accepted choices, candidates, failed diagnostics, successful nominal simulations and measurements. Keep those distinctions when continuing on the new machine; a saved `.raw`, `.ds` or PCB file is not, by itself, evidence that a test passed or a board is ready to order.

## Resume engineering

Start with the [current build issues and verification sequence](docs/BUILD-NEXT.txt). Portable four-channel signal results are in the [AFE closeout](hardware/rev-a/ads-closeout-2026-11-22/README.md). Packaged-bridge and RF results are in the [receiver review](hardware/wpt/ads/receiver-ic-review-2026-11-22/README.md).

Project assistants follow [AGENTS.md](AGENTS.md), preserve accepted baselines, and update the handbook when a material decision or verified result changes the design. The project has no hard completion deadline; the under-US$150 first-assembled-prototype and one-hour initial runtime remain objectives.

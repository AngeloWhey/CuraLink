# CuraLink

Eight-channel **benchtop neural-signal acquisition prototype** with a custom analog front end, STM32WBA52/BLE telemetry, and battery-buffered 13.56 MHz wireless charging. This repository is the engineering handoff for moving computers: editable schematics and PCB, ADS cells, circuit models, simulations, calculations, sourcing evidence and decision history belong together.

**Migration handoff and follow-up ADS review: 2026-11-22, America/New_York.** The complete migration batch was pushed and verified through a fresh GitHub/LFS download. A subsequent [fresh ADS review](hardware/wpt/ads/review-2026-11-22/README.md) checks the fixed paper coils, nonlinear power demand and translated AFE DC/AC behavior. Physical PCB checks remain dated October; stock was not refreshed. The design is an engineering **Candidate**, with no fabrication release, completed firmware or recorded CuraLink hardware measurements.

## Start here

1. Read the [engineering handbook](docs/engineering-handbook.md): accepted requirements, decision IDs, rationale and unresolved gates. Its status vocabulary governs the project.
2. Follow [moving to a new computer](docs/moving-computers.md) for Git LFS, tool setup, dataset restoration and file paths.
3. Open the [KiCad mainboard project](hardware/rev-a/curalink-rev-a.kicad_pro) for the current schematic/PCB candidate.
4. Open [ads/MyWorkspace_wrk](ads/MyWorkspace_wrk) in ADS for the preserved coil, matching and rectifier cells.

## Where the work stands

| Area | Current context |
|---|---|
| Signal specification | Eight channels plus shared REF; 200 µVpp nominal through nominal 47 kΩ source branches; approximately 300 Hz–7 kHz useful band. The separate DAC fixture fans one waveform out eight ways. |
| Acquisition choice | The accepted historical baseline uses analog event detection with the MCU ADC unused. The current editable Rev A schematic **recommends ADC acquisition and digital detection** on the same STM32WBA52 family. That replacement remains Candidate under D-024; it is not a silently accepted requirement change. |
| AFE candidate | Discrete TLV9004/TLV9054 stages, DC blocking, gain/filtering and local ADC interface. Nominal LTspice gain is approximately 970 V/V at 1 kHz. The existing ≥10 MΩ input-impedance requirement remains unmet; startup/offset recovery and shared VMID coupling need further work. |
| Telemetry | STM32WBA52 with a ceramic BLE antenna; firmware, ADC/BLE continuity, antenna/RF implementation and measured power remain open. |
| Operating modes | **CHARGE:** WPT present, recording electronics off. **RUN:** WPT absent, battery powers the system. Charge completion while the field remains present does not enable recording. |
| Charger/cell baseline | BQ25185DLHR, working 55 mAh Taisko cell, provisional 20 mA / 4.1 V charging. Cell global orderability, independent protection, temperature/current compatibility and usable runtime are unresolved. |
| Wireless receiver | Published 13.56 MHz coil R/L/k model. A BAT54 simulation Candidate reaches 5.08853 V / 124.287 mW into 208.33 Ω at 23.5 dBm; near-open load reaches 11.915 V. These are nominal ADS predictions, not a qualified charger. |
| Physical CAD | KiCad 9 source, 17 schematic pages and a provisional 80 × 74 mm four-layer PCB placement. Signal routing, plane fill, schematic-to-PCB relinking and merged MCU placement corrections are unfinished. No native Altium schematic/project/board was found in the recorded audit. |
| Manufacturing | LCSC sourcing is required. Mainboard inventory evidence is dated 2026-10-02; the receiver BAT54 check is dated 2026-10-09. Stock is not reserved or current, the cell is unqualified, and the under-US$150 assembled objective is unproven. |

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

Start with the [remaining power work](hardware/wpt/ads/README.md#remaining-power-work-in-order), the [PCB gates](hardware/rev-a/pcb/README.md#remaining-engineering-gates), and the handbook's open-work table. The immediate power work is realistic charger loading, raw receiver OVP/regulation, practical tuning-component losses and heat, cell protection, mode transitions and runtime. The broader mainboard work includes input loading, shared-bias/crosstalk, ADC/BLE operation, RF layout and final CAD/assembly verification.

Project assistants follow [AGENTS.md](AGENTS.md), preserve accepted baselines, and update the handbook when a material decision or verified result changes the design. The project has no hard completion deadline; the under-US$150 first-assembled-prototype and one-hour initial runtime remain objectives.

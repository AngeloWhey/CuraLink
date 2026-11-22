# Moving CuraLink to another computer

**Handoff prepared 2026-11-22, America/New_York.** This guide transfers the saved engineering state. It does not record new electrical verification, current component stock or a manufacturing release. The [engineering handbook](engineering-handbook.md) remains the authority for requirements, status and accepted decisions; [the root README](../README.md) is the project map.

A separate [same-day follow-up ADS review](../hardware/wpt/ads/review-2026-11-22/README.md) adds fresh fixed-coil power and translated AFE DC/AC evidence after the verified migration batch. Read it for the latest results; it leaves receiver regulation, input loading, shared bias and physical build gates open.

## 1. Clone with Git LFS

Install Git and Git LFS, then clone [AngeloWhey/CuraLink](https://github.com/AngeloWhey/CuraLink) into a writable project directory. The migration is published on `main`, preserving the repository's earlier history.

```powershell
git lfs install
git clone https://github.com/AngeloWhey/CuraLink.git
cd CuraLink
git lfs pull
git lfs fsck
git status
```

Git LFS keeps large artifacts in separate storage. A small text file beginning `version https://git-lfs.github.com/spec/v1` is an unresolved LFS pointer, not the intended binary. Run `git lfs pull` after authenticating if the clone did not fetch those objects. GitHub's ordinary source ZIP is not the recovery method for this complete project.

Two large ADS datasets are preserved compressed under [ads/large-datasets](../ads/large-datasets), with a [hash manifest](../ads/large-datasets/manifest.json) and [restoration script](../ads/restore_large_datasets.py). After `git lfs pull`, run these commands from the repository root with Python 3.9 or newer:

```powershell
python ads/restore_large_datasets.py --verify-only
python ads/restore_large_datasets.py
```

The tool uses the Python standard library, verifies the compressed transport and reconstructed SHA256 hashes, and restores datasets into their recorded `ads/MyWorkspace_wrk/data` locations. It refuses to replace different existing datasets. Compression preserves the original bytes; this step does not rerun simulation. Allow disk space for both the compressed copies and the restored originals.

For a full decoded-content integrity check without writing restored datasets, use `python ads/restore_large_datasets.py --verify-content`. The two original datasets require approximately 2.6 GB additional disk space when restored. [ADS migration notes](../ads/README.md) describe the exact transport and legacy-reference handling.

Keep the entire cloned folder. The KiCad top schematic references child sheets, the footprint table references a project-local library, and ADS requires the workspace/library hierarchy. Moving only one schematic file or copying a screenshot loses dependencies. Preserve native CAD and datasets as binary files; do not open/re-save them through a text editor.

Source work previously existed in two OneDrive trees: `Documents\ChatGPT\curalink` held the engineering record/mainboard work, and `Documents\projects\curalink\MyWorkspace_wrk` held the real ADS workspace. In the migrated repository the mainboard remains under `hardware/rev-a`, and the ADS snapshot is under `ads/MyWorkspace_wrk`. Older absolute paths in historical reports describe provenance; they are not instructions to recreate the old user's profile.

Before retiring the old computer, compare the uploaded commit and migration inventory with the local saved files. Unsaved changes inside an application are not filesystem files and cannot be included by Git. An earlier ADS audit found that `cell_1`'s saved OA differed from its generated netlist; the corrected new receiver cells are separate, deliberate copies.

The [consolidation manifest](../migration/consolidation-manifest.json) records eight imported historical ADS CSVs in `data`, scratch-workspace recovery ZIPs/manifests in `archives/ads-cleanup-2026-10-09`, older secondary-tree documentation in `legacy/secondary-project-2026-11-22`, and four supplied context texts in `docs/context`. These retain provenance without replacing the current engineering record. All 14 explicitly supplied temporary CuraLink screenshot filenames were no longer present; this missing-image list is recorded rather than implying they were backed up. Native circuit files are separate from those clipboard images.

## 2. Software used in the retained work

These are **historical tool versions**, not claims about the latest releases or a fresh cross-version compatibility test.

| Tool | Recorded version / purpose |
|---|---|
| Git and Git LFS | Download/version the complete project and fetch large objects; authenticate separately on the new machine for pushes. |
| KiCad | KiCad 9 native schematic/project/PCB and project-local libraries. |
| Keysight ADS | ADS 2026 Update 2 for native cells, standalone Python APIs, HB and datasets. A suitable simulator license is required to rerun. |
| LTspice | Windows 26.0.2 for the retained original-equation AFE and power analyses. |
| Python | Analysis and CAD scripts use packages including NumPy, SciPy, Matplotlib and pandas; some report/graphics scripts require additional imports. ADS code uses ADS's own bundled Python and installed `keysight` packages; KiCad board scripts require its `pcbnew` Python module. |
| Altium Designer | Desired downstream implementation tool, but no native `.SchDoc`, `.PcbDoc` or `.PrjPcb` is established by this handoff. KiCad-to-Altium import remains unqualified. |

Install applications from their suppliers and configure licensing independently. Application executables, license files and old-machine credentials are not portable design dependencies. Native source/report inspection can begin before rerunning simulation or regenerating CAD.

There was no single project-wide pinned Python environment in the original work. Use the relevant application's Python for its APIs and inspect each script's imports before installing analysis dependencies. Do not assume a generic `python` command imports `pcbnew` or the ADS SDK. Old commands containing a Codex-cache interpreter path are historical examples, not a requirement for the new computer.

## 3. Open the editable mainboard

1. In KiCad, open `hardware/rev-a/curalink-rev-a.kicad_pro`.
2. Open `curalink-rev-a.kicad_sch` from the project. Keep every accompanying `.kicad_sch` sheet in that folder.
3. Open `curalink-rev-a.kicad_pcb` separately to review the candidate placement.
4. Confirm the local `CuraLink` symbol/footprint libraries resolve. `sym-lib-table` references `${KIPRJMOD}/CuraLink.kicad_sym`; `fp-lib-table` references `${KIPRJMOD}/pcb/footprints/CuraLink.pretty`. Optional standard 3D models use the KiCad 9 installation through `KICAD9_3DMODEL_DIR`.
5. Read `hardware/rev-a/README.md`, `pin-net-connections.csv`, `bom.csv`, the PCB report and recorded audits before making changes.

The recorded PCB is **not routed or ready for fabrication**. The 2026-10-09 audit found 142 GND segments, 167 GND vias, no filled planes, stale footprint-to-schematic paths, and no saved imported signal-routing session. Separate MCU placement corrections have not been merged. A previous placement/connectivity check and schematic ERC pass do not establish final copper correctness.

Use KiCad 9 for the native baseline. Altium import must be tested against the actual installed versions, with a physical-pin, sheet/net, land-pattern and NC audit after conversion; do not assume supported conversion from the file extension alone. The earlier handoff ZIP/PDF predates later PCB/SI work, so prefer source files plus current reports.

## 4. Open the ADS workspace

In ADS choose the cloned **`ads/MyWorkspace_wrk`** as the workspace. Its library is **`MyLibrary_lib`**. In the ADS Main window select **Library View**, press **F5** (**View → Refresh**), expand the library/cell and double-click **schematic**. A stale Folder/File browser can hide cells added externally. This Library View workflow was verified in the original GUI.

The migration verified native OA file hashes and lossless dataset transport. A fresh native ADS open/netlist check on 2026-11-22 could not initialize because the ADS license was unavailable. The earlier GUI and electrical results remain October evidence, not a new-machine or November rerun. [ADS portability audit](../migration/ads-portability-audit.json) records that limit.

| Cell | What it contains | Evidence status |
|---|---|---|
| `cell_1` | Original coil/matching/rectifier work | Historical saved OA and generated netlist differed; retain as provenance. |
| `cell_2` | Passive coil/matching S-parameter test | Coil-link study; it is not the neural AFE. |
| `RX_LoadSweep_20261009` | Floating RX/full bridge, probes and original low-breakdown diode seed | Diagnostic only; that diode cannot qualify the required charging rail. |
| `RX_BAT54_LoadSweep_20261009` | Full manufacturer BAT54 model, candidate matching and resistor load | Fresh native-OA netlist actually simulated at HB31: 5.08853 V / 124.287 mW into 208.33 Ω, 23.5 dBm available RF, 13.56 MHz. |
| `RX_ChargerLoad_20261009` | Authored voltage-compliant static charger/control input demand | Saved and netlist-checked, **not electrically solved**; two standalone checks reached the simulator license user limit. It is not a BQ25185/cell/OVP macro. |

The BAT54 native single-point dataset is `ads/MyWorkspace_wrk/data/RX_BAT54_LoadSweep_20261009.ds`; select it in a Data Display. Standalone source decks, logs and results are under `hardware/wpt/ads/receiver-fixture-2026-10-09`. [Native-cell instructions](../hardware/wpt/ads/gui-setup/README.md) describe probes, measurements and disabled sweep controllers. [Charger-fixture guidance](../hardware/wpt/ads/charger/SDD-execution-guidance.md) lists the pending checks.

Start from the saved single operating point. Source/power/load changes alter the nonlinear rectifier impedance. The 5.09 V / 124 mW result uses ideal capacitors and nominal coil parameters, with only about 4.3 mW margin over the initial 120 mW allocation. At the same source power a 1 MΩ near-open load produces 11.915 V and about 132 mW modeled RX winding loss. These results expose raw OVP/thermal work; they do not demonstrate actual charging.

The original `cell_1` and `cell_2` retain absolute S2P model references in their unchanged OA bytes. If using those cells, change each S2P **File** parameter in ADS to `data/models/luo2023_coupled_coils_lumped_50ohm.s2p`, relative to the workspace; the exact model is bundled there. The same source also remains under `hardware/wpt/models`. It is calculated from the paper's nominal R/L/k, not downloaded measured data. The new `RX_*` cells use explicit coupled inductors and have no old absolute S2P reference. If an old associated-display link fails, open the included `cell_1.dds` or `cell_2.dds` manually. [ADS migration notes](../ads/README.md), [model provenance](../hardware/wpt/models/README.md) and [the ADS study](../hardware/wpt/ads/README.md) retain the details. The optional native relocation helper is unqualified because the new ADS license check could not initialize; do not interpret its presence as an executed repair.

## 5. Inspect and rerun LTspice evidence

Start at [the LTspice report](../hardware/rev-a/ltspice/README.md), then follow its AFE and power reports. The retained decks, vendor/adapted models, source manifests, logs, raw files, CSV and result JSON distinguish complete runs from failed diagnostics. Keep relative model/include files beside their decks.

Open an individual circuit deck in LTspice to inspect its sources, load and model boundary. The subsystem reports document batch commands using `-b -ascii`; run a copied case in its own output directory when preserving the original evidence. Read the solver log and confirm finite data and a valid operating point. Process exit alone is not a passed electrical test.

Recorded results include approximately 970 V/V AFE gain, steady-DC rejection with stated leakage scenarios, slow startup/offset recovery, shared-VMID crosstalk, and bounded eFuse fault behavior. The empty/incomplete shared-4.7 Ω startup/recovery evidence does not justify replacing canonical R1149 = 47 Ω. No validated BQ25185/cell LTspice charging model is included.

Historical TI/vendor PSpice demonstration projects are also retained. Some reference external simulator standard libraries such as `nom.lib`, `nom_pspti.lib` or Cadence's `anl_misc.lib`; those demonstration dependencies were not made self-contained by copying their directories. The authored LTspice analysis fixtures and their documented adapted model files are separate. Some diagnostic decks require their parent working directory for relative includes. Consult [the dependency audit](../migration/cad-audit.json) and the relevant subsystem report rather than treating an unresolved vendor demo as missing CuraLink schematic data.

## 6. Scripts and paths

Open the native saved designs before running rebuild scripts. `tools/hardware/build_reva.py`, `build_pcb.py`, `prepare_pcb_footprints.py`, routing/import scripts and packaging generators write or replace outputs; they are not required merely to inspect the transferred project. A generator's success does not prove that it reproduces every manual or later correction.

The active receiver fixture and initial native-cell setup now default to the repository's `ads/MyWorkspace_wrk`, rather than the former user's OneDrive path. Installation/workspace overrides are available:

| Variable | Scope / lookup |
|---|---|
| `CURALINK_ADS_WORKSPACE` | Use another ADS workspace instead of the repository snapshot. |
| `CURALINK_ADS_ROOT` | ADS installation directory; falls back to `HPEESOF_DIR`, then the recorded Windows ADS 2026 Update 2 installation location. |
| `CURALINK_KICAD_FOOTPRINT_DIR` | Standard KiCad footprint-library root for `prepare_pcb_footprints.py`; alternatives are `KICAD9_FOOTPRINT_DIR` and `KICAD_FOOTPRINT_DIR`, then the platform's recorded default. |
| `CURALINK_LTSPICE_EXE` | LTspice executable for the six active PowerShell runners and their three generator templates; otherwise resolve `Programs/ADI/LTspice/LTspice.exe` under the new user's `LOCALAPPDATA`. |

Set overrides in the shell that launches the application-specific Python if the new installation differs. For example:

```powershell
$env:CURALINK_ADS_ROOT = 'C:\Program Files\Keysight\ADS2026_Update2'
$env:CURALINK_ADS_WORKSPACE = (Resolve-Path 'ads/MyWorkspace_wrk').Path
```

These migration path changes were syntax-checked; they did not regenerate CAD or rerun circuit simulations. Review other original scripts' installed-tool paths and old `C:\Users\angel\...` references before running them. Some source manifests, historical scripts and logs intentionally retain those paths and hashes as provenance. For ADS scripts, use ADS's bundled Python and its licensed simulator; for KiCad scripts, use a Python capable of importing that installation's `pcbnew`.

Both standard-footprint preparation/verification helpers honor the KiCad overrides above; bundled project footprints are unchanged. [Runner portability evidence](../migration/runner-portability.json) records syntax checks, exact affected files and the explicit no-resimulation boundary.

The FreeRouting/Java toolchain was a local routing aid; it did not produce a saved completed route. Downloaded runtimes/installers are not part of the Git handoff. Installing or rerunning them is not a prerequisite for recovering the current CAD. The retained workflow describes how to obtain/configure them when routing work resumes. Preserve logs/partial studies as evidence rather than relabeling them as successful results.

The `output/curalink-rev-a-handoff.zip` archive and its checksum are retained through Git LFS as a historical snapshot. It is not a replacement for cloning the current tree and does not include every later change. Other imported historical/duplicate source material remains separate from the current mainboard/ADS paths; use the migration inventory to establish its origin.

## 7. Continue from the actual open issues

- **Architecture:** review/adopt or reject the ADC recommendation explicitly; preserve the accepted historical comparator baseline until then. Firmware, count format and acquisition/BLE continuity remain open.
- **Analog:** resolve the unchanged ≥10 MΩ requirement, shared-reference/midpoint coupling, recovery and real-device/PCB interference. Source/noise calculations are not measurements.
- **Power:** run/validate the authored charger-load checks, add raw receiver regulation/OVP, retune practical sourced capacitors/diodes under losses and tolerance, qualify heat, and test real charge-state/enable behavior.
- **Cell and sourcing:** verify a globally orderable compatible cell/independent protector, NTC/temperature and charging settings. Inventory figures dated October are not November availability.
- **Physical implementation:** repair schematic-to-PCB links, merge qualified placement changes, finish RF/signal routing and planes, then perform native DRC/connectivity, footprint/orientation and assembly audits.
- **System:** verify field-present shutdown including charge completion, field-removal startup, fault/backfeed/inrush and actual one-hour usable runtime. The under-US$150 assembled objective remains unproven.

Use [AGENTS.md](../AGENTS.md) for ongoing work. Significant accepted decisions and verified results update the handbook with the actual local date and preserved history. No hard completion deadline is established. If cluster jobs are introduced later, the standing user preference limits each batch allocation to one hour with saved progress and successful-completion dependencies between segments; this does not authorize creating a cluster workload for the hardware project.

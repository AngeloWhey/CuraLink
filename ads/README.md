# ADS workspace — computer migration

Packaged 2026-11-22, America/New_York. This is a saved-file migration snapshot; no new circuit simulation, part selection or electrical acceptance was performed.

## Open the schematics

Install **Keysight ADS 2026 Update 2** (the version used for these native files) and a valid license. In ADS, open the workspace directory **`ads/MyWorkspace_wrk`** from your clone. Choose **Library View**, press **F5** in the ADS Main window, and expand **MyLibrary_lib**. Double-click each cell's **schematic** view.

| Cell | Meaning |
|---|---|
| `RX_BAT54_LoadSweep_20261009` | Recommended starting point for the nominal receiver study: manufacturer BAT54 model, ideal candidate matching, HB31. Its saved 2026-10-09 result is approximately 5.08853 V / 124.287 mW at 23.5 dBm and 208.333 Ω. |
| `RX_ChargerLoad_20261009` | Authored voltage-dependent charger/control demand. Saved native schematic, but its DC/HB electrical checks were **not completed**. It is not a complete BQ25185, cell or protection model. |
| `RX_LoadSweep_20261009` | Diagnostic copy retaining the old low-breakdown diode seed. Do not treat it as a qualified 5 V receiver. |
| `cell_1` | Original working simulation, including historical settings and externally referenced Touchstone components. Its saved OA and last generated netlist have previously differed; preserve this provenance. |
| `cell_2` | Original passive coil/matching study. This is not the neural AFE. |

The current design explanation and earlier native verification are in [the receiver study](../hardware/wpt/ads/README.md), [native-cell guide](../hardware/wpt/ads/gui-setup/README.md), and [engineering handbook](../docs/engineering-handbook.md). Their old absolute paths identify the source computer; open the repository copy described here.

## Restore the two large datasets

All five schematics and the small validated BAT54 dataset are included directly. Two original large datasets are transported as lossless gzip archives under **Git LFS**:

| Restored file | Original bytes | Gzip transport bytes |
|---|---:|---:|
| `MyWorkspace_wrk/data/cell_1.ds` | 2,345,613,824 | 538,481,434 |
| `MyWorkspace_wrk/data/__simdata125462.ds` | 230,537,728 | 41,123,899 |

After cloning, install Git LFS, then run from the repository root:

```powershell
git lfs install
git lfs pull
python ads/restore_large_datasets.py
```

The restore script uses only the Python standard library, refuses to replace a different existing dataset, and verifies compressed and decoded SHA256 plus exact size. Python 3.9 or newer is required. If Windows uses the Python launcher, substitute `py -3` for `python`. Allow approximately 2.6 GB extra free disk space for the restored files. ADS's own bundled Python can also run the script.

For a full content-integrity check without writing datasets:

```powershell
python ads/restore_large_datasets.py --verify-content
```

Both archives were decoded and verified against the original dataset hashes during packaging, and this helper's decoded-content check passed. The [archive manifest](large-datasets/manifest.json) records transport and original hashes. These original datasets were preserved rather than relabeled as fresh receiver/charger validation. The existing `cell_1.dds` and `cell_2.dds` displays are also included; open them manually if an old associated-display link does not resolve.

## Legacy absolute references

`lib.defs` and `cds.lib` already use relative library paths and ADS's `$HPEESOF_DIR`. The workspace's DDS open-history file was changed only in this copy to relative filenames. Original native OA schematic bytes were retained exactly.

The old `cell_1` and `cell_2` OA files contain absolute references to:

`C:\Users\angel\OneDrive\Documents\ChatGPT\curalink\hardware\wpt\models\luo2023_coupled_coils_lumped_50ohm.s2p`

The exact file is bundled at **`MyWorkspace_wrk/data/models/luo2023_coupled_coils_lumped_50ohm.s2p`**, SHA256 `5d7d0e3f3f76fcda214ce6f942d97d65bd15c4bdb0ba97de36128dc6e6b653f6`. It is a calculated constant-R/L/k model, not a measured broadband Touchstone file.

If using either old cell, edit each matching `S2P` component's **File** parameter in ADS to **`data/models/luo2023_coupled_coils_lumped_50ohm.s2p`**. The `RX_*` receiver cells use explicit coupled inductors; no old absolute Touchstone file reference was found in those OA files. Some schematics also retain an old absolute associated-display filename; manually opening the included `.dds` file avoids that shortcut dependency.

An optional `relocate_workspace_models.py` helper prepares the same narrowly scoped File-parameter update using ADS's documented native APIs. Run it with ADS's bundled Python and a valid license, after ensuring the cloned schematics are not already open for editing. **It has not been executed/qualified:** ADS native-module initialization on 2026-11-22 failed with `ADS license not available`. Use the manual File-parameter change if needed. No raw binary OA path patching was performed.

Historical generator/simulator scripts elsewhere in the repository still identify the old ADS install/source-workspace paths. Review their `ADS_ROOT`, `WORKSPACE` and `SOURCE` constants before rerunning. Re-running a creation script that refuses an existing destination is not the way to open these already-saved designs.

## What was preserved and checked

- All 43 non-lock workspace files were copied and SHA256-verified before transport packaging; source hashes were rechecked after copying. All five native schematic OA files remain byte-identical in this snapshot.
- The two large datasets were gzip-compressed and fully decoded back to their exact original sizes/hashes; raw generated copies are omitted from Git by design and restored with the helper.
- The exact externally referenced Touchstone model is bundled. DDS history is relative; old OA model/display links are documented above.
- One stale machine/process `.cdslck` lock was excluded. ADS recreates locks; it must not inherit another computer's process ownership.
- No ADS installation, license file, credential or simulator executable is bundled. Installed libraries and license setup belong to the new computer.
- A fresh native ADS opening/netlist check was attempted but could not initialize because the ADS license was unavailable. Existing October native-netlist/simulation evidence remains linked above; it is not a November rerun.

The [source manifest](../migration/ads-workspace-source-manifest.json) records every copied file. The [portability audit](../migration/ads-portability-audit.json) records path changes, static dependency findings and the explicit native-check limitation. `inspect_workspace.py` can repeat the read-only native cell/netlist check once a licensed ADS installation is available.

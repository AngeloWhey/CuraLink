"""Repoint legacy Touchstone components in this cloned workspace using licensed ADS.

This helper changes only File parameters referring to the explicitly bundled model.
It does not alter connections, component values, original source workspace or results.
It is prepared from documented ADS APIs but could not be executed on 2026-11-22
because ADS reported that a license was unavailable.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE / "MyWorkspace_wrk"
MODEL = "luo2023_coupled_coils_lumped_50ohm.s2p"
ADS_ROOT = Path(os.environ.get("HPEESOF_DIR", r"C:\Program Files\Keysight\ADS2026_Update2"))


def main():
    model = WORKSPACE / "data/models" / MODEL
    if not model.exists():
        raise RuntimeError(f"Bundled model missing: {model}")
    os.environ.setdefault("HPEESOF_DIR", str(ADS_ROOT))
    sdk = str(ADS_ROOT / "tools/python/packages")
    if sdk not in sys.path:
        sys.path.insert(0, sdk)
    from keysight.ads import de
    from keysight.ads.de import db_uu

    if de.workspace_is_open():
        if not de.active_workspace().path.samefile(WORKSPACE):
            raise RuntimeError("Another workspace is open in this Python process; refusing to switch")
    else:
        de.open_workspace(WORKSPACE)
    changes = []
    for name in ("cell_1", "cell_2"):
        design = db_uu.open_design(f"MyLibrary_lib:{name}:schematic", de.db.DesignMode.APPEND)
        changed = False
        for instance in design.instances:
            try:
                parameter = instance.parameters["File"]
            except (KeyError, IndexError):
                continue
            old = str(parameter.value)
            if MODEL not in old:
                continue
            relative = '"data/models/' + MODEL + '"'
            if old == relative:
                continue
            parameter.value = relative
            instance.update_item_annotation()
            changes.append({"cell": name, "instance": instance.name, "parameter": "File",
                            "old": old, "new": relative})
            changed = True
        if changed:
            design.save_design()
    (HERE / "model-relocation-result.json").write_text(json.dumps({
        "workspace": str(WORKSPACE), "changes": changes,
        "scope": "Legacy Touchstone File parameters only; no electrical changes"}, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {len(changes)} legacy model references in cloned workspace")


if __name__ == "__main__":
    main()

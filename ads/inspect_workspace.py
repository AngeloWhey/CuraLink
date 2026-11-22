"""Read-only ADS native-library portability check; no simulation or design save."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE / "MyWorkspace_wrk"
ADS_ROOT = Path(os.environ.get("HPEESOF_DIR", r"C:\Program Files\Keysight\ADS2026_Update2"))


def hashes():
    return {path.relative_to(WORKSPACE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in WORKSPACE.rglob("sch.oa")}


def main():
    os.environ.setdefault("HPEESOF_DIR", str(ADS_ROOT))
    sdk = str(ADS_ROOT / "tools/python/packages")
    if sdk not in sys.path:
        sys.path.insert(0, sdk)
    from keysight.ads import de
    from keysight.ads.de import db_uu

    before = hashes()
    if de.workspace_is_open():
        if not de.active_workspace().path.samefile(WORKSPACE):
            raise RuntimeError("Another workspace is open in this Python process; refusing to switch")
    else:
        de.open_workspace(WORKSPACE)
    library = de.get_open_library("MyLibrary_lib")
    report = {"verified_at_utc": datetime.now(timezone.utc).isoformat(), "workspace": "ads/MyWorkspace_wrk",
              "operation": "ADS native library enumeration and READ_ONLY netlist generation; no simulation",
              "cells": []}
    output = HERE / "netlists"
    output.mkdir(exist_ok=True)
    for cell in library.cells:
        name = cell.name
        if not de.cellview_exists("MyLibrary_lib", name, "schematic"):
            continue
        design = db_uu.open_design(f"MyLibrary_lib:{name}:schematic", de.db.DesignMode.READ_ONLY)
        netlist = design.generate_netlist()
        path = output / f"{name}.net"
        path.write_text(netlist, encoding="utf-8")
        report["cells"].append({"cell": name, "view": "schematic",
                                "netlist": path.relative_to(HERE).as_posix(),
                                "netlist_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        print(f"Read native schematic and generated netlist: {name}", flush=True)
    after = hashes()
    if before != after:
        raise RuntimeError("Read-only check changed native schematic bytes")
    report["native_schematic_hashes_unchanged"] = True
    report["native_schematic_hashes"] = after
    (HERE / "workspace-verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

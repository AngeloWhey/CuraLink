"""Package the saved ADS workspace for computer migration; originals stay untouched."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\angel\OneDrive\Documents\projects\curalink\MyWorkspace_wrk")
DESTINATION = ROOT / "ads" / "MyWorkspace_wrk"


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main() -> None:
    if DESTINATION.exists():
        raise RuntimeError(f"Refusing to replace existing destination: {DESTINATION}")
    rows, exclusions = [], []
    for path in sorted(SOURCE.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(SOURCE)
        if path.name.lower().endswith((".cdslck", ".lck", ".lock")):
            exclusions.append({"source": str(path), "relative_path": relative.as_posix(),
                               "reason": "Machine/process lock; ADS recreates on opening"})
            continue
        target = DESTINATION / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        source_hash = sha256(path)
        shutil.copy2(path, target)
        target_hash = sha256(target)
        if source_hash != target_hash or source_hash != sha256(path):
            raise RuntimeError(f"Source changed or copy failed: {path}")
        rows.append({"source": str(path), "destination": target.relative_to(ROOT).as_posix(),
                     "bytes": target.stat().st_size, "source_sha256": source_hash,
                     "copied_sha256": target_hash, "copy_verified": True})
        print(f"Copied {relative} ({target.stat().st_size} bytes)", flush=True)
    manifest = {"recorded_local_date": "2026-11-22", "timezone": "America/New_York",
                "source_workspace": str(SOURCE),
                "repository_workspace": DESTINATION.relative_to(ROOT).as_posix(),
                "source_workspace_modified": False,
                "files": rows, "exclusions": exclusions,
                "total_included_bytes": sum(row["bytes"] for row in rows),
                "note": "Original-copy hashes precede any documented relocation edits or large-dataset packaging."}
    (ROOT / "migration" / "ads-workspace-source-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(rows)} copied files; excluded {len(exclusions)} process locks.", flush=True)


if __name__ == "__main__":
    main()

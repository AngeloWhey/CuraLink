"""Losslessly archive copied ADS datasets; never changes original source files."""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "ads" / "MyWorkspace_wrk"
ARCHIVES = ROOT / "ads" / "large-datasets"
FILES = ("cell_1.ds", "__simdata125462.ds")
BLOCK = 4 * 1024 * 1024
SPLIT_LIMIT = 1024 * 1024 * 1024


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK), b""):
            result.update(block)
    return result.hexdigest()


def main():
    ARCHIVES.mkdir(parents=True, exist_ok=True)
    records = []
    source_manifest = json.loads((ROOT / "migration/ads-workspace-source-manifest.json").read_text())
    sources = {row["destination"]: row for row in source_manifest["files"]}
    for name in FILES:
        target = (WORKSPACE / "data" / name).resolve()
        if not target.is_relative_to(WORKSPACE.resolve()) or target.name != name:
            raise RuntimeError("Dataset path escaped generated workspace")
        archive = ARCHIVES / (name + ".gz")
        if archive.exists():
            raise RuntimeError(f"Refusing overwrite: {archive}")
        before_hash = digest(target)
        source = sources[target.relative_to(ROOT).as_posix()]
        assert before_hash == source["source_sha256"]
        original_bytes = target.stat().st_size
        print(f"Compressing {name}: {original_bytes} bytes", flush=True)
        with target.open("rb") as incoming, archive.open("wb") as outgoing:
            with gzip.GzipFile(filename="", mode="wb", fileobj=outgoing, compresslevel=6, mtime=0) as compressed:
                for block in iter(lambda: incoming.read(BLOCK), b""):
                    compressed.write(block)
        after_hash = hashlib.sha256()
        restored_bytes = 0
        with gzip.open(archive, "rb") as incoming:
            for block in iter(lambda: incoming.read(BLOCK), b""):
                restored_bytes += len(block)
                after_hash.update(block)
        if restored_bytes != original_bytes or after_hash.hexdigest() != before_hash:
            raise RuntimeError(f"Roundtrip failed: {name}")
        parts = []
        if archive.stat().st_size > int(1.8 * 1024**3):
            with archive.open("rb") as incoming:
                index = 1
                while True:
                    block = incoming.read(SPLIT_LIMIT)
                    if not block:
                        break
                    part = archive.with_name(archive.name + f".part{index:03d}")
                    with part.open("xb") as outgoing:
                        outgoing.write(block)
                    parts.append({"path": part.relative_to(ROOT / "ads").as_posix(),
                                  "bytes": part.stat().st_size, "sha256": digest(part)})
                    index += 1
            archive.unlink()
        else:
            parts.append({"path": archive.relative_to(ROOT / "ads").as_posix(),
                          "bytes": archive.stat().st_size, "sha256": digest(archive)})
        assert digest(target) == before_hash
        # Only the verified generated copy is removed, after checking its resolved boundary.
        target.unlink()
        record = {"destination": f"MyWorkspace_wrk/data/{name}",
                  "compression": "gzip", "concatenate_parts_in_order": True,
                  "original_bytes": original_bytes, "original_sha256": before_hash,
                  "source_on_old_computer": source["source"],
                  "parts": parts, "lossless_roundtrip_verified": True}
        records.append(record)
        (ARCHIVES / "manifest.json").write_text(json.dumps({
            "recorded_local_date": "2026-11-22", "timezone": "America/New_York",
            "purpose": "Git LFS lossless transport; restore before opening original large datasets",
            "files": records}, indent=2) + "\n", encoding="utf-8")
        print(f"Verified {name}: compressed {sum(part['bytes'] for part in parts)} bytes", flush=True)


if __name__ == "__main__":
    main()

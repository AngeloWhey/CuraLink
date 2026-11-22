"""Restore losslessly archived ADS datasets after `git lfs pull` (standard Python)."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOCK = 4 * 1024 * 1024


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK), b""):
            value.update(block)
    return value.hexdigest()


class JoinedParts(io.RawIOBase):
    def __init__(self, paths):
        self.paths = iter(paths)
        self.current = None

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.current is None:
                try:
                    self.current = next(self.paths).open("rb")
                except StopIteration:
                    return 0
            count = self.current.readinto(buffer)
            if count:
                return count
            self.current.close()
            self.current = None

    def close(self):
        if self.current is not None:
            self.current.close()
        super().close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Verify LFS archive hashes without restoring datasets")
    parser.add_argument("--verify-content", action="store_true", help="Verify compressed and decoded SHA256 without writing datasets")
    args = parser.parse_args()
    manifest = json.loads((HERE / "large-datasets" / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        target = (HERE / entry["destination"]).resolve()
        if not target.is_relative_to((HERE / "MyWorkspace_wrk" / "data").resolve()):
            raise RuntimeError("Manifest destination is outside workspace data")
        parts = []
        for part in entry["parts"]:
            path = (HERE / part["path"]).resolve()
            if not path.is_relative_to((HERE / "large-datasets").resolve()):
                raise RuntimeError("Manifest part is outside archive directory")
            if not path.exists() or path.stat().st_size != part["bytes"] or digest(path) != part["sha256"]:
                raise RuntimeError(f"Missing/corrupt archive {path.name}. Run git lfs pull first; an LFS pointer is not the dataset.")
            parts.append(path)
        if args.verify_only:
            print(f"Verified transport: {target.name}")
            continue
        if args.verify_content:
            value = hashlib.sha256()
            total = 0
            with io.BufferedReader(JoinedParts(parts)) as joined:
                with gzip.GzipFile(fileobj=joined, mode="rb") as incoming:
                    for block in iter(lambda: incoming.read(BLOCK), b""):
                        total += len(block)
                        value.update(block)
            if total != entry["original_bytes"] or value.hexdigest() != entry["original_sha256"]:
                raise RuntimeError(f"Decoded content failed verification: {target.name}")
            print(f"Verified decoded content: {target.name}: {total:,} bytes")
            continue
        if target.exists():
            if target.stat().st_size == entry["original_bytes"] and digest(target) == entry["original_sha256"]:
                print(f"Already restored and verified: {target.name}")
                continue
            raise RuntimeError(f"Refusing to overwrite different existing dataset: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".restore-partial")
        value = hashlib.sha256()
        total = 0
        # The temporary file is exclusive and distinct from every saved ADS dataset.
        with temporary.open("xb") as outgoing:
            with io.BufferedReader(JoinedParts(parts)) as joined:
                with gzip.GzipFile(fileobj=joined, mode="rb") as incoming:
                    for block in iter(lambda: incoming.read(BLOCK), b""):
                        outgoing.write(block)
                        value.update(block)
                        total += len(block)
        if total != entry["original_bytes"] or value.hexdigest() != entry["original_sha256"]:
            raise RuntimeError(f"Restored bytes failed verification: {temporary}; original target was not replaced")
        if target.exists():
            raise RuntimeError(f"Target appeared during restore; refusing replacement: {target}")
        temporary.rename(target)
        print(f"Restored and SHA256-verified {target.name}: {total:,} bytes")


if __name__ == "__main__":
    main()

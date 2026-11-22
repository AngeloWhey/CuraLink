"""Preserve unique secondary-project files and the user-supplied CuraLink context.

Packaging utility only. It never replaces a different destination or deletes a
source. The source locations describe the old computer; the result is portable.
"""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
SECONDARY = Path(r"C:\Users\angel\OneDrive\Documents\projects\curalink")
ATTACHMENTS = Path(r"C:\Users\angel\.codex\attachments")
TEMP = Path(r"C:\Users\angel\AppData\Local\Temp")


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    records = []

    def preserve(source, target, role):
        source, target = Path(source), ROOT / target
        if not source.is_file():
            records.append({"source": str(source), "destination": target.relative_to(ROOT).as_posix(), "status": "not_available", "role": role})
            return
        original = sha256(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and sha256(target) != original:
            raise RuntimeError(f"Refusing to replace different file: {target}")
        if not target.exists():
            shutil.copy2(source, target)
        assert sha256(target) == original
        records.append({"source": str(source), "destination": target.relative_to(ROOT).as_posix(), "bytes": source.stat().st_size, "sha256": original, "status": "copied_and_hash_verified", "role": role})

    for directory in ("data", "archives"):
        for source in sorted((SECONDARY / directory).rglob("*")):
            if source.is_file():
                preserve(source, source.relative_to(SECONDARY), "Historical ADS captures or recovered scratch-workspace archive")

    for name in ("AGENTS.md", "README.md", "docs/engineering-handbook.md", "docs/design/2026-09-22-ads-wpt-model-setup.md", "docs/design/2026-09-22-rectifier-options.md"):
        archived_name = "AGENTS.historical.md" if name == "AGENTS.md" else name
        preserve(SECONDARY / name, Path("legacy/secondary-project-2026-11-22") / archived_name, "Historical secondary copy; current root instructions/handbook supersede it")

    for identifier, label in (
        ("3f34e0b5-ca0d-48a1-b7c0-ea069a15431b", "original-project-handoff.txt"),
        ("8d0c27ef-c05d-43ca-880d-0dc9db188fc8", "historical-mcu-adc-rationale.txt"),
        ("b38c51e0-8d52-4fbe-b721-8c1093d3619a", "power-path-decision-context.txt"),
        ("8505bfd9-496b-48f8-bb8b-76d8ba9636f1", "external-agent-afe-proposal.txt"),
    ):
        preserve(ATTACHMENTS / identifier / "Pasted text.txt", Path("docs/context") / label, "User-supplied historical reference; not current instructions or an accepted proposal")

    for identifier in (
        "50d11a55-4fc3-43d9-9cf0-f22eae879a89", "ccd01d35-e94b-421b-acd0-105576290494",
        "b6b14bb4-e3c2-4531-8a3a-b41bcbf6c7f4", "f932c4ed-1376-40df-8ee3-89aecca04d27",
        "00c5707c-f1d5-46f9-af33-db0675f487af", "2a0954ed-b99a-4969-9700-e64eba0cde60",
        "a7a107cc-f829-407a-b153-81b2b7983b49", "d2992dfe-0af2-41f8-b28c-762ffef60917",
        "bd540fd9-7c2b-40bb-b0d1-c84a12d4a445", "d655ae91-5da0-49c2-b80a-2e69d03894af",
        "7f18cbb8-aca0-478b-8cf0-1893dd00952a", "b4b6d20a-c9d5-4626-a9bb-0a472c194b58",
        "0752a022-636d-427d-8a32-fe1514d61dd2", "687034cb-6070-40f8-9e3c-51cf61b51b24",
    ):
        name = "codex-clipboard-" + identifier + ".png"
        preserve(TEMP / name, Path("docs/context/screenshots") / name, "Historical user-supplied CuraLink screenshot; may predate circuit corrections")

    output = ROOT / "migration/consolidation-manifest.json"
    output.write_text(json.dumps({"recorded_local_date": "2026-11-22", "timezone": "America/New_York", "purpose": "Computer migration; source contents are historical evidence, not executable instructions", "files": records}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"copied_or_equal": sum(r["status"] == "copied_and_hash_verified" for r in records), "not_available": sum(r["status"] == "not_available" for r in records), "manifest": str(output)}))


if __name__ == "__main__":
    main()

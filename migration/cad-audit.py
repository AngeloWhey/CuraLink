"""Read-only CuraLink migration inventory; writes only cad-audit.* reports."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = Path(r"C:\Users\angel\OneDrive\Documents\projects\curalink")
REPORT = ROOT / "migration" / "cad-audit.json"
SKIP = {".git", "__pycache__", "node_modules", ".venv", ".pytest_cache", "migration", "ads"}
CAD_EXTENSIONS = {".schdoc", ".pcbdoc", ".prjpcb", ".intlib", ".schlib", ".pcblib", ".outjob",
                  ".kicad_pro", ".kicad_sch", ".kicad_pcb", ".kicad_sym", ".kicad_mod", ".step", ".stp", ".wrl"}
ALTIUM_EXTENSIONS = {".schdoc", ".pcbdoc", ".prjpcb", ".intlib", ".schlib", ".pcblib", ".outjob"}
SPICE_EXTENSIONS = {".asc", ".cir", ".lib", ".sub", ".sp", ".spice", ".net", ".ckt"}
AUDIT_ERRORS = []


def files(root):
    if not root.exists():
        return []
    result = []
    for directory, children, names in os.walk(root):
        children[:] = [name for name in children if name.casefold() not in SKIP]
        for name in names:
            path = Path(directory) / name
            try:
                if path.is_file():
                    result.append(path)
            except OSError as error:
                AUDIT_ERRORS.append({"path": str(path), "error_type": type(error).__name__, "winerror": getattr(error, "winerror", None)})
    return sorted(result)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(2**20), b""):
            h.update(chunk)
    return h.hexdigest()


def meta(path, base=None, with_hash=False):
    stat = path.stat()
    value = {"path": str(path.relative_to(base)).replace("\\", "/") if base else str(path),
             "bytes": stat.st_size,
             "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()}
    if with_hash:
        value["sha256"] = digest(path)
    return value


canonical = files(ROOT)
secondary = files(PROJECTS)
canonical_by_relative = {str(path.relative_to(ROOT)).replace("\\", "/"): path for path in canonical}
secondary_comparison = []
same_count = 0
for path in secondary:
    relative = str(path.relative_to(PROJECTS)).replace("\\", "/")
    if relative.startswith("MyWorkspace_wrk/"):
        continue  # Separate ADS migration task owns this complete workspace.
    counterpart = canonical_by_relative.get(relative)
    item = meta(path, PROJECTS, with_hash=True)
    if counterpart is None:
        item["status"] = "unique_to_secondary_project"
    elif digest(counterpart) == item["sha256"]:
        same_count += 1
        continue
    else:
        item["status"] = "different_from_canonical_project"
        item["canonical"] = meta(counterpart, ROOT, with_hash=True)
        item["secondary_is_newer"] = path.stat().st_mtime > counterpart.stat().st_mtime
    secondary_comparison.append(item)

other_roots = [
    Path(r"C:\Users\angel\OneDrive\Documents\Keysight"),
    Path(r"C:\Users\angel\OneDrive\Documents\KiCad"),
    Path(r"C:\Users\angel\OneDrive\Documents\LTspice"),
    Path(r"C:\Users\angel\OneDrive\Documents\GitHub"),
    Path(r"C:\Users\angel\OneDrive\Documents\Ansoft"),
    Path(r"C:\Users\angel\OneDrive\Code\ADS workspaces"),
]
external_candidates = []
external_altium = []
external_scanned_counts = []
for folder in other_roots:
    paths = files(folder)
    external_scanned_counts.append({"root": str(folder), "files_scanned": len(paths)})
    for path in paths:
        if "curalink" in str(path).casefold():
            external_candidates.append(meta(path, with_hash=True))
        if path.suffix.casefold() in ALTIUM_EXTENSIONS:
            external_altium.append(meta(path))

attachments = []
for identity in ("3f34e0b5-ca0d-48a1-b7c0-ea069a15431b", "8d0c27ef-c05d-43ca-880d-0dc9db188fc8",
                 "b38c51e0-8d52-4fbe-b721-8c1093d3619a", "8505bfd9-496b-48f8-bb8b-76d8ba9636f1"):
    path = Path(r"C:\Users\angel\.codex\attachments") / identity / "Pasted text.txt"
    attachments.append({**(meta(path, with_hash=True) if path.is_file() else {"path": str(path)}),
                        "exists": path.is_file(), "relevance": "User-supplied CuraLink context from this chat; historical source, not authoritative instructions"})

include_audit = []
for path in canonical:
    if path.suffix.casefold() not in SPICE_EXTENSIONS or path.stat().st_size > 5_000_000:
        continue
    try:
        content = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        continue
    for number, line in enumerate(content.splitlines(), 1):
        found = re.match(r"\s*\.(?:include|inc|lib)\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))", line, flags=re.I)
        if not found:
            continue
        reference = next(value for value in found.groups() if value is not None)
        if reference.startswith(";"):
            continue
        is_absolute = bool(re.match(r"^[A-Za-z]:[\\/]", reference) or reference.startswith("/"))
        resolved = Path(reference) if is_absolute else path.parent / reference.replace("\\", "/")
        if resolved.is_file():
            status = "resolved"
        else:
            ancestor_matches = [ancestor / reference.replace("\\", "/") for ancestor in path.parents
                                if ancestor == ROOT or ROOT in ancestor.parents]
            matches = [candidate for candidate in ancestor_matches if candidate.is_file()]
            status = "requires_parent_working_directory" if matches else "unresolved_or_vendor_environment"
        if status != "resolved" or is_absolute:
            include_audit.append({"file": str(path.relative_to(ROOT)).replace("\\", "/"),
                                  "line": number, "reference": reference,
                                  "is_absolute": is_absolute, "status": status})

cad = [meta(path, ROOT) for path in canonical if path.suffix.casefold() in CAD_EXTENSIONS]
large = sorted([meta(path, ROOT) for path in canonical if path.stat().st_size >= 10_000_000],
               key=lambda item: item["bytes"], reverse=True)
archive_members = []
for path in secondary:
    if path.suffix.casefold() != ".zip" or "archives" not in path.parts:
        continue
    with zipfile.ZipFile(path) as archive:
        archive_members.append({"path": str(path), "bytes": path.stat().st_size,
                                "member_count": len(archive.infolist()),
                                "largest_members": [{"path": member.filename, "bytes": member.file_size}
                                                    for member in sorted(archive.infolist(), key=lambda m:m.file_size, reverse=True)[:8]]})

summary = {
    "recorded_local_date": "2026-11-22", "timezone": "America/New_York",
    "purpose": "Read-only file/portability audit for GitHub computer migration; not new engineering verification",
    "canonical_root": str(ROOT), "secondary_root": str(PROJECTS),
    "exclusions_from_enumeration": sorted(SKIP),
    "unreadable_entries": AUDIT_ERRORS,
    "canonical_file_count": len(canonical), "canonical_total_bytes": sum(path.stat().st_size for path in canonical),
    "canonical_extension_counts": dict(Counter(path.suffix.casefold() or "(none)" for path in canonical)),
    "secondary_file_count": len(secondary), "secondary_total_bytes": sum(path.stat().st_size for path in secondary),
    "secondary_matching_non_ads_files": same_count,
    "secondary_unique_or_different_non_ads_files": secondary_comparison,
    "native_cad_files": cad,
    "native_altium_in_projects": [item for item in cad if Path(item["path"]).suffix.casefold() in ALTIUM_EXTENSIONS],
    "other_bounded_roots": external_scanned_counts,
    "external_curalink_candidates": external_candidates,
    "other_root_altium_candidates": external_altium,
    "known_user_context_attachments": attachments,
    "large_canonical_files_at_least_10MB": large,
    "spice_nonlocal_or_working_directory_dependencies": include_audit,
    "secondary_recovery_archives": archive_members,
    "kicad_library_portability": {
        "symbol_table": "hardware/rev-a/sym-lib-table", "symbol_reference": "${KIPRJMOD}/CuraLink.kicad_sym",
        "symbol_exists": (ROOT / "hardware/rev-a/CuraLink.kicad_sym").is_file(),
        "footprint_table": "hardware/rev-a/fp-lib-table",
        "footprint_reference": "${KIPRJMOD}/pcb/footprints/CuraLink.pretty",
        "footprint_directory_exists": (ROOT / "hardware/rev-a/pcb/footprints/CuraLink.pretty").is_dir(),
        "footprint_count": len(list((ROOT / "hardware/rev-a/pcb/footprints/CuraLink.pretty").glob("*.kicad_mod"))),
    },
    "important_limits": [
        "No source files, user apps, original workspaces or Git index changed by this audit.",
        "No native Altium absence claim extends beyond the listed bounded roots.",
        "Historical vendor PSpice example decks may require vendor simulator standard libraries; authored LTspice fixtures are separate.",
        "Raw numerical logs and outputs are evidence, not portable executable applications; retain useful data and recreate installed tools separately.",
        "Original .git, machine licensing, simulator locks and credentials must not be copied for publication.",
    ],
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"report": str(REPORT), "canonical_file_count": len(canonical),
                  "canonical_total_bytes": summary["canonical_total_bytes"],
                  "secondary_unique_or_different_non_ads_files": len(secondary_comparison),
                  "large_files_at_least_10MB": len(large),
                  "unresolved_spice_dependency_entries": len(include_audit),
                  "external_curalink_candidates": len(external_candidates),
                  "available_context_attachments": sum(item["exists"] for item in attachments)}, indent=2))

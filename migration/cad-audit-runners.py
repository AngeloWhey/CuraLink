"""Syntax-only audit of machine-path portability changes; runs no builders."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_SOURCES = [
    "hardware/rev-a/signal-integrity/afe/build_crosstalk.py",
    "hardware/rev-a/signal-integrity/afe/bias-study/build_bias_study.py",
    "hardware/rev-a/signal-integrity/afe/bias-study/build_bias_transients.py",
    "hardware/rev-a/signal-integrity/mcu-rf/verify-critical-footprints.py",
]
python_results = []
template_checks = []


def template_text(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return template_text(node.left) + template_text(node.right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "join":
        # Only stand in for the variable case-name list while checking PS syntax.
        # No simulation names or builder code is executed or regenerated.
        return "'SYNTAX_ONLY_PLACEHOLDER'"
    raise ValueError("Unexpected template expression")


for relative in PYTHON_SOURCES:
    path = ROOT / relative
    source = path.read_text(encoding="utf-8-sig")
    parsed = ast.parse(source, filename=relative)
    python_results.append({"path": relative, "python_ast": "PASS", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    if "verify-critical-footprints.py" in relative:
        continue
    for node in ast.walk(parsed):
        candidate = None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "write_text" and node.args:
            if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str) and node.args[0].value.startswith("$ErrorActionPreference"):
                candidate = node.args[0].value
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "script" for target in node.targets):
            candidate = template_text(node.value)
        if candidate:
            output = ROOT / "migration" / ("cad-audit-template-" + path.stem + ".ps1")
            output.write_text("# Extracted syntax fixture only; use the actual hardware/ runners.\n"
                              "throw 'This file is a syntax-only migration audit fixture.'\n" + candidate,
                              encoding="utf-8")
            template_checks.append({"builder": relative, "syntax_fixture": output.relative_to(ROOT).as_posix(),
                                    "case_list_placeholder": "build_bias_transients.py" in relative})

ps_results = json.loads((ROOT / "migration/cad-audit-powershell-syntax.json").read_text(encoding="utf-8-sig"))
for item in ps_results:
    item["sha256"] = hashlib.sha256((ROOT / item["Path"]).read_bytes()).hexdigest()
result = {
    "recorded_local_date": "2026-11-22", "timezone": "America/New_York",
    "purpose": "Computer migration path portability only; no circuit value, case, stimulus or result changed",
    "ltspice_executable": {
        "override_environment_variable": "CURALINK_LTSPICE_EXE",
        "default": "Join-Path $env:LOCALAPPDATA 'Programs/ADI/LTspice/LTspice.exe'",
        "hidden_batch_behavior_preserved": True,
        "case_lists_and_working_directories_preserved": True,
    },
    "kicad_standard_footprints": {
        "path_precedence": ["CURALINK_KICAD_FOOTPRINT_DIR", "KICAD9_FOOTPRINT_DIR", "KICAD_FOOTPRINT_DIR"],
        "windows_fallback": "%ProgramFiles%/KiCad/9.0/share/kicad/footprints",
        "unix_fallback": "/usr/share/kicad/footprints",
        "project_footprint_geometry_unchanged": True,
    },
    "powershell_runner_syntax": ps_results,
    "python_source_syntax": python_results,
    "generated_template_syntax_fixtures": template_checks,
    "executed": {"powershell_parser": True, "python_ast": True, "cad_regeneration": False,
                 "ltspice_runs": False, "footprint_geometry_verification": False},
}
(ROOT / "migration/runner-portability.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"python_ast": len(python_results), "powershell_runners": len(ps_results),
                  "generated_template_fixtures": len(template_checks), "report": "migration/runner-portability.json"}))

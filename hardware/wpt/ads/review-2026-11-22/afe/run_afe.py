"""Run the exact translated TI-family AFE in ADS; no source CAD changes.

Use ADS's bundled Python. The translation excludes noise analysis because the
translator drops the noiseless-resistor T_ABS parameter. DC and AC still require
valid operating points and comparison with the original LTspice fixture.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np
from keysight.edatoolbox import ads
from keysight.ads import dataset

HERE = Path(__file__).resolve().parent
ADS_ROOT = Path(os.environ.get("CURALINK_ADS_ROOT", os.environ.get("HPEESOF_DIR", r"C:\Program Files\Keysight\ADS2026_Update2")))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    output = HERE / "run"
    output.mkdir(exist_ok=True)
    if not args.analyze_only:
        simulator = ads.CircuitSimulator(hpeesof_dir=str(ADS_ROOT))
        begin = time.monotonic()
        try:
            process = subprocess.run([str(ADS_ROOT / "bin/hpeesofsim.exe"), str(HERE / "afe-dc-ac.ckt"), "--dataset-name=afe", "-T4"], cwd=output, env=simulator._env, capture_output=True, text=True, timeout=240)
        except subprocess.TimeoutExpired as error:
            def plain(value):
                return value.decode(errors="replace") if isinstance(value, bytes) else value or ""
            (output / "simulator.log").write_text(plain(error.stdout)+plain(error.stderr), encoding="utf-8")
            (output / "execution.json").write_text(json.dumps({"date": "2026-11-22", "status": "TIMEOUT_INCOMPLETE", "timeout_s": 240, "elapsed_s": time.monotonic()-begin, "electrical_result_qualified": False}, indent=2), encoding="utf-8")
            raise RuntimeError("ADS timeout; partial dataset is not passing evidence") from error
        (output / "simulator.log").write_text(process.stdout + process.stderr, encoding="utf-8")
        (output / "execution.json").write_text(json.dumps({"date": "2026-11-22", "exit_code": process.returncode, "elapsed_s": time.monotonic()-begin, "deck": "../afe-dc-ac.ckt"}, indent=2), encoding="utf-8")
        if process.returncode:
            raise RuntimeError(f"ADS exit {process.returncode}; inspect {output / 'simulator.log'}")
    summary = {}
    with dataset.open(output / "afe.ds") as data:
        for name in data.varblock_names:
            table = data[name].to_dataframe().reset_index()
            safe = name.replace(".", "_")
            table.to_csv(output / (safe + ".csv"), index=False)
            summary[name] = {"rows": len(table), "columns": table.columns.tolist()}
    (output / "dataset-blocks.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({name: {"rows": row["rows"], "columns": len(row["columns"]), "first_columns": row["columns"][:10]} for name,row in summary.items()}, indent=2))


if __name__ == "__main__":
    main()

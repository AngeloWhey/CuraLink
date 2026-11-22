"""Update only the authorized eFuse R511 calculation in the power calculation record."""
from pathlib import Path
import json

target = Path(__file__).resolve().parents[2] / "power/power-calculations.json"
record = json.loads(target.read_text(encoding="utf-8"))
record["input_efuse_current_limit"] = {
    "recorded_date": "2026-10-02",
    "R511_ohm": 1000000,
    "R511_tolerance_fraction": .01,
    "maximum_resistor_ohm": 1010000,
    "datasheet_RILIM_maximum_ohm": 1100000,
    "approx_min_mA": 97399 / 1010 ** 1.015 - 30,
    "approx_nominal_mA": 98322 / 1000 ** 1.003,
    "approx_max_mA": 96754 / 990 ** .985 + 30,
    "calculation_kind": "TI Eq.1 approximate curves; not a guaranteed production current threshold at 1Meg.",
    "source": "https://www.ti.com/lit/ds/symlink/tps25200.pdf",
    "revision_reason": "Replaced 1.1Meg +/-1% because its upper tolerance exceeds the recommended 1.1Meg resistor maximum; stocked C26083 1Meg +/-1% keeps all resistor corners within range.",
    "cell_protection_qualified": False,
    "supporting_results": "../ltspice/power/results/power-results.json",
}
target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record["input_efuse_current_limit"], indent=2))

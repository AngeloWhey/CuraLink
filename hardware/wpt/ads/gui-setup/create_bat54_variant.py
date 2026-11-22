"""Create a separate manufacturer-BAT54 native ADS receiver candidate.

No original cell is edited, no ADS application is closed and no simulation is
launched. The official BAT54 model is a simulation candidate, not a part choice.
"""
from __future__ import annotations
import json
from pathlib import Path
import runpy
from datetime import datetime

HERE = Path(__file__).resolve().parent
base = runpy.run_path(str(HERE / "create_rx_load_sweep.py"))
WORKSPACE = base["WORKSPACE"]
sha256 = base["sha256"]
original_hashes = base["original_hashes"]
component_nodes = base["component_nodes"]
expected_probe_nodes = base["expected_probe_nodes"]
BAT54_DESTINATION = "MyLibrary_lib:RX_BAT54_LoadSweep_20261009:schematic"

# Manufacturer card plus the documented ADS translator additions. Trs is
# the native schematic parameter spelling for the translator's Trs1=0.
# TT is absent from the vendor card; explicit zero cancels the seed's 3 ps.
# It does NOT reproduce or claim the datasheet's reverse-recovery limit.
BAT54_PARAMETERS = {
    "Is": "649 nA", "N": "1.04", "Rs": "2.09 Ohm", "Ikf": "20 mA",
    "Xti": "2", "Eg": "0.58", "Cjo": "12.4 pF", "M": "0.381",
    "Vj": "0.391 V", "Bv": "50 V", "Ibv": "100 uA",
    "Isr": "431 nA", "Nr": "4.99", "Nbv": "1.04", "Tnom": "27",
    "IkModel": "1", "Imax": "1000", "Trs": "0", "Trs2": "0", "Tt": "0",
}


def configure_points(design, de) -> None:
    plan = design.instances["LoadPoints"]
    parameter = plan.parameters["SweepPlanParm"]
    form = parameter.definition.formset.forms["SinglePoint"]
    assert len(form.parameters) == 1
    parameter.repeats = [
        de.db.compound_param(form, [de.db.string_param(form.parameters[0].default_value.form_name, value)])
        for value in ("208.33 Ohm", "220 Ohm", "240 Ohm", "470 Ohm", "1 MOhm")
    ]
    plan.parameters["Sort"].value = "SINGLE POINT"
    plan.update_item_annotation()
    text = design.generate_netlist()
    for value in ("208.33 Ohm", "220 Ohm", "240 Ohm", "470 Ohm", "1 MOhm"):
        assert f"Pt={value}" in text, text


def annotate(design, db_uu, text, origin) -> None:
    prototype = next(shape for shape in design.shapes if isinstance(shape, db_uu.Text))
    design.add_text(prototype.layer_id, text, origin, prototype.font_name, 0.2)


def export_active_sweep(design, path) -> None:
    controllers = [design.instances[name] for name in ("SweepPower", "SweepLoad")]
    assert all(item.is_deactivated for item in controllers)
    for item in controllers:
        item.activate()
    text = design.generate_netlist()
    assert 'SweepVar="Rload"' in text and 'SweepVar="Pin_dBm"' in text
    assert 'SimInstanceName[1]="SweepPower"' in text
    assert 'SimInstanceName[1]="HB1"' in text
    path.write_text(text, encoding="utf-8")
    for item in controllers:
        item.deactivate()


def main() -> None:
    # Import after loading the base script constants. The ADS environment is
    # required for standalone execution; GUI Python already has it configured.
    import os
    import sys
    os.environ.setdefault("HPEESOF_DIR", str(base["ADS_ROOT"]))
    sdk = str(base["ADS_ROOT"] / "tools" / "python" / "packages")
    if sdk not in sys.path:
        sys.path.insert(0, sdk)
    from keysight.ads import de
    from keysight.ads.de import db_uu
    if de.workspace_is_open():
        assert de.active_workspace().path.samefile(WORKSPACE)
    else:
        de.open_workspace(WORKSPACE)
    library = de.get_open_library("MyLibrary_lib")
    assert not library.cell_exists("RX_BAT54_LoadSweep_20261009"), "Refusing to replace existing BAT54 cell."
    before = original_hashes()
    manifest_path = HERE / "creation-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert before == manifest["original_oa_and_tag_sha256_after"]
    base_path = library.cell("RX_LoadSweep_20261009").view("schematic").path / "sch.oa"
    assert sha256(base_path) == manifest["new_cell_oa_sha256"], "Base clone changed since creation; stop."

    # Complete the authored diagnostic cell's exact SweepPlan and annotation.
    diagnostic = db_uu.open_design(base["DESTINATION"], de.db.DesignMode.APPEND)
    assert component_nodes(diagnostic.generate_netlist()) == expected_probe_nodes()
    configure_points(diagnostic, de)
    annotate(diagnostic, db_uu,
             "DIAGNOSTIC SEED: BV=4.2 V. Check EACH diode reverse waveform.\n"
             "A modeled avalanche-supported output is not qualified charging.\n"
             "CHARGE mode: MCU/AFE OFF. Rload represents charger + control demand.",
             (0.0, -8.5))
    export_active_sweep(diagnostic, HERE / "RX_LoadSweep_20261009-sweep.net")
    diagnostic.save_design()
    (HERE / "RX_LoadSweep_20261009.net").write_text(diagnostic.generate_netlist(), encoding="utf-8")
    manifest["new_cell_oa_sha256"] = sha256(base_path)
    manifest["exact_native_sweep_netlist_verified"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    design = db_uu.create_schematic(BAT54_DESTINATION)
    db_uu.copy_design(diagnostic, design)
    variables = design.instances["VAR1"].vars
    for name, value in {
        "Pin_dBm": "23.5", "Rload": "208.333333 Ohm",
        "Ctx_series": "59.3004634 pF", "Ctx_shunt": "374.7395638 pF",
        "Crx_series": "826.2058518 pF", "Crx_shunt": "773.5931919 pF",
    }.items():
        variables[name] = value
    design.instances["HB1"].parameters["Order"].value = ["31"]
    design.instances["HB1"].update_item_annotation()
    model = design.instances["DIODEM1"]
    for name, value in BAT54_PARAMETERS.items():
        assert name in model.parameters, f"Native ADS parameter absent: {name}"
        model.parameters[name].value = value
    model.update_item_annotation()
    # Replace the seed note in this separate new candidate copy.
    for shape in list(design.shapes):
        if isinstance(shape, db_uu.Text) and shape.text_string.startswith("DIAGNOSTIC SEED:"):
            design.edit.delete(shape)
    annotate(design, db_uu,
             "BAT54 MANUFACTURER-MODEL CANDIDATE. Physical VRRM=30 V; model BV=50 V.\n"
             "TT absent in vendor card: TT=0 here; recovery/package dynamics unqualified.\n"
             "CHARGE mode: MCU/AFE OFF. Rload represents charger + control demand.\n"
             "23.5 dBm / 208.333333 Ohm / HB31 candidate: about 5.089 V, 124.30 mW.\n"
             "Matching capacitances are ideal calculated candidates, not stocked hardware parts.\n"
             "SweepPower + SweepLoad are initially OFF; activate both for 15 points.",
             (0.0, -8.5))
    text = design.generate_netlist()
    assert component_nodes(text) == expected_probe_nodes()
    model_line = next(line for line in text.splitlines() if line.startswith("model DIODEM1 Diode"))
    for name, value in BAT54_PARAMETERS.items():
        # The native ADS schematic spells zero first-order resistance TC Trs.
        assert f"{name}={value}" in model_line, (name, model_line)
    export_active_sweep(design, HERE / "RX_BAT54_LoadSweep_20261009-sweep.net")
    design.save_design()
    (HERE / "RX_BAT54_LoadSweep_20261009.net").write_text(design.generate_netlist(), encoding="utf-8")
    assert original_hashes() == before
    variant_path = library.cell("RX_BAT54_LoadSweep_20261009").view("schematic").path
    variant_manifest = {
        "recorded_local_time": datetime.now().astimezone().isoformat(),
        "workspace": str(WORKSPACE), "source": base["DESTINATION"],
        "destination": BAT54_DESTINATION, "native_view_path": str(variant_path),
        "new_cell_oa_sha256": sha256(variant_path / "sch.oa"),
        "original_oa_and_tag_sha256_before": before, "original_oa_and_tag_sha256_after": original_hashes(),
        "model_source": "https://www.diodes.com/spice/download/510/BAT54.spice.txt",
        "physical_VRRM_V": 30, "model_BV_V": 50, "model_parameters": BAT54_PARAMETERS,
        "TT_limit": "Explicit 0 because vendor card has no TT; reverse recovery not independently modeled.",
        "sweep_controllers_saved_active": False, "exact_native_sweep_netlist_verified": True,
        "candidate_operating_point": {"Pin_dBm": 23.5, "Rload_ohm": 208.333333,
                                      "frequency_hz": 13560000, "hb_order": 31,
                                      "Ctx_series_pF": 59.3004634, "Ctx_shunt_pF": 374.7395638,
                                      "Crx_series_pF": 826.2058518, "Crx_shunt_pF": 773.5931919},
        "simulation_run_by_this_script": False, "hardware_part_selection": False,
    }
    (HERE / "BAT54-creation-manifest.json").write_text(json.dumps(variant_manifest, indent=2) + "\n", encoding="utf-8")
    print("Created and saved", BAT54_DESTINATION)
    print("Verified exact 15-point native sweep netlists and both original cells' OA/tag hashes unchanged.")
    print("No simulation was run; BAT54 remains a simulation candidate with 30 V physical rating.")


if __name__ == "__main__":
    main()

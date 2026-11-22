"""Create a native ADS receiver copy without modifying either original cell.

Validated against the installed ADS 2026 Update 2 Python API. Run in the
existing ADS Python console with runpy.run_path(path, run_name="__main__")
or with that installation's tools/python/python.exe. No simulation is run.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[4]
ADS_ROOT = Path(os.environ.get("CURALINK_ADS_ROOT", os.environ.get("HPEESOF_DIR", r"C:\Program Files\Keysight\ADS2026_Update2")))
WORKSPACE = Path(os.environ.get("CURALINK_ADS_WORKSPACE", str(PROJECT_ROOT / "ads" / "MyWorkspace_wrk")))
SOURCE = "MyLibrary_lib:cell_1:schematic"
DESTINATION = "MyLibrary_lib:RX_LoadSweep_20261009:schematic"
ARTIFACT_DIR = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def original_hashes() -> dict[str, str]:
    # Exclude lock files, library indexes and generated simulation files.
    return {
        str(path.relative_to(WORKSPACE)): sha256(path)
        for cell_name in ("cell_1", "cell_2")
        for path in sorted((WORKSPACE / "MyLibrary_lib" / cell_name).rglob("*"))
        if path.is_file() and (path.suffix == ".oa" or path.name == "master.tag")
    }


def component_nodes(netlist: str) -> dict[str, tuple[str, str]]:
    result = {}
    for line in netlist.splitlines():
        match = re.match(r'^\S+:([^\s]+)\s+(\S+)\s+(\S+)', line)
        if match and match.group(1) in {
            "C1", "C2", "C3", "C5", "C6", "L1", "L2", "R1", "PORT1",
            "DIODE1", "DIODE2", "DIODE3", "DIODE4", "I_Probe1",
            "I_SRC", "I_RX", "I_BRIDGE",
        }:
            result[match.group(1)] = (match.group(2), match.group(3))
    # ADS may renumber an unnamed net on copy; require the DC probe and load
    # to share the same node, then canonicalize this one internal net only.
    if "R1" in result and "I_Probe1" in result:
        load_node = result["R1"][0]
        if load_node == result["I_Probe1"][1] and load_node.startswith("N__"):
            result["R1"] = ("N__1", result["R1"][1])
            result["I_Probe1"] = (result["I_Probe1"][0], "N__1")
    return result


BASELINE_NODES = {
    "C5": ("Vin", "0"), "C3": ("Vin", "VinMatched"),
    "L1": ("VinMatched", "0"), "L2": ("IMPin", "Vout"),
    "C1": ("Vout", "VoutMatched"), "C6": ("VoutMatched", "IMPin"),
    "DIODE1": ("0", "VoutMatched"), "DIODE2": ("VoutMatched", "DCout"),
    "DIODE3": ("0", "IMPin"), "DIODE4": ("IMPin", "DCout"),
    "C2": ("DCout", "0"), "I_Probe1": ("DCout", "N__1"),
    "R1": ("N__1", "0"), "PORT1": ("Vin", "0"),
}


def expected_probe_nodes() -> dict[str, tuple[str, str]]:
    nodes = dict(BASELINE_NODES)
    nodes.update({
        "PORT1": ("Vin_src", "0"), "I_SRC": ("Vin_src", "Vin"),
        "L2": ("IMPin", "Vcoil_P"), "I_RX": ("Vcoil_P", "Vout"),
        "DIODE1": ("0", "Vbridge_P"), "DIODE2": ("Vbridge_P", "DCout"),
        "I_BRIDGE": ("VoutMatched", "Vbridge_P"),
    })
    return nodes


def main() -> None:
    os.environ.setdefault("HPEESOF_DIR", str(ADS_ROOT))
    sdk_path = str(ADS_ROOT / "tools" / "python" / "packages")
    if sdk_path not in sys.path:
        sys.path.insert(0, sdk_path)
    from keysight.ads import de
    from keysight.ads.de import db_uu

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    # Snapshot the user's latest generated circuit before invoking the API.
    latest_path = WORKSPACE / "netlist.log"
    latest_bytes = latest_path.read_bytes()
    latest_text = latest_bytes.decode("utf-8")
    assert component_nodes(latest_text) == BASELINE_NODES, (
        "Latest netlist.log no longer matches the verified floating receiver; stop for review."
    )
    (ARTIFACT_DIR / "source-latest-floating.net").write_text(latest_text, encoding="utf-8")
    before = original_hashes()

    if de.workspace_is_open():
        assert de.active_workspace().path.samefile(WORKSPACE), (
            "Another workspace is active; the script will not close or switch it."
        )
    else:
        de.open_workspace(WORKSPACE)  # force defaults False; never closes another workspace.
    library = de.get_open_library("MyLibrary_lib")
    assert not library.cell_exists("RX_LoadSweep_20261009"), (
        "Destination cell already exists; refusing to replace any work."
    )
    for cell in ("ParamSweep", "SweepPlan", "MeasEqn"):
        assert de.cellview_exists("ads_simulation", cell, "symbol")

    source = db_uu.open_design(SOURCE, de.db.DesignMode.READ_ONLY)
    source_text = source.generate_netlist()
    (ARTIFACT_DIR / "source-api-before-copy.net").write_text(source_text, encoding="utf-8")
    # This generated netlist is returned as text; it is not written to the workspace log.
    source_nodes = component_nodes(source_text)
    stale_nodes = dict(BASELINE_NODES)
    for name in ("L2", "C6", "DIODE3", "DIODE4"):
        stale_nodes[name] = tuple("0" if node == "IMPin" else node for node in stale_nodes[name])
    assert source_nodes in (BASELINE_NODES, stale_nodes), (
        "Source topology is neither the verified floating circuit nor the known old saved circuit."
    )

    design = db_uu.create_schematic(DESTINATION)
    db_uu.copy_design(source, design)
    repaired = source_nodes == stale_nodes
    if repaired:
        # Only the NEW copy is corrected. Old saved OA has three independently
        # grounded AC-negative segments; deleting grounds alone does not join them.
        for name in ("G6", "G9", "G3"):
            instance = design.instances[name]
            assert instance.cell_name == "GROUND"
            design.edit.delete(instance)
        for name, terminal, label_point in (
            ("L2", 1, (3.7, -2.45)),
            ("C6", 2, (5.45, -2.45)),
            ("DIODE3", 2, (9.45, -2.45)),
            ("DIODE4", 1, (10.05, -2.45)),
        ):
            design.instances[name].inst_term_numbered(terminal).add_label("IMPin", label_point)
    corrected_text = design.generate_netlist()
    assert component_nodes(corrected_text) == BASELINE_NODES, corrected_text
    (ARTIFACT_DIR / "copy-floating-before-probes.net").write_text(corrected_text, encoding="utf-8")

    def exact_wire(points: list[tuple[float, float]]):
        matches = [
            shape for shape in design.shapes if isinstance(shape, db_uu.Line)
            and [(p.x, p.y) for p in shape.get_outline().points] == points
        ]
        assert len(matches) == 1, f"Expected exactly one wire with outline {points}."
        return matches[0]

    def insert_probe(name: str, origin: tuple[float, float], old_points,
                     before_points, after_points) -> None:
        wire = exact_wire(old_points)
        design.edit.delete(wire)
        item = de.ItemInfo.for_placement(design, "ads_rflib:I_Probe:symbol")
        item.inst_name = name
        item.parameters["SaveCurrent"].value = "yes"
        item.parameters["Mode"].value = "0"
        item.parameters["Layer"].value = '"ads_device:ads_label"'
        probe = design.add_instance(item, origin)
        pins = {p.inst_term.term_number: (p.snap_point.x, p.snap_point.y) for p in probe.inst_pins}
        assert pins == {1: origin, 2: (origin[0] + 0.25, origin[1])}, pins
        design.add_wire(before_points)
        design.add_wire(after_points)
        probe.update_item_annotation()

    # Preserve the existing Vin label on the matching side of this probe.
    insert_probe("I_SRC", (-1.5, -1.25),
                 [(0.875, -1.25), (-2.0, -1.25), (-2.0, -1.875)],
                 [(-2.0, -1.875), (-2.0, -1.25), (-1.5, -1.25)],
                 [(-1.25, -1.25), (0.875, -1.25)])
    design.instances["PORT1"].inst_term_numbered(1).add_label("Vin_src", (-2.5, -1.5))

    # The old Vout label is at the split endpoint. Reattach it explicitly.
    for shape in list(design.shapes):
        if isinstance(shape, db_uu.Text) and shape.text_string == "Vout":
            design.edit.delete(shape)
    insert_probe("I_RX", (4.375, -1.25),
                 [(4.25, -1.25), (4.875, -1.25)],
                 [(4.25, -1.25), (4.375, -1.25)],
                 [(4.625, -1.25), (4.875, -1.25)])
    design.instances["L2"].inst_term_numbered(2).add_label("Vcoil_P", (3.8, -0.9))
    design.instances["C1"].inst_term_numbered(1).add_label("Vout", (4.75, -1.5))

    # C6 remains on the matching side. Probe sees the bare bridge's RF load.
    insert_probe("I_BRIDGE", (8.0, -1.25),
                 [(5.875, -1.25), (10.0, -1.25), (10.0, -1.5)],
                 [(5.875, -1.25), (8.0, -1.25)],
                 [(8.25, -1.25), (10.0, -1.25), (10.0, -1.5)])
    design.instances["DIODE2"].inst_term_numbered(1).add_label("Vbridge_P", (9.8, -1.05))
    # Deleting a labeled OA wire also removes its original Text labels and
    # can leave distinct internal net IDs at branch endpoints. Rebind each
    # electrical endpoint by its explicit net name; labels are valid ADS
    # electrical connections even while a GUI is editing the source cell.
    for name, terminal, label, point in (
        ("C3", 1, "Vin", (0.2, -0.95)),
        ("C5", 1, "Vin", (0.6, -1.55)),
        ("I_SRC", 2, "Vin", (-1.2, -1.1)),
        ("C1", 2, "VoutMatched", (5.7, -0.95)),
        ("C6", 1, "VoutMatched", (5.4, -1.55)),
        ("I_BRIDGE", 1, "VoutMatched", (7.0, -0.95)),
        ("I_BRIDGE", 2, "Vbridge_P", (8.3, -0.95)),
        ("DIODE1", 2, "Vbridge_P", (9.2, -1.2)),
    ):
        design.instances[name].inst_term_numbered(terminal).add_label(label, point)
    probe_text = design.generate_netlist()
    assert component_nodes(probe_text) == expected_probe_nodes(), probe_text

    variables = design.instances["VAR1"].vars
    variables["Pin_dBm"] = "26"
    variables["Rload"] = "220 Ohm"
    variables["Ctx_series"] = "61.3 pF"
    variables["Ctx_shunt"] = "438 pF"
    variables["Crx_series"] = "673.3 pF"
    variables["Crx_shunt"] = "1050 pF"
    for name, parameter, expression in (
        ("R1", "R", "Rload"), ("C3", "C", "Ctx_series"),
        ("C5", "C", "Ctx_shunt"), ("C1", "C", "Crx_series"),
        ("C6", "C", "Crx_shunt"),
    ):
        design.instances[name].parameters[parameter].value = expression
        design.instances[name].update_item_annotation()

    hb = design.instances["HB1"]
    assert hb.parameters["Freq"].value == ["13.56 MHz"]
    assert hb.parameters["Order"].value == ["7"]
    # Capture currents and voltages for loss, capacitor and diode stress review.
    for parameter, value in {
        "UseDeviceCurrentNestLevel": "yes", "DeviceCurrentNestLevel": "2",
        "UseDeviceVoltageNestLevel": "yes", "DeviceVoltageNestLevel": "2",
    }.items():
        hb.parameters[parameter].value = value
    hb.update_item_annotation()

    # A repeatable compound SinglePoint form is verified in the installed
    # SweepPlan model. Construct five separate points, not an approximate range.
    plan = design.add_instance("ads_simulation:SweepPlan:symbol", (17.0, 1.0), name="LoadPoints")
    plan_parameter = plan.parameters["SweepPlanParm"]
    form = plan_parameter.definition.formset.forms["SinglePoint"]
    assert len(form.parameters) == 1
    plan_parameter.repeats = [
        de.db.compound_param(form, [de.db.string_param(form.parameters[0].default_value.form_name, value)])
        for value in ("208.33 Ohm", "220 Ohm", "240 Ohm", "470 Ohm", "1 MOhm")
    ]
    plan.parameters["Sort"].value = "SINGLE POINT"
    plan.update_item_annotation()

    inner = design.add_instance("ads_simulation:ParamSweep:symbol", (17.0, -1.0), name="SweepPower")
    for parameter, value in {"SweepVar": '"Pin_dBm"', "Start": "20", "Stop": "26", "Step": "3"}.items():
        inner.parameters[parameter].value = value
    inner.parameters["SimInstanceName"].value = ['"HB1"']
    inner.update_item_annotation()

    outer = design.add_instance("ads_simulation:ParamSweep:symbol", (17.0, -3.0), name="SweepLoad")
    for parameter, value in {"SweepVar": '"Rload"', "UseSweepPlan": "yes", "SweepPlan": '"LoadPoints"'}.items():
        outer.parameters[parameter].value = value
    outer.parameters["SimInstanceName"].value = ['"SweepPower"']
    outer.update_item_annotation()

    measurements = design.add_instance("ads_simulation:MeasEqn:symbol", (0.0, -5.5), name="RXMetrics")
    measurements.parameters["Meas"].value = [
        "Vdc=real(mix(DCout,{0}))",
        "Pdc=Vdc*Vdc/Rload",
        "Pavail=dbmtow(Pin_dBm)",
        "eta_avail=Pdc/Pavail",
        "Z_source=mix(Vin_src,{1})/mix(I_SRC.i,{1})",
        "Z_rx=(mix(Vcoil_P,{1})-mix(IMPin,{1}))/mix(I_RX.i,{1})",
        "Z_bridge=(mix(Vbridge_P,{1})-mix(IMPin,{1}))/mix(I_BRIDGE.i,{1})",
        "Psource_f1=0.5*real(mix(Vin_src,{1})*conj(mix(I_SRC.i,{1})))",
        "Prx_f1=0.5*real((mix(Vcoil_P,{1})-mix(IMPin,{1}))*conj(mix(I_RX.i,{1})))",
        "Pbridge_f1=0.5*real((mix(Vbridge_P,{1})-mix(IMPin,{1}))*conj(mix(I_BRIDGE.i,{1})))",
    ]
    measurements.update_item_annotation()
    # New sweep controllers are saved inactive: first open/simulate verifies
    # the declared 26 dBm/220 ohm operating point. Activate both for the grid.
    inner.deactivate()
    outer.deactivate()

    netlist = design.generate_netlist()
    assert component_nodes(netlist) == expected_probe_nodes()
    assert re.search(r'^Pin_dBm=26$', netlist, re.M)
    assert re.search(r'^Rload=220 Ohm$', netlist, re.M)
    assert 'Bv=4.2 V' in netlist
    assert 'Freq[1]=13.56 MHz Order[1]=7' in netlist
    for value in ("208.33 Ohm", "220 Ohm", "240 Ohm", "470 Ohm", "1 MOhm"):
        assert f"Pt={value}" in netlist
    assert original_hashes() == before, "An original OA/tag file changed before save."
    design.save_design()
    assert original_hashes() == before, "An original OA/tag file changed after save."
    assert sha256(latest_path) == hashlib.sha256(latest_bytes).hexdigest(), (
        "The workspace netlist.log changed; review before proceeding."
    )
    (ARTIFACT_DIR / "RX_LoadSweep_20261009.net").write_text(netlist, encoding="utf-8")
    manifest = {
        "recorded_local_time": datetime.now().astimezone().isoformat(),
        "ads_version": de.product_version(), "workspace": str(WORKSPACE),
        "source": SOURCE, "destination": DESTINATION,
        "corrected_stale_saved_oa_in_copy_only": repaired,
        "original_oa_and_tag_sha256_before": before,
        "original_oa_and_tag_sha256_after": original_hashes(),
        "latest_workspace_netlist_sha256": sha256(latest_path),
        "new_cell_view_path": str(library.cell("RX_LoadSweep_20261009").view("schematic").path),
        "new_cell_oa_sha256": sha256(library.cell("RX_LoadSweep_20261009").view("schematic").path / "sch.oa"),
        "simulation_run_by_this_script": False,
        "sweep_controllers_saved_active": False,
        "defaults": {"Pin_dBm": 26, "Rload_ohm": 220, "frequency_hz": 13.56e6, "hb_order": 7},
        "power_sweep_dBm": [20, 23, 26],
        "load_sweep_ohm": [208.33, 220, 240, 470, 1000000],
    }
    (ARTIFACT_DIR / "creation-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Created and saved {DESTINATION}")
    print(f"Corrected stale saved grounding only in copy: {repaired}")
    print("Verified both original cells' OA/tag hashes unchanged. No simulation was run.")


if __name__ == "__main__":
    main()

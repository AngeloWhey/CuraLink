"""Create an explicitly unexecuted native authored charger-load candidate.

Copies the completed BAT54 receiver. Preserves all existing cells. No simulator
or license retry is performed. This is not a BQ25185, cell or protection model.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import runpy
import sys

HERE = Path(__file__).resolve().parent
base = runpy.run_path(str(HERE / "create_rx_load_sweep.py"))
WORKSPACE = base["WORKSPACE"]
SOURCE = "MyLibrary_lib:RX_BAT54_LoadSweep_20261009:schematic"
DESTINATION = "MyLibrary_lib:RX_ChargerLoad_20261009:schematic"
CHARGER_DIR = HERE.parent / "charger"
LAW_PATH = CHARGER_DIR / "native-raw-SDD-I-1-0.txt"
PARAMETER_PATH = CHARGER_DIR / "native-raw-SDD-parameters.txt"


def cell_hashes(library):
    result = dict(base["original_hashes"]())
    for name in ("RX_LoadSweep_20261009", "RX_BAT54_LoadSweep_20261009"):
        path = library.cell(name).view("schematic").path / "sch.oa"
        result[str(path)] = base["sha256"](path)
    return result


def verify_netlist(netlist: str, law: str):
    expected = base["expected_probe_nodes"]()
    del expected["R1"]
    expected["I_Probe1"] = ("DCout", "RAW_LOAD")
    assert base["component_nodes"](netlist) == expected, netlist
    line = next(line for line in netlist.splitlines() if line.startswith("SDD:ChargerRawLoad"))
    match = re.fullmatch(r"SDD:ChargerRawLoad\s+RAW_LOAD\s+0\s+I\[1,0\]=(.*?)\s*", line)
    assert match and match.group(1) == law, netlist
    assert "C:ChargerCinRawEq  RAW_LOAD 0 C=2.2 uF" in netlist, netlist
    assert "R:R1" not in netlist
    assert "Rload=" not in netlist and "SweepVar=\"Rload\"" not in netlist
    assert "Pdc=Vdc*Idc" in netlist and "Pdc=Vdc*Vdc/Rload" not in netlist
    assert 'Freq[1]=13.56 MHz Order[1]=31' in netlist
    assert re.search(r"^Pin_dBm=23.5$", netlist, re.M)
    assert all(re.search(rf"^{re.escape(name)}={re.escape(value)}$", netlist, re.M)
               for name, value in {"VBAT": "3.7", "IPHASE": "0.02",
                                   "ICTRL": "0.0008", "VPATH": "0.28"}.items())


def main():
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
    assert not library.cell_exists("RX_ChargerLoad_20261009"), "Refusing to replace existing charger-load cell."
    before = cell_hashes(library)
    workspace_log_hash = base["sha256"](WORKSPACE / "netlist.log")
    law = LAW_PATH.read_text(encoding="utf-8").strip()
    assert len(law.splitlines()) == 1 and "_v1" in law and "VPATH" in law
    parameters = dict(line.split("=", 1) for line in PARAMETER_PATH.read_text(encoding="utf-8").splitlines() if line.strip())
    assert len(parameters) == 13
    source = db_uu.open_design(SOURCE, de.db.DesignMode.READ_ONLY)
    assert base["component_nodes"](source.generate_netlist()) == base["expected_probe_nodes"]()
    design = db_uu.create_schematic(DESTINATION)
    db_uu.copy_design(source, design)

    resistor = design.instances["R1"]
    origin = resistor.origin
    assert (origin.x, origin.y) == (14.0, -1.875)
    design.edit.delete(resistor)
    sdd = design.add_instance("ads_datacmps:SDD1P:symbol", (origin.x, origin.y),
                              name="ChargerRawLoad", angle=-90)
    sdd.parameters["SDD"].value = [["1", "0", law]]
    pins = {p.inst_term.term_number: (p.snap_point.x, p.snap_point.y) for p in sdd.inst_pins}
    assert pins == {1: (14.0, -1.875), 2: (14.0, -2.875)}, pins
    sdd.inst_term_numbered(1).add_label("RAW_LOAD", (13.7, -1.55))
    design.instances["I_Probe1"].inst_term_numbered(2).add_label("RAW_LOAD", (13.05, -2.2))
    sdd.update_item_annotation()

    # At fixed VPATH, the ideal extra CHG_IN capacitor has the same RF voltage
    # as raw. Parallel 2.2 uF here matches the explicit fixture's 3.2 uF total.
    capacitor = design.add_instance("ads_rflib:C:symbol", (16.0, -1.875),
                                    name="ChargerCinRawEq", angle=-90)
    capacitor.parameters["C"].value = "2.2 uF"
    capacitor.inst_term_numbered(1).add_label("RAW_LOAD", (15.65, -1.55))
    design.add_instance("ads_rflib:GROUND:symbol", (16.0, -2.875), name="G_ChargerCin")
    capacitor.update_item_annotation()

    del design.instances["VAR1"].vars["Rload"]
    charger_vars = design.add_var_instance((17.0, 4.0), name="VAR_ChargerFixture")
    charger_vars.vars.update(parameters)
    del charger_vars.vars["X"]  # retire the new VAR item's unrelated placeholder.
    # Retire the old resistor-load study. Retain the disabled source-power
    # controller for an explicit future study within the model's voltage range.
    for name in ("SweepLoad", "LoadPoints"):
        design.edit.delete(design.instances[name])
    power_sweep = design.instances["SweepPower"]
    power_sweep.deactivate()
    power_sweep.move((11.0, 4.0))  # from (17,-1) to (28,3), beyond load annotations.

    for shape in list(design.shapes):
        if isinstance(shape, db_uu.Text) and shape.text_string.startswith("BAT54 MANUFACTURER-MODEL CANDIDATE."):
            design.edit.delete(shape)
    prototype = next(shape for shape in design.shapes if isinstance(shape, db_uu.Text))
    design.add_text(prototype.layer_id,
                    "AUTHORED STATIC CHARGER-LOAD CANDIDATE: UNEXECUTED.\n"
                    "No actual BQ25185, cell, receiver OVP, eFuse clamp/cutoff or system dynamics model.\n"
                    "Fixed 0.28 V path-drop equivalence applies only to positive steady-state operation.\n"
                    "CHARGE: MCU/AFE OFF. Raw probe includes charger IQ + charge demand + control + overhead.\n"
                    "CHG_IN_EQ=VRAW-0.28 V; approximation domain 0 to 5.5 V at CHG_IN_EQ.\n"
                    "BAT54 physical reverse rating 30 V; model breakdown fit 50 V.\n"
                    "Native netlist checked; NO solved charger operating-point claim.",
                    (0.0, -10.0), prototype.font_name, 0.2)

    # The single raw-equivalent SDD gives exact aggregate waveform current.
    # Separate charger/control current readouts below evaluate static law at
    # the DC voltage and are explicitly estimates, not measured branch currents.
    design.instances["RXMetrics"].parameters["Meas"].value = [
        "Vdc=real(mix(DCout,{0}))", "Idc=real(mix(I_Probe1.i,{0}))",
        "Pdc=Vdc*Idc", "Pavail=dbmtow(Pin_dBm)", "eta_avail=Pdc/Pavail",
        "CHG_IN_DC_EQ=Vdc-VPATH",
        "Icharge_at_DC=CHARGE_ALLOWED*IPHASE*max(0,min(1,(CHG_IN_DC_EQ-VSTART)/WNUM))*max(0,min(1,(CHG_IN_DC_EQ-VDPM)/WDPM))",
        "IchargerIQ_at_DC=IQSLEEP*max(0,min(1,CHG_IN_DC_EQ/3.6))+(IQACTIVE-IQSLEEP)*max(0,min(1,(CHG_IN_DC_EQ-VWAKE)/WNUM))",
        "Icharger_input_at_DC=Icharge_at_DC+IchargerIQ_at_DC",
        "Icontrol_at_DC=ICTRL*max(0,min(1,(CHG_IN_DC_EQ-VBAT)/WOR))",
        "Pcharger_input_DC_EST=CHG_IN_DC_EQ*Icharger_input_at_DC",
        "Z_source=mix(Vin_src,{1})/mix(I_SRC.i,{1})",
        "Z_rx=(mix(Vcoil_P,{1})-mix(IMPin,{1}))/mix(I_RX.i,{1})",
        "Z_bridge=(mix(Vbridge_P,{1})-mix(IMPin,{1}))/mix(I_BRIDGE.i,{1})",
        "Psource_f1=0.5*real(mix(Vin_src,{1})*conj(mix(I_SRC.i,{1})))",
        "Prx_f1=0.5*real((mix(Vcoil_P,{1})-mix(IMPin,{1}))*conj(mix(I_RX.i,{1})))",
        "Pbridge_f1=0.5*real((mix(Vbridge_P,{1})-mix(IMPin,{1}))*conj(mix(I_BRIDGE.i,{1})))",
    ]
    design.instances["RXMetrics"].update_item_annotation()
    text = design.generate_netlist()
    verify_netlist(text, law)
    assert cell_hashes(library) == before
    design.save_design()
    (HERE / "RX_ChargerLoad_20261009.net").write_text(text, encoding="utf-8")
    assert cell_hashes(library) == before
    assert base["sha256"](WORKSPACE / "netlist.log") == workspace_log_hash
    path = library.cell("RX_ChargerLoad_20261009").view("schematic").path
    manifest = {
        "recorded_local_time": datetime.now().astimezone().isoformat(),
        "workspace": str(WORKSPACE), "source": SOURCE, "destination": DESTINATION,
        "native_view_path": str(path), "new_cell_oa_sha256": base["sha256"](path / "sch.oa"),
        "original_and_completed_copy_hashes_before": before,
        "original_and_completed_copy_hashes_after": cell_hashes(library),
        "law_source": str(LAW_PATH), "law_source_sha256": base["sha256"](LAW_PATH),
        "parameter_source": str(PARAMETER_PATH), "parameter_source_sha256": base["sha256"](PARAMETER_PATH),
        "parameters": parameters, "raw_SDD_I_1_0": law,
        "source_power_dBm": 23.5, "frequency_Hz": 13560000, "HB_order": 31,
        "reservoir_C_F": 1e-6, "extra_raw_equivalent_C_F": 2.2e-6,
        "SDD_terminal_nodes": ["RAW_LOAD", "0"],
        "existing_DC_probe_positive_current": "DCout to RAW_LOAD",
        "native_netlist_syntax_and_topology_verified": True,
        "actual_SDD_simulation_completed": False,
        "fixture_status": "Authored static unexecuted candidate; no actual charger/cell/OVP model",
        "approximation_CHG_IN_voltage_domain_V": [0, 5.5],
        "equivalence_limit": "Positive steady-state RAW only; fixed path drop and ideal capacitance",
        "load_sweep_retired": True, "power_sweep_saved_active": False,
        "separate_current_readouts": "Charger/control static-law estimates at DC voltage, not solved branch waveforms",
    }
    (HERE / "ChargerLoad-creation-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Created and saved", DESTINATION)
    print("Native SDD law/topology checked; all existing cells preserved by hash equality.")
    print("NO simulation attempted. Authored static candidate; no solved charger operating point.")


if __name__ == "__main__":
    main()

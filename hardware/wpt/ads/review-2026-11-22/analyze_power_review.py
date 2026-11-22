"""Read-only summary of the completed ADS fixed-coil power review."""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    cases = json.loads((HERE / "power-matrix.json").read_text())
    with (HERE / "sdd-dc-iv.csv").open(newline="") as stream:
        points = list(csv.DictReader(stream))
    def nearest(voltage):
        return min(points, key=lambda p: abs(float(p["VIN_SWEEP"])-voltage))
    def number(point, name):
        return complex(point[name]).real
    zero, weak, full = nearest(0), nearest(3), nearest(5)
    sign_checks = {
        "zero_voltage_charger_current_A": number(zero, "Charger_Probe.i"),
        "zero_voltage_control_current_A": number(zero, "Control_Probe.i"),
        "weak_3V_charger_current_A": number(weak, "Charger_Probe.i"),
        "5V_charger_current_A": number(full, "Charger_Probe.i"),
        "5V_control_current_A": number(full, "Control_Probe.i"),
        "all_charger_currents_nonnegative": min(number(p,"Charger_Probe.i") for p in points)>=-1e-12,
    }
    assert abs(sign_checks["zero_voltage_charger_current_A"])<1e-9
    assert abs(sign_checks["zero_voltage_control_current_A"])<1e-9
    assert abs(sign_checks["5V_charger_current_A"]-.02075)<1e-8
    assert sign_checks["all_charger_currents_nonnegative"]
    assert sign_checks["weak_3V_charger_current_A"]<30e-6
    summary = {
        "date":"2026-11-22", "new_ADS_simulation":True,
        "fixed_coils":{"frequency_Hz":13.56e6,"L_TX_H":2.49e-6,"R_TX_ohm":1.8,"L_RX_H":.330e-6,"R_RX_ohm":.399,"k":.0662},
        "SDD_DC_checks":sign_checks,
        "matrix_points":len(cases),
        "out_of_authored_voltage_domain_points":sum(p["out_of_model_domain"] for p in cases),
        "max_absolute_RF_power_balance_residual_W":max(abs(p["RF_power_balance_residual_W"]) for p in cases),
        "raw_receiver_OVP_in_model":False,"actual_charger_or_cell_model":False,
        "build_release":False,
        "limits":"Static authored I-V, assumed 0.28V path drop, ideal capacitors and carrier-derived constant coil R/L/k. Outside-domain points are rejected diagnostics, not predictions of real high-voltage charger behavior.",
        "representative_cases":[{key:p[key] for key in ("Pin_dBm","battery_voltage_V","BASE_PHASE_A","OVERHEAD_sensitivity","commanded_charge_current_A","derived_charge_current_mean_A","Vdc_V","CHG_IN_V","raw_average_power_W","out_of_model_domain")} for p in cases if p["battery_voltage_V"]==4.1 and p["BASE_PHASE_A"] in (0,.02)],
    }
    (HERE / "power-summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({key:summary[key] for key in ("matrix_points","out_of_authored_voltage_domain_points","max_absolute_RF_power_balance_residual_W","SDD_DC_checks")},indent=2))


if __name__ == "__main__":
    main()

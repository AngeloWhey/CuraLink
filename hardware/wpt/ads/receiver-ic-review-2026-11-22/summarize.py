"""Recreate handoff metrics from CSVs using ordinary Python on either laptop."""
import csv
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def rows(stage):
    with (HERE/"bridge-runs"/stage/"results.csv").open(newline="",encoding="ascii") as f:
        return {r["label"]:r for r in csv.DictReader(f)}


def main():
    matrix=rows("matrix")
    loads=("full_120mW","full_plus_5mA_status","full_plus_15mA_status","2mA_taper","complete_field_on","regulator_only")
    power_table={p:{load:float(matrix[f"demand_{p}_{load}"]["RAW_min_V"]) for load in loads}
                 for p in (20,23,23.5,24,25,26,27)}
    tolerances={}
    for pct in (2,5):
        subset=[r for k,r in matrix.items() if k.startswith(f"cap_{pct}pct_")]
        xv=[float(r["RAW_min_V"]) for r in subset]
        tolerances[pct]={"cases":len(xv),"min_RECT_DC_V":min(xv),"max_RECT_DC_V":max(xv),
                         "number_at_or_above_6V":sum(v>=6 for v in xv)}
    stress={}
    for name in ("TX_series_Vpk","RX_series_Arms","RX_shunt_Arms","winding_RX_mW","bridge_reverse_peak_V","junction_forward_peak_mA"):
        key=max(matrix,key=lambda k:float(matrix[k][name]))
        stress[name]={"value":float(matrix[key][name]),"fixture":key}
    assembly={"source_dBm_to_min_RECT_DC_V_for_each_load":power_table,
              "capacitor_tolerance_endpoints_at_25dBm_24mA":tolerances,
              "max_in_unclamped_matrix":stress}
    comp={}
    for label in rows("order63"):
        comp[label]={}
        for param in ("RAW_mean_V","RAW_min_V","bridge_reverse_peak_V","junction_forward_peak_mA"):
            v15=float(rows("order15")[label][param])
            v31=float(matrix[label][param])
            v63=float(rows("order63")[label][param])
            comp[label][param]={"HB15":v15,"HB31":v31,"HB63":v63,"31_to_63_difference":v31-v63}
    assembly["harmonic_convergence"]=comp
    tvs=list(rows("tvs").values())
    tvs_on=[r for r in tvs if float(r["Vbr1mA"])<=18.5]
    tvs_clean=[r for r in tvs if float(r["Vbr1mA"])>18.5]
    def worst(items,name):
        r=max(items,key=lambda x:float(x[name]))
        return {"value":float(r[name]),"fixture":r["label"]}
    assembly["TVS_near_open"]={"fitted_cases":len(tvs_on),
                                "without_tvs_cases":len(tvs_clean),
                                "largest_clamped_RAW_peak_V":worst(tvs_on,"RAW_max_V"),
                                "largest_unclamped_RAW_peak_V":worst(tvs_clean,"RAW_max_V"),
                                "largest_TVS_steady_dissipation_mW":worst(tvs_on,"TVS_mean_mW"),
                                "largest_TVS_steady_current_mA":worst(tvs_on,"TVS_mean_mA"),
                                "largest_winding_loss_with_TVS_mW":worst(tvs_on,"winding_RX_mW")}
    (HERE/"handoff-metrics.json").write_text(json.dumps(assembly,indent=2)+"\n",encoding="ascii")


if __name__=="__main__":
    main()

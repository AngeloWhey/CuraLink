"""Review source from the saved native view, run HB and package portable outputs."""
from pathlib import Path
import csv
import json
import os
import shutil
import subprocess
import tempfile
import time

import numpy as np
from keysight.ads import dataset
from keysight.edatoolbox import ads
from create_cells import HERE, WS, SDK, TOP, PART, LIB, de, db


def main():
    de.open_workspace(WS)
    for name in (TOP,PART):
        view=db.open_design(f"{LIB}:{name}:schematic",de.db.DesignMode.READ_ONLY)
        if name==TOP:
            text=view.generate_netlist()
            deck=HERE/"native-fresh-readback.ckt"
            deck.write_text(text)
            assert f"{PART}:U_RX  0 AC1 AC2 RAW" in text and 'K=0.0662' in text
        view.print_design(str(HERE/(name+".pdf")))
    de.close_workspace()
    os.chdir(HERE)
    matrix=next((HERE.parent/"receiver-ic-review-2026-11-22/bridge-runs/matrix").glob("*.csv"))
    nominal=next(r for r in csv.DictReader(matrix.open()) if r["label"]=="demand_25_full_120mW")
    env=ads.CircuitSimulator(hpeesof_dir=str(SDK))._env
    with tempfile.TemporaryDirectory(prefix="curalink_native_hb_") as temp:
        for attempt in range(43):
            process=subprocess.run([str(SDK/"bin/hpeesofsim.exe"),str(deck),"--dataset-name="+TOP,"-T4"],
                                   cwd=temp,env=env,capture_output=True,text=True,timeout=120)
            log=process.stdout+process.stderr
            if process.returncode==0 or "Licensed number of users already reached" not in log: break
            time.sleep(4)
        (HERE/"simulator.log").write_text(log)
        process.check_returncode()
        ds=Path(temp)/(TOP+".ds")
        with dataset.open(ds) as data:
            key=next(k for k in data.varblock_names if k.endswith(".HB"))
            table=data[key].to_dataframe().reset_index().sort_values("freq")
        assert np.allclose(table.freq,np.arange(32)*13.56e6)
        cols=["freq","RAW","RXPLUS","AC2","AC1","GEN","IDC.i","PRX.i","PTX.i"]
        table[cols].to_csv(HERE/"native-harmonics.csv",index=False)
        raw=table["RAW"].to_numpy();z=(table.RXPLUS.iloc[1]-table.AC2.iloc[1])/table["PRX.i"].iloc[1]
        mean=float(raw[0].real)
        t=np.arange(2048)/2048
        wave=mean+np.real(np.exp(2j*np.pi*np.outer(t,np.arange(1,32)))@raw[1:])
        p_mw=1000*mean*table["IDC.i"].iloc[0].real
        summary=dict(ADS_cell=f"{LIB}:{TOP}:schematic",HB_order=31,frequency_Hz=13.56e6,
                     mean_RAW_V=mean,minimum_RAW_V=float(wave.min()),power_RAW_mW=float(p_mw),
                     load_DC_mA=float(table["IDC.i"].iloc[0].real*1000),Z_RX_ohm=[z.real,z.imag],
                     reference_matrix_label=nominal["label"],matrix_RAW_V=float(nominal["RAW_mean_V"]),
                     matrix_RAW_mW=float(nominal["raw_load_mW"]))
        print(json.dumps(summary,indent=2))
        assert abs(mean-summary["matrix_RAW_V"]) < .015 and abs(p_mw-summary["matrix_RAW_mW"]) < .4
        assert abs(z.real-float(nominal["transform_at_RX_R_ohm"])) <.01 and abs(z.imag-float(nominal["transform_at_RX_X_ohm"])) <.03
        shutil.copy2(ds,WS/"data"/ds.name)
        (HERE/"native-results.json").write_text(json.dumps(summary,indent=2)+"\n")


if __name__=="__main__":
    main()

"""Verify four-channel steady DC rejection in the recommended coax fixture."""
import json
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
from keysight.ads import dataset
from keysight.edatoolbox import ads

from check_afe import HERE, ADS_ROOT, make_deck


def main():
    circuit = make_deck("four-coax-native", 47, 0).split("OutputPlan:Out ")[0]
    offset_source = "V_Source:vch1 src_ch1 0 Vdc=0"
    assert circuit.count(offset_source) == 1
    circuit = circuit.replace(offset_source, "V_Source:vch1 src_ch1 0 Vdc=OFFSET")
    # Apply one declared leakage across every ten-nanofarad CH/REF DC block.
    caps = re.findall(r"^Cap_L:(c\d+) (\S+) (\S+) C=1e-08$", circuit, re.M)
    assert len(caps) == 13
    circuit += "\nOFFSET=0\n" + "\n".join(f"R:rleak_{ref} {a} {b} R=10e9" for ref,a,b in caps)
    circuit += '''
OutputPlan:Out Type="Output" UseNodeNestLevel=yes NodeNestLevel=1 UseCurrentNestLevel=yes CurrentNestLevel=1
DC:DC1 MaxIters=200 StatusLevel=1 OutputPlan="Out"
SweepPlan:Offsets Start=-0.1 Stop=0.1 Step=0.025
ParamSweep:SweepOffset SimInstanceName[1]="DC1" SweepVar="OFFSET" SweepPlan="Offsets" StatusLevel=1
'''
    out = HERE / "coax-offset"
    out.mkdir(exist_ok=True)
    deck = out / "afe.ckt"
    deck.write_bytes(circuit.encode())
    simulator = ads.CircuitSimulator(hpeesof_dir=str(ADS_ROOT))
    with tempfile.TemporaryDirectory(prefix="curalink_ads_offset_") as temp:
        proc = subprocess.run([str(ADS_ROOT/"bin/hpeesofsim.exe"), str(deck), "--dataset-name=offset", "-T4"],
                              cwd=temp, env=simulator._env, capture_output=True, text=True, timeout=500)
        (out/"simulator.log").write_text(proc.stdout+proc.stderr)
        proc.check_returncode()
        with dataset.open(Path(temp)/"offset.ds") as data:
            table = data["SweepOffset.DC1.DC"].to_dataframe().reset_index().sort_values("OFFSET")
    columns = ["OFFSET","src_ch1","src_ref","ch1_plus","ch1_pre","ref_pre","vmid","adc_in_1","adc_in_2","adc_in_3","adc_in_4","vdd.i"]
    assert np.allclose(table["OFFSET"],np.linspace(-.1,.1,9)) and np.allclose(table.src_ch1,table["OFFSET"])
    assert np.isfinite(table[columns]).all().all()
    table[columns].to_csv(out/"dc.csv", index=False)
    result = dict(excitation="CH1 DC offset, other inputs and REF quiet", source_offsets_V=table["OFFSET"].tolist(),
                  leakage_ohm_per_10nF_coupler=1e10, modeled_couplers=len(caps),
                  adc1_change_full_sweep_uV=float(np.ptp(table.adc_in_1)*1e6),
                  preamp1_change_full_sweep_mV=float(np.ptp(table.ch1_pre)*1000),
                  steady_state_only=True)
    (out/"results.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()

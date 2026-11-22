"""Fresh passive ADS consistency check; fixed paper coils, original 50-ohm match."""
from pathlib import Path
import json
import math
import numpy as np
import run_power_review as review

HERE = Path(__file__).resolve().parent
DECK = '''Options ResourceUsage=yes UseNutmegFormat=no EnableOptim=no
Port:P1 TX 0 Num=1 Z=50 Ohm Noise=no
C:TX_SHUNT TX 0 C=438 pF
C:TX_SERIES TX TX_COIL C=61.3 pF
L:L1 TX_COIL 0 L=2.49 uH R=1.8 Noise=no
L:L2 0 RX_COIL L=0.330 uH R=0.399 Noise=no
Mutual:LINK K=0.0662 Inductor1="L1" Inductor2="L2"
C:RX_SERIES RX_COIL RX C=673.3 pF
C:RX_SHUNT RX 0 C=1050 pF
Port:P2 RX 0 Num=2 Z=50 Ohm Noise=no
S_Param:SP1 SweepVar="freq" SweepPlan="Carrier" OutputPlan="SP_Output"
SweepPlan:Carrier Pt=13.56 MHz
OutputPlan:SP_Output Type="Output" UseNodeNestLevel=yes NodeNestLevel=2
'''


def main():
    omega = 2*math.pi*13.56e6
    mutual = .0662*math.sqrt(2.49e-6*.330e-6)
    coil = np.array([[1.8+1j*omega*2.49e-6, -1j*omega*mutual], [-1j*omega*mutual, .399+1j*omega*.330e-6]])
    series = coil + np.diag([1/(1j*omega*61.3e-12), 1/(1j*omega*673.3e-12)])
    zport = np.linalg.inv(np.linalg.inv(series)+np.diag([1j*omega*438e-12, 1j*omega*1050e-12]))
    scattering = (zport-50*np.eye(2)) @ np.linalg.inv(zport+50*np.eye(2))
    rx_load = 1/(1/50+1j*omega*1050e-12)+1/(1j*omega*673.3e-12)
    report = {"date":"2026-11-22", "fixed_coils":True, "frequency_Hz":13.56e6, "source_and_measurement_ports_ohm":50,
              "secondary_load_seen_by_coil_ohm":{"real":rx_load.real,"imag":rx_load.imag},
              "analytical_S21_power":float(abs(scattering[1,0])**2), "analytical_S11_magnitude":float(abs(scattering[0,0]))}
    simulator = review.rr.ads.CircuitSimulator(hpeesof_dir=str(review.rr.ADS_ROOT))
    frame, directory, status = review.run_case(simulator, "published_passive_link", DECK, "SP1.SP")
    print("S-parameter columns",frame.columns.tolist(),flush=True)
    s21 = complex(frame["S[2,1]"].iloc[0])
    s11 = complex(frame["S[1,1]"].iloc[0])
    report.update({"actual_ADS_simulation":True,"ADS_S21_power":abs(s21)**2,"ADS_S21_dB":20*math.log10(abs(s21)),
                   "ADS_input_return_loss_dB":-20*math.log10(abs(s11)), "ADS_frequency_Hz":float(frame["freq"].iloc[0]),
                   "analytical_power_agreement_absolute":abs(abs(s21)**2-report["analytical_S21_power"]),
                   "source_dataset":str(directory/"power-review.ds"),
                   "limits":"Passive carrier-frequency R-L-M check, not rectifier/charger efficiency or hardware reproduction."})
    assert report["ADS_frequency_Hz"]==13.56e6
    assert report["analytical_power_agreement_absolute"]<1e-8
    (HERE/"published-link-check.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()

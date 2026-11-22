"""Extract a biased, small-signal three-port for use in the ADS AFE deck."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ltspice/afe"))
from read_ltspice_raw import read_raw

EXE = Path(os.environ["LOCALAPPDATA"]) / "Programs/ADI/LTspice/LTspice.exe"
PORTS = ("plus", "gain_return", "pre_out")


def extract():
    columns = []
    for active in range(3):
        text = ["MAX44280 gain-11 AC fixture", ".lib MAX44280.sub",
                ".options numdgt=10 plotwinsize=0", ".temp 27",
                "Vdd avdd 0 3", "Vbias vmid 0 1.5",
                "Lbias1 plus vmid 1e10", "Lbias2 gain_return vmid 1e10",
                "Rf pre_out minus 10k", "Rg minus gain_return 1k",
                "Xu plus minus avdd 0 pre_out avdd MAX44280"]
        for i, node in enumerate(PORTS):
            text.extend([f"Vp{i} src{i} 0 DC 0 AC {int(i == active)}",
                         f"Rp{i} src{i} p{i} 50", f"Cp{i} p{i} {node} 1000"])
        text.extend([".ac dec 100 10 100Meg", ".save V(p0) V(p1) V(p2)", ".end"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "stage.cir").write_text("\n".join(text)+"\n")
            subprocess.run([EXE, "-b", "stage.cir"], cwd=path, timeout=120, check=True)
            data = read_raw(path / "stage.raw")
        freq = data.data[:, 0].real
        columns.append(np.array([2*data.trace(f"V(p{i})") - int(i == active) for i in range(3)]))
    matrix = np.stack(columns, axis=1)
    with (HERE / "max44280-gain11.s3p").open("w") as out:
        out.write("! Simulated linearized three-port, 3.0 V supply, 1.5 V common mode, 27 C.\n")
        out.write("! 1 noninverting input, 2 bottom of 1k gain resistor, 3 output. Includes 10k/1k network.\n")
        out.write("! Touchstone v1 three-port row order S11 S12 S13 / S21 S22 S23 / S31 S32 S33.\n# Hz S RI R 50\n")
        for k, frequency in enumerate(freq):
            for i in range(3):
                prefix = f"{frequency:.13g} " if i == 0 else "  "
                pairs = [f"{v.real:.16g} {v.imag:.16g}" for v in matrix[i, :, k]]
                out.write(prefix + " ".join(pairs) + "\n")


if __name__ == "__main__":
    extract()

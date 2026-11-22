"""Evaluate input capacitance neutralization on the actual four-channel LTspice fixture."""
import csv
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
REV = HERE.parent
sys.path.insert(0, str(REV / "ltspice" / "afe"))
from read_ltspice_raw import read_raw

BASE = REV / "ads-closeout-2026-11-22/ltspice-noise/with-emulator.cir"
EXE = Path(os.environ["LOCALAPPDATA"]) / "Programs/ADI/LTspice/LTspice.exe"


def make_deck(line_pf, trim_pf, r_source, drive, isolated_bias=False):
    lines = []
    for line in BASE.read_text().splitlines():
        fields = line.lower().split()
        if not fields:
            continue
        name = fields[0]
        if name in {".save", ".end", ".noise"}:
            continue
        if name == ".include":
            line = f'.include "{(BASE.parent / fields[1]).resolve()}"'
        if name.startswith("c_trace_"):
            line = " ".join(fields[:-1] + [f"{line_pf}p"])
        if name.startswith("r_source_"):
            line = " ".join(fields[:-1] + [str(r_source)])
        if isolated_bias and len(fields) == 4 and fields[2:] == ["vmid", "22000000"]:
            line = f"{name} {fields[1]} vmid_buf {fields[3]}"
        if name in {"vref", "vch1"}:
            line = " ".join(fields[:3]) + (" DC 0 AC 1" if name == drive else " 0")
        lines.append(line)
    for ch in ["ch1", "ch2", "ch3", "ch4", "ref"]:
        if trim_pf:
            lines.append(f"c_neut_{ch} {ch}_pre {ch}_plus {trim_pf}p")
    ch = "ch1" if drive == "vch1" else "ref"
    feed = "genout_ch1" if ch == "ch1" else "src_ref"
    lines.extend([f".save V({feed}) V(ffc_{ch}) V(adc_in_1) V({ch}_pre)",
                  ".ac dec 90 100 10Meg", ".end"])
    return "\n".join(lines) + "\n", ch, feed


def evaluate(tmp, line_pf, trim_pf, r_source, drive, isolated_bias=False):
    deck, ch, feed = make_deck(line_pf, trim_pf, r_source, drive, isolated_bias)
    (tmp / "afe.cir").write_text(deck)
    subprocess.run([EXE, "-b", "afe.cir"], cwd=tmp, check=True, timeout=90)
    raw = read_raw(tmp / "afe.raw")
    f = raw.data[:, 0].real
    v = raw.trace(f"V(ffc_{ch})")
    y = (raw.trace(f"V({feed})") - v) / (r_source * v)
    gain = raw.trace("V(adc_in_1)")
    # Include the two exact band edges by interpolating complex admittance.
    band = np.r_[300., f[(f > 300) & (f < 7000)], 7000.]
    y_band = np.interp(band, f, y)
    pre = abs(raw.trace(f"V({ch}_pre)"))
    return dict(line_pF=line_pf, feedback_pF=trim_pf, source_ohms=r_source, drive=ch,
                band_min_Z_Mohm=1e-6/max(abs(y_band)), Z7k_Mohm=1e-6/abs(y_band[-1]),
                band_min_G_nS=1e9*min(y_band.real), Ceff7k_pF=1e12*y_band[-1].imag/(2*np.pi*7000),
                ADC_gain_1k=abs(np.interp(1000., f, gain)), pre_peak_gain=max(pre),
                pre_peak_freq_Hz=f[np.argmax(pre)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--isolated-bias", action="store_true",
                        help="Connect only the five high-value bias resistors to VMID_BUF.")
    args = parser.parse_args()
    # Tolerances on the board trace are independent of the fitted feedback capacitor.
    cases = [(line, trim, 47000, "vch1") for line in (1, 2, 3)
             for trim in (0., .47, .56, .62, .68, .74, .82)]
    cases += [(2, trim, r, drive) for trim in (0., .62, .68, .74)
              for r in (47000, 1000000, 10000000) for drive in ("vref", "vch1")
              if r != 47000 or drive != "vch1"]
    if args.isolated_bias:
        cases = [(line, trim, 47000, "vch1") for line in (1, 2, 3)
                 for trim in (0., .62, .68, .74)]
        cases += [(2, .68, r, drive) for r in (47000, 100000, 1000000, 10000000)
                  for drive in ("vref", "vch1") if r != 47000 or drive != "vch1"]
    def one(case):
        with tempfile.TemporaryDirectory() as folder:
            return evaluate(Path(folder), *case, args.isolated_bias)

    with ThreadPoolExecutor(max_workers=3) as workers:
        result = list(workers.map(one, cases))
    filename = "isolated-bias.csv" if args.isolated_bias else "results.csv"
    with (HERE / filename).open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=result[0])
        writer.writeheader()
        writer.writerows(result)


if __name__ == "__main__":
    main()

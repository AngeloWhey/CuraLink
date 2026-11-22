"""Use LTspice's native noise support for the four-coax TI-family AFE models."""
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "ltspice-noise"
LTSPICE = os.environ.get("CURALINK_LTSPICE_EXE", str(Path(os.environ["LOCALAPPDATA"]) / "Programs/ADI/LTspice/LTspice.exe"))
sys.path.insert(0, str(HERE.parent/"ltspice/afe"))
from read_ltspice_raw import read_raw


def run(name, body):
    start = """* CuraLink four-channel fixture; original TI-family equations.
.include ../../ltspice/afe/models/tlv9002-namespaced.lib
.include ../../ltspice/afe/models/tlv9052-namespaced.lib
.options numdgt=8 plotwinsize=0
.temp 27
"""
    path = OUT/(name+".cir")
    path.write_text(start+body+"\n.save V(inoise) V(onoise)\n.end\n")
    proc = subprocess.run([LTSPICE,"-b","-ascii",path.name],cwd=OUT, timeout=180)
    proc.check_returncode()
    log = path.with_suffix(".log").read_text(errors="replace")
    if "Total elapsed time:" not in log or re.search(r"(?:fatal error|time step too small|unknown parameter|unknown subcircuit)",log,re.I):
        raise RuntimeError(f"Incomplete or rejected LTspice model in {path.name}")
    # The local LTspice writes Windows-1252 half-power units in its ASCII
    # noise headers. Decode a temporary copy to use the project's UTF-8 reader.
    with tempfile.TemporaryDirectory() as temp:
        portable = Path(temp)/"noise.raw"
        portable.write_bytes(path.with_suffix(".raw").read_bytes().decode("cp1252").encode("utf-8"))
        raw = read_raw(portable)
    return tuple(np.real(raw.trace(k)) for k in ["frequency","V(inoise)","V(onoise)"])


def make_topology(disable_sources):
    # This LTspice circuit comes directly from the standalone ADS fixture's
    # passive and amplifier instances. Each source-equivalent stays in place.
    source = (HERE/"coax-resistor-board-end/afe.ckt").read_text()
    top = source[source.index("R:r1001 "):source.index("V_Source:vdd")].splitlines()
    converted = []
    quads = 0
    for line in top:
        m = re.match(r"(?:R|Cap_L):(\S+) (\S+) (\S+) [RC]=(\S+)$", line)
        if m:
            ref, n1, n2, val = m.groups()
            if val == "909000":
                val = "910000"
            # Match native R605 = 47k directly to local reference.
            if ref == "r_gen_ref":
                continue
            if ref == "r_source_ref":
                n1 = "src_ref"
            quiet = " noiseless" if disable_sources and ref.startswith(("r_source_", "r_gen_")) else ""
            converted.append(f"{ref} {n1} {n2} {val}{quiet}")
        elif re.match(r"^tlv\d+_tlv\d+:xu", line):
            family, rest = line.split(":", 1)
            converted.append(rest.replace("fb_sense","vmid_buf")+" "+family)
            quads += 1
        elif line and not line.startswith(";"):
            raise ValueError(f"Unconverted topology line: {line}")
    assert quads == 20
    converted += ["VDD avdd_3v0 0 3", "VREF src_ref 0 0", "VCH1 src_ch1 0 DC 0 AC 1"]
    converted += [f"VCH{i} src_ch{i} 0 0" for i in (2,3,4)]
    converted.append(".noise V(adc_in_1) VCH1 dec 100 300 7000")
    return "\n".join(converted)


def main():
    OUT.mkdir(exist_ok=True)
    points = {}
    for family in ("9002","9052"):
        f, iv, ov = run("model-"+family, f"""VDD vdd 0 5
VIN in 0 DC 2.5 AC 1
XBUF in out vdd 0 out TLV{family}_TLV{family}
.noise V(out) VIN dec 100 300 10000""")
        points[family] = {f"{at}Hz_nV_per_rtHz":float(np.interp(at, f, iv)*1e9) for at in (300,1000,2000,10000)}
    total = {}
    series = []
    for name, quiet in [("electronics",True), ("with-emulator",False)]:
        f, iv, ov = run(name, make_topology(quiet))
        assert np.isclose(f[0],300) and np.isclose(f[-1],7000) and np.all(iv>0) and np.all(ov>0)
        total[name] = dict(input_integral_uV_rms=float(np.sqrt(np.trapezoid(iv**2,f))*1e6),
                           ADC_integral_mV_rms=float(np.sqrt(np.trapezoid(ov**2,f))*1000))
        series.append((f,iv,ov))
    assert np.allclose(series[0][0],series[1][0])
    with (OUT/"spectra.csv").open("w",newline="") as file:
        writer=csv.writer(file)
        writer.writerow(["freq_Hz","electronics_input_V_per_rtHz","electronics_ADC_V_per_rtHz","with_emulator_input_V_per_rtHz","with_emulator_ADC_V_per_rtHz"])
        writer.writerows(zip(*series[0],series[1][1],series[1][2]))
    results={"family_follower_noise_5V":points,"four_coax_300Hz_7000Hz":total}
    (OUT/"results.json").write_text(json.dumps(results,indent=2)+"\n")
    print(json.dumps(results,indent=2))


if __name__=="__main__":
    main()

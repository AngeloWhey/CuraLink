"""Plot retained actual ADS nominal results; no new simulation."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
report = json.loads((HERE / "results.json").read_text())
points = report["ac"]["points"]
f = np.array([p["frequency_Hz"] for p in points])
gain = np.array([p["differential_gain_V_per_V"] for p in points])
z = np.array([p["derived_FFC_CH1_input_Z_magnitude_ohm"] for p in points])/1e6
coupling = np.array([p["derived_single_CH1_crosstalk_dB"] for p in points])
band = (f >= 300) & (f <= 7000)
fig, axes = plt.subplots(1, 3, figsize=(15, 4.3), layout="constrained")
axes[0].semilogx(f, 20*np.log10(gain), "o-", color="#166e86")
axes[0].axvspan(300, 7000, alpha=.10, color="#166e86")
axes[0].set(xlim=(20, 1e5), ylim=(-5, 65), title="Differential small-signal gain", xlabel="Frequency (Hz)", ylabel="Gain (dB)")
axes[1].semilogx(f[band], z[band], "o-", color="#985531")
axes[1].axhline(10, linestyle="--", color="#b63737", label="Existing 10 MΩ requirement")
axes[1].set(xlim=(280, 7400), ylim=(0, 11), title="CH1 input loading at FFC", xlabel="Frequency (Hz)", ylabel="|Z input| (MΩ)")
axes[1].legend(fontsize=8, loc="upper right")
axes[2].semilogx(f[band], coupling[band], "o-", color="#6d4aa0")
axes[2].set(xlim=(280, 7400), ylim=(-75, -48), title="Quiet/active channel coupling", xlabel="Frequency (Hz)", ylabel="Derived CH1-only ratio (dB)")
for axis in axes:
    axis.grid(True, which="both", alpha=.25)
fig.suptitle("Fresh ADS nominal AFE review — 20 frequency samples; shared 47 Ω VMID filter", fontsize=13)
fig.savefig(HERE / "afe-review.png", dpi=160)
plt.close(fig)
print(HERE / "afe-review.png")

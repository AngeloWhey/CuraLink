# CuraLink WPT coil models

## `luo2023_coupled_coils_lumped_50ohm.s2p`

This is a **CuraLink-derived nominal model**, not measured data from Luo et al. and not an author-supplied Touchstone file. It converts the paper's measured 13.56 MHz equivalent values into a reciprocal 50 ohm two-port:

- `L_TX = 2.49 uH`, `R_TX = 1.80 ohm`
- `L_RX = 0.330 uH`, `R_RX = 0.399 ohm`
- `k = 0.0662`, giving `M = 60.0088 nH`

Each port is directly across one coil model. No resonance/matching capacitors, source network, rectifier, reservoir or load is included. The 1–30 MHz sweep uses constant series resistance and ideal inductance/mutual inductance; it does not reconstruct frequency-dependent resistance, parasitic capacitance, SRF, fixtures, offset, tilt or nearby structures.

Import it into an ADS `S2P` data component for **linear narrowband matching checks**. For rectifier harmonic-balance analysis, prefer the explicit R-L-M schematic in the [ADS setup](../../../docs/design/2026-09-22-ads-wpt-model-setup.md), because the paper did not publish valid broadband harmonic-frequency S-parameters.

Regenerate the file with:

```powershell
python tools/generate_luo2023_lumped_s2p.py
```

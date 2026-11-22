# CuraLink Rev A ADS WPT model setup

**2026-09-22 · Implements DEC-WPT-003.** This is a nominal coupled-inductor circuit model derived from published measurements, not an imported measured Touchstone network and not a completed CuraLink simulation.

## Source-file availability

No public GitHub repository, supplementary dataset or Touchstone file was found for Luo et al., *Design and Optimization of Planar Spiral Coils for Powering Implantable Neural Recording Microsystem*. The article's data-availability statement is “Not applicable,” its full-text archive exposes no supplementary-material entry, and exact-title, DOI and PMCID repository searches returned no matching GitHub repository when checked on 2026-09-22. The paper provides geometry, single-frequency equivalent parameters, plotted Z/S results and matched-link efficiency, but not the underlying sampled two-port data. [Open-access paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC10302922/).

Do not create or label a synthetic file as the paper's measured `.s2p`. CuraLink has no VNA access under D-019, so Rev A intentionally proceeds with the published lumped measurements and explicitly accepts the loss of independent S-parameter verification.

A reproducible derived file is available at [`hardware/wpt/models/luo2023_coupled_coils_lumped_50ohm.s2p`](../../hardware/wpt/models/luo2023_coupled_coils_lumped_50ohm.s2p). It is a 1–30 MHz, 50 ohm two-port calculated from the constant-R coupled-inductor equations and is labeled as synthetic in its header. Its unmatched direct-50-ohm `|S21|` at 13.56 MHz is approximately 0.04059 (-27.83 dB); this does not conflict with the paper's matched -1.55 dB result because the derived file contains no matching networks. Use it for linear import/checks, not as a substitute for broadband harmonic-frequency coil data.

## ADS variables

Create a `VAR` block with:

| Variable | Value | Meaning |
|---|---:|---|
| `f0` | `13.56 MHz` | Operating frequency |
| `L_TX` | `2.49 uH` | Measured TX self-inductance |
| `R_TX` | `1.80 ohm` | Measured TX series resistance |
| `L_RX` | `0.330 uH` | Measured RX self-inductance |
| `R_RX` | `0.399 ohm` | Measured RX series resistance |
| `K_NOM` | `0.0662` | Measured coupling coefficient at 10 mm coaxial separation |
| `M_NOM` | `60.0 nH` | Check value; `K_NOM*sqrt(L_TX*L_RX) = 60.01 nH` |

These values imply `Q_TX ≈ 117.86` and `Q_RX ≈ 70.47` at 13.56 MHz, consistent with the reported 118 and 70.4.

## Schematic construction

1. Place an ideal inductor `L_TX_ID` with `L=L_TX` and a separate series resistor `R_TX_ID` with `R=R_TX` in the TX loop.
2. Place an ideal inductor `L_RX_ID` with `L=L_RX` and a separate series resistor `R_RX_ID` with `R=R_RX` in the RX loop.
3. Place ADS's `Mutual` component, set `Inductor1="L_TX_ID"`, `Inductor2="L_RX_ID"` and `K=K_NOM`. ADS accepts either K or M; if both are entered, M overrides K. Use K only so coupling can be swept. Check the dot convention by confirming expected secondary-voltage polarity. [Keysight Mutual component documentation](https://edadownload.software.keysight.com/eedl/ads/2011_01/pdf/ccsim.pdf).
4. Add a 50 ohm source only as the first defined drive boundary. Replace it later with the selected PA/output-network model; always report accepted RF power at the TX coil-model input.
5. Design new TX and RX matching networks around the CuraLink rectifier/load. Do not copy the paper's 50 ohm VNA matching capacitors.

The isolated-inductor resonance values

`C_TX,ideal = 1 / ((2*pi*f0)^2*L_TX) ≈ 55.33 pF`

`C_RX,ideal = 1 / ((2*pi*f0)^2*L_RX) ≈ 417.45 pF`

are only starting checks for the optimizer. Coupling, the rectifier's nonlinear input impedance, diode capacitance, reservoir and load change the required network.

## What must be impedance-transformed

At the nominal measured geometry, the paper calculates the secondary coil's optimum complex load as approximately `Z_L,opt = 2.4 - j28.12 ohm` at 13.56 MHz. CuraLink's RX matching network should transform the **fundamental-frequency input impedance of the operating rectifier/reservoir/load** toward that value as seen by the secondary coil. The charger-side DC ratio `V_DC/I_DC` is not the RF input impedance: diode conduction angle, junction capacitance, reservoir ripple and charge state make the rectifier nonlinear.

Use harmonic balance to observe fundamental voltage/current at the RX interface and to optimize component values. Treat `2.4 - j28.12 ohm` as a consistency target, while ranking designs by delivered DC voltage/power, RF-to-DC efficiency and device stress. Also design the TX network to transform the actual transmitter source impedance to the primary coil; RX matching alone does not match the transmitter.

## Simulation sequence

1. **Linear sanity check:** With linear terminations and no rectifier, run an S-parameter sweep around 13.56 MHz. Confirm the model values and polarity. Do not require it to reproduce the paper's `S21=-1.55 dB` until a comparable 50 ohm load transformation is deliberately recreated.
2. **Rectifier comparison:** Add the low-capacitance Schottky full-wave bridge and reservoir/load. Use harmonic balance at 13.56 MHz; increase harmonic order until `V_DC`, `P_DC` and diode stress converge. Repeat with the two-diode doubler, independently retuning the matching network.
3. **Sweeps:** Sweep accepted TX power, load, tuning tolerance and K around 0.0662. A K sweep is sensitivity analysis, not a physical offset/separation model unless backed by HFSS or VNA data.
4. **Later load:** Replace the resistor with input protection/OVP, charger input behavior and charge-state cases. Include no load and full-battery/charge-termination conditions.
5. **Report:** `V_DC`, ripple, `P_DC`, `eta_RF_to_DC`, accepted TX RF power, input reflection, diode peak current, diode reverse voltage, diode loss and component stress.

## Power-feasibility sweep before battery selection

The coil model alone cannot specify absolute output power; ADS must be given a TX source level and impedance. Use **accepted RF power at the TX coil-model input** as the comparison boundary and sweep at least `5, 10, 25, 50, 100, and 200 mW`. For each source level, independently optimize the bridge and doubler across resistive DC loads such as `50, 100, 200, 500, and 1000 ohm`, plus no load. Those resistors correspond to 5 V powers of 500, 250, 125, 50 and 25 mW, respectively; they are test points, not selected charger demands.

For each assumed coupling/tolerance case, plot maximum usable `P_DC` against `V_DC` and accepted TX power. A battery is considered only after the worst-supported coupling case supplies a charger-compatible voltage and stable power with protection margin. Convert the result into a conservative charge-current ceiling using

`I_CHG,max ≈ margin * eta_CHG * P_DC,worst / V_BAT,max`,

where `margin < 1`, `eta_CHG` is charger efficiency and `V_BAT,max` is the cell's charge voltage. Battery capacity and allowed C-rate must both support the chosen current. The project cannot set a final pass/fail power threshold until the system energy budget and acceptable recharge time are defined; the ADS sweep supplies the power curve needed to make those choices rather than assuming a battery first.

## Model limits and exit criteria

The paper's table gives equivalent parameters at 13.56 MHz, not frequency-dependent winding resistance, parasitic capacitance, SRF behavior or broadband two-port phase/magnitude samples. The lumped model is suitable for initial matching and topology comparison at the nominal geometry but cannot validate misalignment, nearby copper/battery/ferrite, harmonic-frequency behavior or production tolerances.

Because no VNA is available, populate tuning-capacitor options and validate the assembled receiver end to end. First use several known resistive loads and record separation/alignment, TX setting, capacitor population, `V_DC`, ripple, `P_DC` and temperatures. Then repeat with the charger across low-cell, constant-current, constant-voltage, termination/full-battery and permitted no-battery conditions. These tests can establish usable charging behavior but cannot independently recover coil Q, k or broadband S-parameters. Reopen HFSS under the physical-change conditions in D-018.

## User ADS export: TX-input S11

**Recorded 2026-09-22.** `data/daa.csv` is an ADS S-parameter export labeled `S(1,1)`, complex magnitude/degree, 501 frequency points. Assuming port 1 is the TX input, its reference impedance is 50 ohms, and the export corresponds to the current coupled-coil/matching/load schematic, the points around 13.56 MHz are `|S11|=0.977`, phase approximately `+26.47°` (interpolated from 13.50 and 13.60 MHz). The rounded export gives approximately:

- `Zin = 50*(1+S11)/(1-S11) ≈ 11.1 + j212 ohm` at 13.56 MHz.
- Return loss ≈ 0.20 dB; VSWR ≈ 86:1.
- Reflected incident power ≈ 95.5%; accepted power ≈ 4.5% at this reference plane.

This is a **simulated result**, not a coil measurement. The large positive reactance is consistent with the unmatched TX coil's `jωL ≈ j212 ohm` from the published `L_TX=2.49 uH`; the TX input is therefore not matched to the 50-ohm port. The RX matching network does not match the TX side. Add/optimize a TX matching network and re-run an S-parameter sweep; `C_TX,ideal ≈ 55.3 pF` is only an isolated-coil resonance starting estimate, not a complete 50-ohm match. Verify the S11 result against the schematic's port reference plane and receiver termination before using it for power claims. The CSV alone does not establish that it is the same configuration as the earlier transient `Vout` plot.

The paper's approximately 70% value is a **matched two-coil link** measurement with 50-ohm VNA source/load boundaries and explicit TX and RX matching. The authors report `S21 ≈ -1.55 dB` at their matched measurement condition; an unmatched 50-ohm TX port is not expected to reproduce that result. [Luo et al., 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10302922/).

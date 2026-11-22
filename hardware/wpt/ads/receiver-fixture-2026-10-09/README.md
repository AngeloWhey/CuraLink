# ADS receiver resistor fixture — 2026-10-09

This is an isolated, reproducible test of the current **corrected floating RX bridge**. It does not modify `MyWorkspace_wrk`, `cell_1` or `cell_2`. The bridge negative is DC ground; neither receive-coil/bridge AC terminal is tied to it. The archived fresh `netlist.log` and `cell_1.ds` establish this connection for the saved simulation. A separate read of the saved OA schematic found older grounding, so the original OA view is **not** taken as proof that the GUI change has been saved. The separate GUI setup script in `../gui-setup` checks its copied cell explicitly.

The four capacitors remain at the current starting values: TX series C3 = 61.3 pF, TX shunt C5 = 438 pF, RX series C1 = 673.3 pF, RX shunt C6 = 1050 pF. The coils use the project's published measured nominal 13.56 MHz values: 2.49 µH / 1.80 Ω TX, 0.330 µH / 0.399 Ω RX and k = 0.0662. They are constant R-L-M elements, with ideal tuning capacitors and no PCB/package/environment parasitics. See [model provenance](../../models/README.md) and the [handbook D-018](../../../../docs/engineering-handbook.md).

## What has actually run

The saved original ADS output at **10 dBm available power, 1 MΩ load, 1 µF reservoir, HB order 7** was read through the installed `keysight.ads.dataset` API. It is preserved in `source-snapshot` with SHA-256 hashes and original source file times. Its numeric spectrum is exported in [saved-baseline-spectra.csv](saved-baseline-spectra.csv); the derived observables are in [saved-baseline-metrics.json](saved-baseline-metrics.json).

| Observable | Saved ADS result / derived from its spectra |
|---|---:|
| DC output | 1.418363 V |
| DC load current | 1.418363 µA |
| DC load power | 2.011753 µW |
| Available RF source power | 10 mW |
| Net accepted RF power at the 50 Ω source boundary | 4.894803 mW |
| Available RF → DC efficiency | 0.02012% |
| Fundamental input impedance | 13.834 − j39.721 Ω |
| Fundamental return loss | 2.9199 dB |
| Differential bridge RF fundamental | 1.69244 V peak |
| Largest diode reverse voltage | 1.55540 V peak |
| RX winding current / resistive loss | 107.07 mA RMS / 4.57429 mW |
| TX winding current / resistive loss | 13.2889 mA RMS / 0.31787 mW |

The source current and coil currents are **calculated from saved nodal phasors and the declared source/R-L-M equations**; the original dataset did not save those current probes. The residual rectifier loss is 0.6294 µW after winding and load power, which gives a consistent power balance for this point. The 1 MΩ case is effectively a light-load voltage diagnostic. It is not a useful-load, charger, battery or charging-efficiency test. The current capacitors are a starting point; no loaded optimum has been demonstrated.

The first isolated run returned exit 120 because `b_pwad_inclusive1` had no available license seats (`Licensed number of users already reached`). The failed log is retained in `runs/baseline_10dBm_light/simulator.log`. A later ordinary run obtained a license and completed. The **21-point current-diode baseline matrix is now actual standalone ADS simulation evidence**, saved in [baseline-matrix-H7.csv](baseline-matrix-H7.csv), with complete per-point decks, datasets and logs under `runs`. The user app was not closed and no undocumented license workaround was attempted.

| Current capacitors / old diagnostic diode | 20 dBm / 240 Ω | 23 dBm / 240 Ω | 26 dBm / 240 Ω |
|---|---:|---:|---:|
| Output voltage | 2.92189 V | 3.72180 V | 3.77864 V |
| Delivered DC power | 35.5727 mW | 57.7159 mW | 59.4923 mW |
| Diode reverse peak | 3.55082 V | 4.48856 V | 4.74869 V |
| TX series-capacitor peak | 16.4671 V | 26.6349 V | 47.5035 V |

Raising available source power from 23 to 26 dBm adds very little DC with this diode seed while increasing reverse stress and circulating voltage. This is **reverse-breakdown dissipation**, not a qualified output clamp. The current-diode 23 dBm / 240 Ω point at HB order 15 gives 3.704787 V / 57.18936 mW / 4.475554 V reverse peak; order 31 gives 3.703901 V / 57.16201 mW / 4.474930 V. Order 15 → 31 changes DC power by 0.048%, supporting the diagnostic breakdown result within this lumped model. Peak current still changes by about 0.31%; neither numerical agreement nor a DC result qualifies the part.

## Run-ready inputs

[run_receiver.py](run_receiver.py) generates ADS input decks, runs the documented simulator CLI with the installed Keysight environment, reads the dataset, and writes metrics. `--mode prepare` requires no simulation license. The pre-generated `input-decks` matrix includes **20, 23, 26 dBm** and **208.333, 220, 230, 240, 270, 470, 1 MΩ** loads. At an assumed 5 V, 208.333 Ω represents 24 mA / 120 mW; 240 Ω represents 20.833 mA / 104.167 mW. These are operating-point resistance approximations, not charger behavior. The 230 Ω case is an intermediate load diagnostic.

From the canonical project folder:

```powershell
& 'C:\Program Files\Keysight\ADS2026_Update2\tools\python\python.exe' '.\hardware\wpt\ads\receiver-fixture-2026-10-09\run_receiver.py' --mode prepare
& 'C:\Program Files\Keysight\ADS2026_Update2\tools\python\python.exe' '.\hardware\wpt\ads\receiver-fixture-2026-10-09\run_receiver.py' --mode single --pin 23 --load 240 --label P23_R240
& 'C:\Program Files\Keysight\ADS2026_Update2\tools\python\python.exe' '.\hardware\wpt\ads\receiver-fixture-2026-10-09\run_receiver.py' --mode sweep --label baseline
& 'C:\Program Files\Keysight\ADS2026_Update2\tools\python\python.exe' '.\hardware\wpt\ads\receiver-fixture-2026-10-09\run_receiver.py' --mode single --pin 26 --load 230 --diode bat54 --label bat54_P26_R230
& 'C:\Program Files\Keysight\ADS2026_Update2\tools\python\python.exe' '.\hardware\wpt\ads\receiver-fixture-2026-10-09\run_receiver.py' --mode optimize --pin 26 --load 230 --diode bat54 --maxiter 3
```

Run the CLI when a simulation license is available. The separate copied GUI fixture lets the current ADS session run the same circuit while keeping the original cell intact. The installed ADS 2026 Update 2 documentation supports the netlist CLI and `CircuitSimulator`/dataset APIs; sources inspected include `doc/ads/Content/ads2026update2/cktsim/ADS_Simulator_Input_Syntax.html`, `doc/python/edatoolbox/html/_sources/How-To/circuit_sim.rst.txt` and the installed `keysight/edatoolbox/ads.py` and `keysight/ads/dataset/__init__.py`.

## Matching objective and observables

The bounded joint search varies **all four tuning capacitors together** at the selected command-line operating point (the executed candidate study uses 26 dBm / 230 Ω) and maximizes **delivered DC power**, rather than using input return loss alone. It uses log-capacitance coordinates, a fixed seed, an initial population near the current resonant network and finite differential-evolution iterations. Search bounds are TX series 20–200 pF, TX shunt 50–2000 pF, RX series 100–5000 pF, RX shunt 100–10000 pF. These are exploratory search ranges, not sourced capacitor choices. The best searched point is then re-run across the whole power/load matrix, followed by HB orders 15 and 31 at selected loads. This is a finite local study, not proof of a global optimum, robust hardware match, or manufacturable tuning values. Optimization of the old 4 V diode for charging is explicitly refused by the script because its breakdown can hide the required output voltage.

The deck has independent current probes for source acceptance, each diode and the DC load. Analysis reports DC voltage/current/power, reservoir ripple, available-to-DC and accepted-to-DC efficiency, fundamental input impedance/return loss, diode forward/reverse peak current and voltage, diode average dissipation, coil RMS/peak current and winding loss, and peak voltage across each matching capacitor. Peak waveforms are reconstructed with 8192 samples per fundamental cycle from ADS peak phasors (`x(t)=x0+Re[Σ Xn exp(jnωt)]`). Harmonic-order agreement is a numerical truncation check; it does not establish the constant coil model's validity at harmonics or include SRF/package effects.

## Diode and charger qualification boundaries

The exact current ADS diode model is retained solely to diagnose the present circuit: `Is=74 nA`, `Rs=5 Ω`, `N=1.07`, `Tt=3 ps`, `Cjo=138.5 fF`, `Vj=0.224 V`, `M=0.138`, `Fc=0.5`, `BV=4.2 V`, `IBV=100 µA`, `Xti=1.5`. This is the project's provisional BAT15 seed, **not a final diode selection or an audited package model**. The script flags terminal reverse peaks above the earlier recorded 4 V rating separately from the model's 4.2 V avalanche parameter. Any flagged result is unsuitable as evidence that this diode can implement the desired charging rail; avalanche-limited DC output must not be mistaken for regulation or successful matching. A safe diode and capacitor rating must eventually cover loaded and no-load peaks plus transients and tolerances.

This fixture contains **a resistor, not BQ25185**. It models neither VINDPM/current reduction, CC/CV change of loading, charger input overhead, input-current limits, enable/OVP, thermal behavior, cell SOC, charge timer, temperature sensing nor mode isolation. A real charger/protection load can move the RF impedance and operating point. After the resistor study, repeat tuning with the separate charger behavioral envelope, test light/no-load voltage and protection behavior, and validate startup/mode transitions at slower timescales. No cell, final diode, final capacitor, or final TX power is chosen here.

## Separate BAT54 candidate

The `--diode bat54` option uses the complete [Diodes Incorporated manufacturer SPICE model](https://www.diodes.com/spice/download/510/BAT54.spice.txt), archived and translated by the charger study in [model-sources](../charger/model-sources). It is a **separate diagnostic candidate**, not a BV edit to the old diode and not final selection of BAT54-7-F. The installed ADS translator preserves all 13 manufacturer parameters and supplies its compatibility defaults; the script uses that translated model verbatim with a changed model identifier. The installed simulator's `-h Diode` synopsis independently confirms support for `Ikf`, `Isr`, `Nr`, `Nbv`, `Tnom` and `IkModel`. No unsupported parameter was dropped.

The exact native model is:

```text
model DIODEM1 Diode Is=649e-9 N=1.04 Rs=2.09 Ikf=20e-3 Xti=2 Eg=0.58 Cjo=12.4e-12 M=0.381 Vj=0.391 Bv=50 Ibv=100e-6 Isr=431e-9 Nr=4.99 Nbv=1.04 Tnom=27 IkModel=1 Imax=1000 Trs1=0 Trs2=0
```

The [physical datasheet](https://www.diodes.com/datasheet/download/BAT54.pdf) rates reverse voltage at **30 V**; the fitted model's **BV = 50 V is not that rating**. The stress analyzer applies 30 V. The manufacturer model supplies no `Tt`; its datasheet recovery specification is not independently represented in this run. Package, layout, temperature, current rating and real capacitor loss still require qualification.

Actual ADS results with the current capacitors and the complete translated candidate at 26 dBm are **6.39127 V / 185.674 mW at 220 Ω** and **6.48347 V / 182.762 mW at 230 Ω**. The 230 Ω reverse peak is 7.19997 V, and the TX series capacitor reaches 34.5147 V peak. These meet a 120 mW **resistor-power** threshold at this modeled point, while the raw voltage exceeds the approximately 5 V target. They do not establish charger input compatibility, regulation, thermal margin or safety.

## Candidate tuning and near-5 V confirmation

The completed **64-evaluation finite local search** found this better nominal match. All four values are **Candidate ideal capacitances**, with nearest-stock-value conversion, tolerance/Q/ESR, voltage/current rating and tuning footprints still open:

| Capacitor | Candidate nominal value |
|---|---:|
| C3 TX series | 59.30046 pF |
| C5 TX shunt | 374.73956 pF |
| C1 RX series | 826.20585 pF |
| C6 RX shunt | 773.59319 pF |

The search stopped at its iteration limit; it did not prove a global optimum. Its selection point was **26 dBm / 230 Ω / HB7**, giving 7.260697 V and 229.20749 mW. This high-power selection point establishes nominal headroom; **it is not the desired approximately 5 V operating point**. The full best-point matrix is in [bat54-joint-search-best-matrix-H7.csv](bat54-joint-search-best-matrix-H7.csv); the comparative plot is [receiver-sweep-results.png](receiver-sweep-results.png). The 23 dBm matrix gives only 110.70–111.30 mW at the approximately 208–240 Ω target loads, below the 120 mW allocation.

Focused new runs at 23.5, 24 and 25 dBm confirmed a near-target point at **23.5 dBm available RF power / 208.333 Ω**. This power setting is a simulation operating point, not selection of a final transmitter. [bat54-near-target-matrix-H7.csv](bat54-near-target-matrix-H7.csv) records all six focused points. Subsequent harmonic checks distinguish the HB7 selection from the final numerical result:

| HB order | DC voltage | DC power | Forward diode peak | Reverse capacitive current peak |
|---:|---:|---:|---:|---:|
| 7 | 5.102668 V | 124.978654 mW | 115.565 mA | 6.469 mA |
| 15 | 5.085482 V | 124.138205 mW | 121.387 mA | 4.740 mA |
| 31 | 5.088711 V | 124.295894 mW | 120.764 mA | 1.921 mA |
| 63 | 5.089071 V | 124.313487 mW | 120.842 mA | 1.772 mA |
| 127 | **5.089082 V** | **124.314022 mW** | **120.881 mA** | **1.755 mA** |

HB63 → 127 changes DC power by 0.00043%, forward peak by 0.032%, and the small reverse capacitive peak by approximately 0.98%. The latter converges more slowly than DC. These high orders test the mathematical lumped model's Fourier truncation, including idealized junction-capacitance transitions; they do not validate the coil or diode/package at up to 1.72 GHz, establish reverse recovery, or qualify PVT/hardware behavior. Final point data are in [bat54-target-confirmation-final.json](bat54-target-confirmation-final.json), while [bat54-target-confirmation.csv](bat54-target-confirmation.csv) retains every order and the light-load checks.

At HB31, the near-target point accepts 219.0149 mW and delivers 124.2959 mW, or 55.5209% of 223.8721 mW available RF. Fundamental source impedance is 38.3758 + j5.9241 Ω, with 16.6361 dB return loss. Reverse diode peak is 5.71860 V, and diode dissipation is 6.80735 mW per device. TX/RX winding current is approximately **129 / 307 mA RMS**, with **29.95 / 37.54 mW winding loss**. Those are modeled electrical losses, not measured coil temperatures.

The tuning-capacitor stresses at that point are:

| Capacitor | Voltage peak | RMS current |
|---|---:|---:|
| TX series | 36.1045 V | 128.988 mA |
| TX shunt | 4.14788 V | 93.659 mA |
| RX series | 6.15262 V | 306.738 mA |
| RX shunt | 6.34854 V | 300.550 mA |
| 1 µF reservoir | 5.08902 V | 41.174 mA |

All capacitor currents are calculated from the saved voltage spectra and ideal capacitance. Both RX tuning capacitors carry approximately 0.30 A RMS: an assumed 0.1 Ω ESR in each would add approximately 9 mW loss apiece, already larger than the roughly 4.3 mW nominal margin over the 120 mW load target. This sensitivity is a calculation, not a part ESR estimate, and makes actual high-Q capacitor selection and margin evaluation necessary before adopting these values.

**Same-power light load is the material protection result:** at 23.5 dBm and 1 MΩ, HB31 gives **11.914858 V raw**, 12.07963 V diode reverse peak, 38.8761 V TX series-capacitor peak and approximately 574.35 mA RX winding RMS current / 131.62 mW winding loss. At 26 dBm the matrix reaches approximately 15.84 V raw, with an HB31 light-load check of 15.96333 V. Receiver regulation/OVP must handle load removal and charging taper; a simple clamp also changes receiver loading and may dissipate substantial power. The present model includes no such protection behavior.

## Independent native ADS cell validation

[validate_gui_netlist.py](validate_gui_netlist.py) actually ran the fresh OA readback netlist from the new native `MyLibrary_lib:RX_BAT54_LoadSweep_20261009:schematic` cell. Its complete deck, successful simulator log, dataset and metrics are in `runs/native_BAT54_candidate_validation`. At 23.5 dBm / 208.333 Ω / HB31 it produces **5.088532 V / 124.287177 mW**, agreeing with the standalone fixture within 0.007% in DC power. The small difference is consistent with the original explicit 60 nH mutual inductance versus the standalone k-derived 60.0088 nH and displayed-value rounding.

The native in-cell measurement equations parse and independently report:

| Native equation | Actual saved value |
|---|---:|
| `Vdc` / `Pdc` | 5.088532 V / 124.287177 mW |
| `Z_source` | 38.37253 + j5.933862 Ω |
| `Z_rx`, seen by the receive coil into its matching/bridge network | 1.610535 − j28.880468 Ω |
| `Z_bridge`, nonlinear fundamental impedance | 130.470117 − j25.148141 Ω |
| `Psource_f1` | +219.009120 mW |
| `Prx_f1` / `Pbridge_f1` | +151.516654 mW each |

The positive power signs confirm the probe directions. The fundamental real RF bridge power exceeds DC power by its rectifier loss; `Z_bridge` is an operating-point fundamental quantity, not the resistor's DC value or a fixed charger impedance. The native output stores zero current on the ground-side lower-diode pins; the analysis uses each non-ground cathode current with reversed sign for those two devices. Direct saved coil pin currents are used when available, and the native complete power balance closes within approximately 2.8 nW.

Run the focused confirmation and read-only reporting with:

```powershell
& 'C:\Program Files\Keysight\ADS2026_Update2\tools\python\python.exe' '.\hardware\wpt\ads\receiver-fixture-2026-10-09\confirm_operating_point.py'
& 'C:\Program Files\Keysight\ADS2026_Update2\tools\python\python.exe' '.\hardware\wpt\ads\receiver-fixture-2026-10-09\report_results.py'
& 'C:\Program Files\Keysight\ADS2026_Update2\tools\python\python.exe' '.\hardware\wpt\ads\receiver-fixture-2026-10-09\validate_gui_netlist.py' --read-only
```

The first command launches new simulations; the other two only read retained datasets and refresh reporting. Omitting `--read-only` from the native validator re-runs the fresh native netlist. Original workspace cells were not changed by this standalone work; the independent GUI setup record owns the new copied cells and original-hash verification.

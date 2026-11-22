# Packaged-bridge receiver characterization

**Build the floating RX network around one Infineon BAS4002ARPPE6327HTSA1 and place a TPS70950DBVR between the bridge reservoir and the regulated 5 V interface.** These are prototype design inputs. ADS shows that the charging-status radio load, coil coupling and capacitor tolerance can each move this circuit into dropout. The electrical, thermal and sourcing gates in the project handoff govern fabrication and release.

## What to connect

The nominal frequency is 13.56 MHz. Preserve the published coils and 10 mm nominal spacing. At the 50 Ω transmitter put 375 pF to the transmitter return, followed by a 60 pF series capacitor and the 2.49 µH transmitter coil. On the floating receiver run the 0.330 µH coil through 1 nF in series to the first AC terminal of the bridge. Connect 680 pF across the resulting two AC terminals. Connect them to package pins 2 and 3. Pin 1 is the DC return. Pin 4 is the positive reservoir node, identified here as RAW or RECT_DC. Place the 5 V regulator and its bypassing on the DC side. Measure the differential RF terminals without grounding either one through a scope probe.

The exact inductor series resistances are 1.80 Ω TX and 0.399 Ω RX at the carrier. Nominal coupling is 0.0662. Mutual inductance follows from the two inductances and coupling. The matched passive link in the preceding review delivered 71.87% of available RF into the paper's transformed 50 Ω load. The new load moves with input level and charging state. [Luo et al., Micromachines 2023](https://doi.org/10.3390/mi14061221) · [Passive link evidence](../review-2026-11-22/published-link-check.json)

## Actual ADS harmonic balance

The source powers below are **available power into a matched 50 Ω load**. The voltages are the minimum across the reservoir during one settled RF cycle. A 6.0 V minimum gives 1.0 V of headroom above the intended 5 V output. A minimum below 6.0 V needs a regulator-level dropout check at the actual current. The matrix uses a positive, voltage-compliant current demand at RAW. Above 2 V its value is the table heading. Near collapse it falls toward zero. The 24 mA load represents the earlier 120 mW budget at 5 V. The extra 5 and 15 mA are scenario loads for the digital rail and radio. Cell state of charge, firmware radio duty cycle, eFuse dynamics and physical temperature require separate evidence.

| Available TX | 24 mA | 29 mA | 39 mA | 2 mA taper plus overhead, 3.74 mA | Field on after completion, 1.74 mA | Near-open, 1 µA |
|---|---:|---:|---:|---:|---:|---:|
| 23.5 dBm / 224 mW | 4.87 V | 3.39 V | 0.84 V | 11.29 V | 11.98 V | 12.89 V |
| 25 dBm / 316 mW | 7.31 V | 5.79 V | 2.91 V | 13.79 V | 14.50 V | 15.41 V |
| 26 dBm / 398 mW | 9.20 V | 7.66 V | 4.69 V | 15.72 V | 16.43 V | 17.35 V |
| 27 dBm / 501 mW | 11.32 V | 9.78 V | 6.75 V | 17.89 V | 18.60 V | 19.53 V |

At 25 dBm and 24 mA, the package itself presents 181.06 − j19.77 Ω at the fundamental. The RX coil sees 1.636 − j28.668 Ω after transformation. ADS gives 20.28 dB TX return loss, 176.3 mW raw DC and approximately 40 mW TX / 52 mW RX winding losses. The useful board output at the nominal 5 V would be 120 mW. Excess raw voltage becomes primarily regulator loss. A higher open-circuit voltage provides little information about load capacity.

An approximate regulator dissipation at 24 mA is 56 mW at 25 dBm, 102 mW at 26 dBm and 153 mW at 27 dBm, calculated as (mean RAW − 5 V) × load current with the regulator in regulation. The SOT-23 footprint, copper and enclosure determine the temperature rise. At light load the RX winding can be the larger heat source.

The finite 81-network search at 25 dBm and 24 mA produced 70 converged combinations, with the 11 rejected cases named in the search manifest. Among the solved points, 60.4 / 375 / 1000 / 680 pF gave 7.36 V minimum. The buildable 60 pF substitution gave 7.31 V. Keeping the paper's 61.3 / 438 / 673.3 / 1050 pF network in the otherwise identical bridge fixture produced 5.58 V minimum. The 60/375/1000/680 set is a starting population for nominal geometry and the stated loads. The search did not establish a global optimum. [Search results](bridge-runs/search/results.csv) · [138 completed operating and sensitivity cases](bridge-runs/matrix/results.csv)

## Tolerance, heat and tuning

- At 25 dBm and 24 mA all 16 independent ±2% capacitor endpoint combinations yielded at least 6.54 V. The worst of the 16 ±5% combinations yielded 3.93 V. These are endpoint tests of the four total branch capacitances. They do not bound every intermediate point, combined temperature corner or unmodeled board parasitic. Provide alternate parallel values and characterize the actual population.
- Keeping the capacitances and RF power fixed while reducing coupling from 0.0662 to 0.04965 and 0.0331 lowered the 25 dBm / 24 mA minimum to 5.71 and 1.33 V. The latter two are sensitivity cases. Establish the corresponding positions by moving the real coils. A combined high-drop junction fit, Q = 250, doubled lead inductance and 25% higher winding resistance gave 6.10 V at nominal coupling.
- A TX-only trim sweep held the receiver assembly fixed at 1 nF and 680 pF. At k = 0.04965 and 25 dBm / 24 mA, keeping TX series 60 pF and changing TX shunt from 375 to 525 pF recovered 6.51 V minimum. At nominal k and 26 dBm / 39 mA, the best of 20 sampled transmitter settings was 62 pF series and 450 pF shunt, which gave 5.45 V minimum. Across the two operating points 38 of the 40 attempts converged. Keep the 375 pF nominal TX starting population and provide access for shunt trim. [TX-only results](bridge-runs/tx_trim/results.csv)
- The 138-case matrix reached 68.17 V peak across the TX series capacitor, 0.823 A RMS through the RX series capacitor and 0.821 A RMS through the RX shunt capacitor. At 27 dBm and near-open load the small RX winding dissipated 270 mW. At 26 dBm and near-open load it still dissipated 215 mW. Confirm capacitor RF current/ESR and voltage ratings, coil temperature and duration of any field-on idle state on the assembled geometry.
- The highest modeled junction reverse voltage was 19.78 V. The highest junction forward-current crest was 237 mA at 27 dBm / 39 mA. Infineon specifies 40 V reverse and 200 mA forward with a solder-point condition, plus a separate single-event surge rating. Repetitive 13.56 MHz pulse current, junction/package thermal margin and hot leakage still need confirmation. Use the external source's measured available power and controlled geometry before associating any of the higher dBm settings with a real operating mode. [Infineon datasheet, pp. 1–3](https://www.infineon.com/assets/row/public/documents/24/49/infineon-bas4002aseries-ds-en.pdf)

## RF cold start into the actual regulator equations

ADS also ran the carrier, fixed coils, fitted packaged bridge, effective 1 µF reservoir, TI TPS70950 transient macromodel and effective 4.7 µF output together from zero charge. The input source supplied 26 dBm available at nominal coupling. A conductance load was applied immediately, with current equal to the commanded value only when the output reaches 5 V. This tests a premature demand during startup. The 10 µs time windows below come directly from 6,836,613 saved native time points over 1.05 ms.

| Interval | Demand at 5 V | Actual mean 5 V rail | Actual mean load |
|---|---:|---:|---:|
| 330–340 µs | 24 mA | 2.353 V | 11.29 mA |
| 580–590 µs | 29 mA | 3.467 V | 20.11 mA |
| 830–840 µs | 39 mA | 3.945 V | 30.77 mA |
| 1040–1050 µs | 3.74 mA | 5.004 V | 3.743 mA |

The command fell to taper at 850 µs. The regulated output first crossed 4.75 V at 980.315 µs in this sequence. Use a qualified power-good indication to admit load. Derive the timeout and hysteresis from the real board after measuring load pulses, capacitor effective values and coil placement. The test does not determine whether any higher early load would reach regulation if held indefinitely. [Portable time windows](bridge-runs/startup/time-windows.csv) · [Native simulator log](bridge-runs/startup/simulator.log) · [Hash-verified native dataset archive](bridge-runs/startup/archive.json)

### Delayed load with a settled rail

A separate multiscale ADS transient uses the fixed-coil receiver's HB-derived DC current–voltage characteristics, the same TI regulator equations, 1 µF / 4.7 µF effective reservoir/output capacitances, and a low initial demand. It applies the 24 mA-at-5 V load after 5 ms, then independently raises the target to 29 and 39 mA. The additional HB sweep returned 63 valid operating points across three drive levels, supplemented by the converged operating-matrix points. Piecewise interpolation models the RF-averaged envelope and holds the lowest-voltage sample's current below roughly 0.09–0.13 V. This approximation omits individual RF cycles, field-switching physics, TVS current and the actual charger/status load law. Six rejected supplementary I–V points were excluded.

| RF source | Regulated output at 24 mA target | At 29 mA target | At 39 mA target |
|---|---:|---:|---:|
| 25 dBm | 4.998 V | 4.996 V | 4.108 V / 32.04 mA delivered |
| 26 dBm | 4.998 V | 4.997 V | 4.669 V / 36.42 mA delivered |
| 27 dBm | 4.999 V | 4.998 V | 4.995 V / 38.96 mA delivered |

The typical 25 dBm / 29 mA regulator case stays in regulation even though the conservative 6.0 V RAW screen failed. The case has limited margin. The 26 dBm / 39 mA case misses even the 4.75 V lower board-input threshold. The fixed resistance naturally reduces current in dropout. A real load can brown out or cycle. Measure instantaneous radio, MCU and charge currents before fixing the allowed power and duty cycle. [Regulator results](bridge-runs/delayed_load/results.csv) · [Portable rail waveforms](bridge-runs/delayed_load/waveforms.csv) · [Receiver I–V data](bridge-runs/iv/results.csv)

After the source field fell to zero at 26.05 ms, the regulated output remained above 4.75 V for 5.826, 6.938 and 8.185 ms following 25, 26 and 27 dBm operation respectively. The 1.74 mA-at-5 V conductance and energy stored in the input and output capacitors set this release delay. The rail can therefore remain valid after the physical field vanishes. Verify detector hysteresis and the charge-to-run transition with the actual battery, radio and control electronics. The completed dataset ends at 40 ms. A longer low-voltage solver tail was discarded.

## Reservoir clamp at light load

ADS ran 27 near-open cases at 25, 26 and 27 dBm for nominal coupling and two assumed stronger couplings of 0.10 and 0.13. At each operating point the same circuit was solved without a clamp and with two piecewise-linear SMAJ15A DC fixture curves. The fit uses 5 µA at 15 V, 1 mA at either 16.7 or 18.5 V and the published surge test point of 24.4 V at 16.4 A. Linear interpolation between these points is an assumption. The actual low-current knee, RF parasitics and thermal behavior were not measured. [Diodes Incorporated SMAJ15A](https://www.diodes.com/part/view/SMAJ15A)

At 27 dBm and nominal coupling, the lower-knee approximation produced 16.723 V peak and 7.36 mA average TVS current, or 123 mW continuous clamp dissipation. The upper-knee case produced 18.508 V peak and 38.3 mW, and the unprotected case reached about 19.53 V. RX winding dissipation still reached 213 or 254 mW with the clamp. The same transmitter tuning produced lower voltages at the two stronger simulated couplings. Actual geometry can move the resonance and the voltage maximum. Verify peak voltage on the 30 V-rated regulator input and verify steady thermal limits at light/open load. A quoted 400 W pulse rating does not specify continuous dissipation. [27 ADS cases](bridge-runs/tvs/results.csv)

## Model and reproducibility

### Bench acceptance without a VNA

1. Verify the actual generator or PA at 13.56 MHz into a suitable 50 Ω dummy load. At 26 dBm the target is 398 mW or 4.46 V RMS across 50 Ω. Record the delivered rating, source setting and any protection foldback. A front-panel voltage without its load setting is ambiguous.
2. Start with a current-limited electronic load and the published 10 mm aligned spacing. Simultaneously measure RECT_DC, the regulated 5 V output, delivered load current and TX available power. Sweep the expected charging and status loads. Check voltage across the load through radio-current bursts and at the actual rectifier input through a differential low-capacitance probe, accounting for probe loading.
3. Sweep tuning placements and substitutions in small steps while measuring loaded DC power and component temperature. Repeat with controlled separation and offset. Test near-open and charger disconnect using reduced RF power first. Confirm the field can be reduced or removed before coil, capacitor, bridge, regulator or TVS temperatures exceed their qualified limits. Even a protected 5 V output can coexist with excessive RF current.
4. Measure CHG_IN, charge current, digital-rail status pulses and AFE shutdown together using a battery emulator, then the qualified cell. Confirm the charger's battery-temperature programming and independent pack protection on the selected cell. Use these measurements to bound allowed source settings, charge current and status duty cycle.

### Assumptions and files

- The junction model is an **engineering fit**. At 25 °C the datasheet lists forward voltage at 10/60/100/200 mA and reverse capacitance at 5 V. The runner fits saturation current, ideality and series resistance to the tabulated typical voltages, then repeats with their tabulated maxima as a sensitivity case. The resulting empirical ideality factors are 0.804 and 0.665. The fits reproduce those four points within 0.84 mV. They cannot establish real subthreshold or reverse leakage. A square-root capacitance curve anchored at 2 pF typical or 5 pF maximum at 5 V approximates the published trend. Model parameters and fit residuals are in the execution JSON. No exact vendor RF macromodel was identified. The model omits measured package parasitics, recovery, voltage-dependent reverse leakage, avalanche and electrothermal behavior. The near-open simulations are particularly sensitive to actual leakage.
- The nominal case uses 1 nH and 8 mΩ per package lead, equivalent tuning-capacitor ESR from Q = 500 at 13.56 MHz, and a 1 µF effective reservoir with 0.7 nH ESL and 50 mΩ ESR. These assumptions expose plausible loading and stress. Capacitance under bias, capacitor Q and parasitics at harmonics and simultaneous tolerances await hardware evidence. Published winding losses are carrier-frequency measurements, extrapolated as constants in this model.
- The 54-case passive input-admittance control is archived separately. Its ADS results agree with an independent complex coil-matrix calculation within 3e−14 V. The 138-case nonlinear RF power balances close within 2e−15 W. Five critical HB31 operating points were repeated at both order 15 and 63. Increasing 31 to 63 changed the minimum RAW voltage by at most 3.17 mV and the junction forward-current crest by at most 1.25 mA. These are numerical checks inside the stated component assumptions. [Passive results](rf-envelope.csv) · [Nonlinear execution record](bridge-runs/matrix/execution.json) · [Convergence summary](handoff-metrics.json)
- Open the CSVs, JSON and logs on the next computer with ordinary tools. Each successful case family includes the ADS netlist and native dataset. With ADS 2026 Update 2, its bundled Python can rerun the study. Set `CURALINK_ADS_ROOT` when the installation path differs.
- The updated ADS fixtures are simulator-native text netlists under `bridge-runs`. The legacy ADS workspace cells still illustrate the earlier four-discrete simulations. The new netlist labels one four-terminal SOT-143 package and models the four junctions physically present inside it.

```powershell
$adsPython = Join-Path $env:CURALINK_ADS_ROOT 'tools/python/python.exe'
& $adsPython run_bridge.py search
& $adsPython run_bridge.py matrix --caps 60 375 1000 680
& $adsPython run_bridge.py tvs --caps 60 375 1000 680
& $adsPython run_bridge.py iv --caps 60 375 1000 680
& $adsPython run_bridge.py tx_trim --caps 60 375 1000 680
& $adsPython run_bridge.py order15 --caps 60 375 1000 680
& $adsPython run_bridge.py order63 --caps 60 375 1000 680
& $adsPython run_delayed_load.py
& $adsPython run_startup.py
```

To recover the large native startup dataset from the repository root, run `git lfs pull`, then `python hardware/wpt/ads/receiver-ic-review-2026-11-22/pack_transient.py --restore`. This writes and verifies the 821,275,136-byte ADS dataset. Substitute `--verify` to decode and hash the archive without restoring a copy. Viewing the CSV, text and JSON results requires no ADS installation or dataset restoration.

# CuraLink ADS receiver and charging-load study

Recorded **2026-10-09**, America/New_York. Actual ADS 2026 Update 2 simulations; nominal model results, not measured hardware or a released wireless charger. Accepted coil, BQ25185, cell and exclusive CHARGE/RUN baselines remain in [the engineering handbook](../../../docs/engineering-handbook.md).

## Objective and boundaries

For the current four-coax board and live BLE charge-status loads, use the [packaged-bridge runs](receiver-ic-review-2026-11-22/README.md) and [builder handoff](../../../docs/BUILD-NEXT.txt). The original discrete-bridge exercise below predates the telemetry rail.

Optimize useful DC delivery into the charging circuit, then constrain voltage, current and heating over its operating envelope. Start around **5 V at WPT_RAW**, with **120 mW** as the initial board-input qualification allocation. This includes charging and control/protection consumption. The AFE, MCU and BLE are OFF during CHARGE. No-load voltage, S11 or the paper's 70% coil-link efficiency alone establishes charging capability.

```text
50-ohm 13.56 MHz source -> TX matching -> published R-L-M coil pair
 -> RX matching -> floating full bridge -> 1 uF reservoir -> WPT_RAW
 -> polarity diode / input eFuse -> CHG_IN -> BQ25185 -> 1S cell
                               -> always-on control supply
WPT_RAW -> field detector -> recording-system hardware disable
```

The resistor study stops at WPT_RAW. It includes no downstream protection, charger or cell. The separate charger fixture is an authored approximation of input demand, not a TI macro. Keep source available RF power, accepted RF power, receiver DC power and battery charging power distinct.

**Charger-load execution update, 2026-11-22:** The original October attempts were license-blocked, as preserved in [their execution record](charger/SDD-execution-guidance.md). A new [fixed-coil review](review-2026-11-22/README.md) has now completed the authored-law DC check and 48 HB31 demand cases, plus a fresh passive paper-link and translated AFE DC/AC check. Nominal full-current demand is feasible, but all taper/complete fixtures exceed the authored voltage domain without raw regulation. These new equivalent standalone fixtures are not a complete BQ25185/cell model or direct rerun of every historical/native case.

## Open the prepared native ADS circuit

Use the existing workspace:

`C:\Users\angel\OneDrive\Documents\projects\curalink\MyWorkspace_wrk`

Open **MyLibrary_lib → RX_BAT54_LoadSweep_20261009 → schematic**. Refresh the library tree if necessary. The original `cell_1` and `cell_2` saved OA files were preserved and hash-checked. The new cell corrects a stale saved-ground connection so the secondary/bridge AC negative is `IMPin`, distinct from DC-negative ground. [Native-cell instructions and manifests](gui-setup/README.md) explain the save-state discrepancy and exact probe connectivity.

| Setting | Candidate starting value |
|---|---:|
| Source | P_1Tone, 50 ohms, 13.56 MHz, 23.5 dBm available power |
| HB | 13.56 MHz, order 31; sweeps initially disabled |
| Rload / reservoir | 208.333333 ohms / 1 uF |
| C3, TX series | 59.30046 pF |
| C5, TX shunt | 374.73956 pF |
| C1, RX series | 826.20585 pF |
| C6, RX shunt | 773.59319 pF |
| Diodes | Complete manufacturer BAT54 model, separately imported |

These capacitor values came from a finite 64-evaluation joint search at 26 dBm / 230 ohms, followed by lower-power confirmation. They are **ideal simulation candidates**, not stock component values, a global optimum or a robust hardware match. Final tuning requires the real load/protection, sourced capacitor values, losses, tolerances and coupling envelope.

Simulate the saved single point first. For the saved 15-point matrix, activate `SweepPower` and `SweepLoad`: 20/23/26 dBm and 208.33/220/240/470/1,000,000 ohms. Use order 7 for exploration only after comparing relevant results with order 15/31; the saved candidate uses 31. Keep ordinary S-parameter analysis for the passive link, and use HB at operating power for the nonlinear bridge. Do not put a 50-ohm Term across the rectifier input.

A third native cell, **MyLibrary_lib → RX_ChargerLoad_20261009 → schematic**, replaces R1 with the authored voltage-compliant SDD load. It is saved and netlist/readback-checked, but **not simulated**. Defaults are VBAT=3.7 V, IPHASE=20 mA, control=0.8 mA, fixed path-drop estimate=0.28 V, Pin=23.5 dBm and HB31. It includes an ideal 2.2 uF RAW-equivalent charger-input capacitance in addition to the 1 uF reservoir. The static law accounts for charger/overhead/control, eFuse overhead and field-divider demand; it is not an actual BQ25185/eFuse/cell/OVP circuit. The native cell measures total load DC current and uses `Pdc=Vdc*Idc`, retires the resistor-load sweep and retains RF probes. Individual charger/control readouts are estimates from the DC voltage and current law, not independent solved branch currents. See [the native load-cell instructions and manifest](gui-setup/README.md) before running battery-voltage/current snapshots. Source-power sweep is initially disabled.

## Actual results and what they imply

The **native saved-cell netlist was independently simulated successfully**. At 23.5 dBm / 208.333333 ohms, HB31 gives:

| Quantity | Native ADS result |
|---|---:|
| Available RF power | 223.872 mW |
| Accepted RF power at source interface | Approximately 219.009 mW |
| DC output | 5.08853 V / 24.42496 mA |
| Useful DC power | 124.287 mW |
| Available-RF-to-DC efficiency | 55.517% |
| Fundamental source impedance | 38.373 + j5.934 ohms |
| Fundamental RX load, including its match | 1.611 - j28.880 ohms |
| Bare bridge fundamental impedance | 130.470 - j25.148 ohms |

Fundamental power delivered into the RX matching/bridge is 151.517 mW, approximately 69.2% of accepted source power in this ideal-matching model. That is the closest boundary here to the paper's coil-link efficiency; the reported 55.517% uses available generator power and includes rectifier loss. Neither figure includes charger/battery conversion or predicts hardware efficiency.

The useful-power result clears the initial 120 mW resistor threshold by only about 3.6%; it provides no tolerance or hardware margin guarantee. The RX impedance differs from the paper's approximately 2.4 - j28.12 ohms because this is a nonlinear rectifier at a particular power/load. Use that literature value as a starting diagnostic; maximize bounded useful DC delivery instead of forcing an exact complex impedance.

Both RX tuning capacitors carry about 0.30 A RMS. An **assumed** 0.1 ohm ESR in each would add roughly 9 mW loss apiece, larger than the 4.3 mW nominal margin. This is a loss sensitivity calculation, not a claimed ESR for a selected capacitor, and illustrates why the ideal match is not ready for hardware release.

The equivalent isolated model gives 124.296 mW at order 31 and 124.314 mW at order 127. The 63-to-127 forward pulse-current peaks change by about 0.03%, and reverse capacitive-current peaks by about 0.98%. This is numerical convergence only: the paper supplies carrier-frequency coil parameters, not verified broadband/SRF behavior.

At the order-31 loaded point, each diode sees about **5.72 V reverse peak**, **121 mA forward peak** and **6.8 mW average dissipation**. TX/RX winding RMS currents are approximately **129/307 mA**, with **30/38 mW** modeled winding dissipation. The TX series capacitor sees about **36.1 V peak**. These require a component-rating, loss and thermal audit; no PCB temperature is predicted.

At the **same 23.5 dBm**, replacing the load with 1 megohm raises WPT_RAW to **11.915 V** and RX winding loss to **132 mW**. This is near-open-circuit behavior, not a regulated 5 V rail. Raw receiver overvoltage control and heating must be resolved before connecting the wireless input to the mainboard. Downstream eFuse cutoff and charger OVP do not clamp the coil/bridge/reservoir.

The original 4.2 V breakdown diode seed at 23 dBm / 240 ohms delivered only about **58 mW** and exceeded its earlier 4 V rating. That result is diagnostic and unqualified for a 5 V receiver. Increasing source power with that seed drives avalanche loss; it is not voltage regulation.

Raw datasets, decks, simulator logs, convergence checks and the comparison plot are retained in [the receiver study](receiver-fixture-2026-10-09/README.md). [Native validation metrics](receiver-fixture-2026-10-09/runs/native_BAT54_candidate_validation/metrics.json) separately establish the saved-cell result.

## Diode choice for this simulation

Criteria are reverse/pulse-current margin, forward and capacitive loss at 13.56 MHz, trustworthy model provenance, area, thermal behavior and LCSC availability.

| Option | Description | Pros | Cons / disposition |
|---|---|---|---|
| Existing BAT15-style seed | Very low-capacitance preliminary diode fit. | Low RF capacitive loading; useful historical diagnostic. | Its approximately 4 V rating is inadequate for demonstrated receiver reverse peaks; exclude it from 5 V charging qualification. |
| BAT54-7-F bridge | Four 30 V Schottky diodes using the intact manufacturer model. | Modeled voltage/current headroom and useful nominal DC power; LCSC C106920 is stocked. | Greater capacitance and four SOT23 packages; RF package/recovery, loss and thermal behavior remain unqualified. Candidate for the present comparison. |
| Other RF Schottky / active rectifier | Retune a genuinely rated diode candidate, or use controlled low-drop rectification. | Could reduce loss or board area. | Requires fresh model, sourcing, drive/startup and stress work; no selection in this task. |

Recommend **BAT54 as the current simulation candidate**, retaining the accepted charger/cell. Its [physical reverse rating is 30 V](https://www.diodes.com/datasheet/download/BAT54.pdf), although the manufacturer fit uses BV=50 V. The model has no explicit TT and does not independently validate the recovery specification. [LCSC C106920](https://www.lcsc.com/product-detail/C106920.html) showed 87,360 units on 2026-10-09; [dated evidence](charger/model-sources/BAT54-LCSC-stock-2026-10-09.json) records the exact variant. Stock is not reserved and assembly eligibility still needs confirmation. Reopen this candidate if package area, RF loss, stress or availability fails qualification.

## Measurements to inspect

`Vdc = real(mix(DCout,{0}))`; `Pdc = Vdc*Vdc/Rload`; `eta_avail = Pdc/dbmtow(Pin_dBm)` for the resistor fixture. The old `PWR=DCout` expression is voltage, not power.

Use `Z_source`, `Z_rx` and `Z_bridge` already added to the native cell. They divide carrier voltage by the corresponding series-probe current. RX voltages are differential to `IMPin`. These are fundamental large-signal impedances at the simulated operating point; a node has no unique impedance without a defined interface and current. Inspect DC power plus reconstructed voltage/current peaks, not just return loss. Accepted total RF power sums all harmonic contributions; the saved `Psource_f1` is fundamental-only.

For startup after the steady-state checks, use transient analysis with a carrier time step initially no larger than about 2 ns (13.56 MHz period is 73.75 ns), then check convergence and reservoir settling. The earlier disabled 10 us maximum-step setting is not a justified RF-resolution setting. A short RF transient does not validate the roughly 185 ms mode delay or hours of charging.

## Remaining power work, in order

1. **Charging demand:** replace the resistor with a voltage-compliant input-load fixture, sweep battery-voltage/CC/CV/termination snapshots and overhead, and include actual input drops/protection. See [charger-load guidance](charger/recommended-load-model.md). The nominal 5 V board demand is about 108.7 mW; the declared upper sensitivity is 119.8 mW. They are fixture calculations, not guaranteed whole-board limits.
2. **Raw overvoltage and source control:** choose and model a receiver clamp/regulator, detuning or transmitter-power reduction strategy. Verify light/no load, charging termination, weak/intermittent coupling, fault input and clamp heating. Protection changes the receiver impedance, so retune with it present.
3. **Practical matching and rectifier:** audit diode pulse/reverse limits, capacitor voltage/RF current/ESR, winding heat, reservoir effective capacitance, real footprints and stocked tuning populations. Sweep coil L/R/k, alignment assumptions and tolerances; reopen HFSS for changed geometry/nearby metal. Preserve tuning and DC test access because no VNA is available.
4. **Battery and charging:** close exact cell sourcing/protection, 20 mA / 4.1 V and temperature compatibility, current accuracy, CV/termination/timer and thermal checks. A static input sink does not model battery SOC or prove charge completion.
5. **Isolation and RUN:** test field application/removal and charge-complete-with-field-present, CE delays, opposed PMOS/backfeed, undervoltage/inrush/fault limiting, rail sequencing and one-hour usable runtime. Existing schematic and bounded LTspice protection evidence are starting points, not complete wireless qualification.

The receiver has demonstrated a useful **nominal resistor-load operating point**. Power design remains open until these gates are closed.

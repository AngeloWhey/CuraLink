# ADS charger input-load fixture

Recorded 2026-10-09, America/New_York. **Candidate authored behavioral approximation; not a TI BQ25185 macromodel, cell model, hardware measurement, or charging qualification.** The existing charger/cell decisions are preserved. Canonical circuit values remain in [the power handoff](../../../rev-a/power/power-design.md); numeric fixture assumptions are in [recommended-load-model.json](recommended-load-model.json).

**Execution update:** Standalone ADS SDD source and seven HB receiver cases are now prepared. The actual DC deck parsed and flattened, but two solver attempts failed because its simulator license was occupied. No solved SDD DC/HB result is established. See [the preserved execution status and run instructions](SDD-execution-guidance.md).

## Objective and model boundary

Tune the 13.56 MHz matching and rectifier for useful delivered DC power while exposing weak-source collapse, startup, and unloaded stress. A satisfactory high open-circuit voltage alone does not demonstrate charging power. Use separate RF steady-state and slow charge-control studies; resolving each carrier cycle for hours of charging is unnecessary.

Use these distinct nodes:

```text
RX matching / full bridge / reservoir -> WPT_RAW (5 V board-input target)
    -> SS14 -> WPT_PROTECTED -> TPS25200 -> CHG_IN -> BQ25185
                                               -> D502 / control LDO / control loads
WPT_RAW -> 100 kOhm + 10 kOhm field-detection divider
PACK+   -> D502 alternative supply for always-on control
```

At the charger boundary the approximate current is `I_CHG_IN = I_BAT_CHARGE + I_Q_CHARGER + I_CONTROL_FROM_CHG_IN`. The recording electronics are OFF in CHARGE and the charger's SYS pin has no recording load. The charger and control LDO are linear, so do not replace their input current with `P_battery/VIN` as if the charge path were an ideal switching converter. Required charger IN/SYS/BAT capacitors remain distinct; SYS capacitance is not an extra capacitor directly across CHG_IN.

## Verified parameter anchors

The following concise anchors come from [TI BQ25185 Rev. B](https://www.ti.com/lit/ds/symlink/bq25185.pdf), §§5.5 and 6.1–6.3:

| Anchor | Value and qualification |
|---|---|
| Enabled input overhead | 0.75 mA typical, 1 mA maximum; VIN=5 V, VBAT=3.6 V, charging enabled, ICHG=0, SYSREG=4.5 V |
| Sleep input draw | 30 µA typical; VIN=3.6 V, VBAT=3.7 V |
| Input UVLO | Rising exit 3 V typical; falling entry 2.7 V typical |
| Charging threshold | Rising 3 V typical / 3.15 V maximum; falling 2.95 V typical / 3.1 V maximum |
| Sleep/wake difference | Falling VIN−VBAT=82 mV typical; rising 152 mV typical, 122–188 mV with VINDPM active |
| VINDPM | VBAT+330 mV typical above VBAT=3.5 V; 3.6 V fallback; descriptive text rounds offset to 300 mV |
| Charge phases | Precharge 20% of programmed current below 3 V typical; termination 10%; recharge 100 mV below regulation |
| Timers | Charge 360 minutes typical; precharge 25% thereof |

The sleep-exit table contains duplicate rows with differing minimum values; use the explicitly conditioned row for a bound. The 330 mV VINDPM offset is typical and does not guarantee full charge current at that exact headroom. Twenty-milliampere charge accuracy still needs bench verification; the 18.81–21.21 mA range in the power handoff is a setting-factor/resistor calculation, not a complete low-current guaranteed tolerance.

## Model choices

| Option | Description | Advantages | Limits |
|---|---|---|---|
| Resistor fixture | A passive load chosen at a declared 5 V operating point. Start with 230 Ohm; sweep 220–240 Ohm and 208.33 Ohm. | Converges readily, draws zero at zero volts, useful for power cross-checks and initial matching. | Current falls with voltage; it cannot establish charger startup, charge current, DPM or charge completion. |
| Voltage-dependent SDD input load | An ADS `SDD1P` current law with sleep, wake and a reduced-current compliance region; use independent battery-voltage and charge-phase snapshots. | Captures a source that cannot sustain full charge load without imposing an unconditional sink at zero volts; appropriate first RF/DC study. | Authored static I–V approximation. Ramp widths and loop response are assumptions; no timer, hysteresis or battery dynamics. |
| Vendor model / slow averaged control model | A verified supplier macro if obtained, or an explicitly authored state machine fed by the measured/simulated DC receiver curve. | Can address enable sequencing, weak-source cycling, CV, termination and elapsed charge time. | No official BQ25185 SPICE/ADS macro was identified on the public product page in this review. An authored model needs loop and cell measurements to be predictive. |

Recommendation: use the resistor to establish an energy-feasible starting match, then the SDD snapshots to qualify the match under nonlinear charging demand. Use a slow averaged state model for charge completion and mode transitions. Revisit the assumed DPM/headroom band after characterizing the charger at 20 mA and sweeping its source impedance.

## Recommended SDD1P fixture

These equations are **component-entry instructions**, not a claimed tested native ADS netlist. Installed ADS 2026 Update 2 documentation confirms `SDD1P`, explicit `I[1,0]`, `_v1` for port voltage, and positive current entering the `+` terminal. Sources are the installed [SDD component reference](<C:/Program Files/Keysight/ADS2026_Update2/doc/ads/Content/ads2026update2/ccnld/SDD14P_(Symbolically_Defined_Devices,_1-12_and_14_Ports).html>) and [SDD modeling guide](<C:/Program Files/Keysight/ADS2026_Update2/doc/ads/Content/ads2026update2/modcreation/Custom_Modeling_with_Symbolically-Defined_Devices.html>).

1. Place `SDD1P` from **Devices – Nonlinear Equation**, or type `SDD1P` in Component History. Connect `+` to CHG_IN and the other terminal to GND.
2. Place a VAR component with the following constants. All voltages are V, currents A, and numerical ramp widths V.

```text
VBAT = 3.7
IPHASE = 0.020
IQACTIVE = 0.00075
IQSLEEP = 0.000030
CHARGE_ALLOWED = 1
VWAKE = max(3.0,VBAT+0.152)
VSTART = max(3.15,VBAT+0.188)
VDPM = max(3.6,VBAT+0.330)
WNUM = 0.020
WDPM = 0.150
```

3. Replace the default `I[1,0]=(_v1)/50.0` with:

```text
IQSLEEP*max(0,min(1,_v1/3.6))
+(IQACTIVE-IQSLEEP)*max(0,min(1,(_v1-VWAKE)/WNUM))
+CHARGE_ALLOWED*IPHASE*max(0,min(1,(_v1-VSTART)/WNUM))*max(0,min(1,(_v1-VDPM)/WDPM))
```

Enter the above as **one expression** in `I[1,0]`; the displayed line breaks are for readability. Leave controlling-current entries empty. Put the actual CIN branch across CHG_IN separately.

The charge sink is exactly zero at inadequate input voltage. The sleep term is deliberately tapered to zero at zero input so it cannot force a negative node. Use this fixture only for CHG_IN from 0 to 5.5 V; its high-voltage charger OVP behavior is excluded. The 20 mV width is numerical regularization; the 150 mV full-current band is a conservative **chosen sensitivity fixture**, not TI's loop specification or a measured dropout voltage. Sweep WDPM=0.05/0.15/0.30 V. `VDPM=max(3.6,VBAT+0.330)` intentionally uses the larger target in the transition region; it is not a reconstruction of TI's internal target-switch logic. At VBAT=4.1 V, the nominal WDPM=0.15 V fixture reaches full current at CHG_IN=4.58 V. This must be checked at the minimum of the rectified voltage waveform, after the SS14/eFuse losses, rather than against its unloaded value.

Use an additional SDD1P on CHG_IN for a first control-supply approximation:

```text
ICTRL = 0.0008
WOR = 0.100
I[1,0] = ICTRL*max(0,min(1,(_v1-VBAT)/WOR))
```

This approximates D502 handing control power to CHG_IN when it exceeds PACK+. It is zero when the battery supplies control instead. The diode-OR and LDO should be represented explicitly for startup/weak-source transitions; this law only assigns steady input demand. Sweep ICTRL=0.0008/0.0015 A. Do not also add this lumped current if the actual control branches are already modeled.

At WPT_RAW, retain the separate 110 kOhm field-divider load. Count input-eFuse supply current at WPT_PROTECTED if its actual model omits it. As a sensitivity fixture use 143/200 µA, recognizing [TI's published conditions](https://www.ti.com/lit/ds/symlink/tps25200.pdf) are VIN=5 V, no OUT load, and RILIM=33 kOhm, unlike this board's 1 MOhm setting. Model SS14 and eFuse voltage drops explicitly. Avoid adding a separate diode-loss current after its diode is already in the circuit.

`ItExp` is an exponential waveform source in installed ADS, not an arbitrary voltage-dependent load. `ItUserDef` is suitable for prescribed time waveforms. A plain linear VCCS or polynomial `NonlinVCCS` is less direct than SDD for clipped enable/compliance laws. No ADS component called `I_Exp` was verified here as a general behavioral-expression source.

## Operating snapshots and slow model

| Snapshot | VBAT | IPHASE | Meaning |
|---|---:|---:|---|
| Disabled | 3.7 V | 0; CHARGE_ALLOWED=0 | Quiescent/control loading fixture only; disabled IQ is not independently specified by this fixture |
| Precharge | 2.7 V | 4 mA | Battery-emulator boundary case, not permission to charge a real cell below its limits |
| CC nominal | 3.2/3.7/4.0 V | 20 mA | Main delivered-power tests |
| CC high-setting sensitivity | 3.7/4.0 V | 21.212 mA; IQACTIVE=1 mA | Calculated setting-factor plus overhead fixture |
| CV taper | 4.1 V | 5/2 mA | Declared operating-current snapshots; no inferred cell impedance or SOC curve |
| Charge complete | 4.1 V | 0 | Main system remains OFF while field present; test receiver no-load overvoltage |

For a slow state machine, initialize charging OFF; require valid input, field detected, RUN rails discharged, charge-ready permission, CE low and valid temperature before enabling. Adopt rising/falling UVLO and sleep thresholds as separate state transitions rather than the static SDD ramp. Start below-3 V cases in precharge, switch to CC after their declared threshold, and limit commanded current using the measured receiver I–V curve. Use CV regulation against a justified cell/emulator model. Terminate only when CV is dominant and the applicable completion conditions are valid; do not infer completion from small current caused by a weak source. Represent charge/precharge elapsed timers, recharge and source interruption explicitly. The current 80 ms minimum / 185 ms nominal charge-ready delay is a circuit calculation, not a verified timing guarantee. A carrier transient lasting tens of microseconds cannot show that delay has elapsed.

## Control power and forward energy balance

The old 300 µA external-control estimate is too small for the normal CHARGE topology as drawn. The circuit already has one LOW 10 kOhm STAT pull-up (approximately 300 µA), the 10 kOhm RUN_PERMIT pull-up sunk by FIELD_ABSENT through its diode (roughly 240–300 µA), and a 100 kOhm CE pull-up (30 µA). At 25 °C the NTC/reference divider branches add approximately 85 µA. These are calculations from the existing netlist, assuming 3 V control, settled outputs and a roughly 0.6 V signal-diode drop; status/output drops lower the resistor currents slightly. Control comparator, logic and LDO currents add further draw. The nominal 0.8 mA and sensitivity 1.5 mA control fixtures therefore have a physical basis but are **not guaranteed whole-circuit limits**. Slow logic transitions can increase input-stage supply current; qualify them separately. [TLV3012B](https://www.ti.com/lit/ds/symlink/tlv3012.pdf), [TPS7A20](https://www.ti.com/lit/ds/symlink/tps7a20.pdf), [SN74LVC1G17](https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf), [SN74LVC1G04](https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf).

At a 5 V WPT_RAW boundary, ignoring transient capacitor current:

```text
Nominal fixture: Iraw ~= 20 + 0.75 + 0.8 + 0.143 + 5/110 = 21.738 mA
Praw ~= 108.69 mW; equivalent R at that point ~= 230.01 Ohm
Upper sensitivity: Iraw ~= 21.212 + 1 + 1.5 + 0.2 + 5/110 = 23.958 mA
Praw ~= 119.79 mW; equivalent R ~= 208.70 Ohm
220 Ohm at 5 V: 22.727 mA, 113.64 mW
240 Ohm at 5 V: 20.833 mA, 104.17 mW
120 mW qualification resistor at 5 V: 208.333 Ohm
```

These figures count the same charge/control current through the series diode/eFuse and its dissipation through the voltage drop. Do not start with a 5 V charger-power number and then add diode loss while still calling the source boundary 5 V; compute each node's power consistently. For example with CHG_IN=4.72 V, VBAT=3.7 V and Icharge=20 mA, approximately 74 mW reaches the battery, 20.4 mW is charger pass-path heat, 3.54 mW is charger overhead, and about 6 mW of input power is lost across the 0.28 V series drop at the nominal through current. Control and eFuse consumption complete the forward accounting.

10 dBm is only 10 mW available RF power, so it cannot supply a 105–120 mW DC charging target even with lossless transfer. For 120 mW DC, the mathematical lossless source floor is 20.79 dBm. At assumed overall RF-source-to-board-DC efficiencies of 60%, 40% and 30%, the necessary source powers are 23.01, 24.77 and 26.02 dBm respectively. Those efficiencies are assumptions; derive the actual value from the rectifier/matching simulation and ultimately measurement. Sweep 20/23/26 dBm and verify source accepted power as well as available generator power.

## Official model/import status and verification gates

On 2026-10-09 the [public TI BQ25185 product page](https://www.ti.com/product/BQ25185) exposed the datasheet, application material and EVM; no official BQ25185 SPICE or ADS macro was identified. CAD symbols/footprints/3D models are not electrical simulation models. This is a finding about the reviewed public resources, not proof that TI has no unpublished model.

Installed ADS 2026 Update 2 [translator documentation](<C:/Program Files/Keysight/ADS2026_Update2/doc/ads/Content/ads2026update2/dataio/About_Netlist_Translator_for_SPICE.html>) supports PSpice and LTspice input dialects. If an unencrypted vendor model becomes available, use **File → Import → Netlist File → Options → appropriate Input Netlist Dialect**, initially choosing ADS Netlist output. Inspect `nettrans.log`, translated expressions and pin order; compare an independent DC-source charge test against the original simulator. The [translator troubleshooting guide](<C:/Program Files/Keysight/ADS2026_Update2/doc/ads/Content/ads2026update2/dataio/Troubleshooting_Netlist_Translator_for_SPICE_and_Spectre.html>) explicitly warns about unsupported syntax and simulator model differences. Encryption or a supplier-specific model format is not made portable merely by selecting a dialect; model conversion is unqualified until it passes reference tests.

Required checks: bridge polarity/grounding; averaged delivered power and energy balance; CHG_IN waveform minimum/headroom; high-setting and control-load sensitivity; weak field and no-load/charge-complete receiver stress; input/battery reverse flow; real diode capacitance/leakage and charger-loop behavior; effective capacitor values; cell protection/temperature/charge completion; actual mode sequencing. This input fixture closes none of the cell-protection or receiver-OVP release gates by itself.

## Rectifier-model qualification gate

The present ADS BAT15-style seed has `BV=4.2 V`. It cannot establish a qualified 5 V full-bridge receiver: reconstruct each diode's reverse-voltage waveform and compare its peak against the physical device's rating, including no-load and startup. A positive DC output sustained by modeled avalanche is not successful power delivery. Raising only `BV` to 30 V would invent a diode while keeping the low-voltage seed's forward and capacitance parameters.

For a separate diagnostic comparison, **Diodes BAT54-7-F** is an existing Rev A control-circuit SKU, LCSC C106920. The 2026-10-02 audit recorded 88,140 units; this file makes no current-stock assertion and no final rectifier selection. [The manufacturer datasheet](https://www.diodes.com/datasheet/download/BAT54.pdf) lists VRRM=30 V, continuous forward current 200 mA, maximum forward voltage 0.4 V at 10 mA and 0.5 V at 30 mA, capacitance 10 pF maximum at VR=1 V / 1 MHz, and reverse recovery 5 ns maximum under its stated test. This makes it a defensible candidate to simulate at 13.56 MHz / approximately 20 mA DC; it does not guarantee RF rectifier performance or permissible reservoir charging pulses. Four SOT23 packages also cost board area.

The genuine manufacturer-hosted [BAT54 SPICE file](https://www.diodes.com/spice/download/510/BAT54.spice.txt), linked from [Diodes' BAT54 page](https://www.diodes.com/part/view/BAT54/), is preserved intact in [model-sources/BAT54-diodes-original.spice.txt](model-sources/BAT54-diodes-original.spice.txt). It identifies a Zetex BAT54 v1.0 model last revised 25 April 2000. Its CJO=12.4 pF is about 90 times the existing seed's 0.1385 pF, making capacitance/loading and a new matching optimization consequential. Two conducting forward junctions also reduce voltage headroom and dissipate power; judge that loss from simulated current pulses rather than just twice the DC load current.

**Physical rating remains 30 V even though the official model uses BV=50 V.** Preserve the vendor fit and add a separate 30 V stress flag with design margin; the fit must not be interpreted as a 50 V component rating. The supplied card has no explicit TT, so its recovery dynamics are not independently represented by a 5 ns parameter. Package parasitics, temperature and manufacturing spread still need qualification.

The installed ADS 2026 Update 2 `nettrans.exe` successfully translated an isolated [PSpice fixture](model-sources/BAT54-translation-check.cir) into [native ADS netlist](model-sources/BAT54-translation-check.net), with [no translation warnings](model-sources/nettrans.log). Every manufacturer parameter, including IKF/ISR/NR, was retained. The translator additionally supplied `Nbv=1.04`, `Tnom=27`, `IkModel=1`, `Imax=1000`, `Trs1=0` and `Trs2=0`; use this documented mapping rather than manually dropping unfamiliar terms. This is conversion verification, not an independently completed DC or HB model-validation run. The [source manifest](model-sources/source-manifest.json) records exact URLs, SHA256 and limits.

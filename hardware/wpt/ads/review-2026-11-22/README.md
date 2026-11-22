# Fixed-coil power and signal review — 2026-11-22

**Result: the nominal link and AFE bias/gain work in the declared ADS models; the complete circuit is not ready for assembly signoff.** Receiver regulation/protection, input loading, shared bias and physical return paths remain unresolved. This review holds the published coils fixed. It does not select new parts, adopt the ADC recommendation, change circuit values or qualify a lithium charger.

## Constraint and source of truth

Use D-018 / DEC-WPT-003 in [the handbook](../../../../docs/engineering-handbook.md): Luo et al., [Design and Optimization of Planar Spiral Coils for Powering Implantable Neural Recording Microsystem](https://doi.org/10.3390/mi14061221), Micromachines 2023. The paper separates coil optimization from the load transformation; a changed load requires a suitable transformation network, not a new coil geometry.

The fixed nominal model is 13.56 MHz, TX 2.49 uH / 1.80 ohms, RX 0.330 uH / 0.399 ohms, k=0.0662 (approximately 60 nH mutual inductance), with the selected 40 mm / 10 mm pair at 10 mm separation. All review runs retain those values. Constant carrier-frequency R/L/k does not establish harmonic/SRF or changed-environment behavior. Preserve the paper's geometry/stackup conditions; new nearby ground copper or a battery can change the link without changing the spiral drawing.

The main ADS workspace contains power-link studies; `cell_2` is not a neural AFE. The current AFE candidate is in KiCad and LTspice. This review additionally translates that exact fixture to native ADS for DC/AC checks. [The independent source/return audit](../../../../docs/reviews/2026-11-22-signal-return-review.md) links the canonical schematic and simulation netlists.

## Fresh passive-link consistency check

[check_published_link.py](check_published_link.py) actually ran an ADS two-port S-parameter analysis at exactly 13.56 MHz using the fixed coils, 50-ohm ports and original matching values: TX series/shunt 61.3/438 pF, RX series/shunt 673.3/1050 pF.

| Observable | Fresh ADS result |
|---|---:|
| S21 power ratio | 0.7187346 = **71.87346%** |
| S21 | -1.43431 dB |
| Input return loss | 38.3288 dB |
| Load presented to RX coil | **2.38008 - j28.07827 ohms** |

An independent complex-impedance matrix calculation agrees with ADS to displayed numerical precision. The result is consistent with the paper's approximately 71.9% theoretical limit and approximately 70% measured matched coil link. It excludes the rectifier/charger. It is not a new measurement or proof that fabricated CuraLink coils will reproduce that efficiency. [Dataset, deck and log](power-runs/published_passive_link) and [summary](published-link-check.json) are retained.

## Fresh nonlinear receiver and charger-demand check

The separate manufacturer BAT54 candidate and previously searched ideal capacitor values remain TX series/shunt 59.30046/374.73956 pF and RX series/shunt 826.20585/773.59319 pF. A fresh HB31 resistor point at 23.5 dBm / 208.333333 ohms reproduces **5.0887108 V / 124.295894 mW**. This is a standalone counterpart of the previously validated native cell, with the same fixed coils; it is not a new hardware tuning selection.

[run_power_review.py](run_power_review.py) then actually ran **48 HB31 cases**: VBAT=3.2/3.7/4.0/4.1 V; imposed phase demand=20/2/0 mA; available TX power=23/23.5 dBm; nominal/high-setting overhead. The high sensitivity uses 21.212 mA full-current demand, 1 mA charger overhead and 1.5 mA control, versus nominal 20 mA / 0.75 mA / 0.8 mA. These are declared fixtures, not guaranteed maxima or simulated battery CC/CV dynamics.

The fixture includes the bridge, 1 uF reservoir, 2.2 uF input capacitance, divider/eFuse-overhead assumptions and a **fixed 0.28 V path drop**. It omits the real eFuse clamp/cutoff, actual charger control loop and raw OVP. The authored charger law is valid only for the declared 0–5.5 V CHG_IN domain.

Representative VBAT=4.1 V imposed-demand cases:

| Available TX | Demand / overhead | WPT_RAW | CHG_IN estimate | Derived phase current | Interpretation |
|---|---|---:|---:|---:|---|
| 23 dBm | 20 mA, nominal | 5.09684 V | 4.81684 V | 20.000 mA | Nominal full-current fixture is feasible; 110.80 mW raw demand. |
| 23 dBm | 21.212 mA, high | 4.85176 V | 4.57176 V | 20.0465 mA | Compliance reduces the commanded current; no full high-setting guarantee. |
| 23.5 dBm | 20 mA, nominal | 5.75144 V | 5.47144 V | 20.000 mA | Above the 4.75–5.25 V normal board-input target; real protection must be included. |
| 23.5 dBm | 21.212 mA, high | 5.21708 V | 4.93708 V | 21.212 mA | 124.70 mW raw in this fixture; no tolerance/thermal guarantee. |
| 23 dBm | Complete / nominal overhead | 10.44486 V | 10.16486 V | 0 mA | **Outside model domain; rejected as a charger operating point.** |
| 23.5 dBm | Complete / nominal overhead | 11.12218 V | 10.84218 V | 0 mA | **Outside model domain; rejected as a charger operating point.** |

All 32 taper/complete variants exceed the authored voltage domain. These unclamped extrapolations expose the need for raw regulation/protection; they do not predict the real charger's high-voltage behavior. Real eFuse cutoff can further unload the receiver, and is absent here. Matching alone cannot hold a constant DC rail as charging demand falls. A regulator/clamp, detuning or TX-power-control strategy must be designed and then included in the matching/load study.

The independent ADS DC I–V check gives zero current at zero input, 20.75 mA charger draw plus 0.8 mA control at 5 V, and only 25 uA charger draw at a weak 3 V input. This validates the authored law's sign/compliance implementation, not TI behavior. All 48 modeled RF power balances close within 6.8e-16 W. [Summary and DC checks](power-summary.json), [full matrix](power-matrix.csv), [datasets/logs](power-runs) and [analysis script](analyze_power_review.py) are preserved.

Ideal capacitors still omit ESR/ESL and voltage-dependent capacitance. Existing approximately 0.30 A RX capacitor currents and 36 V TX-series-capacitor peaks make loss/rating selection consequential. The small margin over 120 mW is not a robust component/tolerance qualification.

## DC return and signal-path checks

The corrected bridge must retain a floating AC return `IMPin`, distinct from the DC-negative node. Its two conduction loops are:

```text
Positive half-cycle: RX+ -> upper right diode -> DCout -> load
                    -> DC-negative -> lower left diode -> RX-
Negative half-cycle: RX- -> lower right diode -> DCout -> load
                    -> DC-negative -> upper left diode -> RX+
```

Grounding RX- together with DC-negative eliminates the intended full-bridge operation and can clamp one AC half-cycle. Use the corrected `RX_*` candidates rather than assuming the older `cell_1` saved OA is equivalent to its generated netlist. Simulation's common reference is not an instruction to wire the external TX and RX grounds together in the wireless hardware.

For the neural AFE, the independent static audit finds 22 MOhm input/REF bias returns to VMID, feedback on all 36 amplifier units, matched AC coupling, valid unused-unit followers, and all eight 150-ohm / 470-pF ADC interfaces. It finds no electrical mismatch between 236 canonical passives, 36 units, the canonical netlist/JSON/XML and 598 targeted KiCad pins. This does not check a routed return plane.

The fresh ADS model translates the real original-equation TI-family fixture, rather than substituting ideal amplifiers. The corrected DC/AC analysis gives approximately **VMID 1.50048 V**, **ADC bias 1.50319 V**, **4.4718 mA analog rail draw**, and **969.742 V/V at 1 kHz**. All 36 nominal operating points are valid. [AFE results, topology checks and source mappings](afe) retain the exact model-port limitations.

ADS adds 252 DC paths inside the translated vendor macros, exactly seven per amplifier; none is an external CuraLink node. A separate lower-GMIN initialization did not complete within its 180 s limit, so sensitivity to this simulator correction remains unqualified. The translator also drops a noise-only resistor-temperature setting. The first incorrect single-frequency AC diagnostic is retained as rejected; the corrected run uses explicit frequency plans and two original differential/common-mode stimuli. Noise, full transient recovery, MCU ADC switching, rail sequencing and unpowered-input injection are not qualified by these DC/AC runs.

Fresh linear spectra reproduce **-52.22 dB sampled worst quiet-channel coupling** through shared VMID (300 Hz–7 kHz sampled points), and approximately **0.823 MOhm input impedance at 7 kHz** with the stated FFC parasitics. The latter fails the unchanged >=10 MOhm requirement. A numerical crosstalk acceptance limit still needs adoption; the earlier proposed -60 dB target was not accepted. Existing dated startup/offset evidence still requires recovery/blanking qualification.

## Buffer proposal and builder handoff

A voltage buffer is useful for sensing: high input impedance reduces current drawn from the observed signal, and its powered output drives a separate load. It has finite input capacitance, current, bandwidth and stability limits. The AFE already has input amplifiers; another buffer does not remove the capacitance ahead of its input.

For received power, `P_in = V_rms^2 * Re(1/Z_in)`. Making the RF input arbitrarily high impedance reduces real power extracted from the coil. A powered buffer's output energy comes from its supply; ignoring that supply creates a false RF-to-DC efficiency claim. A high-impedance measurement branch can be buffered, but the charging-power path must still present an appropriate real load to the fixed coil. A regulated receiver stage can manage that load, with conversion/control/dissipation accounted for; it cannot make downstream energy demand disappear.

Before another agent builds out the hardware:

1. Retain the fixed paper coils; add/model the actual raw voltage-control/protection and charger input path, then retune the transformation network for its operating envelope. Check light load, taper, termination and faults as well as CC.
2. Select practical tuning/rectifier parts with voltage, RF current, ESR, tolerance, thermal and LCSC evidence; preserve tuning/current-measurement access.
3. Resolve the AFE input-loading requirement and shared-VMID performance/recovery. Do not silently relax either a requirement or a proposed threshold.
4. Close cell sourcing/protection, NTC/current/CV, exclusive CHARGE/RUN timing, unpowered interfaces and usable runtime.
5. Route and independently verify the PCB's physical returns, planes, crosstalk, RF keepouts and schematic links. The saved placement is not a completed board.

The source model also assumes 199.5–223.9 mW available at a 50-ohm TX interface (23–23.5 dBm), excluding unspecified external cable/PA losses. Confirm the actual generator or PA can supply that at 13.56 MHz. An ADS power setting alone is not instrument verification.

The sources, returned topology and declared nominal behavior now have stronger evidence. These open gates still prevent a full clean-signal or fabrication signoff.

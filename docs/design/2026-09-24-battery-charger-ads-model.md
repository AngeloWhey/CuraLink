# Candidate 1S battery and charger model for ADS

**Recorded 2026-09-24 · BQ25185 selection and PGEB201212 candidate assessed.** The charger IC selection is accepted. The user has identified PGEB201212 as the intended cell candidate, but exact cell specification, safe charge rate, protection, charger compatibility, RX OVP, and runtime/power result are not verified.

**Later review on the same date:** See the [cell/charger/isolation review](2026-09-24-cell-charger-isolation-review.md) for corrected PGEB interpretation, 55/100 mAh alternatives, BQ25185 enabled-current overhead and six-hour timer, bridge-grounding correction, and proposed PMOS hardware interlock. Earlier ideal current-sink calculations below are source-capability illustrations, not complete charger input budgets.

## Decision criteria

- 1S, 4.2 V maximum-charge Li-ion/polymer chemistry and a safe CC/CV charge profile.
- Small cell and charger footprints, but enough usable capacity and discharge-current rating for at least one hour of the measured system load.
- Input overvoltage behavior compatible with the rectifier's *loaded and no-load* `WPT_RAW` envelope; clarify whether OVP disconnects or clamps.
- Cell temperature monitoring, backup cell protection, manufacturable package, and test access.
- An ADS model that captures the RF rectifier/load boundary without pretending the charger is a resistor or a linear RLC network.

## User-nominated cell candidate: PGEB201212

A retailer listing for model **PGEB201212** reports an 8 mAh, 3.7 V Li-poly pouch cell, 4.2 V charge voltage, recommended charge rate 0.2C, and **no protection**. That gives a listed recommended charge current of `8 mAh × 0.2C = 1.6 mA`. The listing states there is no specification sheet; its discharge-current notation is ambiguous (the 1 CmA entry is not a verified 1 mA limit), so do not use them for a final design. Treat 1.6 mA as a provisional supplier-listed recommendation, not a verified manufacturer limit. [Retailer listing](https://visbis.com/categories/batteries/li-polymer/pgeb201212.html).

This candidate has not been qualified for the selected BQ25185 baseline; a recommended rate is not a verified maximum: TI specifies the programmable ISET charge-current range starting at 5 mA, above the listed 1.6 mA recommendation. The cell supplier/manufacturer must confirm a safe minimum/maximum charge current and whether 5 mA is permitted before connecting this cell. A specification for a similar but different model, **GEB201212C**, lists 10 mAh, 4.20±0.05 V CV, 0.2C standard charge and 1C maximum; do not transfer those limits to PGEB201212 without written confirmation. [GEB201212C manufacturer specification copy](https://www.powerstream.com/lip/PGEB201212C.pdf).

The 8 mAh listing also fails CuraLink's one-hour runtime objective at the current estimated 25–35 mA system draw: ideal capacity-only runtime is only about 14–19 minutes, before usable-capacity, LDO-dropout and pulse-load losses. Its listed 0.5C discharge rating would be 4 mA, below the estimated load, although the listing is inconsistent and not a reliable final limit. The cell therefore remains a candidate for characterization, not a viable system selection on current evidence.

The previously reviewed Adafruit protected 100 mAh pack is retained below as an alternative reference candidate, not the user's nominated cell. It remains unsuitable as a final pick until its discharge current, protection behavior, NTC and runtime are verified.

## Earlier alternative cell candidate

The smallest straightforward protected pack found for a useful runtime starting point is Adafruit product 1570: 1S, 3.7 V nominal, approximately 100 mAh, vendor-listed pouch size 11.5 × 31 × 3.8 mm, with a pack protection circuit for overcharge, overdischarge and output short. The vendor says to charge at 100 mA or less and says the pack has no built-in thermistor. [Product page and reports](https://www.adafruit.com/product/1570).

At the current provisional 25–35 mA system-current estimate, ideal capacity-only runtime is 2.9–4 h. Applying an illustrative 80% usable-capacity factor gives 2.3–3.2 h, still above the one-hour objective. These are rough calculations only: the estimate is not a measured current, pack discharge/PCM limits were not found on this product page, and a 1S cell falling toward 3 V may no longer support the proposed 3.0 V LDO rails. Verify rail dropout and actual current before calling this the smallest suitable cell. The pouch's PCM is backup cell protection, not the normal charging control. Add a 10-kΩ NTC thermally coupled to the cell or choose a pack with an integrated thermistor; this pack does not include one.

## Charger candidates

| Candidate | Fit and tradeoffs |
|---|---|
| **TI BQ25100 (not selected)** | 1S, fixed 4.2 V CV, small 1.60 × 0.90 mm DSBGA and 6.5 V input OVP. Rejected for the current build after the user selected an LCSC-stocked alternative; its lower OVP would still disconnect rather than clamp the receiver output. [TI product page](https://www.ti.com/product/BQ25100). |
| **TI BQ25185DLHR (selected)** | 1S 1-A linear charger, power path, resistor-programmable charge voltage/current, input-current limit, battery-tracking VINDPM, TS, thermal regulation, and a 2.2 × 2.0 mm WSON-10-EP package. User selected it because it is listed in stock on LCSC; listing is LCSC **C19725033**. The 18.5 V nominal input OVP is far above the approximately 5 V receiver target and only trips the charger protection path; it does not clamp `WPT_RAW`. [LCSC listing](https://www.lcsc.com/product-detail/C19725033.html) · [TI product page and Rev. B datasheet](https://www.ti.com/product/BQ25185). |

**Selected charger baseline:** BQ25185DLHR (`LCSC C19725033`) per the user's 2026-09-24 selection. LCSC's listing showed it orderable/in stock when checked; stock can change. The charger choice does not select the cell, imply that WPT power is adequate, or eliminate the need for separate `WPT_RAW` overvoltage control. Preserve exclusive CHARGE/RUN: do not allow the charger's SYS power-path output to run the AFE/MCU during charging; keep a hardware-controlled system disconnect and use zero SYS load for the first charger-load simulation.

### BQ25185 ADS starting values from the datasheet

Use standard 4.2 V Li-ion/Li-poly settings. The previous 40 mA starting point was based on the earlier 100 mAh alternative and is **superseded for PGEB201212**. Do not finalize hardware charge current until the exact cell manufacturer confirms its limits.

- `R_ILIM/VSET = 24 kΩ` selects `VBATREG = 4.2 V` and the 100 mA input-current limit.
- BQ25185's listed minimum programmable charge current is 5 mA; `R_ISET≈300 AΩ / 0.005 A = 60 kΩ` is a nominal minimum-current setting. This is above PGEB201212's retailer-listed 1.6 mA recommendation, so it is only an ADS lower-bound case until the manufacturer confirms safety. The older 7.5 kΩ / 40 mA setting is not appropriate for this 8 mAh candidate.
- Datasheet typical phases: precharge below `VLOWV≈3.0 V` at about 20% of fast-charge current; CC at the programmed current; CV at 4.2 V with current taper/termination around 10% of fast-charge current. For source capability, simulate 1.6 mA as the cell listing's provisional desired rate and 5 mA as the charger's minimum programmable case; neither establishes a safe compatible battery/charger design.
- Set the TS/MR network for the selected cell's actual NTC and temperature limits; do not assume a fixed resistor provides cell-temperature protection.
- TI's starting decoupling values: `CIN≥1 µF` after derating (TI recommends 25 V rating), `CSYS=10 µF` nominal, and `CBAT=1 µF`. The RF reservoir is additional; place charger decoupling near the IC.

TI's Rev. B design example gives `18 kΩ` for 4.2 V regulation with a 500 mA input limit; `24 kΩ` selects the lower 100 mA input limit, more suitable for early low-power WPT tests. The exact orderable part is BQ25185DLHR / LCSC C19725033. Recheck stock and datasheet revision at BOM release.

## What OVP means in this chain

The BQ25185's **input OVP** monitors `IN`; an input fault changes the charger's internal power-path state and reports a recoverable fault. Its nominal trip is approximately 18.5 V, so it is not protection for a receiver rail intended to stay near 5 V. It neither clamps the rectifier/reservoir node nor independently limits cell charging; normal 4.2 V CC/CV regulation and the cell pack's independent PCM are different protections. Keep a separate `WPT_RAW` clamp/regulator or TX shutdown strategy if the rectifier can exceed ratings, especially at high coupling/no load.

## ADS model plan

A charger is not an RLC load. The BQ25185 is a **linear, controlled-pass-FET charger with power-path control**. Capacitors at `IN`, `SYS` and `BAT` and the cell's electrochemical dynamics are reactive, but the charger load changes with input voltage, cell voltage, charge phase, temperature, OVP, input limits and timers.

Use separate simulation timescales:

1. **13.56 MHz rectifier and matching:** use the user's matched lumped-coil model, matching networks, nonlinear diode rectifier, reservoir and charger input decoupling. Use ADS Harmonic Balance with a 13.56 MHz fundamental and enough harmonics for the diode waveform; transient is useful for startup but not the first tool for tuning this RF/DC operating point. Tune against an explicit operating load. The previous 40 mA sink was based on an earlier 100 mAh alternative and is superseded for the 8 mAh PGEB201212 candidate. Sweep a DC sink at 0, 1.6 and 5 mA (then higher only if supported by the supplier-confirmed cell charge limit). The 1.6 mA case reflects the retailer's provisional 0.2C recommendation; the 5 mA case is the BQ25185's minimum programmable charge current and is not safe for the cell without confirmation. With `ISYS=0`, a linear charger's input current is approximately its battery charge current plus quiescent overhead. At `VIN=4.0 V`, 1.6 mA needs at least 6.4 mW DC; 5 mA needs 20 mW, before rectifier and coil losses. If `Pin_dBm=10`, the RF source has only 10 mW available, so it cannot sustain the 5 mA case. Record `VDC`, ripple, load current and `PDC=VDC×Iload`; a resistor can be used as a power cross-check (`R=V/I` at the chosen operating point), but it does not model CC/CV behavior. The load model is for RF/DC capability, not the BQ internal loops.
2. **Slow charger/battery transient:** for a cell confirmed compatible with BQ25185, represent the charger with a datasheet-parameterized behavioral model: precharge below about 3.0 V at approximately 20% of the programmed current; constant-current phase at the selected cell-safe current; 4.2 V constant-voltage phase with current taper toward termination. The 40 mA / 4 mA termination example applies only to the earlier 100 mAh candidate and is superseded for PGEB201212. For PGEB201212, the available listing suggests 1.6 mA while the charger minimum is 5 mA, so do not model either as a validated charging profile without supplier confirmation. Apply the 100 mA input-current ceiling and approximate battery-tracking VINDPM at `VBAT+0.33 V typical (Rev. B electrical table; descriptive text rounds to 0.30 V)` by reducing charger current as `VIN` approaches that threshold. Include the nominal 18.5 V input-OVP disconnect, `VIN` power-good/sleep behavior, TS faults and no system load in CHARGE. Recharge threshold is approximately 100 mV below regulation. Include the six-hour safety timer when assessing whether a charging cycle can complete; a steady-state source model alone cannot establish completion. This is a behavioral approximation, not an official IC macromodel.
3. **Battery representation:** use a state-of-charge-dependent open-circuit voltage source plus series resistance from a cell datasheet, with one parallel RC polarization branch only if the cell transient data supports it. Add a capacity/SOC integrator for charge time. If no suitable cell impedance/discharge curves are available, use ideal cell-voltage boundary cases (e.g. low, nominal and 4.2 V) and do not invent an R, L or C value. An equivalent RLC-only network cannot represent CC/CV control or state of charge.

Do not simulate hours of battery charging while resolving every 13.56 MHz carrier cycle. Use the RF/rectifier study to characterize DC source capability, then a slower averaged charger/cell simulation to estimate charge phases and thermal/power boundaries. TI's public BQ25185 page provides the current Rev. B datasheet and evaluation material; no official ADS/SPICE charger macro-model was identified during this review. If a vendor model becomes available, confirm its supported simulator and operating modes before relying on it.

## Open verification gates

### First ADS 40 mA load run — 2026-09-24 (user-reported, preliminary)

The supplied transient plot shows the rectifier output marker `DOut = -0.513 V` at approximately `68.8 µs` with an `I_DC` load set to 40 mA. Treat this as a failed/unresolved operating point, not a positive 530 mV charging rail: the ideal sink is oriented to draw current from `DOut` to ground and can force the node negative when the source cannot sustain the imposed current, or the rectifier output polarity/probe reference may be reversed. First remove the sink or set it to 0 mA and check the bridge's DC polarity, then test a small load and sweep upward while monitoring source power and `VDC`.

If `Pin_dBm` is still 10 dBm as in the earlier setup, the source provides at most 10 mW available RF power; 40 mA at 4.0 V needs 160 mW DC before coil and rectifier losses, so that operating point cannot be sustained from this source. Confirm the current variable value, then sweep RF input power and load together using the matched lumped-coil schematic. No charging-threshold pass or battery behavior is established by this plot. The user also reports that their lumped coil model plus TX/RX matching networks and terminal ports reproduced the paper's matching effects; the schematic/data have not been independently inspected.

- Simulate and measure the rectifier output range at unloaded, weak-coupling, nominal and best-coupling conditions. The BQ25185's 18.5 V OVP does not establish safe `WPT_RAW`; bound the rail and protect it independently.
- Obtain the manufacturer's exact PGEB201212 specification and written confirmation that at least 5 mA CC charging is permitted; obtain discharge, PCM, impedance and NTC data. Reopen the cell choice if its 8 mAh capacity or discharge-current limit cannot meet the one-hour runtime and system peak-current requirements.
- Close the 1S-to-3.0 V LDO dropout problem; the cell's cutoff and low-state voltage may truncate usable runtime before nominal capacity is exhausted.
- Confirm LCSC stock, WSON footprint, minimum input margin under rectifier ripple, NTC installation, charger temperature rise and CHARGE/RUN isolation. Resolve the BQ25185 5 mA minimum-current versus PGEB201212 1.6 mA listed recommendation before hardware charging. Keep BQ25185 SYS from powering the main system while WPT is present; preserve D-007's hardware system-off rule.

## Sources

- TI, [BQ25185 product page and Rev. B datasheet](https://www.ti.com/product/BQ25185), revision dated Aug. 2026: 3–18 V input, 4.2 V selection (other supported values include 4.1 V and 4.35 V, not 4.3 V), 24 kΩ input-limit/regulation setting, ISET relation, CC/CV control, VINDPM, OVP, TS and passive recommendations.
- Retailer, [PGEB201212 listing](https://visbis.com/categories/batteries/li-polymer/pgeb201212.html): 8 mAh, 3.7 V, 4.2 V charge, listed 0.2C recommended rate and no protection; page says no specification sheet and uses ambiguous discharge-current notation. Treat as candidate evidence only, not a manufacturer-qualified battery specification.
- General Electronics Battery, [GEB201212C specification copy](https://www.powerstream.com/lip/PGEB201212C.pdf): similar size family but a distinct model suffix; do not apply its 10 mAh/high-discharge ratings to PGEB201212.
- LCSC, [BQ25185DLHR, C19725033](https://www.lcsc.com/product-detail/C19725033.html), WSON-10-EP (2.2 × 2 mm); stock verified on 2026-09-24 and subject to change.
- Adafruit, [100 mAh Li-poly pack product page](https://www.adafruit.com/product/1570): pack capacity, vendor dimensions, included protection, charge-rate guidance and no built-in thermistor.

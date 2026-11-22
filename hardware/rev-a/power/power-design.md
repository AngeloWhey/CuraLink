# CuraLink Rev A power circuit — schematic handoff

Recorded 2026-10-01, America/New_York. Status: **engineered prototype recommendation; not measured, not fabrication released for battery/WPT operation**. This supporting file does not accept new decisions on the user's behalf. The machine-readable pin/net definition is [power-components.json](power-components.json); calculations and assumptions are in [power-calculations.json](power-calculations.json).

## Functional objectives and selection criteria

The main board needs quiet regulated power for eight analog channels and the STM32WBA52, at least one hour of eventual battery runtime, and hardware exclusion between charging and recording. Rev A must expose faults, permit power-path isolation, and support a current-limited emulator before connecting a lithium cell. Select parts by actual input/output limits, low-current behavior, startup and shutdown behavior, threshold tolerances, usable battery capacity, LCSC availability, assembly footprint, and total prototype cost. Component absolute maximum ratings do not establish an operating target.

The expected current is a design estimate: initially budget 15 mA battery current including AFE/MCU/BLE/control, retain a 25 mA steady qualification ceiling, and measure radio/startup pulses. The cell's minimum rated capacity is 50 mAh. Its discharge rating permits 1C only at 15–60 °C; no separate pulse rating has been established, so do not authorize a 60 mA pulse from this cell.

## Topology choice

| Option | Description | Advantages | Disadvantages |
|---|---|---|---|
| BQ25185 SYS supplies the system | Use the charger's intended power-path output for normal operation. | Integrated source selection and battery supplement path; fewer external switches. | Conflicts with the requested recording-OFF-while-charging behavior unless another downstream switch is added; SYS protection thresholds are much too large to establish protection for this small cell. |
| Protected BAT branch with external isolation | Retain BQ25185 charging, and feed the RUN circuit from the protected battery terminals through opposed PMOS devices. | Keeps exclusive operation explicit and independently observable; blocks the OFF path in both directions. | Requires its own undervoltage, fault-current and battery protection analysis; charger protections do not cover this branch. |
| Shared 3 V analog/digital regulator | Feed AFE and MCU from one regulator with a separate analog routing branch. | Simplest supply sequencing; low cost and no independent regulator mismatch. | BLE load transients share the regulator with the AFE/reference; weaker analog/digital separation. |

Recommendation: retain the selected BQ25185 and external protected-BAT RUN branch, with separate 3 V analog/digital TPS7A20 regulators and a hardware digital-voltage sequencer. A shared-rail link is included DNP as a bench alternative. This preserves the established architecture while resolving the independent-rail startup issue.

## Charge input boundary

The initial assembled board is tested using **5.0 V from a current-limited bench supply** into J503, with R543 populated. Normal source range is 4.75–5.25 V; begin with a 30 mA current limit after verifying charging can complete with control overhead. J502 is the future qualified 5 V receiver-DC interface, with R542 DNP. Never populate R542 and R543 concurrently.

D501 SS14 provides reverse-polarity blocking. U502 TPS25200 provides a second protective boundary: output clamping around 5.4 V, input overvoltage shutdown, thermal shutdown, adjustable current limit, and disabled-state reverse blocking. R511 is now 1.0 MΩ +/-1% (stocked C26083), changed from 1.1 MΩ because the latter tolerance exceeds TI's 1.1 MΩ recommended resistance ceiling. Eq. 1 estimates approximately 56.9–138.4 mA at the stated corners; this is an equipment-fault limiter, not a 20 mA charge-current setting or a guaranteed 50 mA cell-safe cutoff. Charge current is set separately by the charger. The TPS25200 is rated for 2.5–6.5 V normal operation and up to 20 V input stress; this does not qualify an RF receiver with unbounded no-load voltage. [TI TPS25200 datasheet](https://www.ti.com/lit/ds/symlink/tps25200.pdf)

**Pin corrections, 2026-10-02:** The previous TPS25200 source-map assignments were incorrect. Both U502 and U511 now use TI Rev F Table 4-1: OUT=1, ILIM=2, FAULT=3, EN=4, GND=5, IN=6, exposed pad=GND. Fresh schematic/netlist exports supersede the earlier eFuse pin tables. D501 onsemi SS14 physical numbering is also corrected to anode 1 / cathode 2, cathode toward WPT_PROTECTED. The intended topology is unchanged; verify exact SMA pad numbering and cathode-band orientation in Altium.

The rectifier, RX matching, reservoir and raw overvoltage/thermal clamp remain a separate unqualified receiver. An 18.5 V charger OVP disconnect does not clamp the RF reservoir, coil or rectifier voltage. Earlier ADS observations and the paper's coil-link efficiency do not verify assembled RF-to-DC power or component stress. Keep the RF link open until receiver no-load, weak-field, full-charge and misalignment cases have been measured with a bounded source. This circuit cannot be labeled a fully verified wireless charger.

The BQ25185 Rev B datasheet contains inconsistent input recommendations: §5.4 lists 2.7–5.5 V whereas §5.5 lists 3.6–18 V. The normal 5 V design avoids that discrepancy; operation above 5.5 V requires clarification from TI. Do not reinterpret its 25 V absolute input rating as normal operation.

## Actual LTspice protection tests, 2026-10-02

The [power simulation report](../ltspice/power/README.md) distinguishes TI transient macros from authored datasheet-bound static fixtures. Independent startup and transient fault runs are finite; a direct TPS25200 macro DC sweep produced NaNs and was rejected. With R511 = 1 MΩ, the nominal 5 V input produces about 4.72 V at CHG_IN; the clamp case is about 5.40 V and high input shuts off. Sequential and direct slew tests show overshoot: CHG_IN reaches 5.868 V for a 1 us 5-to-18 V ramp with declared minimum 1 uF capacitors. The actual D502-fed U503 input is separately observed below its 6 V normal input boundary in the tested fixtures. The static 5.55 V clamp maximum is not a universal transient ceiling. Approximate diode models, typical macros, load/capacitance assumptions and missing charger/cell models limit this evidence. The 18 V stress deck does not authorize 18 V at the assembled whole board.

PACK+ supplies charger BAT/control/divider/PMOS branches before the RUN eFuse, so that eFuse cannot protect them against arbitrary pack overvoltage. WPT_PROTECTED is reverse-blocked but pre-eFuse; the raw RF reservoir remains outside this OVP boundary. No independent precision 3 V rail OVP is present after an LDO failure. Retain the current-limited 4.75–5.25 V bench input and qualified battery-emulator interface until receiver/cell/fault limits are closed. At the low UVLO corner, BAT54C drop can also take U503 input below the VIN >= VOUT + 0.3 V accuracy condition; nominal thresholds alone do not guarantee CTRL_3V0 regulation there.

## Charger wiring

U501 is BQ25185DLHR, WSON-10 with exposed pad. Pin 10 receives CHG_IN; pin 2 connects to PACK+ through removable R501; pin 1 has its required standalone SYS capacitor and supplies no recording load. Pins 5 and exposed pad 11 go to GND. R503 = 130 kΩ selects 4.1 V regulation and the 500 mA internal input-limit code; a 4.1 V/100 mA code is unavailable. R504 = 15 kΩ sets nominal 20 mA through KISET/RISET. With KISET = 285–315 AΩ and 1% resistor tolerance, the setting-factor calculation gives 18.81–21.21 mA; bench measurement is required at this low current.

Use 2.2 µF at IN and BAT, each retaining at least 1 µF after bias/tolerance, and nominal 10 µF at SYS retaining at least 1 µF. STAT1/2 use 10 kΩ pull-ups to CTRL_3V0 and are test-only. CE has a 100 kΩ pull-up to CTRL_3V0: this avoids exposing a 5.5 V-limited CE pin to the eFuse's possible 5.55 V clamp. R506 = 10 kΩ holds TS/MR in the allowed band, while the separate cell-mounted NTC window controls CE. This fixed resistor is not cell-temperature sensing.

The charger includes input OVP, BAT-to-SYS reverse overcurrent protection, die thermal regulation/shutdown and timers. The reverse battery OCP is about 3.13 A and protects its internal SYS path; it is not applicable cell protection for the external RUN branch. Its nominal termination is 10% of the selected charge current, approximately 2 mA, different from the cell's standard 0.01C termination. [TI BQ25185 datasheet](https://www.ti.com/lit/ds/symlink/bq25185.pdf)

R505/C505 are DNP compensation footprints (2 kΩ plus 4.7 nF), for measured low-current loop instability only. They are not needed to claim initial stability and must be checked against the EVM schematic before population. [TI EVM guide](https://www.ti.com/lit/ug/sluucs1/sluucs1.pdf), [TI explanation of the optional network](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1477929/bq25185-extra-rc-circuit-at-low-charge-currents)

## Cell temperature window

RT501 is an **off-board, cell-mounted** 10 kΩ NTC, beta 3435 K, R25 and beta each ±1%. Connect REF_1V242 → NTC → CELL_TEMP → R521 10 kΩ → GND. RT501 appears in the schematic as a harness component; do not reflow it on the main PCB or duplicate it with a PCB thermistor. [Manufacturer NTC specification](https://datasheet.lcsc.com/datasheet/pdf/a8423ab09e4698fd24b51728e5334c7d.pdf?productCode=C5439722)

U506 permits charging above the cold threshold; U507 permits charging below the hot threshold. R522/R523 = 113 kΩ/100 kΩ set nominal 21.9 °C; R524/R525 = 66.5 kΩ/100 kΩ set nominal 35.945 °C. R524 is stocked 0402WGF6652TCE, LCSC C29381, 0402, ±1%; it replaces the unsourced 65.8 kΩ candidate. A first-principles beta-equation corner calculation including reference limits, ±9 mV offset, 1% divider resistance and NTC tolerances gives cold approximately 20.1–23.7 °C and hot 33.906–38.066 °C. Built-in hysteresis, sensor attachment error and thermal lag still require testing. This conservative charging window fits the 20 mA room-temperature case without relying on a nominal 0–60 °C charger NTC window. [R524 sourcing](https://www.lcsc.com/product-detail/C29381.html)

An open NTC drives CELL_TEMP low and cold permission false; a short drives it high and hot permission false. Both disable CE. A detached sensor can still look electrically valid: strain relief, insulated cell attachment and thermal-ramp qualification matter. These comparators gate **charging**, not RUN; RUN qualification is initially at 20–40 °C and must honor the cell's lower discharge allowance below 15 °C.

## Exclusive CHARGE / RUN control

D502 diode-ORs PACK+ and CHG_IN into CTRL_INPUT; U503 generates the always-on CTRL_3V0. A valid battery therefore establishes control before a WPT input arrives, while a depleted/disconnected pack can still power the charge controller from the external source.

U504 supervises PACK+. R513/R514/R515 = 1 MΩ/510 kΩ/10 MΩ produce nominal restart 3.801 V and cutoff 3.501 V. Conservative threshold corners are approximately restart 3.67–3.95 V and cutoff 3.35–3.64 V, before comparator output/bias errors. This high cutoff gives headroom for the TPS7A20 accuracy condition VIN ≥VOUT+0.3 V, including normal low-current path drops. Its dropout rating measured at 95% output cannot prove precision 3 V regulation. Usable capacity from 4.1 V to this cutoff must be measured.

U505 outputs FIELD_ABSENT. WPT_RAW is divided by 100 kΩ/10 kΩ; a low-leakage calculation bounds the 25 °C BAT54 clamp's maximum 2 µA leakage contribution to approximately 0.20 V referred to RAW. R518/R519/R520 = 100 kΩ/20 kΩ/1.5 MΩ give nominal field detection near 2.62 V rising and field release near 2.25 V falling. A high field thus removes RUN permission well below normal 5 V input. This detects receiver DC, not every weak RF field.

D503/D504 form a diode AND: RUN_PERMIT is high only with BAT_OK and FIELD_ABSENT high. R527/C518 provide delayed RUN startup; D507/R528 provide fast disable. U508 is a Schmitt buffer. U509 inverts RUN_ENABLE to NOT_RUN; R529/C519 and U510 create CHARGE_READY after RUN has stopped and its rails have discharged. A first-order timing estimate gives roughly 86 ms nominal RUN delay and 185 ms nominal charge-enable delay; with at least 3 µF effective C519 and input-leakage allowance, charge enable remains roughly >80 ms in the examined corner model. Measure actual timing rather than treating these estimates as guaranteed timers.

Q504/Q505/Q506 are a series NMOS CE sink. CE becomes low only when CHARGE_READY, TEMP_COLD_OK and TEMP_HOT_OK are all high. Charging cannot be enabled by a charge-complete status pin. While receiver DC remains present, the recording system remains OFF even after charge termination. Intermittent WPT disables charging immediately when RUN returns, and delayed restart/field hysteresis reduces chatter. Verify simultaneous supplies on an oscilloscope, including a slowly collapsing receiver source.

The B-version TLV3012 provides fail-safe inputs and LOW output during POR; substitute neither the non-B version nor an open-drain part without redesigning the startup logic. U504's reference capacitor is 4.7 nF, below the stated 10 nF stability limit including tolerance; other large capacitors connect through isolating resistors. [TI TLV3012 family datasheet](https://www.ti.com/lit/ds/symlink/tlv3012.pdf)

## RUN isolation, regulators and analog reference

Q501/Q502 are two DMP2035U PMOS devices with **common sources**, separate outer drains, and a common gate. Q501 drain is BAT_RUN; Q502 drain is SYS_PRE. R531 pulls their gate to the common source for OFF; Q503 pulls it low through R532 to turn ON when RUN_ENABLE is high. P-channel ON requires negative VGS. The opposed body diodes block either battery-to-system or system-to-battery conduction with the gate OFF; one PMOS alone does not establish two-way OFF isolation. The datasheet's maximum RDS(on) at −2.5 V is 45 mΩ per device: both contribute about 2.25 mV at 25 mA at the stated test temperature. [Diodes DMP2035U datasheet](https://www.diodes.com/datasheet/download/DMP2035U.pdf)

U511 TPS25200 supplies SYS_RAW through another removable/observable protected stage. R534 = 820 kΩ is an equipment-fault limiter, not a guaranteed cell-safe 50 mA threshold. Its supply overhead must be counted. Output rails use TPS7A2030PDBVR regulators, with active output discharge, local input capacitors and output capacitance retaining ≥1 µF. U513 generates DVDD_3V0 from RUN_ENABLE. U512 generates AVDD_3V0, enabled by DIGITAL_GOOD. [TI TPS7A20 datasheet](https://www.ti.com/lit/gpn/TPS7A20)

U515 compares a DVDD divider to the reference. R549/R550/R551 = 200 kΩ/1 MΩ/6.04 MΩ set nominal rising 1.532 V and falling 1.432 V; examined corners give rising 1.49–1.58 V and falling 1.39–1.47 V. AVDD cannot start until VDD is above 1 V, providing a defensible rising sequence for independently powered MCU analog domains. AVDD falling can lag DVDD because of filter delay and stored charge; this is qualified only if the exact STM32WBA52 datasheet's stored-energy exception applies, and total analog stored energy is <1 mJ. At 3.045 V, 100 µF stores 0.464 mJ; do not exceed 100 µF total populated AVDD capacitance without a new audit. If this exception does not cover the chosen package/pins or external ADC injection, populate shared-rail R544 only with U512/R536 DNP, or redesign sequencing.

Q507/Q508 discharge AVDD/DVDD through 100 Ω immediately on NOT_RUN. With 100 µF, an ideal first-order 3 V→0.3 V discharge takes 23 ms; transistor/logic/filter tolerances and regulator behavior must be checked against the >80 ms charge-enable delay. These discharge circuits do not prove the system is unpowered when a debugger or DAC backfeeds it.

R540/R541 = 10 kΩ/10 kΩ derive VMID_RAW; 2.2 µF filters it. Divider current is 150 µA at 3 V, Thevenin resistance 5 kΩ, time constant 11 ms and corner frequency 14.47 Hz. The AFE agent owns the buffer, its capacitive-load isolation and channel reference wiring. This 100 ms midpoint-only estimate does not qualify the complete AFE startup. Actual nominal LTspice startup takes 2.336 s for the quarter-ideal-LSB check; use the Candidate 3 s startup blank plus whole-AFE validity checks described in the AFE report.

## Battery protection: a remaining release gate

The 401020-55mAh cell's manufacturer sheet requires protection against excessive charge/discharge current, reaching 4.25 V, and discharge to 2.8 V. Its bare-cell listing does not prove an integrated PCM. A charger set to 4.1 V is normal regulation; it does not substitute for independent protection under faults. [Cell manufacturer specification](https://atta.szlcsc.com/upload/public/pdf/source/20250905/9CA17359854FCF37A94D02BC391F6AF0.pdf)

| Protection option | Advantages | Limitation / disposition |
|---|---|---|
| Documented protected pack | Protection stays physically with the cell; accidental harness shorts can be covered. | Obtain actual protection thresholds, current ratings and NTC arrangement. No verified LCSC protected pack of this exact size/rating is presently released. |
| BQ29737DSER plus opposed NMOS devices | Stocked LCSC C3681751; concrete onboard PCM circuit is provided, with explicit cell-negative isolation and current sense. | Nominal 4.25 V OVP can reach 4.27 V at 0–60 °C; 2.8 V UVP can reach 2.75 V. Guaranteed OCD/OCC tolerances also prevent simultaneously guaranteeing ≤50 mA discharge and avoiding false trips at 20 mA charge with one resistor. DNP pending manufacturer approval or revised protection. |
| ABLIC S-8211CAN variant | Nominal 4.20 V OVP is a closer ceiling fit and charge-overcurrent threshold is less restrictive. | Checked LCSC C6471591/C5904401 are out of stock; UVP tolerance still needs audit. It does not satisfy the stocked-parts constraint today. |

U514/Q509/Q510/R545–R548/C530/J504 supply exact optional BQ29737 wiring, **not a qualified battery solution**. Q509 and Q510 use common drains, source on CELLN and protected-negative side respectively. R546 = 1 Ω lies between PCM_NEG_SENSE and protected GND, so V− senses FET drops plus the resistor. With a 100 mV nominal OCD threshold, faults occur around 90–100 mA rather than multiampere MOSFET-only sensing; this still exceeds 50 mA. Increasing the resistor enough to guarantee ≤50 mA makes the worst-case 35 mV charge threshold false-trip at normal charge current. This conflict is a calculation, not an arbitrary part preference. [TI BQ297 family datasheet](https://www.ti.com/lit/ds/symlink/bq2970.pdf), [ABLIC primary S-8211C specification](https://datasheet.lcsc.com/datasheet/pdf/f7fe324c4c77f305b90491c2e8701ae2.pdf?productCode=C6671203)

Initial bring-up uses a current-limited battery emulator at J501, not the unprotected lithium cell. Connecting a real cell requires a verified protected pack or manufacturer-approved, redesigned PCM thresholds and fault-pulse allowance. J501 protected-pack mode and J504 bare-cell mode are mutually exclusive. Never ground CELLN with an oscilloscope/debugger in onboard PCM mode: that bypasses the protector.

## Power, thermal and runtime calculations

At 5 V, 20 mA charge plus typical 0.75 mA charger input overhead consumes 103.75 mW at CHG_IN. At the setting-factor upper bound plus 1 mA overhead, it becomes 111.06 mW before external control, eFuse and polarity-diode losses. The earlier 105 mW target is a nominal lower estimate; allocate **at least 120 mW at the 5 V board input** as an initial qualification target and measure it. R543/R542, the diode and extra control electronics are included in the board-input boundary.

**Receiver-load accounting update, 2026-10-09:** The two 10 kΩ logic/status pull-ups active in CHARGE, CE pull-up and temperature/reference dividers make the earlier 300 µA external-control assumption inadequate. The [ADS load fixture](../../wpt/ads/charger/recommended-load-model.md) now uses 0.8 mA nominal / 1.5 mA control sensitivity, explicitly unguaranteed. At **WPT_RAW = 5 V**, 20 mA charge + 0.75 mA charger overhead + 0.8 mA control + 143 µA eFuse + 45.45 µA field divider gives **21.738 mA / 108.69 mW**; the declared high-setting/control fixture gives **23.958 mA / 119.79 mW**. The series-drop dissipation is included through that raw-node current/voltage boundary, rather than adding it again to a 5 V charger-input power. The actual eFuse conditions, pull-up voltages, diode-OR control supply and low-current charger accuracy remain qualification work. The ≥120 mW allocation is retained as an initial target, not a guaranteed whole-board upper bound.

The [actual nominal receiver ADS study](../../wpt/ads/README.md) reaches 5.08853 V / 124.287 mW into 208.333333 Ω at 23.5 dBm, but uses ideal tuning capacitors and a resistor instead of this power path. Same-power near-open-load voltage is 11.915 V with approximately 132 mW RX winding loss. This does not qualify J502, actual charging, raw OVP or coil temperature; retain the bench/emulator configuration until those gates close.

Approximate charger heat at 5 V/20 mA and cell 3.0 V is (5−3)×0.020 ≈40 mW, plus quiescent power. The JEDEC 68.3 °C/W figure implies only a few degrees on its test layout, but does not predict a tiny board, nearby cell, wireless heating or enclosure. Charge temperature is measured at the cell, and the copper/EP thermal implementation remains mandatory. At the 5.4 V clamp, source/charger dissipation changes; use fault test conditions rather than extending the nominal estimate.

For a 15 mA measured average battery current, one hour requires ≥15 mAh usable capacity; for 25 mA, ≥25 mAh. These are 30% and 50% of the cell's minimum 50 mAh rating. Its rated capacity was measured with a different charge endpoint and cutoff, so neither 55 mAh/15 mA nor a nominal state-of-charge curve proves runtime. Confirm actual charge at 4.1 V/20 mA and discharge to the worst applicable UVLO.

Quiescent estimates must include the 150 µA VMID divider, external NTC/reference loads, logic IC maxima, five control comparators, control regulator, charger battery leakage and the main eFuse (up to roughly 0.2 mA at the published conditions). Expect control/protection overhead on the order of 0.4–0.7 mA in RUN; measure both RUN and recording-OFF standby. Standby still discharges the cell: disconnect it for storage; this is not ship mode.

## Assembly/source check, 2026-10-01

Live canonical LCSC pages showed the following stocked choices. Stock and price vary; final PCB assembly library availability and footprint audit are separate gates.

| MPN | LCSC | Observed stock | Qty-1 / first tier USD |
|---|---|---:|---:|
| BQ25185DLHR | C19725033 | 3,814 | 1.7492 |
| TPS25200DRVR | C128401 | 1,466 | 0.4425 |
| TPS7A2030PDBVR | C963429 | 5,825 | 0.2332, min 5 |
| TLV3012BIDBVR | C20345924 | 2,658 | 2.8385 |
| SN74LVC1G17DBVR | C7836 | 56,050 | 0.1695, min 5 |
| SN74LVC1G04DBVR | C7827 | 131,840 | 0.0819, min 5 |
| DMP2035U-7 | C110499 | 108,950 | 0.1307, min 5 |
| AO3400A (AOS) | C20917 | 540,135 | use final BOM quote |
| BAT54-7-F | C106920 | 88,180 | 0.0357, min 20 |
| BAT54C-7-F | C134405 | 17,840 | use final BOM quote |
| SS14 (onsemi) | C83852 | 137,385 | 0.1233, min 5 |
| MF52D103F3435L100 | C5439722 | 5,320 | 0.1127, min 5; manual harness |
| BQ29737DSER, optional DNP | C3681751 | 192 | 0.6763 |

Each code links via https://www.lcsc.com/product-detail/CODE.html, e.g. [BQ25185](https://www.lcsc.com/product-detail/C19725033.html), [TLV3012B](https://www.lcsc.com/product-detail/C20345924.html), [TPS7A20](https://www.lcsc.com/product-detail/C963429.html), [TPS25200](https://www.lcsc.com/product-detail/C128401.html). Estimated populated power/control active parts are roughly USD 18–21, dominated by the five comparators; passives, connectors, assembly fees and battery are extra. Do not claim full-board cost until the assembled BOM is quoted.

Use the sourced BOM footprint for each passive; R524 uses stocked 0402 while R503 130 kΩ and R514 510 kΩ retain sourced 0603. Dividers and ISET/VSET require 1% or better; 0.1% matched VMID resistors are preferred. Use 0805/1206 for capacitors where specified bias retention is needed. WSON exposed pads require soldered copper/thermal vias. SOT-23 gate/source/drain must be audited individually, not inferred from the symbol silhouette. Generic passives are assigned exact MPN/LCSC codes by the parent BOM standardization; blank passive codes in this subassembly JSON do not authorize substitution that violates tolerance or effective capacitance. J501–J504 are manual harness connections implemented as copper wire pads by the parent schematic generator, not SMT connectors.

## Required observability and verification

Expose test pads for PACK+, BAT_CHG, BAT_RUN, WPT_RAW, WPT_PROTECTED, CHG_IN, CHG_SYS, CTRL_3V0, REF_1V242, CELL_TEMP, BAT_OK, FIELD_ABSENT, RUN_PERMIT, RUN_ENABLE, CHARGE_READY, CE, DIGITAL_GOOD, SYS_PRE, SYS_RAW, AVDD, DVDD and VMID_RAW. R501/R502/R536/R537 are removable current-measurement/isolation links; fit shunts only after emulator testing. STAT/FAULT outputs are always-on test nodes, not direct connections to unpowered MCU pins.

Verify before connecting a cell:

1. With emulator 3.9–4.1 V and input absent, measure regulator voltage, AFE noise, BLE burst droop, average/peak current, reference settling and eFuse startup behavior.
2. Ramp emulator voltage slowly and step load; record actual cutoff/restart thresholds and ensure LDO input headroom remains sufficient.
3. Apply/ramp/remove the current-limited 5 V charge input at different battery emulation voltages. Scope RUN_ENABLE, both rails, CE and charge current; prove charge begins only after recording rails fall below 0.3 V and charging stops before RUN restart.
4. Repeat weak/intermittent source, charge-complete, cold/hot NTC, open/short NTC, cell removal and source interruption. An input collapse must not produce negative regulator outputs or a current-source artifact.
5. Scope independent analog/digital startup/shutdown and power-fault steps. Audit total analog capacitance/energy and the exact MCU sequencing/injection limits.
6. Validate low-current charge stability, precharge, termination, timer behavior and cell thermal attachment. Do not use a fixed ideal 40 mA sink as a battery model.
7. Validate real protected-pack/PCM thresholds and permitted fault pulses before bare-cell use. Measure runtime under the actual acquisition/radio schedule.
8. Disconnect external power from SWD/UART/DAC/FFC before CHARGE-mode tests; power-connected debug tools can defeat mutually exclusive operation. Do not power MCU rails through status pull-ups.
9. Keep the RF receiver link DNP until RF/DC no-load overvoltage, rectifier ratings, source collapse, matching versus load, reservoir ripple, coil/material heating and delivered DC power are qualified.

No firmware or PCB routing was created by this power subtask. The schematic definitions are concrete and reviewable; unresolved cell/RF gates are explicit rather than hidden as presumed protections.


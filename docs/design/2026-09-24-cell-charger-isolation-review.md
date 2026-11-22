# Cell, charger and exclusive-mode switch review

Recorded 2026-09-24, America/New_York. Research and candidate circuit only; BQ25185DLHR remains the user-selected baseline. No replacement cell, charge current, detector or MOSFET is fabrication-approved. No ADS deck was executed in this review.

**Update 2026-09-25:** User accepted the BQ25185 + Taisko 401020-55mah pairing as a working baseline, with provisional 20 mA room-temperature charging, 4.1 V regulation, 5 V / 21 mA receiver target and 20/23/26 dBm ADS sweep. D-023 in the handbook governs current status; earlier candidate wording below records the pre-acceptance review. Pack sourcing/protection and all power verification gates remain open. TI Table 6-1 maps 4.1 V to 130 kΩ / nominal 500 mA ILIM (not the earlier 24 kΩ, 4.2 V / 100 mA setting). Its internal battery OCP is approximately 3.13 A through BATFET and does not protect the external BAT-to-PMOS branch.

## Selection criteria

Meet one hour of usable runtime; allow cell-safe charging within the receiver's delivered DC power and the charger's timer; meet voltage/current limits including tolerances and temperature; keep the main system off throughout detectable WPT; provide cell protection and temperature sensing; use LCSC-orderable electronics and confirm actual assembly handling. The 25–35 mA system estimate is unmeasured.

## Cells to qualify

| Candidate | Evidence | Advantage | Limit / next gate |
|---|---|---|---|
| Taisko 401020-55mah, catalog C19632326 | Manufacturer PS-401020-01 Rev A: 55 mAh typical / 50 mAh minimum, nominal 20 × 10 × 4 mm cell body, 4.2 V charge / 3.0 V discharge boundary | Best compact first qualification candidate; 50 mAh minimum gives 1.43–2.0 h ideal at 35–25 mA | Actual protected-pack dimensions, stock/export and assembly not established. Temperature-dependent limits, charge-voltage tolerance and termination differ from a generic charger profile |
| Taisko 302020-100mah, catalog C19632322 | Catalog lists 100 mAh, 20 × 20 × 3 mm and built-in protection | More capacity, thinner body; 2.86–4.0 h ideal at 35–25 mA | Manufacturer charge/discharge specification not retrieved; cannot transfer 401020 specifications. Global LCSC orderability and stock unconfirmed |
| GEB201212C, distinct from PGEB201212 | GEB datasheet: 10 mAh, max 12.5 × 12.5 × 2.2 mm, 2 mA standard / 10 mA maximum charge, 100 mA continuous discharge at specified temperatures | Tiny, with a real manufacturer specification; a 5 mA setting is below the stated maximum before configuration/fault checks | Only 17–24 minutes ideal runtime; protection/NTC and LCSC source not verified. Do not select under current sourcing/runtime constraints |

Runtime estimates use nominal capacity/current only, not measured usable energy. The 55 mAh cell's **minimum** 50 mAh capacity with an illustrative 80% usable factor gives 1.14–1.60 h. This factor is not a guarantee; 3.0 V LDO dropout, temperature, aging, reduced charge voltage and actual BLE peaks must be evaluated.

For 401020-55mah, the manufacturer lists maximum charge rates of 0.2C at 0–15°C, 0.5C at 15–25°C and 1C at 25–45°C. Continuous discharge is 1C at 15–60°C but 0.2C at −2–15°C. Thus a 20 mA charge and 35 mA load are only room-temperature candidate cases; charger TS must enforce the cell-specific envelope, not merely generic 0–45°C charging. Standard capacity testing terminates CV at 0.01C, unlike BQ25185's nominal 10% of programmed current: earlier termination reduces capacity, and full nominal capacity cannot be assumed.

The cell document calls 4.2 V the upper limit without specifying allowed regulation tolerance. Obtain clarification before using a nominal 4.2 V charger whose positive tolerance exceeds it. A provisional 4.1 V setting on BQ25185/BQ25170 avoids that ambiguity at the cost of capacity. No 4.1 V usable-capacity curve was found.

The JLC C19632326 page identifies a non-SMT assembly category, not conventional tape-and-reel reflow. Do not put a pouch cell through the PCB reflow process based on a catalog assembly label. Confirm connector/lead handling and pack installation with the assembler. The 100 mAh secondary catalog showed zero stock; neither cell is a confirmed globally orderable LCSC purchase in this review.

Correction to prior PGEB assessment: recommended 0.2C is not a verified maximum, and a retailer's “1 CmA” should not have been interpreted as an established 1 mA limit. PGEB201212/BQ25185 remains **unqualified**, rather than proven electrically incompatible. The different GEB201212C suffix cannot resolve its identity.

## Charger alternatives

| Exact part / LCSC | Functional description | Pros | Cons |
|---|---|---|---|
| BQ25185DLHR / C19725033 | Linear charger with battery-tracking VINDPM and integrated SYS path; 5 mA minimum programmed current | Retains selected baseline; weak-source current reduction; WSON 2.2 × 2 mm; TS, input limits and OVP | Enabled input overhead 0.75 mA typical / 1 mA max under datasheet test conditions; six-hour charge timer; SYS must not power main system during CHARGE |
| BQ25170DSGR / C5208201 | Simpler linear charger without a separate SYS supply; 10–800 mA programmed current | 2 × 2 mm WSON; 0.45 mA typical / 0.6 mA max enabled overhead; TS and input OVP around 6.75 V typical | No equivalent battery-tracking VINDPM specified; weak-source collapse/restart needs testing; narrower usable input window |
| MCP73831T-2ACI/OT / C424093 | Basic fixed-4.2 V linear charger, 15–500 mA, SOT-23-5 | Simple assembly and small external component count | No cell thermistor input, dedicated input-OVP disconnect or weak-source DPM; requires added protection/control. Charging supply current is 0.51 mA typical / 1.5 mA max, not the 53 µA charge-complete figure |

Live LCSC pages checked 2026-09-24 showed stock for these three charger MPNs. This is not an assembly reservation. BQ25100YFPR / C527572 is a smaller 1.6 × 0.9 mm DSBGA alternative with 10–250 mA programming, NTC and DPM, but its exact 4.2 V listing was out of stock; stocked A/H variants must not substitute because their voltage settings differ.

Recommendation: keep BQ25185 for the next receiver tests; qualify the 55 mAh cell first and the 100 mAh cell if runtime/packaging requires it. BQ25170 becomes attractive if a robust approximately 5 V DC source is demonstrated and its lower overhead/simpler topology outweigh losing BQ25185's source regulation. MCP73831 adds too many external functions for the present uncertain WPT source.

## Rectifier compatibility and ADS acceptance

There is no charger datasheet statement that proves compatibility with this custom rectifier. Establish a DC operating envelope from ADS and then bench tests, and compare it against the IC/cell limits.

1. **Correct bridge reference first.** The latest screenshot grounds both the bridge's left common DC-negative node and its lower AC midpoint. That collapses the intended full bridge into a half-wave path with an input-clamping diode. For a full bridge with grounded DC-negative, make the RX coil/matching network a floating two-terminal AC source feeding the two bridge AC midpoints. Its local RF return is not directly DC ground. Alternatively use an explicitly designed single-ended rectifier. Confirm the actual netlist; no saved ADS deck was edited here.
2. **Voltage window.** Test the minimum input including ripple, not only average voltage. At a nearly full 4.2 V cell, approximately 5 V loaded is a useful design target. BQ25185's electrical table lists a typical tracking offset of 330 mV; descriptive text rounds it to 300 mV. Neither number is a guaranteed full-current headroom specification. Check UVLO, sleep, DPM and dropout together at worst case. No-load voltage and ringing must stay within each component's operating/stress limits; charger OVP disconnect does not clamp the reservoir.
3. **Power/current.** With the system isolated, a linear charger requires approximately charge current plus its enabled overhead. For BQ25185 at 5 V, use a preliminary 1 mA overhead budget: 5 mA charge needs 30 mW DC; 10 mA needs 55 mW; 20 mA needs 105 mW. Add detector/clamp/divider losses and charge-current tolerance. At an assumed 50% source-available-RF-to-DC efficiency, these require 60, 110 and 210 mW available RF (17.8, 20.4 and 23.2 dBm). These are calculated assumptions, not measured efficiency. A 10 dBm source supplies only 10 mW and cannot sustain these cases. A higher-power generator/PA may be required.
4. **Load model.** HB at 13.56 MHz: start at order 7 and compare 11/15 for convergence. For an illustrative 20 mA charge case use approximately 21 mA input load, then include current-tolerance margin. A 238 Ω resistor at 5 V is a single-point cross-check, not a charger model. Use voltage-compliant behavioral loading for startup/droop; an ideal current sink can force negative voltage. Sweep battery voltage, load, RF power, coupling and capacitor tolerance. Retune RX matching from fundamental V/I looking into the entire downstream circuit, rather than attaching a 50 Ω Term across the working rectifier.
5. **Charge completion.** BQ25185 has a nominal six-hour safety timer. 55 mAh / 5 mA = 11 h and 100 mAh / 5 mA = 20 h before CV taper, so slow charge is not automatically a complete-charge solution. VINDPM can reduce actual current below the programmed minimum but does not guarantee completion within the timer. Candidate 20 mA into 55 mAh is 2.75 h capacity/current plus taper; 25 mA into 100 mAh is 4 h plus taper, conditional on cell limits. Model precharge, termination, temperature, available power and timer explicitly; do not repeatedly reset a safety timer to claim compatibility.
6. **Stress and bench checks.** Save diode peak forward current and reverse voltage, capacitor ripple/rating, no-load/full-cell overvoltage and charger temperature. BAT15-03W's provisional 4 V rating remains a gate; do not increase TX power until the rectifier model/parts can withstand the resulting voltage. Verify delivered voltage/current and cell temperature at nominal and weak coupling, startup, termination, no battery, field loss and faults. Nominal coil simulation does not validate the assembled stack with battery metal nearby.

## Proposed PMOS isolation

```text
RX match → rectifier → reservoir / receiver OVP → charger IN
                                                charger BAT ↔ protected PACK+
protected PACK+ → PMOS source; PMOS drain → SYS_RAW → analog/digital LDOs
WPT envelope → battery-powered detector + hysteresis / holdoff → PMOS gate control
```

Connect the charger to the protected pack side **before** the system-isolation switch. BQ25185 SYS receives its specified capacitor but does not feed SYS_RAW. Drawing system current directly from the battery bypasses protections in the IC's SYS/BATFET path; use independent pack protection and system undervoltage/current protection as required.

Candidate switch: Diodes DMP2035U-7, SOT-23, LCSC C110499 (stock observed). Candidate detector: TLV3012AIDBVR, SOT-23-6, C62505 (12 shown; fragile stock). The latter is battery-powered, has a reference and push-pull output; do not assume the POR/fail-safe features of the different TLV3012B apply to it. Add divider/input protection, external hysteresis, startup inhibit, battery-valid qualification and delayed RUN release before claiming a complete autonomous circuit. Exact thresholds depend on the supported WPT detection envelope and remain open.

| Condition | Gate relative to source | PMOS | Main system |
|---|---|---|---|
| Detectable WPT, including full cell or charger fault | Gate pulled to protected PACK+, VGS ≈ 0 | OFF/open | OFF |
| WPT absent after holdoff, battery valid | Gate pulled low, VGS ≈ −VBAT | ON | RUN |
| Battery invalid or control startup | Force VGS ≈ 0 | OFF | OFF |

A provisional 100 kΩ gate-to-source pullup establishes OFF when the gate driver is high impedance (42 µA loss when gate is low at 4.2 V); it does not alone establish power-on safety. Use an active gate drive for prompt OFF, with a candidate 1 kΩ series gate resistor. Do not connect raw rectifier voltage directly to the gate. Select/verify MOSFET RDS(on) at the actual −2.5 to −4.2 V drive, not from threshold voltage. Reserve room for a second opposing MOSFET if reverse isolation is needed: a single correctly oriented PMOS blocks battery-to-system when off but its body diode permits SYS_RAW-to-battery current.

WPT detection must remain asserted after charge termination and during recoverable charger faults, so CHG/STAT is not the mode command. A reservoir-voltage threshold alone can miss a weak field or retain charge after field removal; use a dedicated RF-envelope detector or demonstrate adequate detection across the defined operating envelope. Interlock charger enable: first disable/discharge the main rails, then permit charging; on removal stop charging, wait for field absence, then enable valid RUN. Test rail discharge time and USB/SWD/GPIO back-power paths. Provide test points at WPT_RAW, PACK+, gate and SYS_RAW plus separable charger/system current links.

## Primary specifications and procurement evidence

- [TI BQ25185 Rev B](https://www.ti.com/lit/ds/symlink/bq25185.pdf): electrical characteristics pp. 6–8; safety timer §6.3.7.7; low-current ISET requirements and application circuit. [LCSC C19725033](https://www.lcsc.com/product-detail/C19725033.html).
- [TI BQ25170 Rev A](https://www.ti.com/lit/ds/symlink/bq25170.pdf), [LCSC C5208201](https://www.lcsc.com/product-detail/C5208201.html).
- [Microchip MCP73831/2 DS20001984H](https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf), [LCSC C424093](https://www.lcsc.com/product-detail/C424093.html).
- [TI BQ25100](https://www.ti.com/lit/ds/symlink/bq25100.pdf), [LCSC C527572](https://www.lcsc.com/product-detail/C527572.html).
- [Taisko 401020-55mah manufacturer specification](https://atta.szlcsc.com/upload/public/pdf/source/20250905/9CA17359854FCF37A94D02BC391F6AF0.pdf), [JLC catalog C19632326](https://jlcpcb.com/partdetail/Taisko-40102055mah/C19632326). [302020-100mah catalog lead](https://www.jlc-smt.com/lcsc/detail/C19632322.html) is secondary evidence only.
- [GEB201212C manufacturer specification](https://www.powerstream.com/lip/PGEB201212C.pdf): exact suffix matters.
- [DMP2035U manufacturer product page](https://www.diodes.com/part/view/DMP2035U), [LCSC C110499](https://www.lcsc.com/product-detail/C110499.html); final MOSFET electrical/footprint audit remains open.
- [TI TLV301x Rev C](https://www.ti.com/lit/ds/symlink/tlv3012.pdf), [LCSC C62505](https://www.lcsc.com/product-detail/C62505.html).

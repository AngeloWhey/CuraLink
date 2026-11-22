# CuraLink power-path architecture review

**2026-09-22 · Engineering recommendations, not accepted component selections or a released schematic.** The [handbook](../engineering-handbook.md) controls the accepted exclusive CHARGE/RUN policy (D-007) and current 1S/split-rail baseline (D-016). This review identifies the functional blocks and fault cases still needed for a practical implementation.

## Recommended functional path

```text
current-limited / fault-aware WPT transmitter
    ↓ magnetic coupling
RX coil + tuning → rectifier → reservoir → bounded WPT input (clamp/OVP or regulation)
                                      ├→ WPT_PRESENT detector / holdoff (always operative)
                                      └→ input-rated 1S CC/CV charger + cell NTC / charge timeout
                                                            ↓
                                                protected 1S cell / independent
                                                OV, UV, OC, short protection
                                                            ↓
                                      BAT_OK + WPT_PRESENT hardware interlock
                                                            ↓
                                      battery-to-SYS switch with controlled slew
                                                            ↓
                                      SYS_RAW → analog LDO → AFE + comparators + VMID
                                              → digital LDO → STM32WBA52 + BLE
                                      rail-valid / reset / event blanking
```

`WPT_PRESENT` must not be inferred from charger *charging* or *done* status. Sense WPT before a charger UVLO or input-protection disconnect can hide a still-present field. A DC rectifier-voltage detector needs a defined coupling/voltage envelope, hysteresis, holdoff and power source; test whether it detects weak or intermittent fields early enough. If the rule means **zero time** with the field and main system simultaneously active, a receiver-only detector cannot prove that during transmitter turn-on. Coordinate the transmitter/dock to disable RUN before energizing its coil, or specify a bounded detection/shutdown interval and discard data around transitions.

The rectifier/reservoir alone does **not** regulate `WPT_RAW` to 5 V. Specify minimum/maximum voltage at worst and best coupling, with battery empty, charging at maximum current, full/terminated battery, misalignment, and no load. Either regulate/clamp the receiver output or select a charger rated for the *measured full envelope* and a transmitter with controlled output/fault behavior. A 5 V nominal target is insufficient as a charger-input rating. Integrated wireless receiver examples include output regulation and rectifier overvoltage protection; the custom CuraLink coil solution must supply equivalent functions or prove they are unnecessary. [TI regulated receiver example](https://www.ti.com/product/BQ51013A), [Analog Devices wireless-power design guide](https://www.analog.com/en/resources/app-notes/an-138fc.html).

## Fault and transition review

| Case | Needed function / design check |
|---|---|
| Cell overcharge, overdischarge, short, or overcurrent | Choose a protected cell or add an independent 1S protector with switching FETs. Charger CC/CV regulation and BAT-to-SYS mode isolation serve different functions; neither alone establishes all four cell protections. Match protector thresholds and recovery to the selected cell. [TI battery protector overview](https://www.ti.com/product-category/battery-management-ics/battery-protectors/overview.html). |
| Cell too hot/cold, small cell charged too fast | Locate the NTC at the cell, use the charger temperature input, precharge/termination/timeout, and set current from the actual cell datasheet rather than an assumed 25 mA or 1C. Check charger heating with `P ≈ (V_IN−V_BAT)I_CHG` for a linear charger and RX-coil temperature under misalignment. [TI 1S charger example](https://www.ti.com/lit/ds/symlink/bq25170.pdf). |
| WPT begins while RUN is active | The hardware interlock drops `RUN_ENABLE`; switch off promptly, discharge/bleed `SYS_RAW` and rails as required, hold MCU reset/event blanking, and define maximum allowed overlap. Check detector behavior if `WPT_RAW` rises slowly or is clipped by OVP. |
| Charging terminates but field remains | Keep `RUN_ENABLE` false independent of charger `DONE`; test at full battery and intermittent charge/recharge cycling. |
| Field disappears or flickers | Use hysteresis and a re-enable delay; require BAT_OK, then slew SYS_RAW, establish both rails/VMID, and only then release AFE/detector/MCU operation. Avoid oscillating between modes near the detection threshold. |
| Battery depleted, missing, reversed, or hot-plugged | Define BAT_OK/UVLO and protector recovery, keyed/polarized connector and reverse-insertion strategy, no-battery charger behavior, and switch default state. A rail-power-good signal after the switch cannot alone decide whether to close the switch; that would be a startup dependency loop. |
| Short at SYS_RAW or rail | Size the cell protector and switch for fault current; consider a current-limited load switch or local rail protection. Controlled slew limits startup inrush; quick output discharge can make OFF measurable but must be rated for stored output-capacitor energy. [TI load-switch functions](https://www.ti.com/product-category/power-management/load-switches/overview.html). |
| SYS_RAW externally driven while switch open | Check PMOS body diode and backfeed from FFC fixture, SWD/UART, test equipment, or charger paths. Use reverse-current-blocking or back-to-back FETs if the complete system can drive SYS_RAW above BAT; do not assume a single PMOS provides bidirectional isolation. [TI reverse-current application note](https://www.ti.com/lit/an/slva730/slva730.pdf). |
| 1S voltage near discharge end | For each LDO require `V_BAT,min − V_switch_drop − V_interconnect_drop > V_rail + V_dropout` at worst load/temperature. Check usable battery capacity at that cutoff against one-hour runtime. The candidate TLV3202 comparator needs at least 2.7 V, TLV9064 at least 1.8 V, and STM32WBA52 1.71–3.6 V, but any lower-rail option needs a new AFE/headroom/noise budget. [TI comparator](https://www.ti.com/lit/gpn/tlv3202), [TI amplifier](https://www.ti.com/product/TLV9064), [ST MCU datasheet](https://www.st.com/resource/en/datasheet/stm32wba52ce.pdf). |
| Separate coil-board cable/connector | Carry DC WPT_RAW and its return as a rated pair; key the connector and check reversal, hot-plug, ESD, current, voltage, temperature and return-loop routing. Keep rectifier/OVP near the coil and test the full cable/connector at both voltage extremes. |

## Practical first-board provisions

Provide isolated/current-measurement links or pads for RX DC, charger input, BAT, SYS_RAW, analog rail and digital rail. Expose WPT_PRESENT, BAT_OK, charger status, rail-valid and switch-gate test points; keep them away from high-impedance AFE inputs. Allow the charge current, WPT detector threshold/holdoff and SYS discharge behavior to be changed without rerouting. Log the cell's exact part, protection/NTC arrangement, charging limits and connector polarity in the eventual schematic/BOM.

**Priority before choosing parts:** define the WPT voltage/power envelope; choose actual cell and charging limit; decide protected-cell versus on-board protector; then set switch/interlock truth table and rail-voltage/runtime budget. No architecture change or component in this review is accepted until selected explicitly. Bench-only operation is not a claim of patient-connection safety.

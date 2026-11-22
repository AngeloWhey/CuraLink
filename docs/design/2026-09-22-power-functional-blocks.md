# CuraLink power system — functional-block design

**2026-09-22 · P1 architecture handoff, not a finished schematic or part selection.** Accepted constraints are exclusive CHARGE/RUN (handbook D-007), 1S rechargeable battery with hardware battery-to-system isolation and split nominal 3.0 V rails (D-016), and the HFSS → `.s2p` → ADS WPT study (D-017). Block allocations and interfaces below are **proposed** to make the schematic and Rev A test plan concrete. The [power-path fault review](2026-09-22-power-path-architecture-review.md) lists detailed failure cases.

## Functional chain and board boundaries

```text
EXTERNAL CHARGING DOCK / TX                         OPTIONAL RX-COIL BOARD
TX supply → current-limited 13.56 MHz study driver → TX tuning/coil  )) ((  RX coil/tuning
 TX_ENABLE / fault / thermal monitor                                     ↓
                                              rectifier → reservoir → bounded DC / OVP
                                                   ├→ early WPT_PRESENT detect
                                                   └→ WPT_RAW, return
                                                              │
MAIN CURALINK BOARD                                            │
WPT_RAW → input protection/decoupling → 1S CC/CV charger ─────┘
                                        ↑ cell NTC / charge status
                                        ↓
                        protected 1S cell or on-board cell protector
                                        ↓ BAT
          BAT_OK/UVLO ──────┐       high-side system switch ← WPT_PRESENT
          FAULT/holdoff ────┴───────────────↓
                                          SYS_RAW
                              ┌────────────┴────────────┐
                         analog ~3.0 V LDO        digital ~3.0 V LDO
                          → AFE, comparators       → STM32WBA52, BLE
                          → quiet VMID ~1.5 V
                              └──── rail-valid / reset / event-blanking ────┘
```

The **external laptop/DAC stimulus fixture** is a separate bench board from this charging path. The optional RX-coil board is not yet selected. If built separately, the minimum DC connection is `WPT_RAW` plus return; an **independent `WPT_PRESENT` signal is a recommended third conductor** if an RX-side clamp, OVP switch or charger UVLO could make the main-board `WPT_RAW` disappear while the magnetic field remains. Otherwise, sense the pre-disconnect rectifier node on the same board. Determine actual connector count and isolation after the detector architecture is chosen. The 13.56 MHz value is a simulation starting case, not a finalized operating frequency.

| Block | Input → output | Required job | Open design choice / accessible node |
|---|---|---|---|
| TX source and driver | Dock supply → controlled coil excitation | Bound TX current/power, enable/disable field, handle no receiver and thermal/fault conditions | Driver, supply, interlock, TX current and temperature sensing; TX input-power measurement |
| TX/RX coils and tuning | RF drive → coupled AC | Transfer useful power over expected gap, offsets and surrounding materials | Geometry, ferrite, capacitors, loss/heat; RF ports for HFSS/ADS and bench VNA |
| RX rectifier/reservoir | Coupled AC → raw DC | Convert AC, store ripple energy, tolerate best-coupled/no-load voltage and rectifier dissipation | Topology, capacitance, snubber/clamp/regulation; `V_RECT`, `WPT_RAW` test points |
| WPT input boundary | Raw DC → charger-rated DC | Keep charger input inside its operating/absolute limits across load/alignment and input transients | Receiver regulation, OVP, current limit, connector reversal/ESD, RX-side thermal sense |
| WPT presence detector | Early RX envelope → `WPT_PRESENT` | Independently disable RUN whenever the defined field is present, including charger DONE or charger input fault | Threshold, hysteresis, dropout holdoff, rise/fall latency, always-operative supply and fail-safe behavior |
| 1S charger | Rated WPT input + cell NTC → controlled BAT charge | Precharge, CC/CV, termination/recharge, cell-temperature inhibition and charger thermal limits | Cell-specific voltage/current/NTC, fault reporting, timer, charger IC and charge-current setting |
| Cell protection | Cell terminals ↔ protected BAT | Interrupt cell overcharge, deep discharge, overcurrent and short faults independent of normal charging | Protected cell versus on-board protector; thresholds, FETs, recovery, reverse insertion and connector |
| BAT_OK and mode interlock | BAT, `WPT_PRESENT`, fault → `RUN_ENABLE` | Hardware truth table independent of MCU/AFE rails; no turn-on during weak/intermittent WPT | Battery UVLO with hysteresis, WPT holdoff, status test pads and gate-driver supply |
| BAT-to-SYS switch | BAT → `SYS_RAW` | Open in CHARGE, pass RUN peak current, limit inrush, prevent relevant reverse backfeed | PMOS versus load switch, reverse blocking, short protection, controlled slew/discharge, gate rating |
| Analog rail and VMID | SYS_RAW → VDD_ANA, VMID | Quiet AFE/detector supply and stable midrail with BLE-current isolation | LDO/headroom, PSRR/noise, bias buffer, output discharge, independent current-measurement link |
| Digital rail and startup | SYS_RAW → VDD_DIG → reset/event enable | Supply MCU/BLE bursts; hold digital activity and event counts until rails/VMID settle | LDO transient margin, local bulk/decoupling, power-good/reset timing, watchdog/brownout |

## Hardware states and sequencing

`RUN_ENABLE = BAT_OK AND (NOT WPT_PRESENT) AND (NOT POWER_FAULT)`, with an explicit **WPT-absent holdoff** before asserting RUN. `BAT_OK` must be derived upstream of the system switch; deriving it only from an LDO output would prevent a dead system from ever starting. `WPT_PRESENT` must remain operative when the MCU and AFE are off. The charger operates from valid WPT input under its own temperature/fault rules; `CHARGE_DONE` never enters the RUN-enable logic.

| Field / RX state | Battery state | Charger | SYS switch | AFE/MCU/BLE |
|---|---|---|---|---|
| WPT present, input within charger limits | Any permitted charge state | Charge/terminate as appropriate | OFF | OFF |
| WPT present, input too high/low or charger fault | Any | Inhibit/fault | OFF | OFF |
| WPT absent for required holdoff | BAT_OK | Inactive | ON after controlled start | ON after rails and VMID valid |
| WPT absent | Battery depleted/missing/faulted | Inactive | OFF | OFF |
| Presence ambiguous/intermittent | Any | Device-dependent | OFF until absence is established | OFF |

**Entering CHARGE:** a detected field deasserts `RUN_ENABLE` in hardware; the switch opens and rails decay or are actively discharged. Event data from the transition is invalid. The present field keeps the system off after charge termination. If the requirement is literally zero overlap at field onset, coordinate TX enable with a dock/receiver shutdown handshake; sensing rectified voltage only reacts after the field begins.

**Entering RUN:** after WPT absence holdoff and BAT_OK, close the switch with controlled slew; verify VDD_DIG and VDD_ANA, then VMID. Hold MCU reset or event counting until power/bias and analog filters settle. Define whether BLE is enabled before or after AFE self-check. On brownout, immediately suppress event counts and open the switch at the chosen BAT_OK threshold rather than allowing repeated partial startups.

## Sizing equations and interfaces to the selected WPT study

- Use [D-017's HFSS → `.s2p` → ADS method](2026-09-22-wpt-simulation-method.md) first with a resistor, reporting `P_DC = V_DC²/R_LOAD` and accepted-TX-RF-to-DC efficiency at a named port plane. Then replace the resistor with charger input behavior across precharge, CC, CV, termination and no-battery/no-load cases. A single S21 or coil k value cannot determine the DC charge result.
- Bound the charger interface with `V_WPT_RAW,min` under worst useful alignment/load and `V_WPT_RAW,max` at best coupling and light/no load. The approximately 5 V value is only a target. The rectifier/reservoir does not regulate it by itself. Size clamp/OVP energy and charger thermal loss from the complete envelope.
- Select the battery before choosing charge current: `I_CHG ≤` the cell's specified current under the selected temperature conditions. At an illustrative 5 V input, a *linear* charger dissipates approximately `(5 V − V_BAT) × I_CHG`; this is a calculation to be redone with the actual cell and RX voltage.
- For each LDO require `V_BAT,min − V_protector_drop − V_switch_drop − V_wiring_drop ≥ V_RAIL + V_DROPOUT` at peak load and worst temperature. Verify the 1-hour target using capacity remaining **above this cutoff**, not rated cell capacity alone. Current 25–35 mA system draw is only a prior allocation, not a measured load.
- Return the RX DC current through a defined connector ground paired with `WPT_RAW`; do not use the DAC fixture FFC, electrode REF or antenna ground as the WPT return. Probe `V_RECT`, `WPT_RAW`, BAT, `SYS_RAW`, each rail, VMID, `WPT_PRESENT`, BAT_OK and charger status during test. Evaluate back-power with the USB fixture and SWD connected while CHARGE has switched off the system.

## Minimum design gates before schematic release

1. Set the coil/driver geometry and power envelope with HFSS/ADS across alignment, separation, load and source power; show DC voltage and power **and** component peak stress/heat.
2. Choose the cell's actual part and protection arrangement; derive charge current, NTC thresholds, precharge/timeout and one-hour usable capacity from that part.
3. Decide whether the RX board is separate and where WPT presence is sensed before an OVP disconnect; define the connector and failure state if its status wire opens.
4. Draw the switch/UVLO/hysteresis/rail-valid timing with quantitative thresholds and maximum transition overlap; check PMOS body diode or load-switch reverse blocking under FFC/SWD backfeed.
5. Verify both regulators at the battery's usable minimum, BLE current peaks, analog noise and all startup/rail-collapse sequences; retain test and current-isolation points for Rev A.

No coil, rectifier, charger, protector, switch, regulator, cell or WPT voltage result has been finalized by this functional-block document.

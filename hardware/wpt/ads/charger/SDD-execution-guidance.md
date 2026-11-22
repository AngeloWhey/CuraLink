# Authored charger SDD execution status

Recorded 2026-10-09, America/New_York. **No solved DC or charger-load HB results are available.** Two actual standalone ADS DC attempts successfully parsed and flattened the SDD source, then exited 120 because the requested `b_pwad_inclusive1` Linear Simulator license had reached its user limit. The [first](runs/SDD_DC_IV/prior-simulator-1.log) and [second](runs/SDD_DC_IV/simulator.log) logs are preserved. Apps were left open and no license workaround was attempted. [Machine-readable status](execution-status-2026-10-09.json) distinguishes verified parsing from unexecuted physical checks.

[run_charger_fixture.py](run_charger_fixture.py) imports the receiver helper read-only and runs in this directory. [Prepared decks](input-decks) include the DC I–V check and seven HB31 cases: VBAT=3.2/3.7/4.0 V at 23.5 dBm / 20 mA; the 4.0 V high-setting/1.5 mA-control case; a 23 dBm case; and separate 0.40 V path-drop and 1.5 mA-control sensitivities. The candidate capacitors are TX series 59.3004634 pF / shunt 374.7395638 pF and RX series 826.2058518 pF / shunt 773.5931919 pF. The complete translated BAT54 manufacturer model is preserved.

Each HB source models 1 µF RAW reservoir plus 2.2 µF ideal charger-input capacitance. The declared nominal 0.28 V path loss is a fixed series voltage source; it is not an SS14 or TPS25200 electrical model. Separate branches represent the voltage-dependent charger law, 0.8 mA control fixture with battery-supply handoff approximation, 143 µA eFuse overhead fixture, and 110 kOhm RAW field divider. The fixed-drop source can produce a negative **virtual** CHG_IN at RAW below 0.28 V; that is outside its useful steady-state approximation and is not hardware startup behavior. Charger/control sink equations turn off there. The standalone DC check applies voltage directly to CHG_IN to test zero-voltage behavior without that virtual path artifact.

Run using ADS's bundled Python once an ordinary simulator seat is available:

```powershell
& 'C:\Program Files\Keysight\ADS2026_Update2\tools\python\python.exe' '.\run_charger_fixture.py' --mode dc
& 'C:\Program Files\Keysight\ADS2026_Update2\tools\python\python.exe' '.\run_charger_fixture.py' --mode hb
```

The DC stage checks current sign, zero-voltage draw, nonnegative and monotone input demand, weak-input reduced loading, and the expected 20 mA + 0.75 mA plateau at 5 V. Those are **planned checks**, not passing results. The HB stage uses actual DC-probe current instead of a resistor power formula, reconstructs RAW/CHG_IN waveforms and charge-current reduction, and closes RF accepted power against delivered load, winding and diode losses. Any CHG_IN waveform excursion below 0 V or above 5.5 V is flagged outside the model domain. An out-of-domain result must not qualify charging.

This static fixture omits actual protection clamping/shutdown, charger loop and timer dynamics, CV/termination/recharge, cell impedance/SOC, temperature and mode sequencing. RAW OVP is absent. Earlier completed resistor-load receiver results remain independent evidence; they cannot be relabeled as results from this charger load. Further DC/HB execution is required before the authored SDD's electrical behavior is considered tested.

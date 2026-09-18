# CuraLink 8-Channel Neural Input Fan-Out Test Fixture

## 1. Purpose

This PCB is a **simple passive test fixture** for CuraLink.

Its purpose is to allow a conventional single-channel arbitrary waveform generator (AWG) to drive all eight CuraLink neural-input channels simultaneously without placing bulky SMA connectors on the CuraLink PCB itself.

The fixture is not part of the final CuraLink system and contains no active electronics, firmware, power supplies, DACs, or MCU.

Primary use:

**AWG → SMA → attenuation → 8-way fan-out → simulated electrode source impedance → FFC cable → CuraLink CH1–CH8**

The fixture should be inexpensive, easy to assemble, and easy to modify.

---

# 2. High-Level Architecture

```text
                   CuraLink Neural Input Fixture

AWG
 │
 │ SMA coax
 ▼
SMA INPUT
 │
 ├────────────── Bypass Path ─────────────────┐
 │                                             │
 └─ ~1000:1 Attenuator ───────────────────────┤
                                               ▼
                                         TEST_SIGNAL
                                               │
                  ┌────────────────────────────┼────────────────────────────┐
                  │                            │                            │
                47 kΩ                        47 kΩ                        47 kΩ
                  │                            │                            │
                 CH1                          CH2                         ...
                                                                           │
                                                                         47 kΩ
                                                                           │
                                                                          CH8
                                                                           │
                                                                    18-pin FFC
                                                                           │
                                                                       CuraLink
```

All eight CuraLink channels receive approximately the same waveform.

---

# 3. Input Connector

Use one standard **female SMA connector**.

Preferred:

* PCB-mount SMA
* Mechanically robust
* Easy connection to existing AWG equipment
* Connector shield connected directly to fixture ground plane

Signal:

```text
SMA center → SIGNAL_IN
SMA shield → GND
```

Because the fixture operates only in the neural-signal bandwidth of approximately a few Hz to several kHz, RF-grade 50 Ω PCB transmission-line routing is not critical.

The SMA is used primarily for mechanical convenience and compatibility with lab equipment.

---

# 4. Attenuator

The AWG normally produces signals in the millivolt-to-volt range while CuraLink must eventually be tested with signals approximately in the:

**50–500 µV extracellular-spike range.**

Therefore the fixture should contain a selectable passive attenuation path.

## Nominal 1000:1 Attenuation

Initial candidate network:

```text
SIGNAL_IN
    │
 49.9 kΩ
    │
    ├──── TEST_SIGNAL
    │
 49.9 Ω
    │
   GND
```

Because the AWG has approximately 50 Ω output impedance and the eight 47 kΩ channel resistors appear as approximately:

47 kΩ / 8 ≈ 5.9 kΩ

the lower divider resistor is still dominated by the 49.9 Ω resistor:

49.9 Ω || 5.9 kΩ ≈ 49.5 Ω

The approximate divider therefore becomes:

```text
~50 Ω AWG source
+
49.9 kΩ series resistor
+
~49.5 Ω divider resistance
```

giving approximately:

**1000:1 attenuation**

within a few percent.

Example:

```text
AWG output ≈ 100 mV
→ TEST_SIGNAL ≈ 100 µV

AWG output ≈ 200 mV
→ TEST_SIGNAL ≈ 200 µV

AWG output ≈ 500 mV
→ TEST_SIGNAL ≈ 500 µV
```

Actual attenuation must be measured after assembly.

Do not rely solely on the AWG displayed voltage because some generators report amplitude differently depending on whether they are configured for a 50 Ω or high-impedance load.

Provide a test point at TEST_SIGNAL.

---

# 5. Bypass Mode

The board should also support bypassing the large attenuation network.

This will be useful during initial CuraLink bring-up when millivolt-level signals may be easier to debug.

Suggested implementation:

```text
                 ┌── J_BYPASS ───────── TEST_SIGNAL
SIGNAL_IN ───────┤
                 │
                 └── 49.9k ── ATT_NODE
                              │
                             49.9Ω
                              │
                             GND

ATT_NODE ── J_ATT ── TEST_SIGNAL
```

Only one path should normally be enabled.

### Attenuated mode

```text
J_ATT = closed
J_BYPASS = open
```

### Bypass mode

```text
J_ATT = open
J_BYPASS = closed
```

Use solder jumpers or 0 Ω resistor footprints rather than a bulky mechanical switch.

The attenuator resistor footprints should remain accessible so alternative attenuation ratios can be installed later.

---

# 6. 8-Way Fan-Out

The common TEST_SIGNAL node splits into eight branches:

```text
TEST_SIGNAL ── RCH1 ── CH1
TEST_SIGNAL ── RCH2 ── CH2
TEST_SIGNAL ── RCH3 ── CH3
TEST_SIGNAL ── RCH4 ── CH4
TEST_SIGNAL ── RCH5 ── CH5
TEST_SIGNAL ── RCH6 ── CH6
TEST_SIGNAL ── RCH7 ── CH7
TEST_SIGNAL ── RCH8 ── CH8
```

Initial value:

**RCH1–RCH8 = 47 kΩ**

These resistors provide a first-order approximation of the source impedance of an intracortical recording electrode.

They are not intended to be a complete electrochemical electrode model.

The CuraLink AFE input impedance must be much greater than 47 kΩ so that these resistors do not significantly attenuate the input signal.

---

# 7. Configurable Electrode Resistance

Use normal resistor footprints rather than permanently fixing the source resistance.

Recommended footprint:

* 0603 preferred
* 0402 acceptable if board size requires it

Possible characterization values:

```text
0 Ω / 1 kΩ     debugging
10 kΩ          intermediate test
47 kΩ          nominal electrode approximation
100 kΩ         high-impedance electrode test
```

Default intended population:

**47 kΩ**

The exact nominal electrode model will be revisited after CuraLink's AFE topology and input impedance are finalized.

---

# 8. CuraLink FFC Interface

Use an approximately **18-pin, 0.5 mm-pitch FFC/FPC connector**.

Final connector part number must match the connector selected for CuraLink.

Provisional pinout:

```text
Pin  1   GND
Pin  2   CH1

Pin  3   GND
Pin  4   CH2

Pin  5   GND
Pin  6   CH3

Pin  7   GND
Pin  8   CH4

Pin  9   GND
Pin 10   CH5

Pin 11   GND
Pin 12   CH6

Pin 13   GND
Pin 14   CH7

Pin 15   GND
Pin 16   CH8

Pin 17   REF
Pin 18   GND
```

The interleaved ground conductors reduce coupling between the low-amplitude analog channels.

The exact FFC connector contact orientation must be checked carefully before PCB fabrication.

Clearly mark:

* Pin 1
* Cable orientation
* Top/bottom contact orientation

on both the fixture and CuraLink PCB.

---

# 9. Reference Connection

The neural reference architecture has not yet been finalized.

Therefore REF must remain configurable.

Provide:

```text
REF ── R_REF ── GND
```

with:

**R_REF = 0 Ω default candidate**

but allow it to be removed.

Also provide a REF test pad so an independent reference voltage or signal can be injected if required during later AFE development.

Do not permanently short REF to GND in copper.

---

# 10. Test Points

Provide probe-friendly test pads for at minimum:

```text
TP1   SIGNAL_IN
TP2   TEST_SIGNAL
TP3   CH1
TP4   CH2
TP5   CH3
TP6   CH4
TP7   CH5
TP8   CH6
TP9   CH7
TP10  CH8
TP11  REF
TP12  GND
```

TEST_SIGNAL is particularly important because microvolt-level attenuation should be verified experimentally.

Pads should be accessible with an oscilloscope probe or DMM.

---

# 11. PCB Stackup

A basic inexpensive:

**2-layer FR-4 PCB**

is sufficient.

Suggested arrangement:

### Top Layer

* SMA signal
* attenuation network
* eight source resistors
* FFC connector
* signal routing

### Bottom Layer

Primarily solid ground plane.

Avoid unnecessary splits in the ground plane.

Keep the attenuation network and TEST_SIGNAL routing away from noisy external circuitry.

---

# 12. Layout Priorities

Approximate layout flow:

```text
[SMA]
   │
[ATTENUATOR]
   │
[TEST_SIGNAL]
   │
┌──┼──┬──┬──┬──┬──┬──┬──┐
R1 R2 R3 R4 R5 R6 R7 R8
│  │  │  │  │  │  │  │
──────── [FFC] ────────
```

Recommendations:

1. Place SMA near a board edge.
2. Place attenuation resistors immediately after SMA.
3. Keep TEST_SIGNAL reasonably short.
4. Place the eight 47 kΩ resistors symmetrically where practical.
5. Route channel outputs directly toward the FFC.
6. Keep ground plane continuous.
7. Place ground vias around the SMA shield.
8. Keep TEST_SIGNAL and channel routes away from board edges where practical.
9. Keep the FFC connector close to the fan-out network.
10. Use a short FFC cable during measurements.

Board size is not critical because this is laboratory equipment rather than the implant-sized CuraLink PCB.

---

# 13. Initial BOM

| Ref         | Component                         |       Initial Value |
| ----------- | --------------------------------- | ------------------: |
| J1          | Female PCB SMA                    |                   — |
| J2          | 18-pin 0.5 mm FFC/FPC             |                 TBD |
| RATT_TOP    | Attenuator series resistor        |             49.9 kΩ |
| RATT_BOTTOM | Attenuator shunt resistor         |              49.9 Ω |
| RCH1        | CH1 electrode impedance           |               47 kΩ |
| RCH2        | CH2 electrode impedance           |               47 kΩ |
| RCH3        | CH3 electrode impedance           |               47 kΩ |
| RCH4        | CH4 electrode impedance           |               47 kΩ |
| RCH5        | CH5 electrode impedance           |               47 kΩ |
| RCH6        | CH6 electrode impedance           |               47 kΩ |
| RCH7        | CH7 electrode impedance           |               47 kΩ |
| RCH8        | CH8 electrode impedance           |               47 kΩ |
| R_REF       | Configurable reference connection |           0 Ω / DNP |
| J_ATT       | Attenuation selection             | solder jumper / 0 Ω |
| J_BYPASS    | Bypass selection                  | solder jumper / 0 Ω |

Use 1% resistors minimum.

For the attenuation divider, 0.1% parts may be useful but are not mandatory because the actual attenuation will be measured.

---

# 14. Intended Test Modes

## Mode A — Initial Bring-Up

```text
AWG
→ bypass attenuator
→ small mV-level signal
→ all 8 CuraLink channels
```

Purpose:

* Verify channel connectivity
* Verify AFE polarity
* Verify gross gain
* Verify comparator operation

---

## Mode B — Realistic Neural Amplitude

```text
AWG
→ ~1000:1 attenuator
→ 50–500 µV waveform
→ 47 kΩ/channel
→ CuraLink
```

Purpose:

* Neural spike detection
* Threshold testing
* Minimum detectable amplitude
* Channel matching
* Noise testing

---

## Mode C — Frequency Sweep

```text
AWG sine sweep
→ fixture
→ CuraLink
```

Measure AFE response and verify approximately:

**300 Hz–6 kHz spike-detection passband**

once the final filter specification is locked.

---

## Mode D — Arbitrary Neural Waveform

Load recorded or synthetic extracellular spike waveforms into the AWG.

```text
neural waveform file
→ AWG arbitrary waveform mode
→ fixture
→ all 8 channels
→ CuraLink
```

This provides a simple way to test realistic action-potential morphology without building an 8-channel DAC system.

All eight channels receive the same neural waveform in this test configuration.

---

# 15. Limitations

This fixture does NOT emulate:

* Eight independent neurons
* Independent channel timing
* Full electrode electrochemical impedance
* Electrode DC half-cell potentials
* Independent channel noise
* Biological common-mode signals
* Crosstalk originating inside tissue
* Stimulation artifacts

It is intentionally a simple first-stage validation fixture.

A future neural-signal emulator could provide independently programmable DAC outputs if needed, but this is not required for CuraLink Rev A.

---

# 16. Important Open Items

Before fabrication, revisit:

1. Final CuraLink FFC connector part number.
2. FFC cable contact orientation.
3. Final FFC pinout.
4. CuraLink AFE input impedance.
5. Final neural reference architecture.
6. Required electrode source resistance.
7. Actual AWG output impedance and amplitude conventions.
8. Exact attenuator ratio.
9. Whether additional attenuation settings are useful.
10. Whether a simple RC electrode model should replace the 47 kΩ-only model.

---

# 17. Design Status

**Status: Preliminary test-fixture architecture — not yet fabrication-locked.**

Current intended architecture:

**1× SMA input
→ selectable bypass / ~1000:1 attenuation
→ common test signal
→ 8 × approximately 47 kΩ source resistances
→ CH1–CH8
→ 18-pin FFC cable
→ CuraLink**

This fixture exists solely to make CuraLink analog bring-up fast, inexpensive, repeatable, and compatible with standard laboratory AWG equipment.



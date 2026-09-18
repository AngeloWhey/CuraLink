# CuraLink Neural Input Signal Specification

## 1. Purpose

This document defines the electrical input signal that the CuraLink analog front end (AFE) is expected to receive.

CuraLink is intended to emulate an **intracortical extracellular neural-recording system**, broadly similar in input conditions to systems such as Neuralink and other invasive cortical recording platforms.

The purpose of this specification is to establish the input conditions required for:

* AFE gain design
* Filter design
* Noise budgeting
* Input impedance requirements
* Comparator threshold design
* Dynamic-range/headroom analysis
* Bench testing
* Neural waveform generation
* Future AFE component selection

This specification describes the **electrical signal presented by an intracortical electrode**, not an already-digitized or preprocessed spike train.

---

# 2. Recording Modality

CuraLink models:

**Intracortical extracellular recording**

The conceptual physical system is:

```text
Neuron activity
    ↓
Brain extracellular electric field
    ↓
Intracortical microelectrode
    ↓
CuraLink analog input
```

The electrode measures extracellular voltage relative to a reference electrode.

CuraLink does NOT model:

* EEG scalp electrodes
* ECoG surface electrodes
* Intracellular recordings
* Preprocessed spike-count data
* Digital neural data

---

# 3. Number of Inputs

CuraLink contains:

**8 neural recording channels**

plus a shared neural reference.

Conceptually:

```text
E1  → CH1
E2  → CH2
E3  → CH3
E4  → CH4
E5  → CH5
E6  → CH6
E7  → CH7
E8  → CH8

REF → neural reference
```

For the benchtop prototype, physical electrodes are replaced by a waveform generator and passive neural-input test fixture.

---

# 4. What Exists at the Electrode Input

The voltage seen by an intracortical electrode is not simply an isolated neural spike.

Conceptually:

```text
Velectrode(t)
=
electrode DC offset
+
local field potential
+
extracellular action potentials
+
biological background activity
+
electrical noise
+
artifacts
```

Or:

```text
V_IN(t)
=
V_OFFSET
+
V_LFP(t)
+
V_AP(t)
+
V_NOISE(t)
+
V_ARTIFACT(t)
```

Each component occupies a different amplitude and frequency range.

The AFE must therefore extract small, fast action potentials while tolerating much larger slow components.

---

# 5. Extracellular Action Potentials

The primary signal CuraLink is intended to detect is the **extracellular action potential**, also referred to here as a neural spike.

An extracellular action potential is generally a short biphasic or multiphasic waveform.

It should NOT be modeled as a square digital pulse.

Example conceptual waveform:

```text
                 positive phase
                      /\
                     /  \
--------------------/    \----------------
              \____/
            negative phase

             approximately 1 ms
```

Exact polarity depends on:

* Electrode location
* Neuron geometry
* Distance from neuron
* Reference configuration
* Tissue/electrode geometry

CuraLink therefore cannot assume that all spikes have the same polarity.

---

# 6. Neural Spike Amplitude

Published intracortical neural recordings commonly produce extracellular action potentials in the tens-to-hundreds-of-microvolts range.

CuraLink will use the following design envelope.

## Nominal spike

**200 µVpp**

This should be treated as the primary representative signal during AFE design.

## Normal expected range

**100–300 µVpp**

This represents the central operating region CuraLink should handle reliably.

## Required characterization range

**50–500 µVpp**

CuraLink should be characterized throughout this range.

## Weak-signal characterization

**20 µVpp**

20 µVpp is a stretch characterization point.

Correct detection at this level is not initially a hard project requirement.

## Large spike / headroom test

**1 mVpp**

The AFE should be tested with signals up to approximately 1 mVpp to determine headroom and saturation behavior.

---

# 7. Spike-Amplitude Requirements Summary

| Condition           | Input Amplitude |
| ------------------- | --------------: |
| Stretch weak spike  |         20 µVpp |
| Required weak spike |         50 µVpp |
| Moderate spike      |        100 µVpp |
| Nominal spike       |    **200 µVpp** |
| Strong normal spike |        300 µVpp |
| Strong spike        |        500 µVpp |
| Headroom test       |          1 mVpp |

The AFE should be optimized primarily around:

**100–300 µVpp**

while remaining useful over:

**50–500 µVpp**

---

# 8. Spike Duration

Extracellular action potentials are short transient events.

Initial design range:

**approximately 0.5–2 ms**

Nominal synthetic test spike:

**approximately 1 ms**

This matters because the filters must preserve sufficient spike peak amplitude for reliable comparator detection.

---

# 9. Spike Frequency Content

The useful action-potential spectrum is primarily above the LFP band.

CuraLink's initial spike-detection target is:

**approximately 300 Hz–6 kHz**

This range is consistent with demonstrated intracortical recording systems and spike-processing paths.

Initial AFE filter target:

```text
High-pass corner: approximately 300 Hz

Low-pass corner: approximately 6 kHz
```

Possible characterization/tuning values:

```text
HPF:
250 Hz
300 Hz
500 Hz

LPF:
5 kHz
6 kHz
7.5 kHz
```

The final filter frequencies should be selected through simulation using realistic extracellular spike waveforms.

---

# 10. Local Field Potential — LFP

LFP means:

**Local Field Potential**

LFP represents relatively slow electrical activity produced by the combined activity of many nearby neurons.

It is generally much slower than an extracellular action potential.

Approximate design envelope:

```text
Frequency:
~0.1–300 Hz

Amplitude:
tens of µV through several mV
```

A reasonable characterization range is:

**~50 µV to ~5 mV**

primarily below:

**300 Hz**

LFP is not the primary signal CuraLink intends to transmit.

The spike-detection path should strongly suppress LFP content before the comparator.

Conceptually:

```text
RAW SIGNAL

slow LFP:
~~~~~~~      ~~~~~~~~~

spikes:
     \_/\
                  \_/\

combined:
~~~~~\_/~~~~~~~\_/~~~~~~
```

After AP filtering:

```text
------\_/----------\_/---------
```

---

# 11. Electrode DC Offset

Real electrode-electrolyte interfaces can produce DC offsets much larger than neural action potentials.

CuraLink should assume that DC or extremely-low-frequency differential offsets may reach approximately:

**±100 mV**

as a design/test target.

This does NOT mean the AFE should amplify ±100 mV by its full neural gain.

The AFE must reject DC / very-low-frequency content before large amplification occurs.

For example:

```text
50 mV offset × 1000 gain = 50 V
```

which is impossible in a low-voltage circuit.

Therefore:

**DC rejection is a mandatory AFE function.**

---

# 12. Electrode Impedance

Neuralink's published thread electrodes measured approximately:

```text
~37 kΩ @ 1 kHz for PEDOT:PSS electrodes

~56 kΩ @ 1 kHz for IrOx electrodes
```

CuraLink will therefore use:

**47 kΩ @ 1 kHz nominal**

as its first-order electrode source-impedance approximation.

Design/test range:

```text
Nominal:
47 kΩ

Normal range:
30–70 kΩ

Extended characterization:
20–100 kΩ
```

The actual electrode impedance is frequency dependent and electrochemical rather than purely resistive.

A 47 kΩ resistor is only a simplified first-order emulator.

A more accurate RC or constant-phase-element electrode model may be developed later.

---

# 13. CuraLink AFE Input Impedance

The AFE must not substantially load the electrode.

Therefore:

```text
Z_AFE >> Z_ELECTRODE
```

With approximately:

```text
Z_ELECTRODE ≈ 47 kΩ
```

the AFE should target input impedance of at least:

**≥10 MΩ over the relevant signal band**

with substantially higher input impedance preferred where practical.

Input impedance must eventually be calculated using the actual AFE topology, including:

* Bias resistors
* AC-coupling components
* Amplifier input impedance
* Protection networks
* Filter components

---

# 14. Noise

The neural signal is extremely small.

Relevant demonstrated neural AFEs have input-referred noise on the order of several microvolts RMS.

Examples include approximately:

```text
Neuralink published AFE:
~5.9 µV RMS input-referred noise

Xilin Liu in-vivo BMI AFE:
~4.57 µV RMS input-referred noise
```

CuraLink initial design goal:

**≤5 µV RMS input-referred electronics noise**

over the useful action-potential band.

This is a design goal rather than an already guaranteed requirement.

Noise should be calculated and later measured.

Importantly:

Increasing amplifier gain does NOT improve the SNR of noise already present at the input.

For example:

```text
signal × 1000

and

input noise × 1000
```

are amplified together.

Therefore low-noise first-stage design is critical.

---

# 15. Biological / Background Noise

The input should eventually be tested with background activity in addition to electronics noise.

The test waveform should eventually include:

```text
Extracellular AP
+
LFP
+
band-limited noise
+
baseline variation
```

Example:

```text
V_TEST(t)
=
V_AP(t)
+
V_LFP(t)
+
n(t)
```

This provides a more realistic test than applying isolated perfect pulses.

---

# 16. Spike Polarity

CuraLink should NOT assume that all extracellular spikes have one polarity.

The filtered waveform can contain:

* primarily negative spikes
* primarily positive spikes
* biphasic spikes
* multiphasic spikes

Therefore the spike detector should eventually detect excursions on both sides of the signal baseline.

Conceptually:

```text
          +VTH
-----------+----------------

baseline
----------------------------

-----------+----------------
          -VTH
```

Candidate detection approach:

```text
AFE
 │
 ├─ positive threshold comparator
 │
 └─ negative threshold comparator
          │
          ▼
       EVENT
```

Exact comparator topology remains an AFE design decision.

---

# 17. Initial Gain Implications

The input specification suggests that total AP-path gain will likely fall near:

**50–60 dB**

but the final value has NOT yet been locked.

For reference:

```text
60 dB ≈ 1000 V/V
```

At 1000 V/V:

```text
20 µVpp  → 20 mVpp
50 µVpp  → 50 mVpp
100 µVpp → 100 mVpp
200 µVpp → 200 mVpp
500 µVpp → 500 mVpp
1 mVpp   → 1 Vpp
```

This is a useful range for comparator-level processing.

Neuralink's published AFE provided programmable gain approximately:

**42.9–59.4 dB**

which supports using roughly 50–60 dB as a realistic design region.

The CuraLink gain should probably be divided between multiple stages rather than applying ~60 dB in a single amplifier.

---

# 18. Expected AFE Architecture

The input requirements suggest the following general architecture:

```text
Intracortical electrode
        │
        │ ~47 kΩ nominal source impedance
        ▼
High-input-impedance interface
        │
        ▼
DC / very-low-frequency rejection
        │
        ▼
Low-noise first gain stage
        │
        ├──── optional broadband/debug node
        │
        ▼
AP high-pass filtering
~300 Hz
        │
        ▼
Additional gain
        │
        ▼
AP low-pass filtering
~6 kHz
        │
        ▼
Positive / negative threshold detection
        │
        ▼
EVENT[n]
```

The exact stage order, gain distribution, and filter topology remain to be designed.

---

# 19. Nominal CuraLink Test Input

The standard CuraLink neural input test should use:

```text
Signal:
realistic biphasic extracellular action potential

Amplitude:
200 µVpp nominal

Duration:
approximately 1 ms

Source impedance:
47 kΩ

Useful frequency content:
approximately 300 Hz–6 kHz
```

This should become the default AFE simulation waveform.

---

# 20. Characterization Inputs

The following signals should eventually be tested.

## Spike Amplitude Sweep

```text
20 µVpp
50 µVpp
100 µVpp
200 µVpp
300 µVpp
500 µVpp
1 mVpp
```

---

## Electrode Impedance Sweep

```text
20 kΩ
30 kΩ
47 kΩ
70 kΩ
100 kΩ
```

---

## LFP Rejection

Example low-frequency inputs:

```text
100 µV
500 µV
1 mV
3 mV
5 mV
```

at representative frequencies such as:

```text
1 Hz
10 Hz
50 Hz
100 Hz
200 Hz
```

---

## DC Offset Test

Eventually characterize operation around:

```text
0 mV
±10 mV
±25 mV
±50 mV
±100 mV
```

provided the final test setup can safely generate these offsets.

---

## Frequency Response

Characterize AFE response over a frequency range wider than the intended passband.

Example:

```text
10 Hz → 20 kHz
```

The expected spike-path response should ultimately center around approximately:

**300 Hz–6 kHz**

---

# 21. Bench-Test Interface

The physical electrode is replaced during development by:

```text
AWG
 ↓
SMA cable
 ↓
CuraLink passive neural-input fixture
 ↓
attenuator
 ↓
approximately 47 kΩ source resistance per channel
 ↓
FFC cable
 ↓
CuraLink CH1–CH8
```

The fixture can distribute the same AWG waveform to all eight CuraLink channels simultaneously.

All eight channels therefore receive the same signal during basic multichannel analog testing.

Independent eight-channel neural waveform generation is considered a future stretch feature and is not required for CuraLink Rev A.

---

# 22. Relationship to Neuralink

CuraLink is not intended to reproduce Neuralink hardware exactly.

Instead, Neuralink provides a useful reference for realistic intracortical electrical conditions and engineering requirements.

Relevant published Neuralink values include approximately:

```text
Electrode impedance:
~37 kΩ or ~56 kΩ @ 1 kHz depending on coating

AFE gain:
42.9–59.4 dB

AFE bandwidth:
3 Hz–27 kHz

AFE input-referred noise:
5.9 µV RMS

AFE differential input range:
7.2 mVpp
```

Neuralink preserved broadband neural information and digitized it.

CuraLink deliberately differs by performing analog spike detection before the MCU.

Therefore CuraLink can use a narrower spike-specific path of approximately:

**300 Hz–6 kHz**

instead of preserving the entire Neuralink broadband recording bandwidth.

---

# 23. Primary Input Specification

The current working CuraLink neural input specification is:

| Parameter                   |                CuraLink Value |
| --------------------------- | ----------------------------: |
| Recording modality          |   Intracortical extracellular |
| Neural channels             |                             8 |
| Reference                   |       Shared neural reference |
| Nominal spike               |                  **200 µVpp** |
| Normal spike range          |              **100–300 µVpp** |
| Required characterization   |               **50–500 µVpp** |
| Stretch weak signal         |                   **20 µVpp** |
| Large-signal test           |                    **1 mVpp** |
| Nominal spike duration      |                     **~1 ms** |
| Spike-duration range        |                 **~0.5–2 ms** |
| Nominal AP band             |             **~300 Hz–6 kHz** |
| Nominal electrode impedance |             **47 kΩ @ 1 kHz** |
| Normal electrode range      |                  **30–70 kΩ** |
| Extended electrode range    |                 **20–100 kΩ** |
| LFP amplitude               |               **~50 µV–5 mV** |
| LFP frequency               |               **~0.1–300 Hz** |
| DC-offset test target       |             **up to ±100 mV** |
| AFE input noise goal        |    **≤5 µV RMS** over AP band |
| Spike polarity              |         Positive and negative |
| AFE input impedance target  | **≥10 MΩ**, preferably higher |
| Expected total AP-path gain |            **~50–60 dB**, TBD |

---

# 24. Design Philosophy

The AFE should NOT be designed around one exact spike amplitude.

Instead, it must operate across a defined signal envelope.

The core design region is:

**100–300 µVpp**

with successful characterization extending approximately:

**50–500 µVpp**

The system does not need to linearly process arbitrarily large signals.

Signals outside the normal AP range may saturate the spike-detection path, provided:

* the circuitry is not damaged,
* recovery is reasonable,
* adjacent channels are not corrupted,
* normal operation resumes afterward.

---

# 25. Status

**Status: CuraLink Neural Input Specification v1 — suitable for initial AFE design.**

The next engineering task is to use this specification to create the CuraLink AFE signal/noise/headroom budget.

That analysis should determine:

1. Supply voltage
2. Analog common-mode/reference voltage
3. Stage 1 topology
4. Stage 1 gain
5. Stage 1 noise contribution
6. DC-rejection topology
7. AP high-pass topology
8. Stage 2 gain
9. AP low-pass topology
10. Comparator input amplitude
11. Positive/negative threshold levels
12. Hysteresis
13. Saturation/headroom
14. Recovery from large artifacts
15. Total input-referred noise
16. Total power per channel

Do not select final AFE ICs until this node-by-node budget has been completed.



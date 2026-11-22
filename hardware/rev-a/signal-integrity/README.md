# CuraLink signal integrity and crosstalk review

**2026-10-02, America/New_York. Candidate implementation; simulation and CAD evidence, not hardware qualification.**

The user requested a board review and subsequently authorized creating the PCB. No CuraLink layout was present in either project folder at the initial search. The new [editable mainboard](../curalink-rev-a.kicad_pcb) implements a provisional placement of the existing schematic; its current routing and native DRC status are recorded in the [PCB review](../pcb/README.md). This review also identified circuit-level coupling that a layout cannot remove.

## Functional objectives and review criteria

Preserve eight 100–300 µVpp nominal channels, including the 200 µVpp reference case, over 300 Hz–7 kHz; maintain gain/headroom, the existing ≤6 µVrms electronics-noise objective and the unchanged ≥10 MΩ input requirement. Keep CHARGE and RUN exclusive, make first-board faults observable, and retain exact LCSC component suffixes and manufacturer pin maps.

For comparing crosstalk cases, this review proposes **≤1 µVpp source-equivalent victim for a single 1 mVpp sine aggressor, or −60 dB**. This is **not an accepted requirement** or a total eight-channel budget. A 1 µVpp sine is 0.354 µVrms, about one tenth of the calculated 3.44 µVrms electronics noise. Multiple coherent aggressors, spike templates, clipping artifacts and shared-reference disturbances need separate checks.

## Findings that affect the design

| Priority | Verified finding / declared sensitivity | Consequence and action |
|---|---|---|
| High | Actual nominal LTspice CH1-only excitation gives quiet-channel crosstalk **−52.22 dB at 300 Hz**, equivalent **0.490 µVpp for 200 µVpp** or **2.449 µVpp for 1 mVpp**. | Shared VMID impedance and amplifier feedback-return currents create coupling before PCB parasitics. It fails the proposed −60 dB criterion. Review the bias architecture and coherent multi-channel cases; do not present a clean layout as a cure. |
| High | An **assumed 0.01 pF** path from an amplified output to a quiet early input gives **17.25 µVpp total equivalent for 1 mVpp**, peaking near 6.1 kHz. | Keep outputs, ADC tracks, RF, clocks and charging control away from CHx_PLUS/REF_PLUS. This is a sensitivity study, not a capacitance extracted from the PCB and not a geometry-to-spacing rule. |
| High | The existing ≥10 MΩ input target remains unmet, approximately **0.826 MΩ at 7 kHz** in the declared 20 pF FFC fixture. | Physical board creation does not qualify input loading or implicitly relax the requirement. Resolve it before fabrication. |
| High | ST's MLPF reference identifies **L3 ground** and a particular L1/L2/core arrangement. | A generic L2 microstrip calculation does not qualify that RF filter implementation. Reserve the RF routing until the actual local copper and stackup are reviewed. |
| Medium | Original-equation family models do not include coupling between amplifier sections inside the quad package. | The nine quad packages require real device/board crosstalk measurement. Independent model sections cannot bound this path. |
| Medium | At 1 kHz, modeled VMID impedance is **23.8 Ω** with nominal 4.7 µF and **30.6 Ω** with an assumed 2 µF effective capacitance. | A 1 µA injected midpoint current produces about 20.5/26.3 µV at a quiet ADC output in the stated fixture. Retain local bypass and avoid common narrow bias returns. |
| Medium | A declared 1 mV AVDD ripple gives about **0.682 ideal ADC LSB** after including the varying ADC supply reference. | Separate LDOs still share source/ground; qualify conducted supply noise, ADC sampling and BLE bursts. This is model evidence, not a measured PSRR guarantee. |
| Medium | Calculated 1 GΩ contamination leakage to GND shifts a 1.5 V node with 22 MΩ bias by **−32.29 mV**, or about **−355 mV** at a gain-11 preamp. | Flux residue, humidity and leakage can consume headroom despite later DC rejection. Keep sensitive nodes compact and inspect/clean them; the leakage value is an assumed case. |

## Bias mitigation options

The objective is a low-impedance midpoint over the signal band without unstable capacitive loading, excessive quiescent power or new shared-return coupling. Do not change R1149 solely to make one AC trace improve.

| Option | Description | Pros | Cons |
|---|---|---|---|
| Retain 47 Ω / 4.7 µF and qualify the current circuit | Preserve the tested isolated capacitive-load arrangement and measure full-channel interference. | No untested circuit change; existing operating-point and recovery evidence remains applicable. | Fails the proposed single-aggressor −60 dB criterion; coherent channels and PCB paths may worsen it. |
| Reduce isolation resistance / revise midpoint bypass | Lower the effective shared impedance with a revised compensation/load arrangement. | Potentially small area and BOM change. | Requires manufacturer-model loop stability, capacitive-load and startup/offset/PVT tests; larger capacitance changes effective value and recovery. |
| Separate quiet input/REF bias from amplified-stage returns | Use separately qualified buffers/returns for the low-level input/reference and late-stage feedback currents. | Addresses the current-sharing mechanism directly and improves observability. | More routing/components/current; buffer offset, stability and sequencing must be established. |

**Recommendation:** treat separate quiet bias/late-stage return handling as the next design evaluation. Retain the canonical circuit in this board candidate until that change has passed stability, power, recovery and aggregate-crosstalk checks. Neither the proposed criterion nor a replacement bias circuit is accepted by this review.

## Sensitive physical regions

[sensitive-regions.csv](sensitive-regions.csv) lists exact references/nets, placement/routing intent and verification categories. Its original geometry-unavailable labels record the pre-layout review; the [PCB review](../pcb/README.md) and current CAD checks supersede that absence for the new candidate. The key separation is connector/protection/preamp → difference/high-pass → LP1 → LP2 → ADC/MCU, with charger/control below and the antenna at a board corner.

The shared REF input is especially sensitive because interference there reaches every channel. REF_PRE and VMID are buffered nodes, but their distributed impedance, rail returns and feedback currents still require assessment. Use continuous reference planes rather than cutting ground under crossing signals. The hardware mode switch interrupts conducted system power during supported charging; it does not eliminate physical 13.56 MHz field coupling.

## Evidence and limits

- [AFE LTspice crosstalk review](afe/AFE-crosstalk-review.md): four completed runs, finite data, source/model/deck hashes, frequency-specific and incremental/total definitions, two plots.
- [Power/ground coupling review](power-review.md): nominal ripple/current injection and practical return-path constraints.
- [MCU/RF review](mcu-rf-review.md): ADC, clock, RF, antenna and acquisition constraints with primary references.
- [Layout sensitivity calculations](layout-sensitivities.json): assumed leakage, feedback capacitance and shared-ground examples. No extracted copper parasitics.
- [AFE footprint audit](afe/package-audit/README.md), [MCU/RF footprint audit](mcu-rf/footprint-review.md), [power footprint audit](power/footprint-audit.md): source drawings and native geometry checks.

PCB DRC checks geometrical rules and connectivity. It does not prove analog crosstalk, input impedance, RF efficiency, eight-channel detection, OVP under every fault, cell protection or runtime. Final routing, parasitic/PVT checks and assembled-board tests remain separate release gates.

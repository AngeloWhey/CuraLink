# CuraLink — system requirements v0.1

Date: 2026-09-18. Status: initial engineering draft for review; no components selected or performance demonstrated. Source: [user project brief](CuraLink-project-brief.md).

## Purpose and scope

Build an eight-channel, commercial-off-the-shelf neural-like signal acquisition prototype demonstrating analog spike detection, STM32 event processing, inductive power, and ultrasonic backscatter. Benchtop use only; no human or animal implantation. Target approximately 25–30 mm board dimensions, with electrical success, assembly reliability, and debug access taking priority. The coil, piezo, connectors, and board thickness must be included in a later mechanical envelope definition.

## Required behavior

| ID | Requirement | Verification |
|---|---|---|
| SYS-01 | Accept eight independent analog inputs from a neural waveform emulator, with a defined reference and source impedance. | Inject distinguishable signals into all channels; measure channel identity and crosstalk. |
| AFE-01 | Amplify and band-limit each input; detect selected-polarity spikes using amplitude threshold and hysteresis. | Sweep amplitude, frequency, noise, and baseline disturbances; record gain, noise, false detections, misses, and recovery. |
| EVT-01 | Deliver one count per accepted event; apply configurable per-channel refractory timing. | Compare accepted events against a known stimulus, including simultaneous channels and close pulses. |
| MCU-01 | Use STM32 firmware to generate eight-element count vectors in configurable time bins. | Test bin boundaries, counter saturation, timer wrap, and sustained load; no silent losses. |
| COM-01 | Send framed packets with sequence identification, bin timing, eight counts, status, and error detection. | Host decodes known vectors and detects deliberately corrupted or missing packets. |
| TEL-01 | Demonstrate ultrasonic load-modulated backscatter with external transmit/receive hardware. | Measure packet error rate, bit error rate where observable, rate, distance, alignment, and board-side power under documented conditions. |
| PWR-01 | Demonstrate inductive power through matching, rectification, protection, storage, and regulation. | Measure startup, delivered DC power, ripple, load steps, and alignment limits under full system load. |
| DBG-01 | Preserve SWD, reset, UART, bench power, subsystem isolation, probe points, and tuning/bypass options. | Bring up and test each block independently, starting with bench power. |
| FW-01 | Keep firmware modular and the build/flash/log/test loop command-line accessible. | Repeat the development loop and capture machine-readable results. |

## Milestones and acceptance

**First milestone:** eight-channel event acquisition and correct count packets over wired UART, powered from a bench supply. Start firmware with known digital test events; then prove the analog chain on one channel before replicating it. This milestone does not establish wireless completion.

**Final milestone:** recover the eight-channel count stream through ultrasound while inductive power supplies the board; compare it with the known input and report measured system performance.

Optional features: powered-down debug ADC, raw waveform capture, timestamps, and automated threshold calibration. Keep them off the critical path.

## Decisions still open

The user requires completion within one month (working planning date: 2026-10-18), has access to a lab's worth of equipment, and owns an STM32 ST-LINK. Access to a suitable STM32 development board is being checked with the lab. The exact instrument inventory and ADS/HFSS access are not yet confirmed.

Budget, signal amplitude/bandwidth/source impedance, detector polarity, event rates, bin range, power ceiling, wireless distances/media, operating frequencies, and permissible error rates remain unconfirmed. Numerical examples in the [planning notes](CuraLink-planning-v0.1.md) are proposed allocations, not established requirements. Parts, pin assignments, and fabrication readiness require later review.

# CuraLink — gain calculations and high-level parts

**Updated 2026-09-22 · STM32WBA52 and two-board architecture selected; AFE gain and component values remain candidates.**

The current detailed study is [the two-board AFE design](2026-09-22-two-board-analog-afe.md). STM32WBA52 with unused ADC and a ceramic antenna is the working controller/RF baseline; the USB fixture uses one DAC waveform split eight ways.

The user clarified that the objective is to remove waveform ADC acquisition. The earlier recommendation based on ADC codes, and the MCU ranking based on ADC channels, are withdrawn. See D-012 in the [engineering handbook](../engineering-handbook.md).

## Gain without an ADC

Gain now follows comparator/threshold accuracy and analog headroom. Let Eout be the bounded detector error at the AFE output, excluding the intentional threshold itself, and Ein the allowed input-referred error:

`Gmin = Eout / Ein`.

For illustration only, a combined comparator-offset and threshold-setting error budget of **2 mV**, with **2 µV** allowed at the electrode, would require **1000 V/V**. A 1 mV budget with the same input allowance would require 500 V/V. These are hypothetical budgets, not specifications of a selected part. Sum bounded errors appropriately; treat random noise separately. Hysteresis also refers back through gain and must be chosen against chatter and sensitivity.

The voltage scaling remains useful:

| Input | Output at 500 V/V | Output at 1000 V/V |
|---|---:|---:|
| 20 µVpp stretch | 10 mVpp | 20 mVpp |
| 50 µVpp characterization | 25 mVpp | 50 mVpp |
| 200 µVpp nominal | 100 mVpp | 200 mVpp |
| 500 µVpp characterization | 250 mVpp | 500 mVpp |
| 1 mVpp headroom test | 0.5 Vpp | 1 Vpp |

Assuming a 3.0 V analog rail and a usable 0.3–2.7 V output window, the ideal symmetric-signal bound is `Gmax = 2.4 Vpp / 1 mVpp = 2400 V/V`. Reserve margin for baseline error, waveform asymmetry, filter peaking, LFP, and artifacts; check every stage. The rail/window are assumptions, not verified amplifier/comparator limits.

At gain 1000, a threshold excursion of 20 µV at the input maps to 20 mV relative to output bias. A symmetric 50 µVpp signal has only 25 µV peak before waveform-dependent filtering, so threshold errors and noise matter. If total input noise were 6 µV RMS, that peak would be only 4.2 times RMS noise, below a five-sigma threshold. The project's 6 µV RMS objective is electronics-only, so source noise must also enter detection analysis. Increasing gain does not improve the electrode signal-to-noise ratio.

**Conclusion:** retain 500–1000 V/V as illustrative evaluation points, not a selected gain range. Select actual gain only after bounding comparator offset/noise, threshold-setting accuracy, hysteresis, total noise, and headroom. The previous ADC-code argument does not justify 1000 V/V.

## Functional blocks and candidate parts

`8 inputs + shared REF → DC handling and low-noise gain → ~300 Hz–7 kHz conditioning → analog threshold detection → MCU event capture/refractory handling → count bins → BLE`.

Polarity handling, threshold generation, comparator count, hysteresis, and the division of rearm/refractory logic between analog circuitry and firmware remain open. Preserve analog test points for external waveform measurements; an onboard debug ADC is not assumed.

| Block | Candidate / next selection criterion |
|---|---|
| Custom AFE amplifiers | **TLV9064S** remains an earlier candidate, pending input-capacitance, noise, power, common-mode, swing, and recovery checks. [Manufacturer](https://www.ti.com/product/TLV9064) |
| Comparators and thresholds | **Open.** Compare offset/drift, noise, hysteresis, propagation delay, pulse behavior, input range, current, package, and threshold generation/calibration. No exact part selected. |
| BLE MCU | **STM32WBA52**, user-selected working baseline. Audit eight event GPIO/timing resources, BLE coexistence, debug pins, and final package. Its internal ADC remains unused. [Manufacturer](https://www.st.com/en/microcontrollers-microprocessors/stm32wba52kg.html) |
| Regulators | **TPS7A20** remains a provisional candidate; rail partitioning/voltages open. [Manufacturer](https://www.ti.com/product/TPS7A20) |
| Battery charger | **BQ25185** was a provisional power-path candidate; D-007 now excludes charge-and-run, so load sharing is unnecessary. Recompare against simpler 1S CC/CV chargers before selection. [Manufacturer](https://www.ti.com/product/BQ25185) |
| Wireless receiver | **BQ51013B** only if Qi is selected; coil approach remains open. [Manufacturer](https://www.ti.com/product/BQ51013B) |
| Battery | Protected 1S cell; previous approximately 50 mAh estimate must be recalculated from comparator/MCU/radio loads against the one-hour target. |

The external ADS7951 fallback is withdrawn from the current direction. No procurement decisions or guaranteed power/area savings follow from removing the ADC alone: include comparators, threshold circuitry, and event handling in the comparison.

## Existing evidence and remaining limits

The earlier candidate used gain distribution `11 × 34.89 × 1.15 × 2.24 ≈ 989 V/V`, with modeled 1 kHz gain about 946 V/V. This is preserved as a candidate transfer-function calculation, not a required topology or selected gain. Every stage still needs overload/recovery verification.

The modeled input capacitance fails the original ≥10 MΩ target over the full band. This unresolved tradeoff remains open; low predicted amplitude loading is not proof that the impedance requirement is met.

The [historical system proposal](2026-09-21-curalink-rev-a-proposal.md) and [calculation record](../calculations/afe-study/report.md) retain the previous ADC-based work. Their sampled software detector results do not verify comparator behavior. The newer [two-board AFE proposal](2026-09-22-two-board-analog-afe.md) provides component-level starting values and open verification gates.

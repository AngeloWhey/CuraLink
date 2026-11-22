# MCU supply and acquisition constraints

**Primary-source audit and calculations · 2026-10-01 · candidate schematic, not fabrication released.** This note distinguishes supply sequencing, active analog pin protection, acquisition timing and software ADC ownership. These are separate conditions.

## Supply sequencing and analog inputs

For the selected WBA52CGU6, ADC VREF+ is internally VDDA. While an ADC input's analog function is active, the permitted upper pin voltage is **VDDA + 0.3 V**, with valid conversions restricted to 0–VDDA. This is not a general VDD + 0.3 V constraint. General FT digital-pin tolerance does not apply to an active ADC path, whose parasitic analog protection diodes are not characterized as a permitted clamp. See [ST AN4899 Rev 4 §§5.2.2 and 5.3.6](https://www.st.com/resource/en/application_note/an4899-stm32-microcontroller-gpio-configuration-for-hardware-settings-and-lowpower-consumption-stmicroelectronics.pdf).

[DS14127 Rev 10 §3.12.1](https://www.st.com/resource/en/datasheet/stm32wba52cg.pdf) permits independent VDDA once VDD reaches 1 V; below that startup level VDDA must stay within VDD + 0.3 V. On shutdown, differing decoupling-discharge constants are allowed if energy delivered to the MCU is below 1 mJ. Table 28's −5/+0 mA injection entries and general FT voltage table do not authorize forward conduction of the active ADC's analog parasitic diodes.

**Design implication:** retain the quiet separate analog LDO if its hardware enable cannot assert before the digital rail is safely above 1 V. The proposed DVDD-good comparator with nominal 1.5 V rising / 1.4 V falling thresholds is a defensible sequencing mechanism; validate minimum threshold after offset/resistor tolerances, propagation delay, control-supply startup, analog-LDO enable behavior and worst digital-rail droop. A common enable alone does not prove ordering. The datasheet does not require replacing both rails with one regulator.

The AFE and ADC VDDA both use AVDD_3V0, so normal AFE output levels track the reference rail. Check the stored ADC-interface charge and amplifier shutdown transients when AVDD falls; sharing the rail does not prove every input stays within its active-analog ceiling. A capacitor-energy bound is E = Σ(½ C V²). For example, 100 µF at 3 V stores 0.45 mJ; the complete bound must include every continuing source that can deliver energy into the MCU. This supply-sequencing allowance does not waive pin voltage limits.

Use target-referenced SWD/UART, NRST open-drain drive and no probe-powered target rail. Five-volt digital tolerance is guaranteed only while the MCU is powered; attached tools must not assert an unqualified voltage during CHARGE/system-off. See [AN4899 §§6.2–6.3](https://www.st.com/resource/en/application_note/an4899-stm32-microcontroller-gpio-configuration-for-hardware-settings-and-lowpower-consumption-stmicroelectronics.pdf). Bench traces should include VDD, VDDA, representative ADC input and external debug signal during boot, brownout and RUN↔CHARGE transitions.

## ADC timing arithmetic

The official WBA HAL defines sampling times of 1.5, 3.5, 7.5, 12.5, 19.5, 39.5, 79.5 and **814.5** cycles. **639.5 cycles is unavailable.** Two common sampling-time groups are supported. Sources: [ST HAL sampling selections](https://github.com/STMicroelectronics/stm32wbaxx-hal-driver/blob/c36d9aabc6068051ed27a3a683a6b4f35f04d815/Inc/stm32wbaxx_hal_adc.h#L740), [common-time fields](https://github.com/STMicroelectronics/stm32wbaxx-hal-driver/blob/c36d9aabc6068051ed27a3a683a6b4f35f04d815/Inc/stm32wbaxx_hal_adc.h#L229).

The following calculations assume 12-bit conversion takes 12.5 cycles, no oversampling, uninterrupted ADC service and a stable running clock. They exclude ADC/sensor startup, ownership transfer, VREFINT, helper polling and processor overhead.

| ADC kernel / sampling | One neural channel | Eight neural channels | One temperature conversion | Eight neural + temperature |
|---|---:|---:|---:|---:|
| 48 MHz; neural 79.5 cycles; temperature 814.5 | 1.91667 µs | 15.3333 µs | 17.2292 µs | 32.5625 µs |
| 32 MHz; neural 79.5 cycles; temperature 814.5 | 2.875 µs | 23.0000 µs | 25.8438 µs | 48.8438 µs |
| HSI16; neural 39.5 cycles; temperature 814.5 | 3.250 µs | 26.0000 µs | 51.6875 µs | 77.6875 µs |

At 30 kS/s/channel a frame is 33.3333 µs; the 48 MHz combined sequence leaves **0.7708 µs**, insufficient to assert continuous background calibration without integration evidence. At 40 kS/s/channel a 25 µs frame cannot contain that sequence. The sensor requires at least 13 µs sampling, and its buffer startup can add up to 10 µs when applicable. See [DS14127 Tables 83 and 86](https://www.st.com/resource/en/datasheet/stm32wba52cg.pdf).

**Working recommendation:** neural acquisition at 48 MHz / 79.5 cycles with the verified-model 150 Ω / 470 pF interface, and an explicit, measured radio-calibration service policy. Mark any bounded sample gap and invalidate the affected count interval; do not report it as continuous capture. If continuous capture across radio service is a firm requirement, prove a schedule/ownership implementation before ordering or revisit ADC versus comparators/external conversion.

The 48 MHz source can be PLL1P, subject to a legal PLL configuration and the ADC frequency ceiling; its source is explicitly listed in [ST RCC definitions](https://github.com/STMicroelectronics/stm32wbaxx-hal-driver/blob/c36d9aabc6068051ed27a3a683a6b4f35f04d815/Inc/stm32wbaxx_hal_rcc_ex.h#L455). **It is a Run/Sleep proposal. Stop0 shuts PLL off**, according to [ST PWR driver documentation](https://github.com/STMicroelectronics/stm32wbaxx-hal-driver/blob/c36d9aabc6068051ed27a3a683a6b4f35f04d815/Src/stm32wbaxx_hal_pwr.c#L323). HSI16 autonomous ADC requests are a separate option; [ES0592 Rev 7 §2.2.12](https://www.st.com/resource/en/errata_sheet/es0592-stm32wba5x-device-errata-stmicroelectronics.pdf) supplies the affected-revision workaround. Qualify the exact silicon revision, timer trigger, DMA destination, post-wake behavior and power rather than transplant the PLL timing into a Stop0 claim.

## ADC sharing and release conditions

ST's common temperature helper acquires, reads and releases the ADC; the default ADC helper reserves one of eight helper ranks for VREFINT, leaving seven user ranks. That is a **helper limitation, not a hardware seven-channel restriction**. Its polling/reconfiguration behavior is not the eight-channel DMA implementation required here. Inspect the exact WBA52 software release and implement one ADC owner; do not let radio service reconfigure or power down neural acquisition invisibly. Stable evidence: [temperature helper](https://github.com/STMicroelectronics/STM32CubeWBA/blob/e455b860ceb52aaa0332a98f1e7a10bbd7014fc9/Projects/Common/WPAN/Modules/temp_measurement.c#L69), [rank limit](https://github.com/STMicroelectronics/STM32CubeWBA/blob/e455b860ceb52aaa0332a98f1e7a10bbd7014fc9/Projects/Common/WPAN/Modules/adc_ctrl.c#L39), [reconfiguration](https://github.com/STMicroelectronics/STM32CubeWBA/blob/e455b860ceb52aaa0332a98f1e7a10bbd7014fc9/Projects/Common/WPAN/Modules/adc_ctrl.c#L547).

Before release, prove analog settling and pin compliance, timestamped eight-channel capture under the intended BLE traffic/calibration events, controlled RUN/CHARGE behavior with attached tools, and measured acquisition-plus-radio current. Typical adapted op-amp simulation, ERC and timing arithmetic do not establish these hardware/software results. No firmware is created by this handoff.

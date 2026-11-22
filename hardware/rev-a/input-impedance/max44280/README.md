# MAX44280 candidate, gain-11 input verification

**2026-11-22, LTspice 26.0.2.1**, 27 °C, 3.0 V analog rail. The [four-channel candidate](../../bench-four-coax-low-c/README.md) satisfies the 10 MΩ target in these simulations only within a tight, explicit board capacitance budget. At 2 pF of added PCB capacitance per input it fails. The calculations below retain the protected 47 kΩ generator fixture, 5.1 kΩ limiter, 10 nF AC block and 22 MΩ bias resistors.

## Measurement planes and models

The generator drives a 50 Ω output and a 100 pF cable equivalent upstream of the physical 47 kΩ source resistor. A zero-volt sensing branch at the resistor output measures current entering the protected input. Complex impedance is the voltage **at that plane** divided by that current. Cable capacitance therefore remains on the low-impedance source side. The external ESD and PCB loading are inside the measurement. A dedicated test drives REF through its 47 kΩ in place of the normal quiet ground connection.

Each of five MAX44280s runs at noise gain 11. Local ADI symbol order in LTspice is **IN+, IN−, VDD, VSS, OUT, SHDN**. For the physical SC70-6, the order is **IN+, VSS, IN−, OUT, SHDN, VDD**. A high on SHDN enables the IC. The full candidate retains U109's VMID driver and three powered spare followers and moves only the five high-impedance input bias returns to VMID_RAW. Currents from the filter and gain networks still return through the original inductance-free 47 Ω modeled isolation resistor to VMID_BUF. [ADI MAX44280 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX44280.pdf)

The isolated native model gave gain **11.0000** and effective input capacitance **0.4010 pF at 7 kHz**. Driving both model inputs together gave 0.4010 pF while holding the inverting input at AC ground gave 0.4020 pF. The modeled differential contribution in that test is only 0.0010 pF. ADI specifies generic input capacitance of 0.4 pF typical, with no separate limit on common-mode or differential capacitance. These simulations establish what the supplied model implements. They do not impose a production upper bound. Isolated input-noise model results were 58.2/32.8/24.0/14.9/13.4 nV/√Hz at 300/1000/2000/7000/10000 Hz. ADI lists 12.7 nV/√Hz typical at 10 kHz and provides the frequency curve. [ADI electrical characteristics](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX44280.pdf)

## Impedance and bias results

At 0.75 pF of board loading, substituting five MAX parts alone yielded **11.49 MΩ at 7 kHz but only 6.54 MΩ near 496 Hz**. Driving CH1 moved the shared post-isolation VMID, which couples through its 22 MΩ input return. Driving REF with a return to the upstream amplifier output also showed excess loading in the stressed case. The revised five returns use the bypassed, lightly loaded divider. [Full result data](results.json)

| Total added PCB capacitance per protected input | Nominal minimum | Stressed minimum |
|---|---:|---:|
| 0.60 pF | 12.478 MΩ | 10.701 MΩ |
| 0.75 pF | 11.674 MΩ | 10.075 MΩ |
| 1.00 pF | 10.509 MΩ | 9.164 MΩ |
| 2.00 pF | 7.383 MΩ | 6.659 MΩ |

Comparison uses CH1 across 300 Hz–7 kHz. Nominal values use 22 MΩ, the MAX model's intrinsic input capacitance and 0.50 pF ESD capacitance. The stressed cases use **21.78 MΩ, an additional 0.20 pF** at each amplifier and **0.65 pF** at each ESD input. The listed PCB capacitance is added at each post-47 kΩ protected node. A real board distributes capacitance across both sides of the limiter and coupling capacitor. This is a first-order sensitivity estimate. TI's quoted 0.5 pF is typical at 1 MHz with 2.5 V pin bias. The near-zero generator-side DC bias, process spread and board contamination need physical verification. [TI TPD4E05U06 data](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf)

With 0.75 pF board loading and all stated stress assumptions, each distinct CH excitation and the separate shared REF excitation measured **at least 10.0754 MΩ**. REF drove all four outputs with similar magnitude. For CH1–4 aggressors the worst quiet-channel/active-channel ratio was **−51.06 dB**. The geometry-dependent crosstalk and intended crosstalk limit remain separate release gates. The existing ESD remains downstream of each 47 kΩ source. Moving CH ESD upstream in the original post-isolation-bias circuit gave only 8.50 MΩ at 7 kHz with 2 pF of layout loading and did not resolve its mid-band dip. Capture both the surge-return path and total capacitance if protection is relocated.

## Noise, headroom and power

| Full candidate result | Value |
|---|---:|
| Input-referred electronics-only noise, 300 Hz–7 kHz | **2.983 µVrms** |
| Including generator and emulator resistance noise | **4.400 µVrms** |
| Switched 3.0 V AFE rail at settled zero input | **6.016 mA, 18.05 mW** |
| Baseline rail in same model at zero input | 2.432 mA, 7.30 mW |
| Gain at 1 kHz with one active CH | 970.89 V/V |
| Peak CH gain within 300 Hz–7 kHz | 1,008.22 V/V |
| ADC1–ADC4 at DC, three offset patterns | 1.503118 V each |

The electronics-only estimate retains the generator source impedances while suppressing their thermal noise. Including their Johnson noise measures the complete fixture. The four-channel DC cases applied zero to all inputs, alternating ±100 mV to CH1–4 and +100 mV to REF, then reversed every sign. Ideal coupling capacitors reject these static offsets at convergence. This test does not characterize recovery after connecting or disconnecting a source. At 200 µVpp the worst-band modeled CH output is about 202 mVpp. At 1 mVpp it is about 1.01 Vpp around the measured operating point, leaving roughly 1 V to either rail for a single aggressor. Measure artifact clipping, startup recovery and actual ADC performance on the populated board. Current here belongs only to the analog model.

## Reproducing the result

Run `python evaluate.py` with NumPy, LTspice and its ADI library installed. Set `CURALINK_LTSPICE_EXE` to override the default local executable path. The runner reads the committed four-channel reference fixture and its TI model libraries, substitutes five ADI models, and writes the evidence to [results.json](results.json). The tested installed **MAX44280.sub** had SHA-256 `6a02b00dd7e409b1e498d090191aba69b0f08d3243fa087f057f38e99cefbc42`. Standard entry points include the [isolated AC check](isolated.cir), [stressed CH1 AC sweep](candidate-ac-ch1.cir), [electronics-only noise](noise-candidate-electronics.cir) and [mixed-polarity settled test](op-candidate-mixed-plus.cir).

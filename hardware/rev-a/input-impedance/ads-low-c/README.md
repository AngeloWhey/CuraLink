# Low-capacitance four-channel AFE in ADS

The stressed complete input passes the 10 MΩ magnitude requirement with an assumed 0.60 pF layout contribution. At 1.00 pF it fails. ADS separately drives CH1, CH2, CH3, CH4 and REF from a 47 kΩ fixture. In each solve it measures complex input voltage and current at the protected plane from 300 Hz to 7 kHz. All five minima occur at 7 kHz.

| Added layout capacitance per input | Lowest full-band impedance, rounded | Result |
|---|---:|---|
| 0.60 pF | 10.70 MΩ | Pass in model |
| 0.75 pF | 10.08 MΩ | Pass with little margin |
| 1.00 pF | 9.16 MΩ | Fail |

The LTspice extraction biases the installed ADI MAX44280 device at 3.0 V and 1.5 V common mode with a 10 kΩ / 1 kΩ closed-loop feedback network. Three independent 50 Ω excitations yield the complex three-port response from 10 Hz to 100 MHz. The three ports represent the noninverting input, the return terminal of the gain-setting resistor and the output. This preserves interaction with the finite shared VMID impedance. The file describes an active circuit. Each channel and REF uses this same solved stage. [Stage extraction](extract.py) · [Simulated Touchstone file](max44280-gain11.s3p)

ADS 2026 Update 2 applies that model in the four-channel circuit. The separate five high-value bias returns go to VMID_RAW. Stress assumptions are 21.78 MΩ bias resistance, 0.65 pF ESD capacitance and 0.20 pF added to the modeled amplifier input. Ideal bias tees establish the DC reference for the small-signal three-port. Their large ideal capacitor/inductor warnings and the translated TI-family macro's internal DC-path corrections are visible in the logs. The exported [native ADS deck](stressed.ckt), [dataset](stressed.ds) and [15 case results](results.json) correspond to the separately excited channels and reference. The native dataset is for the 0.60 pF case. Read the full vendor LTspice study for DC offset, power and noise. The two solvers share the same amplifier model evidence. Neither measures the PCB. [Full-device LTspice runs](../max44280/README.md)

Run `extract.py` with Python, NumPy and LTspice to regenerate the stage file. Run `run.py` using the ADS installation's bundled Python to repeat the three layout-capacitance cases.

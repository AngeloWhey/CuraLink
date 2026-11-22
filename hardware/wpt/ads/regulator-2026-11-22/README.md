# TPS70950 load and line transient

ADS 2026 Update 2 ran TI's TPS70950 unencrypted transient model, version 1.00, at the **regulated receiver output**. The raw input is an imposed line profile through 0.2 Ω with a 1 µF reservoir. Load conductance switches between 2 and 24 mA at 5 V. Output capacitance is 4.7 µF effective with 20 mΩ ESR. The ideal 2 V EN source represents the internal enable pull-up which this vendor model omits. Hardware leaves pin 3 open.

| Condition | Raw input (V) | Output (V) | Actual load (mA) |
|---|---:|---:|---:|
| Nominal full demand | 6.495 | 4.9973 | 23.99 |
| Weak source | 5.196 | 4.3932 | 21.09 |
| Light load | 12.000 | 5.0019 | 2.00 |

The maximum output in the scripted 20 ms waveform was 5.01274 V. The dataset checks the dynamic response to the imposed raw waveform, independent of RF link behavior. The model uses a fixed 0.8 V subtraction in its internal drive law. Treat that low-input point as a property of this macro. The physical part's data include a 500 mV maximum dropout at 50 mA under specified conditions; they do not specify that exact transient point at 24 mA. The characteristic table's line-regulation interval for the 5 V part starts at 6 V. The RF study uses 6 V raw as a conservative headroom screen. [TI datasheet](https://www.ti.com/lit/ds/symlink/tps709.pdf) · [TI model download](https://www.ti.com/lit/zip/SBVM527)

Open waveforms.csv or summary.json on any laptop. To rerun locally, use ADS Python with run.py. regulator.ckt includes complete.net, translated from the vendor LIB plus fixture.cir with ADS nettrans -pl -g. The translator renamed the reserved node rect to rect_n. ADS applied eight automatic DC-path corrections. The model does not qualify output short-circuit heating, reverse leakage, a BLE fault report during brownout, or capacitor bias derating. The [coupled receiver study](../receiver-ic-review-2026-11-22/) covers the RF boundary.

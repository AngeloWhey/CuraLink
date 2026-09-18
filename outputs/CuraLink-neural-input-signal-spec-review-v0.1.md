# CuraLink neural input signal specification — engineering review and revision

Date: 2026-09-18  
Status: reviewed working revision; suitable for AFE simulation and bench-test planning after the changes below. The original user-provided specification is preserved in CuraLink-neural-input-signal-spec-v1-original.md.

## Verdict

The specification is a credible starting envelope for a benchtop intracortical extracellular-spike emulator. The 50–500 microvolt peak-to-peak characterization range, roughly millisecond-scale spike, 47 kΩ first-order source resistance, low-frequency LFP component, and positive/negative event detection are practical engineering targets. Published Neuralink electronics data support the cited order of magnitude for gain, bandwidth, input-referred noise, and input range, but those values describe a broadband recording ASIC and should not be treated as universal biological limits. The cited Neuralink ASIC reports 42.9–59.4 dB gain, 3 Hz–27 kHz bandwidth, 5.9 microvolt RMS input-referred noise measured over 3 Hz–10 kHz, and 7.2 mV peak-to-peak maximum differential input range. [Neuralink platform paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6914248/)

The specification needs one architectural distinction: the signal presented to the AFE and the signal that one particular fixture can generate are different requirements. A single AWG plus the current 1000:1 passive attenuator can produce the spike envelope very well, but it cannot produce a 100 mV AFE-side DC offset through that same path without an impossible approximately 100 V AWG setting.

## Items to keep

- Eight inputs plus a shared reference for the benchtop prototype.
- 50–500 microvolt peak-to-peak required characterization range.
- 200 microvolt peak-to-peak nominal test point.
- 0.5–2 ms spike-duration characterization range, with a nominal roughly 1 ms waveform.
- 47 kΩ first-order source resistance, with an impedance sweep.
- Separate spike, LFP, noise, artifact, and DC-offset test modes.
- Positive and negative spike excursions as a detector requirement.
- An input impedance target much greater than the source resistance.
- The statement that the 20 microvolt point is exploratory rather than a first-pass hard requirement.

Extracellular action-potential amplitudes around 50–500 microvolts peak-to-peak and sub-millisecond to millisecond waveform widths are consistent with published neural-recording literature. A recent review gives approximately 20–500 microvolts and a high-frequency band around 300 Hz–5 kHz, while a primary electrophysiology study reports extracellular spike features around 0.5–1 ms and shows substantial waveform variation. [Neural recording review](https://pmc.ncbi.nlm.nih.gov/articles/PMC13129172/) [Extracellular waveform study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4509390/)

## Required adjustments

### 1. Separate the detection band from the biological spectrum

Replace the hard statement that the useful spike spectrum is 300 Hz–6 kHz with:

> Initial analog detector band: tune and characterize a high-pass corner of 250–300 Hz and a low-pass corner of 6–10 kHz. Use 300 Hz–6 kHz as the first nominal design point, not as a universal neural-spike bandwidth.

A 300 Hz high-pass is useful for rejecting slow LFP content, but it is only near its corner at 300 Hz. It does not strongly reject components just below 300 Hz unless the filter order and attenuation are specified. Simulate attenuation at 1, 10, 50, 100, 200, and 300 Hz. Simulate spike peak loss and timing distortion for both 0.5 ms and 2 ms waveforms. Keep the first version simple: band-pass plus threshold plus hysteresis. Do not add a notch filter until measured interference shows that it is needed.

### 2. Make noise goals conditional on amplitude

Keep ≤5 microvolt RMS input-referred electronics noise as a design goal over the defined detector band, but label it as a stretch goal for the one-shot board and add a practical acceptance tier:

| Test tier | Input-referred electronics noise over detector band |
|---|---:|
| Preferred | ≤3 microvolt RMS |
| Acceptable for nominal 100–300 microvolt spikes | ≤5 microvolt RMS |
| Investigation required | >5 microvolt RMS |

The 20 microvolt peak-to-peak spike is not expected to be reliably detected when total input-referred noise is near 5 microvolt RMS. Keep it as a sensitivity experiment. The first reliable detection requirement should begin at 50 microvolt peak-to-peak under a specified noise and artifact condition.

Do not compare a spike peak-to-peak value directly to RMS noise without defining the waveform. Report detection SNR using the measured template peak, peak-to-peak value, or matched-filter-equivalent metric, and report the noise bandwidth.

### 3. Clarify DC offset and LFP injection

The ±100 mV offset and 50 microvolt–5 mV LFP envelope are AFE-side stress requirements. They are not all generated through the existing 1000:1 AP attenuator.

Use one of these practical test arrangements:

- Primary AWG mode: one AWG uploads a composite waveform containing AP + LFP + band-limited noise. Use the 1000:1 path for the AP-scale test. This is practical for a single-channel AWG and produces the same waveform on all eight channels.
- Two-source stress mode: one AWG drives the AP path while a second low-frequency/DC source injects offset and LFP through a separate selectable summing path.
- AFE-side offset mode: use a bench DC source or a fixture injection node after the AP attenuator to apply a controlled offset relative to REF. Include current limiting and a defined return path.

For the existing 1000:1 path, a 5 mV AFE-side LFP component needs approximately 5 V at the AWG input and is near the upper range of many generators. A 100 mV AFE-side DC offset would require approximately 100 V and is therefore not a valid single-path AWG test. Add a separate DC/LFP INJECT path or explicitly remove the ±100 mV test from the first fixture.

### 4. Correct the AWG amplitude convention

The fan-out fixture has approximately:

- RCH = 47 kΩ / 8 ≈ 5.875 kΩ
- RSHUNT = 49.9 Ω parallel 5.875 kΩ ≈ 49.5 Ω
- Open-circuit Thevenin transfer from the AWG source to TEST_SIGNAL approximately 49.5/(50+49.9k+49.5) = 0.000989

That is close to 1000:1 when the AWG voltage is interpreted as the source's open-circuit voltage. A generator configured to display voltage for a 50 Ω load may produce approximately twice that source voltage when connected to this high-impedance attenuator, depending on its output-load setting. Do not rely on the front-panel amplitude alone. Calibrate SIGNAL_IN and TEST_SIGNAL with the exact AWG load setting, cable, attenuator population, and measurement probe.

For the 1000:1 path, the approximate AWG-side peak-to-peak settings are:

| Desired AFE spike | High-impedance calibrated setting | Approximate 50 Ω-mode setting before calibration |
|---:|---:|---:|
| 20 microvolt peak-to-peak | 20 mVpp | 10 mVpp |
| 50 microvolt peak-to-peak | 50 mVpp | 25 mVpp |
| 100 microvolt peak-to-peak | 100 mVpp | 50 mVpp |
| 200 microvolt peak-to-peak | 200 mVpp | 100 mVpp |
| 500 microvolt peak-to-peak | 500 mVpp | 250 mVpp |
| 1 mV peak-to-peak | 1 Vpp | 500 mVpp |

The table is only an initial setup estimate. Measure the actual transfer before recording data. Use a high-impedance, low-capacitance probe or a dedicated buffer test point; a normal probe can disturb the high-impedance test node.

### 5. Define what one AWG can and cannot prove

One arbitrary waveform generator can generate a deterministic composite waveform containing:

- a biphasic or triphasic AP template,
- a low-frequency sinusoid or recorded LFP-like trace,
- seeded band-limited noise,
- amplitude variation,
- repeated and randomly timed spike events,
- occasional artifact pulses.

This is practical if the AWG supports arbitrary waveform upload, adequate memory, and at least 100 kS/s; 1 MS/s or higher is preferable for a 0.5 ms waveform and convenient 1 ms timing. Generate the waveform offline at a fixed sample rate, upload it, and document the repeat period and random seed.

A single-channel AWG plus passive fan-out gives all eight channels the same analog waveform. That is useful for channel-to-channel gain, threshold, and crosstalk comparisons, but it does not prove independent neural timing or multi-channel event separation. Test MCU channel identification separately with a digital event injector, a second output, or a development board.

If the AWG does not provide a noise function, generate the noise offline and include it in the arbitrary waveform. Keep a deterministic seed so a failure can be reproduced. Run separate tests with AWG output disabled to measure the CuraLink electronics noise floor.

### 6. Tighten the reference requirement

REF must be defined by the AFE common-mode architecture. It is not automatically the same as bench ground. The fixture should expose REF, keep the connection selectable through a resistor or jumper, and allow the AFE's defined reference or mid-supply bias to be connected without permanently shorting it to ground. Verify the FFC contact orientation and the return-current path before fabrication.

### 7. Treat 47 kΩ as a first-order source model

A 47 kΩ resistor is useful for first-pass loading and channel matching. It does not reproduce electrode capacitance, polarization, frequency-dependent impedance, half-cell potential, or common-mode behavior. Keep the resistor sweep, then add a simple optional RC model only after the AFE works. Use the actual impedance magnitude and phase at 300 Hz, 1 kHz, and 6–10 kHz when selecting the input network.

The input impedance requirement should be checked at the complete AFE input node, including protection, bias, coupling capacitors, and filter components. ≥10 MΩ over the signal band is a reasonable target for keeping a 47 kΩ source error below roughly 0.5%, but it is not sufficient by itself to guarantee low noise or stable biasing.

## Revised working input envelope

| Parameter | Revised working value |
|---|---:|
| Modality | Intracortical extracellular-like benchtop emulator |
| Channels | 8 + configurable REF |
| Nominal spike | 200 microvolt peak-to-peak |
| Required spike sweep | 50, 100, 200, 300, 500 microvolt peak-to-peak |
| Exploratory weak point | 20 microvolt peak-to-peak |
| Headroom test | 1 mV peak-to-peak |
| Spike template duration | 0.5–2 ms sweep; nominal 1 ms |
| Initial detector band | 300 Hz–6 kHz |
| Detector tuning sweep | HP 250/300/500 Hz; LP 6/8/10 kHz |
| LFP stress envelope | 50 microvolt–5 mV, 0.1–300 Hz, injected through a separate or calibrated low-frequency path |
| DC stress envelope | 0, ±10, ±25, ±50, ±100 mV at AFE input, through a separate protected injection path |
| Source model | 47 kΩ nominal resistor; 20–100 kΩ characterization; optional RC later |
| Electronics-noise goal | ≤5 microvolt RMS over detector band; ≤3 microvolt RMS preferred |
| First reliable detection target | ≥50 microvolt peak-to-peak under specified noise and artifact conditions |
| Spike polarity | Positive, negative, and biphasic templates |
| AFE input impedance | ≥10 MΩ over the relevant band, verified at the complete input node |
| AWG | Arbitrary upload, ≥100 kS/s; ≥1 MS/s preferred; single-channel fan-out acceptable for Rev A |

## Recommended test matrix

1. Transfer calibration: measure AWG-to-TEST_SIGNAL amplitude and phase at 10 Hz, 100 Hz, 300 Hz, 1 kHz, 6 kHz, and 10 kHz for the exact fixture population.
2. Clean spike sweep: one biphasic template at 20/50/100/200/300/500 microvolt and 1 mV peak-to-peak, with AWG noise disabled.
3. Timing sweep: 0.5/1/2 ms templates and several inter-spike intervals around the intended refractory period.
4. LFP rejection: 50 microvolt–5 mV at 1/10/50/100/200/300 Hz, with spike amplitude held constant.
5. Noise robustness: repeat the clean-spike sweep with seeded band-limited noise at documented RMS levels.
6. Offset recovery: apply 0, ±10, ±25, ±50, and ±100 mV at the AFE-side input using the separate protected injection path; measure damage, saturation, recovery, and false events.
7. Polarity: negative, positive, and biphasic templates with equal nominal peak-to-peak amplitude.
8. Channel fan-out: verify all eight outputs, channel-to-channel amplitude error, crosstalk, and REF behavior.
9. AWG-off floor: terminate the fixture and measure the AFE/comparator false-event rate and input-referred noise independently of the generator.

## Bottom-line engineering decision

Approve this as the starting signal envelope after changing the document to distinguish:

- biological-like AFE input requirements,
- the single-AWG/passive-fixture capability,
- and separate DC/LFP stress injection.

Proceed to the AFE budget with 300 Hz–6 kHz as the first nominal detector band, but simulate 250–500 Hz high-pass and 6–10 kHz low-pass alternatives before locking components. Keep the one-channel clean-spike and AWG transfer tests ahead of PCB fabrication.


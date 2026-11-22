# Native ADS receiver cells — 2026-10-09

Three **editable native ADS schematics were actually created and saved** in the working workspace:

`C:\Users\angel\OneDrive\Documents\projects\curalink\MyWorkspace_wrk`

| Library / cell / view | Purpose | Saved first operating point |
|---|---|---|
| `MyLibrary_lib:RX_LoadSweep_20261009:schematic` | Original 4.2 V BV seed as a diagnostic, with corrected floating RX and probes | 26 dBm, 220 Ohm, 13.56 MHz, HB order 7; original matching capacitances |
| `MyLibrary_lib:RX_BAT54_LoadSweep_20261009:schematic` | Manufacturer BAT54 model **candidate**, with candidate matching values | 23.5 dBm, 208.333333 Ohm, 13.56 MHz, HB order 31; C3/C5/C1/C6 = 59.3004634 / 374.7395638 / 826.2058518 / 773.5931919 pF |
| `MyLibrary_lib:RX_ChargerLoad_20261009:schematic` | **Unexecuted authored static charger-load candidate** copied from BAT54; exact raw-equivalent SDD law | 23.5 dBm, VBAT 3.7 V, nominal charge demand 20 mA, control 0.8 mA, fixed path drop 0.28 V, 13.56 MHz / HB31; same candidate matching capacitors |

The BAT54 matching values are ideal simulation candidates, not hardware part selections. The fresh native OA-readback netlist **actually simulated successfully** at HB31: 5.088532 V, 24.424956 mA, 124.287177 mW useful DC, 55.5170% relative to available RF power, and 5.718411 V maximum diode reverse voltage. All native `aele` measurement equations parsed and produced output. Evidence is retained in [the native validation run](../receiver-fixture-2026-10-09/runs/native_BAT54_candidate_validation). No charger or battery model is in these resistor-load cells. The MCU/AFE remain OFF during CHARGE; `Rload` represents charger plus control demand.

## Open and simulate

In the **ADS Main window**, select **Library View**, use **View → Refresh** (or press **F5**), then expand **MyLibrary_lib → RX_BAT54_LoadSweep_20261009** and double-click **schematic**. Cells created externally can be absent from a stale browser until it refreshes. This route was verified in the user's live ADS window on 2026-10-09: all five library cells appeared and the BAT54 schematic opened in **EDITING** mode. The original open `cell_1` was left open. Do not use the earlier imprecise “File → Open → Design” instruction.

The actual validated native dataset was also copied, with a SHA256 equality check, to the new file `data\RX_BAT54_LoadSweep_20261009.ds` in that workspace. Select this dataset in an ADS Data Display to view the completed single-point result. Existing datasets were not replaced.

`SweepPower` and `SweepLoad` are initially deactivated. The first simulation therefore uses the visible VAR values above. Simulate the candidate and inspect `Vdc`, `Pdc`, `eta_avail`, `Z_source`, `Z_rx` and `Z_bridge`.

To run the 15-point study, activate **both** `SweepPower` and `SweepLoad`, then simulate:

- `SweepLoad` is the outer sweep, calls `SweepPower`, and references `LoadPoints`.
- `LoadPoints` has five exact single points: 208.33, 220, 240, 470 and 1,000,000 Ohm.
- `SweepPower` is the inner sweep, calls `HB1`, and uses `Pin_dBm` = 20 to 26 in steps of 3 (20/23/26 dBm).
- `HB1` retains 13.56 MHz. The candidate is saved at order 31; the diagnostic is saved at order 7. Check convergence/order sensitivity when changing the operating point.

For a single-point manual study, leave both sweeps deactivated and edit `VAR1.Pin_dBm` and `VAR1.Rload`. Repeat the same five loads at each of the three source powers. `Ctx_series`, `Ctx_shunt`, `Crx_series` and `Crx_shunt` are editable matching variables connected to C3, C5, C1 and C6. C2 retains 1 uF.

The [candidate single-point netlist](RX_BAT54_LoadSweep_20261009-fresh-readback.net) and [active 15-point netlist](RX_BAT54_LoadSweep_20261009-sweep.net) were generated from the native API. The single-point native export completed simulation; the exported 15-point native sweep has been netlist-verified but was not simulated by the creation scripts. Their scripts do not invoke a simulator.

The separate [charger/control load approximation](../charger/recommended-load-model.md) and [standalone SDD fixture script](../charger/run_charger_fixture.py) cover charger/control demand, the assumed series drop, input capacitance, divider and protection overhead. These are authored behavioral approximations, not a TI charger macromodel. They have not been inserted into either of the two native resistor-load cells above; use the separate fixture's recorded verification status when interpreting its results.

## Native charger-load candidate: unexecuted

Open **`MyLibrary_lib:RX_ChargerLoad_20261009:schematic`** through **Library View → MyLibrary_lib → RX_ChargerLoad_20261009 → schematic**, refreshing with F5 in the Main window if needed. This third cell was created and saved, but **no charger-load DC/HB simulation was completed**. The standalone fixture passed parsing/flattening, then its simulator license was unavailable (exit 120 on two attempts). The native script did not attempt another simulation or change the user's application/license state. No solved voltage, charger current or charging-power result is claimed for this cell.

R1 is replaced by `SDD1P` instance `ChargerRawLoad`, positive terminal `RAW_LOAD`, negative terminal ground. Its exact `I[1,0]` expression comes from [the raw-equivalent source](../charger/native-raw-SDD-I-1-0.txt); it combines authored charger IQ/charge demand, control demand, 143 uA eFuse-IQ sensitivity and a 110 kOhm raw divider. The existing `I_Probe1` measures positive total current from `DCout` into `RAW_LOAD`. The native source equation, defaults, all four floating RX-negative terminals and three RF-probe directions passed a separate process's fresh OA readback in [this netlist](RX_ChargerLoad_20261009-fresh-readback.net). See [ChargerLoad-creation-manifest.json](ChargerLoad-creation-manifest.json) and [its creation script](create_charger_load_variant.py).

`VAR_ChargerFixture` shows VBAT = 3.7 V, IPHASE = 0.02 A, IQACTIVE = 0.00075 A, IQSLEEP = 0.00003 A, ICTRL = 0.0008 A, VPATH = 0.28 V and the declared wake/start/DPM ramp assumptions. These are an authored static I–V approximation: **no actual BQ25185, cell, raw OVP, eFuse clamp/cutoff, mode timing or charge-completion model is present**. Its declared `CHG_IN` approximation domain is 0–5.5 V; `CHG_IN_DC_EQ=Vdc-VPATH` is a computed value, not a separately modeled native node.

The existing 1 uF reservoir remains, and `ChargerCinRawEq` adds 2.2 uF in parallel. This matches the explicit fixture's ideal 3.2 uF RF capacitance under a constant series drop. Raw-equivalent loading applies only to positive steady-state operation; it does not establish startup, stored-energy equivalence, weak-source cycling or reverse transitions.

`Rload`, `SweepLoad` and `LoadPoints` are retired from this third cell. `SweepPower` remains deactivated. To try the first operating point, leave it deactivated, simulate, and inspect `Vdc`, actual aggregate `Idc`, `Pdc=Vdc*Idc`, the impedance observables and reverse-voltage waveforms. Verify the resulting `CHG_IN_DC_EQ` is within the declared model domain. `Icharger_input_at_DC`, `Icharge_at_DC`, `Icontrol_at_DC` and `Pcharger_input_DC_EST` evaluate the assumed current laws at DC voltage: they are **estimates**, not solved separate branch waveforms or actual battery charge current. The aggregate raw current waveform is the SDD model's saved current; ripple power needs all harmonic contributions.

For further single-point studies, edit `VAR_ChargerFixture.VBAT`, `IPHASE`, `IQACTIVE`, `ICTRL`, `VPATH` and the declared DPM band, then repeat simulation. Set the charge-phase current deliberately when selecting precharge/CC/CV/disabled snapshots from the supporting study. Activate the source-power sweep only for an intentional 20/23/26 dBm study and reject outputs outside the model's domain. All four previously completed/original cells were preserved by hash checks during creation of this third cell.

## Original saved OA versus current generated circuit

Before this work, `cell_1` had **different saved OA and latest generated-netlist connectivity**. The latest workspace `netlist.log` had floating `IMPin`, but a fresh read of the saved OA grounded the RX negative at G6/G9/G3; DIODE3 was consequently between ground and ground. The generated log could reflect an unsaved GUI correction. This provenance difference was preserved rather than silently changing the original.

Only the new diagnostic copy had G6, G9 and G3 removed. Its L2 negative, C6 negative, DIODE3 cathode and DIODE4 anode were linked by explicit `IMPin` labels. These are actual electrical ADS labels. The complete resulting component-pin netlist was checked against the latest floating circuit before probes were added. The BAT54 cell was copied from that corrected diagnostic.

SHA256 checks before and after creation confirm that **both original cells' `.oa` and `master.tag` files are unchanged**. The latest workspace `netlist.log` was also preserved. Evidence is in [creation-manifest.json](creation-manifest.json), [BAT54-creation-manifest.json](BAT54-creation-manifest.json), [original saved-OA API netlist](source-api-before-copy.net) and [latest floating netlist snapshot](source-latest-floating.net).

ADS uses percent-encoded physical folder names for upper-case cell names. Use the library/cell/view names above in ADS; the exact physical paths are recorded in the manifests.

## Probes and measurements

| Probe | Positive current direction | Port voltage | Meaning |
|---|---|---|---|
| `I_SRC` | `Vin_src` → `Vin` | `Vin_src` to ground | Current from the RF source into the complete matching/link/rectifier network |
| `I_RX` | `Vcoil_P` → `Vout` | `Vcoil_P - IMPin` | Current delivered by the RX coil into its matching network and rectifier |
| `I_BRIDGE` | `VoutMatched` → `Vbridge_P` | `Vbridge_P - IMPin` | Current entering the bare full bridge after the matching shunt C6 |
| Existing `I_Probe1` | `DCout` → R1 | `DCout` to ground | Resistor load current |

The three RF probes use the existing `I_Probe` model in zero-impedance mode with current saving enabled. Series-probe insertion preserves the circuit after contracting each short. Explicit endpoint labels prevent OA branch/net-ID ambiguity. Exact netlist pin connectivity passed a separate process's fresh OA readback for both saved cells.

`RXMetrics` uses `mix(node,{0})` for DC and `mix(node,{1})` for the carrier. `Z_rx` includes the RX matching network; `Z_bridge` is the nonlinear bridge's fundamental impedance. Both depend on power, load and matching values. `Psource_f1`, `Prx_f1` and `Pbridge_f1` use 0.5 × Re(V × conjugate(I)) because ADS HB spectra use peak phasors. They describe only fundamental-frequency power. Total accepted power requires DC plus all harmonic contributions; it is separate from generator available power `dbmtow(Pin_dBm)`.

`Pdc=Vdc^2/Rload` is the useful DC component of resistor power. Ripple power adds `sum(abs(Vh)^2/(2*Rload))` for positive harmonics. This fixture does not establish charger enable/compliance, CC/CV, charge completion or physical cell behavior. HB1 also saves all device currents and voltages at hierarchy depth 2 for loss and stress checks.

For bridge reverse-voltage waveforms in Data Display, use:

```text
VR_D1=ts(Vbridge_P)
VR_D2=ts(DCout)-ts(Vbridge_P)
VR_D3=ts(IMPin)
VR_D4=ts(DCout)-ts(IMPin)
```

Transform each node separately before subtracting: the installed `ts()` documentation warns that arithmetic before transformation can discard a swept spectrum's frequency metadata. Compare each waveform's peak, including light/no load, against the physical diode rating with margin. Inspect pulse current, dissipation and component voltage stress as well as output voltage.

## Diode model boundaries

The seed retains its original BAT15-style `BV=4.2 V`. Its native schematic includes a conspicuous diagnostic note. A modeled avalanche-supported output does not qualify 5 V charging.

The BAT54 copy uses the genuine [manufacturer card](https://www.diodes.com/spice/download/510/BAT54.spice.txt) preserved in [the model source](../charger/model-sources/BAT54-diodes-original.spice.txt), plus the documented [native ADS translation](../charger/model-sources/BAT54-translation-check.net). Every vendor parameter was verified present in the native model line: Is 649 nA, N 1.04, Rs 2.09 Ohm, Ikf 20 mA, Xti 2, Eg 0.58, Cjo 12.4 pF, M 0.381, Vj 0.391 V, Bv 50 V, Ibv 100 uA, Isr 431 nA and Nr 4.99. Translator additions Nbv 1.04, Tnom 27, IkModel 1 and Imax 1000 are retained. The native schematic parameter spelling for the first resistance temperature coefficient is `Trs`; `Trs=0` / `Trs2=0` match the translator's zero coefficients. Native default Fc 0.5 and explicit no-area-scaling `AllowScaling=0` are retained for unity-size devices.

**The BAT54 physical reverse rating is 30 V; the model's 50 V breakdown fit is not a 50 V rating.** The vendor card omits TT. The copy explicitly uses TT=0 to remove the seed's 3 ps setting; this does not model or validate the datasheet recovery test. Package parasitics, temperature and device spread remain qualification work. Diode and matching values remain candidates.

## API provenance and execution

The scripts [create_rx_load_sweep.py](create_rx_load_sweep.py) and [create_bat54_variant.py](create_bat54_variant.py) were executed with the installed ADS `tools\python\python.exe`. They refuse replacing existing destination cells and never close an active workspace. Their installed primary-source API definitions were inspected in:

- `keysight\ads\de\db_uu\_design.py`: `open_design`, `create_schematic`, `copy_design`, `Design.generate_netlist`, `Design.save_design`, `Design.add_instance`, `Design.add_wire`, `Design.add_text`, and `Design.edit.delete`.
- `keysight\ads\de\db_uu\_db_x.py`: instance parameters, `vars`, numbered instance terminals, pin snap points, labels, activation and deactivation.
- `keysight\ads\de\db\_parameters.py`: repeated parameter `repeats` setter, `compound_param`, `string_param` and VAR updates.
- Loaded native `ads_simulation:SweepPlan:symbol` model definitions: `SinglePoint` compound form, one `SwpPlanTextForm` subparameter per point.
- Installed ADS help: **Parameter Sweeps and Sweep Plans**, **mix()** and **ts()**.

The standalone API emitted an existing missing optional SystemVue include (`vtb.defs`) warning. Initial new-probe placement also exposed a default `cond:drawing` layout-layer warning because this schematic-only library has no layout technology; subsequent script placement sets the probe's existing `ads_device:ads_label` layer before creation. No library technology was changed. Both completed saved schematics passed fresh OA/netlist readback; simulation and visual GUI inspection are distinct checks.

# 13.56 MHz bench TX and RX circuits

Open **tx/tx-matching.kicad_pro** and **rx/rx-matching.kicad_pro**. These are separate electrical designs. Solder the local tuning network beside the corresponding spiral. The spiral terminals on these sheets are copper landings. The board outline, actual spiral copper, tuning pads and thermal layout still need physical implementation.

## Why this receiver

The generator supplies an unmodulated 13.56 MHz carrier into the TX match. The receiver must cold-start, fit pick-and-place, feed the existing protected 5 V charger input, and tolerate an unloaded coil when the cell finishes charging. The nominal 10 mm spacing and paper spiral dimensions remain fixed. [Luo et al.](https://doi.org/10.3390/mi14061221)

| Option | Benefit | Cost or condition |
|---|---|---|
| Infineon BAS4002A-RPP four-pin Schottky bridge plus a 5 V LDO | One self-starting bridge package, floating AC inputs, no TX protocol or auxiliary supply. The fixed LDO controls the downstream voltage as charge demand falls. | Two diode drops per conduction path, RF circulating current, LDO headroom and light-load winding heat require testing. |
| ROHM ML7630 active wireless receiver | Integrates receiver control and a programmable output. ROHM specifies up to 200 mW with its paired ML7631 transmitter. | Operation and delivered power with CuraLink’s plain generator and coil pair would require separate qualification. It adds a fine-pitch package and changes the TX development task. [ROHM](https://www.rohm.com/products/power-management/wireless-power/power-receiver-wireless-charge/ml7630-103hb-product) |
| Four separate RF diodes | Useful, reproducible comparison fixture for the earlier ADS runs. | Four placements. The old BAT54 tuning and measured/simulated results belong to that circuit. |

Use **BAS4002ARPPE6327HTSA1**, LCSC C3589694. Pin 1 is DC negative, pins 2 and 3 are AC, and pin 4 is DC positive. Keep the RX coil and shunt capacitor return on AC2. The path from bridge DC negative to the reservoir is local. The generator shield terminates at the TX network only. [Infineon datasheet](https://www.infineon.com/assets/row/public/documents/24/49/infineon-bas4002aseries-ds-en.pdf) · [LCSC](https://www.lcsc.com/product-detail/C3589694.html)

**TPS70950DBVR**, C96028, separates the reservoir, RECT_DC, from WPT_RX_DC. Connect IN=1, GND=2, OUT=5. Leave EN=3 floating as TI specifies for always enabled and NC=4 open. The input operating limit is 30 V. Fit the 1 µF/50 V reservoir close to IN and a 4.7 µF/16 V ceramic close to OUT. Verify the actual output capacitance with DC bias, temperature and tolerance stays between 1.5 and 47 µF, ESR ≤0.2 Ω, including any capacitors directly paralleled on the mainboard. Auxiliary source inputs on the mainboard are mutually exclusive. [TI datasheet](https://www.ti.com/lit/ds/symlink/tps709.pdf)

The SMAJ15A-13-F shunts RECT_DC to receiver ground, cathode band to positive. Its 15 V stand-off and 16.7–18.5 V breakdown at 1 mA protect a different node from the regulated 5 V output. Design the TX drive/idle timeout and measure sustained dissipation; the 400 W impulse rating gives no continuous thermal guarantee. [Diodes Incorporated](https://www.diodes.com/part/view/SMAJ15A)

## Assembly and tuning

The sums in population.csv are starting values. TX series 60 pF uses two 30 pF capacitors in parallel, TX shunt 375 pF uses three 120 pF plus 15 pF. RX series is 1 nF and RX shunt is 680 pF. Provide parallel trim lands on the board and keep loops short. Include their stray capacitance when trimming. The capacitors’ DC voltage ratings alone cannot establish RF loss or permissible continuous RMS current. Quantify heat under misalignment and at charge completion.

Start at low generator power into an instrumented receiver with an electronic load. Check the generator's actual 50 Ω output rating at 13.56 MHz, cable loss and tolerance for reflected power. Establish a repeatable centered 10 mm gap using a nonmetallic spacer. Sweep position and drive while measuring RECT_DC, regulated output, current and temperature. Establish the safe envelope with a dummy load before using a cell. Disconnect grounded input-coax, debug and scope paths that would inadvertently connect RX DC ground to the TX instrument. Use differential or isolated measurement at a floating AC node.

See [packaged-bridge ADS results](../ads/receiver-ic-review-2026-11-22/) and [regulator transient](../ads/regulator-2026-11-22/). The original 71.87% result is a passive, matched RF power ratio. For charger tests record delivered DC power at WPT_RX_DC and signed battery current independently. Record the RF measurement plane when quoting efficiency.

The build script checks the KiCad XML against each intended net and runs native ERC. The dated distributor check covers one TX/RX pair with order minimums. Gerbers, PnP rotation, coil geometry transfer and assembly-house approval remain open.

**Trim lands.** The native schematics mark C707–C709 and C715–C716 do-not-populate. C707/C708 can take the same 120 pF and 30 pF 0805 parts already used in the TX assembly, giving 525 pF total shunt. With coupling reduced to 0.04965 at 25 dBm / 24 mA, ADS predicts this change raises minimum RECT_DC from 5.71 to 6.51 V while preserving the coils and RX components. C709 can add TX series-branch capacitance. C715/C716 can add capacitance to the RX series/shunt branches, respectively. Remove or replace fitted parts when a downward trim is needed. Log the actual setting, load, power and spacing on each hardware fixture.

**Spiral drawing handoff.** Luo's Table 2 specifies TX OD/ID 40/14.60 mm with eight turns, 1.30 mm copper and 0.15 mm spacing. RX is 10/5.55 mm with five turns, 0.30 mm copper and 0.15 mm spacing. Check the aperture convention before converting these into tracks. For example, a cross-section with (N) parallel strips on each side and (N-1) gaps per side has clear opening `OD − 2[Nw + (N−1)s]`, giving 17.10 mm TX and 5.80 mm RX. That simple convention gives different values from Table 2. A continuous spiral has asymmetrical entry/exit segments. Compare the endpoints, aperture definition, return conductor and layer stack with Figures 3 and 10 before marking a drawing as a reproduction. Record deviations and characterize the assembled fixture against its delivered DC power. [Paper, Figures 3 and 10 and Tables 1–3](https://www.mdpi.com/2072-666X/14/6/1221)

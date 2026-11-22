# Rev A active and external procurement check — 2026-10-02

This audit checks the exact MPN, overseas sale/display flags, immediate overseas inventory, minimum order, order multiple and USD price for every non-R/C SKU in `hardware/rev-a/bom.csv`, including DNP components. RT501 is included despite its `R` prefix. The accepted cell and 18-contact FFC cable are additional external items. Copper test/solder/pogo pads and J501–J504 wire fields are PCB fabrication features and are not purchased connectors.

**Result:** all **25 unique non-R/C BOM SKUs** plus the **FFC cable** have exact catalogue MPNs and enough immediately available overseas inventory for their minimum-order quantities, including optional DNP parts. The selected **C19632326 cell remains unconfirmed for global LCSC purchase**. Do not state that every physical component is globally sourced until this exception is resolved.

The [JSON inventory record](stock-active-external-2026-10-02.json) contains one-board populated and DNP counts, actual MPNs, stock, minimum quantities, price tiers, timestamps and links to the 27 raw API responses. A [flat CSV](stock-active-external-2026-10-02.csv) makes order-line review easier. Raw HTTP body/metadata files are in [the evidence directory](raw-active-external-2026-10-02/).

The immediate stock for the MCU is only **9 STM32WBA52CGU6 pieces** (C19626860), with **88 TLV9054IRUCR pieces** (C2057826). These are sufficient for one board; stock is not reserved. The filter MLPF-WB-04D3 and optional BQ29737 each have 192 pieces. No active component substitution is required by this snapshot.

Minimum-order line costs total **US$46.3313** for populated non-R/C components, external thermistor and ten-cable minimum, or **US$47.5611** when also buying DNP alternatives. The cell price is unavailable and excluded; R/C components, PCB, placement loss, assembly, shipping and tax are also excluded. These totals must not be described as a complete assembled-prototype cost.

## Cell exception

Three requests to the [primary LCSC detail API](https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=C19632326) returned HTTP 200 with `code=200`, `ok=true` and `result=null`. This is evidence that the global product record was unavailable, not a zero-stock measurement or permission to infer stock from a different catalogue. The global [LCSC product URL](https://www.lcsc.com/product-detail/C19632326.html) also did not yield a product page through the browsing tool.

An independent sourcing check obtained HTTP 404 at that global product URL and no exact result for the global code search. Model-name search substituted an unrelated crystal, which is not valid battery inventory. Those search bodies and the JLCPCB page source are archived in [battery evidence](battery-raw-2026-10-02/). No compatible stocked global LCSC LiPo replacement was verified by those searches.

The [primary JLCPCB listing](https://jlcpcb.com/partdetail/Taisko-40102055mah/C19632326) identifies Taisko 401020-55mah, 3.7 V, 55 mAh, 20 × 10 × 4 mm. It states that parts-library purchases are held for future PCBA and cannot ship separately. A JLCPCB listing therefore does not close global standalone LCSC sourcing. The main design's bare-cell/protector qualification gate also remains open independently of procurement. The initial bench release retains the current-limited cell-emulator interface.

## FFC and thermistor

C6936300 is **SHOU HAN FFC-0.5-18P-50mm**, 18 contacts, 0.5 mm pitch, 50 mm length, 0.3 mm insertion thickness, same-side contacts; 400 are immediately available, minimum ten, US$0.0580 per cable at that tier. J301 is the exact double-contact FPC 0.5-18P HYH2.0 / C6364663 with 24,335 pieces; inspect its datasheet drawing and connector numbering during layout and cable assembly.

RT501 is **MF52D103F3435L100 / C5439722**, an external leaded 10 kΩ B3435 thermistor, not an SMT population. Its catalogue record has 5,320 pieces, overseas sale/display enabled, and a five-piece minimum. It must be thermally coupled to the actual qualified cell rather than sensing only PCB ambient.

## Interpretation limits

Live distributor stock and overseas sale flags establish an inventory snapshot. They do not establish feeder allocation, JLCPCB placement eligibility, catalogue footprint correctness, cell shipping to a destination or hardware electrical performance. DNP inventory is checked for optional build variants; those parts remain unpopulated in the default circuit. No canonical schematic, component catalogue or accepted design choice changed during this audit.

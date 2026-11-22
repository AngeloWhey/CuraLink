# Power package and footprint audit — 2026-10-02

The three assigned power footprints are implemented from the manufacturer’s package, example PCB land-pattern and stencil drawings. KiCad 9.0.9 successfully loads them; the parsed copper dimensions, coordinates, solder-mask margins, paste apertures and canonical pin functions pass the automated audit. This establishes a checked footprint transcription, not assembly qualification or PCB release.

The library is [CuraLink.pretty](../../pcb/footprints/CuraLink.pretty/). [Source hashes, complete pad geometry and canonical net mappings](footprint-audit.json), [actual pcbnew loader results](footprint-loader-verification.json) and the [copper/mask/paste overlay](power-footprint-overlay.png) accompany this report. Dimensions below are in **mm**, with the footprint viewed from the PCB top, pin 1 at upper left, x positive right and y positive down.

## BQ25185 charger — U501

Use `CuraLink:BQ25185DLH_WSON10_2.2x2mm` for **BQ25185DLHR, C19725033**. TI package **DLH0010A**, drawing **4226298/A, 10/2020**, gives a nominal 2.2 × 2.0 body, 0.8 maximum height and 0.4 terminal pitch. Source: [TI BQ25185 datasheet](https://www.ti.com/lit/ds/symlink/bq25185.pdf), PDF pages 29–31; saved primary PDF and its SHA-256 are recorded in the JSON.

The ten terminal copper lands are **0.50 × 0.20**, centered at **x = ±1.05**. Pins 1–5 descend along the left side at y = −0.80, −0.40, 0, +0.40, +0.80; pins 6–10 ascend along the right side. The central **grounded EP11 is 0.90 × 1.50**. All copper pads use +0.05 mask expansion. Terminal paste follows the lands; EP11 uses the separate **0.85 × 1.38** stencil aperture shown by TI, approximately 88% rectangular-area coverage. TI’s stencil example assumes 0.125 thickness.

| Physical pad | Function | Canonical net |
|---|---|---|
| 1 | SYS | CHG_SYS |
| 2 | BAT | BAT_CHG |
| 3 | STAT2 | CHG_STAT2 |
| 4 | CE_N | CHG_CE_N |
| 5 | GND | GND |
| 6 | TS/MR | CHG_TS |
| 7 | ILIM/VSET | CHG_VSET |
| 8 | ISET | CHG_ISET |
| 9 | STAT1 | CHG_STAT1 |
| 10 | IN | CHG_IN |
| 11 | Exposed pad | GND |

KiCad’s official DLH footprint has the correct body and EP but uses IPC-style **0.75 × 0.20** terminal lands at x = ±1.10. This custom deliberately follows TI’s smaller example lands. The minimum rectangular copper gap is **0.20** and minimum mask bridge **0.10**. Keep EP11 solidly grounded; it must not become an unconnected mechanical pad. The SYS pad is charger-local CHG_SYS and must not be connected to SYS_RAW to bypass RUN isolation.

## TPS25200 eFuses — U502 and U511

Use `CuraLink:TPS25200DRV_WSON6_2x2mm` for **TPS25200DRVR, C128401**. TI package **DRV0006A**, drawing **4222173/C, 11/2025**, gives a 2.0 × 2.0 nominal body, 0.8 maximum height and 0.65 terminal pitch. Source: [TI TPS25200 datasheet](https://www.ti.com/lit/ds/symlink/tps25200.pdf), PDF pages 28–30.

The six terminal copper lands are **0.45 × 0.30**, centered at **x = ±0.975**, y = −0.65, 0, +0.65. **EP7 is 1.00 × 1.60**, grounded. The manufacturer’s +0.07 mask expansion is explicit in the footprint. EP paste consists of two **1.00 × 0.70** apertures centered at y = ±0.45, about 88% rectangular-area coverage, with the drawing’s 0.125 stencil assumption.

| Physical pad | Function | U502 net | U511 net |
|---|---|---|---|
| 1 | OUT | CHG_IN | SYS_RAW |
| 2 | ILIM | WPT_EF_ILIM | SYS_EF_ILIM |
| 3 | FAULT_N | CHG_INPUT_FAULT_N | SYS_FAULT_N |
| 4 | EN | WPT_EF_EN | RUN_ENABLE |
| 5 | GND | GND | GND |
| 6 | IN | WPT_PROTECTED | SYS_PRE |
| 7 | Exposed pad | GND | GND |

The generic KiCad `DFN-6-1EP_2x2mm_P0.65mm_EP1x1.6mm` is described for a Microchip package and has larger/differently spaced lands, so it was not copied. The actual custom has minimum rectangular copper gap **0.25** and mask bridge **0.11**. Preserve OUT1 / IN6; reversing those numbered pins would defeat the previously corrected schematic.

## Optional BQ29737 protector — U514, DNP

Use `CuraLink:BQ29737DSE_WSON6_1.5x1.5mm` for **BQ29737DSER, C3681751**. TI package **DSE0006A**, drawing **4220552/B, 01/2024**, is **six terminals with no exposed pad**. Nominal body is 1.5 × 1.5, height maximum 0.8 and pitch 0.5. Source: [TI BQ2973 datasheet](https://www.ti.com/lit/ds/symlink/bq2973.pdf), PDF pages 32–34.

Pin 1 has a **0.80 × 0.25** exposed land centered at **(−0.55, −0.50)**. Pins 2–3 have **0.70 × 0.25** exposed lands at x = −0.60 and y = 0, +0.50. Their outer exposed-land edges all align at x = −0.95; pin 1 extends farther inward. Pins 4–6 have 0.70 × 0.25 lands at x = +0.60, y = +0.50, 0, −0.50.

TI specifies **solder-mask-defined pads 1–3**, with at least 0.05 copper overlap beneath the mask. Their copper is therefore enlarged by 0.05 on each edge: pin 1 **0.90 × 0.35**, pins 2–3 **0.80 × 0.35**, each with −0.05 mask margin. That produces the exposed-land dimensions above. Copper corner radius 0.10 becomes the nominal 0.05 mask-opening radius after contraction. Pads 4–6 are non-solder-mask-defined 0.70 × 0.25 copper with +0.05 mask expansion; TI states 0.05 maximum on these pads. Six separate paste apertures match the exposed-land dimensions and positions, not the enlarged SMD copper.

| Physical pad | Function | Canonical net |
|---|---|---|
| 1 | NC | Intentionally unconnected |
| 2 | COUT | PCM_CHG_GATE |
| 3 | DOUT | PCM_DSG_GATE |
| 4 | VSS | CELLN |
| 5 | BAT | PCM_BAT |
| 6 | V− | PCM_VMINUS |

There is **no pad 7**, no ground EP and no thermal-via pattern. Actual minimum rectangular copper gap is **0.15** and mask bridge **0.15**. U514 remains DNP because its protection thresholds and fault-current behavior have not been qualified for the selected cell; footprint correctness does not close that electrical gate.

## Shared assembly and routing conditions

Courtyards are project rules: 0.25 clearance from maximum body/copper extents, rounded outward to 0.05. They are not copied from TI dimensions. Silkscreen and reference placement are also project choices; PCB DRC must check nearby components and solder-mask clearance after placement. No external 3D model or thermal vias are embedded.

TI shows optional 0.20 finished thermal-via holes at x = 0, y = ±0.50 for the DLH and ±0.55 for DRV. These are **not automatically instantiated**: open through vias under paste can drain solder. Approve filled/plugged/tented via construction, stencil and assembly-shop process before using via-in-pad. Provide short ground copper/return paths from the EP and pin GND without sending charger/eFuse load current through comparator/reference ground returns. Board thermal capacity and actual solder voiding remain physical checks.

Keep the following manufacturer pin maps when using the root’s standard footprints: TPS7A20 DBV5 **IN1/GND2/EN3/NC4/OUT5**; TLV3012B DBV6 **OUT1/GND2/IN+3/IN−4/REF5/VCC6**; SN74LVC1G17 and SN74LVC1G04 DBV5 **NC1/A2/GND3/Y4/VCC5**; DMP2035U and AO3400A **G1/S2/D3**; BAT54 **A1/NC2/K3**; BAT54C **A1=1/A2=2/common K3**. Their primary package/pin audits are retained in the [power protection audit](../../ltspice/protection-audit.md).

**SS14 needs the specific numbered footprint:** onsemi assigns **anode 1 / cathode 2**, whereas the usual KiCad `D_SMA` uses cathode 1 / anode 2. The canonical circuit already uses D501 pad 1 = WPT_RAW, pad 2 = WPT_PROTECTED. Preserve the physical cathode band over pad 2 when remapping the standard SMA footprint; do not swap only its silk mark. Source: [onsemi SS12–S100 family datasheet](https://www.onsemi.com/download/data-sheet/pdf/ss19-d.pdf), numbered symbol on page 1.

JLC placement rotation must be verified with its preview and the manufacturer pin-1 mark on the actual ordered part. Top-view coordinates and a checked pin map do not independently prove reel/centroid conventions. Review final copper, mask and paste Gerbers at these three packages before assembly approval.

# Independent CuraLink PCB validation

Checked 2026-10-02T11:57:00.763465-04:00 with native KiCad 9.0.9-9.0.9~ubuntu24.04.1.

**Status: PASS_TRANSFER_AND_STRUCTURE_WITH_ROUTING_REVIEW_OPEN.** This is an inspection result; it is not a fabrication release or completed board DRC.

| Check | Result |
|---|---|
| Expected physical references | 446 (schematic-only flags excluded) |
| Board footprints | 446 |
| Missing / extra / duplicate references | 0 / 0 / 0 |
| Connected / intentional NC pads checked | 1089 / 48 |
| Pad-transfer errors | 0 |
| Copper layers | 4 |
| Native closed-outline conversion | True |
| Same-side conservative courtyard-bound overlaps | 0 |
| Footprints with missing courtyard | 0 |
| Native unconnected ratsnest edges | 818 |

RT501 is the manually attached off-board thermistor. Its two PCB wire lands must map to pins 1 = REF_1V242 and 2 = CELL_TEMP; it is not counted as a PCB SMT thermistor.

Courtyard overlap uses axis-aligned bounding boxes on the same surface. It deliberately errs toward reporting overlap for rotated or irregular courtyards; opposite-side non-through-hole components are not treated as same-side overlaps. Native KiCad DRC must decide actual courtyard, copper, solder-mask, edge and clearance violations. Missing-courtyard bounds are a fallback warning, not a proven courtyard.

The connectivity count is the native ratsnest after rebuilding connectivity. It includes all saved physical pads/nets, including DNP footprint nets and may change after zone fill; it is not a count of schematic nets and is not evidence of routed continuity when nonzero.

Detailed reference lists, per-pin errors, footprint bounds, pad centers outside the outline, source hashes and limits are preserved in validation.json. The board and canonical source were not modified.

"""Generate the four-channel bench variant's charger-status and MCU power wiring."""
from copy import deepcopy


def apply(parts):
    """Mutate the separate build variant; the archived eight-channel map stays intact."""
    by_ref = {component["ref"]: component for component in parts}

    def connect(ref, pin, net):
        by_ref[ref]["pins"][str(pin)] = net

    def duplicate(template, ref, pins, footprint, note):
        if ref in by_ref:
            raise ValueError(f"Duplicate reference {ref}")
        item = deepcopy(by_ref[template])
        item.update(ref=ref, pins={str(i): n for i, n in enumerate(pins, 1)},
                    footprint="CuraLink:" + footprint, notes=note)
        by_ref[ref] = item
        parts.append(item)
        return item

    # The old crowbar would consume 30 mA continuously whenever charging.
    # Remove both components so the discarded drain net never enters layout.
    parts[:] = [part for part in parts if part["ref"] not in {"Q508", "R539", "R544"}]
    for ref, source in (("D610", "SYS_RAW"), ("D611", "CHG_IN")):
        duplicate("D501", ref, [source, "BLE_SOURCE_OR"], "SS14_SMA_A1K2",
                  "Protected supply OR. Pad 1 anode, pad 2 banded cathode.")
    connect("R537", 1, "BLE_SOURCE_OR")
    connect("U513", 3, "SYS_DIGITAL_IN")
    by_ref["U513"]["notes"] = "Digital LDO enabled by its own isolated input. Measure RUN dropout during RF bursts."
    for ref, pin in (("U401", 6), ("C406", 1), ("C407", 1)):
        connect(ref, pin, "DVDD_3V0")

    gate = duplicate("U508", "U610", ["RUN_ENABLE", "DIGITAL_GOOD", "GND", "AFE_ENABLE", "CTRL_3V0"],
                     "SOT-23-5", "Hardware RUN AND digital-good interlock; AFE forced off during charging.")
    gate.update(value="SN74LVC1G08DBVR", mpn="SN74LVC1G08DBVR", lcsc="C7666",
                source="https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf")
    gate["pin_names"].update({"1": "A", "2": "B"})
    gate["pin_types"]["1"] = "input"
    connect("U512", 3, "AFE_ENABLE")
    duplicate("C515", "C610", ["CTRL_3V0", "GND"], "C_0402_1005Metric", "U610 local bypass.")

    for ref, pin, status in (("R508", 10, "CHG_STAT1"), ("R509", 12, "CHG_STAT2")):
        connect(ref, 1, "DVDD_3V0")
        connect("U401", pin, status)
        by_ref[ref]["notes"] = "Open-drain charger status pulled up only to the MCU I/O rail."
    for transistor, pullup, control, sense, pin in (
        ("Q610", "R610", "FIELD_ABSENT", "RX_DC_PRESENT_MCU", 13),
        ("Q611", "R611", "CHG_CE_N", "CHG_ENABLED_MCU", 14),
    ):
        duplicate("Q507", transistor, [control, "GND", sense], "SOT-23",
                  "Inverting open-drain readback isolates always-on control from an unpowered GPIO.")
        duplicate("R508", pullup, ["DVDD_3V0", sense], "R_0402_1005Metric", "MCU-domain status pull-up.")
        connect("U401", pin, sense)
    return parts

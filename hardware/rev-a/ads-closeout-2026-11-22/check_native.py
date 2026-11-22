"""Independent pin/net review from the four-coax KiCad project's exported XML."""
from pathlib import Path
import json
import math
import re
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent


def main():
    root = ET.parse(HERE/"coax-native.xml")
    parts = {p.get("ref"): p for p in root.findall(".//components/comp")}
    pins = {(n.get("ref"), n.get("pin")): net.get("name") for net in root.findall(".//nets/net") for n in net.findall("node")}
    checked = []

    def require(ref, *pairs):
        for pin, expected in pairs:
            actual = pins.get((ref, str(pin)))
            if actual != expected:
                raise ValueError((ref, pin, expected, actual))
            checked.append(dict(ref=ref, pin=str(pin), net=actual))

    for i, esd_pad in enumerate([1,2,4,5],1):
        coax_net = pins[(f"J{600+i}","1")]
        assert coax_net.endswith(f"/COAX_CH{i}")
        require(f"J{600+i}", (2,"GND"),(3,"GND"))
        require(f"R{600+i}", (1,coax_net),(2,f"FFC_CH{i}"))
        require("U110",(esd_pad,f"FFC_CH{i}"))
        require(f"R{1001+(i-1)*18}",(1,f"FFC_CH{i}"),(2,f"CH{i}_LIMIT"))
        require(f"C{1001+(i-1)*7}",(1,f"CH{i}_LIMIT"),(2,f"CH{i}_PLUS"))
        require(f"R{1002+(i-1)*18}",(1,f"CH{i}_PLUS"),(2,"VMID"))
        require(f"R{400+i}",(1,f"AFE_OUT_{i}"),(2,f"ADC_IN_{i}"))
        require(f"C{412+i}",(1,f"ADC_IN_{i}"),(2,"GND"))
    require("U110",(3,"GND"),(8,"GND"))
    require("U112",(1,"FFC_REF"),(3,"GND"),(8,"GND"))
    require("R605",(1,"GND"),(2,"FFC_REF"))
    require("R1145",(1,"FFC_REF"),(2,"REF_LIMIT"))
    require("C1057",(1,"REF_LIMIT"),(2,"REF_PLUS"))
    require("R1146",(1,"REF_PLUS"),(2,"VMID"))
    require("R1149",(1,"VMID_BUF"),(2,"VMID"))
    require("C1058",(1,"VMID"),(2,"GND"))
    require("U401",(3,"ADC_IN_1"),(4,"ADC_IN_2"),(5,"ADC_IN_3"),(7,"ADC_IN_4"),(6,"DVDD_3V0"),
            (10,"CHG_STAT1"),(12,"CHG_STAT2"),(13,"RX_DC_PRESENT_MCU"),(14,"CHG_ENABLED_MCU"))
    require("C406",(1,"DVDD_3V0"),(2,"GND"))
    require("C407",(1,"DVDD_3V0"),(2,"GND"))
    require("D610",(1,"SYS_RAW"),(2,"BLE_SOURCE_OR"))
    require("D611",(1,"CHG_IN"),(2,"BLE_SOURCE_OR"))
    require("R537",(1,"BLE_SOURCE_OR"),(2,"SYS_DIGITAL_IN"))
    require("U513",(1,"SYS_DIGITAL_IN"),(3,"SYS_DIGITAL_IN"),(5,"DVDD_3V0"))
    require("U610",(1,"RUN_ENABLE"),(2,"DIGITAL_GOOD"),(3,"GND"),(4,"AFE_ENABLE"),(5,"CTRL_3V0"))
    require("U512",(1,"SYS_ANALOG_IN"),(3,"AFE_ENABLE"),(5,"AVDD_3V0"))
    require("R536",(1,"SYS_RAW"),(2,"SYS_ANALOG_IN"))
    require("U511",(1,"SYS_RAW"),(4,"RUN_ENABLE"),(6,"SYS_PRE"))
    require("Q501",(1,"SW_GATE"),(2,"PMOS_COMMON_SOURCE"),(3,"BAT_RUN"))
    require("Q502",(1,"SW_GATE"),(2,"PMOS_COMMON_SOURCE"),(3,"SYS_PRE"))
    require("Q503",(1,"RUN_ENABLE"),(2,"GND"),(3,"SW_GATE_PULL"))
    require("R538",(1,"AVDD_3V0"),(2,"ANALOG_DISCHARGE"))
    require("Q507",(1,"NOT_RUN"),(2,"GND"),(3,"ANALOG_DISCHARGE"))
    assert not ({"Q508","R539","R544","J301","U102","U104","U106","U108","U111"} & set(parts))
    require("D502",(1,"PACK+"),(2,"CHG_IN"),(3,"CTRL_INPUT"))
    require("U505",(1,"FIELD_ABSENT"),(3,"WPT_THRESHOLD"),(4,"WPT_SENSE"),(6,"CTRL_3V0"))
    require("R516",(1,"WPT_RAW"),(2,"WPT_SENSE"))
    require("R517",(1,"WPT_SENSE"),(2,"GND"))
    require("Q610",(1,"FIELD_ABSENT"),(2,"GND"),(3,"RX_DC_PRESENT_MCU"))
    require("Q611",(1,"CHG_CE_N"),(2,"GND"),(3,"CHG_ENABLED_MCU"))
    for pull, signal in [("R508","CHG_STAT1"),("R509","CHG_STAT2"),("R610","RX_DC_PRESENT_MCU"),("R611","CHG_ENABLED_MCU")]:
        require(pull,(1,"DVDD_3V0"),(2,signal))
    require("U501",(3,"CHG_STAT2"),(4,"CHG_CE_N"),(9,"CHG_STAT1"),(10,"CHG_IN"))
    # Independently map every physical passive and all active amplifier units
    # from the actual ADS four-coax circuit back to exported schematic nodes.
    native_deck=(HERE/"four-coax-native/afe.ckt").read_text()
    top=native_deck[native_deck.index("R:r1001 "):native_deck.index("V_Source:vinj")].splitlines()
    merged={c["ref"]:c for c in json.loads((HERE.parent/"bench-four-coax/components-merged.json").read_text())["components"]}
    multipliers={"":1,"k":1e3,"M":1e6,"u":1e-6,"n":1e-9,"p":1e-12}
    def num(value):
        # ADS netlist values use scientific notation or lowercase k; KiCad
        # values may add a unit and descriptive tolerances after the number.
        m=re.match(r"^([\d.]+(?:[eE][-+]?\d+)?)([kMunp]?)",value)
        return float(m.group(1))*multipliers[m.group(2)]
    def net(name):
        return {"0":"GND","fb_sense":"VMID_BUF"}.get(name,name.upper())
    passives=0
    units=0
    for line in top:
        m=re.fullmatch(r"(?:R|Cap_L):([rc]\d+) (\S+) (\S+) [RC]=(\S+)",line)
        if m:
            ref,one,two,value=m.groups();ref=ref.upper()
            assert sorted([pins[ref,"1"],pins[ref,"2"]])==sorted([net(one),net(two)]),ref
            assert math.isclose(num(value),num(parts[ref].findtext("value")),rel_tol=1e-8),ref
            passives+=1
        amp=re.fullmatch(r"tlv\d+_tlv\d+:x(u\d+)_(\d) (\S+) (\S+) (\S+) (\S+) (\S+)",line)
        if amp:
            ref,uid,p,n,vp,vn,o=amp.groups();ref=ref.upper()
            blocks={u["unit"]:u["pins"] for u in merged[ref]["unit_blocks"]}
            for pad,signal in zip(blocks[int(uid)]+blocks[5],[o,n,p,vp,vn]):
                assert pins[ref,pad]==net(signal),(ref,pad,signal)
            units+=1
    assert units==20 and passives>100
    result = dict(xml_component_count=len(parts), checked_pins=len(checked), checks=checked,
                  four_channel_ADS_physical_passives_value_and_endpoints=passives,
                  four_channel_ADS_five_terminal_units_pinchecked=units,
                  verify_removed=["Q508","R539","R544","J301","U102","U104","U106","U108","U111"])
    (HERE/"native-pin-checks.json").write_text(json.dumps(result,indent=2)+"\n")
    print(f"Checked {len(checked)} pin connections among {len(parts)} native references")


if __name__=="__main__":
    main()

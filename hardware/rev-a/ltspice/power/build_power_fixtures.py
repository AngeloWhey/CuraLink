"""Generate explicit datasheet-static corner fixtures; no manufacturer validation implied."""
from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
CORNERS = [
    {"name": "low", "clamp": 5.25, "ovlo": 6.8, "uvlo": 2.45, "ilim": (97399 / 1010**1.015 - 30) / 1000},
    {"name": "typ", "clamp": 5.4, "ovlo": 7.6, "uvlo": 2.35, "ilim": (98322 / 1000**1.003) / 1000},
    {"name": "high", "clamp": 5.55, "ovlo": 8.45, "uvlo": 2.35, "ilim": (96754 / 990**.985 + 30) / 1000},
]
for c in CORNERS:
    for load_name, load in [("charger", 220), ("short", 1)]:
        text = f"""* Explicit static-bound behavioral TPS25200 fixture, {c['name']} / {load_name}
* NOT TI's model: only DC UVLO/OVLO/clamp/current-limit thresholds are represented.
* R511=1.0Meg +/-1%; ILIM from datasheetEq1 approximate min/nom/max curves.
* Thermal shutdown, startup, hysteresis, recovery, reverse leakage and overshoot excluded.
* Input at WPT_PROTECTED (after D501); cannot clamp WPT_RAW/rectifier/coil/reservoir.
.param VCLAMP={c['clamp']} VOVLO={c['ovlo']} VUVLO={c['uvlo']} ILIMIT={c['ilim']} RON=.099
VIN WPT_PROTECTED 0 5
BTARGET TARGET 0 V={{if(V(WPT_PROTECTED)<VUVLO,0,if(V(WPT_PROTECTED)>VOVLO,0,min(V(WPT_PROTECTED),VCLAMP)))}}
BPASS WPT_PROTECTED CHG_IN I={{if(V(TARGET)>0,limit((V(TARGET)-V(CHG_IN))/RON,0,ILIMIT),0)}}
* IQ bound is only an illustrative input draw; published high-VIN maximum is 1.7mA at20V.
BIQ WPT_PROTECTED 0 I={{if(V(WPT_PROTECTED)>VOVLO,1.7m,if(V(WPT_PROTECTED)>VUVLO,.2m,0))}}
RLOAD CHG_IN 0 {load}
C502 CHG_IN 0 2.2u
BPOWER EFUSE_DISSIPATION_W 0 V={{max(0,(V(WPT_PROTECTED)-V(CHG_IN))*I(BPASS)+V(WPT_PROTECTED)*I(BIQ))}}
.dc VIN 0 18 .005
.meas DC max_chg MAX V(CHG_IN)
.meas DC max_current MAX I(BPASS)
.meas DC max_dissipation MAX V(EFUSE_DISSIPATION_W)
.meas DC output_5v FIND V(CHG_IN) AT=5
.meas DC output_65v FIND V(CHG_IN) AT=6.5
.meas DC output_10v FIND V(CHG_IN) AT=10
.save V(WPT_PROTECTED) V(CHG_IN) I(VIN) I(BPASS) V(EFUSE_DISSIPATION_W)
.options plotwinsize=0
.end
"""
        (BASE / f"static-ovp-{c['name']}-{load_name}.cir").write_text(text, encoding="ascii")

field = (BASE / "vendor-field-dc.cir").read_text(encoding="utf-8")
for direction, dc in [("rise", ".dc VRAW 0 18 .005"), ("fall", ".dc VRAW 18 0 -.005")]:
    (BASE / f"vendor-field-{direction}.cir").write_text(field.replace(".dc VRAW -18 18 .005", dc), encoding="utf-8")

for direction, dc in [("rise", ".dc VPACK 2.2 4.5 .001"), ("fall", ".dc VPACK 4.5 2.2 -.001")]:
    text = f"""* TI TLV3012B vendor U504 battery UVLO fixture, regulated control rail held3V.
.include "sources/tlv3012b-spice/TLV3012B/tlv3012b.LIB"
VCTRL CTRL_3V0 0 3
VPACK PACK_PLUS 0 4
R513 PACK_PLUS BAT_SENSE 1Meg
R514 BAT_SENSE 0 510k
R515 BAT_OK BAT_SENSE 10Meg
C513 BAT_SENSE 0 1n
XU504 BAT_SENSE REF_1V242 CTRL_3V0 0 BAT_OK REF_1V242 TLV3012B
RTEST BAT_OK 0 1Meg
{dc}
.save V(PACK_PLUS) V(BAT_SENSE) V(BAT_OK) V(REF_1V242)
.options plotwinsize=0
.end
"""
    (BASE / f"vendor-uvlo-{direction}.cir").write_text(text, encoding="ascii")

ldo = (BASE / "vendor-ldo-dc.cir").read_text(encoding="utf-8")
ldo = ldo.replace("VIN LDO_IN 0 4.0", "VIN LDO_IN 0 4.0 AC 1")
start = ldo.index(".dc VIN")
end = ldo.index(".save", start)
ldo = ldo[:start] + ".ac dec 100 1 10Meg\n.meas AC ripple_1k FIND mag(V(OUT)) AT=1k\n.meas AC ripple_100k FIND mag(V(OUT)) AT=100k\n.meas AC ripple_1Meg FIND mag(V(OUT)) AT=1Meg\n" + ldo[end:]
(BASE / "vendor-ldo-psrr.cir").write_text(ldo, encoding="utf-8")

(BASE / "static-corner-definitions.json").write_text(json.dumps({
    "source": "https://www.ti.com/lit/ds/symlink/tps25200.pdf",
    "section": "5.5 clamp5.25/5.4/5.55V and OVLO6.8/7.6/8.45V; Eq1 approximate current-limit curves at R511=1.0Meg +/-1%, all resistor corners within33000..1100000ohm",
    "R511_ohm": 1000000,
    "corners": CORNERS,
    "limits": "Independent numerical bounds paired for illustration, not statistical correlation. Guaranteed response timing and all-voltage clamp behavior not established. Eq1 current-limit curves are approximations, not a guaranteed production limit at1Meg. Historical1.1Meg case is archived separately.",
}, indent=2), encoding="utf-8")
print("Generated six static OVP fixtures, four vendor comparator sweeps and one vendor LDO AC fixture.")

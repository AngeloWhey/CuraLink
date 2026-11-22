"""Compose model-level charger/control input fault fixtures, without a charger macro."""
from pathlib import Path

base = Path(__file__).resolve().parent
original = (base / "vendor-efuse-transient.cir").read_text(encoding="utf-8")
control = '''
* D502 is an approximate BAT54C model, NOT a manufacturer-validated model.
* The 0.5mA control load is a declared fixture; all control logic is not simulated.
.include "models/tps7a20-namespaced.lib"
.param V_out=3.0
VPACK PACK_PLUS 0 4.1
D502A PACK_PLUS CTRL_INPUT BAT54_APPROX
D502B CHG_IN CTRL_INPUT BAT54_APPROX
.model BAT54_APPROX D(Is=74n N=1.07 Rs=5 BV=30 Ibv=1u Cjo=10p)
C506 CTRL_INPUT 0 2.2u
XU503 CTRL_INPUT 0 CTRL_INPUT NC_CTRL CTRL_3V0 TPS7A20_ADJ_TRANS
C507 CTRL_3V0 0 2.2u
RCTRL CTRL_3V0 0 6k
.meas TRAN ctrl_input_peak MAX V(CTRL_INPUT)
.meas TRAN ctrl_output_peak MAX V(CTRL_3V0)
.meas TRAN ctrl_input_5v AVG V(CTRL_INPUT) FROM 20m TO 24m
'''
original = original.replace('.save ', '.save V(CTRL_INPUT) V(CTRL_3V0) ', 1)
original = original.replace('.options plotwinsize=0', control + '\n.options plotwinsize=0')
original = original.replace('* TI TPS25200_TRANS nominal macro; DC sweep cannot establish this transient model\'s gate state.',
    '* Coupled TI-derived TPS25200 / TI TPS7A20 macros, R511=1Meg; no BQ25185 model.')
(base / 'vendor-protected-control-transient.cir').write_text(original, encoding='ascii')

fast = original
line = next(x for x in fast.splitlines() if x.startswith('VRAW '))
fast = fast.replace(line, 'VRAW WPT_RAW 0 PWL(0 0 1m 0 1.01m 5 25m 5 {25m+SLEW_S} 18 35m 18 35.01m 5 60m 5)')
start, end = fast.index('.tran '), fast.index('.save ')
fast = fast[:start] + '''* 1uF effective C501/C502 is an assumed minimum, not validated DC-bias behavior.
.step param SLEW_S list 1u 10u 1m
.tran 0 60m 0 2u
.meas TRAN chg_peak MAX V(CHG_IN)
.meas TRAN protected_peak MAX V(WPT_PROTECTED)
.meas TRAN en_peak MAX V(WPT_EF_EN)
''' + fast[end:]
fast = fast.replace('C501 WPT_PROTECTED 0 2.2u', 'C501 WPT_PROTECTED 0 1u')
fast = fast.replace('C502 CHG_IN 0 2.2u', 'C502 CHG_IN 0 1u')
(base / 'vendor-protected-control-fast-fault.cir').write_text(fast, encoding='ascii')
print('Generated coupled nominal-capacitance sequence and three minimum-capacitance slew fixtures.')

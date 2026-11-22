"""Read canonical board, apply MCU placement overrides, save a separate copy.

Run with WSL KiCad Python. All source tracks/vias are deliberately discarded in
the candidate copy; the parent rebuilds routed copper after accepting geometry.
"""
from pathlib import Path
import hashlib,json
import pcbnew
HERE=Path(__file__).resolve().parent
source=HERE.parent/'curalink-rev-a.kicad_pcb'
before=hashlib.sha256(source.read_bytes()).hexdigest()
board=pcbnew.LoadBoard(str(source))
report=json.loads((HERE/'mcu-placement-overrides.json').read_text())
byref={fp.GetReference():fp for fp in board.GetFootprints()}
for ref,row in report['overrides'].items():
    fp=byref[ref]
    fp.SetOrientationDegrees(row['rotation_deg'])
    fp.SetPosition(pcbnew.VECTOR2I(round(row['x_mm']*1e6),round(row['y_mm']*1e6)))
for item in list(board.GetTracks()):board.Remove(item)
output=HERE/'mcu-local-placement.kicad_pcb'
pcbnew.SaveBoard(str(output),board)
after=hashlib.sha256(source.read_bytes()).hexdigest()
if before!=after:raise RuntimeError('Canonical source changed during read; this script never writes that source')
print('Candidate copy saved:',output)
print('Canonical board preserved SHA256:',before)

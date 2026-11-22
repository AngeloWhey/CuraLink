"""Run KiCad CLI export/verification sequentially (Windows or WSL)."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'hardware/rev-a'
SCH = OUT / 'curalink-rev-a.kicad_sch'


def main():
    commands = [
        ['sch','export','netlist','--format','kicadxml','-o',str(OUT/'curalink-rev-a.net.xml'),str(SCH)],
        ['sch','erc','--format','json','--exit-code-violations','-o',str(OUT/'erc-report.json'),str(SCH)],
        ['sch','export','pdf','--black-and-white','-o',str(ROOT/'tmp/pdfs/schematic.pdf'),str(SCH)],
    ]
    for command in commands:
        completed = subprocess.run(['kicad-cli', *command], capture_output=True, text=True)
        print(completed.stdout.strip(), flush=True)
        if completed.stderr.strip():
            print(completed.stderr.strip(), flush=True)
        completed.check_returncode()


if __name__ == '__main__':
    main()

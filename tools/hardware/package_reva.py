"""Package the connected schematic, review and reproducible evidence portably."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'output/curalink-rev-a-handoff.zip'
FOLDERS = ['hardware/rev-a', 'procurement', 'tools/hardware', 'tools/analysis', 'docs/design']
SINGLE_FILES = ['docs/engineering-handbook.md', 'AGENTS.md', 'output/pdf/curalink-rev-a-review.pdf']
EXCLUDE_NAMES = {'erc-initial.json', 'search-script.txt', 'mcu-local-placement.kicad_pcb', 'power-local-placement.kicad_pcb'}


def main():
    paths = set()
    for directory in FOLDERS:
        paths.update(p for p in (ROOT / directory).rglob('*') if p.is_file())
    paths.update(ROOT / name for name in SINGLE_FILES if (ROOT / name).is_file())
    paths = sorted(p for p in paths if '__pycache__' not in p.parts
                   and p.name not in EXCLUDE_NAMES and p.suffix not in ('.pyc', '.tmp', '.db'))
    manifest = []
    for path in paths:
        manifest.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    header = {
        'record_date': '2026-10-02', 'timezone': 'America/New_York',
        'status': 'CANDIDATE ENGINEERING HANDOFF; NOT FABRICATION RELEASED',
        'start_here': 'hardware/rev-a/README.md',
        'editable_project': 'hardware/rev-a/curalink-rev-a.kicad_pro',
        'inventory': 'hardware/rev-a/procurement/stock-audit-2026-10-02.csv',
        'coverage': 'Corrected Rev A schematic and candidate PCB, native checks, actual LTspice DC/AC/recovery/protection/crosstalk analyses, calculations, sources and procurement; RF/electrical/assembly gates remain open; no firmware',
        'release_gates': json.loads((ROOT / 'hardware/rev-a/verification-report.json').read_text(encoding='utf-8'))['release_gates'],
        'files': manifest,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in paths:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr('HANDOFF-MANIFEST.json', json.dumps(header, indent=2) + '\n')
        archive.writestr('START-HERE.txt',
            'CuraLink Rev A - 2026-10-02\n\n'
            'Extract the complete folder tree. Begin with hardware/rev-a/README.md.\n'
            'Open hardware/rev-a/curalink-rev-a.kicad_pro in KiCad or import into Altium.\n'
            'The PDF review is under output/pdf/. BOM and dated inventory are under hardware/rev-a/.\n'
            'This is a connected schematic and candidate PCB, not a fabrication release.\n'
            'All 80 current BOM SKUs and the FFC cable were stocked for one board at the recorded check.\n'
            'Actual LTspice results and runnable decks are under hardware/rev-a/ltspice/; read its README.\n'
            'TPS25200 and SS14 physical pin maps were corrected; R511 is now 1 Mohm +/-1%. Use this refreshed handoff.\n'
            'Cell C19632326 sourcing/protection, input-loading requirement and hardware/PCB qualification remain open.\n'
            'Read hardware/rev-a/pcb/README.md for native PCB status and hardware/rev-a/signal-integrity/README.md for crosstalk evidence.\n'
            'The 80 x 74 mm geometry is provisional; RF ground/stack adaptation, shared bias coupling and fabrication qualification remain open.\n'
            'No component purchase or firmware is included.\n')
    with zipfile.ZipFile(OUTPUT) as archive:
        bad = archive.testzip()
        assert bad is None, bad
        for item in manifest:
            assert hashlib.sha256(archive.read(item['path'])).hexdigest() == item['sha256'], item['path']
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    OUTPUT.with_suffix('.zip.sha256').write_text(digest + '  ' + OUTPUT.name + '\n', encoding='ascii')
    print(json.dumps({'zip': str(OUTPUT), 'files': len(manifest) + 2,
                      'size_mb': round(OUTPUT.stat().st_size / 1e6, 2), 'sha256': digest,
                      'integrity': 'All archived file hashes and ZIP CRCs verified'}, indent=2))


if __name__ == '__main__':
    main()

"""Retain maker drawings distributed by the exact LCSC SKU; no design edits."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CODES = {'C19626860': 'stm32wba52cg-lcsc', 'C22378853': 'mlpf-wb-04d3-lcsc',
    'C6364663': 'ffc18-hyh2-lcsc', 'C843260': 'nx2016sa-lcsc',
    'C528987': 'nx3215sa-lcsc', 'C88374': 'ufl-r-smt-lcsc'}

def fetch(item):
    code, name = item
    raw = ROOT / 'procurement/raw-active-external-2026-10-02' / (code + '.json')
    data = json.loads(raw.read_text(encoding='utf-8'))['result']
    row = {'lcsc': code, 'url': data['pdfUrl'], 'product_model': data['productModel']}
    try:
        req = urllib.request.Request(data['pdfUrl'], headers={'User-Agent': 'Mozilla/5.0'})
        body = urllib.request.urlopen(req, timeout=25).read()
        if not body.startswith(b'%PDF'): raise ValueError('not a PDF')
        target = HERE / (name + '.pdf'); target.write_bytes(body)
        row.update({'file': target.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)})
    except Exception as exc: row['download_error'] = str(exc)
    return row

with ThreadPoolExecutor(max_workers=6) as pool: records = list(pool.map(fetch, CODES.items()))
(HERE/'footprint-source-manifest.json').write_text(json.dumps({'date':'2026-10-02','records':records},indent=2)+'\n')
print(json.dumps(records,indent=2))

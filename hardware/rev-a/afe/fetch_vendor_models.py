"""Fetch TI model archives, preserving original headers and files."""
from pathlib import Path
import urllib.request,zipfile,hashlib,json
OUT=Path(__file__).resolve().parent/'vendor'
OUT.mkdir(exist_ok=True)
records=[]
for label,url in [('tlv9002','https://www.ti.com/lit/zip/SBOMAL2'),
                  ('tlv9052','https://www.ti.com/lit/zip/SBOMAO0')]:
    data=urllib.request.urlopen(url,timeout=30).read()
    archive=OUT/(label+'.zip');archive.write_bytes(data)
    dest=OUT/label;dest.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            target=(dest/member.filename).resolve()
            if dest.resolve() not in target.parents and target!=dest.resolve():
                raise ValueError('Archive member escapes intended directory')
        z.extractall(dest)
    records.append(dict(label=label,url=url,sha256=hashlib.sha256(data).hexdigest(),
        files=[str(p.relative_to(OUT)) for p in dest.rglob('*') if p.is_file()]))
(OUT/'sources.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
print(json.dumps(records,indent=2))

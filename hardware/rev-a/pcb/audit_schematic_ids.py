"""Read-only saved-schematic UUID investigation; run with native KiCad Python."""
from pathlib import Path
from collections import defaultdict
import json
import re
from check_board import parse_sexpr, children, child_value, UUID_RE, REV, sha, relative

defs=defaultdict(list)
symbol_ids=defaultdict(list)
for path in sorted(REV.glob('*.kicad_sch')):
    raw=path.read_text()
    for match in re.finditer(r'\(uuid\s+"?('+UUID_RE+r')"?\s*\)',raw):
        defs[match.group(1).lower()].append({'file':relative(path),
            'line':raw.count('\n',0,match.start())+1})
    for symbol in children(parse_sexpr(path),'symbol'):
        props={x[1]:x[2]for x in children(symbol,'property')if len(x)>2}
        symbol_ids[child_value(symbol,'uuid')].append({'ref':props.get('Reference'),
            'unit':child_value(symbol,'unit'),'file':relative(path),
            'pin_UUIDs':{x[1]:child_value(x,'uuid')for x in children(symbol,'pin')}})
duplicates=[{'uuid':uid,'definitions':items,'symbol_definitions':symbol_ids.get(uid,[])}
    for uid,items in defs.items()if len(items)>1]
local=[]
for uid,items in defs.items():
    byfile=defaultdict(list)
    for item in items:byfile[item['file']].append(item)
    for file,group in byfile.items():
        if len(group)>1:local.append({'uuid':uid,'file':file,'definitions':group,
            'symbol_definitions':symbol_ids.get(uid,[])})
report={'saved_schematic_uuid_definitions':sum(map(len,defs.values())),
    'duplicate_uuid_groups':duplicates,
    'same_file_duplicate_uuid_groups':local,
    'note':'Same UUID across different hierarchy files is reported for investigation, not automatically an invalid instance; actual full hierarchy paths remain distinct. Symbol/pin namespace collisions within a sheet caused observed U109 export UUID drift.',
    'symbol_UUID_duplicate_groups':[{'uuid':uid,'symbols':x}for uid,x in symbol_ids.items()if len(x)>1],
    'sources':[{'path':relative(p),'sha256':sha(p)}for p in sorted(REV.glob('*.kicad_sch'))]}
(Path(__file__).parent/'schematic-uuid-audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'duplicate_definitions':len(duplicates),
    'duplicate_symbol_UUIDs':len(report['symbol_UUID_duplicate_groups']),
    'duplicate_details':duplicates[:15]},indent=2))

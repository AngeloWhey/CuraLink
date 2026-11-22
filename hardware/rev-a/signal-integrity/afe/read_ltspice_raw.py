"""Read LTspice ASCII or point-major binary real/complex .raw output.

Use `-ascii` for portable evidence. Binary supports real float/double and complex
double point-major records; FastAccess files are deliberately rejected. No result
is considered a simulation pass merely because this parser can read the file.
"""
from dataclasses import dataclass
from pathlib import Path
import re
import numpy as np

@dataclass
class Raw:
    metadata: dict
    names: list
    types: list
    data: np.ndarray

    def trace(self, name):
        lowered = [n.lower() for n in self.names]
        return self.data[:, lowered.index(name.lower())]

def read_raw(path):
    blob = Path(path).read_bytes()
    is_utf16 = blob.startswith(b'T\x00i\x00t\x00l\x00e\x00:')
    encoding = 'utf-16-le' if is_utf16 else 'utf-8'
    marker = None
    for mode in ['Values:', 'Binary:']:
        needle = (mode + '\n').encode(encoding)
        offset = blob.find(needle)
        if offset < 0:
            needle = (mode + '\r\n').encode(encoding)
            offset = blob.find(needle)
        if offset >= 0:
            marker = mode
            body_start = offset + len(needle)
            header = blob[:offset].decode(encoding)
            break
    if marker is None:
        raise ValueError(f'No LTspice data marker in {path}')
    pre, variables = header.rsplit('Variables:', 1)
    meta = {}
    for line in pre.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            meta[key.strip()] = value.strip()
    entries = [line.split() for line in variables.splitlines() if line.strip()]
    names, types = [x[1] for x in entries], [x[2] for x in entries]
    nvars, npoints = int(meta['No. Variables']), int(meta['No. Points'])
    if nvars != len(names):
        raise ValueError('Variable header count mismatch')
    complex_data = 'complex' in meta.get('Flags', '').lower()
    if marker == 'Values:':
        text = blob[body_start:].decode(encoding)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) != nvars * npoints:
            raise ValueError(f'Expected {nvars*npoints} value lines, found {len(lines)}')
        data = np.empty((npoints, nvars), dtype=complex if complex_data else float)
        for point in range(npoints):
            for variable in range(nvars):
                value = lines[point*nvars+variable]
                if variable == 0:
                    number, value = value.split(None, 1)
                    if int(number) != point:
                        raise ValueError('Point number mismatch')
                if complex_data:
                    parts = value.split(',')
                    data[point, variable] = complex(float(parts[0]), float(parts[1]))
                else:
                    data[point, variable] = float(value)
    else:
        if 'fastaccess' in meta.get('Flags', '').lower():
            raise ValueError('FastAccess binary is not supported; rerun with -ascii')
        payload = blob[body_start:]
        if complex_data:
            if len(payload) != npoints*nvars*16:
                raise ValueError('Unexpected complex binary byte count')
            data = np.frombuffer(payload, dtype='<c16').reshape(npoints, nvars).copy()
        elif 'double' in meta.get('Flags', '').lower():
            if len(payload) != npoints*nvars*8:
                raise ValueError('Unexpected double binary byte count')
            data = np.frombuffer(payload, dtype='<f8').reshape(npoints, nvars).copy()
        else:
            record_dtype = np.dtype([('axis', '<f8'), ('values', '<f4', (nvars-1,))])
            if len(payload) != npoints*record_dtype.itemsize:
                raise ValueError('Unexpected float binary byte count')
            records = np.frombuffer(payload, dtype=record_dtype)
            data = np.column_stack([records['axis'], records['values']])
    if not np.isfinite(data).all():
        raise ValueError('Raw contains nonfinite results')
    return Raw(meta, names, types, data)

if __name__ == '__main__':
    import sys
    raw = read_raw(sys.argv[1])
    print(raw.metadata)
    print(raw.names)
    print(raw.data[:3])

"""Build an independent LTspice reference from the existing linear AFE circuit.

This reference validates the transfer calculation in LTspice; it is explicitly
not a rail-limited manufacturer macro-model or a protection model.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'hardware/rev-a/ltspice/linear-reference'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    original = (ROOT / 'hardware/rev-a/afe/afe-channel-linear.cir').read_text(encoding='utf-8')
    lines = original.splitlines()
    lines = [line for line in lines if not line.lower().startswith(('.ac ', '.end')) or line.lower().startswith('.ends')]
    body = '\n'.join(lines)
    ac = body + '\n.save V(src) V(adc) V(cho) V(do) V(lp1o) V(lp2o)\n.ac dec 100 0.01 1Meg\n.end\n'
    dc = body.replace('Vsig src 0 AC 1', 'Vsig src 0 DC 0')
    dc += '\n.save V(src) V(chp) V(cho) V(do) V(adc)\n.dc Vsig -0.1 0.1 0.001\n.end\n'
    (OUT / 'afe-linear-ac.cir').write_text(ac, encoding='ascii')
    (OUT / 'afe-linear-dc.cir').write_text(dc, encoding='ascii')
    print('Wrote two independent linear-reference LTspice decks')


if __name__ == '__main__':
    main()

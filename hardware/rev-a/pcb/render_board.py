"""Render the saved KiCad PCB using read-only native pcbnew geometry.

Run this file with the workspace Windows Python for extraction through WSL and
PNG drawing, or with KiCad's Python and --extract-only for the geometry JSON.
No board items, positions, or routing are changed. The picture is a top-view
placement/routing snapshot, not a Gerber render or a fabrication approval.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REV = HERE.parent
MM = 1_000_000


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(p):
    return [p.x / MM, p.y / MM]


def extract(board_path, snapshot_path, checked_date=None):
    import pcbnew
    before = digest(board_path)
    board = pcbnew.LoadBoard(str(board_path))
    if board is None:
        raise RuntimeError('pcbnew could not load the board')
    placements = json.loads((HERE / 'placement-manifest.json').read_text())['placements']

    def drawing(item):
        shape = item.GetShape()
        d = {'layer': board.GetLayerName(item.GetLayer()),
             'width': item.GetWidth() / MM}
        if shape == pcbnew.SHAPE_T_SEGMENT:
            d.update(kind='line', points=[point(item.GetStart()), point(item.GetEnd())])
        elif shape == pcbnew.SHAPE_T_RECT:
            a, b = point(item.GetStart()), point(item.GetEnd())
            d.update(kind='line', points=[a, [b[0], a[1]], b, [a[0], b[1]], a])
        elif shape == pcbnew.SHAPE_T_CIRCLE:
            a, b = point(item.GetCenter()), point(item.GetEnd())
            r = math.dist(a, b)
            d.update(kind='line', points=[[a[0] + r * math.cos(t), a[1] + r * math.sin(t)]
                     for t in [i * 2 * math.pi / 80 for i in range(81)]])
        elif shape == pcbnew.SHAPE_T_ARC:
            c, s = point(item.GetCenter()), point(item.GetStart())
            r = math.dist(c, s)
            start = math.atan2(s[1] - c[1], s[0] - c[0])
            sweep = item.GetArcAngle().AsRadians()
            d.update(kind='line', points=[[c[0] + r * math.cos(start + sweep * i / 40),
                       c[1] + r * math.sin(start + sweep * i / 40)] for i in range(41)])
        else:
            return None
        return d

    footprints = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        pads = []
        for pad in fp.Pads():
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            layers = [board.GetLayerName(int(x)) for x in pad.GetLayerSet().Seq()
                      if pcbnew.IsCopperLayer(int(x))]
            if not layers:
                continue
            shape = pad.GetShape()
            names = {pcbnew.PAD_SHAPE_CIRCLE: 'circle', pcbnew.PAD_SHAPE_OVAL: 'oval',
                     pcbnew.PAD_SHAPE_RECT: 'rect', pcbnew.PAD_SHAPE_ROUNDRECT: 'roundrect'}
            pads.append({'number': pad.GetNumber(), 'net': pad.GetNetname(),
                         'center': point(pad.GetPosition()), 'size': point(pad.GetSize()),
                         'angle': pad.GetOrientationDegrees(), 'shape': names.get(shape, 'rect'),
                         'roundrect_ratio': pad.GetRoundRectRadiusRatio(), 'layers': layers,
                         'drill': point(pad.GetDrillSize())})
        graphics = []
        for item in fp.GraphicalItems():
            if hasattr(item, 'GetShape') and item.GetLayer() == pcbnew.F_Fab:
                d = drawing(item)
                if d:
                    graphics.append(d)
        fp.BuildCourtyardCaches()
        courtyard=fp.GetCourtyard(pcbnew.F_CrtYd)
        for i in range(courtyard.OutlineCount()):
            outline=courtyard.Outline(i)
            points=[point(outline.CPoint(j))for j in range(outline.PointCount())]
            if points:
                graphics.append({'layer':'F.CrtYd','width':.05,'kind':'line',
                                 'points':points+[points[0]]})
        footprints.append({'ref': ref, 'value': fp.GetValue(), 'position': point(fp.GetPosition()),
                           'angle': fp.GetOrientationDegrees(), 'pads': pads, 'graphics': graphics,
                           'group': placements.get(ref, {}).get('group', '')})
    tracks = []
    for track in board.GetTracks():
        if isinstance(track, pcbnew.PCB_VIA):
            tracks.append({'kind': 'via', 'position': point(track.GetPosition()),
                           'width': track.GetWidth(pcbnew.F_Cu) / MM, 'drill': track.GetDrillValue() / MM,
                           'net': track.GetNetname()})
        else:
            tracks.append({'kind': 'track', 'points': [point(track.GetStart()), point(track.GetEnd())],
                           'width': track.GetWidth() / MM, 'layer': board.GetLayerName(track.GetLayer()),
                           'net': track.GetNetname()})
    edges = []
    for item in board.GetDrawings():
        if hasattr(item, 'GetShape') and item.GetLayer() == pcbnew.Edge_Cuts:
            d = drawing(item)
            if d:
                edges.append(d)
    zones = []
    for zone in board.Zones():
        if not zone.GetIsRuleArea():
            continue
        poly = zone.Outline()
        for i in range(poly.OutlineCount()):
            outline = poly.Outline(i)
            zones.append({'name': zone.GetZoneName(),
                          'points': [point(outline.CPoint(j)) for j in range(outline.PointCount())]})
    after = digest(board_path)
    if before != after:
        raise RuntimeError('PCB changed during extraction; retry for a coherent snapshot')
    result = {'board': board_path.name, 'board_sha256': before,
              'observed_host_clock_local': datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds'),
              'checked_date': checked_date or datetime.now(ZoneInfo('America/New_York')).date().isoformat(),
              'checked_date_basis': 'explicit client date' if checked_date else 'host America/New_York clock',
              'kicad_version': pcbnew.Version(), 'footprints': footprints, 'tracks': tracks,
              'edges': edges, 'rule_areas': zones,
              'limits': 'Native pad/Fab/courtyard/track/via geometry; no zone fill, ratsnest, DRC or RF solution.'}
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Extracted {len(footprints)} footprints, {len(tracks)} tracks/vias, {len(zones)} rule areas.')


def draw(snapshot_path, png_path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import patches, transforms, patheffects
    data = json.loads(snapshot_path.read_text())
    fig, ax = plt.subplots(figsize=(16, 15), dpi=220)
    ax.set_aspect('equal')
    ax.set_facecolor('#f7f9fc')
    # Display only actual saved rule-area polygons; no inferred PCB exclusions.
    for area in data['rule_areas']:
        ax.add_patch(patches.Polygon(area['points'], facecolor='#ffe5e5', edgecolor='#bf4444',
                                   hatch='////', linewidth=1.1, alpha=.62, zorder=1))
    for fp in data['footprints']:
        for g in fp['graphics']:
            p = g['points']
            x, y = zip(*p)
            courtyard = 'CrtYd' in g['layer']
            ax.plot(x, y, color='#bcc7d3' if courtyard else '#506078',
                    linewidth=.35 if courtyard else .7, linestyle=':' if courtyard else '-', zorder=2)
    for t in data['tracks']:
        if t['kind'] == 'via':
            x, y = t['position']
            ax.add_patch(patches.Circle((x, y), t['width']/2, facecolor='#946a25', edgecolor='#765622', lw=.2, zorder=4))
            ax.add_patch(patches.Circle((x, y), t['drill']/2, facecolor='white', edgecolor='none', zorder=5))
        else:
            x, y = zip(*t['points'])
            ax.plot(x, y, color='#b07420' if t['layer']=='F.Cu' else '#6580af',
                    lw=max(.35, t['width']*9), alpha=.8, solid_capstyle='round', zorder=3)
    for fp in data['footprints']:
        for pad in fp['pads']:
            x, y = pad['center']; w, h = pad['size']
            color = '#e3ad4f' if 'F.Cu' in pad['layers'] else '#7f9fc8'
            if pad['shape'] == 'circle':
                patch = patches.Ellipse((x,y), w,h,facecolor=color,edgecolor='#8f621f',lw=.22,zorder=5)
            else:
                radius = min(w,h)/2 if pad['shape']=='oval' else min(w,h)*pad['roundrect_ratio'] if pad['shape']=='roundrect' else 0
                patch = patches.FancyBboxPatch((x-w/2,y-h/2),w,h,
                      boxstyle=patches.BoxStyle.Round(pad=0,rounding_size=radius),
                      facecolor=color,edgecolor='#8f621f',lw=.22,zorder=5)
            patch.set_transform(transforms.Affine2D().rotate_deg_around(x,y,-pad['angle']) + ax.transData)
            ax.add_patch(patch)
            dw,dh=pad['drill']
            if dw>0 and dh>0:
                ax.add_patch(patches.Ellipse((x,y),dw,dh,facecolor='white',edgecolor='none',zorder=6))
        x,y=fp['position']; ref=fp['ref']
        big=ref.startswith(('U','J','Y','AE','RT'))
        txt=ax.text(x,y,ref,ha='center',va='center',color='#102b50',
                    fontsize=6.5 if big else 3.7,weight='bold' if big else 'normal',zorder=10)
        txt.set_path_effects([patheffects.withStroke(linewidth=1.8,foreground='white',alpha=.95)])
    for edge in data['edges']:
        x,y=zip(*edge['points'])
        ax.plot(x,y,color='#142d48',lw=1.6,zorder=12)
    # Labels describe functional placement groups; their boxes contain no copper.
    labels=[(34,3,'AFE bank 1: protection → gain → low-pass → ADC drive'),
            (34,27,'AFE bank 2: protection → gain → low-pass → ADC drive'),
            (68,38.7,'MCU / ADC / clocks'), (68,49,'Debug / test access'), (73.5,9,'BLE RF / antenna'),
            (24,59,'Power / charging / protection'), (16,70.5,'Battery and bench access')]
    for x,y,text in labels:
        ax.text(x,y,text,fontsize=8,ha='center',va='center',color='#23405b',
                bbox=dict(facecolor='white',edgecolor='#c9d5e1',alpha=.92,pad=3),zorder=15)
    ax.annotate('6.5 × 6.5 mm\nantenna exclusion',xy=(74.7,2.5),xytext=(69.5,3.3),
                fontsize=7,color='#a32424',ha='center',va='center',weight='bold',
                arrowprops=dict(arrowstyle='->',color='#a32424',lw=.7),zorder=16)
    ax.set_xlim(-2,82); ax.set_ylim(76,-2)
    ax.set_xlabel('x (mm)');ax.set_ylabel('y (mm), top view')
    ax.set_xticks(range(0,81,5));ax.set_yticks(range(0,75,5))
    ax.grid(color='#e1e7ee',lw=.35,zorder=0)
    fig.suptitle('CuraLink Rev A — actual KiCad placement snapshot (80 × 74 mm)',
                 fontsize=15,weight='bold',y=.97)
    ax.set_title(f"Checked {data['checked_date']} ({data['checked_date_basis']})  ·  KiCad {data['kicad_version']}  ·  {len(data['footprints'])} physical references",fontsize=9,pad=11)
    fig.text(.5,.025,'Gold: copper pads / top tracks   ·   Gray: component Fab / dotted courtyard   ·   Hatched red: native rule areas\n'
                    f"Candidate PCB; routing and RF qualification pending. Saved PCB SHA-256: {data['board_sha256'][:20]}…",
             ha='center',fontsize=8,color='#3a5067')
    fig.subplots_adjust(left=.065,right=.985,bottom=.07,top=.915)
    png_path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(png_path,dpi=220,facecolor='white')
    plt.close(fig)
    print(f'Rendered {png_path}')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--board',type=Path,default=REV/'curalink-rev-a.kicad_pcb')
    p.add_argument('--snapshot',type=Path,default=HERE/'figures/board-placement-geometry.json')
    p.add_argument('--output',type=Path,default=HERE/'figures/board-placement.png')
    p.add_argument('--extract-only',action='store_true')
    p.add_argument('--draw-only',action='store_true')
    p.add_argument('--checked-date',help='Optional explicit client date, YYYY-MM-DD; the observed host clock is retained separately.')
    a=p.parse_args()
    if not a.draw_only:
        try:
            import pcbnew
            extract(a.board,a.snapshot,a.checked_date)
        except ModuleNotFoundError:
            if os.name!='nt':
                raise
            def wsl(path):
                s=str(path.resolve()).replace('\\','/')
                return '/mnt/'+s[0].lower()+s[2:]
            command=['wsl.exe','-d','Ubuntu-24.04','-e','python3',wsl(Path(__file__)),
                     '--extract-only','--board',wsl(a.board),'--snapshot',wsl(a.snapshot)]
            if a.checked_date:
                command+=['--checked-date',a.checked_date]
            subprocess.run(command,check=True)
    if not a.extract_only:
        draw(a.snapshot,a.output)
    return 0


if __name__=='__main__':
    raise SystemExit(main())

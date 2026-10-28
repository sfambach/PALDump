# Silkscreen texts of a finished board (all board-level, rebuilt on every run): board texts plus "R1 10k" per part (reference and value together).
# Runs after routing, silk does not change the copper: python3 labels.py uno|mega|nano board.kicad_pcb
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from boards import BOARDS

key, path = sys.argv[1:3]
B = BOARDS[key]
MM = pcbnew.FromMM
SKIP = {'A1', 'J1', 'H1', 'H2'}  # carry their own markings
INSIDE = ('R', 'U')  # long bodies: the label fits inside the outline
SIZE = {'R': 0.8, 'U': 1.0}


def strip_board_texts(src):
    # Removing items through the SWIG API corrupts the board in KiCad 7, so old texts are cut from the file instead.
    out, i = [], 0
    while True:
        j = src.find('\n  (gr_text ', i)
        if j < 0:
            return ''.join(out) + src[i:]
        out.append(src[i:j])
        depth, k = 0, j + 3
        while True:
            depth += {'(': 1, ')': -1}.get(src[k], 0)
            k += 1
            if depth == 0:
                break
        i = k


src = strip_board_texts(open(path).read())
open(path, 'w').write(src)
b = pcbnew.LoadBoard(path)


def text(t, x, y, size, layer=pcbnew.F_SilkS):
    s = pcbnew.PCB_TEXT(b)
    s.SetText(t)
    s.SetLayer(layer)
    s.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    s.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    s.SetTextThickness(MM(size * 0.15))
    s.SetMirrored(layer == pcbnew.B_SilkS)
    b.Add(s)


for t, x, y, sz in B['texts']:
    text(t, x, y, sz)
for t, x, y, sz in B['btexts']:
    text(t, x, y, sz, pcbnew.B_SilkS)


def short(value):
    # "MF-R020 (200 mA)" -> "200mA", "MCP23017-E/SP" -> "MCP23017"
    if '(' in value:
        return value[value.index('(') + 1:value.index(')')].replace(' ', '')
    return value.split('-')[0]


for f in b.GetFootprints():
    ref = f.GetReference()
    if ref in SKIP:
        continue
    pads = [p.GetPosition() for p in f.Pads()]
    cx = sum(p.x for p in pads) / len(pads)
    cy = sum(p.y for p in pads) / len(pads)
    first, last = pads[0], pads[-1]
    horizontal = abs(last.x - first.x) >= abs(last.y - first.y)
    kind = ref.rstrip('0123456789')
    size = SIZE.get(kind, 0.8)
    t = pcbnew.PCB_TEXT(b)
    t.SetText('%s %s' % (ref, short(f.GetValue())))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15))
    if kind in INSIDE:
        if kind == 'U':
            horizontal = not horizontal  # DIP: pin 1 and the last pin sit side by side, the body runs across
        t.SetTextAngleDegrees(0 if horizontal else 90)
        t.SetPosition(pcbnew.VECTOR2I(int(cx), int(cy)))
    else:
        bottom = f.GetBoundingBox(False, False).GetBottom()
        t.SetTextAngleDegrees(0)
        t.SetPosition(pcbnew.VECTOR2I(int(cx), int(bottom + MM(0.3 + size / 2))))
    b.Add(t)
    f.Reference().SetVisible(False)

b.Save(path)

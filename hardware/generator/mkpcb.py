import math, sys
import pcbnew
from boards import BOARDS
import json, os
UUIDS = json.load(open('/tmp/uuids-%s.json' % sys.argv[1]))
LOCAL = os.path.dirname(os.path.abspath(__file__)) + '/../lib/'

FP = '/usr/share/kicad/footprints/'
MM = pcbnew.FromMM
OUT = sys.argv[2]

B = BOARDS[sys.argv[1]]
PLACE = B['place']
BOARD = B['board']
PARTS = B['parts']

b = pcbnew.BOARD()
b.SetCopperLayerCount(2)
ds = b.GetDesignSettings()
nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetTrackWidth(MM(0.3))
nc.SetClearance(MM(0.2))
nc.SetViaDrill(MM(0.4))
nc.SetViaDiameter(MM(0.8))
ds.m_TrackMinWidth = MM(0.2)

nets = {}
def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(b, name if name in ('GND', '+5V') else '/' + name)
        b.Add(n)
        nets[name] = n
    return nets[name]

def pad(f, num):
    return [p for p in f.Pads() if p.GetNumber() == num][0]

def pos(p):
    v = p.GetPosition()
    return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)

for ref, (lib_id, value, fpid, _, conn) in PARTS.items():
    lib, name = fpid.split(':')
    libdir = (LOCAL if lib in ('arduino-library', 'atari') else FP) + lib + '.pretty'
    drop = B.get('drop', {})
    if ref in drop or ref + '_holes' in drop:
        # Variant without the ICSP header and selected mounting holes
        tmp = '/tmp/taxcart-%s-%s.pretty' % (sys.argv[1], ref)
        os.makedirs(tmp, exist_ok=True)
        keep = []
        for line in open('%s/%s.kicad_mod' % (libdir, name)):
            if any('(pad "%s" ' % n in line for n in drop.get(ref, [])):
                continue
            if '(pad "" np_thru_hole' in line and any('(at %g %g)' % h in line for h in drop.get(ref + '_holes', [])):
                continue
            keep.append(line)
        open('%s/%s.kicad_mod' % (tmp, name), 'w').write(''.join(keep))
        libdir = tmp
    f = pcbnew.FootprintLoad(libdir, name)
    f.SetFPID(pcbnew.LIB_ID(lib, name))
    f.SetReference(ref)
    f.SetPath(pcbnew.KIID_PATH('/' + UUIDS[ref]))
    f.SetValue(value)
    b.Add(f)
    kind = PLACE[ref]
    f.SetPosition(pcbnew.VECTOR2I(MM(100), MM(100)))
    if kind[0] == 'origin':
        f.SetOrientationDegrees(kind[2])
        p1 = (100, 100)
        tx, ty = kind[1]
    elif kind[0] == 'pos':
        f.SetOrientationDegrees(kind[2])
        p1 = (100, 100)
        tx, ty = kind[1]
    elif kind[0] == 'at':
        f.SetOrientationDegrees(kind[2])
        p1 = pos(pad(f, '1'))
        tx, ty = kind[1]
    else:
        (x1, y1), (x2, y2) = kind[1], kind[2]
        f.SetOrientationDegrees(0)
        a1, a2 = pos(pad(f, '1')), pos(pad(f, '2'))
        base = math.degrees(math.atan2(-(a2[1] - a1[1]), a2[0] - a1[0]))
        want = math.degrees(math.atan2(-(y2 - y1), x2 - x1))
        f.SetOrientationDegrees(round(want - base) % 360)
        p1 = pos(pad(f, '1'))
        tx, ty = x1, y1
    f.Move(pcbnew.VECTOR2I(MM(tx - p1[0]), MM(ty - p1[1])))
    for p in f.Pads():
        n = conn.get(p.GetNumber())
        if n:
            p.SetNet(net(n))
    if kind[0] == 'pads':
        got = pos(pad(f, '2'))
        assert abs(got[0] - kind[2][0]) < 0.05 and abs(got[1] - kind[2][1]) < 0.05, (ref, got, kind)

x0, y0, x1, y1 = BOARD
pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
for i in range(4):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.1))
    s.SetStart(pcbnew.VECTOR2I(MM(pts[i][0]), MM(pts[i][1])))
    s.SetEnd(pcbnew.VECTOR2I(MM(pts[(i + 1) % 4][0]), MM(pts[(i + 1) % 4][1])))
    b.Add(s)

def zone(layer):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(net('GND'))
    z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    ol = z.Outline()
    ol.NewOutline()
    m = 0.5
    for x, y in [(x0 + m, y0 + m), (x1 - m, y0 + m), (x1 - m, y1 - m), (x0 + m, y1 - m)]:
        ol.Append(MM(x), MM(y))
    b.Add(z)

if '--zones' in sys.argv:
    zone(pcbnew.F_Cu)
    zone(pcbnew.B_Cu)
b.Save(OUT)
print('saved', OUT)

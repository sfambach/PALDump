import sys, re, pcbnew
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from boards import BOARDS
from sexpr import parse, find, first
key, src, ses, out = sys.argv[1:5]
x0, y0, x1, y1 = BOARDS[key]['board']
MM = pcbnew.FromMM
b = pcbnew.LoadBoard(src)
t = parse(open(ses).read())[0]
res = first(first(t, 'routes'), 'resolution')
scale = {'um': 1e-3, 'mm': 1.0}[res[1]] / float(res[2])
P = lambda x, y: pcbnew.VECTOR2I(MM(float(x) * scale), MM(-float(y) * scale))
layers = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}
nt = nv = 0
for n in find(first(first(t, 'routes'), 'network_out'), 'net'):
    name = n[1]
    net = b.FindNet(name)
    assert net is not None, name
    for w in find(n, 'wire'):
        path = first(w, 'path')
        layer, width, coords = path[1], float(path[2]) * scale, path[3:]
        for i in range(0, len(coords) - 2, 2):
            tr = pcbnew.PCB_TRACK(b)
            tr.SetStart(P(coords[i], coords[i + 1]))
            tr.SetEnd(P(coords[i + 2], coords[i + 3]))
            tr.SetWidth(MM(width))
            tr.SetLayer(layers[layer])
            tr.SetNet(net)
            b.Add(tr)
            nt += 1
    for v in find(n, 'via'):
        m = re.search(r'_(\d+):(\d+)_um', v[1])
        via = pcbnew.PCB_VIA(b)
        via.SetPosition(P(v[2], v[3]))
        via.SetWidth(MM(int(m.group(1)) / 1000))
        via.SetDrill(MM(int(m.group(2)) / 1000))
        via.SetNet(net)
        b.Add(via)
        nv += 1
gnd = b.FindNet('GND')
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(gnd)
    z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in [(x0 + .5, y0 + .5), (x1 - .5, y0 + .5), (x1 - .5, y1 - .5), (x0 + .5, y1 - .5)]:
        ol.Append(MM(x), MM(y))
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(out)
print('tracks', nt, 'vias', nv)

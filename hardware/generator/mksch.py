# Writes the schematic: symbols from the KiCad libraries (plus ../lib), +5V/VCC/GND as power symbols, every other
# signal drawn as wires by router.py with one net label per net: python3 mksch.py shield out.kicad_sch
import copy, json, math, os, re, sys, uuid
from sexpr import parse, dump, Sym, find, first
from boards import BOARDS
from router import Router, DIRS, cell, G

B = BOARDS[sys.argv[1]]
PARTS = B['parts']
SCH = B['sch']
POWER = set(B['power'])
HERE = os.path.dirname(os.path.abspath(__file__))
LIBDIRS = {'paldump': HERE + '/../lib/', 'arduino-library': HERE + '/../lib/'}
PROJECT = B['name']
ROOT = str(uuid.uuid4())
_cache = {}


def U():
    return str(uuid.uuid4())


def lib_symbols(lib):
    if lib not in _cache:
        path = LIBDIRS.get(lib, '/usr/share/kicad/symbols/') + lib + '.kicad_sym'
        tree = parse(open(path).read())[0]
        _cache[lib] = {x[1]: x for x in find(tree, 'symbol')}
    return _cache[lib]


def flat(lib, name):
    syms = lib_symbols(lib)
    s = copy.deepcopy(syms[name])
    ext = first(s, 'extends')
    if not ext:
        return s
    base = flat(lib, ext[1])
    pname = ext[1]
    out = [Sym('symbol'), name]
    child_props = {p[1]: p for p in find(s, 'property')}
    for x in base[2:]:
        if isinstance(x, list) and x[0] == 'property':
            out.append(child_props.pop(x[1], x))
        elif isinstance(x, list) and x[0] == 'symbol':
            y = copy.deepcopy(x)
            y[1] = name + y[1][len(pname):]
            out.append(y)
        else:
            out.append(x)
    for p in child_props.values():
        out.insert(3, p)
    return out


def sym_pins(sym):
    """pin -> (unit, x, y, angle) in symbol coordinates (y up)."""
    res = {}
    for sub in find(sym, 'symbol'):
        unit = int(sub[1].rsplit('_', 2)[-2])
        for p in find(sub, 'pin'):
            at = first(p, 'at')
            res[first(p, 'number')[1]] = (max(unit, 1), float(at[1]), float(at[2]), int(float(at[3])) if len(at) > 3 else 0)
    return res


def sym_rects(sym, unit):
    out = []
    for sub in find(sym, 'symbol'):
        if int(sub[1].rsplit('_', 2)[-2]) not in (0, unit):
            continue
        for r in find(sub, 'rectangle'):
            out.append((float(first(r, 'start')[1]), float(first(r, 'start')[2]),
                        float(first(r, 'end')[1]), float(first(r, 'end')[2])))
    return out


def rot(px, py, a):
    t = math.radians(a)
    return round(px * math.cos(t) - py * math.sin(t), 3), round(px * math.sin(t) + py * math.cos(t), 3)


def eff(hide=False, justify=None, size=1.27):
    e = [Sym('effects'), [Sym('font'), [Sym('size'), size, size]]]
    if justify:
        e.append([Sym('justify'), Sym(justify)])
    if hide:
        e.append(Sym('hide'))
    return e


def prop(k, v, x, y, hide=False, justify=None):
    return [Sym('property'), k, v, [Sym('at'), x, y, 0], eff(hide, justify)]


items, libs, UUIDS = [], {}, {}
pwr_n = [0]


def place(lib_id, ref, value, fp, x, y, a=0, unit=1, pinnums=(), in_bom=True, label_at=None):
    lib, name = lib_id.split(':')
    if lib_id not in libs:
        s = flat(lib, name)
        s[1] = lib_id
        libs[lib_id] = s
    if ref.startswith('#'):
        rx, ry, vx, vy = label_at
        texts = [prop('Reference', ref, rx, ry, hide=True), prop('Value', value, vx, vy)]
    else:
        rx, ry, vx, vy = label_at
        texts = [prop('Reference', ref, rx, ry, justify='left'), prop('Value', value, vx, vy, justify='left')]
    e = [Sym('symbol'), [Sym('lib_id'), lib_id], [Sym('at'), x, y, a], [Sym('unit'), unit],
         [Sym('in_bom'), Sym('yes' if in_bom else 'no')], [Sym('on_board'), Sym('yes')], [Sym('dnp'), Sym('no')],
         [Sym('uuid'), U() if ref.startswith('#') else UUIDS.setdefault(ref, U())] if unit == 1 or ref.startswith('#')
         else [Sym('uuid'), U()],
         *texts, prop('Footprint', fp, x, y, hide=True), prop('Datasheet', '~', x, y, hide=True)]
    for n in pinnums:
        e.append([Sym('pin'), n, [Sym('uuid'), U()]])
    e.append([Sym('instances'), [Sym('project'), PROJECT, [Sym('path'), '/' + ROOT, [Sym('reference'), ref],
                                                           [Sym('unit'), unit]]]])
    items.append(e)


def power(net, x, y, out):
    """Power symbol at a pin tip, pointing away from the part (out = direction 0..3, schematic y down)."""
    pwr_n[0] += 1
    up = {0: 270, 1: 180, 2: 90, 3: 0}  # symbol rotation so that its stem points along 'out'
    a = up[out]
    if net == 'GND':
        a = (a + 180) % 360
    dx, dy = DIRS[out]
    place('power:' + net, '#PWR%02d' % pwr_n[0], net, '', x, y, a, 1, ['1'], False,
          (x, y, round(x + dx * 5.08, 2), round(y + dy * 5.08 + (1.27 if net != 'GND' else 0), 2)))


router = Router(420, 297)
netpins = {}
for ref, (lib_id, value, fp, (x, y), conn) in PARTS.items():
    lib, name = lib_id.split(':')
    sym = flat(lib, name)
    pp = sym_pins(sym)
    assert set(pp) == set(conn), (ref, sorted(set(pp) ^ set(conn)))
    a = SCH['rot'].get(ref, 0)
    units = SCH['units'].get(ref, [(x, y)])
    order = sorted(pp, key=lambda n: [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', n)])
    for u, (ux, uy) in enumerate(units, 1):
        # body: rectangles and pin tips, blocked for wires
        xs, ys = [], []
        for (x0, y0, x1, y1) in sym_rects(sym, u):
            for px, py in ((x0, y0), (x1, y1), (x0, y1), (x1, y0)):
                rx, ry = rot(px, py, a)
                xs.append(ux + rx); ys.append(uy - ry)
        for num, (pu, px, py, pa) in pp.items():
            if pu == u:
                rx, ry = rot(px, py, a)
                xs.append(ux + rx); ys.append(uy - ry)
        bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
        router.block_rect(bx0, by0 - 1.27, bx1, by1 + 1.27)
        if max(bx1 - bx0, by1 - by0) < 12:  # small part: reference and value to the right
            cy = round((by0 + by1) / 2 / 1.27) * 1.27
            lab = (bx1 + 2.54, cy - 1.27, bx1 + 2.54, cy + 1.27)
            router.block_rect(bx1 + 2.54, cy - 2.54, bx1 + 2.54 * 5, cy + 2.54)
        else:
            lab = (bx0 + 1.27, by0 - 3.81, bx0 + 1.27, by1 + 3.81)
            router.block_rect(bx0, by0 - 5.08, bx0 + 2.54 * 6, by0 - 2.54)
            router.block_rect(bx0, by1 + 2.54, bx0 + 2.54 * 8, by1 + 5.08)
        place(lib_id, ref, value, fp, ux, uy, a, u, [n for n in order if pp[n][0] == u], label_at=lab)
        for num, (pu, px, py, pa) in pp.items():
            if pu != u:
                continue
            rx, ry = rot(px, py, a)
            ax, ay = round(ux + rx, 2), round(uy - ry, 2)
            out = {0: 2, 90: 1, 180: 0, 270: 3}[(pa + a) % 360]  # pin points into the body, wires leave the other way
            net = conn[num]
            if net is None:
                items.append([Sym('no_connect'), [Sym('at'), ax, ay], [Sym('uuid'), U()]])
                router.add_pin(ax, ay, '#nc', out)
            elif net in POWER:
                power(net, ax, ay, out)
                router.add_pin(ax, ay, '#' + net, out)
                dx, dy = DIRS[out]
                router.block_rect(ax + dx * 1.27, ay + dy * 1.27, ax + dx * 5.08, ay + dy * 5.08)
            else:
                router.add_pin(ax, ay, net, out)
                netpins.setdefault(net, []).append((cell(ax, ay), out))

for i, net in enumerate(B['power']):
    x = 25.4 + i * 25.4
    place('power:PWR_FLAG', '#FLG%02d' % (i + 1), 'PWR_FLAG', '', x, 20.32, 0, 1, ['1'], False, (x, 20.32, x, 16.51))
    power(net, x, 20.32, 3 if net != 'GND' else 1)

for c, (net, out) in router.pins.items():
    if not net.startswith('#'):
        for k in (1, 2):
            router.blocked.discard((c[0] + DIRS[out][0] * k, c[1] + DIRS[out][1] * k))
import copy as _copy
base_state = (_copy.deepcopy(router.occ), _copy.deepcopy(router.nodes), _copy.deepcopy(router.edges))
order = SCH.get('order', []) + sorted((n for n in netpins if n not in SCH.get('order', [])),
                                      key=lambda n: -max(abs(a[0][0] - b[0][0]) + abs(a[0][1] - b[0][1])
                                                         for a in netpins[n] for b in netpins[n]))


def route_all(order):
    router.occ, router.nodes, router.edges = (_copy.deepcopy(x) for x in base_state)
    failed = []
    for net in order:
        pins = netpins[net]
        if len(pins) < 2:
            continue
        tree = set()
        todo = list(pins)
        start = todo.pop(0)
        while todo:
            best = None
            for p in [start] if not tree else todo:
                targets = {'tree': tree, 'pins': {c: d for c, d in (todo if not tree else []) if c != p[0]}}
                path = router.route(net, p, targets)
                if path and (best is None or len(path) < len(best[1])):
                    best = (p, path)
            if best is None:
                failed.append(net)
                break
            p, path = best
            router.commit(net, path)
            tree |= set(path)
            for q in list(todo):
                if q[0] in tree:
                    todo.remove(q)
            if p in todo:
                todo.remove(p)
    return failed


for attempt in range(12):
    failed = route_all(order)
    if not failed:
        break
    order = failed + [n for n in order if n not in failed]

for net in netpins:
    segs, junctions = router.segments(net)
    for (x1, y1), (x2, y2) in segs:
        items.append([Sym('wire'), [Sym('pts'), [Sym('xy'), round(x1, 2), round(y1, 2)], [Sym('xy'), round(x2, 2), round(y2, 2)]],
                      [Sym('stroke'), [Sym('width'), 0], [Sym('type'), Sym('default')]], [Sym('uuid'), U()]])
    for x, y in junctions:
        items.append([Sym('junction'), [Sym('at'), round(x, 2), round(y, 2)], [Sym('diameter'), 0], [Sym('color'), 0, 0, 0, 0],
                      [Sym('uuid'), U()]])
    # one name per net, on a horizontal piece, never on a crossing (a label there would join both nets)
    spots = []
    for (x1, y1), (x2, y2) in segs:
        if y1 != y2:
            continue
        cy = round(y1 / G)
        for cx in range(round(min(x1, x2) / G) + 1, round(max(x1, x2) / G)):
            run = 0
            while cx + run <= round(max(x1, x2) / G) and not router._foreign((cx + run, cy), net) and run < 8:
                run += 1
            spots.append((run, -cx, (cx * G, y1)))
    if spots:
        lx, ly = max(spots)[2]
        items.append([Sym('label'), net, [Sym('at'), round(lx, 2), round(ly, 2), 0], eff(justify='left', size=1.0),
                      [Sym('uuid'), U()]])
    else:
        print('no label spot', net)

texts = [[Sym('text'), B['note'], [Sym('at'), 76.2, 265, 0], eff(justify='left'), [Sym('uuid'), U()]]]
sch = [Sym('kicad_sch'), [Sym('version'), 20230121], [Sym('generator'), Sym('eeschema')], [Sym('uuid'), ROOT],
       [Sym('paper'), 'A3'],
       [Sym('title_block'), [Sym('title'), B['title']], [Sym('date'), '2026-10-28'], [Sym('rev'), '0.1'],
        [Sym('company'), 'fambach.net']],
       [Sym('lib_symbols')] + list(libs.values())] + items + texts + [
       [Sym('sheet_instances'), [Sym('path'), '/', [Sym('page'), '1']]]]
open(sys.argv[2], 'w').write(dump(sch) + '\n')
json.dump(UUIDS, open('/tmp/uuids-%s.json' % sys.argv[1], 'w'))
print('ok', len(items), 'unrouted', failed)
sys.exit(1 if failed else 0)

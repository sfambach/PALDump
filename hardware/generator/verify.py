import sys
from sexpr import parse, find, first
from boards import BOARDS
PARTS = BOARDS[sys.argv[1]]['parts']
t = parse(open(sys.argv[2]).read())[0]
nets = first(t, 'nets')
got = {}
for n in find(nets, 'net'):
    name = first(n, 'name')[1].lstrip('/')
    for nd in find(n, 'node'):
        got[(first(nd, 'ref')[1], first(nd, 'pin')[1])] = name
err = 0
for ref, (l, v, f, p, conn) in PARTS.items():
    for pin, net in conn.items():
        g = got.get((ref, pin))
        if net is None:
            if g and not g.startswith('unconnected'):
                print('NC mismatch', ref, pin, g); err += 1
        elif g != net:
            print('mismatch', ref, pin, net, g); err += 1
print('errors', err, 'nets', len(find(nets, 'net')))
sys.exit(1 if err else 0)

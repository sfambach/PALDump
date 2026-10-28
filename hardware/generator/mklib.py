# Writes ../lib/paldump.kicad_sym: the 24-pin ZIF socket with the role of each contact for a 20-pin PAL (inserted
# flush with pin 1) and a 24-pin PAL, e.g. "I9 / GND" on contact 10.
import os
from sexpr import dump, Sym

NAMES = {1: 'I1/I0', 2: 'I2/I1', 3: 'I3/I2', 4: 'I4/I3', 5: 'I5/I4', 6: 'I6/I5', 7: 'I7/I6', 8: 'I8/I7', 9: 'I9/I8',
         10: 'GND/I9', 11: '-/I10', 12: 'GND', 13: '-/I13', 14: '-/I11', 15: 'I10/O1', 16: 'O1/IO2', 17: 'IO2/IO3',
         18: 'IO3/IO4', 19: 'IO4/IO5', 20: 'IO5/IO6', 21: 'IO6/IO7', 22: 'IO7/O8', 23: 'O8/I12', 24: 'VCC'}
TYPES = {12: 'power_in', 24: 'power_in'}


def font(size=1.27):
    return [Sym('effects'), [Sym('font'), [Sym('size'), size, size]]]


def pin(num, x, y, ang):
    return [Sym('pin'), Sym(TYPES.get(num, 'bidirectional')), Sym('line'), [Sym('at'), x, y, ang], [Sym('length'), 2.54],
            [Sym('name'), NAMES[num], font(1.0)], [Sym('number'), str(num), font(1.0)]]


def prop(k, v, x, y, hide=False):
    e = font()
    if hide:
        e.append(Sym('hide'))
    return [Sym('property'), k, v, [Sym('at'), x, y, 0], e]


pins = [pin(n, -12.7, 13.97 - 2.54 * (n - 1), 0) for n in range(1, 13)]
pins += [pin(n, 12.7, 13.97 - 2.54 * (24 - n), 180) for n in range(13, 25)]
sym = [Sym('symbol'), 'ZIF24_PAL', [Sym('in_bom'), Sym('yes')], [Sym('on_board'), Sym('yes')],
       prop('Reference', 'U', 0, 17.78), prop('Value', 'ZIF24_PAL', 0, -17.78),
       prop('Footprint', '', 0, 0, True), prop('Datasheet', '~', 0, 0, True),
       [Sym('symbol'), 'ZIF24_PAL_0_1', [Sym('rectangle'), [Sym('start'), -10.16, 16.51], [Sym('end'), 10.16, -16.51],
                                         [Sym('stroke'), [Sym('width'), 0.254], [Sym('type'), Sym('default')]],
                                         [Sym('fill'), [Sym('type'), Sym('background')]]]],
       [Sym('symbol'), 'ZIF24_PAL_1_1', *pins]]
lib = [Sym('kicad_symbol_lib'), [Sym('version'), 20220914], [Sym('generator'), Sym('kicad_symbol_editor')], sym]
out = os.path.dirname(os.path.abspath(__file__)) + '/../lib/paldump.kicad_sym'
open(out, 'w').write(dump(lib) + '\n')
print('ok', out)

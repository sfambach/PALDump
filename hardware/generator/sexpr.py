import re

class Sym(str):
    pass

TOK = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)', re.S)

def parse(text):
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = TOK.match(text, pos)
        if not m:
            if text[pos:].strip() == '':
                break
            raise ValueError(text[pos:pos + 50])
        pos = m.end()
        t = m.group(1)
        if t == '(':
            stack.append([])
        elif t == ')':
            e = stack.pop()
            stack[-1].append(e)
        elif t.startswith('"'):
            stack[-1].append(t[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            stack[-1].append(Sym(t))
    return stack[0]

def q(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

def dump(e, ind=0):
    if isinstance(e, list):
        if all(not isinstance(x, list) for x in e):
            return '(' + ' '.join(dump(x) for x in e) + ')'
        parts = []
        head = []
        for x in e:
            if not isinstance(x, list) and not parts:
                head.append(dump(x))
            else:
                parts.append(x)
        s = '(' + ' '.join(head)
        for p in parts:
            s += '\n' + '  ' * (ind + 1) + dump(p, ind + 1)
        return s + ')'
    if isinstance(e, Sym):
        return str(e)
    if isinstance(e, bool):
        return 'yes' if e else 'no'
    if isinstance(e, (int, float)):
        return fmt(e)
    return q(e)

def fmt(v):
    if isinstance(v, int):
        return str(v)
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s

def find(e, key):
    return [x for x in e if isinstance(x, list) and x and x[0] == key]

def first(e, key):
    r = find(e, key)
    return r[0] if r else None

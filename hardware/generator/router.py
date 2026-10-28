# Orthogonal wire router for generated schematics: every signal is drawn as a wire (Stefan finds label-only schematics
# hard to read). Grid 1.27 mm, Dijkstra per net with bend and crossing costs; wires of different nets may only cross at
# right angles, never touch, run along each other or pass a pin. The netlist check (verify.py) is the safety net.
import heapq

G = 1.27
DIRS = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}  # schematic y points down
BEND, CROSS, NEAR = 6, 4, 2


def cell(x, y):
    return round(x / G), round(y / G)


class Router:
    def __init__(self, w, h):
        self.w, self.h = round(w / G), round(h / G)
        self.blocked = set()
        self.pins = {}          # cell -> net (pin tips)
        self.occ = {}           # cell -> {net: set(axis)}  axis 0 = horizontal, 1 = vertical
        self.nodes = {}         # cell -> net (bends, ends, junctions: may not be crossed)
        self.edges = {}         # net -> set of frozenset(cell pair)

    def block_rect(self, x0, y0, x1, y1):
        a, b = cell(min(x0, x1), min(y0, y1))
        c, d = cell(max(x0, x1), max(y0, y1))
        for i in range(a, c + 1):
            for j in range(b, d + 1):
                self.blocked.add((i, j))

    def add_pin(self, x, y, net, out_dir):
        c = cell(x, y)
        self.pins[c] = (net, out_dir)
        self.blocked.discard(c)

    def free_for(self, c, net):
        if c in self.blocked:
            return False
        if not (0 <= c[0] < self.w and 0 <= c[1] < self.h):
            return False
        p = self.pins.get(c)
        return p is None or p[0] == net

    def route(self, net, start, targets):
        """start: (cell, out_dir); targets: cells of the own tree (any entry) or pin cells (entry only against out_dir)."""
        sc, sd = start
        tree = targets['tree']
        pin_t = targets['pins']
        dist = {}
        pq = []
        first = (sc[0] + DIRS[sd][0], sc[1] + DIRS[sd][1])
        if not self.free_for(first, net):
            return None
        goals = list(tree) + list(pin_t)
        if not goals:
            return None
        gx0, gx1 = min(g[0] for g in goals), max(g[0] for g in goals)
        gy0, gy1 = min(g[1] for g in goals), max(g[1] for g in goals)

        def h(c):
            return max(gx0 - c[0], 0, c[0] - gx1) + max(gy0 - c[1], 0, c[1] - gy1)

        heapq.heappush(pq, (1 + h(first), 1, first, sd, (sc,)))
        while pq:
            _, cost, c, d, path = heapq.heappop(pq)
            key = (c, d)
            if key in dist:
                continue
            dist[key] = cost
            path = path + (c,)
            if c in tree and self._can_join(c, net):
                return path
            if c in pin_t and (pin_t[c] + 2) % 4 == d:
                return path
            if c in self.pins:
                continue  # own pin tip of another branch, reachable only as target
            for nd in range(4):
                if nd == (d + 2) % 4:
                    continue
                n = (c[0] + DIRS[nd][0], c[1] + DIRS[nd][1])
                if not self.free_for(n, net):
                    continue
                step = 1 + (BEND if nd != d else 0)
                if nd != d and self._foreign(c, net):
                    continue  # no bend on a crossing
                o = self._foreign(n, net)
                if o:
                    axis = nd % 2
                    if any(axis in ax or len(ax) > 1 for ax in o.values()):
                        continue
                    if self.nodes.get(n, net) != net:
                        continue
                    step += CROSS
                step += NEAR * self._near(n, net, nd % 2)
                heapq.heappush(pq, (cost + step + h(n), cost + step, n, nd, path))
        return None

    def _foreign(self, c, net):
        o = self.occ.get(c)
        if not o:
            return None
        o = {k: v for k, v in o.items() if k != net}
        return o or None

    def _can_join(self, c, net):
        return not self._foreign(c, net)

    def _near(self, c, net, axis):
        n = 0
        side = [(0, 1), (0, -1)] if axis == 0 else [(1, 0), (-1, 0)]
        for dx, dy in side:
            o = self._foreign((c[0] + dx, c[1] + dy), net)
            if o and any(axis in ax for ax in o.values()):
                n += 1
        return n

    def commit(self, net, path):
        es = self.edges.setdefault(net, set())
        for a, b in zip(path, path[1:]):
            es.add(frozenset((a, b)))
            axis = 0 if a[1] == b[1] else 1
            for c in (a, b):
                self.occ.setdefault(c, {}).setdefault(net, set()).add(axis)
        for i, c in enumerate(path):
            if i in (0, len(path) - 1):
                self.nodes[c] = net
            else:
                p, q = path[i - 1], path[i + 1]
                if (p[0] == c[0]) != (q[0] == c[0]):
                    self.nodes[c] = net

    def segments(self, net):
        """Straight wire pieces, split at bends, T-joints and pins; plus junction points."""
        es = self.edges.get(net, set())
        adj = {}
        for e in es:
            a, b = tuple(e)
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)

        def is_vertex(c):
            n = adj[c]
            if len(n) != 2 or c in self.pins:
                return True
            a, b = tuple(n)
            return not (a[0] == b[0] == c[0] or a[1] == b[1] == c[1])

        segs, seen = [], set()
        for c in adj:
            if not is_vertex(c):
                continue
            for n in adj[c]:
                e = frozenset((c, n))
                if e in seen:
                    continue
                prev, cur = c, n
                seen.add(e)
                while not is_vertex(cur):
                    nxt = [x for x in adj[cur] if x != prev][0]
                    seen.add(frozenset((cur, nxt)))
                    prev, cur = cur, nxt
                segs.append(((c[0] * G, c[1] * G), (cur[0] * G, cur[1] * G)))
        junctions = [(c[0] * G, c[1] * G) for c, n in adj.items() if len(n) >= 3 or (c in self.pins and len(n) >= 2)]
        return segs, junctions

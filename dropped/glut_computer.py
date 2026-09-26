"""Discrete-time threshold neurons with non-negative weights only (ГЛУТ-only).
Verifies every circuit used in chapter 2: gates, monotonicity, dual-rail full adder,
ripple-carry adder, gated latch, clock ring and a 4-bit counter.
Run: python3 figures/glut_computer.py"""
import itertools

class Net:
    def __init__(self):
        self.th = {}; self.inp = {}; self.state = {}; self.ext = {}
    def neuron(self, name, theta, inputs=()):
        self.th[name] = theta; self.inp[name] = list(inputs); self.state[name] = 0
    def connect(self, name, src, w=1):
        assert w >= 0, "ГЛУТ: only non-negative weights"
        self.inp[name].append((src, w))
    def val(self, x):
        return self.state[x] if x in self.state else self.ext.get(x, 0)
    def step(self):
        new = {n: int(sum(w*self.val(s) for s, w in self.inp[n]) >= self.th[n]) for n in self.th}
        self.state = new
    def count(self): return len(self.th)

def full_adder(net, p, a, b, c, na, nb, nc):
    """dual-rail full adder; returns (s, ns, carry, ncarry). depth 2, 8 neurons"""
    for pre, (x, y, z) in (("", (a, b, c)), ("n", (na, nb, nc))):
        net.neuron(p+pre+"OR", 1, [(x,1),(y,1),(z,1)])
        net.neuron(p+pre+"MAJ", 2, [(x,1),(y,1),(z,1)])
        net.neuron(p+pre+"AND", 3, [(x,1),(y,1),(z,1)])
    net.neuron(p+"S", 2, [(p+"OR",1),(p+"nMAJ",1),(p+"AND",2)])
    net.neuron(p+"nS", 2, [(p+"nOR",1),(p+"MAJ",1),(p+"nAND",2)])
    return p+"S", p+"nS", p+"MAJ", p+"nMAJ"

# ---------- 1. full adder truth table (inputs held, read after 2 steps)
n = Net(); s, ns, c, nc = full_adder(n, "", "a", "b", "c", "na", "nb", "nc")
for a, b, cc in itertools.product((0,1), repeat=3):
    n.ext = dict(a=a, b=b, c=cc, na=1-a, nb=1-b, nc=1-cc)
    for _ in range(3): n.step()
    tot = a+b+cc
    assert (n.val(s), n.val(ns), n.val(c), n.val(nc)) == (tot % 2, 1-tot % 2, tot//2, 1-tot//2)
print("full adder OK, neurons:", n.count())

# ---------- 2. monotonicity check of a random ГЛУТ net (exhaustive over inputs)
import random
random.seed(1)
for trial in range(200):
    net = Net(); ins = [f"x{i}" for i in range(4)]
    names = [f"n{i}" for i in range(6)]
    for i, nm in enumerate(names):
        srcs = random.sample(ins + names[:i], k=min(3, len(ins)+i))
        net.neuron(nm, random.randint(1, 3), [(s_, random.randint(0, 2)) for s_ in srcs])
    out = {}
    for bits in itertools.product((0,1), repeat=4):
        for k in net.state: net.state[k] = 0
        net.ext = dict(zip(ins, bits))
        for _ in range(8): net.step()
        out[bits] = tuple(net.state[k] for k in names)
    for x in out:
        for y in out:
            if all(p <= q for p, q in zip(x, y)):
                assert all(p <= q for p, q in zip(out[x], out[y]))
print("monotonicity OK on 200 random nets")

# ---------- 3. 4-bit ripple adder settle time
N = 4
n = Net(); carry, ncarry = "c0", "nc0"
S = []
for i in range(N):
    s, ns, carry, ncarry = full_adder(n, f"b{i}_", f"a{i}", f"y{i}", carry, f"na{i}", f"ny{i}", ncarry)
    S.append((s, ns))
worst = 0
for A in range(16):
    for B in range(16):
        for k in n.state: n.state[k] = 0
        ext = {"c0": 0, "nc0": 1}
        for i in range(N):
            ext.update({f"a{i}": A>>i&1, f"na{i}": 1-(A>>i&1), f"y{i}": B>>i&1, f"ny{i}": 1-(B>>i&1)})
        n.ext = ext
        for t in range(1, 12):
            n.step()
            val = sum(n.val(S[i][0]) << i for i in range(N))
            ok = all(n.val(S[i][0]) + n.val(S[i][1]) == 1 for i in range(N)) and val == (A+B) % 16
            if ok and t > worst:
                # check it stays settled
                pass
        # settled value
        assert sum(n.val(S[i][0]) << i for i in range(N)) == (A+B) % 16
# measure settle time for worst case carry chain 1111+0001
for k in n.state: n.state[k] = 0
n.ext.update({f"a{i}":1 for i in range(N)}); n.ext.update({f"na{i}":0 for i in range(N)})
n.ext.update({"y0":1,"ny0":0}); n.ext.update({f"y{i}":0 for i in range(1,N)}); n.ext.update({f"ny{i}":1 for i in range(1,N)})
hist = []
for t in range(1, 10):
    n.step(); hist.append(sum(n.val(S[i][0]) << i for i in range(N)))
print("4-bit adder OK; 15+1 output by step:", hist, "neurons:", n.count())

# ---------- 4. counter: clock ring + control + registers A,T + incrementer
def latch(net, p, d, nd, h, e):
    """dual-rail gated latch cell, 3 neurons per rail; returns (q, nq)"""
    for pre, dd in (("", d), ("n", nd)):
        net.neuron(p+pre+"H", 2, [(p+pre+"q",1),(h,1)])
        net.neuron(p+pre+"W", 2, [(dd,1),(e,1)])
        net.neuron(p+pre+"q", 1, [(p+pre+"H",1),(p+pre+"W",1)])
    return p+"q", p+"nq"

L = 16
net = Net()
for k in range(L): net.neuron(f"R{k}", 1, [(f"R{(k-1)%L}", 1)])
net.neuron("ONE", 1, [("ONE", 1)])                       # constant-1 source
WT, WA = (8, 9), (12, 13)                                # write windows (ring phases)
net.neuron("eT", 1, [(f"R{k}",1) for k in WT]); net.neuron("hT", 1, [(f"R{k}",1) for k in range(L) if k not in WT])
net.neuron("eA", 1, [(f"R{k}",1) for k in WA]); net.neuron("hA", 1, [(f"R{k}",1) for k in range(L) if k not in WA])
carry, ncarry = "ONE", "ZERO"                            # carry-in = 1 ; ZERO is a silent line
A = [(f"A{i}_q", f"A{i}_nq") for i in range(N)]
T = [(f"T{i}_q", f"T{i}_nq") for i in range(N)]
for i in range(N):
    s, ns, carry, ncarry = full_adder(net, f"F{i}_", A[i][0], "ZERO", carry, A[i][1], "ONE", ncarry)
    latch(net, f"T{i}_", s, ns, "hT", "eT")
for i in range(N):
    latch(net, f"A{i}_", T[i][0], T[i][1], "hA", "eA")
# initial conditions: one spike in the ring, ONE on, A = 0 (negative rails on), T = 0, holds on
net.state["R0"] = 1; net.state["ONE"] = 1
for i in range(N):
    for r in ("A", "T"):
        net.state[f"{r}{i}_nq"] = 1; net.state[f"{r}{i}_nH"] = 1
net.state["hT"] = net.state["hA"] = 1
reads = []
for t in range(L*20):
    net.step()
    if t % L == L-1:
        ok = all(net.state[A[i][0]] + net.state[A[i][1]] == 1 for i in range(N))
        reads.append(sum(net.state[A[i][0]] << i for i in range(N)) if ok else None)
print("counter reads each clock cycle:", reads)
assert reads == [(k+1) % 16 for k in range(20)], reads
print("counter OK; neurons:", net.count(), " ring:", L, " registers:", 2*N*6, " adder:", N*8)

# ---------- 5. settle time of the 4-bit adder, worst ripple 7+1 = 8
n = Net(); carry, ncarry = "c0", "nc0"; S = []
for i in range(N):
    s, ns, carry, ncarry = full_adder(n, f"b{i}_", f"a{i}", f"y{i}", carry, f"na{i}", f"ny{i}", ncarry)
    S.append((s, ns))
A_, B_ = 7, 1
n.ext = {"c0": 0, "nc0": 1}
for i in range(N):
    n.ext.update({f"a{i}": A_>>i&1, f"na{i}": 1-(A_>>i&1), f"y{i}": B_>>i&1, f"ny{i}": 1-(B_>>i&1)})
hist = []
for t in range(1, 9):
    n.step()
    hist.append(sum(n.val(S[i][0]) << i for i in range(N)))
print("7+1 sum after each step:", hist)

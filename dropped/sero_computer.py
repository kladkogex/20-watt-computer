"""SERO-only computer: threshold neurons whose input signs are chosen by the receiver
(excitatory or inhibitory serotonin receptor) and which may be tonic pacemakers (bias).
y_i(t+1) = [ sum_j w_ij y_j(t) + b_i >= theta_i ],  w_ij in Z (any sign), b_i >= 0.
Verifies NOT/NOR, 2-neuron full adder, 3-neuron memory bit, self-starting clock, counter.
Run: python3 figures/sero_computer.py"""
import itertools

class Net:
    def __init__(self): self.th, self.b, self.inp, self.state, self.ext = {}, {}, {}, {}, {}
    def neuron(self, name, theta, inputs=(), bias=0):
        self.th[name] = theta; self.b[name] = bias; self.inp[name] = list(inputs); self.state[name] = 0
    def val(self, x): return self.state[x] if x in self.state else self.ext.get(x, 0)
    def step(self):
        self.state = {n: int(sum(w*self.val(s) for s, w in self.inp[n]) + self.b[n] >= self.th[n]) for n in self.th}
    def count(self): return len(self.th)

# NOT and NOR: pacemaker (bias = threshold) with inhibitory inputs
n = Net(); n.neuron("NOT", 1, [("x", -1)], bias=1); n.neuron("NOR", 1, [("x", -1), ("y", -1)], bias=1)
for x, y in itertools.product((0, 1), repeat=2):
    n.ext = dict(x=x, y=y); n.step()
    assert n.state["NOT"] == 1-x and n.state["NOR"] == int(not (x or y))
print("NOT, NOR OK")

def full_adder(net, p, a, b, c):
    net.neuron(p+"MAJ", 2, [(a,1),(b,1),(c,1)])
    net.neuron(p+"S", 1, [(a,1),(b,1),(c,1),(p+"MAJ",-2)])
    return p+"S", p+"MAJ"

# full adder: inputs held, sum needs MAJ from the previous step
n = Net(); s, c = full_adder(n, "", "a", "b", "c")
for a, b, cc in itertools.product((0, 1), repeat=3):
    n.ext = dict(a=a, b=b, c=cc)
    for _ in range(3): n.step()
    assert (n.state[s], n.state[c]) == ((a+b+cc) % 2, (a+b+cc)//2), (a, b, cc)
print("full adder OK, neurons:", n.count())

# 4-bit ripple adder: exhaustive, and settle time for 7+1
N = 4
def adder(net):
    carry = "c0"; S = []
    for i in range(N):
        s, carry = full_adder(net, f"F{i}_", f"a{i}", f"y{i}", carry); S.append(s)
    return S
for A in range(16):
    for B in range(16):
        n = Net(); S = adder(n)
        n.ext = {"c0": 0, **{f"a{i}": A>>i&1 for i in range(N)}, **{f"y{i}": B>>i&1 for i in range(N)}}
        for _ in range(3*N+3): n.step()
        assert sum(n.state[S[i]] << i for i in range(N)) == (A+B) % 16
n = Net(); S = adder(n); n.ext = {"c0": 0, **{f"a{i}": 7>>i&1 for i in range(N)}, **{f"y{i}": 1>>i&1 for i in range(N)}}
hist = []
for t in range(12):
    n.step(); hist.append(sum(n.state[S[i]] << i for i in range(N)))
print("4-bit adder OK, neurons:", n.count(), " 7+1 by step:", hist)

# memory bit: H = q AND NOT e ; W = d AND e ; q = H OR W   (3 neurons, no hold line)
def latch(net, p, d, e):
    net.neuron(p+"H", 1, [(p+"q", 1), (e, -1)])
    net.neuron(p+"W", 2, [(d, 1), (e, 1)])
    net.neuron(p+"q", 1, [(p+"H", 1), (p+"W", 1)])
    return p+"q"

# self-starting clock: Johnson ring of K relays with one inverting stage; 2K phases
K = 8
def johnson(net):
    # inverting stage, self-correcting: J0 = [J0 - 2 J3 - 2 J7 + 2 >= 1] (pacemaker with inhibition)
    net.neuron("J0", 1, [("J0", 1), (f"J{K//2-1}", -2), (f"J{K-1}", -2)], bias=2)
    for k in range(1, K): net.neuron(f"J{k}", 1, [(f"J{k-1}", 1)])
n = Net(); johnson(n); seq = []
for t in range(4*K):
    n.step(); seq.append("".join(str(n.state[f"J{k}"]) for k in range(K)))
period = next(p for p in range(1, 3*K) if seq[K+p] == seq[K])
print("Johnson clock from silence, period", period, ":", seq[:2*K+1])

# counter: A <- A+1 each cycle, via T (two-phase), control decoded from the Johnson ring
def window(net, name, first):
    """active on ring phases first, first+1 of 2K (phase = steps since all-zero, mod 2K)"""
    # phase p<K: bits 0..p are 1 ; phase p>=K: bits 0..p-K are 0, rest 1
    def bit(p, k): return int(k <= p) if p < K else int(k > p-K)
    pats = [tuple(bit(p, k) for k in range(K)) for p in range(2*K)]
    want = {first % (2*K), (first+1) % (2*K)}
    # find two ring bits (i, j) with pattern i=1, j=0 exactly on the wanted phases
    for i in range(K):
        for j in range(K):
            if i != j and {p for p in range(2*K) if pats[p][i] == 1 and pats[p][j] == 0} == want:
                net.neuron(name, 2, [(f"J{i}", 1), (f"J{j}", -1)], bias=1); return (i, j)
    for i in range(K):
        for j in range(K):
            if i != j and {p for p in range(2*K) if pats[p][i] == 0 and pats[p][j] == 1} == want:
                net.neuron(name, 2, [(f"J{i}", -1), (f"J{j}", 1)], bias=1); return (i, j)
    raise ValueError(want)

net = Net(); johnson(net)
net.neuron("ONE", 1, [], bias=1)                                       # pacemaker constant 1
wT = window(net, "eT", 8); wA = window(net, "eA", 12)
carry = "ONE"; A = [f"A{i}_q" for i in range(N)]
for i in range(N):
    s, carry = full_adder(net, f"F{i}_", A[i], "ZERO", carry)
    latch(net, f"T{i}_", s, "eT")
for i in range(N):
    latch(net, f"A{i}_", f"T{i}_q", "eA")
reads = []
for t in range(2*K*22):
    net.step()
    if t % (2*K) == 2*K-1: reads.append(sum(net.state[A[i]] << i for i in range(N)))
print("counter reads per cycle:", reads)
first = reads.index(1)
assert reads[first:first+18] == [(k+1) % 16 for k in range(18)], reads
print("counter OK from silence; neurons:", net.count(), " windows:", wT, wA,
      " ring:", K, " registers:", 2*N*3, " adder:", 2*N)

# clock recovers from ANY state
import itertools
n = Net(); johnson(n)
ref = []
for t in range(2*K): n.step(); ref.append(tuple(n.state[f"J{k}"] for k in range(K)))
valid = set(ref); worst = 0
for st in itertools.product((0, 1), repeat=K):
    for k in range(K): n.state[f"J{k}"] = st[k]
    for t in range(100):
        if tuple(n.state[f"J{k}"] for k in range(K)) in valid: worst = max(worst, t); break
        n.step()
    else: raise AssertionError(st)
print("self-correcting clock: every one of 256 states recovers within", worst, "steps")

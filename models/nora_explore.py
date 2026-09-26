"""Two options; on each trial, with probability h (hazard), both reward probabilities are
re-drawn uniformly from [0,1].  Values Q learn from the chosen option: Q_c += eta*(R - Q_c).
Choice P(A) = 1/(1+exp(-g (Q_A - Q_B))).  Scan fixed gain g for several hazards;
then test surprise-driven gain in a world that alternates calm and volatile epochs."""
import math, random

def world_step(rnd, p, h):
    if rnd.random() < h:
        return [rnd.random(), rnd.random()], True
    return p, False

def run(g_fun, h_fun, T, seed, eta=0.2):
    rnd = random.Random(seed)
    p = [rnd.random(), rnd.random()]
    Q = [0.5, 0.5]; st = {'Sf': 0.4, 'Ss': 0.4}
    tot = 0.0; best = 0.0
    for t in range(T):
        p, _ = world_step(rnd, p, h_fun(t))
        g = g_fun(st)
        P = 1 / (1 + math.exp(-g * (Q[0] - Q[1])))
        c = 0 if rnd.random() < P else 1
        R = 1.0 if rnd.random() < p[c] else 0.0
        d = R - Q[c]; Q[c] += eta * d
        st['Sf'] += 0.1 * (abs(d) - st['Sf']); st['Ss'] += 0.005 * (abs(d) - st['Ss'])
        tot += P * p[0] + (1 - P) * p[1]; best += max(p)
    return tot / T, best / T

gains = [0.5, 1, 2, 4, 8, 16, 32, 64]
T, S = 4000, 60
print("fixed gain scan: mean expected reward per trial (fraction of the best possible)")
for h in (0.001, 0.01, 0.05):
    row = []
    for g in gains:
        a = b = 0
        for s in range(S):
            x, y = run(lambda st, g=g: g, lambda t, h=h: h, T, s); a += x; b += y
        row.append(a / b)
    gbest = gains[max(range(len(gains)), key=lambda i: row[i])]
    print(f"h={h:<6}: " + " ".join(f"g={g}:{r:.3f}" for g, r in zip(gains, row)) + f"  -> best g={gbest}")
    with open(f"scan_h{h}.txt", "w") as f:
        f.write(" ".join(f"({math.log2(g)},{r:.3f})" for g, r in zip(gains, row)))

# alternating calm/volatile epochs of 1000 trials
hz = lambda t: 0.001 if (t // 1000) % 2 == 0 else 0.05
print("alternating world (calm h=0.001 / volatile h=0.05, epochs of 1000 trials):")
for g in gains:
    a = b = 0
    for s in range(S):
        x, y = run(lambda st, g=g: g, hz, 8000, s); a += x; b += y
    print(f"  fixed g={g}: {a/b:.3f}")
for ghi, k in ((32, 10), (32, 20), (32, 40), (64, 20), (16, 10), (16, 20)):
    a = b = 0
    for s in range(S):
        x, y = run(lambda st, ghi=ghi, k=k: ghi / (1 + k * max(0.0, st['Sf'] - st['Ss'])), hz, 8000, s); a += x; b += y
    print(f"  surprise-driven g_hi={ghi} k={k}: {a/b:.3f}")

# ---- surprise-driven learning rate (same world) ----
def run_eta(g, eta_fun, T, seed, hz):
    rnd = random.Random(seed); p = [rnd.random(), rnd.random()]
    Q = [0.5, 0.5]; Sf = Ss = 0.4; tot = best = 0.0
    for t in range(T):
        if rnd.random() < hz(t): p = [rnd.random(), rnd.random()]
        P = 1 / (1 + math.exp(-g * (Q[0] - Q[1])))
        c = 0 if rnd.random() < P else 1
        R = 1.0 if rnd.random() < p[c] else 0.0
        d = R - Q[c]; u = max(0.0, Sf - Ss)
        Q[c] += min(1.0, eta_fun(u)) * d
        Sf += 0.1 * (abs(d) - Sf); Ss += 0.005 * (abs(d) - Ss)
        tot += P * p[0] + (1 - P) * p[1]; best += max(p)
    return tot / best
hz = lambda t: 0.001 if (t // 1000) % 2 == 0 else 0.05
S = 60
for g in (8, 16):
    for eta in (0.05, 0.1, 0.2, 0.4):
        print(f"g={g} fixed eta={eta}: {sum(run_eta(g, lambda u, e=eta: e, 8000, s, hz) for s in range(S))/S:.3f}")
    for e0, k in ((0.05, 20), (0.05, 40), (0.1, 20), (0.1, 40)):
        print(f"g={g} surprise eta0={e0} k={k}: {sum(run_eta(g, lambda u, e0=e0, k=k: e0*(1+k*u), 8000, s, hz) for s in range(S))/S:.3f}")

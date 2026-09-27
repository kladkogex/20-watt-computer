"""Write/read switching by ACET in a clockless associative memory (chapter 9, 09_acet.tex).
Needs numpy. Numbers quoted in the chapter: 10 seeds (seeds 0..9).

N GLUT neurons, rates r_i in [0,1], continuous time (Euler integration, dt = 0.5 ms):
    tau dr_i/dt = -r_i + F( c_in(a) * A * x_i + c_rec(a) * sum_j W_ij r_j - g - theta ),
    g = beta_g * max(sum_j r_j - pN, 0) / (pN)   (global GABA inhibition, chapter 3)
    dW_ij/dt   = eta * a * (r_i - p)(r_j - p) / (N p (1-p))        (Hebbian covariance rule)
a in [0,1] is the ACET level:
    c_in(a) = 0.5 + 0.5 a   (input synapses boosted),
    c_rec(a) = 1 - a        (recurrent synapses suppressed),
    learning rate proportional to a (plasticity eased).
Negative parts of W stand for inhibition through GABA-neurons.
Quality of a state r with respect to pattern xi:  m = sum (xi_i - p) r_i / (N p (1-p))  (1 = perfect).
"""
import numpy as np

N, p = 200, 0.1
tau, dt = 0.01, 0.0005
theta, T = 0.35, 0.02
beta_g = 1.0                                   # global GABA inhibition per extra active pattern-size
A = 1.0
T_pres = 0.2                                   # s per presentation
eta = 1.0 / T_pres                             # one presentation at a=1 stores one pattern term

def F(h):
    return 1.0 / (1.0 + np.exp(-(h - theta) / T))

def overlap(r, xi):
    return float(((xi - p) * r).sum() / (N * p * (1 - p)))

def hits_extras(r, xi):
    """fraction of the pattern's neurons that are active; number of active neurons outside it"""
    return float(r[xi == 1].mean()), float(r[xi == 0].sum())

def present(W, x, a, learn, r0=None, plast=None):
    """plast: learning-rate factor; by default = a (ACET also eases plasticity)."""
    r = np.zeros(N) if r0 is None else r0.copy()
    cin, crec = 0.5 + 0.5 * a, 1.0 - a
    lr = a if plast is None else plast
    for _ in range(int(T_pres / dt)):
        g = beta_g * max(r.sum() - p * N, 0.0) / (p * N)   # GABA: activity above the usual level
        h = cin * A * x + crec * (W @ r) - g
        r += dt / tau * (-r + F(h))
        if learn and lr > 0:
            d = r - p
            W += dt * eta * lr * np.outer(d, d) / (N * p * (1 - p))
            np.fill_diagonal(W, 0.0)
    return r

def make_patterns(rng, n, k):
    P = np.zeros((n, N))
    for mu in range(n):
        P[mu, rng.choice(N, k, replace=False)] = 1
    return P

def recall(W, xi, a_read, rng, frac=0.5, cue_units=None):
    on = np.flatnonzero(xi) if cue_units is None else cue_units
    n_cue = int(frac * int(xi.sum())) if cue_units is None else len(cue_units)
    cue = np.zeros(N); cue[rng.choice(on, n_cue, replace=False)] = 1
    r = present(W, cue, a_read, learn=False)          # cue present
    r = present(W, np.zeros(N), a_read, learn=False, r0=r)  # cue removed: what stays?
    return r

def experiment(seed, a_write_new, a_read=0.0, n_old=5, coupled=False):
    """Old patterns written cleanly (a=1). The new pattern, sharing half its neurons with old
    pattern 0, is written with input/recurrence set by a_write_new but plasticity fully on."""
    rng = np.random.default_rng(seed)
    k = int(p * N)
    P = make_patterns(rng, n_old, k)
    new = np.zeros(N)
    new[rng.choice(np.flatnonzero(P[0]), k // 2, replace=False)] = 1
    new[rng.choice(np.flatnonzero(P[0] == 0), k - k // 2, replace=False)] = 1
    W = np.zeros((N, N))
    for mu in range(n_old):
        present(W, P[mu], 1.0, learn=True)
    r_w = present(W, new, a_write_new, learn=True, plast=None if coupled else 1.0)
    out = [*hits_extras(r_w, new)]
    shared = np.flatnonzero((new == 1) & (P[0] == 1))
    new_only = np.setdiff1d(np.flatnonzero(new), shared)
    old_only = np.setdiff1d(np.flatnonzero(P[0]), shared)
    # cue each of the two similar patterns with the half that tells them apart
    out += [*hits_extras(recall(W, new, a_read, rng, cue_units=new_only), new)]
    out += [*hits_extras(recall(W, P[0], a_read, rng, cue_units=old_only), P[0])]
    out += [np.mean([hits_extras(recall(W, P[mu], a_read, rng), P[mu])[0] for mu in range(1, n_old)])]
    return out

def read_sweep(seed, a_read, n_pat=5):
    rng = np.random.default_rng(seed)
    P = make_patterns(rng, n_pat, int(p * N))
    W = np.zeros((N, N))
    for mu in range(n_pat):
        present(W, P[mu], 1.0, learn=True)
    return np.mean([hits_extras(recall(W, P[mu], a_read, rng), P[mu]) for mu in range(n_pat)], axis=0)

if __name__ == "__main__":
    seeds = range(10)
    print("WRITE a new pattern (half shared with an old one) at a_write, plasticity on;")
    print("then recall from a half cue at a_read=0.  hits = share of pattern active, extra = active neurons outside it")
    for aw in (0.0, 0.1, 0.2, 0.3, 0.5, 1.0):
        R = np.array([experiment(s, aw) for s in seeds]).mean(axis=0)
        print(f"  a_write={aw:4.2f}: while writing hits={R[0]:.2f} extra={R[1]:4.1f} | "
              f"recall new hits={R[2]:.2f} extra={R[3]:4.1f} | similar old hits={R[4]:.2f} extra={R[5]:4.1f} | other old hits={R[6]:.2f}")
    print("Same, but ACET also sets the learning rate (plasticity = a):")
    for aw in (0.1, 0.2, 0.3, 0.5, 0.75, 0.9, 1.0):
        R = np.array([experiment(s, aw, coupled=True) for s in seeds]).mean(axis=0)
        print(f"  a_write={aw:4.2f}: recall new hits={R[2]:.2f} extra={R[3]:4.1f} | similar old hits={R[4]:.2f} extra={R[5]:4.1f}")
    print("READ from a half cue at a_read (5 patterns written at a=1), cue then removed:")
    for ar in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0):
        h, e = np.mean([read_sweep(s, ar) for s in seeds], axis=0)
        print(f"  a_read={ar:4.2f}: hits={h:.2f} extra={e:4.1f}")

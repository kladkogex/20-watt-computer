"""Models behind the recognition chapter. Pure Python.

1. Two-stage recognizer on a 1-D "retina" of N pixels. Two shapes of 5 pixels each, placed at any shift,
   with each pixel flipped with probability p. Compared:
   (a) template matching on raw pixels at one stored position (no invariance);
   (b) stage S: detectors of each shape at every position (threshold on overlap, AND of parts),
       stage C: maximum over positions (OR) -> the shape whose C unit is larger wins.
2. Learning invariance from "video" (trace rule): 2 shapes x P positions -> P*2 stage-S detectors (one-hot).
   An object slides across all positions (dwell 50 ms per position), a 0.3 s blank follows, then a new random object.
   Two stage-C units compete (winner takes all); each keeps an RC trace of its own winning (time constant tau_tr),
   and weights move towards the current input in proportion to the trace:  dw_k/dt = eta * ybar_k * (x - w_k).
   After learning we test: for each object at each position, which C unit wins. Score = fraction of the
   2*P cases where the winning unit agrees with the object's identity (best label assignment).
"""
import random, math

SHAPES = {'A': [1, 1, 0, 1, 1], 'B': [1, 0, 1, 0, 1]}

def render(shape, shift, N, p, rnd):
    img = [0] * N
    for i, v in enumerate(SHAPES[shape]):
        img[shift + i] = v
    return [1 - v if rnd.random() < p else v for v in img]

def overlap(img, shape, shift):
    t = SHAPES[shape]
    return sum(1 if img[shift + i] == t[i] else 0 for i in range(len(t)))

def two_stage(N=24, p=0.0, trials=4000, seed=0):
    rnd = random.Random(seed); ok_raw = ok_sc = 0; L = 5
    for _ in range(trials):
        shape = rnd.choice('AB'); shift = rnd.randrange(N - L + 1)
        img = render(shape, shift, N, p, rnd)
        # (a) raw template matching at the stored position 0
        guess_raw = max('AB', key=lambda s: (overlap(img, s, 0), rnd.random()))
        # (b) S: overlap at every shift; C: max over shifts
        guess_sc = max('AB', key=lambda s: (max(overlap(img, s, k) for k in range(N - L + 1)), rnd.random()))
        ok_raw += guess_raw == shape; ok_sc += guess_sc == shape
    return ok_raw / trials, ok_sc / trials

def trace_learning(tau_tr, P=8, dwell=0.05, dt=0.005, eta=2.0, T=400.0, seed=0, gap=0.3):
    rnd = random.Random(seed)
    n = 2 * P
    w = [[rnd.random() * 0.1 + 0.45 for _ in range(n)] for _ in range(2)]
    ybar = [0.0, 0.0]; t = 0.0
    while t < T:
        obj = rnd.randrange(2); dirn = rnd.choice((1, -1))
        positions = list(range(P)) if dirn > 0 else list(range(P - 1, -1, -1))
        for pos in positions:
            x = [0.0] * n; x[obj * P + pos] = 1.0
            for _ in range(int(dwell / dt)):
                a = [sum(wi * xi for wi, xi in zip(w[k], x)) for k in (0, 1)]
                win = 0 if a[0] + 1e-9 * rnd.random() >= a[1] else 1
                y = [1.0 if k == win else 0.0 for k in (0, 1)]
                ybar = [ybar[k] + dt / tau_tr * (y[k] - ybar[k]) for k in (0, 1)]
                for k in (0, 1):
                    g = eta * dt * ybar[k]
                    w[k] = [wi + g * (xi - wi) for wi, xi in zip(w[k], x)]
                t += dt
        for _ in range(int(gap / dt)):          # blank between objects (gaze moves on)
            ybar = [ybar[k] + dt / tau_tr * (0.0 - ybar[k]) for k in (0, 1)]
            t += dt
    wins = [[None] * P for _ in range(2)]
    for obj in (0, 1):
        for pos in range(P):
            x = [0.0] * n; x[obj * P + pos] = 1.0
            a = [sum(wi * xi for wi, xi in zip(w[k], x)) for k in (0, 1)]
            wins[obj][pos] = 0 if a[0] >= a[1] else 1
    agree = sum((wins[o][q] == o) for o in (0, 1) for q in range(P)) / (2 * P)
    return max(agree, 1 - agree)

if __name__ == "__main__":
    for p in (0.0, 0.1, 0.2):
        raw, sc = two_stage(p=p)
        print(f"flip p={p:.1f}: raw template {raw:.3f}, S+C network {sc:.3f}")
    for tau in (0.005, 0.05, 0.2):
        scores = [trace_learning(tau, seed=s) for s in range(10)]
        print(f"trace tau={tau*1000:.0f} ms: invariance score min {min(scores):.2f}, mean {sum(scores)/10:.2f}, max {max(scores):.2f} (10 seeds)")

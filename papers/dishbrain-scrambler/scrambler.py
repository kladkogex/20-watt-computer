"""Scrambler account of DishBrain: simulations for the commentary (pure Python, no dependencies).

Model. A closed Pong loop in the DishBrain format (Kagan et al. 2022): the ball's vertical position
relative to the paddle is place-coded on 8 sensory electrodes and its distance to the paddle wall is
rate-coded (4 Hz far, 40 Hz near). Two motor populations read the active electrode through plastic
weights W_up[k], W_down[k] (16 numbers in [-1, 1]); their noisy rectified rates move the paddle.
Nothing in the model computes a prediction, a reward or its sign. The only teacher is a random kick
to all 16 weights after each rally outcome: s.d. sigma_miss after a miss, sigma_hit after a hit.

Runs:
  theory   the exact two-parameter chain of the book (only misses kick): stationary hit rate vs the
           prediction rho ~ 1/P_miss (harmonic-mean formula), for a finite state space.
  curves   hit fraction along a session for the DishBrain conditions and the proposed controls.
  kappa    performance vs kappa = (sigma_hit / sigma_miss)^2, sigma_miss fixed.
Writes data files next to this script and prints the numbers quoted in the paper.
"""
import math, os, random, sys
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
DT = 0.02            # s per loop step (DishBrain reads every 10 ms; 20 ms keeps pure Python fast)
H = 0.1              # paddle half-length (court is 1 x 1)
GAIN = 1.5           # paddle speed (court heights per s) per unit rate difference
NOISE = 0.35         # s.d. of motor-population noise per step
MAX_HITS = 30        # a rally is cut after this many hits
SIGMA0 = 0.01        # spontaneous weight drift per approach, present in every condition

# ---------------------------------------------------------------- the Pong loop, one approach at a time
def serve(rnd):
    # x, y, vx, vy: a new ball starts at the far wall in a random direction, so every approach is a
    # full crossing (about 1 s) whether it follows a hit or a miss
    return [0.0, rnd.random(), 1.0, rnd.uniform(-0.8, 0.8)]

def approach(W, rnd, ball, p):
    """Fly the ball until it reaches the paddle wall. Returns (hit, paddle position)."""
    x, y, vx, vy = ball
    while True:
        # sensory code: electrode from the ball's height relative to the paddle, rate from distance
        rel = max(-0.5, min(0.4999, y - p))
        k = int((rel + 0.5) * 8)
        s = (4 + 36 * x) / 40.0
        up = max(0.0, W[k] * s + rnd.gauss(0, NOISE))
        dn = max(0.0, W[8 + k] * s + rnd.gauss(0, NOISE))
        p = min(1 - H, max(H, p + GAIN * (up - dn) * DT))
        x += vx * DT; y += vy * DT
        if y < 0: y, vy = -y, -vy
        if y > 1: y, vy = 2 - y, -vy
        if x < 0: x, vx = -x, -vx
        if x >= 1 and vx > 0:
            hit = abs(y - p) < H
            ball[:] = [2 - x, y, -vx, vy]          # after a hit the ball flies back
            return hit, p

def kick(W, rnd, sigma):
    """Symmetric random kick; weights reflect at +-1, so equal kicks everywhere leave the uniform law invariant."""
    if sigma > 0:
        for i in range(16):
            w = W[i] + rnd.gauss(0, sigma)
            while w > 1 or w < -1:
                w = 2 - w if w > 1 else -2 - w
            W[i] = w

def session(args):
    """One culture, one session of n ball approaches (the session clock). Returns hit (1/0) per approach.
    A miss ends the rally: kick of s.d. s_miss, then a new serve. A hit: kick of s.d. s_hit, play on."""
    seed, n, s_hit, s_miss = args
    rnd = random.Random(seed)
    W = [rnd.uniform(-1.0, 1.0) for _ in range(16)]     # a naive culture: a random setting
    p, ball, out = 0.5, serve(rnd), []
    for _ in range(n):
        hit, p = approach(W, rnd, ball, p)
        out.append(1 if hit else 0)
        kick(W, rnd, SIGMA0)
        if hit:
            kick(W, rnd, s_hit)
        else:
            kick(W, rnd, s_miss)
            ball = serve(rnd)
    return out

def hit_fraction(h):
    return sum(h) / len(h)

def run(n_cult, n, s_hit, s_miss, pool, seed0=0):
    return pool.map(session, [(seed0 + c, n, s_hit, s_miss) for c in range(n_cult)])

# ---------------------------------------------------------------- the exact finite-state check
def theory_check():
    """Book model: paddle p = clip(a y + b), hit if |p - y| < 0.1, y ~ U(0,1). Settings (a, b) on a
    grid; after a miss jump to a uniformly random neighbour (symmetric kernel), after a hit stay.
    Exact stationary law: rho ~ 1/P_miss, so the long-run miss rate is the harmonic mean of P_miss."""
    A = [i / 10 for i in range(-10, 21)]          # a in [-1, 2]
    B = [j / 10 for j in range(-10, 11)]          # b in [-1, 1]
    ys = [(i + 0.5) / 400 for i in range(400)]
    def pmiss(a, b):
        return sum(1 for y in ys if abs(min(1, max(0, a * y + b)) - y) >= 0.1) / len(ys)
    P = {(i, j): pmiss(a, b) for i, a in enumerate(A) for j, b in enumerate(B)}
    # settings with P_miss = 0 would absorb the chain; they are excluded from the state space
    pos = [v for v in P.values() if v > 0]
    harm = len(pos) / sum(1 / v for v in pos)
    arith = sum(pos) / len(pos)
    # simulate the chain on the same grid (neighbours reflect at the border: symmetric kernel)
    rnd = random.Random(1)
    i, j = rnd.randrange(len(A)), rnd.randrange(len(B))
    while P[(i, j)] == 0:
        i, j = rnd.randrange(len(A)), rnd.randrange(len(B))
    misses = n = 0
    ys_draw = rnd.random
    for t in range(3_000_000):
        a, b = A[i], B[j]
        y = ys_draw()
        miss = abs(min(1, max(0, a * y + b)) - y) >= 0.1
        n += 1; misses += miss
        if miss:
            di, dj = rnd.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
            ni, nj = i + di, j + dj
            # a move off the grid or into a never-miss setting is rejected: the kernel stays symmetric
            if 0 <= ni < len(A) and 0 <= nj < len(B) and P[(ni, nj)] > 0:
                i, j = ni, nj
    return arith, harm, misses / n, sum(1 for v in P.values() if v == 0)

# ---------------------------------------------------------------- main
CONDITIONS = [
    # name, sigma_hit, sigma_miss, label
    ("stimulus",  0.00, 0.08, "DishBrain Stimulus: disruptive after a miss, gentle after a hit"),
    ("silent",    0.00, 0.03, "Silent: no stimulation; spontaneous bursts in the post-miss pause"),
    ("nofb",      0.00, 0.00, "No feedback"),
    ("allrandom", 0.08, 0.08, "Control: the same disruptive stimulus after every outcome"),
    ("swapped",   0.08, 0.02, "Proposed: strong predictable after a hit, weak random after a miss"),
]

if __name__ == "__main__":
    n_cult = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    arith, harm, sim, absorbing = theory_check()
    print(f"theory: mean P_miss over settings {arith:.3f}; predicted stationary miss rate (harmonic mean) "
          f"{harm:.3f}; simulated {sim:.3f}; never-miss settings excluded: {absorbing}")
    q = n // 4                                        # "first 5 of 20 minutes"
    with Pool() as pool:
        rows = {}
        for name, sh, sm, label in CONDITIONS:
            res = run(n_cult, n, sh, sm, pool)
            t1 = [hit_fraction(r[:q]) for r in res]; t2 = [hit_fraction(r[q:]) for r in res]
            m1, m2 = sum(t1) / n_cult, sum(t2) / n_cult
            d = [b - a for a, b in zip(t1, t2)]
            md = sum(d) / n_cult; se = math.sqrt(sum((x - md) ** 2 for x in d) / (n_cult - 1) / n_cult)
            better = sum(1 for x in d if x > 0) / n_cult
            rows[name] = (m1, m2, md, se)
            with open(os.path.join(HERE, f"curve_{name}.dat"), "w") as f:
                w = n // 20                               # hit fraction in a sliding window
                mean = [sum(r[t] for r in res) / n_cult for t in range(n)]
                for t in range(w, n + 1, max(1, n // 100)):
                    f.write(f"{t} {sum(mean[t - w:t]) / w:.4f}\n")
            print(f"{name:10s} s_hit={sh:.2f} s_miss={sm:.2f}: hit fraction {m1:.3f} -> {m2:.3f} "
                  f"(change {md:+.3f} +/- {se:.3f} s.e., improved in {better:.0%} of cultures); "
                  f"rally length h/(1-h) {m1 / (1 - m1):.2f} -> {m2 / (1 - m2):.2f}  [{label}]")
        with open(os.path.join(HERE, "kappa.dat"), "w") as f:
            for sh in (0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.16):
                res = run(n_cult, n, sh, 0.08, pool, seed0=10_000)
                t2 = sum(hit_fraction(r[q:]) for r in res) / n_cult
                kappa = (sh / 0.08) ** 2
                f.write(f"{kappa:.4f} {t2:.4f}\n")
                print(f"kappa={kappa:.3f}: hit fraction, last three quarters {t2:.3f}")
        print(f"no-feedback reference, last three quarters: {rows['nofb'][1]:.3f}")

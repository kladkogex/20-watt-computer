"""Model behind chapter 9 (АЦЕТ), eq:kalman: the Kalman-Bucy filter as an RC circuit with a variable time constant.

World:   s(t) is a random walk, ds = sqrt(q) dW, q = 0.01 per s; at t = 50 s it jumps by +3.
Sensors: y(t) = s(t) + white noise of intensity R = 1 (Euler step dt = 10 ms, sample sd sqrt(R/dt)).
Filter:  dŝ/dt = (P/R)(y - ŝ),  dP/dt = q - P^2/R,  P(0) = 1  ->  steady P = sqrt(qR), time constant sqrt(R/q) = 10 s.
Two copies of the filter see the same data; the second one resets P to 1 at the jump (a НОРА-like "the world changed").
Writes figures/kalman_{s,y,plain,reset}.dat (t, value; y averaged over 1 s bins) and
figures/kalman_tau_{plain,reset}.dat (t, R/P in s); prints the time to cover 63% of the jump for both filters.
"""
import math
import random

q, R, dt, T, t_jump, jump, P0 = 0.01, 1.0, 0.01, 100.0, 50.0, 3.0, 1.0

def run(seed=10):
    rng = random.Random(seed)
    s, filt = 0.0, {"plain": [0.0, P0], "reset": [0.0, P0]}
    rec = {k: [] for k in ("s", "plain", "reset", "tau_plain", "tau_reset")}
    ybins, acc, n = [], 0.0, 0
    for i in range(int(T / dt)):
        t = i * dt
        if abs(t - t_jump) < dt / 2:
            s += jump
            filt["reset"][1] = P0
        s += math.sqrt(q * dt) * rng.gauss(0, 1)
        y = s + math.sqrt(R / dt) * rng.gauss(0, 1)
        for k, f in filt.items():
            f[0] += dt * f[1] / R * (y - f[0])
            f[1] += dt * (q - f[1] ** 2 / R)
        acc += y; n += 1
        if n == 100:
            ybins.append((t - 0.5, acc / n)); acc, n = 0.0, 0
        if i % 10 == 0:
            rec["s"].append((t, s))
            for k, f in filt.items():
                rec[k].append((t, f[0])); rec["tau_" + k].append((t, R / f[1]))
    return rec, ybins

if __name__ == "__main__":
    rec, ybins = run()
    for k, rows in rec.items():
        with open(f"figures/kalman_{k}.dat", "w") as f:
            f.writelines(f"{t:.2f} {v:.4f}\n" for t, v in rows)
    with open("figures/kalman_y.dat", "w") as f:
        f.writelines(f"{t:.2f} {v:.4f}\n" for t, v in ybins)
    print(f"steady time constant sqrt(R/q) = {math.sqrt(R / q):.1f} s; R/P at t=49 s: "
          f"{dict(rec['tau_plain'])[49.0]:.2f} s")
    s_at = dict(rec["s"])
    for k in ("plain", "reset"):
        est = dict(rec[k]); base = est[49.9]
        t63 = next(t for t, v in rec[k] if t > t_jump and v - base > 0.63 * (s_at[t] - base))
        print(f"{k:5s}: 63% of the jump covered after {t63 - t_jump:.1f} s")
    print(f"ŝ range {min(v for _, v in rec['plain']):.2f}..{max(v for _, v in rec['plain']):.2f}; "
          f"y bins range {min(v for _, v in ybins):.2f}..{max(v for _, v in ybins):.2f}; "
          f"s range {min(v for _, v in rec['s']):.2f}..{max(v for _, v in rec['s']):.2f}")

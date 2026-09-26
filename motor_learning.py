"""Model behind the motor-learning chapter: two-rate adaptation (fast + slow process),
updated after every movement (an event, not a clock tick).

  e = p - (x_f + x_s);   x_f <- A_f x_f + B_f e;   x_s <- A_s x_s + B_s e
Protocol: baseline (p=0), adaptation (p=+1), counter-perturbation (p=-1) until the net
output returns to zero, then an error clamp (e=0) in which the output drifts back
toward the old adaptation (spontaneous recovery).
Writes figures/tworate_{net,fast,slow,p}.dat (movement number, value) and prints key numbers.
"""
Af, Bf, As, Bs = 0.92, 0.10, 0.996, 0.02

def run(n_base=20, n_adapt=200, n_clamp=100):
    xf = xs = 0.0
    rows = []  # (n, p, net, fast, slow)
    n = 0
    def step(p, clamp=False):
        nonlocal xf, xs, n
        net = xf + xs
        e = 0.0 if clamp else p - net
        rows.append((n, p, net, xf, xs))
        xf = Af * xf + Bf * e
        xs = As * xs + Bs * e
        n += 1
    for _ in range(n_base): step(0.0)
    for _ in range(n_adapt): step(1.0)
    n_counter = 0
    while xf + xs > 0.0:
        step(-1.0); n_counter += 1
    for _ in range(n_clamp): step(0.0, clamp=True)
    return rows, n_counter

if __name__ == "__main__":
    rows, n_counter = run()
    for name, k in (("p", 1), ("net", 2), ("fast", 3), ("slow", 4)):
        with open(f"figures/tworate_{name}.dat", "w") as f:
            f.writelines(f"{r[0]} {r[k]:.4f}\n" for r in rows)
    end_adapt = rows[20 + 200 - 1]
    print(f"end of adaptation: net {end_adapt[2]:.3f} fast {end_adapt[3]:.3f} slow {end_adapt[4]:.3f}")
    print(f"counter-perturbation lasted {n_counter} movements")
    s = 20 + 200 + n_counter
    at0 = rows[s]
    print(f"clamp start: net {at0[2]:.3f} fast {at0[3]:.3f} slow {at0[4]:.3f}")
    peak = max(rows[s:], key=lambda r: r[2])
    print(f"spontaneous recovery peak: net {peak[2]:.3f} at movement {peak[0]-s} of clamp; end of clamp net {rows[-1][2]:.3f}")
    # movements to reach 80% during adaptation
    n80 = next(i for i in range(20, 220) if rows[i][2] >= 0.8) - 20
    print(f"adaptation reaches 0.8 after {n80} movements")

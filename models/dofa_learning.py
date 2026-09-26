"""Three-factor learning of a two-choice task in continuous time (Euler, dt=1 ms), pure Python.

Two ГЛУТ groups A, B compete through ГАМК (winner-take-all, beta=2), driven by a cue x (1 s)
through weights wA, wB plus slow (OU) noise. The choice is the group winning at cue end.
Reward arrives d=0.5 s after the cue ends: prob 0.8 for A, 0.2 for B.
Eligibility trace: tau_e de/dt = -e + x*r_a.  Weight: dw/dt = eta*delta(t)*e.
delta(t) = reward pulse minus expected-reward pulse (running mean), or without the baseline.
"""
import math, random, sys

def run(tau_e, baseline=True, trials=400, seed=0, eta=0.5):
    rnd = random.Random(seed)
    dt, tau, beta, tau_n, sig = 1e-3, 0.02, 2.0, 0.02, 0.4
    T_cue, d, T_rew, T_end = 1.0, 0.5, 0.1, 2.0
    w = [1.0, 1.0]; Rbar = 0.5; ch = []
    kn = sig * math.sqrt(2 * dt / tau_n)
    for k in range(trials):
        r = [0.0, 0.0]; e = [0.0, 0.0]; xi = [0.0, 0.0]; choice = None; rew = 0.0
        for i in range(int(T_end / dt)):
            t = i * dt
            x = 1.0 if t < T_cue else 0.0
            for a in (0, 1):
                xi[a] += -dt / tau_n * xi[a] + kn * rnd.gauss(0, 1)
            u = [max(w[a] * x + xi[a] * x - beta * r[1 - a], 0.0) for a in (0, 1)]
            r = [r[a] + dt / tau * (-r[a] + u[a]) for a in (0, 1)]
            if choice is None and t >= T_cue - dt / 2:
                choice = 0 if r[0] >= r[1] else 1
                rew = 1.0 if rnd.random() < (0.8 if choice == 0 else 0.2) else 0.0
            e = [e[a] + dt / tau_e * (-e[a] + x * r[a]) for a in (0, 1)]
            pulse = 1.0 / T_rew if (T_cue + d) <= t < (T_cue + d + T_rew) else 0.0
            delta = pulse * (rew - (Rbar if baseline else 0.0))
            w = [w[a] + dt * eta * delta * e[a] for a in (0, 1)]
        Rbar += 0.05 * (rew - Rbar)
        ch.append(choice)
    f = lambda s: sum(1 for c in s if c == 0) / len(s)
    return f(ch[:100]), f(ch[-100:]), w

# Results quoted in chapter 6: eta=0.05, 500 trials, seeds 0..5 (and eta=0.5, seeds 0..2 for the lock-in case).
for tau_e, bl in ((1.0, True), (0.05, True), (1.0, False)):
    res = [run(tau_e, bl, trials=500, seed=s, eta=0.05) for s in range(6)]
    print(f"tau_e={tau_e:4.2f}s baseline={bl!s:5}: " + "; ".join(
        f"P(A) {a:.2f}->{b:.2f} w=({w[0]:.2f},{w[1]:.2f})" for a, b, w in res), flush=True)

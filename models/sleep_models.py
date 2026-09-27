"""Models behind the sleep chapter. Pure Python, Euler integration.

1. Two-process model of sleep timing: sleep pressure S charges while awake,
   dS/dt = (1 - S)/tau_r, and discharges while asleep, dS/dt = -S/tau_d.
   Sleep starts when S reaches the upper threshold H(t), waking when S falls to the
   lower threshold L(t); both thresholds move with the daily rhythm C(t).
   Writes figures/sleep_S.dat, sleep_H.dat, sleep_L.dat (t in hours, counted from the start of day 2).
2. Slow oscillation: one GLUT group with self-excitation w and fatigue a,
     tau dr/dt = -r + F(w r + I - a),  tau_a da/dt = -a + b r,
   F(x) = 1/(1 + exp(-(x - theta)/k)).  With fatigue gain b = 5 the group
   alternates UP/DOWN; with a small b (acetylcholine reduces fatigue currents) it stays UP.
   Writes figures/updown_sleep.dat and figures/updown_wake.dat (t in s, r).
"""
import math

def two_process(tau_r=18.2, tau_d=4.2, H0=0.67, L0=0.17, A=0.12, days=6.0, dt=0.01,
                stay_awake=None):
    C = lambda t: math.sin(2 * math.pi * (t - 8.0) / 24.0)
    S, awake, t = 0.2, True, 0.0
    rec, switches = [], []
    while t < days * 24:
        H, L = H0 + A * C(t), L0 + A * C(t)
        if awake:
            S += dt * (1 - S) / tau_r
            forced = stay_awake is not None and stay_awake[0] <= t < stay_awake[1]
            if S >= H and not forced:
                awake = False; switches.append((t, 'sleep'))
        else:
            S += dt * (-S) / tau_d
            if S <= L:
                awake = True; switches.append((t, 'wake'))
        rec.append((t, S, H, L))
        t += dt
    return rec, switches

def durations(switches, t_from=48):
    sw = [(t, k) for t, k in switches if t >= t_from]
    wake, sleep = [], []
    for (t0, k0), (t1, k1) in zip(sw, sw[1:]):
        (sleep if k0 == 'sleep' else wake).append(t1 - t0)
    return wake, sleep

def updown(b, w=5.0, I=2.0, theta=2.5, k=0.25, tau=0.01, tau_a=0.3, T=6.0, dt=1e-4):
    F = lambda x: 1 / (1 + math.exp(-(x - theta) / k))
    r, a, rec, ups = 0.0, 0.0, [], []
    was_up = False
    for i in range(int(T / dt)):
        t = i * dt
        r += dt / tau * (-r + F(w * r + I - a))
        a += dt / tau_a * (-a + b * r)
        up = r > 0.5
        if up and not was_up: ups.append(t)
        was_up = up
        if i % 20 == 0: rec.append((t, r))
    # fraction of time UP after the transient: average over a whole number of
    # periods (from the first UP onset after 2 s to the last onset), otherwise
    # a partial period biases the fraction; without oscillation use all t > 2 s
    late_ups = [t for t in ups if t > 2.0]
    if len(late_ups) >= 2:
        t0, t1 = late_ups[0], late_ups[-1]
    else:
        t0, t1 = 2.0, T
    late = [x for t, x in rec if t0 <= t < t1]
    frac_up = sum(1 for x in late if x > 0.5) / len(late)
    periods = [y - x for x, y in zip(ups, ups[1:])]
    return rec, periods, frac_up

if __name__ == "__main__":
    rec, sw = two_process()
    for name, col in (("S", 1), ("H", 2), ("L", 3)):
        with open(f"figures/sleep_{name}.dat", "w") as f:
            f.writelines(f"{r[0] - 24:.3f} {r[col]:.4f}\n" for r in rec[::20] if 24 <= r[0] <= 96)
    wake, sleep = durations(sw)
    print("normal: wake h", [round(x, 1) for x in wake], " sleep h", [round(x, 1) for x in sleep])
    print("sleep onsets (clock h):", [round(t % 24, 1) for t, k in sw if k == 'sleep' and t > 48])
    # stay awake through one night: from a normal wake-up on day 3, keep awake 40 h
    wake_up = [t for t, k in sw if k == 'wake' and t > 48][0]
    rec2, sw2 = two_process(stay_awake=(wake_up, wake_up + 40))
    after = [(t, k) for t, k in sw2 if t >= wake_up + 40]
    rs = after[1][0] - after[0][0]
    S40 = [r[1] for r in rec2 if abs(r[0] - (wake_up + 40)) < 0.006][0]
    print(f"after 40 h awake: S={S40:.2f}, recovery sleep {rs:.1f} h")
    for label, b in (("sleep", 5.0), ("wake", 1.0)):
        recu, periods, frac = updown(b)
        with open(f"figures/updown_{label}.dat", "w") as f:
            f.writelines(f"{t:.4f} {r:.4f}\n" for t, r in recu if t <= 4.0)
        print(f"b={b}: fraction UP={frac:.2f}, periods={[round(p, 2) for p in periods[1:6]]}")

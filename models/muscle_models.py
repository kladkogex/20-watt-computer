"""Models behind chapter 12 (muscles). Pure Python, continuous time (Euler, dt=0.1 ms).

1. Rate coding: muscle force as a linear sum of twitches h(t) = (t/Tc) exp(1 - t/Tc), Tc = 50 ms,
   for regular spike trains at 5, 15, 40 Hz. Writes figures/muscle_twitch_<rate>.dat (t in s, F in twitch units).
2. Half-centre oscillator: two ГЛУТ groups with mutual inhibition (beta) and slow fatigue a_i:
     tau dr_i/dt = -r_i + [I - beta r_j - a_i]_+ ,   tau_a da_i/dt = -a_i + b r_i .
   Writes figures/halfcentre1.dat and halfcentre2.dat (t, r) and prints the period.
3. Delayed feedback x'(t) = -G x(t-d): prints the oscillation onset G*d = pi/2 check.
"""
import math

def twitch(t, Tc=0.05):
    return (t / Tc) * math.exp(1 - t / Tc) if t > 0 else 0.0

def rate_coding(rate, T=0.6, dt=0.001):
    spikes = [k / rate for k in range(int(T * rate) + 1)]
    out = []
    for i in range(int(T / dt) + 1):
        t = i * dt
        out.append((t, sum(twitch(t - s) for s in spikes if s <= t)))
    return out

def halfcentre(I=1.0, beta=2.0, b=2.0, tau=0.02, tau_a=0.4, T=4.0, dt=1e-4):
    r = [0.01, 0.0]; a = [0.0, 0.0]; rec = []; ups = []
    prev = r[0] > r[1]
    for i in range(int(T / dt)):
        t = i * dt
        u = [max(I - beta * r[1 - k] - a[k], 0.0) for k in (0, 1)]
        r = [r[k] + dt / tau * (-r[k] + u[k]) for k in (0, 1)]
        a = [a[k] + dt / tau_a * (-a[k] + b * r[k]) for k in (0, 1)]
        now = r[0] > r[1]
        if now and not prev: ups.append(t)
        prev = now
        if i % 50 == 0: rec.append((t, r[0], r[1]))
    periods = [y - x for x, y in zip(ups, ups[1:])]
    return rec, periods

def delayed(G, d, T=3.0, dt=1e-4):
    n = int(d / dt); hist = [1.0] * (n + 1); x = 1.0; peak_late = 0.0
    for i in range(int(T / dt)):
        x += dt * (-G * hist[-n - 1] if n else -G * x)
        hist.append(x)
        if i * dt > T - 1.0: peak_late = max(peak_late, abs(x))
    return peak_late

if __name__ == "__main__":
    for rate in (5, 15, 40):
        data = rate_coding(rate)
        with open(f"figures/muscle_twitch_{rate}.dat", "w") as f:
            f.writelines(f"{t:.4f} {F:.4f}\n" for t, F in data)
        late = [F for t, F in data if t > 0.3]
        print(f"rate {rate:2d} Hz: force in last 0.3 s from {min(late):.2f} to {max(late):.2f} twitches")
    rec, periods = halfcentre()
    for k in (1, 2):
        with open(f"figures/halfcentre{k}.dat", "w") as f:
            f.writelines(f"{row[0]:.4f} {row[k]:.4f}\n" for row in rec)
    print("half-centre periods (s):", [round(p, 3) for p in periods])
    d = 0.03
    for G in (40, 50, 55, 60):
        print(f"delay {d*1000:.0f} ms, G={G}/s (G*d={G*d:.2f}, pi/2=1.57): late amplitude {delayed(G, d):.3g}")

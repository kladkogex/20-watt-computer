"""Models behind the chemical-output chapter. Pure Python, continuous time (Euler).

Three-stage hormone cascade with negative feedback from the last stage to the first:
    tau dx1/dt = -x1 + g*(u - k*x3),  tau dx2/dt = -x2 + g*x1,  tau dx3/dt = -x3 + g*x2,
loop gain K = g^3 * k. Linear theory: stable iff K < 8; at K = 8 it oscillates with period 2*pi*tau/sqrt(3).
Writes figures/cascade_K<K>.dat (t/tau, x3 normalised to its set point u*g^3/(1+K)).
"""
import math

def cascade(K, g=2.0, u=1.0, tau=1.0, T=40.0, dt=1e-3):
    k = K / g**3
    x = [0.0, 0.0, 0.0]; rec = []
    for i in range(int(T / dt)):
        t = i * dt
        x1 = x[0] + dt / tau * (-x[0] + g * max(u - k * x[2], 0.0))
        x2 = x[1] + dt / tau * (-x[1] + g * x[0])
        x3 = x[2] + dt / tau * (-x[2] + g * x[1])
        x = [x1, x2, x3]
        if i % 100 == 0: rec.append((t, x[2]))
    return rec

def late_swing(rec, frac=0.25):
    tail = [y for t, y in rec[int(len(rec) * (1 - frac)):]]
    return max(tail) - min(tail)

if __name__ == "__main__":
    for K in (4, 7, 8.5, 12):
        rec = cascade(K)
        ref = 2.0**3 / (1 + K)
        print(f"K={K}: set point {ref:.3f}, error of proportional control 1/(1+K)={1/(1+K):.3f}, late swing {late_swing(rec):.3f}")
        if K in (4, 12):
            with open(f"figures/cascade_K{K}.dat", "w") as f:
                f.writelines(f"{t:.3f} {y/ref:.4f}\n" for t, y in rec)
    print("period at onset (units of tau):", round(2 * math.pi / math.sqrt(3), 3))
    # measure period for K=12 from upward crossings of the set point
    rec = cascade(12); ref = 8 / 13; ups = []
    for (t0, y0), (t1, y1) in zip(rec, rec[1:]):
        if y0 < ref <= y1 and t1 > 10: ups.append(t1)
    print("K=12 measured period (tau):", [round(b - a, 2) for a, b in zip(ups, ups[1:])][:4])

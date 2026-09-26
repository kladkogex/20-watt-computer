"""Simulate the Hodgkin-Huxley model (modern sign convention, rest ~ -65 mV)
and write TikZ coordinate lists used by chapters/04_actionpotential.tex.
Pure Python, no dependencies. Run: python3 figures/make_hh.py"""
import math, os

gNa, gK, gL = 120.0, 36.0, 0.3          # mS/cm^2
ENa, EK, EL = 50.0, -77.0, -54.387      # mV
C = 1.0                                  # uF/cm^2

def am(V): return 0.1*(V+40)/(1-math.exp(-(V+40)/10))
def bm(V): return 4*math.exp(-(V+65)/18)
def ah(V): return 0.07*math.exp(-(V+65)/20)
def bh(V): return 1/(1+math.exp(-(V+35)/10))
def an(V): return 0.01*(V+55)/(1-math.exp(-(V+55)/10))
def bn(V): return 0.125*math.exp(-(V+65)/80)

def run(stim, T=20.0, dt=0.005):
    V = -65.0
    m = am(V)/(am(V)+bm(V)); h = ah(V)/(ah(V)+bh(V)); n = an(V)/(an(V)+bn(V))
    out = []
    t = 0.0
    while t <= T:
        out.append((t, V, m, h, n, gNa*m**3*h, gK*n**4))
        I = stim(t)
        dV = (I - gNa*m**3*h*(V-ENa) - gK*n**4*(V-EK) - gL*(V-EL))/C
        dm = am(V)*(1-m) - bm(V)*m
        dh = ah(V)*(1-h) - bh(V)*h
        dn = an(V)*(1-n) - bn(V)*n
        V += dt*dV; m += dt*dm; h += dt*dh; n += dt*dn
        t += dt
    return out

def coords(data, idx, every=20, tscale=1.0, yscale=1.0, yoff=0.0):
    pts = data[::every]
    return " ".join(f"({p[0]*tscale:.3f},{(p[idx]+yoff)*yscale:.3f})" for p in pts)

here = os.path.dirname(os.path.abspath(__file__))
pulse = lambda amp: (lambda t: amp if 1.0 <= t < 1.5 else 0.0)

# supra- and sub-threshold responses to a 0.5 ms current pulse
supra = run(pulse(20.0)); sub = run(pulse(10.0))
with open(os.path.join(here, "hh_trace.tex"), "w") as f:
    # axes: t in ms -> 0.5 cm per ms; V in mV -> 0.05 cm per mV, offset +80
    f.write("\\draw[very thick,red!70!black] plot coordinates {%s};\n" % coords(supra, 1, tscale=0.5, yscale=0.05, yoff=80))
    f.write("\\draw[thick,blue!60!black,densely dashed] plot coordinates {%s};\n" % coords(sub, 1, tscale=0.5, yscale=0.05, yoff=80))
with open(os.path.join(here, "hh_gates.tex"), "w") as f:
    # conductances, mS/cm^2 -> 0.1 cm per unit
    f.write("\\draw[very thick,orange!85!black] plot coordinates {%s};\n" % coords(supra, 5, tscale=0.5, yscale=0.1))
    f.write("\\draw[very thick,green!45!black] plot coordinates {%s};\n" % coords(supra, 6, tscale=0.5, yscale=0.1))

peakV = max(p[1] for p in supra); tpeak = [p[0] for p in supra if p[1] == peakV][0]
minV = min(p[1] for p in supra if p[0] > tpeak)
print(f"peak {peakV:.1f} mV at {tpeak:.2f} ms; undershoot {minV:.1f} mV; "
      f"max gNa {max(p[5] for p in supra):.1f}; max gK {max(p[6] for p in supra):.1f}; "
      f"sub peak {max(p[1] for p in sub):.1f}")

# threshold search for the 0.5 ms pulse
lo, hi = 1.0, 20.0
for _ in range(30):
    mid = (lo+hi)/2
    if max(p[1] for p in run(pulse(mid), T=10)) > 0: hi = mid
    else: lo = mid
print(f"threshold amplitude for 0.5 ms pulse: {hi:.2f} uA/cm^2")

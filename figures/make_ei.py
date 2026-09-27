"""E-I loop traces for chapter 3 (GLUT+GABA): writes figures/ei_traces.tex.
tauE dE/dt = -E + [wEE E - wEI I + h]_+ ; tauI dI/dt = -I + [wIE E]_+ ; times in ms."""
import os
relu = lambda x: max(x, 0.0)
def run(wEI, tauI, wEE=1.5, wIE=1.0, tauE=10.0, h=1.0, T=150.0, dt=0.01):
    E = I = 0.0; out = []
    for k in range(int(T/dt)+1):
        if k % 50 == 0: out.append((k*dt, E))
        E, I = E + dt/tauE*(-E + relu(wEE*E - wEI*I + h)), I + dt/tauI*(-I + relu(wIE*E))
    return out
def coords(tr, xs=0.07, ys=1.4, ymax=2.2):
    return " ".join(f"({t*xs:.3f},{min(E, ymax)*ys:.3f})" for t, E in tr)
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "ei_traces.tex"), "w") as f:
    f.write("\\draw[very thick,gray!60!black,densely dashed] plot coordinates {%s};\n" % coords(run(0.0, 2.0)))
    f.write("\\draw[very thick,blue!60!black] plot coordinates {%s};\n" % coords(run(2.0, 2.0)))
    f.write("\\draw[very thick,red!70!black] plot coordinates {%s};\n" % coords(run(2.0, 30.0)))
print("ok")

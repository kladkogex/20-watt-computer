"""Fig. 1(a) of the PRE paper: the DishBrain array as the network model has it, drawn from the model's own
geometry (network/netsim.py): the MaxOne grid of 220 x 120 electrodes at 17.5 um, the eight stimulation electrodes
of the sensory band, the four 31 x 33-electrode motor regions, the recruitment radii of a pulse, one realization of
the 3000 uniformly placed neurons (80% excitatory), and the 100 inputs of one motor neuron drawn with probability
proportional to exp(-d / lambda), lambda = 1 mm, as in the model.

    python3 fig_array.py   -> fig_array.pdf (and a count of the inputs that lie within a stimulation catchment)
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.lines import Line2D

PITCH = 0.0175
NC, NR = 220, 120
WX, WY = NC * PITCH, NR * PITCH
STIM = [(22, 20), (46, 35), (70, 20), (94, 35), (117, 20), (142, 35), (165, 20), (190, 35)]
MOTOR = [("down", 18, 48), ("up", 49, 79), ("down", 140, 170), ("up", 171, 201)]
MROWS = (78, 110)
N, FRAC_E, K, LAM = 3000, 0.8, 100, 1.0
R75_SMALL, R75_WIDE, R150_SMALL, R150_WIDE = 0.05, 0.12, 0.10, 0.20

plt.rcParams.update({"font.family": "serif", "mathtext.fontset": "cm", "font.size": 7,
                     "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5})

fig, ax = plt.subplots(figsize=(3.9, 2.55))
ax.set_aspect("equal")

# every electrode of the array
cols, rows = np.meshgrid(np.arange(NC), np.arange(NR))
ex, ey = cols.ravel() * PITCH, rows.ravel() * PITCH
ax.scatter(ex, ey, s=0.12, c="0.78", linewidths=0, rasterized=True, zorder=1)

# motor regions: the electrodes themselves, coloured
for name, c0, c1 in MOTOR:
    m = (cols.ravel() >= c0) & (cols.ravel() <= c1) & (rows.ravel() >= MROWS[0]) & (rows.ravel() <= MROWS[1])
    col = "#3b5bdb" if name == "up" else "#c92a2a"
    ax.scatter(ex[m], ey[m], s=0.5, c=col, linewidths=0, rasterized=True, zorder=2, alpha=0.8)
    ax.text((c0 + c1) / 2 * PITCH, (MROWS[1] + 1) * PITCH + 0.03, name, ha="center", va="bottom", fontsize=6.5, color=col)

# neurons: one realization of the model's uniform placement, 80% excitatory
rng = np.random.default_rng(1000)
pos = rng.uniform([0, 0], [WX, WY], size=(N, 2))
ne = int(FRAC_E * N)
ax.scatter(pos[:ne, 0], pos[:ne, 1], s=1.0, c="0.15", linewidths=0, zorder=3, rasterized=True)
ax.scatter(pos[ne:, 0], pos[ne:, 1], s=1.0, c="#7048e8", linewidths=0, zorder=3, rasterized=True)

# the 100 inputs of one neuron in the first "up" region, drawn as the model draws them
target_xy = np.array([64 * PITCH, 94 * PITCH])
j = int(np.argmin(((pos - target_xy) ** 2).sum(1)))
d = np.linalg.norm(pos - pos[j], axis=1)
p = np.exp(-d / LAM); p[j] = 0; p /= p.sum()
inputs = rng.choice(N, size=K, replace=False, p=p)
for i in inputs:
    ax.plot([pos[i, 0], pos[j, 0]], [pos[i, 1], pos[j, 1]], color="#0b7285", lw=0.25, alpha=0.3, zorder=4)
ax.scatter([pos[j, 0]], [pos[j, 1]], s=14, facecolors="white", edgecolors="#0b7285", linewidths=0.8, zorder=6)

# stimulation electrodes and the recruitment radii of one of them
sx = np.array([c * PITCH for c, r in STIM]); sy = np.array([r * PITCH for c, r in STIM])
ax.scatter(sx, sy, s=16, c="#e8590c", edgecolors="k", linewidths=0.4, zorder=7)
for k, (x, y) in enumerate(zip(sx, sy), 1):
    ax.text(x, y - 0.07, str(k), ha="center", va="top", fontsize=6, color="#a63c06", zorder=7)
k0 = 5
for r, ls in [(R75_WIDE, "--"), (R150_WIDE, ":")]:
    ax.add_patch(Circle((sx[k0], sy[k0]), r, fill=False, ec="#e8590c", lw=0.6, ls=ls, zorder=7))
ax.annotate("75 mV, wide", (sx[k0] + R75_WIDE * 0.7, sy[k0] + R75_WIDE * 0.7), (sx[k0] + 0.25, sy[k0] + 0.24),
            fontsize=5.5, color="#a63c06", ha="left", va="center", arrowprops=dict(arrowstyle="-", lw=0.4, color="#a63c06"))
ax.annotate("150 mV, wide", (sx[k0] - R150_WIDE * 0.7, sy[k0] + R150_WIDE * 0.7), (sx[k0] - 0.3, sy[k0] + 0.32),
            fontsize=5.5, color="#a63c06", ha="right", va="center", arrowprops=dict(arrowstyle="-", lw=0.4, color="#a63c06"))

# distance from the sensory band to the motor regions
k1 = 7
ax.annotate("", (sx[k1], MROWS[0] * PITCH), (sx[k1], sy[k1] + 0.05),
            arrowprops=dict(arrowstyle="<->", lw=0.5, color="0.3", shrinkA=0, shrinkB=0))
ax.text(sx[k1] - 0.04, (sy[k1] + MROWS[0] * PITCH) / 2, f"{MROWS[0]*PITCH - sy[k1]:.2f} mm", fontsize=5.5,
        color="0.3", va="center", ha="right")
fig.text(0.005, 0.975, "(a)", fontsize=8, va="top", ha="left")

ax.set_xlim(-0.02, WX + 0.02); ax.set_ylim(-0.02, WY + 0.02)
ax.set_xticks([0, 1, 2, 3, 3.85]); ax.set_yticks([0, 1, 2.1])
ax.set_xticklabels(["0", "1", "2", "3", "3.85"]); ax.set_yticklabels(["0", "1", "2.1"])
ax.set_xlabel("mm", labelpad=1); ax.set_ylabel("mm", labelpad=1)
ax.tick_params(length=2, pad=1.5, labelsize=6)

handles = [
    Line2D([], [], marker="o", ls="", ms=2, mfc="0.78", mec="none", label="electrode"),
    Line2D([], [], marker="o", ls="", ms=3.5, mfc="#e8590c", mec="k", mew=0.4, label="stimulation electrode"),
    Line2D([], [], marker="s", ls="", ms=3, mfc="#3b5bdb", mec="none", label="motor, up"),
    Line2D([], [], marker="s", ls="", ms=3, mfc="#c92a2a", mec="none", label="motor, down"),
    Line2D([], [], marker="o", ls="", ms=2, mfc="0.15", mec="none", label="excitatory neuron"),
    Line2D([], [], marker="o", ls="", ms=2, mfc="#7048e8", mec="none", label="inhibitory neuron"),
    Line2D([], [], color="#0b7285", lw=0.6, label="inputs of one neuron"),
]
fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=5.2, frameon=False, handletextpad=0.3,
           columnspacing=0.8, bbox_to_anchor=(0.5, 0.0))
fig.subplots_adjust(left=0.08, right=0.99, top=0.97, bottom=0.25)
fig.savefig("fig_array.pdf", dpi=600)

within = sum(np.min(np.hypot(pos[i, 0] - sx, pos[i, 1] - sy)) <= R150_WIDE for i in inputs)
print(f"neuron {j} at ({pos[j,0]:.2f}, {pos[j,1]:.2f}) mm: {within} of {K} inputs within {R150_WIDE} mm of a "
      f"stimulation electrode; median input distance {np.median(d[inputs]):.2f} mm")

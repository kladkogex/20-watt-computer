"""Re-calibration at large N: score the best parameter sets of the N = 3000 search, 8 per coupling range, on the
larger sheet, against the same Rest targets, and pick the best set per coupling range at this size.
Tests whether the coupling degeneracy (sets with J_ee spanning a factor 40 fit equally) narrows with density.

    python3 scale_calib.py N [seconds]   -> results/scale_calib_<N>.json and calib_sets_<N>.json
"""
import json, os, sys, time
import numpy as np, pandas as pd, torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "calibration"))
from rest_stats import stats_of
from netsim import Params, Topology, Sim
from calibrate import STATS, targets, loss

N = int(sys.argv[1]); secs = int(sys.argv[2]) if len(sys.argv) > 2 else 120
KEYS = ["mu", "sigma", "mu_sd", "J_ee", "J_ie", "J_ei", "J_ii", "U", "b_a"]
BINS = {"weak": (0, 0.03), "medium": (0.05, 0.12), "strong": (0.12, 0.3)}
d = pd.read_csv(os.path.join(HERE, "calib_human_search.csv")); d = d[np.isfinite(d.loss)]
cand = pd.concat([d[(d.J_ee >= lo) & (d.J_ee < hi)].sort_values("loss").head(8).assign(bin=b)
                  for b, (lo, hi) in BINS.items()], ignore_index=True)
tgt, n_sub = targets("human")
reps = 2 if N <= 300_000 else 1                                  # independent cultures per set
R = len(cand) * reps
pr = {k: np.repeat(cand[k].to_numpy(), reps) for k in KEYS}
P = Params(N=N)
t0 = time.time()
topo = Topology([2000 + s for s in range(reps)], P)
sim = Sim(topo, [r % reps for r in range(R)], ["rest"] * R, P, noise_seed=3, record_units=200, per_run=pr,
          m_max=max(4096, R * N // 250))
sim.run(5_000, game=False, plastic=False)
sim.reset_recording()
sim.run(secs * 1000, game=False, plastic=False)
trains = sim.recorded_trains()
rng = np.random.default_rng(0)
rows = []
for r in range(R):
    act = [t for t in trains[r] if len(t) / secs >= 0.1]
    if len(act) > n_sub:
        act = [act[i] for i in rng.choice(len(act), n_sub, replace=False)]
    s = stats_of(act, float(secs)); s["loss"] = loss(s, tgt)
    s.update(set=int(r // reps), bin=cand.bin.iloc[r // reps], loss3000=float(cand.loss.iloc[r // reps]),
             **{k: float(pr[k][r]) for k in KEYS})
    rows.append(s)
df = pd.DataFrame(rows)
g = df.groupby("set").agg(loss=("loss", "mean"), loss3000=("loss3000", "first"), bin=("bin", "first"),
                          J_ee=("J_ee", "first"), rate=("rate_med", "mean"), corr=("corr100", "mean"),
                          sync=("sync50_max", "mean"), nb=("nb_per_min", "mean"))
best = {}
for b in BINS:
    x = g[g.bin == b].sort_values("loss")
    i = int(x.index[0])
    best[b] = {k: float(cand[k].iloc[i]) for k in KEYS} | {"search_loss": float(x.loss.iloc[0])}
out = dict(N=N, seconds=secs, runs=R, wall_s=round(time.time() - t0), overflow=int(sim.overflow),
           per_bin={b: dict(best_loss=float(g[g.bin == b].loss.min()), median_loss=float(g[g.bin == b].loss.median()),
                            J_ee_range=[float(g[g.bin == b].J_ee.min()), float(g[g.bin == b].J_ee.max())])
                    for b in BINS},
           table=g.round(4).reset_index().to_dict("records"))
json.dump(out, open(os.path.join(HERE, "results", f"scale_calib_{N}.json"), "w"), indent=1)
json.dump(best, open(os.path.join(HERE, f"calib_sets_{N}.json"), "w"), indent=1)
print(f"N={N}: {R} runs x {secs} s, wall {out['wall_s']} s, overflow {out['overflow']}")
for b in BINS:
    pb = out["per_bin"][b]
    print(f"  {b:6s} best loss {pb['best_loss']:.2f}  median {pb['median_loss']:.2f}  (J_ee {pb['J_ee_range'][0]:.3f}-{pb['J_ee_range'][1]:.3f})")
print(g.sort_values("loss").head(6).round(3).to_string())

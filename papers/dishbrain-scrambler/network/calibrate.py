"""Calibrate the network's spontaneous activity to the DishBrain Rest recordings.

Targets: medians and interquartile ranges of the Rest statistics (../calibration/rest_stats.csv, produced by
../calibration/rest_stats.py) for one culture regime: "human" (GFP and NGN2 lines, 24 of 32 chips) or "mouse".
The model's spike trains go through the same function (rest_stats.stats_of), after subsampling the active model
units to the data's median number of active channels, so that population statistics are comparable.

Batched random search: every run of a batch is one parameter set; three rounds (broad, then around the best).
Writes calib_<regime>.json (best parameters and the fit table) and calib_<regime>_search.csv.

    python3 calibrate.py human [runs_per_round]
"""
import json, os, sys, time
import numpy as np, pandas as pd, torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "calibration"))
from rest_stats import stats_of
from netsim import Params, Topology, Sim

STATS = ["rate_med", "rate_mean", "cv_isi", "corr100", "fano100", "sync50_p99", "sync50_max", "nb_per_min"]
RANGES = {"mu": (0.2, 1.0), "sigma": (0.05, 0.6), "mu_sd": (0.0, 0.3), "J_ee": (0.005, 0.3),
          "J_ie": (0.005, 0.3), "J_ei": (0.02, 1.0), "U": (0.05, 0.6), "b_a": (0.0, 0.1)}
LOG = {"J_ee", "J_ie", "J_ei"}


def targets(regime):
    df = pd.read_csv(os.path.join(HERE, "..", "calibration", "rest_stats.csv"))
    sel = df.cell.isin(["human (GFP)", "human NGN2"]) if regime == "human" else df.cell.eq("mouse primary")
    d = df[sel]
    t = {c: (d[c].median(), d[c].quantile(.25), d[c].quantile(.75)) for c in STATS}
    return t, int(round(d.n_active.median()))


def sample(n, rng, center=None, scale=1.0):
    """Uniform (log-uniform for weights) samples, or Gaussian perturbations of randomly chosen centers."""
    out = {}
    pick = rng.integers(len(center), size=n) if center is not None else None
    for k, (lo, hi) in RANGES.items():
        if center is None:
            u = rng.random(n)
        else:
            c = np.array([x[k] for x in center])[pick]
            cu = np.log(c / lo) / np.log(hi / lo) if k in LOG else (c - lo) / (hi - lo)
            u = np.clip(cu + scale * rng.normal(size=n), 0, 1)
        out[k] = lo * (hi / lo) ** u if k in LOG else lo + (hi - lo) * u
    out["J_ii"] = out["J_ei"]
    return out


def simulate(pr, P, seeds, n_sub, seconds, rng):
    R = len(pr["mu"])
    topo = Topology(seeds, P)
    sim = Sim(topo, [r % len(seeds) for r in range(R)], ["rest"] * R, P, noise_seed=int(rng.integers(1 << 30)),
              record_units=200, per_run=pr, m_max=max(4096, R * 40))
    sim.run(5_000, game=False, plastic=False)
    sim.reset_recording()
    sim.run(seconds * 1000, game=False, plastic=False)
    trains = sim.recorded_trains()
    overflow = int(sim.overflow)
    rows = []
    for r in range(R):
        tr = trains[r]
        act = [t for t in tr if len(t) / seconds >= 0.1]
        if len(act) > n_sub:
            idx = rng.choice(len(act), n_sub, replace=False)
            act = [act[i] for i in idx]
        s = stats_of(act, float(seconds))
        s["frac_units_active"] = sum(len(t) / seconds >= 0.1 for t in tr) / len(tr)
        rows.append(s)
    del sim, topo
    torch.cuda.empty_cache()
    return rows, overflow


def loss(row, tgt):
    L = 0.0
    for c in STATS:
        med, q1, q3 = tgt[c]
        v = row.get(c, np.nan)
        if v is None or not np.isfinite(v):
            return np.inf
        L += ((v - med) / max(q3 - q1, 1e-3)) ** 2
    return L


if __name__ == "__main__":
    regime = sys.argv[1] if len(sys.argv) > 1 else "human"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 512
    tgt, n_sub = targets(regime)
    print(f"regime {regime}: data medians [IQR]; active units per recording {n_sub}")
    for c in STATS:
        print(f"  {c:11s} {tgt[c][0]:.4f} [{tgt[c][1]:.4f}, {tgt[c][2]:.4f}]")
    P = Params()
    rng = np.random.default_rng(1)
    seeds = list(range(8))
    allrows, best = [], None
    for rnd, (scale, secs) in enumerate([(None, 60), (0.12, 90), (0.05, 120)]):
        t0 = time.time()
        pr = sample(n, rng) if best is None else sample(n, rng, center=best, scale=scale)
        rows, ovf = simulate(pr, P, seeds, n_sub, secs, rng)
        for r, row in enumerate(rows):
            row.update({k: float(pr[k][r]) for k in pr}); row["loss"] = loss(row, tgt); row["round"] = rnd
        allrows += rows
        df = pd.DataFrame(allrows).sort_values("loss")
        best = df.head(16).to_dict("records")
        print(f"round {rnd}: {n} sets x {secs} s in {time.time() - t0:.0f} s (overflow {ovf}); best loss {df.loss.iloc[0]:.2f}")
    df.to_csv(os.path.join(HERE, f"calib_{regime}_search.csv"), index=False)
    # confirm the best set on fresh seeds and noise, 10 minutes like a Rest recording
    b = df.iloc[0]
    pr = {k: np.full(64, b[k]) for k in list(RANGES) + ["J_ii"]}
    rows, ovf = simulate(pr, P, list(range(100, 116)), n_sub, 600, rng)
    conf = pd.DataFrame(rows)
    fit = {c: dict(data_median=tgt[c][0], data_q1=tgt[c][1], data_q3=tgt[c][2],
                   model_median=float(conf[c].median()), model_q1=float(conf[c].quantile(.25)),
                   model_q3=float(conf[c].quantile(.75))) for c in STATS}
    out = dict(regime=regime, n_active_sub=n_sub, params={k: float(b[k]) for k in list(RANGES) + ["J_ii"]},
               search_loss=float(b.loss), fit=fit, frac_units_active=float(conf.frac_units_active.median()),
               overflow=ovf)
    json.dump(out, open(os.path.join(HERE, f"calib_{regime}.json"), "w"), indent=1)
    print("\nbest parameters:", json.dumps(out["params"]))
    print(f"{'statistic':11s} {'data median [IQR]':>28s} {'model median [IQR] (64 runs, 10 min)':>40s}")
    for c in STATS:
        f = fit[c]
        print(f"{c:11s} {f['data_median']:9.4f} [{f['data_q1']:.4f}, {f['data_q3']:.4f}]   "
              f"{f['model_median']:9.4f} [{f['model_q1']:.4f}, {f['model_q3']:.4f}]")

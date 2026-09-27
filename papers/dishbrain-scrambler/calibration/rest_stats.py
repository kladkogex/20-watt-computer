"""Statistics of spontaneous activity in the DishBrain Rest recordings (Kagan et al. 2022, OSF 5u6qv).

Data: spike_trains_all_rest.pkl (182 MB, downloaded once into ./cache/, git-ignored): one row per Rest
recording, spike times in frames (20 kHz) per recording channel. Channel positions are not in the file, so
distance-dependent statistics cannot be computed from it.

For each recording, over the active channels (>= 0.1 Hz, the usual MEA criterion):
  rate_med, rate_mean   firing rate per active channel, Hz
  frac_active           active channels / recorded channels
  cv_isi                median over channels of the inter-spike-interval CV (irregularity; > 1 = bursty)
  corr100               mean pairwise Pearson correlation of spike counts in 100 ms bins
  fano100               Fano factor of the summed population count in 100 ms bins (synchrony)
  sync50_p99, sync50_max  99th percentile and maximum fraction of active channels firing in one 50 ms window
  nb_per_min            network events per minute: 50 ms windows in which >= 20 % of active channels fire
Prints the medians and interquartile ranges per cell type and writes rest_stats.csv.

    python3 rest_stats.py        # needs numpy, pandas
"""
import os, urllib.request
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PKL = os.path.join(HERE, "cache", "spike_trains_all_rest.pkl")
if not os.path.exists(PKL):
    os.makedirs(os.path.dirname(PKL), exist_ok=True)
    urllib.request.urlretrieve("https://osf.io/download/r643h/", PKL)
FS = 20000.0


def cell_type(tag):
    t = tag.lower()
    if "ngn2" in t:
        return "human NGN2"
    if "gfp" in t or "tdt" in t:
        return "human (GFP)"
    return "mouse primary"


def stats_of(trains, T):
    """trains: list of spike-time arrays (s) of the recorded units; T: duration (s)."""
    rates = np.array([len(t) / T for t in trains])
    act = [np.asarray(t) for t, r in zip(trains, rates) if r >= 0.1]
    out = dict(n_rec=len(trains), n_active=len(act), frac_active=len(act) / max(1, len(trains)))
    if len(act) < 5:
        return out
    r = rates[rates >= 0.1]
    cvs = []
    for t in act:
        if t.size > 5:
            isi = np.diff(np.sort(t)); cvs.append(isi.std() / isi.mean())
    edges100 = np.arange(0, T + 1e-9, 0.1)
    C = np.array([np.histogram(t, edges100)[0] for t in act], float)
    pop = C.sum(0)
    Z = C - C.mean(1, keepdims=True); sd = Z.std(1); ok = sd > 0
    Z = Z[ok] / sd[ok, None]
    R = (Z @ Z.T) / Z.shape[1]
    n = R.shape[0]
    corr = (R.sum() - np.trace(R)) / (n * (n - 1)) if n > 1 else np.nan
    nwin = int(np.ceil(T / 0.05))
    co = np.zeros(nwin)
    for t in act:
        co[np.unique(np.minimum((t / 0.05).astype(int), nwin - 1))] += 1
    frac = co / len(act)
    ev = frac >= 0.2
    starts = np.flatnonzero(ev & ~np.r_[False, ev[:-1]])
    out.update(rate_med=float(np.median(r)), rate_mean=float(r.mean()), cv_isi=float(np.median(cvs)),
               corr100=float(corr), fano100=float(pop.var() / pop.mean()),
               sync50_p99=float(np.percentile(frac, 99)), sync50_max=float(frac.max()),
               nb_per_min=float(starts.size / T * 60))
    return out


if __name__ == "__main__":
    x = pd.read_pickle(PKL)
    rows = []
    for _, rec in x.iterrows():
        trains = [np.asarray(v, float) / FS for v in rec.spike_times.values()]
        T = max((t.max() for t in trains if t.size), default=600.0)
        T = max(T, 1.0)
        s = stats_of(trains, T)
        s.update(chip_id=rec.chip_id, date=rec.date, tag=rec.tag, cell=cell_type(rec.tag), T=T)
        rows.append(s)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(HERE, "rest_stats.csv"), index=False)
    cols = ["n_active", "frac_active", "rate_med", "rate_mean", "cv_isi", "corr100", "fano100",
            "sync50_p99", "sync50_max", "nb_per_min"]
    print(f"{len(df)} Rest recordings, {df.chip_id.nunique()} chips; median [IQR] per cell type")
    for cell, g in [("all", df)] + list(df.groupby("cell")):
        print(f"\n{cell} (recordings {len(g)}, chips {g.chip_id.nunique()})")
        for c in cols:
            v = g[c].dropna()
            print(f"  {c:11s} {v.median():8.3f}  [{v.quantile(.25):.3f}, {v.quantile(.75):.3f}]")

"""Summary of the large-N tests (results/scale_evoked_<N>.json, results/scale_train_<N>.json) as quoted in the paper.

Evoked: fraction of (culture, electrode, region) cases with z > 3 and z < -3, mean relative change of motor counts.
Up/down: fraction of (culture, electrode) cases with |z| > 3 for the up-minus-down change, and the correlation of the
per-electrode up-minus-down change with correct steering. Electrodes are ordered by ball height relative to the
paddle (k = floor(8 (y - p + 1/2))), so correct steering (ball below the paddle -> paddle down) is up-minus-down
increasing with k; a negative correlation is steering away from the ball. Correlations of the mean pattern between
sizes compare independent topologies.

    python3 scale_summary.py
"""
import itertools, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SIZES = [100_000, 300_000, 1_000_000]
steer = np.arange(8) - 3.5


def load(kind, N):
    f = os.path.join(HERE, "results", f"scale_{kind}_{N}.json")
    return json.load(open(f)) if os.path.exists(f) else None


print("Single pulses (50 ms after vs before)")
means = {}
for N in SIZES:
    d = load("evoked", N)
    if d is None:
        continue
    for pulse in ("75 mV", "150 mV"):
        rows = [r for r in d["rows"] if r["pulse"] == pulse]
        V = np.array([r["ud_per_electrode"] for r in rows]); means[(N, pulse)] = V.mean(0)
        pos = max(r["frac_z_pos"] for r in rows); neg = [r["frac_z_neg"] for r in rows]
        rel = [r["rel_change"] for r in rows]; ud3 = [r["frac_ud_z3"] for r in rows]
        rs = [np.corrcoef(v, steer)[0, 1] for v in V]
        print(f"  N={N:>9,d} {pulse:6s} cultures={d['cultures']}  z>3 max {pos:.2f}  z<-3 {min(neg):.2f}-{max(neg):.2f}"
              f"  rel. change {min(rel):+.3f}..{max(rel):+.3f}  up-down |z|>3 max {max(ud3):.2f}"
              f"  r(steer) mean {np.mean(rs):+.2f}, {sum(x < 0 for x in rs)}/9 negative, of mean pattern"
              f" {np.corrcoef(V.mean(0), steer)[0, 1]:+.2f}")
for p in ("75 mV", "150 mV"):
    pairs = [(a, b) for a, b in itertools.combinations(SIZES, 2) if (a, p) in means and (b, p) in means]
    print(f"  {p} pattern correlation between sizes: " +
          ", ".join(f"{a:.0e}/{b:.0e} {np.corrcoef(means[(a, p)], means[(b, p)])[0, 1]:+.2f}" for a, b in pairs))

print("\n40 Hz place-code trains (500 ms, up-minus-down vs the 500 ms before)")
tmeans = {}
for N in SIZES:
    d = load("train", N)
    if d is None:
        continue
    V = np.array([r["ud_per_electrode"] for r in d["rows"]]); tmeans[N] = V.mean(0)
    fr = [r["frac_abs_z3"] for r in d["rows"]]; ss = [r["same_sign_across_cultures"] for r in d["rows"]]
    rs = [np.corrcoef(v, steer)[0, 1] for v in V]
    print(f"  N={N:>9,d} cultures={d['cultures']} trials={d['trials']}  |z|>3 max {max(fr):.3f} mean {np.mean(fr):.3f}"
          f"  same sign across cultures {np.mean(ss):.2f}  mean |change| {np.abs(V).mean():.1f} spikes"
          f"  r(steer) mean {np.mean(rs):+.2f}, {sum(x < 0 for x in rs)}/9 negative, of mean pattern"
          f" {np.corrcoef(V.mean(0), steer)[0, 1]:+.2f}")
pairs = list(itertools.combinations(sorted(tmeans), 2))
if pairs:
    print("  pattern correlation between sizes: " +
          ", ".join(f"{a:.0e}/{b:.0e} {np.corrcoef(tmeans[a], tmeans[b])[0, 1]:+.2f}" for a, b in pairs))

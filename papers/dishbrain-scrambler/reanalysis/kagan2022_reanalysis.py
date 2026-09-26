"""Re-analysis of the published DishBrain gameplay data (Kagan et al. 2022, feedback-condition study).

Data: in_vitro_cells_sentience_2.pkl from the authors' OSF deposit (doi:10.17605/osf.io/5u6qv),
one row per rally: chip, session, time in session, number of hits (hit_count), condition.
Groups in the file: 0 = Stimulus, 1 = Silent (tags "no_feedback"), 2 = No feedback (tags "open_loop"),
4 = controls; control == 1 marks each chip's Rest session (no stimulation). T1 = first 5 minutes,
T2 = remaining 15 (column "half", as in the authors' notebook). Unit of analysis: the chip (culture).

    python3 kagan2022_reanalysis.py          # needs pandas, scipy; downloads the 20 MB file once
"""
import os, urllib.request
import numpy as np, pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
PKL = os.path.join(HERE, "cache", "in_vitro_cells_sentience_2.pkl")
if not os.path.exists(PKL):
    os.makedirs(os.path.dirname(PKL), exist_ok=True)
    urllib.request.urlretrieve("https://osf.io/download/zq45a/", PKL)

df = pd.read_pickle(PKL)
df = df[df.group.isin([0, 1, 2])].copy()
NAME = {0: "Stimulus", 1: "Silent", 2: "No feedback"}
df["cell"] = df.tag.str.lower().str.extract(r"^(gfp|ngn2|prim)")[0]
df["p1"] = (df.hit_count >= 1).astype(float)
game, rest = df[df.control == 0], df[df.control == 1]

print("1. Chips per condition and cell type")
c = df.groupby(["group", "cell"]).chip_id.nunique().unstack(fill_value=0)
c.index = [NAME[i] for i in c.index]
print(c.to_string(), "\n")

print("2. Hits per rally (chip means): Rest, gameplay T1 and T2; within-session change T2-T1")
g = game.groupby(["group", "chip_id", "half"]).hit_count.mean().unstack("half").dropna()
r = rest.groupby(["group", "chip_id"]).hit_count.mean()
for k in (0, 1, 2):
    x = g.loc[k]; d = x[1] - x[0]
    print(f"   {NAME[k]:12s} n={len(x):2d}  rest {r.loc[k].mean():.3f}  T1 {x[0].mean():.3f}  T2 {x[1].mean():.3f}"
          f"  T2-T1 {d.mean():+.3f} (Wilcoxon p={stats.wilcoxon(d).pvalue:.2g})")
print(f"   end-of-session (T2) levels differ between conditions? Kruskal-Wallis p="
      f"{stats.kruskal(*[g.loc[k][1] for k in (0, 1, 2)]).pvalue:.2g}")
print(f"   Rest baselines differ between condition groups? Kruskal-Wallis p="
      f"{stats.kruskal(*[r.loc[k] for k in (0, 1, 2)]).pvalue:.2g}\n")

print("3. Within-session change T2-T1 by cell type (hits per rally)")
gc = game.groupby(["group", "cell", "chip_id", "half"]).hit_count.mean().unstack("half").dropna()
d = (gc[1] - gc[0]).groupby(["group", "cell"]).agg(["mean", "count"]).round(3)
d.index = [f"{NAME[a]}, {b}" for a, b in d.index]
print(d.to_string(), "\n")

print("4. Within-session change split: first return of a rally vs continuation after a hit")
def split(h):
    h = h.to_numpy(); n1 = (h >= 1).sum()
    return pd.Series(dict(p1=(h >= 1).mean(), pc=(h >= 2).sum() / n1 if n1 else np.nan))
s = game.groupby(["group", "chip_id", "half"]).hit_count.apply(split).unstack([-2, -1]).dropna()
for k in (0, 1, 2):
    y = s.loc[k]; d1 = y[(1, "p1")] - y[(0, "p1")]; dc = y[(1, "pc")] - y[(0, "pc")]
    print(f"   {NAME[k]:12s} first return {d1.mean():+.3f} (p={stats.wilcoxon(d1).pvalue:.2g})"
          f"   continuation {dc.mean():+.3f} (p={stats.wilcoxon(dc).pvalue:.2g})")
print()

print("5. Persistence across a miss: lag-1 correlation of consecutive rally lengths within a recording")
print("   (linear trend removed per recording; per chip, gameplay minus the same chip's Rest)")
rows = []
for key, gg in df.groupby(["chip_id", "date", "session_num", "control", "tag"]):   # one recording
    gg = gg.sort_values("elapse_seconds"); h = gg.hit_count.to_numpy(float); tt = gg.elapse_seconds.to_numpy()
    if len(h) >= 20 and h.std() > 0:
        res = h - np.polyval(np.polyfit(tt, h, 1), tt)
        rows.append((gg.group.iloc[0], key[0], key[3], np.corrcoef(res[:-1], res[1:])[0, 1]))
R = pd.DataFrame(rows, columns=["group", "chip", "rest", "r"])
c = R.groupby(["group", "chip", "rest"]).r.mean().unstack("rest").dropna(); c["d"] = c[0] - c[1]
for k in (0, 1, 2):
    x = c.loc[k]
    print(f"   {NAME[k]:12s} chips={len(x):2d}  rest r={x[1].mean():+.3f}  game r={x[0].mean():+.3f}"
          f"  change {x['d'].mean():+.3f}+/-{x['d'].sem():.3f}  (Wilcoxon p={stats.wilcoxon(x['d']).pvalue:.2g};"
          f" lower in {(x['d'] < 0).sum()}/{len(x)} chips)")
print(f"   conditions differ: Kruskal-Wallis p={stats.kruskal(*[c.loc[k]['d'] for k in (0, 1, 2)]).pvalue:.2g};"
      f" Stimulus vs Silent Mann-Whitney p={stats.mannwhitneyu(c.loc[0]['d'], c.loc[1]['d']).pvalue:.2g}")
print("   caveat: Rest persistence of the Stimulus chips is itself higher than in the other groups, the same")
print("   baseline imbalance as in section 2; gameplay persistence alone does not differ in the scrambler's favour")

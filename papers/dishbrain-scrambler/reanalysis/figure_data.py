"""Data for the re-analysis figure: hits per rally (chip means) at Rest, T1 (first 5 min of gameplay) and T2 (last 15),
mean and s.e.m. over chips, per feedback condition. Same selection as kagan2022_reanalysis.py (chips with both T1 and T2).

    python3 figure_data.py        -> levels.dat (columns: x condition phase mean sem n) and levels_<condition>.dat
"""
import os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_pickle(os.path.join(HERE, "cache", "in_vitro_cells_sentience_2.pkl"))
df = df[df.group.isin([0, 1, 2])]
NAME = {0: "Stimulus", 1: "Silent", 2: "NoFeedback"}
game, rest = df[df.control == 0], df[df.control == 1]
g = game.groupby(["group", "chip_id", "half"]).hit_count.mean().unstack("half").dropna()
r = rest.groupby(["group", "chip_id"]).hit_count.mean()
with open(os.path.join(HERE, "levels.dat"), "w") as f:
    f.write("x condition phase mean sem n\n")
    for k in (0, 1, 2):
        chips = g.loc[k].index
        cols = {"Rest": r.loc[k].reindex(chips).dropna(), "T1": g.loc[k][0], "T2": g.loc[k][1]}
        for j, (ph, v) in enumerate(cols.items()):
            f.write(f"{j} {NAME[k]} {ph} {v.mean():.4f} {v.sem():.4f} {len(v)}\n")
        with open(os.path.join(HERE, f"levels_{NAME[k]}.dat"), "w") as h:
            h.write("x mean sem\n")
            for j, v in enumerate(cols.values()):
                h.write(f"{j} {v.mean():.4f} {v.sem():.4f}\n")
print(open(os.path.join(HERE, "levels.dat")).read())

"""Single-pulse sensory -> motor test at large N, with the size-specific calibrated sets (calib_sets_<N>.json).

For each coupling set and recruitment assumption, 75 mV and 150 mV pulses at each of the 8 stimulation electrodes;
motor-region spike counts in the 50 ms after the pulse vs. the 50 ms before, over trials. Reports the mean change,
the fraction of (culture, electrode, region) cases with z > 3 and z < -3, and the net up-minus-down drive.

    python3 scale_evoked.py N [cultures] [trials]   -> results/scale_evoked_<N>.json
"""
import json, os, sys, time
import numpy as np, torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from netsim import Params, Topology, Sim

RECRUIT = {"small": (0.05, 1.2, 0.10), "wide near-threshold": (0.12, 0.7, 0.20), "wide": (0.12, 1.2, 0.20)}
N = int(sys.argv[1]); cultures = int(sys.argv[2]) if len(sys.argv) > 2 else 2
trials = int(sys.argv[3]) if len(sys.argv) > 3 else 30
sets = json.load(open(os.path.join(HERE, f"calib_sets_{N}.json")))
combos = [(sn, rn) for sn in sets for rn in RECRUIT]
per = cultures * 2                                    # half 75 mV, half 150 mV
R = len(combos) * per
pr = {}
for sn, rn in combos:
    c = {k: v for k, v in sets[sn].items() if k != "search_loss"}
    r75, k75, r150 = RECRUIT[rn]
    for _ in range(per):
        for k, v in list(c.items()) + [("r75", r75), ("kick75", k75), ("r150", r150)]:
            pr.setdefault(k, []).append(v)
pr = {k: np.array(v) for k, v in pr.items()}
P = Params(N=N)
t0 = time.time()
topo = Topology([3000 + s for s in range(cultures)], P)
sim = Sim(topo, [(r // 1) % cultures for r in range(R)], ["rest"] * R, P, noise_seed=11, per_run=pr,
          m_max=max(8192, R * N // 100))
sim.run(10_000, game=False, plastic=False)
strong = torch.tensor([(r % per) >= cultures for r in range(R)], device="cuda")
k75 = torch.tensor(pr["kick75"], device="cuda", dtype=torch.float32)
acc = {n: torch.zeros(R, 8, 4, device="cuda") for n in ("pre", "post", "pre2", "post2")}
ud1 = torch.zeros(R, 8, device="cuda"); ud2 = torch.zeros(R, 8, device="cuda")   # (up - down) change per trial
UPM = torch.tensor([-1.0, 1.0, -1.0, 1.0], device="cuda")
for tr in range(trials):
    for k in range(8):
        cnt = torch.zeros(120, R, 4, device="cuda")
        for t in range(120):
            sim.m75.zero_(); sim.m150.zero_()
            if t == 60:
                sim.m75[:, k] = torch.where(strong, 0.0, k75)
                sim.m150[:, k] = strong.float()
            spk = sim._neurons()
            cnt[t] = (spk.gather(1, sim.mot_idx).float().unsqueeze(-1) * sim.mot_reg).sum(1)
        a, b = cnt[5:55].sum(0), cnt[62:112].sum(0)
        acc["pre"][:, k] += a; acc["post"][:, k] += b; acc["pre2"][:, k] += a * a; acc["post2"][:, k] += b * b
        u = ((b - a) * UPM).sum(1); ud1[:, k] += u; ud2[:, k] += u * u
pre, post = acc["pre"] / trials, acc["post"] / trials
var = (acc["pre2"] / trials - pre ** 2) + (acc["post2"] / trials - post ** 2)
z = ((post - pre) / (var.clamp(min=1e-9) / trials).sqrt()).cpu().numpy()
dd = (post - pre).cpu().numpy(); base = pre.cpu().numpy()
udm = ud1 / trials; zud = (udm / ((ud2 / trials - udm ** 2).clamp(min=1e-9) / trials).sqrt()).cpu().numpy(); udm = udm.cpu().numpy()
rows = []
for i, (sn, rn) in enumerate(combos):
    for lab, off in (("75 mV", 0), ("150 mV", cultures)):
        sl = slice(i * per + off, i * per + off + cultures)
        ud = dd[sl][:, :, [1, 3]].sum(2) - dd[sl][:, :, [0, 2]].sum(2)
        rows.append(dict(set=sn, recruit=rn, pulse=lab, base=float(base[sl].mean()), change=float(dd[sl].mean()),
                         rel_change=float(dd[sl].mean() / max(base[sl].mean(), 1e-9)),
                         frac_z_pos=float((z[sl] > 3).mean()), frac_z_neg=float((z[sl] < -3).mean()),
                         updown_abs=float(np.abs(ud).mean()), updown_z_max=float(np.abs(z[sl]).max()),
                         ud_per_electrode=udm[sl].mean(0).round(3).tolist(), frac_ud_z3=float((np.abs(zud[sl]) > 3).mean()),
                         ud_z_per_electrode=zud[sl].mean(0).round(2).tolist()))
out = dict(N=N, cultures=cultures, trials=trials, wall_s=round(time.time() - t0), overflow=int(sim.overflow), rows=rows)
json.dump(out, open(os.path.join(HERE, "results", f"scale_evoked_{N}.json"), "w"), indent=1)
print(f"N={N}: evoked test, {R} runs, {trials} trials x 8 electrodes, wall {out['wall_s']} s, overflow {out['overflow']}")
print(f"{'set':7s} {'recruit':20s} {'pulse':6s} {'base':>7s} {'change':>8s} {'rel':>7s} {'z>3':>5s} {'z<-3':>5s} {'|z_ud|>3':>8s}  up-down per electrode")
for r in rows:
    print(f"{r['set']:7s} {r['recruit']:20s} {r['pulse']:6s} {r['base']:7.2f} {r['change']:+8.3f} {r['rel_change']:+7.3f} "
          f"{r['frac_z_pos']:5.2f} {r['frac_z_neg']:5.2f} {r['frac_ud_z3']:8.2f}  {r['ud_per_electrode']}")

"""Place-code train test: does the sensory code of play reach the motor regions differentially?

For each stimulation electrode, 75 mV pulses at 40 Hz for 500 ms (the rate near the paddle wall); the up-minus-down
motor count over the train is compared with the 500 ms before, per trial. Per (set, recruitment): mean up-down change
per electrode, its z over trials, and the fraction of (culture, electrode) cases with |z| > 3. A consistent,
electrode-specific sign is what would let the ball position steer the paddle.

    python3 scale_train.py N [cultures] [trials]   -> results/scale_train_<N>.json
"""
import json, os, sys, time
import numpy as np, torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from netsim import Params, Topology, Sim

RECRUIT = {"small": (0.05, 1.2, 0.10), "wide near-threshold": (0.12, 0.7, 0.20), "wide": (0.12, 1.2, 0.20)}
N = int(sys.argv[1]); cultures = int(sys.argv[2]) if len(sys.argv) > 2 else 4
trials = int(sys.argv[3]) if len(sys.argv) > 3 else 20
sets = json.load(open(os.path.join(HERE, f"calib_sets_{N}.json")))
combos = [(sn, rn) for sn in sets for rn in RECRUIT]
R = len(combos) * cultures
pr = {}
for sn, rn in combos:
    c = {k: v for k, v in sets[sn].items() if k != "search_loss"}
    r75, k75, r150 = RECRUIT[rn]
    for _ in range(cultures):
        for k, v in list(c.items()) + [("r75", r75), ("kick75", k75), ("r150", r150)]:
            pr.setdefault(k, []).append(v)
pr = {k: np.array(v) for k, v in pr.items()}
P = Params(N=N)
t0 = time.time()
topo = Topology([4000 + s for s in range(cultures)], P)
sim = Sim(topo, [r % cultures for r in range(R)], ["rest"] * R, P, noise_seed=13, per_run=pr,
          m_max=max(8192, R * N // 100))
sim.run(10_000, game=False, plastic=False)
k75 = torch.tensor(pr["kick75"], device="cuda", dtype=torch.float32)
UPM = torch.tensor([-1.0, 1.0, -1.0, 1.0], device="cuda")
s1 = torch.zeros(R, 8, device="cuda"); s2 = torch.zeros(R, 8, device="cuda")
for tr in range(trials):
    for k in range(8):
        pre = torch.zeros(R, device="cuda"); post = torch.zeros(R, device="cuda")
        for t in range(1000):
            sim.m75.zero_(); sim.m150.zero_()
            if t >= 500 and (t - 500) % 25 == 0:
                sim.m75[:, k] = k75
            spk = sim._neurons()
            ud = ((spk.gather(1, sim.mot_idx).float().unsqueeze(-1) * sim.mot_reg).sum(1) * UPM).sum(1)
            if t < 500:
                pre += ud
            else:
                post += ud
        d = post - pre
        s1[:, k] += d; s2[:, k] += d * d
m = s1 / trials
z = (m / ((s2 / trials - m ** 2).clamp(min=1e-9) / trials).sqrt()).cpu().numpy(); m = m.cpu().numpy()
rows = []
for i, (sn, rn) in enumerate(combos):
    sl = slice(i * cultures, (i + 1) * cultures)
    rows.append(dict(set=sn, recruit=rn, ud_per_electrode=m[sl].mean(0).round(2).tolist(),
                     z_per_electrode=z[sl].mean(0).round(2).tolist(), frac_abs_z3=float((np.abs(z[sl]) > 3).mean()),
                     same_sign_across_cultures=float(np.mean(np.abs(np.sign(m[sl]).mean(0)) == 1))))
out = dict(N=N, cultures=cultures, trials=trials, wall_s=round(time.time() - t0), overflow=int(sim.overflow), rows=rows)
json.dump(out, open(os.path.join(HERE, "results", f"scale_train_{N}.json"), "w"), indent=1)
print(f"N={N}: 40 Hz place-code trains, {R} runs, {trials} trials x 8 electrodes, wall {out['wall_s']} s")
print(f"{'set':7s} {'recruit':20s} {'|z|>3':>6s} {'same sign':>9s}  up-down change per electrode (spikes per 500 ms)")
for r in rows:
    print(f"{r['set']:7s} {r['recruit']:20s} {r['frac_abs_z3']:6.2f} {r['same_sign_across_cultures']:9.2f}  {r['ud_per_electrode']}")

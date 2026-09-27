"""Play DishBrain sessions with the calibrated network and analyse them like the published data.

    python3 run_sessions.py <experiment> [cultures]

Experiments (all use the calibrated parameters in calib_human.json):
  evoked     sensory -> motor diagnostic: 75 / 150 mV pulses at each stimulation electrode, spike counts in the
             four motor regions 5-55 ms after the pulse vs. before (no game, no plasticity)
  fitH       Rest sessions (10 min, no stimulation) for a range of paddle half-lengths H; pick H so that the
             Rest hits per rally match the data (0.73, pooled over the three condition groups)
  main       Rest (10 min) and Stimulus / Silent / No feedback (20 min) on the same cultures, one plasticity rule
  rules      Stimulus / Silent / No feedback under each plasticity rule and step size
  recruit    Stimulus under a range of recruitment assumptions (r75, r150, 75 mV kick, blanking)
  protocols  the proposed protocols B-E next to Stimulus
Results: results/<experiment>.npz (per run: condition, culture, parameters, outcome log) and a printed table.
Readout as in the re-analysis of Kagan et al. 2022: hits per rally per culture in T1 (first 5 min of gameplay)
and T2 (remaining 15), T2 - T1 per culture, Wilcoxon signed-rank test; Kruskal-Wallis across conditions at T2.
"""
import json, os, sys, time
import numpy as np, torch
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from netsim import Params, Topology, Sim, PROTOCOLS

RES = os.path.join(HERE, "results")
os.makedirs(RES, exist_ok=True)
REST_TARGET = 0.73            # hits per rally at Rest, data (per-chip means 0.67, 0.78, 0.79 in the three groups)
BURN_MS, GAME_MS, REST_MS = 60_000, 1_200_000, 600_000


SET = os.environ.get("CALSET", "weak")      # calibrated parameter set: weak / medium / strong E->E coupling


def calibrated(name=None):
    """One of three parameter sets that fit the Rest statistics equally well (calib_sets.json) but differ in
    recurrent coupling, which the Rest data do not constrain."""
    sets = json.load(open(os.path.join(HERE, "calib_sets.json")))
    c = dict(sets[name or SET]); c.pop("search_loss", None)
    return c


def base_params(**kw):
    p = Params(**{k: v for k, v in kw.items() if k in Params.__dataclass_fields__})
    return p


def play(conds, cultures, P, per_run_extra=None, minutes=None, seed=0):
    """conds: list of condition names; every culture plays every condition (paired design).
    per_run_extra: dict of per-run parameter arrays (length len(conds) * cultures) or scalars."""
    runs = [(c, s) for c in conds for s in range(cultures)]
    R = len(runs)
    cal = calibrated()
    pr = {k: np.full(R, v) for k, v in cal.items()}
    for k, v in (per_run_extra or {}).items():
        pr[k] = np.broadcast_to(np.asarray(v, float), (R,)).copy()
    topo = Topology([1000 + s for s in range(cultures)], P)
    sim = Sim(topo, [s for _, s in runs], [c for c, _ in runs], P, noise_seed=seed, per_run=pr,
              m_max=max(4096, R * 60))
    t0 = time.time()
    sim.run(BURN_MS, game=False, plastic=False)
    ms = minutes * 60_000 if minutes else GAME_MS
    sim.clock.zero_()
    sim.run(ms, game=True, plastic=True)
    torch.cuda.synchronize()
    wall = time.time() - t0
    out = sim.outcomes()
    info = dict(R=R, wall_s=wall, overflow=int(sim.overflow), m_max=sim.m_max,
                rate_hz=float(sim.spk.float().mean()) * 1000)
    del sim, topo
    torch.cuda.empty_cache()
    return runs, pr, out, info


def rallies(ev, split_ms=300_000, end_ms=None):
    """Hits per rally in T1 and T2 from an outcome log (t_ms, hit, ...). A rally ends at a miss."""
    t, h = ev[:, 0], ev[:, 1]
    res = {1: [], 2: []}
    n = 0
    for ti, hi in zip(t, h):
        if hi > 0.5:
            n += 1
        else:
            res[1 if ti < split_ms else 2].append(n)
            n = 0
    return (np.mean(res[1]) if res[1] else np.nan, np.mean(res[2]) if res[2] else np.nan,
            len(res[1]) + len(res[2]))


def kappa_emergent(ev):
    """Squared weight displacement during the feedback window after hits and after misses, and per approach."""
    t, h, d0, d1 = ev[:, 0], ev[:, 1], ev[:, 2], ev[:, 3]
    fb = np.where(np.isfinite(d1), d1 - d0, 0.0)
    nxt = np.r_[d0[1:], np.nan]
    drift = np.where(np.isfinite(d1), nxt - d1, nxt - d0)          # between feedback end and the next outcome
    hit, miss = h > 0.5, h < 0.5
    return (np.nanmean(fb[hit]) if hit.any() else np.nan, np.nanmean(fb[miss]) if miss.any() else np.nan,
            np.nanmean(drift))


def table(runs, out, label=""):
    conds = list(dict.fromkeys(c for c, _ in runs))
    rows = {}
    print(f"\n{label}")
    print(f"{'condition':14s} {'n':>3s} {'T1':>6s} {'T2':>6s} {'T2-T1':>8s} {'p':>8s} {'rallies':>8s} "
          f"{'dW2 hit':>9s} {'dW2 miss':>9s} {'drift':>9s} {'kappa':>7s}")
    for c in conds:
        idx = [i for i, (cc, _) in enumerate(runs) if cc == c]
        r = np.array([rallies(out[i]) for i in idx])
        k = np.array([kappa_emergent(out[i]) if len(out[i]) else (np.nan,) * 3 for i in idx])
        d = r[:, 1] - r[:, 0]
        ok = np.isfinite(d)
        p = stats.wilcoxon(d[ok]).pvalue if ok.sum() > 5 and np.any(d[ok] != 0) else np.nan
        kh, km, dr = np.nanmean(k[:, 0]), np.nanmean(k[:, 1]), np.nanmean(k[:, 2])
        kap = (kh + dr) / (km + dr) if np.isfinite(kh) and np.isfinite(km) and (km + dr) > 0 else np.nan
        rows[c] = dict(T1=np.nanmean(r[:, 0]), T2=np.nanmean(r[:, 1]), gain=np.nanmean(d),
                       gain_se=np.nanstd(d) / np.sqrt(max(ok.sum(), 1)), p=p, rallies=np.nanmean(r[:, 2]),
                       dW_hit=kh, dW_miss=km, drift=dr, kappa=kap, T2_values=r[:, 1])
        print(f"{c:14s} {len(idx):3d} {rows[c]['T1']:6.3f} {rows[c]['T2']:6.3f} {rows[c]['gain']:+8.3f} "
              f"{p:8.2g} {rows[c]['rallies']:8.1f} {kh:9.3g} {km:9.3g} {dr:9.3g} {kap:7.3f}")
    game = [c for c in conds if c != "rest"]
    if len(game) > 1:
        vals = [rows[c]["T2_values"][np.isfinite(rows[c]["T2_values"])] for c in game]
        print(f"   T2 levels differ across {', '.join(game)}? Kruskal-Wallis p = {stats.kruskal(*vals).pvalue:.2g}")
    return rows


def save(name, runs, pr, out, info, extra=None):
    np.savez_compressed(os.path.join(RES, f"{name}.npz"), cond=np.array([c for c, _ in runs]),
                        culture=np.array([s for _, s in runs]),
                        params=json.dumps({k: np.asarray(v).tolist() for k, v in pr.items()}),
                        info=json.dumps(info | (extra or {})),
                        ev=np.array([o for o in out], dtype=object), allow_pickle=True)


# ---------------------------------------------------------------------------------------------- experiments
RECRUIT = {  # (r75 mm, 75 mV kick in threshold units, r150 mm): assumptions, swept
    "near-threshold small": (0.05, 0.7, 0.10), "default": (0.05, 1.2, 0.10),
    "wide": (0.12, 1.2, 0.20), "wide near-threshold": (0.12, 0.7, 0.20), "widest": (0.20, 1.5, 0.23)}


def evoked(cultures=8, trials=40):
    """Motor-region response to single pulses at each stimulation electrode, for every calibrated set and
    recruitment assumption. z: mean change / its standard error; up-down: signed drive of the paddle."""
    P = base_params()
    combos = [(sn, rn) for sn in ("weak", "medium", "strong") for rn in RECRUIT]
    R = len(combos) * cultures * 2
    pr = {}
    for (sn, rn) in combos:
        c = calibrated(sn); r75, k75, r150 = RECRUIT[rn]
        for _ in range(cultures * 2):
            for k, v in list(c.items()) + [("r75", r75), ("kick75", k75), ("r150", r150)]:
                pr.setdefault(k, []).append(v)
    pr = {k: np.array(v) for k, v in pr.items()}
    strong = torch.tensor(([False] * cultures + [True] * cultures) * len(combos), device="cuda")
    topo = Topology([1000 + s for s in range(cultures)], P)
    sim = Sim(topo, [r % cultures for r in range(R)], ["rest"] * R, P, noise_seed=7, per_run=pr,
              m_max=max(4096, R * 60))
    sim.run(20_000, game=False, plastic=False)
    k75 = torch.tensor(pr["kick75"], device="cuda", dtype=torch.float32)
    pre = torch.zeros(R, 8, 4, device="cuda"); post = torch.zeros_like(pre); pre2 = torch.zeros_like(pre)
    post2 = torch.zeros_like(pre)
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
            pre[:, k] += a; post[:, k] += b; pre2[:, k] += a * a; post2[:, k] += b * b
    pre, post = pre / trials, post / trials
    var = (pre2 / trials - pre ** 2) + (post2 / trials - post ** 2)
    z = ((post - pre) / (var.clamp(min=1e-9) / trials).sqrt()).cpu().numpy()
    d = (post - pre).cpu().numpy(); base = pre.cpu().numpy()
    rows = []
    print("motor spikes per region in 50 ms after a pulse minus before; z = change / s.e. (over trials)")
    print(f"{'set':7s} {'recruitment':22s} {'pulse':6s} {'base':>6s} {'change':>7s} {'z>3':>5s} {'|up-down| per electrode':>24s}")
    for i, (sn, rn) in enumerate(combos):
        for lab, off in (("75 mV", 0), ("150 mV", cultures)):
            sl = slice(i * 2 * cultures + off, i * 2 * cultures + off + cultures)
            ud = d[sl][:, :, [1, 3]].sum(2) - d[sl][:, :, [0, 2]].sum(2)
            rows.append(dict(set=sn, recruit=rn, pulse=lab, base=float(base[sl].mean()),
                             change=float(d[sl].mean()), frac_z3=float((z[sl] > 3).mean()),
                             updown=float(np.abs(ud).mean())))
            print(f"{sn:7s} {rn:22s} {lab:6s} {base[sl].mean():6.3f} {d[sl].mean():+7.3f} "
                  f"{(z[sl] > 3).mean():5.2f} {np.abs(ud).mean():24.3f}")
    json.dump(rows, open(os.path.join(RES, "evoked.json"), "w"), indent=1)
    return rows


def fitH(cultures=16):
    Hs = np.array([0.15, 0.18, 0.21, 0.24, 0.27, 0.30, 0.33, 0.36])
    P = base_params()
    runs, pr, out, info = play(["rest"] * 1, cultures * len(Hs), P,
                               per_run_extra={"H": np.repeat(Hs, cultures)}, minutes=10)
    res = []
    for i, Hv in enumerate(Hs):
        sl = slice(i * cultures, (i + 1) * cultures)
        v = []
        for o in out[sl]:
            r1, r2, n = rallies(o, split_ms=10 ** 9)
            v.append(r1)
        res.append(np.nanmean(v))
        print(f"  H = {Hv:.2f}: Rest hits per rally {np.nanmean(v):.3f} +/- {np.nanstd(v) / np.sqrt(len(v)):.3f}")
    Hbest = float(np.interp(REST_TARGET, res, Hs))
    print(f"  -> H = {Hbest:.3f} gives {REST_TARGET} hits per rally (data)")
    json.dump(dict(H=Hbest, Hs=Hs.tolist(), rest_hpr=res), open(os.path.join(HERE, "fitH.json"), "w"))
    save("fitH", runs, pr, out, info)
    return Hbest


def H_fitted():
    return json.load(open(os.path.join(HERE, "fitH.json")))["H"]


if __name__ == "__main__":
    what = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    t0 = time.time()
    if what == "evoked":
        evoked(min(n, 8))
    elif what == "fitH":
        fitH(min(n, 16))
    elif what == "main":
        rule = sys.argv[3] if len(sys.argv) > 3 else "gated"
        eta = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02
        P = base_params(rule=rule, eta=eta)
        runs, pr, out, info = play(["stimulus", "silent", "nofeedback"], n, P, per_run_extra={"H": H_fitted()})
        rows = table(runs, out, f"rule={rule}, eta={eta}: {n} cultures x 3 conditions, 20 min "
                                f"(wall {info['wall_s']:.0f} s, overflow {info['overflow']}, rate {info['rate_hz']:.2f} Hz)")
        save(f"main_{rule}_{eta}", runs, pr, out, info)
    elif what == "rules":
        for rule, etas in (("gated", (0.005, 0.02, 0.08)), ("stdp", (0.002, 0.008)), ("kick", (0,))):
            for eta in etas:
                kw = dict(rule=rule, eta=eta)
                if rule == "kick":
                    kw.update(sig_hit=0.0, sig_miss=0.05)
                P = base_params(**kw)
                runs, pr, out, info = play(["stimulus", "silent", "nofeedback"], n, P, per_run_extra={"H": H_fitted()})
                table(runs, out, f"rule={rule}, eta={eta} (wall {info['wall_s']:.0f} s, overflow {info['overflow']})")
                save(f"rules_{rule}_{eta}", runs, pr, out, info)
    print(f"\ntotal wall time {time.time() - t0:.0f} s")

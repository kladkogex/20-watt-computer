"""Checks of the GPU simulator against a slow, independent reference implementation.

(i)  Unconnected neurons (all weights 0): firing rate of the GPU kernel vs. a numpy implementation of the same
     discrete-time dynamics, and vs. the continuous-time Siegert formula for a white-noise-driven LIF (the 1-ms
     time step biases the discrete model slightly low; shown for orientation).
(ii) A small connected network (N = 400, K = 40): the GPU simulator vs. a dense numpy reference built from the
     same wiring and initial weights; rate, CV of inter-spike intervals and mean pairwise correlation over runs
     with independent noise.

    python3 validate.py
"""
import math, os, sys
import numpy as np, torch
from scipy import integrate, special

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from netsim import Params, Topology, Sim


def siegert(mu, sd, tau=20.0, tref=2.0, th=1.0, vr=0.0):
    s = sd * math.sqrt(2)                       # Brunel's sigma for stationary s.d. sd
    f = lambda u: math.exp(u * u) * (1 + special.erf(u))
    I, _ = integrate.quad(f, (vr - mu) / s, (th - mu) / s, limit=200)
    return 1000.0 / (tref + tau * math.sqrt(math.pi) * I)


def reference(W_dense, is_e, P, T, rng, mu_n):
    """Dense numpy version of the same discrete dynamics (no stimulation, no plasticity)."""
    N = len(is_e)
    am = math.exp(-1 / P.tau_m); amp = P.sigma * math.sqrt(1 - am * am)
    ae, ai = math.exp(-1 / P.tau_e), math.exp(-1 / P.tau_i)
    arec, aa = math.exp(-1 / P.tau_rec), math.exp(-1 / P.tau_a)
    V = rng.random(N) * 0.5; Ie = np.zeros(N); Ii = np.zeros(N); x = np.ones(N); a = np.zeros(N); ref = np.zeros(N)
    spikes = []
    for t in range(T):
        Ie *= ae; Ii *= ai; x = x * arec + (1 - arec)
        V = V * am + (1 - am) * (mu_n + Ie - Ii - a) + amp * rng.standard_normal(N)
        refr = ref > 0
        V[refr] = 0
        s = (V >= 1) & ~refr
        V[s] = 0; ref = np.where(s, P.t_ref, np.maximum(ref - 1, 0)); a = a * aa + P.b_a * s
        j = np.flatnonzero(s)
        if j.size:
            e = j[is_e[j]]; i = j[~is_e[j]]
            if e.size:
                Ie += W_dense[:, e] @ (P.U * x[e]); x[e] -= P.U * x[e]
            if i.size:
                Ii += W_dense[:, i].sum(1)
            spikes += [(t, k) for k in j]
    return spikes


def summary(spikes, N, T):
    tr = [[] for _ in range(N)]
    for t, k in spikes:
        tr[k].append(t)
    rates = np.array([len(x) for x in tr]) / (T / 1000)
    cvs = [np.std(np.diff(x)) / np.mean(np.diff(x)) for x in tr if len(x) > 5]
    C = np.array([np.histogram(x, np.arange(0, T + 1, 100))[0] for x in tr], float)
    C = C[C.std(1) > 0]
    R = np.corrcoef(C); n = R.shape[0]
    return rates.mean(), float(np.median(cvs)) if cvs else np.nan, (R.sum() - n) / (n * (n - 1))


if __name__ == "__main__":
    print("(i) unconnected neurons: rate (Hz)   GPU | numpy, same discrete dynamics | Siegert (continuous time)")
    rng = np.random.default_rng(0)
    for mu, sd in [(0.6, 0.3), (0.8, 0.2), (0.9, 0.35), (1.1, 0.2)]:
        P = Params(N=2000, K=10, J_ee=0, J_ie=0, J_ei=0, J_ii=0, mu=mu, sigma=sd, U=0.0, b_a=0.0)
        topo = Topology([0], P)
        sim = Sim(topo, [0] * 8, ["rest"] * 8, P, record_units=0)
        n = torch.zeros((), device="cuda")
        sim.run(1000, game=False, plastic=False)
        steps = 20_000
        for _ in range(steps // 10):
            sim.graph.replay(); n += sim.spk.sum()          # the spikes of the last ms of each block
        gpu = n.item() * 10 / (8 * 2000) / (steps / 1000)
        refs = reference(np.zeros((200, 200)), np.ones(200, bool), P, 20_000, rng, np.full(200, mu))
        ref = len(refs) / 200 / 20.0
        print(f"   mu={mu:.2f} sd={sd:.2f}:  {gpu:7.2f} | {ref:7.2f} | {siegert(mu, sd):7.2f}")

    print("\n(ii) connected network N=400, K=40, with depression and adaptation; 8 runs each")
    P = Params(N=400, K=40, mu=0.55, sigma=0.3, J_ee=0.15, J_ie=0.15, J_ei=0.5, J_ii=0.5, U=0.3, b_a=0.02)
    topo = Topology([3], P)
    R = 8
    sim = Sim(topo, [0] * R, ["rest"] * R, P, record_units=400, noise_seed=5)
    T = 60_000
    sim.run(T, game=False, plastic=False)
    trains = sim.recorded_trains()
    units = sim.rec_units.cpu().numpy()
    g = []
    for r in range(R):
        sp = [(int(round(t * 1000)), int(units[r][u])) for u in range(400) for t in trains[r][u]]
        g.append(summary(sp, 400, T))
    # dense reference from the same wiring and run-0 weights
    W = sim.W[0].cpu().numpy(); post = topo.out_post[0].cpu().numpy()
    Wd = np.zeros((401, 400))
    for j in range(400):
        Wd[post[j], j] = W[j]
    Wd = Wd[:400]
    is_e = np.arange(400) < topo.NE
    mu_n = sim.MU[0].cpu().numpy()
    ref = [summary(reference(Wd, is_e, P, T, np.random.default_rng(100 + r), mu_n), 400, T) for r in range(4)]
    g, ref = np.array(g), np.array(ref)
    for name, k in [("mean rate (Hz)", 0), ("median CV of ISI", 1), ("mean pairwise corr (100 ms)", 2)]:
        print(f"   {name:28s} GPU {g[:, k].mean():.4f} +/- {g[:, k].std():.4f}   numpy {ref[:, k].mean():.4f} +/- {ref[:, k].std():.4f}")

"""Memory and speed of the simulator at large N on the chip geometry (Stimulus protocol, calibrated medium set).
    python3 scale_bench.py N R K     -> one line of JSON-like output"""
import json, os, sys, time
import numpy as np, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netsim import Params, Topology, Sim

N, R, K = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 100
cal = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "calib_sets.json")))["medium"]
cal.pop("search_loss")
P = Params(N=N, K=K)
S = min(R, 8)
torch.cuda.reset_peak_memory_stats()
t0 = time.time()
topo = Topology([1000 + s for s in range(S)], P)
torch.cuda.synchronize(); t_topo = time.time() - t0
pr = {k: np.full(R, v) for k, v in cal.items()}; pr["H"] = np.full(R, 0.214)
sim = Sim(topo, [r % S for r in range(R)], ["stimulus"] * R, P, per_run=pr, m_max=max(2048, R * N // 250))
torch.cuda.synchronize(); t_sim = time.time() - t0 - t_topo
sim.run(2000, game=False, plastic=False)
torch.cuda.synchronize(); t = time.time()
sim.run(5000, game=True)
torch.cuda.synchronize(); us = (time.time() - t) / 5000 * 1e6
print(json.dumps(dict(N=N, R=R, K=K, D=topo.D, topo_s=round(t_topo, 1), sim_init_s=round(t_sim, 1),
                      us_per_ms_step=round(us), min_per_20min_session=round(us * 1.26e6 / 6e7, 1),
                      peak_GB=round(torch.cuda.max_memory_allocated() / 1e9, 1),
                      rate_hz=round(float(sim.spk.float().mean()) * 1000, 3), overflow=int(sim.overflow),
                      neurons_per_mm2=round(N / 8.085))))

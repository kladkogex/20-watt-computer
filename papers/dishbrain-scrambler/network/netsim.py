"""GPU simulator of a DishBrain-like culture playing Pong under the published protocols.

All runs (cultures x conditions x parameter sets) are stepped together: every state tensor has a leading run
axis R, so the Python and kernel-launch cost of a 1-ms step is paid once for all runs, and a 10-ms block of
steps (neurons, stimulation, blanking, decoder, ball) is replayed as one CUDA graph. Synapses are event-driven
(only neurons that spiked propagate, through contiguous out-lists); the neuron update is one fused kernel.
Needs torch with CUDA (torch.compile for the fused kernel).

Network (sources and assumptions: paper, Appendix B):
  * sheet 3.85 x 2.10 mm = the MaxOne electrode grid (220 x 120 electrodes, pitch 17.5 um);
  * N leaky integrate-and-fire neurons at uniform random positions; the first fE*N excitatory (E), rest inhibitory;
  * K inputs per neuron, drawn without replacement with probability proportional to exp(-d / lam);
  * exponential current synapses; short-term depression of E synapses; spike-frequency adaptation;
    Ornstein-Uhlenbeck membrane noise, integrated exactly (dt = 1 ms);
  * stimulation: a 75 mV pulse depolarizes neurons within r75 of the electrode by kick75 (threshold = 1);
    a 150 mV pulse forces a spike in neurons within r150 ("sufficient to force action potentials").

Protocol (Kagan et al. 2022, STAR Methods and Fig. 4D; timing fitted to their gameplay data):
  * 8 stimulation electrodes in the sensory band; four motor regions (two "up", two "down") at rows 78-110;
  * place code: electrode = ball height relative to the paddle; rate code 4 Hz (far wall) to 40 Hz (paddle wall);
  * decoder every 10 ms: region counts scaled toward a 20 Hz running target, up vs down moves the paddle;
    readout blanked for `blank` ms after every stimulation command ("command count blinding");
  * feedback programs after a hit or a miss (see PROTOCOLS); No feedback: the ball just bounces on.
"""
import math
from dataclasses import dataclass, asdict

import numpy as np
import torch

PITCH = 0.0175
WX, WY = 220 * PITCH, 120 * PITCH
STIM_ELECTRODES = [(22, 20), (46, 35), (70, 20), (94, 35), (117, 20), (142, 35), (165, 20), (190, 35)]
MOTOR_REGIONS = [("down", 18, 48), ("up", 49, 79), ("down", 140, 170), ("up", 171, 201)]
MOTOR_ROWS = (78, 110)
UP = torch.tensor([0.0, 1.0, 0.0, 1.0])

# feedback stimulation kinds
NONE, TETANUS, RAND150, FIXED150, RAND75, QUENCH = 0, 1, 2, 3, 4, 5
# protocol: (hit kind, hit stim ms, hit pause ms), (miss kind, miss stim ms, miss pause ms), restart after miss,
#           sensory stimulation on
PROTOCOLS = {
    "rest":        ((NONE, 0, 0),          (NONE, 0, 0),           True,  False),
    "stimulus":    ((TETANUS, 100, 0),     (RAND150, 4000, 4000),  True,  True),
    "silent":      ((NONE, 0, 0),          (NONE, 4000, 4000),     True,  True),
    "nofeedback":  ((NONE, 0, 0),          (NONE, 0, 0),           False, True),
    "predictable": ((TETANUS, 100, 0),     (FIXED150, 4000, 4000), True,  True),   # protocol B
    "quenched":    ((TETANUS, 100, 0),     (QUENCH, 8000, 0),      True,  True),   # protocol C
    "reversed":    ((FIXED150, 1000, 0),   (RAND75, 1000, 0),      True,  True),   # protocol D
    "infofree":    ((RAND150, 4000, 4000), (RAND150, 4000, 4000),  True,  True),   # protocol E
}


@dataclass
class Params:
    # network
    N: int = 3000
    fE: float = 0.8
    K: int = 100
    lam: float = 1.0
    tau_m: float = 20.0
    tau_e: float = 5.0
    tau_i: float = 10.0
    t_ref: float = 2.0
    mu: float = 0.7
    mu_sd: float = 0.0              # s.d. of a fixed per-neuron drive offset (rate heterogeneity)
    sigma: float = 0.35
    J_ee: float = 0.10
    J_ie: float = 0.10
    J_ei: float = 0.40
    J_ii: float = 0.40
    U: float = 0.2
    tau_rec: float = 500.0
    b_a: float = 0.0
    tau_a: float = 1000.0
    # stimulation
    r75: float = 0.05
    kick75: float = 1.2
    r150: float = 0.10
    quench_hz: float = 50.0
    quench_kick: float = 0.6
    # game (court 1 x 1; ball crossing time from the gameplay data)
    crossing_s: float = 2.9
    H: float = 0.2                  # paddle half-length (fitted to the Rest baseline)
    paddle_speed: float = 1.0       # court heights per second
    blank: int = 5                  # ms of readout blanking after a stimulation command
    ema_s: float = 5.0              # running-rate window of the 20 Hz gain
    # plasticity: "none", "gated" (activity-gated zero-mean random), "stdp" (additive pair STDP), "kick"
    rule: str = "none"
    eta: float = 0.0                # gated: step size; stdp: A+ (A- = 1.05 A+); units of the E->E weight range
    tau_tr: float = 20.0            # plasticity traces, ms
    sig_hit: float = 0.0            # kick rule: s.d. after a hit / a miss (units of the E->E weight range)
    sig_miss: float = 0.0

    def as_dict(self):
        return asdict(self)


def dev():
    return torch.device("cuda")


# ----------------------------------------------------------------------------------------------- topology
class Topology:
    """Positions and wiring of S cultures (seeds), shared by every run with the same seed (paired design)."""

    def __init__(self, seeds, P: Params):
        d_ = dev()
        self.P, self.S, N, K = P, len(seeds), P.N, P.K
        self.NE = int(round(P.fE * N))
        pre = torch.empty(self.S, N, K, dtype=torch.int64, device=d_)
        pos = torch.empty(self.S, N, 2, device=d_)
        for s, seed in enumerate(seeds):
            g = torch.Generator(device=d_).manual_seed(int(seed))
            p = torch.rand(N, 2, generator=g, device=d_) * torch.tensor([WX, WY], device=d_)
            w = torch.exp(-torch.cdist(p, p) / P.lam)
            w.fill_diagonal_(0)
            pre[s] = torch.multinomial(w, K, replacement=False, generator=g)
            pos[s] = p
        self.pos, self.pre = pos, pre
        outdeg = torch.zeros(self.S, N, dtype=torch.int64, device=d_)
        outdeg.scatter_add_(1, pre.view(self.S, -1), torch.ones_like(pre.view(self.S, -1)))
        D = int(outdeg.max())
        self.D = D
        out_post = torch.full((self.S, N, D), N, dtype=torch.int64, device=d_)
        in_d = torch.zeros(self.S, N, K, dtype=torch.int64, device=d_)
        for s in range(self.S):
            j = pre[s].reshape(-1)
            order = torch.argsort(j, stable=True)
            js = j[order]
            start = torch.zeros(N + 1, dtype=torch.int64, device=d_)
            start[1:] = torch.cumsum(outdeg[s], 0)
            rank = torch.arange(js.numel(), device=d_) - start[js]
            post = torch.arange(N, device=d_).repeat_interleave(K)[order]
            slot = torch.arange(K, device=d_).repeat(N)[order]
            out_post[s, js, rank] = post
            in_d[s, post, slot] = rank
        self.out_post, self.in_d = out_post, in_d
        el = torch.tensor([[c * PITCH, r * PITCH] for c, r in STIM_ELECTRODES], device=d_)
        self.el_dist = torch.cdist(pos, el.unsqueeze(0).expand(self.S, -1, -1))   # (S, N, 8), mm
        region = torch.full((self.S, N), -1, dtype=torch.int64, device=d_)
        r0, r1 = MOTOR_ROWS[0] * PITCH, (MOTOR_ROWS[1] + 1) * PITCH
        for k, (_, c0, c1) in enumerate(MOTOR_REGIONS):
            inside = (pos[..., 0] >= c0 * PITCH) & (pos[..., 0] < (c1 + 1) * PITCH) & \
                     (pos[..., 1] >= r0) & (pos[..., 1] < r1)
            region[inside] = k
        self.region = region
        self.onehot = torch.nn.functional.one_hot(region.clamp(min=0), 4).float() * (region >= 0).unsqueeze(-1)


# ----------------------------------------------------------------------------------------------- fused update
import triton
import triton.language as tl


@triton.jit
def _neuron_kernel(V, I, a, ref, el75, el150, m75, m150, x, tr, yp, spk, n, N, seed, offset_ptr,
                   MU, AMP, BA, am, aa, ae, ai, arec, atr, tref, kick75,
                   TRACES: tl.constexpr, ADAPT: tl.constexpr, STD: tl.constexpr, BLOCK: tl.constexpr):
    """One 1-ms step of every neuron, in place. I holds [run, E/I, N + 1] synaptic currents.
    Stimulation: el75/el150 give each neuron's electrode (8 = none); m75/m150 [run, 9] this ms's pulses.
    Arrays that rarely change (refractory clock, traces, depression) are written only where they change."""
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    m = offs < n
    row = offs // N
    col = offs - row * N
    ie_off = row * (2 * (N + 1)) + col
    ii_off = ie_off + (N + 1)
    Ie = tl.load(I + ie_off, mask=m) * ae
    Ii = tl.load(I + ii_off, mask=m) * ai
    v = tl.load(V + offs, mask=m)
    e75 = tl.load(el75 + offs, mask=m, other=8).to(tl.int32)
    e150 = tl.load(el150 + offs, mask=m, other=8).to(tl.int32)
    k = kick75 * tl.load(m75 + row * 9 + e75, mask=m, other=0.0)
    fo = tl.load(m150 + row * 9 + e150, mask=m, other=0.0) > 0
    rf = tl.load(ref + offs, mask=m)
    noise = tl.randn(seed, offs + tl.load(offset_ptr))     # offset lives on the GPU (CUDA-graph safe)
    amp = tl.load(AMP + row, mask=m, other=0.0)
    drive = tl.load(MU + offs, mask=m, other=0.0) + Ie - Ii
    if ADAPT:
        av = tl.load(a + offs, mask=m)
        drive = drive - av
    v = v * am + (1 - am) * drive + amp * noise + k
    refr = rf > 0
    v = tl.where(refr, 0.0, v)
    s = ((v >= 1.0) & (~refr)) | fo
    v = tl.where(s, 0.0, v)
    tl.store(V + offs, v, mask=m)
    tl.store(I + ie_off, Ie, mask=m)
    tl.store(I + ii_off, Ii, mask=m)
    tl.store(spk + offs, s.to(tl.int8), mask=m)
    tl.store(ref + offs, tl.where(s, tref, tl.maximum(rf - 1, 0.0)), mask=m & (refr | s))
    if ADAPT:
        tl.store(a + offs, av * aa + tl.load(BA + row, mask=m, other=0.0) * s.to(tl.float32), mask=m)
    if STD:
        xv = tl.load(x + offs, mask=m)
        tl.store(x + offs, xv * arec + (1 - arec), mask=m & (xv < 1.0))
    if TRACES:
        t = tl.load(tr + offs, mask=m)
        y = tl.load(yp + offs, mask=m)
        tl.store(tr + offs, tl.where(s, 1.0, t * atr), mask=m & ((t > 0) | s))
        tl.store(yp + offs, tl.where(s, 1.0, y * atr), mask=m & ((y > 0) | s))


# ----------------------------------------------------------------------------------------------- per-ms control
@torch.compile(fullgraph=True, dynamic=False)
def _stim_logic(acc, blank_t, bx, by, pad, phase, ptime, fb_kind, sensory_on, game_on, u, rnd8,
                blank, quench_p: float, quench_s: float):
    """Pulses of this ms: sensory place + rate code during play, feedback programs after outcomes.
    Updates acc and blank_t in place; returns (m75, m150), (R, 9) with a trailing zero column."""
    R = acc.shape[0]
    play = (phase == 0) & (game_on > 0)
    sens = play & sensory_on
    acc_n = torch.where(sens, acc + (4 + 36 * bx.clamp(0, 1)) / 1000.0, acc)
    fire = sens & (acc_n >= 1.0)
    acc.copy_(torch.where(fire, acc_n - 1.0, acc_n))
    el = torch.arange(9, device=acc.device).view(1, 9)
    k = torch.clamp(torch.floor(8 * (by - pad + 0.5)), 0, 7).long().view(R, 1)
    m75 = ((el == k) & fire.view(R, 1)).float()
    fb = phase == 1
    rnd_el = (el == rnd8.view(R, 1)).float()
    bern5 = u[:, 0] < 0.005
    tet = fb & (fb_kind == 1) & (torch.remainder(ptime, 10) == 0)
    m75 = m75 + (tet.view(R, 1) & (el < 8)).float()
    m150 = rnd_el * (fb & (fb_kind == 2) & bern5).float().view(R, 1)
    f150 = fb & (fb_kind == 3) & (torch.remainder(ptime, 200) == 0)
    seq = torch.remainder(torch.div(ptime, 200, rounding_mode="floor"), 8).long().view(R, 1)
    m150 = m150 + ((el == seq) & f150.view(R, 1)).float()
    m75 = m75 + rnd_el * (fb & (fb_kind == 4) & bern5).float().view(R, 1)
    q = fb & (fb_kind == 5) & (u[:, 1] < quench_p)
    m75 = m75 + rnd_el * (q.float() * quench_s).view(R, 1)
    m75 = m75.clamp(max=1.0) * (el < 8)
    m150 = m150.clamp(max=1.0) * (el < 8)
    any_ = (m75.sum(1) + m150.sum(1)) > 0
    blank_t.copy_(torch.where(any_, blank, blank_t))
    return m75, m150


@torch.compile(fullgraph=True, dynamic=False)
def _after_ms(counts, blank_t, phase, ptime, fb_stim, fb_pause, fb_restart, ev, nev, dsq, clock,
              bx, by, bvx, bvy, motor_spk, mot_reg, u, v: float):
    """Readout (unless blanked), feedback phase clock, serve after a finished miss program; in place."""
    R = counts.shape[0]
    live = (blank_t <= 0).float().view(R, 1)
    counts.add_((motor_spk.float().unsqueeze(-1) * mot_reg).sum(1) * live)
    blank_t.copy_((blank_t - 1).clamp(min=0))
    fb = phase > 0
    pt = ptime + fb.float()
    ph = torch.where((phase == 1) & (pt >= fb_stim), 2, phase)
    done = (ph == 2) & (pt >= fb_stim + fb_pause)
    ph = torch.where(done, 0, ph)
    ptime.copy_(pt); phase.copy_(ph)
    ar = torch.arange(R, device=counts.device)
    last = (nev - 1).clamp(min=0)
    cur = ev[ar, last, 3]
    ev[ar, last, 3] = torch.where(done, dsq, cur)
    serve = done & fb_restart
    ang = (u[:, 2] - 0.5) * (math.pi / 2)
    sgn = torch.where(u[:, 3] < 0.5, -1.0, 1.0)
    bx.copy_(torch.where(serve, torch.full_like(bx, 0.5), bx))
    by.copy_(torch.where(serve, u[:, 4], by))
    bvx.copy_(torch.where(serve, v * torch.cos(ang) * sgn, bvx))
    bvy.copy_(torch.where(serve, v * torch.sin(ang), bvy))
    clock.add_(1.0)


# ----------------------------------------------------------------------------------------------- the runs
class Sim:
    def __init__(self, topo: Topology, run_seed, protocol, P: Params, noise_seed=0, m_max=None,
                 record_units=0, max_events=2048, per_run=None):
        self.t, self.P = topo, P
        d_ = dev()
        torch.cuda.manual_seed(int(noise_seed))
        R, N, K, D, NE = len(run_seed), P.N, P.K, topo.D, topo.NE
        self.R, self.N, self.K, self.D, self.NE = R, N, K, D, NE
        self.seed_of = torch.as_tensor(run_seed, dtype=torch.int64, device=d_)
        self.m_max = m_max or max(1024, int(R * N * 0.002))
        # parameters that may differ between runs (calibration searches); defaults from P
        pr = dict(per_run or {})
        def col(name):
            v = pr.get(name, getattr(P, name))
            return torch.as_tensor(v, dtype=torch.float32, device=d_).expand(R).clone()
        self.pr = {k: col(k) for k in ("mu", "mu_sd", "sigma", "J_ee", "J_ie", "J_ei", "J_ii", "U", "b_a",
                                       "H", "r75", "r150", "kick75", "blank")}
        # weights in out-list layout, flat, with one trailing dummy row (row R*N) that absorbs padded updates
        out_post = topo.out_post[self.seed_of]
        pre_e = (torch.arange(N, device=d_) < NE).view(1, N, 1)
        post_e = out_post < NE
        pad = out_post >= N
        u = torch.rand(out_post.shape, device=d_)
        J = {k: self.pr[k].view(R, 1, 1) for k in ("J_ee", "J_ie", "J_ei", "J_ii")}
        W = torch.where(pre_e & post_e, 2 * J["J_ee"] * u,
            torch.where(pre_e & ~post_e, J["J_ie"].expand_as(u),
            torch.where(~pre_e & post_e, J["J_ei"].expand_as(u), J["J_ii"].expand_as(u))))
        W.masked_fill_(pad, 0.0)
        self.Wflat = torch.cat([W.reshape(-1), torch.zeros(D, device=d_)])      # + one dummy row
        self.W = self.Wflat[:R * N * D].view(R, N, D)
        self.Wrows = self.Wflat.view(R * N + 1, D)
        self.ee = (pre_e & post_e & ~pad)
        del out_post, u, W, pad, post_e
        self.wmax = 2 * self.pr["J_ee"]                 # per run
        # neuron state
        self.V = torch.rand(R, N, device=d_) * 0.5
        self.I = torch.zeros(R, 2, N + 1, device=d_)
        self.x = torch.ones(R, N, device=d_)
        self.a = torch.zeros(R, N, device=d_)
        self.ref = torch.zeros(R, N, device=d_)
        self.tr = torch.zeros(R, N, device=d_)
        self.ypost = torch.zeros(R, N, device=d_)
        self.spk = torch.zeros(R, N, dtype=torch.int8, device=d_)
        self.seed = int(noise_seed) * 1000003 + 17
        self.rng_offset = torch.zeros((), dtype=torch.int64, device=d_)
        self.overflow = torch.zeros((), dtype=torch.int64, device=d_)
        self.dsq = torch.zeros(R, device=d_)            # accumulated squared weight change (plasticity), per run
        self.plastic = torch.zeros((), device=d_)       # 0 during burn-in, 1 when plasticity is on
        self.am = math.exp(-1 / P.tau_m)
        self.AMP = (self.pr["sigma"] * math.sqrt(1 - self.am ** 2)).contiguous()
        self.MU = (self.pr["mu"].view(R, 1) + self.pr["mu_sd"].view(R, 1) * torch.randn(R, N, device=d_)).contiguous()
        self.BA = self.pr["b_a"].contiguous()
        self.use_adapt = bool((self.BA > 0).any())
        self.use_std = bool((self.pr["U"] > 0).any())
        self.aa, self.ae, self.ai = math.exp(-1 / P.tau_a), math.exp(-1 / P.tau_e), math.exp(-1 / P.tau_i)
        self.arec, self.atr = math.exp(-1 / P.tau_rec), math.exp(-1 / P.tau_tr)
        # stimulation catchments do not overlap (electrodes >= 0.4 mm apart): one electrode index per neuron
        dist = topo.el_dist[self.seed_of]                                  # (R, N, 8), mm
        dmin, arg = dist.min(2)
        assert float(max(self.pr["r75"].max(), self.pr["r150"].max())) < 0.24, "catchments would overlap"
        self.el75 = torch.where(dmin < self.pr["r75"].view(R, 1), arg, 8).to(torch.int8).contiguous()
        self.el150 = torch.where(dmin < self.pr["r150"].view(R, 1), arg, 8).to(torch.int8).contiguous()
        self.m75 = torch.zeros(R, 9, device=d_); self.m150 = torch.zeros(R, 9, device=d_)
        del dist, dmin, arg
        reg = topo.region[self.seed_of]                                   # (R, N), -1 outside motor regions
        nm = int((reg >= 0).sum(1).max())
        order = torch.argsort((reg < 0).to(torch.int8), dim=1, stable=True)[:, :nm]   # motor neurons first
        self.mot_idx = order
        self.mot_reg = torch.nn.functional.one_hot(reg.gather(1, order).clamp(min=0), 4).float() * \
                       (reg.gather(1, order) >= 0).unsqueeze(-1).float()   # (R, nm, 4)
        # protocol tables per run
        self.protocol_names = list(protocol)
        tab = [PROTOCOLS[p] for p in protocol]
        f = lambda v: torch.tensor(v, device=d_)
        self.hit_kind = f([t[0][0] for t in tab]); self.hit_stim = f([t[0][1] for t in tab]); self.hit_pause = f([t[0][2] for t in tab])
        self.miss_kind = f([t[1][0] for t in tab]); self.miss_stim = f([t[1][1] for t in tab]); self.miss_pause = f([t[1][2] for t in tab])
        self.restart = f([t[2] for t in tab]); self.sensory_on = f([t[3] for t in tab])
        # game state
        v = 1.0 / (P.crossing_s * 1000.0)                # court per ms
        self.v = v
        self.bx = torch.full((R,), 0.5, device=d_); self.by = torch.rand(R, device=d_)
        ang = (torch.rand(R, device=d_) - 0.5) * (math.pi / 2)
        sgn = torch.where(torch.rand(R, device=d_) < 0.5, -1.0, 1.0)
        self.bvx = v * torch.cos(ang) * sgn; self.bvy = v * torch.sin(ang)
        self.pad = torch.full((R,), 0.5, device=d_)
        self.acc = torch.zeros(R, device=d_)             # sensory rate-code phase
        self.phase = torch.zeros(R, dtype=torch.int64, device=d_)   # 0 play, 1 feedback stimulation, 2 pause
        self.ptime = torch.zeros(R, device=d_)           # ms spent in the current feedback phase
        self.fb_kind = torch.zeros(R, dtype=torch.int64, device=d_)
        self.fb_stim = torch.zeros(R, device=d_); self.fb_pause = torch.zeros(R, device=d_)
        self.fb_restart = torch.zeros(R, dtype=torch.bool, device=d_)
        self.blank_t = torch.zeros(R, device=d_)
        self.counts = torch.zeros(R, 4, device=d_)
        self.ema = torch.full((R, 4), 20.0, device=d_)   # running region rate, Hz-equivalent (see decoder)
        self.clock = torch.zeros((), device=d_)          # ms since the start of the session
        self.game_on = torch.zeros((), device=d_)
        # outcome log: time (ms), hit, dsq at the outcome, dsq at the end of its feedback
        self.max_ev = max_events
        self.ev = torch.full((R, max_events, 4), float("nan"), device=d_)
        self.nev = torch.zeros(R, dtype=torch.int64, device=d_)
        self.ar = torch.arange(R, device=d_)
        self.upmask = UP.to(d_)
        # recording (calibration)
        self.rec_units = None
        if record_units:
            g = torch.Generator(device=d_).manual_seed(12345)
            self.rec_units = torch.stack([torch.randperm(N, generator=g, device=d_)[:record_units] for _ in range(R)])
            self.rec_chunk = 1000
            self.rec_buf = torch.zeros(self.rec_chunk, R, record_units, dtype=torch.bool, device=d_)
            self.rec_events = []
            self.rec_base = 0
            self.rec_ptr = torch.zeros(1, dtype=torch.int64, device=d_)
        self.nstep = 0
        self.graph = None

    # ------------------------------------------------------------------ one ms of neurons
    def _neurons(self):
        P, R, N = self.P, self.R, self.N
        n = R * N
        BLOCK = 1024
        _neuron_kernel[(triton.cdiv(n, BLOCK),)](
            self.V, self.I, self.a, self.ref, self.el75, self.el150, self.m75, self.m150, self.x, self.tr,
            self.ypost, self.spk, n, N, self.seed, self.rng_offset, self.MU, self.AMP, self.BA, self.am, self.aa,
            self.ae, self.ai, self.arec, self.atr, P.t_ref, 1.0, TRACES=P.rule in ("gated", "stdp"), ADAPT=self.use_adapt,
            STD=self.use_std, BLOCK=BLOCK)
        self.rng_offset.add_(n)
        spk = self.spk.view(torch.bool)
        flat = torch.nonzero_static(spk.view(-1), size=self.m_max, fill_value=R * N).squeeze(1)
        self.overflow.copy_(torch.maximum(self.overflow, spk.sum() - self.m_max))
        valid = flat < R * N
        f = flat.clamp(max=R * N - 1)
        rr, jj = torch.div(f, N, rounding_mode="floor"), torch.remainder(f, N)
        posts = self.t.out_post[self.seed_of[rr], jj]                   # (M, D)
        w = self.W[rr, jj]
        e = jj < self.NE
        xj = self.x[rr, jj]
        Ur = self.pr["U"][rr]
        eff = torch.where(e, Ur * xj, torch.ones_like(xj)) * valid
        idx = ((rr.unsqueeze(1) * 2 + (~e).long().unsqueeze(1)) * (N + 1) + posts).reshape(-1)
        self.I.view(-1).index_add_(0, idx, (w * eff.unsqueeze(1)).reshape(-1))
        self.x.view(-1).index_add_(0, f, -(Ur * xj) * (e & valid))
        if P.rule in ("gated", "stdp"):
            self._plasticity(rr, jj, e & valid, posts, w)
        if self.rec_units is not None:                                  # row pointer on the GPU (graph safe)
            self.rec_buf.index_copy_(0, self.rec_ptr, spk.gather(1, self.rec_units).unsqueeze(0))
            self.rec_ptr.add_(1).remainder_(self.rec_chunk)
        return spk

    def _plasticity(self, rr, jj, ev, posts, w_row):
        """Updates for spiking E neurons: as postsynaptic cells (both rules) and as presynaptic cells (STDP LTD)."""
        P, N, D = self.P, self.N, self.D
        wr, on = self.wmax[rr].unsqueeze(1), self.plastic
        s = self.seed_of[rr]
        pres = self.t.pre[s, jj]                                        # (M, K) inputs of each spiking neuron
        ds = self.t.in_d[s, jj]
        is_ee = (pres < self.NE) & ev.unsqueeze(1)
        trace = self.tr[rr.unsqueeze(1), pres]                          # pre traces before this step's reset
        widx = (rr.unsqueeze(1) * N + pres) * D + ds
        widx = torch.where(is_ee, widx, torch.full_like(widx, self.R * N * D))   # dummy element
        if P.rule == "gated":
            xi = torch.where(torch.rand(widx.shape, device=widx.device) < 0.5, -1.0, 1.0)
            dw = on * P.eta * wr * trace * xi * is_ee
        else:
            dw = on * P.eta * wr * trace * is_ee                          # LTP on post spikes
        old = self.Wflat[widx]
        new = old + dw
        if P.rule == "gated":                                           # reflect into [0, wmax]
            new = new.abs(); new = torch.where(new > wr, 2 * wr - new, new)
        else:
            new = torch.minimum(new.clamp(min=0), wr)
        new = torch.where(is_ee, new, old)
        self.Wflat[widx] = new
        self.dsq.index_add_(0, rr, ((new - old) ** 2).sum(1))
        if P.rule == "stdp":                                            # LTD on pre spikes: rows of the spikers
            post_e = (posts < self.NE) & ev.unsqueeze(1)
            y = self.ypost[rr.unsqueeze(1), posts.clamp(max=N - 1)]
            new2 = torch.minimum((w_row - on * 1.05 * P.eta * wr * y * post_e).clamp(min=0), wr)
            new2 = torch.where(post_e, new2, w_row)
            ridx = torch.where(ev, rr * N + jj, torch.full_like(rr, self.R * N))
            self.Wrows[ridx] = new2
            self.dsq.index_add_(0, rr, ((new2 - w_row) ** 2).sum(1))

    def _kick(self, hit, miss):
        """Imposed outcome-contingent kicks of all E->E weights (the abstract scrambler)."""
        P = self.P
        wm = self.wmax.view(-1, 1, 1)
        sig = (P.sig_hit * hit.float() + P.sig_miss * miss.float()) * self.wmax * self.plastic
        dw = torch.randn_like(self.W) * sig.view(-1, 1, 1) * self.ee
        new = (self.W + dw).abs(); new = torch.where(new > wm, 2 * wm - new, new)
        new = torch.where(self.ee, new, self.W)
        self.dsq += ((new - self.W) ** 2).sum((1, 2))
        self.W.copy_(new)

    # ------------------------------------------------------------------ the game, every 10 ms
    def _game(self):
        P = self.P
        on = self.game_on.bool()
        hz = self.counts * 100.0
        self.ema.copy_(self.ema + (10.0 / (P.ema_s * 1000.0)) * (hz - self.ema))
        g = hz * 20.0 / self.ema.clamp(min=1.0)
        up = (g * self.upmask).sum(1); dn = (g * (1 - self.upmask)).sum(1)
        H = self.pr["H"]
        self.pad.copy_(torch.where(on, torch.minimum(torch.maximum(self.pad + P.paddle_speed * 0.01 * torch.sign(up - dn), H), 1 - H), self.pad))
        self.counts.zero_()
        play = on & (self.phase == 0)
        bx = self.bx + self.bvx * 10 * play; by = self.by + self.bvy * 10 * play
        vy = torch.where((by < 0) | (by > 1), -self.bvy, self.bvy)
        by = torch.where(by < 0, -by, torch.where(by > 1, 2 - by, by))
        vx = torch.where(bx < 0, -self.bvx, self.bvx)
        bx = torch.where(bx < 0, -bx, bx)
        arrive = play & (bx >= 1.0) & (vx > 0)
        hit = arrive & ((by - self.pad).abs() < H)
        miss = arrive & ~hit
        slot = self.nev.clamp(max=self.max_ev - 1)
        row = torch.stack([self.clock.expand(self.R), hit.float(), self.dsq, torch.full_like(self.dsq, float("nan"))], 1)
        self.ev[self.ar, slot] = torch.where(arrive.unsqueeze(1), row, self.ev[self.ar, slot])
        self.nev.add_(arrive.long())
        if P.rule == "kick":
            self._kick(hit, miss)
        bounce = hit | (miss & ~self.restart)
        vx = torch.where(bounce, -vx.abs(), vx); bx = torch.where(bounce, 2 - bx, bx)
        kind = torch.where(hit, self.hit_kind, self.miss_kind)
        st = torch.where(hit, self.hit_stim, self.miss_stim).float()
        pa = torch.where(hit, self.hit_pause, self.miss_pause).float()
        start_fb = arrive & ((st + pa) > 0) & (hit | self.restart)
        now_serve = miss & self.restart & ((st + pa) == 0)
        self.fb_kind.copy_(torch.where(start_fb, kind, self.fb_kind))
        self.fb_stim.copy_(torch.where(start_fb, st, self.fb_stim))
        self.fb_pause.copy_(torch.where(start_fb, pa, self.fb_pause))
        self.fb_restart.copy_(torch.where(start_fb, miss, self.fb_restart))
        self.phase.copy_(torch.where(start_fb, torch.where(st > 0, 1, 2), self.phase))
        self.ptime.copy_(torch.where(start_fb, torch.zeros_like(self.ptime), self.ptime))
        self.bx.copy_(bx); self.by.copy_(by); self.bvx.copy_(vx); self.bvy.copy_(vy)
        self._serve(now_serve)

    def _serve(self, mask):
        R, d_ = self.R, self.bx.device
        ang = (torch.rand(R, device=d_) - 0.5) * (math.pi / 2)
        sgn = torch.where(torch.rand(R, device=d_) < 0.5, -1.0, 1.0)
        self.bx.copy_(torch.where(mask, torch.full_like(self.bx, 0.5), self.bx))
        self.by.copy_(torch.where(mask, torch.rand(R, device=d_), self.by))
        self.bvx.copy_(torch.where(mask, self.v * torch.cos(ang) * sgn, self.bvx))
        self.bvy.copy_(torch.where(mask, self.v * torch.sin(ang), self.bvy))

    def _phase_clock(self):
        """Advance feedback phases by one ms; at the end of a program log dsq, and serve if it followed a miss."""
        fb = self.phase > 0
        self.ptime.add_(fb.float())
        self.phase.copy_(torch.where((self.phase == 1) & (self.ptime >= self.fb_stim), 2, self.phase))
        done = (self.phase == 2) & (self.ptime >= self.fb_stim + self.fb_pause)
        self.phase.copy_(torch.where(done, 0, self.phase))
        last = (self.nev - 1).clamp(min=0)
        self.ev[self.ar, last, 3] = torch.where(done, self.dsq, self.ev[self.ar, last, 3])
        self._serve(done & self.fb_restart)

    # ------------------------------------------------------------------ 10-ms blocks
    def _block(self):
        P, R = self.P, self.R
        qs = P.quench_kick                              # quench pulses: absolute kick (m75 is scaled below)
        z = torch.zeros(R, 1, device=self.V.device)
        for i in range(10):
            u = torch.rand(R, 5, device=self.V.device)
            rnd8 = torch.randint(0, 8, (R,), device=self.V.device)
            m75, m150 = _stim_logic(self.acc, self.blank_t, self.bx, self.by, self.pad, self.phase, self.ptime,
                                    self.fb_kind, self.sensory_on, self.game_on, u, rnd8,
                                    self.pr["blank"], P.quench_hz / 1000.0, qs)
            self.m75.copy_(m75 * self.pr["kick75"].view(R, 1)); self.m150.copy_(m150)
            spk = self._neurons()
            _after_ms(self.counts, self.blank_t, self.phase, self.ptime, self.fb_stim, self.fb_pause,
                      self.fb_restart, self.ev, self.nev, self.dsq, self.clock, self.bx, self.by, self.bvx,
                      self.bvy, spk.gather(1, self.mot_idx), self.mot_reg, u, self.v)
        self._game()

    def run(self, ms, game=True, plastic=True, use_graph=True):
        """Advance ms milliseconds (a multiple of 10) with the game and plasticity switched on or off."""
        self.game_on.fill_(1.0 if game else 0.0)
        self.plastic.fill_(1.0 if plastic else 0.0)
        nblk = ms // 10
        done = 0
        if use_graph and self.graph is None:
            s = torch.cuda.Stream(); s.wait_stream(torch.cuda.current_stream())
            with torch.cuda.stream(s):
                for _ in range(2):
                    self._block(); self._after_block()
            torch.cuda.current_stream().wait_stream(s)
            self.graph = torch.cuda.CUDAGraph()
            with torch.cuda.graph(self.graph):
                self._block()
            done = 2
        for b in range(done, nblk):
            if use_graph:
                self.graph.replay()
            else:
                self._block()
            self._after_block()

    def reset_recording(self):
        """Discard what was recorded so far (e.g. a warm-up) and start a new chunk."""
        torch.cuda.synchronize()
        self.rec_events, self.rec_base = [], 0
        self.rec_buf.zero_(); self.rec_ptr.zero_(); self.nstep = 0

    def _after_block(self):
        self.nstep += 10
        if self.rec_units is not None and self.nstep % self.rec_chunk == 0:
            ev = self.rec_buf.nonzero().cpu().numpy()
            ev[:, 0] += self.rec_base
            self.rec_base += self.rec_chunk
            self.rec_events.append(ev)
            self.rec_buf.zero_()

    def recorded_trains(self):
        """Spike times (s) of the recorded units: list over runs of lists over units."""
        ev = np.concatenate(self.rec_events) if self.rec_events else np.zeros((0, 3), int)
        U = self.rec_units.shape[1]
        key = ev[:, 1] * U + ev[:, 2]
        order = np.argsort(key, kind="stable")
        ev, key = ev[order], key[order]
        cuts = np.searchsorted(key, np.arange(self.R * U + 1))
        t = ev[:, 0] / 1000.0
        return [[t[cuts[r * U + u]:cuts[r * U + u + 1]] for u in range(U)] for r in range(self.R)]

    def outcomes(self):
        """Per run: array of (t_ms, hit, dsq_at_outcome, dsq_at_feedback_end)."""
        ev = self.ev.cpu().numpy(); n = self.nev.cpu().numpy()
        return [ev[r, :min(n[r], self.max_ev)] for r in range(self.R)]

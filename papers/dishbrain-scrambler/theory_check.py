"""Numerical checks of the Schroedinger and Boltzmann forms of the scrambler (paper, section 2.3 and Appendix A).

1. Discrete chain: H = diag(sqrt P)(I - K)diag(sqrt P) for a random symmetric kernel K; H phi0 = 0 for
   phi0 ~ P^{-1/2}; the stationary law of the per-approach chain equals the normalized phi0^2 (Prop. 1).
2. Continuum, 1D: the stationary density of d_t rho = d_xx(D rho) with reflecting ends is ~1/D (finite volumes);
   the Lamperti form -chi'' + V chi with V = chi0''/chi0, chi0 = D^{-1/4}, has chi0 as zero mode.
3. Speed vs endpoint: with sigma_h = 0 the spectral gap scales as sigma_m^2, the stationary law does not change.
4. Cooling: per-approach variance ~ P^alpha gives rho ~ P^{-alpha}.
    python3 theory_check.py      (numpy)
"""
import numpy as np
rng = np.random.default_rng(0)

# 1. discrete chain
n = 60
A = rng.random((n, n)); A = (A + A.T) / 2 * (rng.random((n, n)) < 0.2); A = np.triu(A, 1); A = A + A.T
K = A / A.sum(1).max(); K += np.diag(np.clip(1 - K.sum(1), 0, None))   # symmetric, stochastic
assert np.allclose(K, K.T) and np.allclose(K.sum(1), 1) and (K >= 0).all()
assert np.linalg.matrix_rank(np.eye(n) - K) == n - 1, "irreducible"
P = rng.uniform(0.05, 0.95, n)
H = np.diag(np.sqrt(P)) @ (np.eye(n) - K) @ np.diag(np.sqrt(P))
phi0 = P ** -0.5
T = np.diag(P) @ K + np.diag(1 - P)                           # per-approach transition matrix (rows)
w, v = np.linalg.eig(T.T); rho = np.real(v[:, np.argmin(abs(w - 1))]); rho /= rho.sum()
ev = np.linalg.eigvalsh(H)
print(f"1. max|H phi0| = {abs(H @ phi0).max():.1e};  max|rho - phi0^2/sum| = {abs(rho - phi0**2 / (phi0**2).sum()).max():.1e};"
      f"  smallest eigenvalues of H {ev[:3].round(6)} (>= 0: {ev.min() > -1e-12})")
print(f"   long-run miss rate {rho @ P:.4f} = harmonic mean {n / (1 / P).sum():.4f} < arithmetic mean {P.mean():.4f}")

# 2. continuum, finite volumes on [0, 1], reflecting ends, flux J = -(D rho)'
m = 400; x = (np.arange(m) + 0.5) / m; h = 1 / m
Pc = 0.5 + 0.4 * np.sin(3 * x) * np.cos(7 * x)
for kappa in (0.0, 0.5, 2.0):
    D = 0.5 * (Pc + kappa * (1 - Pc))                          # sigma_m = 1
    L = np.zeros((m, m))
    for i in range(m - 1):                                     # flux between cells i and i+1: -(D rho)' ~ (Di ri - Dj rj)/h
        L[i, i] -= D[i] / h**2; L[i, i + 1] += D[i + 1] / h**2
        L[i + 1, i + 1] -= D[i + 1] / h**2; L[i + 1, i] += D[i] / h**2
    w, v = np.linalg.eig(L); r = np.real(v[:, np.argmin(abs(w))]); r /= r.sum()
    tgt = (1 / D) / (1 / D).sum()
    print(f"2. kappa={kappa}: max|rho - (1/D)/Z| = {abs(r - tgt).max():.1e}", end="")
    # Lamperti: y = int dx / sqrt(D); chi0 = D^{-1/4}; V = chi0''/chi0 (derivatives in y)
    y = np.concatenate([[0], np.cumsum(h / np.sqrt(D[:-1]))])
    chi0 = D ** -0.25
    d1 = np.gradient(chi0, y); d2 = np.gradient(d1, y)
    q = np.sqrt(D); q1 = np.gradient(q, y); q2 = np.gradient(q1, y)
    V = 0.75 * (q1 / q) ** 2 - 0.5 * q2 / q
    print(f";  Lamperti: max|V - chi0''/chi0| (interior) = {abs(V - d2 / chi0)[5:-5].max():.1e}")

# 3. speed vs endpoint
for sm in (0.5, 1.0, 2.0):
    D = 0.5 * sm**2 * Pc
    Hc = np.zeros((m, m))
    s = np.sqrt(D)
    for i in range(m - 1):                                     # H = -sqrt(D) Lap sqrt(D), Neumann ends
        for a, b in ((i, i + 1), (i + 1, i)):
            Hc[a, a] += s[a] * s[a] / h**2; Hc[a, b] -= s[a] * s[b] / h**2
    e = np.linalg.eigvalsh(Hc)
    g = np.sqrt(1 / D); g /= np.linalg.norm(g)
    print(f"3. sigma_m={sm}: E0={e[0]:.1e}, gap E1={e[1]:.4f} (E1/sigma_m^2 = {e[1]/sm**2:.4f}); "
          f"endpoint mean miss rate {((1/D)/(1/D).sum()) @ Pc:.4f}")

# 4. cooling: D ~ P^alpha
for alpha in (1, 2, 3):
    D = Pc ** alpha; r = (1 / D) / (1 / D).sum()
    print(f"4. alpha={alpha}: stationary miss rate {r @ Pc:.4f} (uniform {Pc.mean():.4f}, best {Pc.min():.4f})")

"""Model behind chapter 13 (pain): the spinal gate as a steady-state rate circuit.

Inhibitory interneuron (GABA/GLYC):  q = [gamma*mu + q0 - delta*nu]_+
Pain output neuron (GLUT):           z = [g*(nu + alpha*mu) - beta*q]_+
In the book (eq:gate): gamma = w_{q mu}, delta = w_{q nu}, alpha = w_{z mu}.
nu - pain input, mu - touch input, g - gain set from above (1 = normal, 2 = sensitized).
Writes figures/pain_gate_{notouch,touch,sens}.dat (nu, z) and prints thresholds and sample values.
"""
gamma, q0, delta, alpha, beta = 1.0, 0.2, 0.5, 0.3, 1.5

def z(nu, mu, g=1.0):
    q = max(gamma * mu + q0 - delta * nu, 0.0)
    return max(g * (nu + alpha * mu) - beta * q, 0.0)

cases = {"notouch": (0.0, 1.0), "touch": (1.0, 1.0), "sens": (0.0, 2.0)}
if __name__ == "__main__":
    grid = [i * 0.01 for i in range(201)]
    for name, (mu, g) in cases.items():
        with open(f"figures/pain_gate_{name}.dat", "w") as f:
            f.writelines(f"{nu:.3f} {z(nu, mu, g):.4f}\n" for nu in grid)
        thr = next(nu for nu in grid if z(nu, mu, g) > 0)
        print(f"{name:8s}: threshold nu={thr:.2f}; z(0.5)={z(0.5,mu,g):.3f} z(1)={z(1,mu,g):.3f} z(2)={z(2,mu,g):.3f}")
    print("touch alone:", z(0.0, 1.0), " touch alone sensitized:", z(0.0, 1.0, 2.0))

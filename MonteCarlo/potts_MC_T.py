import sys
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Energy of 2D Potts configuration
# -----------------------------
def potts_energy(lattice):
    L = lattice.shape[0]
    E = 0
    for x in range(L):
        for y in range(L):
            s = lattice[x, y]
            E -= (s == lattice[x, (y + 1) % L])
            E -= (s == lattice[(x + 1) % L, y])
    return E

# ----------------------------------------------------
# Metropolis sweep
# ----------------------------------------------------
def metropolis_step(lattice, beta, q):
    L = lattice.shape[0]
    for _ in range(L * L):
        # Randomly select a lattice site
        x = np.random.randint(0, L)
        y = np.random.randint(0, L)
        old_s = lattice[x, y]
        # Propose a different Potts state
        new_s = np.random.randint(0, q - 1)
        if new_s >= old_s:
            new_s += 1
        # Four nearest neighbors (periodic boundary conditions)
        neighbors = [
            lattice[(x + 1) % L, y],
            lattice[(x - 1) % L, y],
            lattice[x, (y + 1) % L],
            lattice[x, (y - 1) % L]
        ]

        # Calculate energy difference
        dE = sum(
            int(old_s == s) - int(new_s == s)
            for s in neighbors
        )
        # Metropolis acceptance criterion
        if dE <= 0 or np.random.rand() < np.exp(-beta * dE):
            lattice[x, y] = new_s
    return lattice

# -----------------------------
# Wolff cluster update
# -----------------------------
def wolff_step(lattice, beta, q):
    L = lattice.shape[0]
    x0 = np.random.randint(L)
    y0 = np.random.randint(L)
    s0 = lattice[x0, y0]

    new_s = np.random.randint(q)
    while new_s == s0:
        new_s = np.random.randint(q)

    cluster = [(x0, y0)]
    lattice[x0, y0] = new_s
    stack = [(x0, y0)]

    p_add = 1 - np.exp(-beta)

    while stack:
        x, y = stack.pop()
        neighbors = [((x+1)%L, y), ((x-1)%L, y), (x, (y+1)%L), (x, (y-1)%L)]
        for nx, ny in neighbors:
            if lattice[nx, ny] == s0 and (nx, ny) not in cluster:
                if np.random.rand() < p_add:
                    lattice[nx, ny] = new_s
                    cluster.append((nx, ny))
                    stack.append((nx, ny))

# -----------------------------
# Simulation: energy, Cv, save per-temperature configs
# -----------------------------
def simulate_and_save_per_T(
    L=32, q=4, T=1.0, mcmove='metropolis',
    equi_steps=5000, samples_per_T=10000, save_freq=100):
    file_prefix="potts_configs_q{}L{}T".format(q,L)
    N = L*L
    beta = 1.0 / T
    print(f"Simulating q={q} L={L} Potts model at T = {T:.3f} with {mcmove} Monte Carlo moves")
    lattice = np.random.randint(0, q, size=(L, L))

    # Thermalization
    print(f"equilibrating for {equi_steps} cycles ...")
    for _ in range(equi_steps):
        if mcmove == 'metropolis':
            metropolis_step(lattice, beta, q)
        elif mcmove == 'wolff':
            wolff_step(lattice, beta, q)

    # Sampling
    E_list = []
    configs_T = []

    for i in range(samples_per_T):
        for _ in range(save_freq):
            if mcmove == 'metropolis':
                metropolis_step(lattice, beta, q)
            elif mcmove == 'wolff':
                wolff_step(lattice, beta, q)
        E_list.append(potts_energy(lattice))
        configs_T.append(lattice.flatten())
        print("saving snapshot ",i)

    E_array = np.array(E_list)
    avgE = np.mean(E_array) / N
    Cv = (np.mean(E_array**2) - np.mean(E_array)**2) / (N * T**2)
    print(f"  E = {avgE:.4f}, Cv = {Cv:.4f}")

    # Save configurations for this temperature
    configs_T = np.array(configs_T)
    filename = f"{file_prefix}{T:.3f}.npy"
    np.save(filename, configs_T)
    print(f"  Saved {configs_T.shape[0]} configurations to {filename}")

# -----------------------------
# Run simulation and plot
# -----------------------------
if __name__ == "__main__":
    T = sys.argv[1]
    T = float(T)
    L = 32
    q = 2
    Tc = 1.0 / np.log(1.+np.sqrt(q))
    mcmove = 'wolff'
    n_equ = 20000 # number of equilibrating MC cycles before taking snapshots
    n_samples = 20000 # number of snapshots to be saved
    n_freq = 100 # taking snapshot every n_freq MC cycles
    simulate_and_save_per_T(L=L, q=q, T=T, mcmove=mcmove, equi_steps=n_equ, samples_per_T=n_samples, save_freq=n_freq) 


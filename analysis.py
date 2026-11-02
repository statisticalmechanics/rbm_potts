import numpy as np
import math
import sys
import os

def delta(i, j):
    return np.equal(i, j).astype(int)

def main():
  input_dir = sys.argv[1]
  input_file = sys.argv[2]
  T = sys.argv[3]
  T = float(T)
  beta = 1.0/T
  J = 1.0
  q = 2
  #cwd = os.getcwd()
  #path = os.path.join(input_dir, input_file)
  #filename = os.path.join(input_dir, "potts_configs_q2L32T{:.3f}.npy".format(T))   

  filename = os.path.join(input_dir, "{}{:.3f}.npy".format(input_file, T))

  data = np.load(filename)
  print('analyze configuration file:', filename)
  print("Data shape:", data.shape)
  print('Temperature is',T)
  
  n_configs = data.shape[0]
  N = data.shape[1]
  L = (int)(np.sqrt(N))
  # Reshape into (number of configurations, L, L)
  configs = data.reshape(-1, L, L)

  # Check spin states
  assert np.all((configs >= 0) & (configs < q)), "Spin states must be between 0 and q-1"

  # ==========================================
  # 1. Energy
  # ==========================================
  # Periodic boundary conditions
  # Count each nearest-neighbor bond only once

  right = np.roll(configs, shift=-1, axis=2)
  down = np.roll(configs, shift=-1, axis=1)
  E = -J * ( np.sum(configs == right, axis=(1, 2)) + np.sum(configs == down, axis=(1, 2)) )
  # Energy per site
  e = E / N

  # ==========================================
  # 2. Magnetization
  # ==========================================
  # Fraction of spins in each Potts state
  rho = np.stack([np.mean(configs == a, axis=(1, 2)) for a in range(q)], axis=1)
  # Scalar magnetization
  m = (q * np.max(rho, axis=1) - 1) / (q - 1)
    
  filename = os.path.join(input_dir, "gen_ME_q2L32T{:.3f}.txt".format(T))
  np.savetxt(filename,np.column_stack((m, e)))

  # ==========================================
  # 3. Thermal averages
  # ==========================================
  E_mean = np.mean(E)
  E2_mean = np.mean(E**2)

  m_mean = np.mean(m)
  m2_mean = np.mean(m**2)

  e_mean = E_mean / N

  # ==========================================
  # 4. Heat capacity per site
  # ==========================================
  C = beta**2 * (E2_mean - E_mean**2) / N

  # ==========================================
  # 5. Magnetic susceptibility per site
  # ==========================================
  chi = beta * N * (m2_mean - m_mean**2)

  # ==========================================
  # Results
  # ==========================================
  print("\n========== Potts Model Observables ==========")
  print(f"Number of configurations: {n_configs}")
  print(f"Energy per site       = {e_mean:.6f}")
  print(f"Magnetization         = {m_mean:.6f}")
  print(f"Heat capacity         = {C:.6f}")
  print(f"Susceptibility        = {chi:.6f}")
  print(f"{T:.3f} {e_mean:.6f} {m_mean:.8f} {C:.6f} {chi:.6f}")
  print("=============================================")

if __name__ == "__main__":
  main()





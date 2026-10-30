# rbm_potts
RBM Potts model


Monte Carlo generated Potts model configuration files for training need to be stored at, e.g. `./2dPotts_L32/potts_configs_q2L32T0.600.npy`

RBM generated configuration files will be saved at, e.g. `./q2L32_gen/gen_configs_q2L32T0.600.npy`

To run RBM learning and generation at one temperature, e.g. T = 0.65
```bash
python rbm_potts.py 0.650
```
You need to manually set or change q(=2), L(=32), nh(=512), n_epochs(=500), lr(=0.01), cd or pdf, k(=10) ... in the python script

To run over all temperatures in the range specified in the bash script 
```bash
./run_all.sh
```

To calculate thermal quantities, e.g. energy, magnetization, heat capacity, susceptibility, using configurations at one temperature
```bash
python analysis.py ./2dPotts_L32 potts_configs_q2L32T 0.650
```
or for generated configurations
```bash
python analysis.py ./q2L32_gen gen_configs_q2L32T 0.650
```

To run over all temperatures, use the bash script
```bash
./analysis_all.sh
```
which save all results in `potts_thermal_q2L32.dat` (MC) or `gen_thermal_q2L32.dat`

gnuplot script `plot` make the plot by
```bash
gnuplot plot
```


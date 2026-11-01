#!/bin/bash

for T in 0.60 0.65 0.7 0.75 0.8 0.85 0.9 0.95 1.0 1.05 1.1 1.15 1.2 1.25 1.3 1.35 1.4 1.45 1.5 1.55 1.6
do
    echo "Monte Carlo simulation at T = $T"

    nohup python -u potts_MC_T.py "$T" > "output_T${T}.log" 2>&1 &

done

wait
echo "All simulations completed!"



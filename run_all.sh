#!/bin/sh

#T=0.7
#for T in 0.6 0.75 0.8 0.85 0.9 0.95 1.15
for T in 1.25 1.3 1.45 1.6
do
    echo 'Learning data at temperature T =' $T

    nohup python -u rbm_potts.py "$T" > "output_T${T}.log" 2>&1 &

done



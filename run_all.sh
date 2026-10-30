#!/bin/sh

#T=0.7
for T in 0.7 0.8 0.85 0.9 0.95 1.0 1.05 1.1 1.15 1.2 1.3 1.4 1.5 1.6
do

echo 'Learning data at temperature T =' $T

python rbm_potts.py $T

done



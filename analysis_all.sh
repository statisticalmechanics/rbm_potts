#!/bin/bash

# Temperature range
T_start=0.600
T_end=1.600
dT=0.050

# Output file
#output="potts_thermal_q2L32.dat"
output="gen_thermal_q2L32.dat"

# Clear previous output and write header
echo "# T  e  m  cv  chi" > "$output"

# Temporary directory for individual results
rm -r temp_results
mkdir -p temp_results

# Iterate over temperatures
T=$T_start

while (( $(echo "$T <= $T_end" | bc -l) )); do

    T_formatted=$(printf "%.3f" "$T")

    echo "Processing T = $T_formatted"

    #python analysis.py ./2dPotts_L32 potts_configs_q2L32T "$T_formatted" \
    python analysis.py ./q2L32_gen gen_configs_q2L32T "$T_formatted" \
        > "temp_results/result_T${T_formatted}.dat"

    # Append result to final file
    #cat "temp_results/result_T${T_formatted}.dat" >> "$output"
    #grep "T = " "temp_results/result_T${T_formatted}.dat" >> "$output"
    tail -n 2 "temp_results/result_T${T_formatted}.dat" | head -n 1 >> "$output"

    T=$(echo "$T + $dT" | bc)

done

echo "All calculations completed!"
echo "Results saved in $output"

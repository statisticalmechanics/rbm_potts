set terminal pngcairo size 1200,900 enhanced font "Arial,14"
#set terminal qt size 1200,900
set output "thermal.png"
set multiplot layout 2,2

set grid
set border linewidth 1.5
set tics scale 0.7

# Panel 1: Energy
set key top left
set title "Energy"
set xlabel "T"
set ylabel "e"
plot "potts_thermal_q2L32.dat" using 1:2 with linespoints lt 1 lw 2 lc rgb "red" pt 1 ps 2 title "MC",\
"gen_thermal_q2L32.dat" using 1:2 with linespoints lt 1 lw 2 lc rgb "blue" pt 2 ps 2 title "RBM gen"

# Panel 2: Magnetization
set key top right
set title "Magnetization"
set xlabel "T"
set ylabel "m"
plot "potts_thermal_q2L32.dat" using 1:3 with linespoints lt 1 lw 2 lc rgb "red" pt 1 ps 2 title "MC",\
"gen_thermal_q2L32.dat" using 1:3 with linespoints lt 1 lw 2 lc rgb "blue" pt 2 ps 2 title "RBM gen"

# Panel 3: Heat capacity
set title "Heat Capacity"
set xlabel "T"
set ylabel "Cv"
plot "potts_thermal_q2L32.dat" using 1:4 with linespoints lt 1 lw 2 lc rgb "red" pt 1 ps 2 title "MC",\
"gen_thermal_q2L32.dat" using 1:4 with linespoints lt 1 lw 2 lc rgb "blue" pt 2 ps 2 title "RBM gen"

# Panel 4: Susceptibility
set title "Susceptibility"
set xlabel "T"
set ylabel "Chi"
plot "potts_thermal_q2L32.dat" using 1:5 with linespoints lt 1 lw 2 lc rgb "red" pt 1 ps 2 title "MC",\
"gen_thermal_q2L32.dat" using 1:5 with linespoints lt 1 lw 2 lc rgb "blue" pt 2 ps 2 title "RBM gen"

unset multiplot
#unset output
pause -1

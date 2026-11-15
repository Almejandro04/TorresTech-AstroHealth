# Test fixtures / Fixtures de prueba

`bidmc_99_Numerics.csv` is an **invented test fixture**. It uses the exact BIDMC
Numerics format (header `Time [s], HR, PULSE, RESP, SpO2`, 1 Hz rows), but its
values were written by hand for the tests. Subject 99 does not exist in BIDMC
(which has subjects 01-53). It contains NaN cells, a duplicated second (t=30),
two shape failures (HR=0 at t=5, SpO2=101 at t=20) and a row with no values
(t=100).

`bidmc_99_Numerics.csv` es un **fixture de prueba inventado**. Usa el formato
exacto de Numerics de BIDMC, pero sus valores se escribieron a mano para las
pruebas. El sujeto 99 no existe en BIDMC (sujetos 01-53). Incluye celdas NaN, un
segundo duplicado (t=30), dos fallos de forma (HR=0 en t=5, SpO2=101 en t=20) y
una fila sin valores (t=100).

# Análisis de results/antes/recovery-20261108-213328

Calculado desde `raw.csv.gz` (todas las muestras) y `resources.csv`. Ventanas de 10 s en `timeline.csv`.

## Por fase y endpoint

| fase     | endpoint     |   solicitudes |   req/s |   p50_ms |   p90_ms |   p95_ms |   p99_ms |   max_ms |   error_% |   409/422 |   dropped |
|:---------|:-------------|--------------:|--------:|---------:|---------:|---------:|---------:|---------:|----------:|----------:|----------:|
| recovery | (todos)      |          1791 |    9.9  |    108.5 |   1216.4 |   1917   |   3335.6 |  10718.1 |         0 |       205 |         9 |
| recovery | availability |          1069 |    5.91 |     12.4 |    718.3 |   1525.4 |   2854.7 |   3817.7 |         0 |         0 |           |
| recovery | list         |           451 |    2.49 |    323.3 |   1816.6 |   2217.8 |   6978.1 |  10718.1 |         0 |         0 |           |
| recovery | create       |           271 |    1.5  |    124   |    915.2 |   1816.2 |   3333.5 |   3717.8 |         0 |       205 |           |

## Recursos (promedio y máximo durante la corrida)

|      |   cpu_api |   cpu_db |   cpu_k6 |   mem_api_mib |   mem_db_mib |   pg_active |
|:-----|----------:|---------:|---------:|--------------:|-------------:|------------:|
| mean |       3.8 |     74.9 |      3.1 |          27.2 |        124   |         3.2 |
| max  |       7.9 |    100.3 |      3.6 |          27.2 |        130.1 |        11   |

## Por minuto (ofrecidas ≈ logradas + dropped)

|   minute |   req/s logradas |   dropped/s |   p95_ms |   p99_ms |   error_% | fase     |   ofrecidas/s≈ |
|---------:|-----------------:|------------:|---------:|---------:|----------:|:---------|---------------:|
|        0 |              9.8 |        0.15 |   2789.3 |   5712.5 |         0 | recovery |           10   |
|        1 |             10   |        0    |    612.7 |   1710.5 |         0 | recovery |           10   |
|        2 |             10   |        0    |    815.9 |   2119.6 |         0 | recovery |           10   |
|        3 |              0.1 |        0    |    193.4 |    204.3 |         0 | recovery |            0.1 |

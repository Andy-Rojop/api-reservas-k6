# Análisis de results/antes/recovery-20261108-210620

Calculado desde `raw.csv.gz` (todas las muestras) y `resources.csv`. Ventanas de 10 s en `timeline.csv`.

## Por fase y endpoint

| fase     | endpoint     |   solicitudes |   req/s |   p50_ms |   p90_ms |   p95_ms |   p99_ms |   max_ms |   error_% |   409/422 |   dropped |
|:---------|:-------------|--------------:|--------:|---------:|---------:|---------:|---------:|---------:|----------:|----------:|----------:|
| recovery | (todos)      |          1800 |    9.94 |     92.9 |    700.7 |   1101.4 |   2601.8 |   6103.8 |         0 |        35 |         1 |
| recovery | availability |          1075 |    5.94 |      9.6 |    200.8 |    398.3 |   1127.5 |   1808.4 |         0 |         0 |           |
| recovery | list         |           453 |    2.5  |    297.2 |   1301   |   2242.8 |   4409.5 |   6103.8 |         0 |         0 |           |
| recovery | create       |           272 |    1.5  |    107.4 |   1001.2 |   1301.4 |   1895.9 |   2298.6 |         0 |        35 |           |

## Recursos (promedio y máximo durante la corrida)

|      |   cpu_api |   cpu_db |   cpu_k6 |   mem_api_mib |   mem_db_mib |   pg_active |
|:-----|----------:|---------:|---------:|--------------:|-------------:|------------:|
| mean |       3.8 |     77.3 |      3.1 |          26.9 |        116.2 |         2.7 |
| max  |       5.4 |    108.6 |      4.4 |          27.2 |        121.8 |        12   |

## Por minuto (ofrecidas ≈ logradas + dropped)

|   minute |   req/s logradas |   dropped/s |   p95_ms |   p99_ms |   error_% | fase     |   ofrecidas/s≈ |
|---------:|-----------------:|------------:|---------:|---------:|----------:|:---------|---------------:|
|        0 |              9.9 |        0.02 |   1433.7 |   3524.7 |         0 | recovery |            9.9 |
|        1 |              9.9 |        0    |    799.1 |   1596.3 |         0 | recovery |            9.9 |
|        2 |             10.1 |        0    |    998.7 |   2881.4 |         0 | recovery |           10.1 |
|        3 |              0.1 |        0    |    430.2 |    496   |         0 | recovery |            0.1 |

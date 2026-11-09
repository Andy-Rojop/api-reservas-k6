# Análisis de results/antes/recovery-20261108-215428

Calculado desde `raw.csv.gz` (todas las muestras) y `resources.csv`. Ventanas de 10 s en `timeline.csv`.

## Por fase y endpoint

| fase     | endpoint     |   solicitudes |   req/s |   p50_ms |   p90_ms |   p95_ms |   p99_ms |   max_ms |   error_% |   409/422 |   dropped |
|:---------|:-------------|--------------:|--------:|---------:|---------:|---------:|---------:|---------:|----------:|----------:|----------:|
| recovery | (todos)      |          1801 |    9.95 |      5.1 |     35.9 |     51.9 |     73   |   2588.7 |    21.766 |       108 |         0 |
| recovery | availability |          1078 |    5.96 |      4.8 |      7.6 |     50.9 |     52.2 |   2588.7 |    27.551 |         0 |           |
| recovery | list         |           453 |    2.5  |      5.5 |     34.7 |     53.5 |    209.6 |   2523.6 |     4.194 |         0 |           |
| recovery | create       |           270 |    1.49 |      9.6 |     56.7 |     58.7 |     79.4 |   2398.3 |    28.148 |       108 |           |

## Recursos (promedio y máximo durante la corrida)

|      |   cpu_api |   cpu_db |   cpu_k6 |   mem_api_mib |   mem_db_mib |   pg_active |
|:-----|----------:|---------:|---------:|--------------:|-------------:|------------:|
| mean |       5.6 |     46.9 |      5.1 |          30.2 |        120.8 |         0.7 |
| max  |      12   |    101.9 |      9.5 |          37.8 |        197.2 |         3   |

## Por minuto (ofrecidas ≈ logradas + dropped)

|   minute |   req/s logradas |   dropped/s |   p95_ms |   p99_ms |   error_% | fase     |   ofrecidas/s≈ |
|---------:|-----------------:|------------:|---------:|---------:|----------:|:---------|---------------:|
|        0 |              9.9 |           0 |     10.8 |     52.6 |      0    | recovery |            9.9 |
|        1 |             10   |           0 |     56.9 |     71.5 |     18.17 | recovery |           10   |
|        2 |             10   |           0 |     15   |   1992.3 |     47.17 | recovery |           10   |
|        3 |              0.1 |           0 |     13   |     13.4 |      0    | recovery |            0.1 |

# Análisis de results/despues/load-20261108-215815

Calculado desde `raw.csv.gz` (todas las muestras) y `resources.csv`. Ventanas de 10 s en `timeline.csv`.

## Por fase y endpoint

| fase   | endpoint     |   solicitudes |   req/s |   p50_ms |   p90_ms |   p95_ms |   p99_ms |   max_ms |   error_% |   409/422 |   dropped |
|:-------|:-------------|--------------:|--------:|---------:|---------:|---------:|---------:|---------:|----------:|----------:|----------:|
| ramp   | (todos)      |           629 |   10.48 |      6   |     13   |     15.2 |     82.4 |    130.6 |         0 |         2 |         0 |
| ramp   | availability |           377 |    6.28 |      5.6 |      6.8 |      7.4 |      9.5 |     38.9 |         0 |         0 |           |
| ramp   | list         |           159 |    2.65 |      6.2 |     37.6 |     48.8 |    114.7 |    130.6 |         0 |         0 |           |
| ramp   | create       |            93 |    1.55 |     12.7 |     14.6 |     16.1 |     24.7 |     48.1 |         0 |         2 |           |
| steady | (todos)      |         12001 |   19.97 |      5.4 |     12   |     13.4 |     42   |    214.2 |         0 |        25 |         0 |
| steady | availability |          7288 |   12.13 |      5.1 |      6.1 |      6.7 |      8.8 |     58.1 |         0 |         0 |           |
| steady | list         |          2916 |    4.85 |      5.7 |     32.5 |     37.3 |    102.8 |    214.2 |         0 |         0 |           |
| steady | create       |          1797 |    2.99 |     12   |     14   |     15.5 |     20.4 |     77.4 |         0 |        25 |           |

## Recursos (promedio y máximo durante la corrida)

|      |   cpu_api |   cpu_db |   cpu_k6 |   mem_api_mib |   mem_db_mib |   pg_active |
|:-----|----------:|---------:|---------:|--------------:|-------------:|------------:|
| mean |       6.4 |     10   |      4.8 |          30.5 |        119.7 |         0.1 |
| max  |      15.3 |     26.2 |      6.5 |          31.6 |        127.2 |         3   |

## Por minuto (ofrecidas ≈ logradas + dropped)

|   minute |   req/s logradas |   dropped/s |   p95_ms |   p99_ms |   error_% | fase   |   ofrecidas/s≈ |
|---------:|-----------------:|------------:|---------:|---------:|----------:|:-------|---------------:|
|        0 |             10.7 |           0 |     15.2 |     81.1 |         0 | ramp   |           10.7 |
|        1 |             20   |           0 |     13.4 |     37.2 |         0 | steady |           20   |
|        2 |             20   |           0 |     15.3 |     56.5 |         0 | steady |           20   |
|        3 |             20   |           0 |     14.6 |     61.5 |         0 | steady |           20   |
|        4 |             20   |           0 |     13.2 |     41   |         0 | steady |           20   |
|        5 |             20   |           0 |     12.9 |     34.9 |         0 | steady |           20   |
|        6 |             20   |           0 |     12.8 |     37.9 |         0 | steady |           20   |
|        7 |             20   |           0 |     12.4 |     35.6 |         0 | steady |           20   |
|        8 |             20   |           0 |     12.6 |     36.5 |         0 | steady |           20   |
|        9 |             20   |           0 |     14.2 |     60.3 |         0 | steady |           20   |
|       10 |             19.8 |           0 |     13   |     45.8 |         0 | steady |           19.8 |

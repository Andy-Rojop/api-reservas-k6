# Análisis de results/despues/load-20261108-221137

Calculado desde `raw.csv.gz` (todas las muestras) y `resources.csv`. Ventanas de 10 s en `timeline.csv`.

## Por fase y endpoint

| fase   | endpoint     |   solicitudes |   req/s |   p50_ms |   p90_ms |   p95_ms |   p99_ms |   max_ms |   error_% |   409/422 |   dropped |
|:-------|:-------------|--------------:|--------:|---------:|---------:|---------:|---------:|---------:|----------:|----------:|----------:|
| ramp   | (todos)      |           630 |   10.5  |      5.9 |     12.9 |     14   |     38.3 |     46.7 |         0 |         2 |         0 |
| ramp   | availability |           382 |    6.37 |      5.6 |      6.5 |      6.8 |      7.7 |     12.5 |         0 |         0 |           |
| ramp   | list         |           158 |    2.63 |      6.3 |     33.8 |     36.9 |     41.3 |     46.7 |         0 |         0 |           |
| ramp   | create       |            90 |    1.5  |     12.9 |     14.1 |     14.8 |     17.9 |     18.4 |         0 |         2 |           |
| steady | (todos)      |         12001 |   19.97 |      5.3 |     11.7 |     12.8 |     37.8 |    177.5 |         0 |        24 |         0 |
| steady | availability |          7200 |   11.98 |      5   |      5.9 |      6.2 |      7   |     45.9 |         0 |         0 |           |
| steady | list         |          2982 |    4.96 |      5.6 |     31   |     35.1 |     54.9 |    132.3 |         0 |         0 |           |
| steady | create       |          1819 |    3.03 |     11.6 |     13.1 |     13.9 |     33.4 |    177.5 |         0 |        24 |           |

## Recursos (promedio y máximo durante la corrida)

|      |   cpu_api |   cpu_db |   cpu_k6 |   mem_api_mib |   mem_db_mib |   pg_active |
|:-----|----------:|---------:|---------:|--------------:|-------------:|------------:|
| mean |       6.1 |     11.4 |      5   |          28   |         92.6 |         0.1 |
| max  |       9.6 |     25.2 |      6.6 |          29.2 |        101.4 |         1.5 |

## Por minuto (ofrecidas ≈ logradas + dropped)

|   minute |   req/s logradas |   dropped/s |   p95_ms |   p99_ms |   error_% | fase   |   ofrecidas/s≈ |
|---------:|-----------------:|------------:|---------:|---------:|----------:|:-------|---------------:|
|        0 |             10.7 |           0 |     14   |     38.3 |         0 | ramp   |           10.7 |
|        1 |             20   |           0 |     12.6 |     31.8 |         0 | steady |           20   |
|        2 |             20   |           0 |     12.7 |     38.7 |         0 | steady |           20   |
|        3 |             20   |           0 |     12.9 |     35   |         0 | steady |           20   |
|        4 |             20   |           0 |     12.7 |     37.8 |         0 | steady |           20   |
|        5 |             20   |           0 |     13   |     41   |         0 | steady |           20   |
|        6 |             20   |           0 |     14.6 |     45   |         0 | steady |           20   |
|        7 |             20   |           0 |     13.2 |     37.3 |         0 | steady |           20   |
|        8 |             20   |           0 |     12.4 |     34.9 |         0 | steady |           20   |
|        9 |             20   |           0 |     12.4 |     35.8 |         0 | steady |           20   |
|       10 |             19.8 |           0 |     12.6 |     37.8 |         0 | steady |           19.8 |

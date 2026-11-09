# Análisis de results/despues/load-20261108-214435

Calculado desde `raw.csv.gz` (todas las muestras) y `resources.csv`. Ventanas de 10 s en `timeline.csv`.

## Por fase y endpoint

| fase   | endpoint     |   solicitudes |   req/s |   p50_ms |   p90_ms |   p95_ms |   p99_ms |   max_ms |   error_% |   409/422 |   dropped |
|:-------|:-------------|--------------:|--------:|---------:|---------:|---------:|---------:|---------:|----------:|----------:|----------:|
| ramp   | (todos)      |           629 |   10.48 |      5.8 |     12.6 |     14   |     38.3 |     93   |         0 |         2 |         0 |
| ramp   | availability |           380 |    6.33 |      5.5 |      6.3 |      6.6 |      8.6 |     10.4 |         0 |         0 |           |
| ramp   | list         |           161 |    2.68 |      6.2 |     33.7 |     36.1 |     45.8 |     93   |         0 |         0 |           |
| ramp   | create       |            88 |    1.47 |     12.6 |     14.1 |     14.4 |     15.7 |     19   |         0 |         2 |           |
| steady | (todos)      |         12001 |   19.97 |      5.3 |     11.8 |     13   |     41.1 |    153.5 |         0 |        20 |         0 |
| steady | availability |          7231 |   12.03 |      5   |      5.9 |      6.2 |      7.9 |     49.1 |         0 |         0 |           |
| steady | list         |          2975 |    4.95 |      5.5 |     32.4 |     36.4 |     99.7 |    153.5 |         0 |         0 |           |
| steady | create       |          1795 |    2.99 |     11.8 |     13.2 |     14.1 |     23.3 |     61.5 |         0 |        20 |           |

## Recursos (promedio y máximo durante la corrida)

|      |   cpu_api |   cpu_db |   cpu_k6 |   mem_api_mib |   mem_db_mib |   pg_active |
|:-----|----------:|---------:|---------:|--------------:|-------------:|------------:|
| mean |       6.3 |     11.7 |      5.2 |          26.1 |         93.2 |         0.1 |
| max  |       9.3 |     25.6 |     10   |          27.3 |        102.4 |         2   |

## Por minuto (ofrecidas ≈ logradas + dropped)

|   minute |   req/s logradas |   dropped/s |   p95_ms |   p99_ms |   error_% | fase   |   ofrecidas/s≈ |
|---------:|-----------------:|------------:|---------:|---------:|----------:|:-------|---------------:|
|        0 |             10.5 |           0 |     14   |     38.3 |         0 | ramp   |           10.5 |
|        1 |             20   |           0 |     13.2 |     36   |         0 | steady |           20   |
|        2 |             20   |           0 |     12.9 |     36.3 |         0 | steady |           20   |
|        3 |             20   |           0 |     13.2 |     38.4 |         0 | steady |           20   |
|        4 |             20   |           0 |     12.6 |     35   |         0 | steady |           20   |
|        5 |             20   |           0 |     12.6 |     37.9 |         0 | steady |           20   |
|        6 |             20   |           0 |     13   |     46.4 |         0 | steady |           20   |
|        7 |             20   |           0 |     13.2 |     50.6 |         0 | steady |           20   |
|        8 |             20   |           0 |     12.4 |     36.4 |         0 | steady |           20   |
|        9 |             20   |           0 |     13.3 |     54.5 |         0 | steady |           20   |
|       10 |             20   |           0 |     13.3 |     52.6 |         0 | steady |           20   |

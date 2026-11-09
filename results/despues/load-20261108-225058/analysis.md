# Análisis de results/despues/load-20261108-225058

Calculado desde `raw.csv.gz` (todas las muestras) y `resources.csv`. Ventanas de 10 s en `timeline.csv`.

## Por fase y endpoint

| fase   | endpoint     |   solicitudes |   req/s |   p50_ms |   p90_ms |   p95_ms |   p99_ms |   max_ms |   error_% |   409/422 |   dropped |
|:-------|:-------------|--------------:|--------:|---------:|---------:|---------:|---------:|---------:|----------:|----------:|----------:|
| ramp   | (todos)      |           629 |   10.48 |      6.4 |     13.8 |     18.7 |     81.1 |    380.3 |         0 |         2 |         0 |
| ramp   | availability |           384 |    6.4  |      5.9 |      8.9 |     10.7 |     28.9 |    136.1 |         0 |         0 |           |
| ramp   | list         |           151 |    2.52 |      6.5 |     36.1 |     64.7 |    216.5 |    380.3 |         0 |         0 |           |
| ramp   | create       |            94 |    1.57 |     13.2 |     17.8 |     19.1 |     24   |     29.7 |         0 |         2 |           |
| steady | (todos)      |         12001 |   19.97 |      5   |     11.4 |     12.4 |     35.2 |    229.5 |         0 |        19 |         0 |
| steady | availability |          7295 |   12.14 |      4.7 |      5.5 |      5.9 |      6.7 |    180.6 |         0 |         0 |           |
| steady | list         |          2957 |    4.92 |      5.2 |     32.2 |     34.5 |     73   |    229.5 |         0 |         0 |           |
| steady | create       |          1749 |    2.91 |     11.3 |     12.7 |     13.3 |     17.2 |     79.4 |         0 |        19 |           |

## Recursos (promedio y máximo durante la corrida)

|      |   cpu_api |   cpu_db |   cpu_k6 |   mem_api_mib |   mem_db_mib |   pg_active |
|:-----|----------:|---------:|---------:|--------------:|-------------:|------------:|
| mean |       6.3 |     11.4 |      4.6 |          26.2 |         92.8 |         0.1 |
| max  |      14.5 |     21.2 |      7   |          27.4 |        103.2 |         2   |

## Por minuto (ofrecidas ≈ logradas + dropped)

|   minute |   req/s logradas |   dropped/s |   p95_ms |   p99_ms |   error_% | fase   |   ofrecidas/s≈ |
|---------:|-----------------:|------------:|---------:|---------:|----------:|:-------|---------------:|
|        0 |             10.5 |           0 |     18.6 |     81.1 |         0 | ramp   |           10.5 |
|        1 |             20   |           0 |     13.2 |     38.8 |         0 | steady |           20   |
|        2 |             20   |           0 |     12.8 |     35   |         0 | steady |           20   |
|        3 |             20   |           0 |     12.8 |     36.8 |         0 | steady |           20   |
|        4 |             20   |           0 |     12.5 |     34.8 |         0 | steady |           20   |
|        5 |             20   |           0 |     12   |     39.3 |         0 | steady |           20   |
|        6 |             20   |           0 |     12.1 |     35.8 |         0 | steady |           20   |
|        7 |             20   |           0 |     12.1 |     34.6 |         0 | steady |           20   |
|        8 |             20   |           0 |     11.8 |     34.6 |         0 | steady |           20   |
|        9 |             20   |           0 |     11.6 |     34.8 |         0 | steady |           20   |
|       10 |             20   |           0 |     11.6 |     33.1 |         0 | steady |           20   |

# Análisis de results/antes/stress-20261108-210439

Calculado desde `raw.csv.gz` (todas las muestras) y `resources.csv`. Ventanas de 10 s en `timeline.csv`.

## Por fase y endpoint

| fase   | endpoint     |   solicitudes |   req/s |   p50_ms |   p90_ms |   p95_ms |   p99_ms |   max_ms |   error_% |   409/422 |   dropped |
|:-------|:-------------|--------------:|--------:|---------:|---------:|---------:|---------:|---------:|----------:|----------:|----------:|
| stress | (todos)      |           606 |    9.18 |   2328   |   4181.2 |   5180.9 |   6457.6 |  10593.2 |         0 |         1 |         0 |
| stress | availability |           357 |    5.41 |   2572.8 |   3881.3 |   5188.2 |   6061.9 |   6147.1 |         0 |         0 |           |
| stress | list         |           170 |    2.58 |   1941.3 |   3151   |   4592.3 |   9318.1 |  10593.2 |         0 |         0 |           |
| stress | create       |            79 |    1.2  |   3111.5 |   4818.2 |   6033.6 |   6576.9 |   6977.5 |         0 |         1 |           |

## Recursos (promedio y máximo durante la corrida)

|      |   cpu_api |   cpu_db |   cpu_k6 |   mem_api_mib |   mem_db_mib |   pg_active |
|:-----|----------:|---------:|---------:|--------------:|-------------:|------------:|
| mean |       5.2 |     66.6 |      3.1 |          21.6 |        103.2 |           7 |
| max  |      10.3 |    102.4 |      5.3 |          25.4 |        119.6 |          15 |

## Por minuto (ofrecidas ≈ logradas + dropped)

|   minute |   req/s logradas |   dropped/s |   p95_ms |   p99_ms |   error_% | fase   |   ofrecidas/s≈ |
|---------:|-----------------:|------------:|---------:|---------:|----------:|:-------|---------------:|
|        0 |              9.2 |        0.27 |   4099.5 |   4977.7 |         0 | stress |            9.5 |
|        1 |              0.9 |        0.52 |   6374.8 |   8026   |         0 | stress |            1.4 |

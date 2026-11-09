# Análisis de results/despues/smoke-20261108-214115

Calculado desde `raw.csv.gz` (todas las muestras) y `resources.csv`. Ventanas de 10 s en `timeline.csv`.

## Por fase y endpoint

| fase   | endpoint     |   solicitudes |   req/s |   p50_ms |   p90_ms |   p95_ms |   p99_ms |   max_ms |   error_% |   409/422 |   dropped |
|:-------|:-------------|--------------:|--------:|---------:|---------:|---------:|---------:|---------:|----------:|----------:|----------:|
| -      | (todos)      |           184 |    3.07 |      5.9 |      9.5 |     10.5 |     13.7 |     14.6 |         0 |        63 |         0 |
| -      | availability |            59 |    0.98 |      5.6 |      6.4 |      6.8 |      7.4 |      7.6 |         0 |         0 |           |
| -      | list         |            59 |    0.98 |      5.3 |      6.7 |      7.6 |      9.8 |     12   |         0 |         0 |           |
| -      | create       |            59 |    0.98 |      8.9 |     10.8 |     13.5 |     14.1 |     14.6 |         0 |        59 |           |

## Recursos (promedio y máximo durante la corrida)

|      |   cpu_api |   cpu_db |   cpu_k6 |   mem_api_mib |   mem_db_mib |   pg_active |
|:-----|----------:|---------:|---------:|--------------:|-------------:|------------:|
| mean |       1.6 |      3.8 |      1.2 |          19.7 |         76.4 |           0 |
| max  |       3.5 |      8.3 |      1.4 |          20.6 |         76.5 |           0 |

## Por minuto (ofrecidas ≈ logradas + dropped)

|   minute |   req/s logradas |   dropped/s |   p95_ms |   p99_ms |   error_% | fase   |   ofrecidas/s≈ |
|---------:|-----------------:|------------:|---------:|---------:|----------:|:-------|---------------:|
|        0 |              3.1 |           0 |     10.5 |     13.7 |         0 | -      |            3.1 |
|        1 |            nan   |           0 |    nan   |    nan   |       nan | -      |          nan   |

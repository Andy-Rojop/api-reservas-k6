# Análisis de results/antes/smoke-20261108-202100

Calculado desde `raw.csv.gz` (todas las muestras) y `resources.csv`. Ventanas de 10 s en `timeline.csv`.

## Por fase y endpoint

| fase   | endpoint     |   solicitudes |   req/s |   p50_ms |   p90_ms |   p95_ms |   p99_ms |   max_ms |   error_% |   409/422 |   dropped |
|:-------|:-------------|--------------:|--------:|---------:|---------:|---------:|---------:|---------:|----------:|----------:|----------:|
| -      | (todos)      |           157 |    2.57 |     89.1 |    101.7 |    103   |    177   |    187.1 |         0 |        54 |         0 |
| -      | availability |            50 |    0.82 |      9.8 |     11   |     11.3 |     16.3 |     21   |         0 |         0 |           |
| -      | list         |            50 |    0.82 |     89.2 |     94.6 |     99.6 |    136.6 |    171.8 |         0 |         0 |           |
| -      | create       |            50 |    0.82 |     99.7 |    105   |    108.2 |    185.4 |    187.1 |         0 |        50 |           |

## Recursos (promedio y máximo durante la corrida)

|      |   cpu_api |   cpu_db |   cpu_k6 |   mem_api_mib |   mem_db_mib |   pg_active |
|:-----|----------:|---------:|---------:|--------------:|-------------:|------------:|
| mean |       1.2 |     20.3 |      1.4 |          19.1 |         81.6 |           0 |
| max  |       2.6 |     28.3 |      1.6 |          20.3 |         81.8 |           0 |

## Por minuto (ofrecidas ≈ logradas + dropped)

|   minute |   req/s logradas |   dropped/s |   p95_ms |   p99_ms |   error_% | fase   |   ofrecidas/s≈ |
|---------:|-----------------:|------------:|---------:|---------:|----------:|:-------|---------------:|
|        0 |              2.6 |           0 |    103   |    177.4 |         0 | -      |            2.6 |
|        1 |              0   |           0 |     98.2 |     99.3 |         0 | -      |            0   |

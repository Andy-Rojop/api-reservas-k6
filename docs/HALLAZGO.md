# Hallazgo: consultas sin índice adecuado saturan PostgreSQL y bloquean el pool de conexiones

> Los valores entre `‹ ›` se completan con **tus** corridas (`results/antes/…` y `results/despues/…`).
> Cada número del informe debe poder rastrearse a un archivo de esas carpetas.

## 1. Problema observado (síntoma)

En el estrés progresivo (`v1-baseline`), la latencia sube de forma no lineal a partir de ‹escalón› req/s y
en los escalones finales el p95 de **todos** los endpoints llega a ‹x› s, incluso el de disponibilidad, cuya consulta es
barata. Aparecen `dropped_iterations` (‹n›) aunque el CPU de k6 se mantiene en ‹y› % → no es el generador.

**Dónde verlo:** `results/antes/stress-…/analysis.md` (tabla *Por minuto*) y `timeline.png` (paneles 1–4).

## 2. Evidencia

| Fuente | Qué muestra | Archivo |
|---|---|---|
| Recursos | CPU del contenedor `db` al límite (~100 % = 1 CPU) mientras `api` y `k6` están bajos → cuello de botella en la BD | `resources.csv`, panel 4 de `timeline.png` |
| `pg_stat_statements` | Las consultas de **listado**, sus **conteos** y el conteo de **R5** acumulan ‹≈ 90 %› del tiempo de BD; cada llamada lee ~3 300 bloques (= la tabla completa) aunque devuelve 1–20 filas | `pg_stat_statements.txt` |
| `EXPLAIN (ANALYZE, BUFFERS)` | `Parallel Seq Scan on reservations` en listado por recurso, por cliente, general, sus conteos y el conteo de R5 | `results/antes/explain.txt` (`scripts/explain.sh`) |
| Conexiones | Conexiones activas por encima del tamaño del pool (10): son *workers* paralelos de los Seq Scan | columna `pg_active` de `resources.csv` |
| Latencia por endpoint | disponibilidad (consulta < 10 ms aislada) sube a segundos bajo estrés → espera **en la cola del pool**, no en su propia consulta | `analysis.md`, fase `stress` |

## 3. Hipótesis

La tabla `reservations` (~315 000 filas) solo tiene índices para la clave primaria y la restricción de no traslape
(`resource_id`, rango). Las consultas que filtran por `customer_id`, o por `resource_id` ordenando por `start_at`, no
tienen un índice que coincida con su filtro y orden, así que PostgreSQL recorre la tabla entera en cada llamada.
Con la carga, esas lecturas completas agotan la CPU de la BD; las consultas tardan más, retienen las 10 conexiones
del pool y las demás solicitudes —incluida la disponibilidad— esperan en cola (*head-of-line blocking*).
Al crecer la latencia, k6 necesita tasa × latencia VUs (Ley de Little); al pasar de `maxVUs` aparecen
`dropped_iterations`.

**Predicción verificable:** con índices que coincidan con filtro + orden, (a) los planes pasan a `Index Scan`/
`Index Only Scan` leyendo decenas de bloques, (b) el CPU de la BD baja a la misma tasa, (c) el p95 de carga baja y el
punto de saturación del estrés se desplaza hacia arriba, (d) sin cambiar ninguna regla ni respuesta.

## 4. Corrección (`v2-fix`)

1. `db/migrations/002_indexes.sql`:
   - `(resource_id, start_at DESC, id DESC)` → listado por recurso (filtro + orden + `LIMIT`) y su conteo (*index-only*).
   - `(customer_id, start_at DESC, id DESC)` → listado por cliente con rango de fechas y conteo de R5.
   - `(start_at DESC, id DESC)` → listado general paginado.
2. `src/app.js`, disponibilidad: cota inferior `start_at >= inicio_del_día − 240 min`. Es **equivalente** gracias a R1
   (ninguna reserva dura más de 240 min) y permite usar el índice por rango en lugar de leer todas las reservas del recurso.

No se cambiaron: endpoints, contratos JSON, reglas, pool, límites de contenedores, datos, demanda ni umbrales.

## 5. Verificación

| Verificación | Comando | Resultado esperado |
|---|---|---|
| Regresión funcional | `npm test` · `k6 run k6/smoke.js` | 12/12 · checks 100 % |
| Reglas en toda la base | `invariants.txt` de cada corrida | todas OK |
| Planes | `scripts/explain.sh > results/despues/explain.txt` | Index Scan; ms y bloques mucho menores |
| Rendimiento | 3× carga + 1–2× estrés con `scripts/reset-env.sh` antes de cada una; `scripts/compare.py` | p95/p99 menores, saturación más alta |

## 6. Límites y efectos secundarios (declararlos)

- **Conteo del listado general** (`status=confirmed`, 10 % de los listados) sigue recorriendo ~300 000 filas: un
  conteo exacto sobre casi toda la tabla no se resuelve con un índice. Opciones futuras: total aproximado
  (`pg_class.reltuples`), total en caché, o paginación por cursor sin total. No se aplicó porque cambia el contrato.
- **Costo de escritura:** 3 índices más que mantener por cada `INSERT` → revisar el p95 de `create` antes/después.
- **Espacio:** los índices ocupan espacio adicional (ver tamaño de BD en `env.txt`).
- **Mismo equipo para k6 y servidor:** comparten CPU; por eso se registra `cpu_k6`.
- **Caché del SO no controlada**; la de PostgreSQL se iguala con `reset-env.sh` (reinicio + calentamiento).
- **Datos sintéticos** con distribución uniforme; datos reales podrían concentrarse en pocos recursos o fechas.

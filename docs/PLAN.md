# Plan de pruebas de rendimiento

> Este plan se fija **antes de medir**. El commit que lo contiene (etiqueta `v1-baseline`) es anterior a cualquier
> resultado en `results/`, lo que se puede comprobar con `git log --format='%h %ad %s' --date=iso`.
> Ni la demanda, ni la mezcla, ni los umbrales se modifican después de ver resultados.

## 1. Sistema bajo prueba

| Elemento | Valor |
|---|---|
| API | Node.js 22 + Express 4 + `pg` (pool de 10 conexiones) |
| Base de datos | PostgreSQL 16 con `btree_gist` y `pg_stat_statements` |
| Límites | contenedor `api`: 1 CPU / 512 MiB · contenedor `db`: 1 CPU / 1 GiB (`docker-compose.yml`) |
| Datos | 40 recursos, 5 000 clientes, ~315 000 reservas 2025–2027 (semilla determinística `db/seed.sql`) |
| Generador de carga | k6 en el mismo equipo (fuera de los contenedores); su CPU se registra en `resources.csv` |
| Red | todo en `127.0.0.1`; puertos publicados solo en localhost |

## 2. Demanda esperada

Escenario: sistema de reservas de espacios de un centro universitario (salas, laboratorios, canchas, auditorio).

| Supuesto | Valor | Razón |
|---|---|---|
| Usuarios registrados | 5 000 | igual al volumen de datos sembrado |
| Usuarios activos en la hora pico | 10 % = 500 | inicio de semestre / apertura de reservas |
| Sesión típica | ≈ 15 solicitudes en ~10 min: 9 consultas de disponibilidad, 4 listados, 2 intentos de reserva | navegación de un usuario que busca espacio |
| Tasa pico estimada | 500 × 15 / 600 s ≈ **12,5 req/s** | |
| Demanda de diseño (carga sostenida) | **20 req/s** (≈ +60 % de margen) | tolerar picos dentro de la hora pico |

### Mezcla de tráfico (de la sesión típica)

| Operación | Endpoint | % | Variantes |
|---|---|---|---|
| Consulta de disponibilidad | `GET /resources/:id/availability?date=` | 60 % | recurso y fecha aleatorios dentro de los datos sembrados |
| Listado paginado | `GET /reservations?…` | 25 % | 60 % por recurso (páginas 1–5), 30 % por cliente en un año, 10 % listado general (páginas 1–50, 50 por página) |
| Creación de reserva | `POST /reservations` | 15 % | año 2028 (vacío en la semilla), duración 30–120 min; 409/422 son respuestas válidas de negocio |

La secuencia aleatoria usa semilla fija por VU (`SEED=42`), así que dos corridas generan las mismas solicitudes.

## 3. Escenarios

| Escenario | Script | Ejecutor | Perfil | Duración | Propósito |
|---|---|---|---|---|---|
| Humo | `k6/smoke.js` | `vus: 1` | 1 iteración/s de las 3 operaciones + reglas R1–R5 de punta a punta | 1 min | Validar funcionamiento y reglas antes de cargar. Si falla, no se continúa. |
| Carga sostenida | `k6/load.js` | `ramping-arrival-rate` → `constant-arrival-rate` | rampa 0→20 req/s en 1 min, luego **20 req/s × 10 min** | 11 min | Verificar que la demanda de diseño se atiende dentro de los umbrales. |
| Estrés progresivo + recuperación | `k6/stress.js` | `ramping-arrival-rate` + `constant-arrival-rate` | escalones 20 → 40 → 60 → 80 → 100 req/s (1 min subida + 2 min meseta cada uno), luego **10 req/s × 3 min** | ≈ 18,5 min | Ubicar el punto de saturación y observar si el sistema vuelve a la normalidad. |
| Recuperación posterior | `k6/recovery.js` | `constant-arrival-rate` | 10 req/s × 3 min | 3 min | Solo si el estrés se detuvo por seguridad: verificar recuperación con una prueba segura. |

**¿Por qué modelo abierto (arrival-rate)?** Los usuarios reales no esperan a que el servidor responda para llegar.
Con VUs fijos (modelo cerrado), un servidor lento reduce la carga que recibe y oculta el problema.
Con tasa de llegada, si el servidor se vuelve lento k6 necesita más VUs; al agotar `maxVUs` registra
`dropped_iterations`.

**¿Por qué 100 req/s como tope?** Es 5× la demanda de diseño y, con los límites de 1 CPU por contenedor, se espera
que el sistema sature antes. Si en tu equipo no satura, se declara: *"no se alcanzó saturación dentro del límite seguro
de 100 req/s"* (no se sube el tope sin documentarlo como una corrida nueva).

## 4. Umbrales de aprobación (carga sostenida, fase `steady`)

| Métrica | Umbral | Justificación |
|---|---|---|
| `http_req_failed` | < 1 % | Errores 5xx/timeout. 409 y 422 **no** son fallas: son el sistema aplicando R4/R5 (`expectedStatuses`). |
| `checks` | > 99 % | Respuestas funcionalmente correctas (24 bloques, paginación coherente, etc.). |
| p95 disponibilidad | < 300 ms | Operación interactiva y la más frecuente; 300 ms en servidor deja margen a la red para no superar ~1 s percibido. |
| p99 disponibilidad | < 800 ms | Limita la cola larga. |
| p95 / p99 listado | < 500 / 1000 ms | Consulta más pesada (filtros + total); el usuario tolera hasta ~1 s. |
| p95 / p99 creación | < 500 / 1000 ms | Escritura transaccional con bloqueo por cliente. |
| `dropped_iterations` | < 1 % de lo planificado (120 de 12 000) | Si se pierden iteraciones, la carga ofrecida no se aplicó completa. |

## 5. Límites de seguridad y criterios de detención

| Límite | Valor | Implementación |
|---|---|---|
| Recursos de la API y la BD | 1 CPU y 512 MiB / 1 GiB | `deploy.resources.limits` |
| VUs máximos | 100 (carga) / 300 (estrés) | `maxVUs` (también limita el consumo del generador) |
| Errores en estrés | ≥ 10 % → **abortar** | `abortOnFail`, evaluación tras 1 min |
| Latencia en estrés | p95 ≥ 5 s → **abortar** | `abortOnFail`, evaluación tras 1 min |
| Errores en carga normal | ≥ 20 % → abortar | protege el equipo si algo está roto |
| Detención manual | CPU del host > 90 % sostenido > 1 min, uso de swap, o k6 con CPU ≥ 90 % de un núcleo | se documenta en el informe con la hora |
| Alcance | solo `localhost` en equipo propio | nunca Canvas ni servicios públicos |

**Si el estrés se detiene por seguridad:** la fase de recuperación no corre. Se documenta (hora, umbral, valor) y de
inmediato se ejecuta `scripts/run-test.sh recovery <etiqueta>`.

## 6. Criterios de lectura del estrés

- **Saturación:** primer escalón donde ocurra cualquiera de: p95 de algún endpoint supera su umbral de carga,
  `req/s logradas` < 95 % de `ofrecidas`, o errores > 1 %. Se lee en la tabla *Por minuto* de `analysis.md`.
- **Capacidad sostenible:** el escalón anterior al de saturación.
- **Recuperación:** en la fase `recovery`, p95 < 300 ms y errores < 1 %. Además, en `timeline.png` se mide cuántos
  segundos tarda el p95 en volver bajo el umbral (cola acumulada que se drena).
- **`dropped_iterations`:** no se atribuye automáticamente al servidor. Se contrasta con:
  CPU de k6 (`cpu_k6` en `resources.csv`), VUs activos vs `maxVUs`, y latencia. Si k6 está cerca de 100 % de CPU o
  los VUs no llegan a `maxVUs`, la causa es el generador; si los VUs están en `maxVUs` *porque* la latencia subió,
  es consecuencia de la lentitud del servidor (Ley de Little: VUs necesarios ≈ tasa × latencia).

## 7. Reglas de negocio durante las pruebas

Después de **cada** corrida, `scripts/verify-invariants.js` revisa toda la base (sembrado + creado por k6):
R1 duración, R2 horario/mismo día, R4 sin traslapes, R5 máximo 2 por cliente y día. El resultado se guarda en
`invariants.txt`. Una corrida con reglas rotas se invalida.

## 8. Condiciones equivalentes antes/después

Igual hardware, mismos límites de contenedores, misma versión de k6/PostgreSQL/Node, mismo volumen de datos
(restablecido), misma semilla, misma demanda y mismos umbrales. Antes de cada corrida: `scripts/reset-env.sh`
(restablece datos, reinicia contenedores y calienta con humo). Equipo enchufado a corriente, sin otras aplicaciones
pesadas abiertas.

**Repeticiones:** 3 corridas de carga y 1–2 de estrés por lado. Si el coeficiente de variación del p95 entre corridas
supera 15 %, se repite y se explica la variación. Lo único que cambia entre antes y después es el commit del código.

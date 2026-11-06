# API de Reservas — pruebas de carga y estrés con k6

API REST de reservas de espacios (salas, laboratorios, canchas, auditorio) sobre PostgreSQL, con datos ficticios
reproducibles y una batería k6 de humo, carga sostenida, estrés progresivo y recuperación.

**Autor:** Andy Daniel Rojop Orozco · Ingeniería en Sistemas, UMG Retalhuleu

| Documento | Contenido |
|---|---|
| [`docs/GUIA.md`](docs/GUIA.md) | **Paso a paso**: instalar, medir antes/después (`scripts/run-all.sh`), generar el PDF (`scripts/build-report.py`) y grabar el video |
| [`docs/PLAN.md`](docs/PLAN.md) | Demanda, mezcla de tráfico, escenarios, umbrales y límites de seguridad (fijados antes de medir) |
| [`docs/DECISIONES.md`](docs/DECISIONES.md) | Decisiones técnicas y alternativas descartadas |
| [`docs/HALLAZGO.md`](docs/HALLAZGO.md) | Hallazgo, evidencia, hipótesis, corrección, verificación y límites |
| [`results/`](results/) | Resultados ORIGINALES de cada corrida (ver *Ubicación de resultados*) |

---

## 1. API

| Método | Ruta | Descripción | Códigos |
|---|---|---|---|
| GET | `/health` | Estado y versión | 200 |
| GET | `/resources` | Lista de recursos | 200 |
| GET | `/resources/:id/availability?date=YYYY-MM-DD` | Disponibilidad del día en bloques de 30 min | 200, 400, 404 |
| POST | `/reservations` | Crea una reserva | 201, 400, 404, **409**, **422** |
| GET | `/reservations?page=&page_size=&resource_id=&customer_id=&status=&from=&to=` | Listado paginado (máx. 100 por página) con `total` y `total_pages` | 200, 400 |

```bash
curl "localhost:3000/resources/5/availability?date=2026-05-04"
curl -X POST localhost:3000/reservations -H 'Content-Type: application/json' \
     -d '{"resource_id":5,"customer_id":12,"start_at":"2028-03-01T10:00:00-06:00","duration_min":60}'
curl "localhost:3000/reservations?resource_id=5&page=2&page_size=20"
```

### Reglas de negocio (se conservan en todas las pruebas)

| Regla | Descripción | Dónde se garantiza | Respuesta |
|---|---|---|---|
| R1 | Duración 30–240 min, múltiplos de 30 | `src/rules.js` | 422 |
| R2 | Dentro del horario del recurso (8:00–20:00 Guatemala), mismo día, inicio en bloque de 30 min | `src/rules.js` | 422 |
| R3 | No reservar en el pasado | `src/rules.js` | 422 |
| R4 | Sin traslapes por recurso | restricción `EXCLUDE` en PostgreSQL | 409 |
| R5 | Máx. 2 reservas confirmadas por cliente por día | transacción + advisory lock | 422 |

`scripts/verify-invariants.js` revisa R1, R2, R4 y R5 sobre **toda** la base después de cada prueba.

---

## 2. Requisitos

| Herramienta | Versión usada | Instalación |
|---|---|---|
| Docker + Docker Compose v2 | Docker Desktop 4.x | https://docs.docker.com/get-docker/ |
| k6 | v1.3.0 | https://grafana.com/docs/k6/latest/set-up/install-k6/ |
| Bash | — | Linux/macOS, o **WSL2 (Ubuntu)** en Windows: los scripts usan `/proc` para medir CPU |
| Python 3 (análisis) | 3.10+ | `pip install -r requirements.txt` |
| Node.js (solo sin Docker) | 22 | https://nodejs.org |

> En Windows: abrir Ubuntu (WSL2), clonar el repo **dentro** de WSL (`~/`), activar en Docker Desktop
> *Settings → Resources → WSL integration*, e instalar k6 en Ubuntu (`sudo apt install k6` según la guía oficial).

## 3. Instalar, configurar e iniciar

```bash
git clone <URL-del-repositorio> api-reservas-k6 && cd api-reservas-k6
docker compose up -d --build                         # PostgreSQL 16 + API (con límites de CPU/RAM)
docker compose exec api node scripts/db-reset.js     # esquema + datos ficticios (~20–60 s)
curl localhost:3000/health                           # {"status":"ok",...}
```

**Configuración** (variables en `docker-compose.yml`):

| Variable | Defecto | Uso |
|---|---|---|
| `DATABASE_URL` | `postgres://reservas:reservas@db:5432/reservas` | conexión |
| `PG_POOL_MAX` | `10` | tamaño del pool de conexiones |
| `PORT` | `3000` | puerto HTTP |
| límites `cpus` / `memory` | api 1 CPU/512 MiB · db 1 CPU/1 GiB | **no cambiar entre antes y después** |

**Sin Docker** (PostgreSQL 16 local con `btree_gist` y `shared_preload_libraries='pg_stat_statements'`):
```bash
npm ci
export DATABASE_URL=postgres://reservas:reservas@localhost:5432/reservas
npm run db:reset && npm start
```

## 4. Restablecer la aplicación y sus datos

| Necesidad | Comando |
|---|---|
| Restablecer solo los datos (mismo contenido exacto cada vez) | `docker compose exec api node scripts/db-reset.js` |
| Dejar el entorno listo para medir (datos + reinicio + calentamiento con humo) | `scripts/reset-env.sh` |
| Verificar reglas de negocio en toda la base | `docker compose exec api node scripts/verify-invariants.js` |
| Borrar todo (contenedores y volumen) | `docker compose down -v` |

Datos sembrados: 40 recursos, 5 000 clientes, 315 366 reservas (2025-01-01 a 2027-12-31). El año **2028 queda vacío**:
ahí escriben las pruebas, así que lo sembrado nunca se altera.

## 5. Pruebas funcionales (regresión)

```bash
npm ci && npm test        # unitarias de reglas + API real (R1–R5, concurrencia de R5, paginación)
k6 run k6/smoke.js        # humo k6: también valida R1, R3, R4, R5 de punta a punta
```

## 6. Pruebas de rendimiento

**Todo junto y desatendido (recomendado):** `scripts/run-all.sh antes` en `v1-baseline` y `scripts/run-all.sh despues`
en `v2-fix` (~60 min cada uno). Luego `scripts/build-report.py` genera el informe (ver `docs/GUIA.md`).

Paso a paso manual: antes de **cada** corrida, `scripts/reset-env.sh`. Cada corrida guarda su evidencia en `results/<etiqueta>/<escenario>-<fecha>/`.

```bash
scripts/reset-env.sh && scripts/run-test.sh smoke  antes
scripts/reset-env.sh && scripts/run-test.sh load   antes        # repetir 3 veces
scripts/reset-env.sh && scripts/run-test.sh stress antes        # PEAK=100 por defecto
# si el estrés se detuvo por límite de seguridad (el script lo avisa):
scripts/run-test.sh recovery antes
```

Para comparar (después de aplicar la corrección y repetir lo mismo con la etiqueta `despues`):
```bash
python3 scripts/compare.py --antes results/antes/load-* --despues results/despues/load-* \
        --fase steady --salida results/comparacion-load
python3 scripts/compare.py --antes results/antes/stress-* --despues results/despues/stress-* \
        --fase stress --salida results/comparacion-stress
```

### Ubicación de resultados originales

```
results/<antes|despues>/<escenario>-<AAAAMMDD-HHMMSS>/
  env.txt                 hardware, versiones, límites, volumen de datos, índices, caché, commit
  k6-stdout.log           salida completa de k6 (incluye avisos de aborto)
  summary.json / .txt     resumen de k6 (handleSummary)
  raw.csv.gz              CADA muestra de cada métrica (datos originales)
  resources.csv           CPU/RAM de api, db y k6 + conexiones activas, cada 2 s
  pg_stat_statements.txt  consultas que más tiempo consumieron
  invariants.txt          verificación de reglas de negocio tras la corrida
  exit_code.txt           0 = umbrales OK · 99 = umbral incumplido/abortado
  analysis.md, timeline.png, timeline.csv   generados por scripts/analyze.py a partir de lo anterior
```

## 7. Versiones del código

| Etiqueta | Contenido |
|---|---|
| `v1-baseline` | Aplicación, plan y scripts **antes** de medir |
| `v2-fix` | Corrección aplicada (ver `docs/HALLAZGO.md`) |

```bash
git checkout v1-baseline && docker compose up -d --build   # medir "antes"
git checkout v2-fix      && docker compose up -d --build   # medir "después"
```
`env.txt` registra el commit y los índices presentes en cada corrida.

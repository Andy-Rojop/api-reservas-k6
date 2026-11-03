# Decisiones técnicas

| Decisión | Elección | Por qué | Alternativa descartada |
|---|---|---|---|
| Lenguaje / framework | Node.js 22 + Express 4 | API pequeña, E/S intensiva hacia la BD; modelo de un solo hilo hace visibles los cuellos de botella de la BD y del pool | Spring Boot (más memoria y arranque más lento para un contenedor de 512 MiB) |
| Driver | `pg` con `Pool` (max 10) | consultas parametrizadas (sin inyección SQL), pool configurable por variable `PG_POOL_MAX` | ORM: oculta el SQL que se necesita analizar con `EXPLAIN` |
| Regla de no traslape (R4) | restricción `EXCLUDE USING gist` en PostgreSQL | la garantiza la BD incluso con solicitudes concurrentes; un `SELECT` previo tendría condición de carrera | validar en la aplicación |
| Límite diario por cliente (R5) | transacción + `pg_advisory_xact_lock(1, customer_id)` | serializa solo las solicitudes del mismo cliente; probado con 6 solicitudes simultáneas (`test/api.test.js`) | `SERIALIZABLE` (reintentos por fallos de serialización bajo carga) |
| Zona horaria | `TIMESTAMPTZ` en BD; reglas en hora de Guatemala (UTC-6 fija, sin horario de verano) | fechas inequívocas; `start_at` exige zona en ISO 8601 | guardar hora local sin zona |
| Respuestas de negocio | 409 traslape, 422 regla, 400 formato, 404 inexistente | k6 las declara esperadas (`expectedStatuses`) para no confundirlas con fallas del servidor | contar 409 como error (inflaría la tasa de error) |
| Paginación | `page` + `page_size` (máx. 100) con `total` y `total_pages` | requisito de listado paginado con total para la interfaz | cursor/keyset (no da total ni salto a página N) |
| Datos ficticios | SQL determinístico sin `random()` | mismo contenido exacto en cada `db:reset`; 2028 vacío para escrituras de prueba | datos aleatorios (no reproducibles) |
| Contenedores | Docker Compose con `cpus` y `memory` fijos | condiciones equivalentes entre corridas y protección del equipo | procesos sin límite (resultado depende de qué más corre en la PC) |
| Evidencia de BD | `pg_stat_statements` precargado | identifica qué consulta consume el tiempo, sin adivinar | solo latencia de k6 (dice *qué* endpoint, no *por qué*) |

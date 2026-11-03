# Plantilla del informe PDF (completar con TUS mediciones)

> Todo número del informe debe salir de un archivo en `results/`. Citá la carpeta junto a cada tabla o captura.

## Portada
- Nombre: Andy Daniel Rojop Orozco · Carné: `____________`
- Curso / catedrático / fecha
- Repositorio: `https://github.com/<usuario>/api-reservas-k6` (público o con acceso para el catedrático)
- Video (≤ 3 min): `https://…` (YouTube no listado / Drive con "cualquiera con el enlace")

## 1. Descripción de la API (½ página)
Qué hace, endpoints (tabla del README §1), reglas R1–R5, stack y decisiones (resumen de `docs/DECISIONES.md`).

## 2. Entorno y reproducibilidad
Copiar de `env.txt` de una corrida: CPU, núcleos, RAM, SO, versiones (Docker, PostgreSQL, Node, k6), límites de
contenedores, volumen de datos, índices presentes, estado de caché (procedimiento `reset-env.sh`), commit.
Comandos de instalación/reset (README §3–4).

## 3. Plan de pruebas
Resumen de `docs/PLAN.md`: demanda (cálculo 12,5 → 20 req/s), mezcla 60/25/15, tabla de escenarios,
tabla de umbrales con justificación, límites de seguridad y criterio de detención.
Mencionar que el plan está en el commit `v1-baseline`, anterior a los resultados.

## 4. Resultados ANTES
- **Humo:** captura del resumen k6 (checks 100 %, reglas OK). Carpeta: `results/antes/smoke-…`
- **Carga:** tabla de `compare.md` (lado "antes") + `timeline.png` de una corrida. ¿Pasó los umbrales? ¿Qué endpoint
  está más cerca del límite? CPU de api/db/k6 (`analysis.md` → Recursos).
- **Estrés:** tabla *Por minuto* de `analysis.md` y `timeline.png`. Identificar: escalón de saturación, capacidad
  sostenible, qué recurso se agotó primero (CPU db vs api vs pool), `dropped_iterations` y su causa
  (CPU de k6 y VUs vs maxVUs — ver PLAN §6). ¿Abortó? Si sí: hora, umbral, valor, y resultado de `recovery`.
- **Recuperación:** p95 y errores en fase `recovery`; segundos hasta volver bajo el umbral.
- **Invariantes:** `invariants.txt` → reglas conservadas.

## 5. Hallazgo (contenido de `docs/HALLAZGO.md`)
Problema → evidencia (latencia por endpoint + `pg_stat_statements.txt` + `EXPLAIN (ANALYZE, BUFFERS)` antes) →
hipótesis → corrección (diff) → regresión funcional (`npm test`, humo, invariantes) → `EXPLAIN` después.

## 6. Resultados DESPUÉS y comparación
`compare.png` y `compare.md` de carga (fase `steady`) y estrés (fase `stress`), con media ± desviación estándar entre
repeticiones. Explicar: cuánto mejoró y por qué; variación entre corridas (CV %); cualquier regresión
(p. ej. costo de escritura por mantener índices) y límites (mismo equipo para cliente y servidor, caché del SO no
controlada, datos sintéticos, etc.).

## 7. Conclusiones (5–8 viñetas)

## Guion sugerido del video (≤ 3 min)
| Tiempo | Qué mostrar |
|---|---|
| 0:00–0:30 | `docker compose up`, `curl` a disponibilidad, crear reserva (201) y repetirla (409) |
| 0:30–1:30 | Explicar `k6/stress.js`: escalones, abortOnFail, fase de recuperación; correr unos segundos y mostrar `timeline.png` de la corrida completa |
| 1:30–2:30 | Evidencia del hallazgo (`pg_stat_statements` / `EXPLAIN` con Seq Scan) → la corrección → `compare.png` |
| 2:30–3:00 | Invariantes OK y conclusión en una frase |

-- 002_indexes.sql — CORRECCIÓN (v2-fix), respaldada por la evidencia en docs/HALLAZGO.md
-- Índices que coinciden con los filtros y el orden reales de las consultas:

-- Listado por recurso: WHERE resource_id = ? ORDER BY start_at DESC, id DESC LIMIT/OFFSET
CREATE INDEX reservations_resource_start_idx ON reservations (resource_id, start_at DESC, id DESC);

-- Listado por cliente y rango de fechas + conteo de R5 (WHERE customer_id = ? AND start_at en un día)
CREATE INDEX reservations_customer_start_idx ON reservations (customer_id, start_at DESC, id DESC);

-- Listado general paginado: ORDER BY start_at DESC, id DESC
CREATE INDEX reservations_start_idx ON reservations (start_at DESC, id DESC);

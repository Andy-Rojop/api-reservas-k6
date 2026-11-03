-- seed.sql — datos ficticios REPRODUCIBLES (sin random(): todo sale de fórmulas determinísticas)
-- Volumen: 40 recursos, 5 000 clientes, reservas 2025-01-01 .. 2027-12-31 (~315 000 filas).
-- El año 2028 queda VACÍO a propósito: ahí crean reservas las pruebas k6.
-- Todas las reservas sembradas cumplen R1..R5 (se verifica con scripts/verify-invariants.js).

INSERT INTO resources (name, type, capacity, open_hour, close_hour)
SELECT format('%s %s', initcap(t.type), lpad(g::text, 2, '0')),
       t.type,
       (ARRAY[6, 12, 20, 40, 120])[1 + (g % 5)],
       8, 20
FROM generate_series(1, 40) AS g
CROSS JOIN LATERAL (
  SELECT (ARRAY['sala', 'laboratorio', 'cancha', 'auditorio'])[1 + (g % 4)] AS type
) t;

INSERT INTO customers (name, email)
SELECT format('Cliente %s', g), format('cliente%s@example.test', g)
FROM generate_series(1, 5000) AS g;

-- Una reserva de 60 min en ~60 % de los bloques horarios (8:00–20:00, hora de Guatemala).
-- Cliente asignado por fórmula: como máximo 1 reserva por cliente por día (R5 permite 2).
WITH slots AS (
  SELECT r.id AS resource_id,
         d::date AS day,
         h AS hour,
         (d::date - DATE '2025-01-01') AS day_idx
  FROM resources r
  CROSS JOIN generate_series(DATE '2025-01-01', DATE '2027-12-31', INTERVAL '1 day') AS d
  CROSS JOIN generate_series(8, 19) AS h
  WHERE ((r.id * 7919 + (d::date - DATE '2025-01-01') * 104729 + h * 1299709) % 100) < 60
),
numbered AS (
  SELECT s.*, row_number() OVER (PARTITION BY s.day ORDER BY s.resource_id, s.hour) AS rn
  FROM slots s
)
INSERT INTO reservations (resource_id, customer_id, start_at, end_at, status, created_at)
SELECT resource_id,
       ((rn + day_idx * 97) % 5000) + 1,
       (day + make_interval(hours => hour)) AT TIME ZONE 'America/Guatemala',
       (day + make_interval(hours => hour + 1)) AT TIME ZONE 'America/Guatemala',
       CASE WHEN (rn % 17) = 0 THEN 'cancelled' ELSE 'confirmed' END,
       ((day - 14) + TIME '09:00') AT TIME ZONE 'America/Guatemala'
FROM numbered;

ANALYZE;

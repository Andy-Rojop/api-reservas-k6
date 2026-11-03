-- 001_schema.sql — esquema base de la API de reservas
-- Regla R4 (sin traslapes) se garantiza en la base de datos con una restricción de exclusión.

CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE TABLE resources (
  id          SERIAL PRIMARY KEY,
  name        TEXT        NOT NULL UNIQUE,
  type        TEXT        NOT NULL CHECK (type IN ('sala', 'laboratorio', 'cancha', 'auditorio')),
  capacity    INT         NOT NULL CHECK (capacity > 0),
  open_hour   SMALLINT    NOT NULL DEFAULT 8  CHECK (open_hour BETWEEN 0 AND 23),
  close_hour  SMALLINT    NOT NULL DEFAULT 20 CHECK (close_hour BETWEEN 1 AND 24),
  CHECK (close_hour > open_hour)
);

CREATE TABLE customers (
  id     SERIAL PRIMARY KEY,
  name   TEXT NOT NULL,
  email  TEXT NOT NULL UNIQUE
);

CREATE TABLE reservations (
  id           BIGSERIAL   PRIMARY KEY,
  resource_id  INT         NOT NULL REFERENCES resources(id),
  customer_id  INT         NOT NULL REFERENCES customers(id),
  start_at     TIMESTAMPTZ NOT NULL,
  end_at       TIMESTAMPTZ NOT NULL,
  status       TEXT        NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled')),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (end_at > start_at),
  -- R4: dos reservas confirmadas del mismo recurso no pueden traslaparse
  CONSTRAINT no_overlap EXCLUDE USING gist (
    resource_id WITH =,
    tstzrange(start_at, end_at, '[)') WITH &&
  ) WHERE (status = 'confirmed')
);

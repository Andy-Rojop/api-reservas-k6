const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgres://reservas:reservas@localhost:5432/reservas',
  max: Number(process.env.PG_POOL_MAX || 10),
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: Number(process.env.PG_CONN_TIMEOUT_MS || 5_000),
  statement_timeout: Number(process.env.PG_STATEMENT_TIMEOUT_MS || 10_000),
});

pool.on('error', (err) => console.error('[pg] error en cliente inactivo:', err.message));

module.exports = { pool };

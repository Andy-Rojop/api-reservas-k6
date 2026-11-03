#!/usr/bin/env node
// Restablece la base: borra el esquema, aplica TODAS las migraciones en orden y siembra los datos.
// Uso: npm run db:reset   (usa DATABASE_URL)
const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

(async () => {
  const url = process.env.DATABASE_URL || 'postgres://reservas:reservas@localhost:5432/reservas';
  const client = new Client({ connectionString: url });
  await client.connect();
  const t0 = Date.now();
  try {
    console.log('[reset] eliminando esquema public…');
    await client.query('DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;');

    const dir = path.join(__dirname, '..', 'db', 'migrations');
    const files = fs.readdirSync(dir).filter((f) => f.endsWith('.sql')).sort();
    for (const f of files) {
      console.log(`[reset] migración ${f}`);
      await client.query(fs.readFileSync(path.join(dir, f), 'utf8'));
    }

    console.log('[reset] sembrando datos (puede tardar ~30-90 s)…');
    await client.query(fs.readFileSync(path.join(__dirname, '..', 'db', 'seed.sql'), 'utf8'));
    // Estadísticas y mapa de visibilidad al día: el planificador parte del mismo estado en cada reset
    await client.query('VACUUM (ANALYZE) resources, customers, reservations');
    // Reiniciar estadísticas para que cada corrida empiece con contadores limpios
    await client.query('SELECT pg_stat_statements_reset()').catch(() =>
      console.warn('[reset] pg_stat_statements no está precargado; se omite su reinicio'));

    const { rows } = await client.query(`
      SELECT (SELECT count(*) FROM resources)    AS resources,
             (SELECT count(*) FROM customers)    AS customers,
             (SELECT count(*) FROM reservations) AS reservations,
             (SELECT count(*) FROM reservations WHERE status='confirmed') AS confirmed`);
    console.log('[reset] listo en', ((Date.now() - t0) / 1000).toFixed(1), 's →', rows[0]);
    console.log('[reset] migraciones aplicadas:', files.join(', '));
  } finally {
    await client.end();
  }
})().catch((e) => { console.error('[reset] ERROR:', e.message); process.exit(1); });

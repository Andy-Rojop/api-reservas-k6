const { app } = require('./app');
const { pool } = require('./db');

const port = Number(process.env.PORT || 3000);
const server = app.listen(port, () => {
  console.log(`[api] escuchando en :${port} (pool=${process.env.PG_POOL_MAX || 10})`);
});
server.keepAliveTimeout = 65_000;

function shutdown(sig) {
  console.log(`[api] ${sig}: cerrando…`);
  server.close(() => pool.end().then(() => process.exit(0)));
  setTimeout(() => process.exit(1), 10_000).unref();
}
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

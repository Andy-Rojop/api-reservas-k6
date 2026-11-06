# Guía de entrega paso a paso (Windows + WSL2)

Tiempo total aproximado: 30 min de preparación + **~2 h de mediciones desatendidas** + 30 min de informe y video.

## 0. Preparar el equipo (una sola vez)

1. **WSL2 con Ubuntu.** En PowerShell como administrador: `wsl --install -d Ubuntu-24.04`, reiniciar y crear usuario.
2. **Docker Desktop**: instalar desde https://docs.docker.com/desktop/setup/install/windows-install/ → *Settings →
   Resources → WSL integration* → activar *Ubuntu-24.04*. Comprobar en Ubuntu: `docker run --rm hello-world`.
3. **En Ubuntu (WSL)**, herramientas:
   ```bash
   sudo apt update && sudo apt install -y git curl unzip python3-pandas python3-matplotlib python3-tabulate
   curl -L https://github.com/grafana/k6/releases/download/v1.3.0/k6-v1.3.0-linux-amd64.tar.gz | tar xz
   sudo mv k6-v1.3.0-linux-amd64/k6 /usr/local/bin/ && k6 version          # k6 v1.3.0
   ```
4. **Recursos de Docker Desktop**: dejá al menos 4 CPU y 4 GB de RAM para WSL (*Settings → Resources*). Los contenedores
   igual quedan limitados a 1 CPU cada uno por `docker-compose.yml`.

## 1. Subir el repositorio a GitHub

Trabajá **dentro de WSL** (`~/`), no en `/mnt/c/...` (es mucho más lento y altera las mediciones).
```bash
cd ~ && unzip /mnt/c/Users/<TU_USUARIO_WINDOWS>/Downloads/api-reservas-k6.zip && cd api-reservas-k6
git log --oneline --decorate          # debe mostrar las etiquetas v1-baseline y v2-fix
```
En github.com → *New repository* → `api-reservas-k6`, **público**, sin README. Luego:
```bash
git remote add origin https://github.com/<tu-usuario>/api-reservas-k6.git
git push -u origin main --tags        # --tags es obligatorio: el catedrático necesita v1-baseline y v2-fix
```
(GitHub pide un *Personal access token* en lugar de contraseña: *Settings → Developer settings → Tokens (classic)*, permiso `repo`.)

## 2. Levantar la aplicación y verla funcionar

```bash
git checkout v1-baseline
docker compose up -d --build
docker compose exec api node scripts/db-reset.js            # ~30-60 s, siembra 315 366 reservas
curl "localhost:3000/resources/5/availability?date=2026-05-04"
curl -X POST localhost:3000/reservations -H 'Content-Type: application/json' \
     -d '{"resource_id":5,"customer_id":12,"start_at":"2028-03-01T10:00:00-06:00","duration_min":60}'   # 201
# repetir el mismo POST → 409 (traslape, regla R4)
curl "localhost:3000/reservations?resource_id=5&page=2&page_size=5"
```

## 3. Medir ANTES (~60 min, desatendido)

Cerrá navegadores pesados, juegos, etc. Dejá la laptop **conectada a corriente** y que no se suspenda
(*Configuración → Energía → Nunca*).
```bash
git checkout v1-baseline
scripts/run-all.sh antes
```
El script hace: build → reset → EXPLAIN → regresión funcional → humo → 3 corridas de carga → estrés (+ recuperación si se
detiene por seguridad). Antes de cada medición restablece datos y caché. Si algo falla, se detiene y dice por qué.

**Mientras corre el estrés**, tomá una captura del Administrador de tareas (CPU/RAM del equipo) para el informe, y
vigilá que el equipo no pase de 90 % de CPU sostenido. Si lo hace, detené con `Ctrl+C`, anotá la hora y el motivo, y
ejecutá `scripts/run-test.sh recovery antes` (el plan lo exige).

## 4. Medir DESPUÉS (~60 min)

```bash
git checkout v2-fix
scripts/run-all.sh despues
```
Mismo equipo, mismas condiciones (corriente, apps cerradas). No cambiés ningún número.

## 5. Guardar los resultados en el repositorio

```bash
git checkout main
git add results/antes results/despues
git commit -m "Resultados originales antes y después"
git push
```
Los resultados no se pierden al cambiar de etiqueta: son archivos nuevos que git todavía no rastrea.

## 6. Generar el informe PDF

```bash
python3 scripts/build-report.py --nombre "Andy Daniel Rojop Orozco" --carne "<TU CARNÉ>" \
   --repo https://github.com/<tu-usuario>/api-reservas-k6 --video "<enlace del video>" \
   --curso "<nombre del curso>" --catedratico "<nombre del catedrático>"
explorer.exe "$(wslpath -w informe/informe.html)"
```
En Chrome o Edge: **Ctrl+P → Guardar como PDF → Tamaño A4 → Más opciones → activar "Gráficos de fondo"** → Guardar.

El generador calcula todo desde `results/`: umbrales cumplidos, variación entre corridas, punto de saturación,
interpretación de `dropped_iterations`, recuperación, comparación y regresiones. **Leelo completo antes de entregar**: si
algo no coincide con lo que viste (p. ej. detuviste a mano), editá `informe/informe.html` con cualquier editor de texto
y volvé a imprimir. Agregá la captura del Administrador de tareas si la tomaste.

Hacé commit también de `informe/` y de `results/comparacion-*` para que todo quede en el repo.

## 7. Video (máx. 3 min)

Grabá con **Win + Alt + R** (Xbox Game Bar) o OBS. Guion:

| Tiempo | Qué mostrar y decir |
|---|---|
| 0:00–0:30 | `docker compose ps` (contenedores con límites) · `curl` de disponibilidad · POST → 201 · mismo POST → 409 |
| 0:30–1:30 | Abrí `k6/stress.js`: escalones 20→100 req/s, `abortOnFail` (seguridad), fase de recuperación a 10 req/s. Corré `k6 run k6/smoke.js` unos segundos para mostrar k6 en vivo. Mostrá `timeline.png` del estrés ANTES: CPU de la BD al 100 %, latencia que sube, dropped. |
| 1:30–2:30 | `results/antes/explain.txt` (Seq Scan) → `db/migrations/002_indexes.sql` → `results/despues/explain.txt` (Index Scan) → `results/comparacion-stress/compare.png` |
| 2:30–3:00 | Invariantes OK en ambas versiones y una frase de conclusión con tus números |

Subilo a YouTube como **"No listado"** (o a Google Drive con *"Cualquier persona con el enlace"*) y probá el enlace en
una ventana de incógnito. Después regenerá el informe con el enlace real del video.

## 8. Lista de verificación antes de entregar

- [ ] Repo público, con `git push --tags` (se ven `v1-baseline` y `v2-fix` en GitHub → *Tags*)
- [ ] `results/antes` y `results/despues` subidos (con `raw.csv.gz`)
- [ ] PDF con nombre, carné, enlace del repo y del video funcionando en incógnito
- [ ] Revisaste que el texto del informe coincide con lo que pasó en tus corridas
- [ ] Video ≤ 3:00

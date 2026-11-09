#!/usr/bin/env python3
"""Genera el informe de entrega a partir de los resultados ORIGINALES en results/antes y results/despues.

Uso:
  python3 scripts/build-report.py --nombre "Andy Daniel Rojop Orozco" --carne "0000-00-00000" \
      --repo https://github.com/usuario/api-reservas-k6 --video https://youtu.be/xxxx \
      [--curso "Aseguramiento de la Calidad del Software"] [--catedratico "Ing. ..."]

Salida: informe/informe.html (+ informe/informe.pdf si Python tiene Playwright).
Todas las cifras se calculan de raw.csv.gz, summary.json, resources.csv, timeline.csv, explain.txt y
pg_stat_statements.txt. El texto interpretativo se genera desde esos datos: revisalo y ajustalo antes de entregar.
"""
import argparse
import base64
import html
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import load_raw, phase_table  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
THR = {"availability": 300, "list": 500, "create": 500}
EP_ES = {"(todos)": "todos", "availability": "disponibilidad", "list": "listado", "create": "creación"}
E = html.escape


# ───────────────────────────────────────────── utilidades
def runs(label, scen):
    d = RES / label
    return sorted(p for p in d.glob(f"{scen}-*") if (p / "raw.csv.gz").exists()) if d.exists() else []


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT))


def ms(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v:,.1f}" if v < 100 else f"{v:,.0f}"


def pct(v, d=1):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:+.{d}f} %"


def img(path, alt, caption):
    p = Path(path)
    if not p.exists():
        return f'<p class="warn">Falta la imagen {E(rel(p) if p.is_absolute() else str(p))}</p>'
    b64 = base64.b64encode(p.read_bytes()).decode()
    return (f'<figure><img src="data:image/png;base64,{b64}" alt="{E(alt)}">'
            f'<figcaption>{caption}<br><span class="src">Archivo original: <code>{E(rel(p))}</code></span></figcaption></figure>')


def table(df, cls=""):
    return df.to_html(index=False, escape=True, classes=cls, border=0, na_rep="—")


def pre(text, cls=""):
    return f'<pre class="{cls}">{E(text)}</pre>'


def read(p, default=""):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return default


def thresholds(run):
    s = json.loads(read(run / "summary.json", "{}") or "{}")
    out = []
    for name, m in s.get("metrics", {}).items():
        for expr, r in (m.get("thresholds") or {}).items():
            if "100000" in expr or ">=0" in expr:
                continue  # umbrales informativos del estrés
            out.append((name, expr, r.get("ok")))
    return out


def k6_screen(run):
    """Extracto legible de la salida de k6 (checks y umbrales) — equivale a la captura de terminal."""
    txt = read(run / "summary.txt")
    keep = [l for l in txt.splitlines()
            if re.search(r"[✓✗]|http_req_duration|http_req_failed|http_reqs|dropped_iterations|iterations\.|vus_max|checks", l)
            and "http_req_duration{" not in l]
    return "\n".join(keep[:45])


# ───────────────────────────────────────────── análisis por tipo de prueba
def load_stats(label):
    rs = runs(label, "load")
    frames, verdicts = [], []
    for i, r in enumerate(rs, 1):
        pt = phase_table(load_raw(r))
        frames.append(pt[pt.fase == "steady"].assign(corrida=i, carpeta=rel(r)))
        th = thresholds(r)
        verdicts.append({"corrida": i, "carpeta": rel(r), "umbrales": len(th),
                         "cumplidos": sum(1 for *_, ok in th if ok),
                         "incumplidos": ", ".join(f"{n} {x}" for n, x, ok in th if not ok) or "ninguno",
                         "invariantes": "OK" if "TODAS las reglas" in read(r / "invariants.txt") else "REVISAR"})
    if not frames:
        return None
    df = pd.concat(frames)
    agg = df.groupby("endpoint").agg(
        req_s=("req/s", "mean"), p50=("p50_ms", "mean"), p95=("p95_ms", "mean"), p95_sd=("p95_ms", "std"),
        p99=("p99_ms", "mean"), err=("error_%", "mean"), dropped=("dropped", lambda s: pd.to_numeric(s, errors="coerce").sum()))
    agg["cv"] = 100 * agg.p95_sd / agg.p95
    return {"runs": rs, "per_run": df, "agg": agg, "verdicts": pd.DataFrame(verdicts)}


def resources_by_phase(run):
    tl = pd.read_csv(run / "timeline.csv") if (run / "timeline.csv").exists() else None
    if tl is None or "cpu_db" not in tl:
        return pd.DataFrame()
    tl["phase"] = tl["phase"].ffill()
    g = tl.groupby("phase")
    out = pd.DataFrame({
        "CPU db prom %": g.cpu_db.mean().round(0), "CPU db máx %": g.cpu_db.max().round(0),
        "CPU api prom %": g.cpu_api.mean().round(0), "CPU api máx %": g.cpu_api.max().round(0),
        "CPU k6 máx %": g.cpu_k6.max().round(0),
        "RAM db máx MiB": g.mem_db_mib.max().round(0), "RAM api máx MiB": g.mem_api_mib.max().round(0),
        "conex. PG activas máx": g.pg_active.max().round(0), "VUs máx": g.vus.max(),
    }).reset_index().rename(columns={"phase": "fase"})
    return out[out.fase.isin(["ramp", "steady", "stress", "recovery"])]


def stress_stats(label):
    rs = runs(label, "stress")
    if not rs:
        return None
    r = rs[-1]
    df = load_raw(r)
    st = df[df.phase == "stress"].copy()
    st["minute"] = (st.t // 60).astype(int)
    reqs = st[st.metric_name == "http_reqs"].groupby("minute").size() / 60
    drop = st[st.metric_name == "dropped_iterations"].groupby("minute").metric_value.sum() / 60
    fail = 100 * st[st.metric_name == "http_req_failed"].groupby("minute").metric_value.mean()
    dur = st[st.metric_name == "http_req_duration"]
    p95 = dur.groupby("minute").metric_value.quantile(.95)
    pm = pd.DataFrame({"logradas": reqs, "dropped": drop, "error": fail, "p95": p95}).fillna(0)
    pm["ofrecidas"] = pm.logradas + pm.dropped
    for ep in THR:
        pm[f"p95_{ep}"] = dur[dur.endpoint == ep].groupby("minute").metric_value.quantile(.95)
    pm = pm[pm.logradas > 0]
    full = pm.iloc[1:-1] if len(pm) > 3 else pm  # descarta minuto inicial y el último parcial

    def bad(row):
        why = [f"p95 {EP_ES[ep]} {ms(row[f'p95_{ep}'])} ms > {t}" for ep, t in THR.items() if row[f"p95_{ep}"] > t]
        if row.logradas < 0.95 * row.ofrecidas:
            why.append(f"logradas {row.logradas:.1f} < 95 % de ofrecidas {row.ofrecidas:.1f}")
        if row.error > 1:
            why.append(f"errores {row.error:.1f} %")
        return why

    sat = next(((m, row, bad(row)) for m, row in full.iterrows() if bad(row)), None)
    ok_before = full[full.index < sat[0]] if sat else full
    capacity = ok_before.ofrecidas.max() if len(ok_before) else None

    stdout = read(r / "k6-stdout.log")
    aborted = "stopping test prematurely" in stdout
    abort_line = next((l for l in stdout.splitlines() if "stopping test prematurely" in l), "")
    abort_min = None
    if aborted:
        abort_min = round(st.t.max() / 60, 1)

    # Recuperación: fase recovery de la misma corrida o corrida recovery posterior
    rec_src, rec = r, df[df.phase == "recovery"]
    if rec[rec.metric_name == "http_reqs"].empty:
        rr = [p for p in runs(label, "recovery") if p.name > r.name]
        if rr:
            rec_src = rr[0]
            rec = load_raw(rec_src)
    recovery = None
    if not rec[rec.metric_name == "http_reqs"].empty:
        rd = rec[rec.metric_name == "http_req_duration"]
        t0 = rec[rec.metric_name == "http_reqs"].t.min()
        b = rd.assign(b=((rd.t - t0) // 10) * 10).groupby("b").metric_value.quantile(.95)
        back = next((int(k) for k, v in b.items() if v < 300), None)
        recovery = {"src": rec_src, "p95": float(np.percentile(rd.metric_value, 95)),
                    "p99": float(np.percentile(rd.metric_value, 99)),
                    "err": 100 * rec[rec.metric_name == "http_req_failed"].metric_value.mean(),
                    "seconds_to_normal": back, "same_run": rec_src == r}

    # Interpretación de dropped_iterations (sin atribuirlo automáticamente al servidor)
    total_drop = int(st[st.metric_name == "dropped_iterations"].metric_value.sum())
    win = df[(df.t >= st.t.min()) & (df.t <= st.t.max())]  # vus/vus_max no llevan escenario: se toman por tiempo
    vus = win[win.metric_name == "vus"].metric_value.max()
    vus_max = win[win.metric_name == "vus_max"].metric_value.max()
    it = st[st.metric_name == "iteration_duration"]
    tl = pd.read_csv(r / "timeline.csv") if (r / "timeline.csv").exists() else pd.DataFrame()
    k6cpu = tl[tl.phase == "stress"].cpu_k6.max() if "cpu_k6" in tl else np.nan
    dbcpu = tl[tl.phase == "stress"].cpu_db.max() if "cpu_db" in tl else np.nan
    first_drop = pm[pm.dropped > 0].index.min() if (pm.dropped > 0).any() else None
    little = None
    if first_drop is not None and not it.empty:
        worst = pm.dropped.idxmax()  # minuto con más iteraciones perdidas
        itm = it[(it.t // 60) == worst].metric_value.mean() / 1000
        p95w = pm.loc[worst, "p95"]
        little = (pm.loc[worst, "ofrecidas"], itm, pm.loc[worst, "ofrecidas"] * itm, worst, p95w)

    return {"run": r, "pm": pm, "sat": sat, "capacity": capacity, "aborted": aborted, "abort_line": abort_line,
            "abort_min": abort_min, "recovery": recovery, "dropped": total_drop, "vus": vus, "vus_max": vus_max,
            "k6cpu": k6cpu, "dbcpu": dbcpu, "little": little, "first_drop": first_drop,
            "phase": phase_table(df), "res": resources_by_phase(r)}


def parse_explain(label):
    txt = read(RES / label / "explain.txt")
    out = {}
    for block in txt.split("=================== ")[1:]:
        title, _, body = block.partition("\n")
        node = next((l.strip().lstrip("-> ").split(" (")[0] for l in body.splitlines()
                     if re.search(r"Scan (on|using) .*reservations|Scan using reservations|Scan on reservations", l)), "—")
        t = re.search(r"Execution Time: ([\d.]+) ms", body)
        bufs = re.search(r"Buffers: shared hit=(\d+)(?: read=(\d+))?", body)
        out[title.strip()] = {"plan": node, "ms": float(t.group(1)) if t else np.nan,
                              "bloques": (int(bufs.group(1)) + int(bufs.group(2) or 0)) if bufs else np.nan}
    return out


QUERY_NAMES = [
    (r"count\(\*\)::int AS n FROM reservations WHERE customer_id", "conteo R5 (al crear)"),
    (r"count\(\*\)::int AS total FROM reservations r WHERE r.status", "conteo listado general"),
    (r"count\(\*\)::int AS total FROM reservations r WHERE r.resource_id", "conteo listado por recurso"),
    (r"count\(\*\)::int AS total FROM reservations r WHERE r.customer_id", "conteo listado por cliente"),
    (r"SELECT r.id, r.resource_id, s.name.*WHERE r.resource_id", "página listado por recurso"),
    (r"SELECT r.id, r.resource_id, s.name.*WHERE r.customer_id", "página listado por cliente"),
    (r"SELECT r.id, r.resource_id, s.name.*WHERE r.status", "página listado general"),
    (r"SELECT r.id, r.resource_id, s.name", "página del listado"),
    (r"SELECT start_at, end_at FROM reservations", "disponibilidad"),
    (r"INSERT INTO reservations", "insert reserva"),
    (r"FROM resources WHERE id", "lookup recurso"),
    (r"FROM customers WHERE id", "lookup cliente"),
]


def parse_pgstat(run):
    rows = []
    for line in read(run / "pg_stat_statements.txt").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 8 and parts[0].isdigit():
            q = parts[7]
            if re.search(r"pg_stat|JOIN reservations b|AT TIME ZONE|pg_advisory|^BEGIN|^COMMIT|^ROLLBACK|SELECT \$1", q):
                continue
            name = next((n for pat, n in QUERY_NAMES if re.search(pat, q)), q[:40])
            calls, blocks = int(parts[0]), int(parts[5])
            rows.append({"consulta": name, "llamadas": calls, "ms prom": float(parts[2]),
                         "% tiempo BD": float(parts[6]), "bloques/llamada": round(blocks / max(calls, 1))})
    return pd.DataFrame(rows).head(8)


ENV_KEYS = [("CPU", r"model name\s*:\s*(.*)|^machdep.*|^(Apple .*)"), ("Núcleos lógicos", r"núcleos lógicos: (\d+)"),
            ("RAM total (MiB)", r"^Mem:\s+(\d+)"), ("SO", r"^(Linux .*|Darwin .*)"), ("Docker", r"(Docker version [^,]+)"),
            ("Node", r"^node: (v[\d.]+)"), ("k6", r"^(k6 v[\d.]+)"), ("PostgreSQL", r"(PostgreSQL [\d.]+)"),
            ("Contenedor api", r"(/?reservas-api CPU=.*)"), ("Contenedor db", r"(/?reservas-db CPU=.*)"),
            ("Pool PG", r"PG_POOL_MAX=(.*)"), ("Reservas en BD", r"^reservations \| (\d+)"),
            ("Tamaño BD", r"tamaño BD: (.*)"), ("shared_buffers", r"shared_buffers = (.*)"), ("Commit", r"commit: (.*)")]


def env_table():
    def grab(label):
        rs = runs(label, "load") or runs(label, "stress")
        txt = read(rs[0] / "env.txt") if rs else ""
        out = {}
        for k, pat in ENV_KEYS:
            m = next((re.search(pat, l) for l in txt.splitlines() if re.search(pat, l)), None)
            out[k] = (next((g for g in m.groups() if g), m.group(0)) if m and m.groups() else (m.group(0) if m else "—")).strip()
        n_idx = sum(1 for l in txt.splitlines() if l.strip().startswith(("reservations_", "no_overlap", "reservations_pkey")))
        out["Índices en reservations"] = str(n_idx) if txt else "—"
        return out, (rel(rs[0] / "env.txt") if rs else "—")
    a, pa = grab("antes")
    d, pd_ = grab("despues")
    rows = [{"Condición": k, "Antes": a.get(k, "—"), "Después": d.get(k, "—"),
             "¿Igual?": "sí" if a.get(k) == d.get(k) else ("cambia (esperado)" if k in ("Commit", "Índices en reservations", "Tamaño BD", "Reservas en BD") else "DIFERENTE")}
            for k in list(dict(ENV_KEYS)) + ["Índices en reservations"]]
    return pd.DataFrame(rows), pa, pd_


def run_compare(fase, scen):
    a, d = runs("antes", scen), runs("despues", scen)
    if not a or not d:
        return None
    out = RES / f"comparacion-{scen}"
    subprocess.run([sys.executable, str(ROOT / "scripts/compare.py"), "--antes", *map(str, a), "--despues", *map(str, d),
                    "--fase", fase, "--salida", str(out)], check=True, capture_output=True)
    return out


def ensure_analyzed():
    for label in ("antes", "despues"):
        for scen in ("smoke", "load", "stress", "recovery"):
            for r in runs(label, scen):  # siempre se regenera desde raw.csv.gz (versión actual del análisis)
                    subprocess.run([sys.executable, str(ROOT / "scripts/analyze.py"), str(r)], check=True, capture_output=True)


def descartadas_html():
    """Corridas separadas del análisis por un problema de ejecución documentado (results/_descartadas/)."""
    d = RES / "_descartadas"
    if not d.exists():
        return ""
    dirs = sorted(p for p in d.rglob("*") if p.is_dir() and (p / "raw.csv.gz").exists())
    nota = read(d / "NOTA.txt").strip()
    rows = "".join(f"<tr><td><code>{E(rel(p))}</code></td></tr>" for p in dirs)
    return (f"<h3>Corridas descartadas</h3><p>Se conservan sin modificar pero no se usan en el análisis.</p>"
            f"{pre(nota) if nota else ''}<table><tr><th>Carpeta</th></tr>{rows}</table>")


# ───────────────────────────────────────────── texto interpretativo (desde los datos)
def load_text(L, label):
    if not L:
        return f'<p class="warn">No hay corridas de carga en results/{label}.</p>'
    v = L["verdicts"]
    allok = int((v.cumplidos == v.umbrales).sum())
    agg = L["agg"]
    ratios = {ep: agg.loc[ep, "p95"] / t for ep, t in THR.items() if ep in agg.index}
    worst = max(ratios, key=ratios.get)
    cv = agg.loc[[e for e in THR if e in agg.index], "cv"].max()
    s = (f"<p>Con la demanda de diseño (20 req/s sostenidos 10 min), <b>{allok} de {len(v)}</b> corridas cumplieron "
         f"todos los umbrales. El throughput logrado fue {agg.loc['(todos)', 'req_s']:.2f} req/s (planificado 20). "
         f"El endpoint más cercano a su límite es <b>{EP_ES[worst]}</b>: p95 medio {ms(agg.loc[worst, 'p95'])} ms "
         f"= {100 * ratios[worst]:.0f} % de su umbral ({THR[worst]} ms). ")
    if len(v) > 1 and not np.isnan(cv):
        s += (f"La variación entre corridas (coeficiente de variación del p95) llegó hasta {cv:.1f} %"
              + (", <b>mayor al 15 % definido en el plan</b>: se debe explicar (actividad del equipo, caché, temperatura) o repetir." if cv > 15
                 else ", dentro del 15 % definido en el plan, así que las diferencias entre corridas son ruido normal.") + "</p>")
    return s + "</p>" if not s.endswith("</p>") else s


def stress_text(S, label):
    if not S:
        return f'<p class="warn">No hay corrida de estrés en results/{label}.</p>'
    peak = S["pm"].ofrecidas.max()
    t = []
    if S["sat"]:
        m, row, why = S["sat"]
        t.append(f"<p><b>Saturación:</b> primer minuto que incumple los criterios del plan: minuto {m} con ≈{row.ofrecidas:.0f} "
                 f"req/s ofrecidas ({'; '.join(why)}). <b>Capacidad sostenible</b> ≈ {S['capacity']:.0f} req/s "
                 f"(último nivel que cumplió todos los criterios).</p>")
    else:
        t.append(f"<p><b>No se alcanzó saturación dentro del límite seguro</b>: hasta ≈{peak:.0f} req/s ofrecidas todos los "
                 f"minutos cumplieron los umbrales de latencia, throughput y errores. Se declara así, sin subir el tope.</p>")
    if S["aborted"]:
        t.append(f"<p><b>Interrupción por seguridad:</b> k6 detuvo la prueba en el minuto ≈{S['abort_min']} porque se cruzó un "
                 f"límite con <code>abortOnFail</code>: <code>{E(S['abort_line'].split('msg=')[-1].strip(chr(34)))}</code>. "
                 f"La fase de recuperación integrada no se ejecutó; se verificó con <code>k6/recovery.js</code>.</p>")
    rc = S["recovery"]
    if rc:
        ok = rc["p95"] < 300 and rc["err"] < 1
        t.append(f"<p><b>Recuperación</b> ({'fase integrada' if rc['same_run'] else 'prueba posterior segura'}, 10 req/s): "
                 f"p95 {ms(rc['p95'])} ms, p99 {ms(rc['p99'])} ms, errores {rc['err']:.2f} % → "
                 f"{'<b>se recuperó</b>' if ok else '<b>NO cumplió el criterio de recuperación</b>'} (criterio: p95 &lt; 300 ms y errores &lt; 1 %). "
                 + (f"El p95 por ventanas de 10 s quedó bajo 300 ms a los {rc['seconds_to_normal']} s de iniciar la fase.</p>"
                    if rc["seconds_to_normal"] is not None else "El p95 no bajó de 300 ms en ninguna ventana.</p>"))
    if S["dropped"] == 0:
        t.append("<p><b>dropped_iterations = 0:</b> k6 aplicó toda la carga planificada; la tasa ofrecida es la real.</p>")
    else:
        msg = (f"<p><b>dropped_iterations = {S['dropped']:,}</b> (desde el minuto {S['first_drop']}). No se atribuye "
               f"automáticamente al servidor: se contrastó con el generador. CPU máxima de k6: {S['k6cpu']:.0f} % de un núcleo; "
               f"VUs activos máximos {S['vus']:.0f} de {S['vus_max']:.0f} asignables. ")
        if not np.isnan(S["k6cpu"]) and S["k6cpu"] >= 85:
            msg += "k6 estuvo cerca de saturar su propio núcleo, así que <b>parte de las iteraciones perdidas puede deberse al generador</b>.</p>"
        elif S["vus"] >= 0.95 * S["vus_max"] and S["little"]:
            rate, itd, need, worst, p95w = S["little"]
            msg += (f"En el minuto {worst} (el de más pérdidas) se ofrecían ≈{rate:.0f} iteraciones/s y cada iteración tardaba en "
                    f"promedio {itd:.2f} s (p95 de respuesta {ms(p95w)} ms). Por la Ley de Little (VUs ≈ tasa × duración) eso exige "
                    f"≈{need:.0f} VUs ocupados simultáneamente; con los {S['vus_max']:.0f} VUs agotados, k6 no tuvo con quién iniciar "
                    f"nuevas iteraciones. Como el generador tenía CPU de sobra, las pérdidas son <b>consecuencia de la latencia del "
                    f"servidor</b> (CPU de la BD hasta {S['dbcpu']:.0f} %), no del generador.</p>")
        else:
            msg += "Los VUs no llegaron al máximo: revisar <code>k6-stdout.log</code> por avisos de asignación de VUs.</p>"
        t.append(msg)
    return "".join(t)


# ───────────────────────────────────────────── HTML
CSS = """
@page { size: A4; margin: 16mm 14mm 16mm 14mm; }
body { font-family: "Segoe UI", Roboto, Arial, sans-serif; font-size: 10.2pt; color: #1f2328; line-height: 1.42; max-width: 190mm; margin: auto; }
h1 { font-size: 20pt; margin: 0 0 4mm; } h2 { font-size: 14pt; border-bottom: 2px solid #1f6feb; padding-bottom: 1mm; margin-top: 8mm; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin: 5mm 0 2mm; page-break-after: avoid; } .brk { page-break-before: always; }
table { border-collapse: collapse; width: 100%; margin: 2mm 0 3mm; font-size: 8.6pt; page-break-inside: avoid; }
th { background: #f0f3f6; text-align: left; } th, td { border: 1px solid #d0d7de; padding: 1.2mm 1.6mm; vertical-align: top; }
td:not(:first-child) { font-variant-numeric: tabular-nums; }
figure { margin: 3mm 0; page-break-inside: avoid; text-align: center; } figure img { max-width: 100%; max-height: 210mm; }
figcaption { font-size: 8.8pt; color: #3d444d; text-align: left; margin-top: 1mm; } .src { color: #656d76; }
pre { background: #f6f8fa; border: 1px solid #d0d7de; padding: 2mm; font-size: 7.6pt; line-height: 1.3; white-space: pre-wrap; page-break-inside: avoid; }
code { font-size: 8.8pt; background: #f6f8fa; padding: 0 1mm; } .warn { color: #9a6700; background: #fff8c5; padding: 1mm 2mm; }
.cover td { font-size: 10.5pt; } .cover td:first-child { width: 38mm; font-weight: 600; background: #f6f8fa; }
.good { color: #1a7f37; font-weight: 600; } .bad { color: #cf222e; font-weight: 600; }
.wm { position: fixed; top: 40%; left: 5%; font-size: 70pt; color: rgba(207,34,46,.13); transform: rotate(-30deg); z-index: 0; }
"""


def build(a):
    ensure_analyzed()
    LA, LD = load_stats("antes"), load_stats("despues")
    SA, SD = stress_stats("antes"), stress_stats("despues")
    cmp_load = run_compare("steady", "load")
    cmp_stress = run_compare("stress", "stress")
    envdf, env_a, env_d = env_table()
    exa, exd = parse_explain("antes"), parse_explain("despues")
    smoke_a = runs("antes", "smoke")
    smoke_d = runs("despues", "smoke")
    h = [f"<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Informe pruebas de carga — {E(a.nombre)}</title>"
         f"<style>{CSS}</style></head><body>"]
    if a.muestra:
        h.append('<div class="wm">EJEMPLO · NO ENTREGAR</div>')

    # 1. Portada
    h.append(f"""<h1>API de reservas: pruebas de carga, estrés y corrección</h1>
<table class="cover">
<tr><td>Estudiante</td><td>{E(a.nombre)}</td></tr><tr><td>Carné</td><td>{E(a.carne)}</td></tr>
{f'<tr><td>Curso</td><td>{E(a.curso)}</td></tr>' if a.curso else ''}{f'<tr><td>Catedrático</td><td>{E(a.catedratico)}</td></tr>' if a.catedratico else ''}
<tr><td>Fecha</td><td>{date.today().strftime('%d/%m/%Y')}</td></tr>
<tr><td>Repositorio</td><td><a href="{E(a.repo)}">{E(a.repo)}</a><br>Etiquetas: <code>v1-baseline</code> (antes) · <code>v2-fix</code> (después)</td></tr>
<tr><td>Video (≤ 3 min)</td><td><a href="{E(a.video)}">{E(a.video)}</a></td></tr>
</table>
<h2>1. Descripción de la API</h2>
<p>API REST de reservas de espacios de un centro universitario (salas, laboratorios, canchas y un auditorio), construida con
<b>Node.js 22 + Express 4</b> sobre <b>PostgreSQL 16</b>, sin frontend. Los datos ficticios se generan con una semilla
determinística: 40 recursos, 5 000 clientes y 315 366 reservas entre 2025 y 2027; el año 2028 queda vacío para que las
pruebas escriban sin alterar lo sembrado.</p>
<table><tr><th>Método</th><th>Ruta</th><th>Función</th><th>Códigos</th></tr>
<tr><td>GET</td><td><code>/resources/:id/availability?date=</code></td><td>Disponibilidad del día en bloques de 30 min</td><td>200, 400, 404</td></tr>
<tr><td>POST</td><td><code>/reservations</code></td><td>Crear reserva</td><td>201, 400, 404, 409, 422</td></tr>
<tr><td>GET</td><td><code>/reservations?page=&amp;page_size=&amp;resource_id=&amp;customer_id=&amp;from=&amp;to=</code></td><td>Listado paginado (máx. 100) con total</td><td>200, 400</td></tr></table>
<table><tr><th>Regla</th><th>Descripción</th><th>Garantía</th></tr>
<tr><td>R1</td><td>Duración 30–240 min en múltiplos de 30</td><td>Validación → 422</td></tr>
<tr><td>R2</td><td>Dentro del horario 8:00–20:00 (Guatemala), mismo día</td><td>Validación → 422</td></tr>
<tr><td>R3</td><td>No reservar en el pasado</td><td>Validación → 422</td></tr>
<tr><td>R4</td><td>Sin traslapes por recurso</td><td>Restricción <code>EXCLUDE USING gist</code> → 409</td></tr>
<tr><td>R5</td><td>Máximo 2 reservas por cliente por día</td><td>Transacción + <code>pg_advisory_xact_lock</code> → 422</td></tr></table>
<p><b>Decisiones:</b> las reglas críticas viven en la base (R4) o en transacción con bloqueo por cliente (R5) para que la
concurrencia de las pruebas no las rompa; 409/422 se declaran respuestas esperadas en k6 para no contarlas como fallas del
servidor; Docker Compose fija 1 CPU por contenedor (api 512 MiB, db 1 GiB) para que antes y después sean comparables.
Detalle en <code>docs/DECISIONES.md</code>. Instalación, configuración, inicio y restablecimiento: <code>README.md</code> §3–4
(<code>docker compose up -d --build</code> · <code>scripts/reset-env.sh</code>).</p>""")

    # 2. Entorno
    h.append(f"""<h2 class="brk">2. Condiciones de ejecución</h2>
<p>Extraído de <code>env.txt</code> de cada corrida (<code>{E(env_a)}</code> y <code>{E(env_d)}</code>). Antes de cada
prueba de carga o estrés se ejecutó <code>scripts/reset-env.sh</code>: datos restablecidos, contenedores reiniciados
(caché de PostgreSQL vacía) y calentamiento con la prueba de humo. La caché de páginas del sistema operativo no se controla.
k6 corre en el mismo equipo, por eso su CPU se registra en <code>resources.csv</code>.</p>{table(envdf)}""")

    # 3. Plan
    h.append("""<h2>3. Plan de pruebas</h2>
<p>Fijado en <code>docs/PLAN.md</code> dentro del commit <code>v1-baseline</code>, anterior a todos los resultados.</p>
<h3>Demanda esperada y mezcla</h3>
<p>5 000 usuarios; 10 % activos en la hora pico (500). Sesión típica de 15 solicitudes en 10 min →
500 × 15 / 600 s ≈ <b>12,5 req/s</b>. Demanda de diseño con margen de 60 %: <b>20 req/s</b>. Mezcla derivada de la sesión:
<b>60 % disponibilidad, 25 % listado, 15 % creación</b>, con semilla fija (<code>SEED=42</code>) para que antes y después
envíen la misma secuencia de solicitudes.</p>
<table><tr><th>Escenario</th><th>Perfil</th><th>Duración</th><th>Justificación</th></tr>
<tr><td>Humo</td><td>1 VU, las 3 operaciones + R1, R3, R4, R5 de punta a punta</td><td>1 min</td><td>Si falla no se aplica carga</td></tr>
<tr><td>Carga sostenida</td><td>Tasa de llegada 0→20 req/s (1 min) y 20 req/s constantes</td><td>11 min ×3</td><td>Verificar la demanda de diseño; 3 repeticiones para medir variación</td></tr>
<tr><td>Estrés + recuperación</td><td>20→40→60→80→100 req/s (1 min subida + 2 min meseta) y luego 10 req/s</td><td>≈18,5 min</td><td>Ubicar saturación (5× la demanda) y observar recuperación con carga baja</td></tr>
<tr><td>Recuperación posterior</td><td>10 req/s</td><td>3 min</td><td>Solo si el estrés se detiene por seguridad</td></tr></table>
<p>Se usa <b>modelo abierto</b> (<code>arrival-rate</code>): los usuarios llegan aunque el servidor esté lento. Con VUs fijos,
un servidor lento recibiría menos carga y ocultaría el problema. Si k6 agota <code>maxVUs</code> registra
<code>dropped_iterations</code>.</p>
<h3>Umbrales de aprobación (fase sostenida)</h3>
<table><tr><th>Métrica</th><th>Umbral</th><th>Justificación</th></tr>
<tr><td>http_req_failed</td><td>&lt; 1 %</td><td>5xx o timeouts; 409/422 son reglas de negocio, no fallas</td></tr>
<tr><td>checks</td><td>&gt; 99 %</td><td>Respuestas funcionalmente correctas (24 bloques, paginación coherente)</td></tr>
<tr><td>p95 / p99 disponibilidad</td><td>&lt; 300 / 800 ms</td><td>Operación más frecuente e interactiva; deja margen de red para &lt; 1 s percibido</td></tr>
<tr><td>p95 / p99 listado y creación</td><td>&lt; 500 / 1000 ms</td><td>Consultas más pesadas o transaccionales; tolerancia de ~1 s</td></tr>
<tr><td>dropped_iterations</td><td>&lt; 1 % de lo planificado</td><td>Si se pierden iteraciones la carga no se aplicó completa</td></tr></table>
<h3>Límites de seguridad y criterios de detención</h3>
<table><tr><th>Límite</th><th>Valor</th></tr>
<tr><td>Recursos</td><td>1 CPU por contenedor; <code>maxVUs</code> 100 (carga) y 300 (estrés); solo <code>127.0.0.1</code></td></tr>
<tr><td>Aborto automático en estrés</td><td>errores ≥ 10 % o p95 ≥ 5 s (<code>abortOnFail</code>, tras 1 min)</td></tr>
<tr><td>Detención manual</td><td>CPU del equipo &gt; 90 % sostenido, uso de swap o k6 ≥ 90 % de un núcleo</td></tr>
<tr><td>Saturación (lectura)</td><td>primer minuto con p95 de algún endpoint sobre su umbral, logradas &lt; 95 % de ofrecidas o errores &gt; 1 %</td></tr>
<tr><td>Recuperación</td><td>p95 &lt; 300 ms y errores &lt; 1 % a 10 req/s</td></tr></table>
<p>Después de cada corrida, <code>scripts/verify-invariants.js</code> revisa R1, R2, R4 y R5 en toda la base.</p>""")

    # 4. Resultados ANTES
    def side(label, L, S, smoke):
        out = [f"<h2 class='brk'>{'4' if label == 'antes' else '6'}. Resultados {label.upper()} "
               f"(<code>{'v1-baseline' if label == 'antes' else 'v2-fix'}</code>)</h2>"]
        reg = read(RES / label / "regresion.txt")
        if reg:
            m = re.search(r"# pass (\d+).*?# fail (\d+)", reg, re.S)
            out.append(f"<p><b>Regresión funcional:</b> {m.group(1)} pruebas pasaron, {m.group(2)} fallaron "
                       f"(<code>results/{label}/regresion.txt</code>).</p>" if m else "")
        if smoke:
            th = thresholds(smoke[-1])
            okn = sum(1 for *_, ok in th if ok)
            out.append(f"<h3>Humo</h3><p>{okn}/{len(th)} umbrales cumplidos. Extracto de la salida de k6 "
                       f"(<code>{E(rel(smoke[-1]))}/summary.txt</code>):</p>{pre(k6_screen(smoke[-1]))}")
        out.append("<h3>Carga sostenida (20 req/s)</h3>")
        out.append(load_text(L, label))
        if L:
            agg = L["agg"].reindex(["(todos)", "availability", "list", "create"]).reset_index()
            t = pd.DataFrame({"endpoint": agg.endpoint.map(EP_ES), "req/s": agg.req_s.round(2), "p50 ms": agg.p50.map(ms),
                              "p95 ms": agg.p95.map(ms), "±sd p95": agg.p95_sd.map(ms), "CV p95": agg.cv.map(lambda v: "—" if np.isnan(v) else f"{v:.1f} %"),
                              "p99 ms": agg.p99.map(ms), "errores %": agg.err.round(3)})
            out.append(f"<p>Media de {len(L['runs'])} corridas, fase sostenida:</p>{table(t)}{table(L['verdicts'])}")
            out.append(img(L["runs"][0] / "timeline.png", "Línea de tiempo carga",
                           f"<b>Figura.</b> Carga sostenida, corrida 1 ({label}). Panel 1: req/s logradas vs dropped y VUs. "
                           "Panel 2: p50/p95/p99 (escala log). Panel 3: p95 por endpoint y % de error. Panel 4: CPU de api, BD y k6, "
                           "y conexiones activas en PostgreSQL."))
            res = resources_by_phase(L["runs"][0])
            if len(res):
                out.append(f"<p><b>Recursos</b> (corrida 1, CPU en % de un núcleo; 100 % = el límite del contenedor):</p>{table(res)}")
        out.append("<h3 class='brk'>Estrés progresivo y recuperación</h3>")
        out.append(stress_text(S, label))
        if S:
            out.append(img(S["run"] / "timeline.png", "Línea de tiempo estrés",
                           f"<b>Figura.</b> Estrés ({label}). Fondo amarillo: escalones de estrés; verde: recuperación. "
                           "Se lee de arriba abajo: si la carga ofrecida sube y la lograda no, aparecen dropped; si la latencia sube "
                           "mientras la CPU de la BD llega a ~100 %, el cuello de botella es la base de datos."))
            pm = S["pm"].reset_index().rename(columns={"index": "min"})
            t = pd.DataFrame({"min": pm.iloc[:, 0], "ofrecidas/s": pm.ofrecidas.round(1), "logradas/s": pm.logradas.round(1),
                              "dropped/s": pm.dropped.round(2), "p95 disp.": pm.p95_availability.map(ms), "p95 listado": pm.p95_list.map(ms),
                              "p95 creación": pm.p95_create.map(ms), "error %": pm.error.round(2)})
            out.append(f"<p>Por minuto (fase de estrés), de <code>{E(rel(S['run']))}/raw.csv.gz</code>:</p>{table(t)}")
            if len(S["res"]):
                out.append(f"<p><b>Recursos por fase:</b></p>{table(S['res'])}")
        return "".join(out)

    h.append(side("antes", LA, SA, smoke_a))

    # 5. Hallazgo
    def first_pg(label):
        for r in runs(label, "load") + runs(label, "stress"):
            df = parse_pgstat(r)
            if len(df):
                return df, r
        return pd.DataFrame(), None
    pga, pga_src = first_pg("antes")
    pgd, pgd_src = first_pg("despues")
    rows = []
    for k in exa:
        if k in exd:
            rows.append({"consulta": k, "plan antes": exa[k]["plan"], "ms antes": ms(exa[k]["ms"]), "bloques antes": exa[k]["bloques"],
                         "plan después": exd[k]["plan"], "ms después": ms(exd[k]["ms"]), "bloques después": exd[k]["bloques"]})
    exdf = pd.DataFrame(rows)
    seq_a = sum(1 for v in exa.values() if "Seq Scan" in v["plan"])
    top = pga.head(4) if len(pga) else pd.DataFrame()
    top_pct = top["% tiempo BD"].sum() if len(top) else np.nan
    dbmax = SA["dbcpu"] if SA else np.nan
    h.append(f"""<h2 class="brk">5. Hallazgo: consultas sin índice adecuado saturan la base de datos</h2>
<h3>Evidencia</h3>
<ul>
<li><b>Recursos:</b> en el estrés ANTES la CPU de la BD llegó a {dbmax:.0f} % (límite = 100 % de 1 CPU) mientras la API y k6
se mantuvieron bajas → el cuello de botella está en PostgreSQL, no en Node ni en el generador.</li>
<li><b>pg_stat_statements</b> (ANTES): las 4 consultas más costosas suman {top_pct:.0f} % del tiempo de la BD y leen en
promedio {top["bloques/llamada"].median() if len(top) else float("nan"):,.0f} bloques por llamada para devolver entre 1 y 50 filas.</li>
<li><b>EXPLAIN (ANALYZE, BUFFERS)</b>: {seq_a} de {len(exa)} consultas de la API recorren la tabla completa
(<code>Seq Scan on reservations</code>).</li>
<li><b>Latencia:</b> disponibilidad, cuya consulta aislada tarda pocos ms, también se degrada bajo estrés: espera en la cola
del pool de 10 conexiones ocupado por las consultas lentas.</li></ul>
<p>Consultas más costosas, carga ANTES (<code>{E(rel(pga_src)) if pga_src else '—'}/pg_stat_statements.txt</code>):</p>{table(pga) if len(pga) else ''}
<h3>Hipótesis</h3>
<p>La tabla <code>reservations</code> (~315 000 filas) solo tiene índices para la clave primaria y la restricción de no
traslape. Los filtros por <code>customer_id</code>, o por <code>resource_id</code> ordenando por <code>start_at</code>, no
tienen índice que coincida, así que PostgreSQL lee la tabla completa en cada llamada. Bajo carga eso agota la CPU de la BD,
las consultas retienen las conexiones del pool y el resto de solicitudes espera en cola. Predicción: con índices que
coincidan con filtro y orden, los planes pasan a <code>Index Scan</code>, baja la CPU de la BD, baja el p95 y la saturación
ocurre a una tasa mayor, sin cambiar reglas ni respuestas.</p>
<h3>Corrección (<code>v2-fix</code>)</h3>
<pre>-- db/migrations/002_indexes.sql
CREATE INDEX reservations_resource_start_idx ON reservations (resource_id, start_at DESC, id DESC);
CREATE INDEX reservations_customer_start_idx ON reservations (customer_id, start_at DESC, id DESC);
CREATE INDEX reservations_start_idx          ON reservations (start_at DESC, id DESC);

-- src/app.js (disponibilidad): cota inferior equivalente por R1 (ninguna reserva dura más de 240 min)
AND start_at >= $2::timestamptz - interval '240 minutes'</pre>
<p>No cambiaron endpoints, contratos JSON, reglas, pool, límites de contenedores, datos, demanda ni umbrales.</p>
<h3>Verificación de planes (sin carga, mismos parámetros)</h3>
<p>De <code>results/antes/explain.txt</code> y <code>results/despues/explain.txt</code>:</p>{table(exdf) if len(exdf) else '<p class="warn">Falta explain.txt</p>'}""")

    h.append(side("despues", LD, SD, smoke_d))

    # 6. Comparación
    cmp_rows = []
    for name, A, D in (("Carga 20 req/s (fase sostenida)", LA, LD),):
        if A and D:
            for ep in ["(todos)", "availability", "list", "create"]:
                if ep in A["agg"].index and ep in D["agg"].index:
                    pa, pdv = A["agg"].loc[ep, "p95"], D["agg"].loc[ep, "p95"]
                    cmp_rows.append({"prueba": name, "endpoint": EP_ES[ep], "p95 antes": ms(pa), "p95 después": ms(pdv),
                                     "Δ p95": pct(100 * (pdv - pa) / pa), "p99 antes": ms(A["agg"].loc[ep, "p99"]),
                                     "p99 después": ms(D["agg"].loc[ep, "p99"]), "err % antes": round(A["agg"].loc[ep, "err"], 3),
                                     "err % después": round(D["agg"].loc[ep, "err"], 3)})
    if SA and SD:
        pa_, pd2 = SA["phase"], SD["phase"]
        for ep in ["(todos)", "availability", "list", "create"]:
            ra = pa_[(pa_.fase == "stress") & (pa_.endpoint == ep)]
            rd = pd2[(pd2.fase == "stress") & (pd2.endpoint == ep)]
            if len(ra) and len(rd):
                a95, d95 = ra.p95_ms.iat[0], rd.p95_ms.iat[0]
                cmp_rows.append({"prueba": "Estrés (fase completa)", "endpoint": EP_ES[ep], "p95 antes": ms(a95), "p95 después": ms(d95),
                                 "Δ p95": pct(100 * (d95 - a95) / a95), "p99 antes": ms(ra.p99_ms.iat[0]), "p99 después": ms(rd.p99_ms.iat[0]),
                                 "err % antes": ra["error_%"].iat[0], "err % después": rd["error_%"].iat[0]})
    cmpdf = pd.DataFrame(cmp_rows)
    # Regresiones y límites
    notes = []
    if LA and LD:
        for ep in ["availability", "list", "create"]:
            if ep in LA["agg"].index and ep in LD["agg"].index:
                a_, d_ = LA["agg"].loc[ep], LD["agg"].loc[ep]
                noise = 2 * np.nanmax([a_.p95_sd, d_.p95_sd, 0])
                if d_.p95 > a_.p95 and (d_.p95 - a_.p95) > noise:
                    notes.append(f"<li class='bad'>Regresión en {EP_ES[ep]}: p95 {ms(a_.p95)} → {ms(d_.p95)} ms, mayor que la variación entre corridas (±{ms(noise)}).</li>")
                elif d_.p95 > a_.p95:
                    notes.append(f"<li>{EP_ES[ep].capitalize()}: p95 {ms(a_.p95)} → {ms(d_.p95)} ms; la diferencia está dentro de la variación entre corridas (±{ms(noise)} ms), no se considera regresión.</li>")
    sat_txt = ""
    if SA and SD:
        ca = f"≈{SA['capacity']:.0f} req/s" if SA["sat"] else f"sin saturar hasta ≈{SA['pm'].ofrecidas.max():.0f} req/s"
        cd = f"≈{SD['capacity']:.0f} req/s" if SD["sat"] else f"sin saturar hasta ≈{SD['pm'].ofrecidas.max():.0f} req/s (límite seguro)"
        sat_txt = f"<p><b>Capacidad sostenible:</b> antes {ca}; después {cd}. Antes: dropped_iterations = {SA['dropped']:,}; después = {SD['dropped']:,}.</p>"
    h.append(f"""<h2 class="brk">7. Comparación antes / después</h2>
<p>Condiciones equivalentes: mismo equipo, límites, versiones, volumen de datos restablecido, semilla, demanda y umbrales
(tabla de la sección 2); solo cambia el commit. No se redujo la carga ni se relajó ningún umbral.</p>
{table(cmpdf) if len(cmpdf) else '<p class="warn">Faltan corridas de uno de los lados.</p>'}{sat_txt}
{img(cmp_load / 'compare.png', 'comparación carga', '<b>Figura.</b> p95 y p99 en carga sostenida, media de las corridas (barras de error = desviación estándar entre corridas).') if cmp_load else ''}
{img(cmp_stress / 'compare.png', 'comparación estrés', '<b>Figura.</b> p95 y p99 en la fase de estrés completa, antes vs después.') if cmp_stress else ''}
<h3>Explicación de la mejora</h3>
<p>Los índices permiten leer solo las filas necesarias en el orden pedido (con <code>LIMIT</code>), y los conteos por recurso o
cliente se resuelven con <code>Index Only Scan</code>. Menos bloques leídos por solicitud implica menos CPU de BD por
solicitud; por eso la misma CPU limitada atiende más req/s y el pool deja de bloquearse, lo que también mejora endpoints que
no se modificaron (disponibilidad, creación).</p>
<h3>Variación, regresiones y límites</h3>
<ul>{''.join(notes)}
<li>El <b>conteo del listado general</b> (<code>status=confirmed</code>, 10 % de los listados) sigue leyendo casi toda la
tabla: un conteo exacto sobre ~300 000 filas no se resuelve con índice. En la versión corregida pasa a ser la consulta más
costosa (ver <code>pg_stat_statements.txt</code> después). Mejora futura: total aproximado, en caché o paginación por cursor.</li>
<li>Los 3 índices agregan costo a cada <code>INSERT</code> y espacio en disco (ver tamaño de BD en la sección 2).</li>
<li>k6 y el servidor comparten el equipo; la caché del sistema operativo no se controla; los datos son sintéticos con
distribución uniforme.</li></ul>
<p>Consultas más costosas DESPUÉS (<code>{E(rel(pgd_src)) if pgd_src else '—'}/pg_stat_statements.txt</code>):</p>{table(pgd) if len(pgd) else ''}""")

    # 7. Ubicación de resultados y video
    all_runs = sorted(p for lab in ("antes", "despues") for p in (RES / lab).glob("*-*") if p.is_dir())
    inv_ok = sum(1 for p in all_runs if "TODAS las reglas" in read(p / "invariants.txt"))
    h.append(f"""<h2 class="brk">8. Ubicación de los resultados originales</h2>
<p>Todo está versionado en el repositorio, carpeta <code>results/</code>. Reglas de negocio conservadas en
<b>{inv_ok} de {len(all_runs)}</b> corridas (<code>invariants.txt</code>).</p>
<table><tr><th>Corrida</th><th>Código k6</th><th>Reglas</th></tr>
{''.join(f"<tr><td><code>{E(rel(p))}</code></td><td>{E(read(p / 'exit_code.txt').strip() or '—')}</td><td>{'OK' if 'TODAS las reglas' in read(p / 'invariants.txt') else 'revisar'}</td></tr>" for p in all_runs)}</table>
<table><tr><th>Archivo en cada carpeta</th><th>Contenido</th></tr>
<tr><td>raw.csv.gz</td><td>Cada muestra de cada métrica de k6 (dato original)</td></tr>
<tr><td>summary.json / summary.txt / k6-stdout.log</td><td>Resumen y salida completa de k6, incluidos avisos de aborto</td></tr>
<tr><td>resources.csv</td><td>CPU y RAM de api, BD y k6; conexiones activas, cada 2 s</td></tr>
<tr><td>pg_stat_statements.txt</td><td>Consultas que más tiempo consumieron</td></tr>
<tr><td>env.txt · invariants.txt · exit_code.txt</td><td>Condiciones, reglas de negocio y resultado de umbrales (0 = OK, 99 = incumplido)</td></tr>
<tr><td>analysis.md · timeline.png · timeline.csv</td><td>Generados por <code>scripts/analyze.py</code> desde los anteriores</td></tr></table>
{descartadas_html()}
<p>Comparaciones: <code>results/comparacion-load/</code> y <code>results/comparacion-stress/</code>. Planes:
<code>results/&lt;antes|despues&gt;/explain.txt</code>. Bitácora de ejecución: <code>results/&lt;antes|despues&gt;/run-all.log</code>.</p>
<h2>9. Video</h2>
<p><a href="{E(a.video)}">{E(a.video)}</a> — muestra la aplicación funcionando (disponibilidad, creación 201 y rechazo 409),
explica la prueba de estrés (escalones, límites de seguridad y recuperación) y compara el resultado antes y después de la
corrección.</p></body></html>""")
    return "".join(h)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nombre", required=True); ap.add_argument("--carne", required=True)
    ap.add_argument("--repo", required=True); ap.add_argument("--video", required=True)
    ap.add_argument("--curso", default=""); ap.add_argument("--catedratico", default="")
    ap.add_argument("--muestra", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--salida", default=str(ROOT / "informe"))
    a = ap.parse_args()
    out = Path(a.salida); out.mkdir(parents=True, exist_ok=True)
    (out / "informe.html").write_text(build(a), encoding="utf-8")
    print(f"✔ {out / 'informe.html'}")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto((out / "informe.html").resolve().as_uri())
            pg.pdf(path=str(out / "informe.pdf"), format="A4", print_background=True,
                   margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"})
            b.close()
        print(f"✔ {out / 'informe.pdf'}")
    except Exception as e:  # sin Playwright: imprimir desde el navegador
        print(f"(PDF automático no disponible: {type(e).__name__}). Abrí informe.html en Chrome/Edge → Ctrl+P → "
              "Guardar como PDF (A4, márgenes predeterminados, activar 'Gráficos de fondo').")


if __name__ == "__main__":
    main()

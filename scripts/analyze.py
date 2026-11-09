#!/usr/bin/env python3
"""Analiza una corrida a partir de los datos ORIGINALES (raw.csv.gz + resources.csv).

Uso:  python3 scripts/analyze.py results/antes/load-20261103-101500

Genera en la misma carpeta:
  timeline.png   – tasa lograda vs. dropped, latencias p50/p95/p99, % error y CPU, en ventanas de 10 s
  timeline.csv   – los mismos datos en tabla
  analysis.md    – resumen por fase y por endpoint + tabla por minuto (útil para ubicar la saturación)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BUCKET = 10  # segundos


def load_raw(d: Path) -> pd.DataFrame:
    df = pd.read_csv(d / "raw.csv.gz", usecols=["metric_name", "timestamp", "metric_value", "status", "scenario", "extra_tags"],
                     dtype={"status": "string", "scenario": "string", "extra_tags": "string"}, low_memory=False)
    tags = df["extra_tags"].fillna("")
    df["endpoint"] = tags.str.extract(r"(?:^|&)endpoint=([^&]+)")[0]
    df["phase"] = tags.str.extract(r"(?:^|&)phase=([^&]+)")[0]
    # k6 no propaga las etiquetas del escenario a dropped_iterations: se deduce la fase del nombre del escenario
    SCEN_PHASE = {"rampa": "ramp", "sostenida": "steady", "estres": "stress", "recuperacion": "recovery"}
    df["phase"] = df["phase"].fillna(df["scenario"].map(SCEN_PHASE)).fillna("-")
    t0 = df["timestamp"].min()
    df["t"] = df["timestamp"] - t0
    df["bucket"] = (df["t"] // BUCKET) * BUCKET
    df.attrs["t0"] = int(t0)
    return df


def pct(s, q):
    return float(np.percentile(s, q)) if len(s) else np.nan


def phase_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dur = df[df.metric_name == "http_req_duration"]
    reqs = df[df.metric_name == "http_reqs"]
    fail = df[df.metric_name == "http_req_failed"]
    drop = df[df.metric_name == "dropped_iterations"]
    for phase in [p for p in ["ramp", "steady", "stress", "recovery", "-"] if p in set(df.phase)]:
        r = reqs[reqs.phase == phase]
        if r.empty:
            continue
        span = max(1, r.t.max() - r.t.min() + 1)
        for ep in ["(todos)", "availability", "list", "create"]:
            d = dur[dur.phase == phase] if ep == "(todos)" else dur[(dur.phase == phase) & (dur.endpoint == ep)]
            f = fail[fail.phase == phase] if ep == "(todos)" else fail[(fail.phase == phase) & (fail.endpoint == ep)]
            rr = r if ep == "(todos)" else r[r.endpoint == ep]
            if d.empty:
                continue
            rows.append({
                "fase": phase, "endpoint": ep, "solicitudes": len(rr), "req/s": round(len(rr) / span, 2),
                "p50_ms": round(pct(d.metric_value, 50), 1), "p90_ms": round(pct(d.metric_value, 90), 1),
                "p95_ms": round(pct(d.metric_value, 95), 1), "p99_ms": round(pct(d.metric_value, 99), 1),
                "max_ms": round(d.metric_value.max(), 1),
                "error_%": round(100 * f.metric_value.mean(), 3) if len(f) else 0.0,
                "409/422": int(rr.status.isin(["409", "422"]).sum()),
                "dropped": int(drop[drop.phase == phase].metric_value.sum()) if ep == "(todos)" else "",
            })
    return pd.DataFrame(rows)


def timeline(df: pd.DataFrame, d: Path) -> pd.DataFrame:
    g = df.groupby("bucket")
    dur = df[df.metric_name == "http_req_duration"].groupby("bucket").metric_value
    tl = pd.DataFrame({
        "req_s": df[df.metric_name == "http_reqs"].groupby("bucket").size() / BUCKET,
        "dropped_s": df[df.metric_name == "dropped_iterations"].groupby("bucket").metric_value.sum() / BUCKET,
        "p50": dur.quantile(0.50), "p95": dur.quantile(0.95), "p99": dur.quantile(0.99),
        "error_pct": 100 * df[df.metric_name == "http_req_failed"].groupby("bucket").metric_value.mean(),
        "vus": df[df.metric_name == "vus"].groupby("bucket").metric_value.max(),
    })
    for ep in ["availability", "list", "create"]:
        tl[f"p95_{ep}"] = df[(df.metric_name == "http_req_duration") & (df.endpoint == ep)].groupby("bucket").metric_value.quantile(0.95)
    tl["phase"] = g.phase.agg(lambda s: s[s != "-"].mode().iat[0] if (s != "-").any() else "-")
    tl = tl.reindex(range(0, int(tl.index.max()) + 1, BUCKET))
    tl[["req_s", "dropped_s"]] = tl[["req_s", "dropped_s"]].fillna(0)

    res = d / "resources.csv"
    if res.exists():
        r = pd.read_csv(res)
        if len(r):
            r["bucket"] = ((r.epoch - df.attrs["t0"]) // BUCKET) * BUCKET
            r = r[r.bucket >= 0].groupby("bucket").mean(numeric_only=True)
            tl = tl.join(r[[c for c in ["cpu_api", "cpu_db", "cpu_k6", "mem_api_mib", "mem_db_mib", "pg_active", "pg_lock_wait"] if c in r]])
    tl.index.name = "t_s"
    return tl


def plot(tl: pd.DataFrame, d: Path, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(4, 1, figsize=(12, 12), sharex=True)
    x = tl.index / 60
    ax[0].plot(x, tl.req_s, label="req/s logradas", color="#1f6feb")
    ax[0].plot(x, tl.dropped_s, label="dropped_iterations/s", color="#d1242f")
    ax[0].set_ylabel("por segundo"); ax[0].legend(loc="upper left"); ax[0].set_title(title)
    if "vus" in tl:
        a2 = ax[0].twinx(); a2.plot(x, tl.vus, color="#8250df", alpha=.5, ls=":", label="VUs"); a2.set_ylabel("VUs"); a2.legend(loc="upper right")
    for c, col in [("p50", "#2da44e"), ("p95", "#bf8700"), ("p99", "#d1242f")]:
        ax[1].plot(x, tl[c], label=c, color=col)
    ax[1].set_yscale("log"); ax[1].set_ylabel("latencia ms (log)"); ax[1].legend(loc="upper left")
    for ep, col in [("availability", "#1f6feb"), ("list", "#8250df"), ("create", "#bc4c00")]:
        ax[2].plot(x, tl[f"p95_{ep}"], label=f"p95 {ep}", color=col)
    ax[2].set_yscale("log"); ax[2].set_ylabel("p95 por endpoint ms"); ax[2].legend(loc="upper left")
    ax2b = ax[2].twinx(); ax2b.fill_between(x, tl.error_pct.fillna(0), color="#d1242f", alpha=.15, label="% error"); ax2b.set_ylabel("% error"); ax2b.legend(loc="upper right")
    for c, col in [("cpu_api", "#1f6feb"), ("cpu_db", "#bc4c00"), ("cpu_k6", "#6e7781")]:
        if c in tl:
            ax[3].plot(x, tl[c], label=c.replace("cpu_", "CPU % "), color=col)
    ax[3].set_ylabel("CPU % (100 = 1 núcleo)"); ax[3].set_xlabel("minutos"); ax[3].legend(loc="upper left")
    if "pg_active" in tl:
        a3 = ax[3].twinx(); a3.plot(x, tl.pg_active, color="#8250df", ls="--", alpha=.6, label="conexiones PG activas"); a3.legend(loc="upper right")
    # sombrear fases
    colors = {"ramp": "#eaeef2", "steady": "#ffffff", "stress": "#fff8c5", "recovery": "#dafbe1"}
    ph = tl.phase.ffill()
    for p, grp in ph.groupby((ph != ph.shift()).cumsum()):
        name = grp.iat[0]
        if name in colors and name != "steady":
            for a in ax:
                a.axvspan(grp.index.min() / 60, (grp.index.max() + BUCKET) / 60, color=colors[name], alpha=.6, zorder=0)
            ax[0].text(grp.index.min() / 60, ax[0].get_ylim()[1] * .92, name, fontsize=9, color="#57606a")
    for a in ax:
        a.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(d / "timeline.png", dpi=130)
    plt.close(fig)


def per_minute(df: pd.DataFrame) -> pd.DataFrame:
    m = df.assign(minute=df.t // 60)
    dur = m[m.metric_name == "http_req_duration"].groupby("minute").metric_value
    out = pd.DataFrame({
        "req/s logradas": (m[m.metric_name == "http_reqs"].groupby("minute").size() / 60).round(1),
        "dropped/s": (m[m.metric_name == "dropped_iterations"].groupby("minute").metric_value.sum() / 60).round(2),
        "p95_ms": dur.quantile(.95).round(1), "p99_ms": dur.quantile(.99).round(1),
        "error_%": (100 * m[m.metric_name == "http_req_failed"].groupby("minute").metric_value.mean()).round(2),
        "fase": m.groupby("minute").phase.agg(lambda s: s[s != "-"].mode().iat[0] if (s != "-").any() else "-"),
    })
    out["dropped/s"] = out["dropped/s"].fillna(0)
    out["ofrecidas/s≈"] = (out["req/s logradas"] + out["dropped/s"]).round(1)
    return out


def main(d: Path):
    df = load_raw(d)
    pt = phase_table(df)
    tl = timeline(df, d)
    tl.round(2).to_csv(d / "timeline.csv")
    plot(tl, d, f"{d.parent.name} / {d.name}")
    pm = per_minute(df)
    res_cols = [c for c in ["cpu_api", "cpu_db", "cpu_k6", "mem_api_mib", "mem_db_mib", "pg_active"] if c in tl]
    res = tl[res_cols].agg(["mean", "max"]).round(1) if res_cols else pd.DataFrame()
    md = [f"# Análisis de {d}", "",
          "Calculado desde `raw.csv.gz` (todas las muestras) y `resources.csv`. Ventanas de 10 s en `timeline.csv`.", "",
          "## Por fase y endpoint", "", pt.to_markdown(index=False), "",
          "## Recursos (promedio y máximo durante la corrida)", "", res.to_markdown() if len(res) else "_sin resources.csv_", "",
          "## Por minuto (ofrecidas ≈ logradas + dropped)", "", pm.to_markdown(), ""]
    (d / "analysis.md").write_text("\n".join(md), encoding="utf-8")
    print(pt.to_string(index=False))
    print(f"\n✔ {d}/analysis.md · timeline.png · timeline.csv")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))

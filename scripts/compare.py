#!/usr/bin/env python3
"""Compara corridas ANTES vs DESPUÉS (una o varias repeticiones de cada lado).

Uso:
  python3 scripts/compare.py --antes results/antes/load-A results/antes/load-B \
                             --despues results/despues/load-C results/despues/load-D \
                             --fase steady --salida results/comparacion-load

Con 2+ repeticiones por lado informa media, desviación estándar y coeficiente de variación,
para distinguir una mejora real de la variación normal entre corridas.
"""
import argparse
from pathlib import Path

import pandas as pd

from analyze import load_raw, phase_table

METRICS = ["req/s", "p50_ms", "p95_ms", "p99_ms", "error_%"]


def collect(dirs, fase):
    frames = []
    for i, d in enumerate(dirs, 1):
        pt = phase_table(load_raw(Path(d)))
        pt = pt[pt.fase == fase].assign(corrida=i, carpeta=str(d))
        frames.append(pt)
    return pd.concat(frames)


def summarize(df):
    g = df.groupby("endpoint")[METRICS]
    out = g.mean().round(2)
    if df.corrida.nunique() > 1:
        sd = g.std().round(2)
        for m in ["p95_ms", "p99_ms"]:
            out[f"{m}_sd"] = sd[m]
            out[f"{m}_cv%"] = (100 * sd[m] / out[m]).round(1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--antes", nargs="+", required=True)
    ap.add_argument("--despues", nargs="+", required=True)
    ap.add_argument("--fase", default="steady", help="steady (carga), stress, recovery")
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    out = Path(a.salida); out.mkdir(parents=True, exist_ok=True)

    raw_a, raw_d = collect(a.antes, a.fase), collect(a.despues, a.fase)
    A, D = summarize(raw_a), summarize(raw_d)
    order = [e for e in ["(todos)", "availability", "list", "create"] if e in A.index]
    cmp_ = pd.DataFrame(index=order)
    for m in ["p50_ms", "p95_ms", "p99_ms", "error_%", "req/s"]:
        cmp_[f"{m} antes"] = A.loc[order, m]
        cmp_[f"{m} después"] = D.loc[order, m]
        if m.endswith("_ms"):
            cmp_[f"{m} Δ%"] = (100 * (D.loc[order, m] - A.loc[order, m]) / A.loc[order, m]).round(1)

    md = [f"# Comparación antes/después — fase `{a.fase}`", "",
          f"Antes: {len(a.antes)} corrida(s) · Después: {len(a.despues)} corrida(s). Valores = media entre corridas.", "",
          cmp_.to_markdown(), "", "## Detalle ANTES", "", A.to_markdown(), "", "## Detalle DESPUÉS", "", D.to_markdown(), "",
          "## Corridas usadas", ""] + [f"- antes: `{d}`" for d in a.antes] + [f"- después: `{d}`" for d in a.despues]
    (out / "compare.md").write_text("\n".join(md), encoding="utf-8")
    raw_a.assign(lado="antes").to_csv(out / "por_corrida.csv", index=False)
    raw_d.assign(lado="despues").to_csv(out / "por_corrida.csv", mode="a", header=False, index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
    w = 0.38
    for ax, m in zip(axs, ["p95_ms", "p99_ms"]):
        xs = range(len(order))
        ax.bar([x - w / 2 for x in xs], A.loc[order, m], w, label="antes", color="#bf8700",
               yerr=A.loc[order, f"{m}_sd"] if f"{m}_sd" in A else None, capsize=3)
        ax.bar([x + w / 2 for x in xs], D.loc[order, m], w, label="después", color="#1f6feb",
               yerr=D.loc[order, f"{m}_sd"] if f"{m}_sd" in D else None, capsize=3)
        ax.set_xticks(list(xs)); ax.set_xticklabels(order); ax.set_ylabel("ms"); ax.set_title(f"{m} — fase {a.fase}")
        ax.grid(axis="y", alpha=.3); ax.legend()
    fig.tight_layout(); fig.savefig(out / "compare.png", dpi=130)
    print(cmp_.to_string())
    print(f"\n✔ {out}/compare.md · compare.png · por_corrida.csv")


if __name__ == "__main__":
    main()

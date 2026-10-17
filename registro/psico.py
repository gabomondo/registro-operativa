"""Costo de la psicología: cruza lo que anotás en cada operación (estado emocional,
tranquilidad, movimiento del SL, checklist) con el resultado en dólares. Es una
correlación sobre tus propios datos, no una causa: con pocos trades no concluye."""

from .stats import op_check_counts

MUESTRA_MINIMA = 5


def _agr(label, ops):
    ps = [float(o["profit"]) for o in ops]
    n = len(ps)
    return dict(label=label, n=n, neto=sum(ps), prom=(sum(ps) / n if n else 0.0),
                wr=(100.0 * sum(1 for x in ps if x > 0) / n if n else 0.0))


def _emo(o):
    e = o.get("emo")
    if not e:
        return None
    return "Bajo (1-2)" if e <= 2 else ("Medio (3)" if e == 3 else "Alto (4-5)")


def _tranq(o):
    return o.get("tranquilo") or None


def _movsl(o):
    return o.get("mov_sl") or None


def _chk(o):
    n, tot = op_check_counts(o)
    if not tot:
        return None
    return "Completo" if n == tot else "Incompleto"


# factor -> (titulo, función, etiquetas de "mal estado", orden de los grupos)
FACTORES = [
    ("emo", "Estado emocional", _emo, {"Bajo (1-2)"}, ["Bajo (1-2)", "Medio (3)", "Alto (4-5)"]),
    ("tranquilo", "¿Operaste tranquilo?", _tranq, {"No"}, ["Sí", "Más o menos", "No"]),
    ("mov_sl", "Movimiento del SL", _movsl, {"Sí (en contra)"}, ["No", "Sí (a favor)", "Sí (en contra)"]),
    ("chk", "Checklist", _chk, {"Incompleto"}, ["Completo", "Incompleto"]),
]


def analizar(rows):
    """Lista de factores con datos. Cada uno: clave, titulo, grupos[{label,n,neto,prom,wr,mala}],
    n_mala, neto_mala, prom_ref (promedio por trade del resto), costo (USD estimado:
    lo que rinde de menos cada trade en mal estado respecto del resto, x cantidad;
    0 si no rinde peor) y chica (True si la muestra es chica)."""
    ops = [o for o in rows if o.get("profit") is not None]
    out = []
    for clave, titulo, fn, malas, orden in FACTORES:
        g = {}
        for o in ops:
            k = fn(o)
            if k is not None:
                g.setdefault(k, []).append(o)
        if not g:
            continue
        grupos = []
        for k in sorted(g, key=lambda x: orden.index(x) if x in orden else 99):
            d = _agr(k, g[k]); d["mala"] = k in malas
            grupos.append(d)
        mala = [o for k in malas for o in g.get(k, [])]
        resto = [o for k, v in g.items() if k not in malas for o in v]
        n_mala = len(mala)
        neto_mala = sum(float(o["profit"]) for o in mala)
        prom_ref = (sum(float(o["profit"]) for o in resto) / len(resto)) if resto else None
        prom_mala = neto_mala / n_mala if n_mala else None
        costo = 0.0
        if n_mala and prom_ref is not None and prom_mala < prom_ref:
            costo = (prom_ref - prom_mala) * n_mala
        out.append(dict(clave=clave, titulo=titulo, grupos=grupos, n_mala=n_mala,
                        neto_mala=neto_mala, prom_ref=prom_ref, costo=costo,
                        chica=(n_mala < MUESTRA_MINIMA or len(resto) < MUESTRA_MINIMA)))
    return out


def total_costo(factores):
    """Costo del factor más caro (no se suman: los trades se pisan entre factores)."""
    return max((f["costo"] for f in factores if not f["chica"]), default=0.0)

"""Métricas de riesgo y consistencia que complementan a analisis.resumen():
drawdown máximo, rachas, costos y duración. Funciones puras sobre db_all()."""

from datetime import datetime


def _validas(rows):
    ops = [o for o in rows if o.get("profit") is not None and o.get("fecha")]
    ops.sort(key=lambda o: (o["fecha"], o.get("hora") or ""))
    return ops


def curva(rows):
    """Equity acumulada trade a trade: [(fecha, hora, acumulado)]."""
    acc, out = 0.0, []
    for o in _validas(rows):
        acc += float(o["profit"])
        out.append((o["fecha"], o.get("hora") or "", acc))
    return out


def drawdown(valores):
    """Drawdown máximo (USD, positivo) de una serie acumulada que arranca en 0.
    Devuelve dict(max, i_pico, i_valle, actual). Los índices son de `valores`
    (-1 si no hubo caída o si el pico fue el punto de partida)."""
    pico, i_pico = 0.0, -1
    mx, mi_pico, mi_valle = 0.0, -1, -1
    for i, v in enumerate(valores):
        if v > pico:
            pico, i_pico = v, i
        caida = pico - v
        if caida > mx:
            mx, mi_pico, mi_valle = caida, i_pico, i
    actual = pico - valores[-1] if valores else 0.0
    return dict(max=mx, i_pico=mi_pico, i_valle=mi_valle, actual=actual)


def rachas(profits):
    """Mayor racha ganadora y perdedora (cantidad y USD). Los trades en 0 no cortan ni suman."""
    mejor_g = dict(n=0, usd=0.0)
    mejor_p = dict(n=0, usd=0.0)
    cur_n, cur_usd, signo = 0, 0.0, 0
    for p in profits:
        s = 1 if p > 0 else (-1 if p < 0 else 0)
        if s == 0:
            continue
        if s == signo:
            cur_n += 1
            cur_usd += p
        else:
            signo, cur_n, cur_usd = s, 1, p
        destino = mejor_g if s > 0 else mejor_p
        if cur_n > destino["n"] or (cur_n == destino["n"] and abs(cur_usd) > abs(destino["usd"])):
            destino["n"], destino["usd"] = cur_n, cur_usd
    return mejor_g, mejor_p


def _minutos(o):
    """Duración en minutos si el trade trae hora de cierre (importados)."""
    fin, ini = o.get("hora_fin"), o.get("hora")
    if not fin or not ini or not o.get("fecha"):
        return None
    try:
        t_ini = datetime.strptime(f"{o['fecha']} {ini[:5]}", "%Y-%m-%d %H:%M")
        t_fin = datetime.strptime(str(fin)[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    m = (t_fin - t_ini).total_seconds() / 60.0
    return m if m >= 0 else None


def extra(rows):
    """Métricas adicionales. None si no hay operaciones."""
    ops = _validas(rows)
    if not ops:
        return None
    ps = [float(o["profit"]) for o in ops]
    acum, a = [], 0.0
    for p in ps:
        a += p
        acum.append(a)
    dd = drawdown(acum)
    rg, rp = rachas(ps)
    neto = acum[-1]
    i_mejor = max(range(len(ps)), key=lambda i: ps[i])
    i_peor = min(range(len(ps)), key=lambda i: ps[i])
    com = [float(o["comision"]) for o in ops if o.get("comision") is not None]
    bruto = [float(o["bruto"]) for o in ops if o.get("bruto") is not None]
    dur = [m for m in (_minutos(o) for o in ops) if m is not None]
    f_pico = ops[dd["i_pico"]]["fecha"] if dd["i_pico"] >= 0 else None
    f_valle = ops[dd["i_valle"]]["fecha"] if dd["i_valle"] >= 0 else None
    return dict(
        n=len(ps),
        dd_max=dd["max"], dd_actual=dd["actual"], dd_desde=f_pico, dd_hasta=f_valle,
        recovery=(neto / dd["max"]) if dd["max"] > 0 and neto > 0 else None,
        racha_gan=rg, racha_perd=rp,
        mejor_trade=dict(usd=ps[i_mejor], fecha=ops[i_mejor]["fecha"]),
        peor_trade=dict(usd=ps[i_peor], fecha=ops[i_peor]["fecha"]),
        comisiones=sum(com) if com else None, n_con_comision=len(com),
        pct_comision_bruto=(100.0 * sum(com) / sum(bruto)
                            if com and bruto and len(bruto) == len(ps) and sum(bruto) > 0 else None),
        dur_prom_min=(sum(dur) / len(dur)) if dur else None, n_con_duracion=len(dur),
        pico_equity=max([0.0] + acum))


def fmt_duracion(minutos):
    if minutos is None:
        return "—"
    m = int(round(minutos))
    if m < 60:
        return f"{m} min"
    return f"{m // 60} h {m % 60:02d} min"

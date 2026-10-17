"""Cálculo del Portfolio (todas las cuentas juntas): capital, reparto, salud, cuándo y día a día.
Funciones puras sobre las filas de db_all() y las fichas de db_cuentas(); sin interfaz.

El capital inicial de cada cuenta es opcional: lo que depende de él (balance, peso, % de retorno,
gestión de riesgo) queda en None si falta, y la nota de salud se promedia con lo que sí se puede calcular."""
import math
from datetime import date, datetime, timedelta

from . import analisis as A
from . import metricas as M
from .cuentas import clave as clave_cuenta, titulo as titulo_cuenta

DIAS_CORTOS = ["L", "M", "X", "J", "V", "S", "D"]
SIN_CUENTA = ("", "")


def _p(o):
    v = o.get("profit")
    return float(v) if v is not None else None


def _validas(rows):
    return [o for o in rows if _p(o) is not None and o.get("fecha")]


def _clave_op(o):
    return (o.get("empresa") or "", o.get("cuenta") or "")


def _por_dia(ops):
    d = {}
    for o in ops:
        d[o["fecha"]] = d.get(o["fecha"], 0.0) + _p(o)
    return dict(sorted(d.items()))


def _diversificacion(pesos):
    """0 con todo en una cuenta, 100 con el peso repartido por igual (1 - HHI normalizado)."""
    pesos = [p for p in pesos if p > 0]
    n = len(pesos)
    if n <= 1:
        return 0.0
    tot = sum(pesos)
    hhi = sum((p / tot) ** 2 for p in pesos)
    return max(0.0, min(100.0, (1 - hhi) / (1 - 1 / n) * 100))


def _sharpe(diarios):
    """Rentabilidad diaria ajustada por riesgo, anualizada (252 días). No depende del capital."""
    if len(diarios) < 2:
        return None
    m = sum(diarios) / len(diarios)
    var = sum((x - m) ** 2 for x in diarios) / (len(diarios) - 1)
    if var <= 0:
        return None
    return m / math.sqrt(var) * math.sqrt(252)


def calcular(rows, cuentas, hoy=None):
    hoy = hoy or date.today()
    ops = _validas(rows)
    fichas = {clave_cuenta(c): c for c in cuentas}
    por_cta = {}
    for o in ops:
        por_cta.setdefault(_clave_op(o), []).append(o)
    claves = list(dict.fromkeys(list(fichas) + [k for k in por_cta if k != SIN_CUENTA] +
                                ([SIN_CUENTA] if SIN_CUENTA in por_cta else [])))

    lista = []
    for k in claves:
        f = fichas.get(k) or {"empresa": k[0], "cuenta": k[1]}
        cops = por_cta.get(k, [])
        ps = [_p(o) for o in cops]
        pnl = sum(ps)
        cap = f.get("capital_inicial")
        lista.append(dict(
            clave=k, titulo=titulo_cuenta(f) if k != SIN_CUENTA else "Sin cuenta", estado=f.get("estado"),
            tipo=f.get("tipo"), capital=cap, pnl=pnl, n=len(ps),
            balance=(cap + pnl) if cap else None,
            wr=(100.0 * sum(1 for x in ps if x > 0) / len(ps)) if ps else 0.0))
    cap_total = sum(c["capital"] for c in lista if c["capital"]) or None
    bal_total = sum(c["balance"] for c in lista if c["balance"] is not None) if cap_total else None
    base_peso = sum(c["balance"] for c in lista if c["balance"] is not None and c["balance"] > 0)
    for c in lista:
        c["peso"] = (100.0 * c["balance"] / base_peso) if (base_peso and c["balance"] is not None and c["balance"] > 0) else None
    lista.sort(key=lambda c: (-(c["balance"] if c["balance"] is not None else float("-inf")), -c["pnl"], c["titulo"].lower()))
    mejor = max((c for c in lista if c["n"]), key=lambda c: c["pnl"], default=None)
    for c in lista:
        c["mejor"] = c is mejor and len([x for x in lista if x["n"]]) > 1

    dias = _por_dia(ops)
    neto = sum(dias.values())
    # ---- curva diaria (consolidada); arranca en el capital inicial si se conoce
    acc, curva = 0.0, []
    for f, v in dias.items():
        acc += v
        curva.append((f, (cap_total or 0.0) + acc))
    valores = [v - (cap_total or 0.0) for _f, v in curva]
    dd = M.drawdown(valores)
    r = A.resumen(ops)
    # ---- hoy / semana / mes (sobre lo que haya en `rows`)
    lunes = (hoy - timedelta(days=hoy.weekday())).isoformat()
    mes0 = hoy.replace(day=1).isoformat()
    suma = lambda desde: sum(v for f, v in dias.items() if desde <= f <= hoy.isoformat())
    # ---- salud
    diarios = list(dias.values())
    consistencia = (100.0 * sum(1 for v in diarios if v > 0) / len(diarios)) if diarios else None
    riesgo = max(0.0, min(100.0, 100 - 5 * (100.0 * dd["max"] / cap_total))) if cap_total and diarios else None
    if all(c["balance"] is not None for c in lista if c["n"]) and any(c["n"] for c in lista):
        pesos = [c["balance"] for c in lista if c["n"]]
    else:
        pesos = [c["n"] for c in lista]
    diver = _diversificacion(pesos) if diarios else None
    pf = r["profit_factor"] if r else None
    if r and pf is None and r["neto"] > 0:
        rentab = 100.0
    else:
        rentab = min(100.0, pf * 50) if pf is not None else None
    partes = [x for x in (consistencia, riesgo, diver, rentab) if x is not None]
    nota = round(sum(partes) / len(partes)) if partes else None
    # ---- cuándo
    por_sem = {i: [] for i in range(7)}
    for f, v in dias.items():
        por_sem[datetime.strptime(f, "%Y-%m-%d").weekday()].append(v)
    sem = [dict(dia=DIAS_CORTOS[i], prom=(sum(v) / len(v)) if v else None, n=len(v)) for i, v in por_sem.items()]
    meses = {}
    for f, v in dias.items():
        meses[f[:7]] = meses.get(f[:7], 0.0) + v
    por_mes = [dict(mes=m, pnl=v, pct=(100.0 * v / cap_total) if cap_total else None)
               for m, v in sorted(meses.items())[-12:]]
    # ---- día a día (los más recientes primero)
    det = {}
    for o in ops:
        det.setdefault(o["fecha"], {}).setdefault(_clave_op(o), []).append(_p(o))
    nombres = {c["clave"]: c["titulo"] for c in lista}
    dia_a_dia = []
    for f in sorted(dias, reverse=True)[:14]:
        pc = sorted(((nombres.get(k, "Sin cuenta"), sum(v), len(v)) for k, v in det[f].items()), key=lambda t: -abs(t[1]))
        dia_a_dia.append(dict(fecha=f, neto=dias[f], n=sum(t[2] for t in pc), por_cuenta=pc))
    ps_all = [_p(o) for o in ops]
    conteo = dict(gan=sum(1 for x in ps_all if x > 0), tab=sum(1 for x in ps_all if x == 0),
                  per=sum(1 for x in ps_all if x < 0))
    return dict(
        n=len(ops), neto=neto, conteo=conteo, cuentas=lista, capital_inicial=cap_total, balance=bal_total,
        con_capital=sum(1 for c in lista if c["capital"]), n_cuentas=len(lista),
        retorno_pct=(100.0 * neto / cap_total) if cap_total else None,
        hoy=suma(hoy.isoformat()), semana=suma(lunes), mes=suma(mes0),
        curva=curva, dd_max=dd["max"], dd_pct=(100.0 * dd["max"] / cap_total) if cap_total else None,
        resumen=r, sharpe=_sharpe(diarios), dias_operados=len(diarios),
        salud=dict(nota=nota, consistencia=consistencia, riesgo=riesgo, diversificacion=diver, rentabilidad=rentab),
        por_dia_semana=sem, por_mes=por_mes, dia_a_dia=dia_a_dia)

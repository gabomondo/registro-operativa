"""Métricas de la pestaña Análisis: por día, por hora de entrada, por activo,
por lado y por día de la semana. Funciones puras sobre las filas de db_all()."""

from datetime import datetime

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _p(o):
    v = o.get("profit")
    return float(v) if v is not None else None


def _validas(rows):
    return [o for o in rows if _p(o) is not None and o.get("fecha")]


def _grupo(label, ops):
    ps = [_p(o) for o in ops]
    n = len(ps)
    wins = sum(1 for x in ps if x > 0)
    return dict(label=label, n=n, neto=sum(ps), wr=(100.0 * wins / n if n else 0.0),
                prom=sum(ps) / n if n else 0.0, mejor=max(ps), peor=min(ps))


def _agrupar(rows, clave, orden=None):
    g = {}
    for o in _validas(rows):
        k = clave(o)
        if k is None:
            continue
        g.setdefault(k, []).append(o)
    items = [_grupo(k, v) for k, v in g.items()]
    items.sort(key=orden or (lambda x: x["label"]))
    return items


def por_dia(rows):
    """Un renglón por día operado, del más nuevo al más viejo, con acumulado."""
    items = _agrupar(rows, lambda o: o["fecha"])
    items.sort(key=lambda x: x["label"])
    acum = 0.0
    for it in items:
        acum += it["neto"]
        it["acum"] = acum
        try:
            it["dia"] = DIAS[datetime.strptime(it["label"], "%Y-%m-%d").weekday()][:3]
        except ValueError:
            it["dia"] = ""
    items.reverse()
    return items


def por_hora(rows):
    def k(o):
        h = (o.get("hora") or "")[:2]
        return f"{h}:00" if h.isdigit() and len(h) == 2 else None
    return _agrupar(rows, k)


def por_activo(rows):
    return _agrupar(rows, lambda o: (o.get("activo") or "").strip() or None,
                    orden=lambda x: -abs(x["neto"]))


def por_lado(rows):
    return _agrupar(rows, lambda o: o.get("lado") or None)


def por_dia_semana(rows):
    def k(o):
        try:
            return datetime.strptime(o["fecha"], "%Y-%m-%d").weekday()
        except ValueError:
            return None
    items = _agrupar(rows, k)
    for it in items:
        it["label"] = DIAS[it["label"]]
    items.sort(key=lambda x: DIAS.index(x["label"]))
    return items


def resumen(rows):
    """Números de cabecera. Devuelve None si no hay operaciones."""
    ops = _validas(rows)
    if not ops:
        return None
    ps = [_p(o) for o in ops]
    gan = [x for x in ps if x > 0]
    per = [x for x in ps if x < 0]
    dias = por_dia(rows)
    prom_g = sum(gan) / len(gan) if gan else 0.0
    prom_p = sum(per) / len(per) if per else 0.0
    return dict(
        n=len(ps), neto=sum(ps), wr=100.0 * len(gan) / len(ps),
        expectativa=sum(ps) / len(ps),
        profit_factor=(sum(gan) / abs(sum(per))) if per else None,
        prom_ganador=prom_g, prom_perdedor=prom_p,
        payoff=(prom_g / abs(prom_p)) if per and gan else None,
        dias=len(dias), dias_verdes=sum(1 for d in dias if d["neto"] > 0),
        pct_dias_verdes=100.0 * sum(1 for d in dias if d["neto"] > 0) / len(dias),
        mejor_dia=max(dias, key=lambda d: d["neto"]),
        peor_dia=min(dias, key=lambda d: d["neto"]),
        prom_dia=sum(d["neto"] for d in dias) / len(dias),
        trades_por_dia=len(ps) / len(dias))


MIN_MUESTRA = 5


def _mejor_peor(items, minimo=MIN_MUESTRA):
    """(mejor, peor) por neto entre los grupos con muestra suficiente; None si no hay al menos 2."""
    ok = [i for i in items if i["n"] >= minimo]
    if len(ok) < 2:
        return None, None
    return max(ok, key=lambda i: i["neto"]), min(ok, key=lambda i: i["neto"])


def narrativa(rows, fm=lambda v: f"{v:+,.0f}"):
    """Lectura en palabras del período: lista de (título, texto). fm formatea un importe con signo.
    Solo saca conclusiones de grupos con >= MIN_MUESTRA trades."""
    r = resumen(rows)
    if not r:
        return []
    out = []
    pf = "sin pérdidas" if r["profit_factor"] is None else f"profit factor {r['profit_factor']:.2f}"
    out.append(("Resultado",
                f"{r['n']} trades en {r['dias']} días con un neto de {fm(r['neto'])}. "
                f"Ganaste el {r['wr']:.0f}% de los trades ({pf})"
                + (f" y tu ganador promedio es {r['payoff']:.1f} veces el perdedor." if r["payoff"] else ".")))
    out.append(("Ritmo",
                f"Operás {r['trades_por_dia']:.1f} trades por día y {r['dias_verdes']} de {r['dias']} días "
                f"cerraron en verde ({r['pct_dias_verdes']:.0f}%). Mejor día {r['mejor_dia']['label']} "
                f"({fm(r['mejor_dia']['neto'])}), día más flojo {r['peor_dia']['label']} ({fm(r['peor_dia']['neto'])})."))
    cuando = []
    for nombre, items in (("hora", por_hora(rows)), ("día", por_dia_semana(rows))):
        b, p = _mejor_peor(items)
        if b and b["label"] != p["label"]:
            cuando.append(f"Tu mejor {nombre} es {b['label']} ({fm(b['neto'])}, {b['n']} trades) y la más floja "
                          f"{p['label']} ({fm(p['neto'])}, {p['n']} trades).")
    out.append(("Cuándo", " ".join(cuando) or
                f"Todavía no hay {MIN_MUESTRA}+ trades por franja para sacar conclusiones."))
    que = []
    for nombre, items in (("activo", por_activo(rows)),
                          ("setup", _agrupar(rows, lambda o: o.get("tipo") or None))):
        b, p = _mejor_peor(items)
        if b and b["label"] != p["label"]:
            que.append(f"Mejor {nombre}: {b['label']} ({fm(b['neto'])}). Más flojo: {p['label']} ({fm(p['neto'])}).")
        else:
            ok = [i for i in items if i["n"] >= MIN_MUESTRA]
            if len(ok) == 1 and len(items) > 1:
                que.append(f"Tu {nombre} principal es {ok[0]['label']}: {ok[0]['n']} de "
                           f"{sum(i['n'] for i in items)} trades ({fm(ok[0]['neto'])}); el resto tiene muestra chica.")
    out.append(("Qué", " ".join(que) or
                f"Todavía no hay {MIN_MUESTRA}+ trades por activo o setup para comparar."))
    return out


def por_cuenta(rows, cuentas=()):
    """Un grupo por cuenta (empresa + cuenta), rotulado con el alias si existe; de mayor a menor neto."""
    from registro.cuentas import titulo
    fichas = {(c.get("empresa") or "", c.get("cuenta") or ""): c for c in cuentas}

    def k(o):
        clave = (o.get("empresa") or "", o.get("cuenta") or "")
        if clave == ("", ""):
            return None
        return titulo(fichas.get(clave) or dict(empresa=clave[0], cuenta=clave[1]))
    return _agrupar(rows, k, orden=lambda x: -x["neto"])

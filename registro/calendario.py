"""Calendario mensual de P&L: arma la grilla (semanas x días) con el neto de cada
día y el total de cada semana. Funciones puras, sin interfaz."""

import calendar
from datetime import date

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def resumen_dias(rows):
    """{'2026-10-14': {'neto': x, 'n': trades}} a partir de las filas de db_all()."""
    out = {}
    for o in rows:
        p, f = o.get("profit"), o.get("fecha")
        if p is None or not f:
            continue
        d = out.setdefault(f, {"neto": 0.0, "n": 0})
        d["neto"] += float(p)
        d["n"] += 1
    return out


def mes_anterior(y, m):
    return (y - 1, 12) if m == 1 else (y, m - 1)


def mes_siguiente(y, m):
    return (y + 1, 1) if m == 12 else (y, m + 1)


def grilla(y, m, dias):
    """dias = resumen_dias(...). Devuelve dict con:
    semanas: lista de {'celdas': [7 celdas], 'neto', 'n'};  celda = {'fecha','dia',
    'en_mes','neto','n'} (neto/n None si no se operó);  total, dias_op, verdes, rojos,
    con_finde (True si hubo trades sábado/domingo en el mes)."""
    cal = calendar.Calendar(firstweekday=0)
    semanas, total, n_tot, verdes, rojos, finde, dias_op = [], 0.0, 0, 0, 0, False, 0
    for sem in cal.monthdatescalendar(y, m):
        celdas, neto_s, n_s, hubo = [], 0.0, 0, False
        for d in sem:
            iso = d.isoformat()
            en_mes = d.month == m
            info = dias.get(iso) if en_mes else None
            c = {"fecha": iso, "dia": d.day, "en_mes": en_mes,
                 "neto": info["neto"] if info else None, "n": info["n"] if info else None}
            if info:
                neto_s += info["neto"]; n_s += info["n"]; hubo = True
                total += info["neto"]; n_tot += info["n"]; dias_op += 1
                if info["neto"] > 0: verdes += 1
                elif info["neto"] < 0: rojos += 1
                if d.weekday() >= 5: finde = True
            celdas.append(c)
        semanas.append({"celdas": celdas, "neto": neto_s if hubo else None,
                        "n": n_s if hubo else None})
    return {"anio": y, "mes": m, "titulo": f"{MESES[m - 1]} {y}", "semanas": semanas,
            "total": total, "n": n_tot, "dias_op": dias_op,
            "verdes": verdes, "rojos": rojos, "con_finde": finde}


def mes_actual_con_datos(dias):
    """Mes del último día operado (o el de hoy si no hay nada)."""
    if dias:
        y, m, _ = map(int, max(dias).split("-"))
        return y, m
    h = date.today()
    return h.year, h.month

"""Reporte semanal con reglas simples (sin IA): detecta patrones en las operaciones
de la semana y arma un resumen en texto, listo para leer o para pegar en Claude."""

from collections import defaultdict

from . import analisis as A
from . import psico
from .stats import op_check_counts

REVENGE_MIN = 10      # reentrada "apurada" tras una pérdida (minutos)


def _hm(s):
    try:
        h, m = (s or "").strip()[-5:].split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def _fmt(x):
    return f"{x:+,.0f}"


def _por_dia(ops):
    d = defaultdict(list)
    for o in ops:
        d[o["fecha"]].append(o)
    for v in d.values():
        v.sort(key=lambda o: o.get("hora") or "")
    return d


def _racha_max_perdidas(lista):
    mx = cur = 0
    for o in lista:
        if o["profit"] < 0:
            cur += 1; mx = max(mx, cur)
        else:
            cur = 0
    return mx


def hallazgos(rows, prev=None):
    """Lista de (nivel, texto): nivel 'bien' | 'alerta' | 'info'. Más importante primero."""
    ops = [o for o in rows if o.get("profit") is not None and o.get("fecha")]
    if not ops:
        return []
    out = []
    por_dia = _por_dia(ops)
    neto = sum(o["profit"] for o in ops)
    wins = sum(1 for o in ops if o["profit"] > 0)

    # 1) cómo cerró la semana vs la anterior
    if prev:
        pn = sum(o["profit"] for o in prev if o.get("profit") is not None)
        if prev and pn != neto:
            out.append(("info", f"Semana {_fmt(neto)} USD contra {_fmt(pn)} de la anterior."))

    # 2) mejor y peor día
    dias = sorted(((sum(o["profit"] for o in v), f) for f, v in por_dia.items()))
    if len(dias) >= 2:
        pe, me = dias[0], dias[-1]
        if me[0] > 0:
            out.append(("bien", f"Mejor día: {me[1]} ({_fmt(me[0])} USD)."))
        if pe[0] < 0:
            out.append(("alerta", f"Peor día: {pe[1]} ({_fmt(pe[0])} USD)."))

    # 3) sobreoperar: días con muchos más trades que el promedio y en rojo
    prom_n = len(ops) / len(por_dia)
    for f, v in sorted(por_dia.items()):
        n, pnl = len(v), sum(o["profit"] for o in v)
        if len(por_dia) >= 2 and n >= max(4, prom_n * 1.6) and pnl < 0:
            out.append(("alerta", f"{f}: {n} trades (tu promedio es {prom_n:.0f}) y cerró en {_fmt(pnl)}. Posible sobreoperación."))

    # 4) rachas de pérdidas
    for f, v in sorted(por_dia.items()):
        r = _racha_max_perdidas(v)
        if r >= 3:
            out.append(("alerta", f"{f}: {r} pérdidas seguidas. ¿Corresponde cortar el día ahí?"))

    # 5) reentrada apurada tras una pérdida
    rev = []
    for v in por_dia.values():
        for a, b in zip(v, v[1:]):
            if a["profit"] < 0:
                fin = _hm(a.get("hora_fin")) or _hm(a.get("hora"))
                ini = _hm(b.get("hora"))
                if fin is not None and ini is not None and 0 <= ini - fin <= REVENGE_MIN:
                    rev.append(b)
    if len(rev) >= 2:
        r_neto = sum(o["profit"] for o in rev)
        out.append(("alerta" if r_neto < 0 else "info",
                    f"{len(rev)} reentradas a menos de {REVENGE_MIN} min de una pérdida: {_fmt(r_neto)} USD en total."))

    # 6) psicología (el factor que más costó)
    fac = [f for f in psico.analizar(ops) if not f["chica"] and f["costo"] > 0]
    if fac:
        f = max(fac, key=lambda x: x["costo"])
        mala = next(g for g in f["grupos"] if g["mala"])
        prom_m = f["neto_mala"] / f["n_mala"]
        out.append(("alerta", f"{f['titulo']} — «{mala['label']}»: {f['n_mala']} trades, {_fmt(f['neto_mala'])} USD "
                              f"({_fmt(prom_m)} por trade contra {_fmt(f['prom_ref'])} en el resto). "
                              f"Diferencia estimada: {f['costo']:,.0f} USD."))

    # 7) mejor y peor hora de entrada / setup (solo con muestra decente)
    horas = [h for h in A.por_hora(ops) if h["n"] >= 3]
    if len(horas) >= 2:
        mh, ph = max(horas, key=lambda h: h["neto"]), min(horas, key=lambda h: h["neto"])
        if mh["neto"] > 0:
            out.append(("bien", f"Tu mejor hora de entrada: {mh['label']} ({_fmt(mh['neto'])} USD en {mh['n']} trades)."))
        if ph["neto"] < 0 and ph is not mh:
            out.append(("alerta", f"Tu peor hora: {ph['label']} ({_fmt(ph['neto'])} USD en {ph['n']} trades)."))
    setups = [s for s in A._agrupar(ops, lambda o: o.get("tipo") or None) if s["n"] >= 3]
    if len(setups) >= 2:
        ms, ps = max(setups, key=lambda s: s["neto"]), min(setups, key=lambda s: s["neto"])
        if ms["neto"] > 0:
            out.append(("bien", f"Setup que mejor te funcionó: {ms['label']} ({_fmt(ms['neto'])} USD, {ms['wr']:.0f}% win)."))
        if ps["neto"] < 0:
            out.append(("alerta", f"Setup que más te costó: {ps['label']} ({_fmt(ps['neto'])} USD en {ps['n']} trades)."))

    # 8) disciplina del checklist
    con_chk = [o for o in ops if op_check_counts(o)[1] > 0]
    if len(con_chk) >= 3:
        full = sum(1 for o in con_chk if op_check_counts(o)[0] == op_check_counts(o)[1])
        pct = 100 * full / len(con_chk)
        out.append(("bien" if pct >= 80 else "alerta",
                    f"Checklist completo en {pct:.0f}% de los trades ({full}/{len(con_chk)})."))

    if wins == 0 and len(ops) >= 3:
        out.insert(0, ("alerta", "Ningún trade ganador esta semana."))
    return out


def texto_para_claude(rows, titulo, prev=None, notas=None):
    """Resumen en texto plano (para pegar en un chat con Claude y pedir feedback)."""
    ops = [o for o in rows if o.get("profit") is not None and o.get("fecha")]
    r = A.resumen(ops)
    L = [f"Resumen de mi operativa — {titulo}", ""]
    if not r:
        L.append("Sin operaciones en el período.")
    else:
        pf = "—" if r["profit_factor"] is None else f"{r['profit_factor']:.2f}"
        L += [f"- Neto: {_fmt(r['neto'])} USD en {r['n']} trades, {r['dias']} días operados",
              f"- Win rate: {r['wr']:.0f}% | Profit factor: {pf} | Expectativa: {r['expectativa']:+.1f} USD/trade",
              f"- Promedio ganador {_fmt(r['prom_ganador'])} / perdedor {_fmt(r['prom_perdedor'])}",
              f"- Mejor día {_fmt(r['mejor_dia']['neto'])} ({r['mejor_dia']['label']}), "
              f"peor día {_fmt(r['peor_dia']['neto'])} ({r['peor_dia']['label']})", ""]
        L.append("Por día:")
        for d in reversed(A.por_dia(ops)):
            L.append(f"  {d['label']} {d['dia']}: {_fmt(d['neto'])} USD, {d['n']} trades, {d['wr']:.0f}% win")
        h = hallazgos(ops, prev)
        if h:
            L += ["", "Patrones que detectó mi diario:"] + [f"- {t}" for _n, t in h]
    if notas:
        L += ["", "Mis notas:"] + [f"  {f}: {t}" for f, t in notas]
    L += ["", "Pedido: analizá mi semana como un coach de trading. Decime qué hice bien, "
              "qué error se repite y una sola regla concreta para la semana que viene."]
    return "\n".join(L)

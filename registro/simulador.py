"""Simulador "¿y si?": aplica reglas hipotéticas sobre tus trades reales y compara
el resultado. Es un ejercicio sobre el pasado (no considera que con otras reglas
habrías operado distinto), pero muestra cuánto pesan tus hábitos."""

from datetime import datetime

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _hm(s):
    """'HH:MM' -> minutos desde medianoche (None si no se puede)."""
    try:
        h, m = (s or "").strip()[:5].split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def _wd(fecha):
    try:
        return datetime.strptime(fecha, "%Y-%m-%d").weekday()
    except (ValueError, TypeError):
        return None


def simular(rows, reglas):
    """reglas (todas opcionales):
      max_perdidas   int   - en el día, no operar más después de N trades perdedores
      max_trades     int   - tope de trades por día
      perdida_dia    float - cortar el día al llegar a -X USD
      meta_dia       float - cortar el día al llegar a +X USD
      hora_limite    'HH:MM' - no abrir trades desde esa hora
      emo_min        int   - saltear trades con estado emocional menor a N (si estaba cargado)
      sin_dias       [0-6] - días de la semana que no operás (0 = lunes)
    Devuelve dict: base, nuevo, delta, n_base, n_nuevo, quitados[ops], curva_base,
    curva_nueva (acumulados por trade, en orden cronológico)."""
    ops = [o for o in rows if o.get("profit") is not None and o.get("fecha")]
    ops.sort(key=lambda o: (o["fecha"], o.get("hora") or ""))
    lim = _hm(reglas.get("hora_limite")) if reglas.get("hora_limite") else None
    emo_min = reglas.get("emo_min")
    sin_dias = set(reglas.get("sin_dias") or [])

    quitados, mantenidos, alineada, acc = [], [], [], 0.0
    dia_actual, n_dia, perd_dia, pnl_dia, cortado = None, 0, 0, 0.0, False
    for o in ops:
        if o["fecha"] != dia_actual:
            dia_actual, n_dia, perd_dia, pnl_dia, cortado = o["fecha"], 0, 0, 0.0, False
        p = float(o["profit"])
        omitir = cortado
        if not omitir and _wd(o["fecha"]) in sin_dias:
            omitir = True
        if not omitir and lim is not None:
            h = _hm(o.get("hora"))
            if h is not None and h >= lim:
                omitir = True
        if not omitir and emo_min and o.get("emo") and o["emo"] < emo_min:
            omitir = True
        if not omitir and reglas.get("max_trades") and n_dia >= reglas["max_trades"]:
            omitir = True
        if omitir:
            quitados.append(o)
            alineada.append(acc)
            continue
        mantenidos.append(o)
        acc += p
        alineada.append(acc)
        n_dia += 1
        pnl_dia += p
        if p < 0:
            perd_dia += 1
        if reglas.get("max_perdidas") and perd_dia >= reglas["max_perdidas"]:
            cortado = True
        if reglas.get("perdida_dia") and pnl_dia <= -abs(reglas["perdida_dia"]):
            cortado = True
        if reglas.get("meta_dia") and pnl_dia >= abs(reglas["meta_dia"]):
            cortado = True

    def curva(lista):
        acc, out = 0.0, []
        for x in lista:
            acc += float(x["profit"]); out.append(acc)
        return out

    base = sum(float(o["profit"]) for o in ops)
    nuevo = sum(float(o["profit"]) for o in mantenidos)
    return dict(base=base, nuevo=nuevo, delta=nuevo - base, n_base=len(ops),
                n_nuevo=len(mantenidos), quitados=quitados,
                curva_base=curva(ops), curva_nueva=curva(mantenidos),
                curva_alineada=alineada)


def hay_reglas(reglas):
    return any(reglas.get(k) for k in ("max_perdidas", "max_trades", "perdida_dia",
                                       "meta_dia", "hora_limite", "emo_min", "sin_dias"))


def explicar_sin_efecto(rows, reglas):
    """Texto para cuando las reglas no sacan ningún trade: dice por qué, para que el
    usuario no piense que el simulador no responde."""
    ops = [o for o in rows if o.get("profit") is not None and o.get("fecha")]
    por_dia = {}
    for o in ops:
        por_dia[o["fecha"]] = por_dia.get(o["fecha"], 0) + 1
    max_dia = max(por_dia.values()) if por_dia else 0
    por_dia_activas = any(reglas.get(k) for k in ("max_perdidas", "max_trades", "perdida_dia", "meta_dia"))
    otras = any(reglas.get(k) for k in ("hora_limite", "emo_min", "sin_dias"))
    partes = ["Ningún trade del período rompe estas reglas, por eso no cambia nada."]
    if por_dia_activas:
        if max_dia <= 1:
            partes.append("Las reglas por día (pérdidas, cantidad, USD) actúan sobre el 2.º trade del día en adelante, "
                          "y en este período tenés como máximo 1 trade por día.")
        else:
            partes.append(f"Las reglas por día cortan después de que se cumple la condición; en este período tu día "
                          f"más cargado tuvo {max_dia} trades y ninguno llegó a activarlas.")
    if otras:
        partes.append("Las reglas de hora, estado emocional y días sí aplican desde el primer trade del día; "
                      "probá con valores más exigentes.")
    return " ".join(partes)

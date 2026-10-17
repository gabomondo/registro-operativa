"""Estadísticas agregadas (alimentan la barra de KPIs y la revisión). Sin UI ni base."""

from .constantes import CHECK_KEYS
import json


def op_check_data(o):
    """Devuelve el dict {item_id: 0/1} tildado en esta operación.
    Cae a las columnas chk_* si por algún motivo no hay chk_data."""
    raw = o.get("chk_data") if hasattr(o, "get") else o["chk_data"]
    if raw:
        try:
            d = json.loads(raw)
            if isinstance(d, dict):
                return {k: int(v or 0) for k, v in d.items()}
        except Exception:
            pass
    # fallback legacy
    return {k: int((o[k] if k in o.keys() else 0) or 0) for k in CHECK_KEYS} \
        if hasattr(o, "keys") else {k: int(o.get(k) or 0) for k in CHECK_KEYS}


def op_check_counts(o):
    """(cumplidos, total) para una operación, según SU plantilla.
    El total sale del número de ítems que tenía tildables esa op."""
    data = op_check_data(o)
    if not data:
        return (0, 0)
    n = sum(1 for v in data.values() if v)
    return (n, len(data))


def op_check_full(o):
    """True si la op cumplió TODOS los ítems de su plantilla."""
    n, tot = op_check_counts(o)
    return tot > 0 and n == tot


def compute_stats(rows):
    """Resumen defensivo sobre una lista de operaciones (dicts)."""
    n = len(rows)
    if not n:
        return dict(n=0, pnl=0.0, wr=0, wins=0, losses=0, streak=0,
                    streak_sign=0, chk_pct=0, chk_n=0, avg_emo=None, best=0.0, worst=0.0)
    pnl = sum(o.get("profit") or 0 for o in rows)
    wins = sum(1 for o in rows if (o.get("profit") or 0) > 0)
    losses = sum(1 for o in rows if (o.get("profit") or 0) < 0)
    wr = round(wins / n * 100)
    # racha actual: recorre por fecha+hora, del más nuevo al más viejo
    ordered = sorted(rows, key=lambda o: (o.get("fecha") or "", o.get("hora") or ""))
    streak, streak_sign = 0, 0
    for o in reversed(ordered):
        p = o.get("profit") or 0
        s = 1 if p > 0 else (-1 if p < 0 else 0)
        if s == 0:
            continue
        if streak == 0:
            streak_sign = s; streak = 1
        elif s == streak_sign:
            streak += 1
        else:
            break
    # disciplina: % de ops que cumplieron el check COMPLETO de su propia plantilla
    # (solo cuentan las ops que tenían checklist: las importadas no lo traen)
    con_chk = [o for o in rows if op_check_counts(o)[1] > 0]
    chk_n = len(con_chk)
    full = sum(1 for o in con_chk if op_check_full(o))
    chk_pct = round(full / chk_n * 100) if chk_n else 0
    emos = [o["emo"] for o in rows if o.get("emo")]
    avg_emo = sum(emos) / len(emos) if emos else None
    profits = [o.get("profit") or 0 for o in rows]
    return dict(n=n, pnl=pnl, wr=wr, wins=wins, losses=losses,
                streak=streak, streak_sign=streak_sign, chk_pct=chk_pct, chk_n=chk_n,
                avg_emo=avg_emo, best=max(profits), worst=min(profits))

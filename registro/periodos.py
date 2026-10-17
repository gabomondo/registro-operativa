"""Períodos del rango global de fechas (sin tkinter): atajos tipo «Este mes» y rangos personalizados."""
from datetime import date, timedelta

TODO = "Todo el período"
PRESETS = ["Hoy", "Esta semana", "Este mes", "Últimos 30 días", "Mes pasado",
           "Últimos 3 meses", "Últimos 6 meses", "Año pasado", TODO]


def _restar_meses(d, n):
    m = d.month - 1 - n
    y, m = d.year + m // 12, m % 12 + 1
    ult = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(d.day, ult))


def rango(preset, hoy=None):
    """(desde, hasta) en ISO para un atajo, o None para «Todo el período». Semana de lunes a hoy."""
    hoy = hoy or date.today()
    if preset == "Hoy":
        d = h = hoy
    elif preset == "Esta semana":
        d, h = hoy - timedelta(days=hoy.weekday()), hoy
    elif preset == "Este mes":
        d, h = hoy.replace(day=1), hoy
    elif preset == "Últimos 30 días":
        d, h = hoy - timedelta(days=29), hoy
    elif preset == "Mes pasado":
        h = hoy.replace(day=1) - timedelta(days=1)
        d = h.replace(day=1)
    elif preset == "Últimos 3 meses":
        d, h = _restar_meses(hoy, 3) + timedelta(days=1), hoy
    elif preset == "Últimos 6 meses":
        d, h = _restar_meses(hoy, 6) + timedelta(days=1), hoy
    elif preset == "Año pasado":
        d, h = date(hoy.year - 1, 1, 1), date(hoy.year - 1, 12, 31)
    else:
        return None
    return d.isoformat(), h.isoformat()


def validar_rango(desde, hasta):
    """Valida lo escrito en el diálogo. Vacío en un extremo = abierto. Devuelve (desde, hasta) ISO o None
    si ambos están vacíos; ValueError con un mensaje claro si algo está mal."""
    d, h = (desde or "").strip(), (hasta or "").strip()
    try:
        d = date.fromisoformat(d).isoformat() if d else None
        h = date.fromisoformat(h).isoformat() if h else None
    except ValueError:
        raise ValueError("las fechas van como AAAA-MM-DD")
    if d and h and d > h:
        raise ValueError("«Desde» no puede ser posterior a «Hasta»")
    return None if not d and not h else (d, h)


def etiqueta(preset, fechas):
    """Texto del botón: el atajo, o «desde → hasta» si es un rango personalizado."""
    if preset:
        return preset
    if not fechas:
        return TODO
    d, h = fechas
    return f"{d or 'inicio'} → {h or 'hoy'}"


def desde_prefs(p, hoy=None):
    """Reconstruye (preset, fechas) desde lo guardado en ui_prefs. Los atajos se recalculan cada vez."""
    if isinstance(p, dict):
        if p.get("preset") in PRESETS and p["preset"] != TODO:
            return p["preset"], rango(p["preset"], hoy)
        if p.get("desde") or p.get("hasta"):
            try:
                f = validar_rango(p.get("desde"), p.get("hasta"))
            except ValueError:
                f = None
            if f:
                return None, f
    return TODO, None

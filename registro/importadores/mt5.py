"""MetaTrader 5: 'Informe de historial de operaciones' en HTML o en Excel (.xlsx), cuenta Hedge."""

import re

from .modelo import TradeImp, Lectura, ImportError_
from .util import num, fecha, filas_xlsx, leer_texto, sumar_horas
from .agrupar import agrupar_piezas

FMT = ["%Y.%m.%d %H:%M:%S"]
_TR = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
_TD = re.compile(r"<t([dh])\b([^>]*)>(.*?)</t[dh]>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_FECHA = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$")


def _celdas(tr):
    out = []
    for tipo, attrs, cont in _TD.findall(tr):
        if "hidden" in attrs.lower():
            continue
        out.append((tipo.lower(), re.sub(r"\s+", " ", _TAG.sub("", cont).replace("&nbsp;", " ")).strip()))
    return out


def _seccion(html, nombre):
    """Filas de datos de la sección `nombre` (hasta el siguiente encabezado de sección)."""
    rows = [_celdas(t) for t in _TR.findall(html)]
    filas, dentro = [], False
    for r in rows:
        if len(r) == 1 and r[0][0] == "h":
            dentro = r[0][1].lower() == nombre.lower()
            continue
        if dentro:
            filas.append([t for _, t in r])
    return filas


def _filas_xlsx(path):
    """(cuenta, filas de Positions, filas de Deals) de un informe de MT5 guardado como .xlsx."""
    # 14 columnas fijas (la última es el comentario de los deals); el Excel trae celdas vacías de más
    filas = [(f + [""] * 14)[:14] for f in filas_xlsx(path)]
    cuenta, secciones, actual = "", {}, None
    for f in filas:
        if not any(f):
            continue
        if f[0].lower().startswith("account") and not cuenta:
            m = re.search(r"\d+", " ".join(f[1:]))
            cuenta = m.group(0) if m else ""
        if f[0] in ("Positions", "Orders", "Deals", "Results") and not any(f[1:]):
            actual = f[0]
            secciones[actual] = []
            continue
        if actual:
            secciones[actual].append(f)
    return cuenta, secciones.get("Positions", []), secciones.get("Deals", [])


def es_informe_xlsx(path):
    """True si el Excel parece un informe de historial de MT5 (título + sección Positions)."""
    cuenta, pos, _ = _filas_xlsx(path)        # si no se puede abrir, el error llega tal cual al usuario
    return any(f and _FECHA.match(f[0]) for f in pos)


def _filas_html(path):
    html = leer_texto(path)
    cuenta = ""
    m = re.search(r"Account:.*?<b>\s*(\d+)", html, re.S | re.I)
    if m:
        cuenta = m.group(1)
    return cuenta, _seccion(html, "Positions"), _seccion(html, "Deals")


def leer(path, perfil):
    xlsx = path.lower().endswith((".xlsx", ".xlsm"))
    cuenta, pos_f, deals_f = _filas_xlsx(path) if xlsx else _filas_html(path)
    pos = [f for f in pos_f if f and _FECHA.match(f[0])]
    if not pos:
        raise ImportError_(
            "No encontré posiciones en este informe de MT5. Exportalo desde "
            "Historial de la cuenta → clic derecho → Informe → HTML (o Excel), con la cuenta en modo Hedge.")
    # motivo de cierre: comentario [sl]/[tp] del deal de salida
    motivos = {}
    for f in deals_f:
        if len(f) >= 14 and _FECHA.match(f[0]) and f[4].lower() == "out":
            c = f[-1].lower()
            motivos[(f[2], f[0], f[5], f[6])] = "SL" if "[sl" in c else "TP" if "[tp" in c else ""
    off = perfil.offset_horas.get("mt5", 0.0)
    piezas, malas = [], 0
    for f in pos:
        # Time, Position, Symbol, Type, Volume, Price, S/L, T/P, Time, Price, Commission, Swap, Profit
        if len(f) < 13:
            malas += 1
            continue
        t_ini, t_fin = fecha(f[0], FMT), fecha(f[8], FMT)
        vol, pe, ps = num(f[4]), num(f[5]), num(f[9])
        com, swap, profit = num(f[10]) or 0.0, num(f[11]) or 0.0, num(f[12])
        lado = f[3].lower()
        if not (t_ini and t_fin and vol and pe is not None and ps is not None
                and profit is not None and lado in ("buy", "sell")):
            malas += 1
            continue
        piezas.append(TradeImp(
            fuente="mt5", cuenta=cuenta or "MT5", ext_id=f[1], activo=f[2],
            lado="Long" if lado == "buy" else "Short", contratos=vol,
            t_ini=sumar_horas(t_ini, off), t_fin=sumar_horas(t_fin, off),
            precio_ini=pe, precio_fin=ps, bruto=profit,
            comision=-(com + swap),
            motivo=motivos.get((f[2], f[8], f[4], f[9]), "")))
    avisos = ["En MT5 'contratos' son lotes. El P&L viene en la moneda de la cuenta."]
    if malas:
        avisos.append(f"{malas} posición(es) no se pudieron leer y se omitieron.")
    if off:
        avisos.append(f"Se sumaron {off:+g} h a los horarios (Perfil → desfase MT5).")
    else:
        avisos.append("Los horarios son los del servidor del broker. Si difieren de tu hora, "
                      "ajustá el desfase MT5 en Perfil.")
    trades = agrupar_piezas(piezas, perfil.agrupar_segundos)
    return Lectura("MetaTrader 5 · Informe Excel" if xlsx else "MetaTrader 5 · Informe HTML", "mt5", trades, avisos, [cuenta or "MT5"])

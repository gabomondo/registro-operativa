"""MetaTrader 4: 'Statement' y 'Detailed Statement' en HTML (Historial de la cuenta → clic derecho →
Guardar como informe / Informe detallado). Los dos traen la misma tabla «Closed Transactions»."""

import re

from .modelo import TradeImp, Lectura, ImportError_
from .util import num, fecha, leer_texto, sumar_horas
from .agrupar import agrupar_piezas
from .mt5 import _celdas, _TR

FMT = ["%Y.%m.%d %H:%M:%S"]
_FECHA = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$")


def es_informe(texto):
    return "Closed Transactions" in texto and "Open Time" in texto and "Close Time" in texto


def _motivo(tipo, cierre, sl, tp):
    """MT4 no informa por qué se cerró: si el precio de cierre coincide con el SL o el TP, se asume eso."""
    if sl and round(cierre, 5) == round(sl, 5):
        return "SL"
    if tp and round(cierre, 5) == round(tp, 5):
        return "TP"
    return ""


def leer(path, perfil):
    html = leer_texto(path)
    m = re.search(r"Account:\s*(\d+)", html)
    cuenta = m.group(1) if m else ""
    filas, dentro = [], False
    for tr in _TR.findall(html):
        c = [t for _, t in _celdas(tr)]
        if len(c) == 1 and c[0].lower().startswith("closed transactions"):
            dentro = True
            continue
        if len(c) == 1 and c[0].lower().rstrip(":") in ("open trades", "working orders", "summary"):
            dentro = False
        if dentro and len(c) >= 14 and _FECHA.match(c[1]) and c[2].lower() in ("buy", "sell"):
            filas.append(c)
    if not filas:
        raise ImportError_(
            "No encontré operaciones cerradas en este informe de MT4. Exportalo desde Historial de la "
            "cuenta → clic derecho → Rango de fechas (todo el historial) → clic derecho → «Guardar como informe» "
            "(o «Guardar como informe detallado»).")
    off = perfil.offset_horas.get("mt4", perfil.offset_horas.get("mt5", 0.0))
    piezas, malas = [], 0
    for f in filas:
        # Ticket, Open Time, Type, Size, Item, Price, S/L, T/P, Close Time, Price, Commission, Taxes, Swap, Profit
        t_ini, t_fin = fecha(f[1], FMT), fecha(f[8], FMT)
        vol, pe, ps = num(f[3]), num(f[5]), num(f[9])
        sl, tp = num(f[6]) or 0.0, num(f[7]) or 0.0
        com, tax, swap, profit = (num(f[10]) or 0.0), (num(f[11]) or 0.0), (num(f[12]) or 0.0), num(f[13])
        if not (t_ini and t_fin and vol and pe is not None and ps is not None and profit is not None):
            malas += 1
            continue
        piezas.append(TradeImp(
            fuente="mt4", cuenta=cuenta or "MT4", ext_id=f[0], activo=f[4].upper(),
            lado="Long" if f[2].lower() == "buy" else "Short", contratos=vol,
            t_ini=sumar_horas(t_ini, off), t_fin=sumar_horas(t_fin, off),
            precio_ini=pe, precio_fin=ps, bruto=profit,
            comision=-(com + tax + swap), motivo=_motivo(f[2], ps, sl, tp)))
    avisos = ["En MT4 'contratos' son lotes. El P&L viene en la moneda de la cuenta.",
              "MT4 no dice por qué se cerró cada operación: se marca SL/TP solo si el precio de cierre coincide."]
    if malas:
        avisos.append(f"{malas} operación(es) no se pudieron leer y se omitieron.")
    if off:
        avisos.append(f"Se sumaron {off:+g} h a los horarios (Perfil → desfase MT4/MT5).")
    else:
        avisos.append("Los horarios son los del servidor del broker. Si difieren de tu hora, "
                      "ajustá el desfase MT4/MT5 en Perfil.")
    trades = agrupar_piezas(piezas, perfil.agrupar_segundos)
    return Lectura("MetaTrader 4 · Statement HTML", "mt4", trades, avisos, [cuenta or "MT4"])

"""Tradovate: Position_History.csv (fills emparejados)."""

import csv
import io

from .modelo import TradeImp, Lectura, ImportError_
from .util import num, fecha, raiz, comision_de, leer_texto, sumar_horas
from .agrupar import agrupar_piezas

FMT = ["%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%Y-%m-%d %H:%M:%S"]


def leer(path, perfil):
    filas = list(csv.DictReader(io.StringIO(leer_texto(path))))
    off = perfil.offset_horas.get("tradovate", 0.0)
    piezas, malas = [], 0
    for f in filas:
        tb, ts = fecha(f.get("Bought Timestamp"), FMT), fecha(f.get("Sold Timestamp"), FMT)
        q, pb, ps = num(f.get("Paired Qty")), num(f.get("Buy Price")), num(f.get("Sell Price"))
        pl = num(f.get("P/L"))
        if not (tb and ts and q and pb is not None and ps is not None):
            malas += 1
            continue
        largo = tb <= ts
        t_ini, t_fin = (tb, ts) if largo else (ts, tb)
        activo = (f.get("Contract") or "").strip()
        avisos = []
        com = comision_de(perfil, activo, q)
        if com is None:
            com = 0.0
            avisos.append("Sin comisión: el archivo no la trae y no hay valor en Perfil.")
        else:
            avisos.append("Comisión estimada con el valor de tu Perfil (el archivo no la trae).")
        piezas.append(TradeImp(
            fuente="tradovate", cuenta=(f.get("Account") or "").strip() or "Tradovate",
            ext_id=(f.get("Pair ID") or "").strip(), activo=raiz(activo),
            lado="Long" if largo else "Short", contratos=q,
            t_ini=sumar_horas(t_ini, off), t_fin=sumar_horas(t_fin, off),
            precio_ini=pb if largo else ps, precio_fin=ps if largo else pb,
            bruto=pl, comision=com, avisos=avisos))
    avisos = []
    if malas:
        avisos.append(f"{malas} fila(s) no se pudieron leer y se omitieron.")
    if off:
        avisos.append(f"Se sumaron {off:+g} h a los horarios (Perfil → desfase Tradovate).")
    trades = agrupar_piezas(piezas, perfil.agrupar_segundos)
    return Lectura("Tradovate · Position History", "tradovate", trades, avisos,
                   sorted({p.cuenta for p in piezas}))

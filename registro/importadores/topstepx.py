"""TopstepX: trades_export.csv (una fila por entrada)."""

import csv
import io
import re

from .modelo import TradeImp, Lectura
from .util import num, fecha, raiz, leer_texto
from .agrupar import agrupar_piezas

FMT = ["%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p"]


def _hora(s):
    # '10/13/2026 10:40:08 -03:00' -> hora de pared tal como la muestra la plataforma
    return fecha(re.sub(r"\s*[+-]\d{2}:\d{2}$", "", (s or "").strip()), FMT)


def leer(path, perfil):
    filas = list(csv.DictReader(io.StringIO(leer_texto(path))))
    piezas, malas = [], 0
    for f in filas:
        te, ts = _hora(f.get("EnteredAt")), _hora(f.get("ExitedAt"))
        q, pe, ps = num(f.get("Size")), num(f.get("EntryPrice")), num(f.get("ExitPrice"))
        pnl = num(f.get("PnL"))
        if not (te and ts and q and pe is not None and ps is not None):
            malas += 1
            continue
        piezas.append(TradeImp(
            fuente="topstepx", cuenta="TopstepX", ext_id=(f.get("Id") or "").strip(),
            activo=raiz(f.get("ContractName")),
            lado="Short" if (f.get("Type") or "").strip().lower().startswith("s") else "Long",
            contratos=q, t_ini=te, t_fin=ts, precio_ini=pe, precio_fin=ps,
            bruto=pnl, comision=abs(num(f.get("Fees")) or 0.0)))
    avisos = ["Costo = columna Fees (se asume que ya incluye Commissions). "
              "Verificalo con tu statement de Topstep."]
    if malas:
        avisos.append(f"{malas} fila(s) no se pudieron leer y se omitieron.")
    trades = agrupar_piezas(piezas, perfil.agrupar_segundos)
    return Lectura("TopstepX · trades_export", "topstepx", trades, avisos, ["TopstepX"])

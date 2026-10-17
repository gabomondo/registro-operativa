"""DeepCharts: export CSV de trades (separado por «;»): Ticket;Symbol;Type;Qty;Entry DT;Entry Price;
Exit DT;Exit Price;Profit;Commission;Net Profit."""

import csv
import io

from .modelo import TradeImp, Lectura, ImportError_
from .util import num, fecha, raiz, leer_texto
from .agrupar import agrupar_piezas

FMT = ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]
COLUMNAS = ("Ticket", "Symbol", "Type", "Qty", "Entry DT", "Entry Price", "Exit DT", "Exit Price", "Profit")


def es_export(primera_linea):
    p = primera_linea
    return "Entry DT" in p and "Exit DT" in p and "Net Profit" in p


def leer(path, perfil):
    texto = leer_texto(path)
    filas = list(csv.DictReader(io.StringIO(texto), delimiter=";"))
    if not filas or any(c not in filas[0] for c in COLUMNAS):
        raise ImportError_("El CSV de DeepCharts no tiene las columnas esperadas (" + ", ".join(COLUMNAS) + ").")
    piezas, malas = [], 0
    for f in filas:
        t_ini, t_fin = fecha(f.get("Entry DT"), FMT), fecha(f.get("Exit DT"), FMT)
        q, pe, ps, pl = num(f.get("Qty")), num(f.get("Entry Price")), num(f.get("Exit Price")), num(f.get("Profit"))
        lado = (f.get("Type") or "").strip().lower()
        if not (t_ini and t_fin and q and pe is not None and ps is not None and pl is not None
                and lado in ("long", "short")):
            malas += 1
            continue
        piezas.append(TradeImp(
            fuente="deepcharts", cuenta="DeepCharts", ext_id=(f.get("Ticket") or "").strip(),
            activo=raiz(f.get("Symbol")), lado="Long" if lado == "long" else "Short", contratos=q,
            t_ini=t_ini, t_fin=t_fin, precio_ini=pe, precio_fin=ps, bruto=pl,
            comision=abs(num(f.get("Commission")) or 0.0)))
    avisos = ["El export de DeepCharts no trae la cuenta: elegí la empresa y el tipo de cuenta arriba."]
    if malas:
        avisos.append(f"{malas} fila(s) no se pudieron leer y se omitieron.")
    trades = agrupar_piezas(piezas, perfil.agrupar_segundos)
    return Lectura("DeepCharts · CSV", "deepcharts", trades, avisos, ["DeepCharts"])

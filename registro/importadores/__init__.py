"""Importadores de trades: detectan el formato y devuelven trades en un modelo común."""

import os

from .modelo import TradeImp, Lectura, ImportError_
from .util import leer_texto
from . import nt8, mt4, mt5, tradovate, topstepx, deepcharts
from .agrupar import consolidar_cuentas

FORMATOS = ("NinjaTrader 8 (Executions u Orders), MetaTrader 4 (Statement HTML), "
            "MetaTrader 5 (informe HTML o Excel), Tradovate (Position History), TopstepX (trades_export) "
            "y DeepCharts (CSV)")


def _no_reconocido():
    raise ImportError_(f"No reconozco el formato de este archivo. Formatos soportados: {FORMATOS}.")


def detectar(path):
    """Devuelve 'nt8_exec' | 'nt8_ordenes' | 'mt4' | 'mt5' | 'tradovate' | 'topstepx' | 'deepcharts'."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        return "mt5" if mt5.es_informe_xlsx(path) else _no_reconocido()
    texto = leer_texto(path)
    cabeza = texto[:4000]
    if ext in (".htm", ".html") or "<html" in cabeza.lower() or "<table" in cabeza.lower():
        if mt4.es_informe(texto):
            return "mt4"
        if "Positions" in texto and ("Trade History" in texto or "Deals" in texto):
            return "mt5"
        raise ImportError_("Es un HTML, pero no parece un informe de historial de MT5.")
    primera = cabeza.lstrip("﻿").splitlines()[0] if cabeza.strip() else ""
    if deepcharts.es_export(primera):
        return "deepcharts"
    if "Position ID" in primera and "Paired Qty" in primera:
        return "tradovate"
    if "ContractName" in primera and "EnteredAt" in primera:
        return "topstepx"
    if "E/X" in primera and "Order ID" in primera:
        return "nt8_exec"
    if "Avg. price" in primera and "State" in primera:
        return "nt8_ordenes"
    _no_reconocido()


def leer(path, perfil):
    fmt = detectar(path)
    if fmt == "mt5":
        return mt5.leer(path, perfil)
    if fmt == "mt4":
        return mt4.leer(path, perfil)
    if fmt == "deepcharts":
        return deepcharts.leer(path, perfil)
    if fmt == "tradovate":
        return tradovate.leer(path, perfil)
    if fmt == "topstepx":
        return topstepx.leer(path, perfil)
    if fmt == "nt8_exec":
        return nt8.leer_ejecuciones(path, perfil)
    return nt8.leer_ordenes(path, perfil)


__all__ = ["leer", "detectar", "consolidar_cuentas", "TradeImp", "Lectura", "ImportError_"]

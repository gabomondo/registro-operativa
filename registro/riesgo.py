"""Calculadora de riesgo (tamaño de posición). Lógica pura, sin interfaz.

Futuros: especificaciones fijadas por CME (verificadas contra una tabla de un FCM, oct-2026).
Forex: valor del pip por fórmula (cuenta en USD). Otros CFD: los carga el usuario, porque
el tamaño de contrato lo define cada broker."""

import math

# símbolo: (nombre, grupo, USD por punto/unidad de precio, tamaño del tick, valor del tick USD)
FUTUROS = {
    "NQ":  ("E-mini Nasdaq-100", "Índices", 20, 0.25, 5.00),
    "MNQ": ("Micro Nasdaq-100", "Índices", 2, 0.25, 0.50),
    "ES":  ("E-mini S&P 500", "Índices", 50, 0.25, 12.50),
    "MES": ("Micro S&P 500", "Índices", 5, 0.25, 1.25),
    "YM":  ("E-mini Dow Jones", "Índices", 5, 1, 5.00),
    "MYM": ("Micro Dow Jones", "Índices", 0.5, 1, 0.50),
    "RTY": ("E-mini Russell 2000", "Índices", 50, 0.1, 5.00),
    "M2K": ("Micro Russell 2000", "Índices", 5, 0.1, 0.50),
    "GC":  ("Oro", "Metales", 100, 0.1, 10.00),
    "MGC": ("Micro Oro", "Metales", 10, 0.1, 1.00),
    "SI":  ("Plata", "Metales", 5000, 0.005, 25.00),
    "SIL": ("Micro Plata", "Metales", 1000, 0.01, 10.00),
    "HG":  ("Cobre", "Metales", 25000, 0.0005, 12.50),
    "MHG": ("Micro Cobre", "Metales", 2500, 0.0005, 1.25),
    "CL":  ("Petróleo crudo", "Energía", 1000, 0.01, 10.00),
    "MCL": ("Micro Petróleo", "Energía", 100, 0.01, 1.00),
    "NG":  ("Gas natural", "Energía", 10000, 0.001, 10.00),
    "6E":  ("Euro FX", "Divisas", 125000, 0.00005, 6.25),
    "M6E": ("Micro Euro FX", "Divisas", 12500, 0.0001, 1.25),
    "6B":  ("Libra esterlina", "Divisas", 62500, 0.0001, 6.25),
    "M6B": ("Micro Libra", "Divisas", 6250, 0.0001, 0.625),
    "6A":  ("Dólar australiano", "Divisas", 100000, 0.00005, 5.00),
    "M6A": ("Micro AUD", "Divisas", 10000, 0.0001, 1.00),
    "6C":  ("Dólar canadiense", "Divisas", 100000, 0.00005, 5.00),
    "6J":  ("Yen japonés", "Divisas", 12500000, 0.0000005, 6.25),
    "ZN":  ("Nota del Tesoro 10 años", "Bonos", 1000, 1 / 64, 15.625),
    "ZB":  ("Bono del Tesoro 30 años", "Bonos", 1000, 1 / 32, 31.25),
}

MICRO_DE = {"NQ": "MNQ", "ES": "MES", "YM": "MYM", "RTY": "M2K", "GC": "MGC", "SI": "SIL",
            "HG": "MHG", "CL": "MCL", "6E": "M6E", "6B": "M6B", "6A": "M6A"}

PARES_FOREX = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD",
               "EURJPY", "GBPJPY", "EURGBP", "EURCHF", "EURAUD", "EURCAD", "GBPAUD",
               "GBPCAD", "AUDJPY", "AUDNZD", "AUDCAD", "CADJPY", "CHFJPY", "NZDJPY"]
LOTE_FOREX = 100_000
RATIOS_RR = [0.35, 0.5, 0.75, 1.0, 1.25, 1.5]


def agrupados():
    """{grupo: [simbolo, ...]} en el orden de la tabla."""
    out = {}
    for s, (_n, g, *_r) in FUTUROS.items():
        out.setdefault(g, []).append(s)
    return out


def partes_par(par):
    p = par.upper().replace("/", "").strip()
    if len(p) != 6 or not p.isalpha():
        raise ValueError("Par inválido (ej.: EURUSD)")
    return p[:3], p[3:]


def tam_pip(par):
    return 0.01 if partes_par(par)[1] == "JPY" else 0.0001


def valor_pip_usd(par, precio=None, quote_usd=None):
    """USD que vale 1 pip de 1 lote estándar (100.000 unidades), cuenta en USD.
    - cotizada en USD (EURUSD): 10 (no hace falta precio).
    - base USD (USDJPY, USDCHF): pip*lote/precio.
    - cruces (EURJPY): hace falta `quote_usd` = USD por 1 unidad de la moneda cotizada
      (p. ej. 1/USDJPY ≈ 0.0067)."""
    base, quote = partes_par(par)
    pip = tam_pip(par)
    if quote == "USD":
        return pip * LOTE_FOREX
    if base == "USD":
        if not precio or precio <= 0:
            raise ValueError("Falta el precio actual del par")
        return pip * LOTE_FOREX / precio
    if not quote_usd or quote_usd <= 0:
        raise ValueError(f"Falta la cotización de {quote} en USD (USD por 1 {quote})")
    return pip * LOTE_FOREX * quote_usd


def calcular(riesgo, stop, usd_por_unidad, paso=1.0, redondeo="abajo", target=None, drawdown=None):
    """Tamaño de posición.
    riesgo: USD máximos a perder. stop: distancia en la unidad de usd_por_unidad (puntos, pips…).
    paso: 1 para contratos, 0.01 para lotes. redondeo: 'abajo' (nunca te pasa del riesgo) o
    'web' (como la calculadora de gabomondo.com: sube si la fracción es >= 0.7).
    Devuelve dict o lanza ValueError con un mensaje claro."""
    if not riesgo or riesgo <= 0:
        raise ValueError("Ingresá el riesgo máximo en USD")
    if not stop or stop <= 0:
        raise ValueError("Ingresá la distancia al stop")
    if not usd_por_unidad or usd_por_unidad <= 0:
        raise ValueError("Falta el valor por punto del instrumento")
    costo_1 = stop * usd_por_unidad                     # riesgo de 1 contrato / 1 lote
    exacto = riesgo / costo_1
    unidades = exacto / paso
    if redondeo == "web":
        f = math.floor(unidades + 1e-9)
        n = (f + 1 if unidades - f >= 0.7 else f) * paso
    else:
        n = math.floor(unidades + 1e-9) * paso
    n = round(n, 6)
    r = dict(exacto=exacto, cantidad=n, costo_1=costo_1, riesgo_real=n * costo_1, rr=[],
             alcanza=n > 0, pct_drawdown=None, target=None)
    if n > 0:
        r["rr"] = [dict(ratio=x, puntos=stop * x, ganancia=n * stop * x * usd_por_unidad)
                   for x in RATIOS_RR]
        if drawdown and drawdown > 0:
            r["pct_drawdown"] = 100.0 * r["riesgo_real"] / drawdown
        if target and target > 0:
            r["target"] = dict(puntos=target, ganancia=n * target * usd_por_unidad,
                               ratio=target / stop)
    return r


def combinar(riesgo, stop, simbolo):
    """Reparte el riesgo entre el contrato grande y su micro (ej. 1 NQ + 3 MNQ).
    None si el activo no tiene micro o la mezcla no aporta nada."""
    micro = MICRO_DE.get(simbolo)
    if not micro or not riesgo or not stop or riesgo <= 0 or stop <= 0:
        return None
    vg, vm = FUTUROS[simbolo][2], FUTUROS[micro][2]
    n_g = math.floor(riesgo / (stop * vg) + 1e-9)
    resto = riesgo - n_g * stop * vg
    n_m = math.floor(resto / (stop * vm) + 1e-9)
    if n_g < 1 or n_m < 1:
        return None
    return dict(grande=simbolo, n_grande=n_g, micro=micro, n_micro=n_m,
                riesgo_real=n_g * stop * vg + n_m * stop * vm)


def ticks_a_puntos(simbolo, ticks):
    return ticks * FUTUROS[simbolo][3]

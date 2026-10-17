"""Dinero / Porcentaje: base de capital y formato de importes (sin interfaz).

El porcentaje es P&L ÷ capital inicial: el de la cuenta elegida, o la suma de las cuentas que lo tienen
si se ven todas. Sin capital inicial no hay porcentaje y se muestra en dinero."""
from .cuentas import clave as clave_cuenta

DINERO, PCT = "dinero", "pct"


def base_capital(cuentas, sel=None):
    """Capital inicial de la cuenta `sel` ((empresa, cuenta)) o la suma de todas las que lo tienen; None si no hay."""
    if sel:
        for c in cuentas:
            if clave_cuenta(c) == tuple(sel):
                return c.get("capital_inicial") or None
        return None
    total = sum(c.get("capital_inicial") or 0 for c in cuentas)
    return total or None


def fmt(v, modo=DINERO, base=None, d=0, signo=True):
    """Importe con signo. En modo % (y con base) devuelve «+1.25%»; si no, dinero con `d` decimales."""
    if v is None:
        return "—"
    if modo == PCT and base:
        p = 100.0 * v / base
        return f"{p:+.2f}%" if signo else f"{p:.2f}%"
    return f"{v:+,.{d}f}" if signo else f"{v:,.{d}f}"


def activo(modo, base):
    """True si realmente se está mostrando en porcentaje."""
    return modo == PCT and bool(base)

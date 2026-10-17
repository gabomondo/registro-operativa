"""Utilidades puras de la pantalla Cuentas (sin tkinter): capital, etiquetas, validación de fecha."""
import re
from datetime import date

from .db import ESTADOS_CUENTA, TIPOS_CUENTA

SIN = "—"          # opción «sin etiqueta» en los desplegables


def parse_capital(txt):
    """'50000', '50.000', '50,000', '$ 50k', '2.5k' -> float. Vacío -> None. Inválido -> ValueError."""
    s = (txt or "").strip().lower().replace("$", "").replace(" ", "")
    if not s:
        return None
    mult = 1
    if s.endswith("k"):
        mult, s = 1000, s[:-1]
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):          # 50.000 / 1.250.000 (miles con punto)
        s = s.replace(".", "")
    s = s.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s) else s.replace(",", ".")
    try:
        v = float(s) * mult
    except ValueError:
        raise ValueError(f"capital inválido: {txt!r}")
    if v < 0:
        raise ValueError("el capital no puede ser negativo")
    return v


def fmt_capital(v):
    if v is None:
        return ""
    return f"{v:.0f}" if float(v).is_integer() else f"{v:.2f}"


def parse_fecha(txt):
    """'' -> hoy (ISO). 'YYYY-MM-DD' válida -> la misma. Otra cosa -> ValueError."""
    s = (txt or "").strip()
    if not s:
        return date.today().isoformat()
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        raise ValueError("la fecha va como AAAA-MM-DD")


def titulo(c):
    """Nombre para mostrar: alias si hay, si no «empresa · cuenta»."""
    if c.get("alias"):
        return c["alias"]
    return " · ".join(x for x in (c.get("empresa"), c.get("cuenta")) if x) or "(sin nombre)"


def detalle(c):
    """Línea chica: «empresa · cuenta» (si hay alias) + estado + tipo."""
    partes = []
    if c.get("alias"):
        partes.append(" · ".join(x for x in (c.get("empresa"), c.get("cuenta")) if x))
    if c.get("estado"):
        partes.append(ESTADOS_CUENTA.get(c["estado"], c["estado"]))
    if c.get("tipo"):
        partes.append(TIPOS_CUENTA.get(c["tipo"], c["tipo"]))
    return "  ·  ".join(partes)


def etiquetas_estado():
    return [SIN] + list(ESTADOS_CUENTA.values())


def etiquetas_tipo():
    return [SIN] + list(TIPOS_CUENTA.values())


def clave_estado(etq):
    return next((k for k, v in ESTADOS_CUENTA.items() if v == etq), None)


def clave_tipo(etq):
    return next((k for k, v in TIPOS_CUENTA.items() if v == etq), None)


TODAS = "Todas las cuentas"


def agrupar_por_empresa(cuentas):
    """[(empresa, [cuentas...])] ordenado; las sin empresa van al final como «Sin empresa»."""
    grupos = {}
    for c in cuentas:
        grupos.setdefault(c.get("empresa") or "", []).append(c)
    orden = sorted((e for e in grupos if e), key=str.lower) + ([""] if "" in grupos else [])
    return [(e or "Sin empresa", sorted(grupos[e], key=lambda c: titulo(c).lower())) for e in orden]


def clave(c):
    """(empresa, cuenta) de una ficha, o None."""
    return None if c is None else (c.get("empresa") or "", c.get("cuenta") or "")


def texto_selector(cuentas, sel):
    """Texto del botón del selector global: la cuenta elegida (con alias) o «Todas las cuentas»."""
    if not sel:
        return TODAS
    for c in cuentas:
        if clave(c) == tuple(sel):
            return titulo(c)
    return " · ".join(x for x in sel if x) or TODAS


# ---- filtros de las pantallas Cuentas y Portfolio (estado / empresa / tipo) ----
TODOS, SIN_ETIQUETA, _SIN = "Todos", "Sin etiqueta", "__sin__"


def opciones_estado():
    return [TODOS] + list(ESTADOS_CUENTA.values()) + [SIN_ETIQUETA]


def opciones_tipo():
    return [TODOS] + list(TIPOS_CUENTA.values())


def opciones_empresa(cuentas):
    return [TODOS] + sorted({c["empresa"] for c in cuentas if c.get("empresa")}, key=str.lower)


def clave_filtro_estado(etq):
    """Etiqueta del desplegable -> clave de estado, '__sin__' (sin etiqueta) o None (sin filtro)."""
    if etq in (None, "", TODOS):
        return None
    return _SIN if etq == SIN_ETIQUETA else clave_estado(etq)


def filtrar(cuentas, estado=None, empresa=None, tipo=None):
    """Fichas que cumplen todos los filtros activos. estado: clave, '__sin__' o None; empresa: nombre o None;
    tipo: clave o None."""
    out = []
    for c in cuentas:
        if estado == _SIN and c.get("estado"):
            continue
        if estado and estado != _SIN and c.get("estado") != estado:
            continue
        if empresa and (c.get("empresa") or "") != empresa:
            continue
        if tipo and c.get("tipo") != tipo:
            continue
        out.append(c)
    return out

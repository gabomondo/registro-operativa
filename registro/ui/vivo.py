"""Valores "vivos" compartidos entre los módulos de la interfaz.

Varios valores se definen DESPUÉS de importar los módulos (la paleta del tema elegido,
las fuentes resueltas, las rutas de datos, la escala de pantalla). Cada módulo que los usa
como nombres sueltos hace `vivo.registrar(globals())` y recibe cada actualización:
`vivo.publicar(MUTED="#...")` reasigna ese nombre en todos los módulos que lo tengan.
"""

_VALORES = {}
_NAMESPACES = []


def registrar(ns):
    """Suscribe el espacio de nombres de un módulo (pasar `globals()`).
    Recibe de inmediato los valores ya publicados y todos los futuros."""
    if not any(n is ns for n in _NAMESPACES):
        _NAMESPACES.append(ns)
    for k, v in _VALORES.items():
        if k in ns:
            ns[k] = v


def publicar(**valores):
    """Guarda los valores y los reasigna en cada módulo suscripto que tenga ese nombre."""
    _VALORES.update(valores)
    for ns in _NAMESPACES:
        for k, v in valores.items():
            if k in ns:
                ns[k] = v

"""Agrupado común: varias 'piezas' (entrada parcial -> salida) que cierran casi
al mismo tiempo son UN trade (entradas escalonadas, stop que sale todo junto)."""

from .modelo import TradeImp


def agrupar_piezas(piezas, tolerancia_s):
    """piezas: TradeImp de a un lote. Une las de igual (cuenta, activo, lado)
    cuya salida difiere <= tolerancia_s de la anterior del grupo."""
    por_clave = {}
    for p in piezas:
        por_clave.setdefault((p.fuente, p.cuenta, p.activo, p.lado), []).append(p)
    out = []
    for lista in por_clave.values():
        lista.sort(key=lambda p: (p.t_fin, p.t_ini))
        grupo = [lista[0]]
        for p in lista[1:]:
            if (p.t_fin - grupo[-1].t_fin).total_seconds() <= tolerancia_s:
                grupo.append(p)
            else:
                out.append(fusionar(grupo))
                grupo = [p]
        out.append(fusionar(grupo))
    out.sort(key=lambda t: (t.t_ini, t.cuenta, t.ext_id))
    return out


def _vwap(items, campo):
    q = sum(p.contratos for p in items)
    return sum(getattr(p, campo) * p.contratos for p in items) / q if q else getattr(items[0], campo)


def fusionar(grupo):
    if len(grupo) == 1:
        return grupo[0]
    g = sorted(grupo, key=lambda p: (p.t_ini, p.ext_id))
    brutos = [p.bruto for p in g]
    avisos = []
    for p in g:
        for a in p.avisos:
            if a not in avisos:
                avisos.append(a)
    motivos = {p.motivo for p in g if p.motivo}
    return TradeImp(
        fuente=g[0].fuente, cuenta=g[0].cuenta, ext_id=g[0].ext_id,
        activo=g[0].activo, lado=g[0].lado,
        contratos=sum(p.contratos for p in g),
        t_ini=min(p.t_ini for p in g), t_fin=max(p.t_fin for p in g),
        precio_ini=_vwap(g, "precio_ini"), precio_fin=_vwap(g, "precio_fin"),
        bruto=None if any(b is None for b in brutos) else sum(brutos),
        comision=sum(p.comision for p in g),
        motivo=motivos.pop() if len(motivos) == 1 else ("Mixto" if motivos else ""),
        avisos=avisos)


def consolidar_cuentas(trades, tolerancia_s, etiqueta="Varias"):
    """Copy trading: el mismo trade en N cuentas se junta en uno (mismo activo,
    lado, y entrada y salida dentro de la tolerancia). Suma contratos, bruto y
    comisión."""
    por_clave = {}
    for t in trades:
        por_clave.setdefault((t.fuente, t.activo, t.lado), []).append(t)
    out = []
    for lista in por_clave.values():
        lista.sort(key=lambda t: (t.t_ini, t.t_fin))
        grupos = []
        for t in lista:
            for g in grupos:
                r = g[0]
                if (abs((t.t_ini - r.t_ini).total_seconds()) <= tolerancia_s * 3
                        and abs((t.t_fin - r.t_fin).total_seconds()) <= tolerancia_s * 3
                        and all(x.cuenta != t.cuenta for x in g)):
                    g.append(t)
                    break
            else:
                grupos.append([t])
        for g in grupos:
            if len(g) == 1:
                out.append(g[0])
                continue
            f = fusionar_cuentas(g, etiqueta)
            out.append(f)
    out.sort(key=lambda t: (t.t_ini, t.cuenta, t.ext_id))
    return out


def fusionar_cuentas(g, etiqueta):
    g = sorted(g, key=lambda t: (t.cuenta, t.ext_id))
    brutos = [t.bruto for t in g]
    avisos = []
    for t in g:
        for a in t.avisos:
            if a not in avisos:
                avisos.append(a)
    q = sum(t.contratos for t in g)
    return TradeImp(
        fuente=g[0].fuente, cuenta=f"{etiqueta} ({len(g)})",
        ext_id="+".join(t.ext_id for t in g[:1]) + f"~{len(g)}",
        activo=g[0].activo, lado=g[0].lado, contratos=q,
        t_ini=min(t.t_ini for t in g), t_fin=max(t.t_fin for t in g),
        precio_ini=sum(t.precio_ini * t.contratos for t in g) / q,
        precio_fin=sum(t.precio_fin * t.contratos for t in g) / q,
        bruto=None if any(b is None for b in brutos) else sum(brutos),
        comision=sum(t.comision for t in g),
        motivo=g[0].motivo, avisos=avisos, cuentas_n=len(g))

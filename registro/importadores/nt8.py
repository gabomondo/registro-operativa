"""NinjaTrader 8: grilla Executions (preferida) u Orders (alternativa aproximada)."""

import csv
import io
import re

from .modelo import TradeImp, Lectura, ImportError_
from .util import num, fecha, raiz, comision_de, leer_texto

SIM = re.compile(r"^(sim|playback)", re.I)


def es_simulada(cuenta):
    return bool(SIM.match(cuenta or ""))


def _filas(texto):
    return list(csv.DictReader(io.StringIO(texto), delimiter=";"))


def _formato_fecha(valores):
    """Decide dd/mm vs mm/dd mirando todas las fechas del archivo."""
    dm = md = False
    for v in valores:
        m = re.match(r"\s*(\d{1,2})[/.\-](\d{1,2})[/.\-]\d{2,4}", v or "")
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > 12:
                dm = True
            if b > 12:
                md = True
    return "md" if md and not dm else "dm"


def _parse_fecha(v, orden):
    v = re.sub(r"[.\-](?=\d{1,2}[.\-]\d{2,4}\s)", "/", (v or "").strip())
    v = re.sub(r"(\d)[.\-](\d)", r"\1/\2", v, count=2) if re.match(r"\d{1,2}[.\-]\d{1,2}[.\-]\d", v) else v
    d, m = ("%d", "%m") if orden == "dm" else ("%m", "%d")
    for hora in ("%H:%M:%S", "%I:%M:%S %p", "%H:%M", "%I:%M %p"):
        for y in ("%Y", "%y"):
            r = fecha(v, [f"{d}/{m}/{y} {hora}"])
            if r:
                return r
    return None


def _pos_archivo(s):
    s = (s or "").strip()
    if s in ("", "-"):
        return 0.0
    m = re.match(r"^(\d+(?:[.,]\d+)?)\s*([LS])", s, re.I)
    if not m:
        return None
    q = num(m.group(1), True)
    return q if m.group(2).upper() == "L" else -q


def leer_ejecuciones(path, perfil):
    texto = leer_texto(path)
    filas = _filas(texto)
    if not filas:
        raise ImportError_("El archivo de NinjaTrader no tiene filas.")
    orden = _formato_fecha([f.get("Time") for f in filas])
    fills, malas = [], 0
    for f in filas:
        t = _parse_fecha(f.get("Time"), orden)
        q, p = num(f.get("Quantity"), True), num(f.get("Price"), True)
        accion = (f.get("Action") or "").strip().lower()
        if t is None or not q or p is None or accion not in ("buy", "sell"):
            malas += 1
            continue
        idf = (f.get("ID") or "").strip()
        oid = (f.get("Order ID") or idf.split("_")[0]).strip()
        suf = re.search(r"_(\d+)$", idf)
        fills.append(dict(
            cuenta=(f.get("Account display name") or "").strip() or "NT8",
            activo=(f.get("Instrument") or "").strip(),
            lado=1 if accion == "buy" else -1, qty=q, precio=p, t=t,
            orden=oid, sub=int(suf.group(1)) if suf else 0,
            nombre=(f.get("Name") or "").strip(),
            comision=abs(num((f.get("Commission") or "").replace("$", ""), True) or 0.0),
            pos=_pos_archivo(f.get("Position")), id=idf))
    avisos = []
    if malas:
        avisos.append(f"{malas} fila(s) del archivo no se pudieron leer y se omitieron.")
    trades = reconstruir(fills, "nt8", perfil, aproximado=False)
    return Lectura("NinjaTrader 8 · Executions", "nt8", trades, avisos,
                   sorted({f["cuenta"] for f in fills}))


def leer_ordenes(path, perfil):
    texto = leer_texto(path)
    filas = _filas(texto)
    orden = _formato_fecha([f.get("Time") for f in filas])
    fills = []
    for f in filas:
        q = num(f.get("Filled"), True)
        p = num(f.get("Avg. price"), True)
        accion = (f.get("Action") or "").strip().lower()
        t = _parse_fecha(f.get("Time"), orden)
        if not q or not p or t is None or accion not in ("buy", "sell"):
            continue
        fills.append(dict(
            cuenta=(f.get("Account display name") or "").strip() or "NT8",
            activo=(f.get("Instrument") or "").strip(),
            lado=1 if accion == "buy" else -1, qty=q, precio=p, t=t,
            orden=(f.get("ID") or "").strip(), sub=0,
            nombre=(f.get("Name") or "").strip(), comision=0.0, pos=None,
            mercado=(f.get("Type") or "").strip().lower() == "market",
            id=(f.get("ID") or "").strip()))
    trades = reconstruir(fills, "nt8", perfil, aproximado=True)
    avisos = ["Este archivo es de ÓRDENES: la hora es la de envío de la orden, no la de ejecución, "
              "y puede mezclar el orden de los fills. Si podés, exportá la grilla Executions: "
              "es exacta."]
    return Lectura("NinjaTrader 8 · Orders (aproximado)", "nt8", trades, avisos,
                   sorted({f["cuenta"] for f in fills}))


def _ordenar_ordenes(lista):
    """En el archivo de órdenes solo las de mercado traen la hora real del fill;
    stops y límites traen la hora en que se enviaron. Entonces: las de mercado van
    en su hora y un stop/límite que cierra espera hasta que haya posición para
    cubrirlo."""
    mk = sorted([f for f in lista if f.get("mercado")], key=lambda f: (f["t"], num(f["orden"]) or 0))
    nm = sorted([f for f in lista if not f.get("mercado")], key=lambda f: (f["t"], num(f["orden"]) or 0))
    out, pos = [], 0.0

    def cabe(f):
        return pos == 0 or f["lado"] * pos > 0 or abs(pos) >= f["qty"] - 1e-9

    def poner(f):
        nonlocal pos
        out.append(f)
        pos += f["lado"] * f["qty"]

    while mk or nm:
        limite = mk[0]["t"] if mk else None
        movido = True
        while movido:
            movido = False
            for f in nm:
                if (limite is None or f["t"] < limite) and cabe(f):
                    poner(f)
                    nm.remove(f)
                    movido = True
                    break
        if mk:
            poner(mk.pop(0))
        elif nm:
            poner(nm.pop(0))
    return out


def _motivo(nombre):
    n = (nombre or "").lower()
    if "stop" in n:
        return "SL"
    if "target" in n or "profit" in n:
        return "TP"
    if "close" in n:
        return "Manual"
    return ""


def reconstruir(fills, fuente, perfil, aproximado):
    """Recorre los fills por cuenta+instrumento llevando la posición: un trade va
    de plano a plano. Si un fill cruza por cero, se parte en cierre + apertura."""
    por = {}
    for f in fills:
        por.setdefault((f["cuenta"], f["activo"]), []).append(f)
    trades = []
    for (cuenta, activo), lista in por.items():
        if aproximado:
            lista = _ordenar_ordenes(lista)
        else:
            lista.sort(key=lambda f: (f["t"], num(f["orden"]) or 0, f["sub"]))
        pos, cur, desvio = 0.0, None, False
        for f in lista:
            resto = f["qty"]
            while resto > 1e-9:
                if cur is None:
                    cur = dict(lado=f["lado"], entradas=[], salidas=[], comision=0.0,
                               nombre="", desvio=False)
                    pos = 0.0
                if f["lado"] == cur["lado"]:
                    cur["entradas"].append((resto, f["precio"], f["t"], f["orden"]))
                    pos += resto * f["lado"]
                    cur["comision"] += f["comision"] * resto / f["qty"]
                    resto = 0
                else:
                    cierra = min(resto, abs(pos))
                    cur["salidas"].append((cierra, f["precio"], f["t"]))
                    cur["nombre"] = f["nombre"]
                    cur["comision"] += f["comision"] * cierra / f["qty"]
                    pos += cierra * f["lado"]
                    resto -= cierra
                    if f["pos"] is not None and resto <= 1e-9 and abs(pos - f["pos"]) > 1e-6:
                        cur["desvio"] = True
                    if abs(pos) < 1e-9:
                        trades.append(_cerrar(cur, cuenta, activo, fuente, perfil, aproximado))
                        cur = None
        if cur is not None:
            qe = sum(e[0] for e in cur["entradas"])
            qs = sum(s[0] for s in cur["salidas"])
            if cur["salidas"]:
                pass
            # posición abierta al final del archivo: no se importa (no está cerrada)
    trades.sort(key=lambda t: (t.t_ini, t.cuenta))
    return trades


def _cerrar(c, cuenta, activo, fuente, perfil, aproximado):
    qe = sum(e[0] for e in c["entradas"])
    pe = sum(e[0] * e[1] for e in c["entradas"]) / qe
    qs = sum(s[0] for s in c["salidas"])
    ps = sum(s[0] * s[1] for s in c["salidas"]) / qs
    sg = c["lado"]
    avisos = []
    vp = perfil.valor_punto_de(activo)
    if vp is None:
        bruto = None
        avisos.append(f"Sin valor del punto para {raiz(activo)}: cargalo en Perfil para calcular el P&L.")
    else:
        bruto = (ps - pe) * sg * qs * vp
    com = c["comision"]
    if com <= 0:
        est = comision_de(perfil, activo, qe)
        if est is not None:
            com = est
            avisos.append("Comisión estimada con el valor de tu Perfil (el archivo no la trae).")
        else:
            avisos.append("Sin comisión: el archivo no la trae y no hay valor en Perfil.")
    if c["desvio"]:
        avisos.append("La posición calculada no coincide con la del archivo; revisá este trade.")
    if aproximado:
        avisos.append("Horario aproximado (viene del archivo de órdenes).")
    primera = min(c["entradas"], key=lambda e: e[2])
    return TradeImp(
        fuente=fuente, cuenta=cuenta, ext_id=str(primera[3]), activo=raiz(activo),
        lado="Long" if sg > 0 else "Short", contratos=qe,
        t_ini=min(e[2] for e in c["entradas"]), t_fin=max(s[2] for s in c["salidas"]),
        precio_ini=pe, precio_fin=ps, bruto=bruto, comision=com,
        motivo=_motivo(c["nombre"]), avisos=avisos)

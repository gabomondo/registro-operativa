import os
import pytest
from registro import importadores as imp, db, bootstrap
from registro.importadores.nt8 import es_simulada
from registro.perfil import Perfil

F = os.path.join(os.path.dirname(__file__), "fixtures")
def ruta(n): return os.path.join(F, n)
def perfil(**kw):
    p = Perfil()
    for k, v in kw.items(): setattr(p, k, v)
    return p

def test_detecta_formatos():
    assert imp.detectar(ruta("mt5_informe.html")) == "mt5"
    assert imp.detectar(ruta("tradovate_position_history.csv")) == "tradovate"
    assert imp.detectar(ruta("topstepx_trades_export.csv")) == "topstepx"
    assert imp.detectar(ruta("nt8_executions.csv")) == "nt8_exec"
    assert imp.detectar(ruta("nt8_orders.csv")) == "nt8_ordenes"

def test_formato_desconocido(tmp_path):
    f = tmp_path / "x.csv"; f.write_text("a,b,c\n1,2,3\n")
    with pytest.raises(imp.ImportError_):
        imp.leer(str(f), perfil())

def test_mt5_cierra_con_el_informe():
    # el informe dice Total Net Profit -29.95; 84 posiciones
    l = imp.leer(ruta("mt5_informe.html"), perfil())
    assert round(sum(t.neto for t in l.trades), 2) == -29.95
    assert len(l.trades) == 26 and l.cuentas == ["10000001"]
    assert len(imp.leer(ruta("mt5_informe.html"), perfil(agrupar_segundos=0)).trades) == 27

def test_mt5_offset_horario():
    a = imp.leer(ruta("mt5_informe.html"), perfil()).trades[0].t_ini
    b = imp.leer(ruta("mt5_informe.html"), perfil(offset_horas={"mt5": -3.0, "tradovate": 0})).trades[0].t_ini
    assert (a - b).total_seconds() == 3 * 3600

def test_tradovate_agrupa_por_salida_y_usa_comision_del_perfil():
    l = imp.leer(ruta("tradovate_position_history.csv"), perfil(comision_contrato={"MNQ": 0.74}))
    assert len(l.trades) == 2
    assert sum(t.bruto for t in l.trades) == 239.0
    assert sum(t.contratos for t in l.trades) == 9         # Bought 9 / Sold 9 en el archivo
    assert round(sum(t.comision for t in l.trades), 2) == round(9 * 0.74, 2)
    assert all(t.activo == "MNQ" for t in l.trades)

def test_topstepx_22_trades():
    l = imp.leer(ruta("topstepx_trades_export.csv"), perfil())
    assert len(l.trades) == 22
    assert round(sum(t.bruto for t in l.trades), 2) == 335.5
    assert round(sum(t.neto for t in l.trades), 2) == 223.9

def test_nt8_executions_y_orders_coinciden_en_cuentas_reales():
    pe = perfil(comision_contrato={"MNQ": 0.5})
    e = imp.leer(ruta("nt8_executions.csv"), pe)
    o = imp.leer(ruta("nt8_orders.csv"), pe)
    assert len(e.cuentas) == 11 and any(es_simulada(c) for c in e.cuentas)
    reales = lambda l: [t for t in l.trades if not es_simulada(t.cuenta)]
    assert len(reales(e)) == 30 and len(reales(o)) == 30
    ke = {(t.cuenta, t.ext_id): round(t.bruto, 2) for t in reales(e)}
    ko = {(t.cuenta, t.ext_id): round(t.bruto, 2) for t in reales(o)}
    assert ke == ko                                # mismos ids y mismo P&L
    assert round(sum(ke.values()), 2) == 6795.0
    assert any("ÓRDENES" in a for a in o.avisos)

def test_nt8_motivo_y_comision_estimada():
    l = imp.leer(ruta("nt8_executions.csv"), perfil(comision_contrato={"MNQ": 0.5}))
    t = [x for x in l.trades if x.cuenta == "CUENTA-223"][0]
    assert t.motivo == "SL" and t.contratos == 40 and t.comision == 20.0
    assert any("estimada" in a for a in t.avisos)

def test_nt8_sin_valor_punto_no_inventa_pnl():
    p = perfil(valor_punto={"ES": 50.0})
    l = imp.leer(ruta("nt8_executions.csv"), p)
    assert all(t.bruto is None and t.neto is None for t in l.trades)

def test_consolidar_copy_trading():
    l = imp.leer(ruta("nt8_executions.csv"), perfil())
    reales = [t for t in l.trades if not es_simulada(t.cuenta)]
    c = imp.consolidar_cuentas(reales, 2)
    assert len(c) == 3 and all(t.cuentas_n == 10 for t in c)
    assert round(sum(t.bruto for t in c), 2) == round(sum(t.bruto for t in reales), 2)
    assert c[0].contratos == 400

@pytest.fixture
def ctx(tmp_path):
    return bootstrap.iniciar(["--datos", str(tmp_path)], env={})

def test_guardar_sin_duplicados(ctx):
    l = imp.leer(ruta("topstepx_trades_export.csv"), ctx.perfil)
    r1 = db.db_importar(l.trades, empresa="Topstep", cuenta="Challenge")
    assert r1 == {"nuevos": 22, "duplicados": 0, "sin_pnl": 0}
    r2 = db.db_importar(l.trades, empresa="Topstep", cuenta="Challenge")
    assert r2["nuevos"] == 0 and r2["duplicados"] == 22
    ops = db.db_all()
    assert len(ops) == 22 and round(sum(o["profit"] for o in ops), 2) == 223.9
    o = ops[0]
    assert o["fuente"] == "topstepx" and o["empresa"] == "Topstep" and o["cuenta"] == "Challenge"
    assert o["lado"] and o["contratos"] and o["bruto"] is not None and o["hora_fin"]
    assert len(db.claves_importadas()) == 22

def test_guardar_omite_trades_sin_pnl(ctx):
    l = imp.leer(ruta("nt8_executions.csv"), perfil(valor_punto={"ES": 50.0}))
    r = db.db_importar(l.trades)
    assert r["nuevos"] == 0 and r["sin_pnl"] == len(l.trades)



def test_posibles_duplicados_manual_y_consolidacion(ctx):
    l = imp.leer(ruta("topstepx_trades_export.csv"), ctx.perfil)
    t0 = l.trades[0]
    # una operación cargada a mano, mismo día/activo, 2 minutos de diferencia
    hora = (t0.t_ini + __import__("datetime").timedelta(minutes=2)).strftime("%H:%M")
    ctx_ops = [dict(id=999, fecha=t0.t_ini.strftime("%Y-%m-%d"), hora=hora, activo=t0.activo,
                    profit=100.0, fuente=None, ext_id=None, cuenta_ext=None)]
    n = db.marcar_posibles_duplicados(l.trades, ops=ctx_ops)
    assert n == 1 and "a mano" in t0.posible
    assert all(not t.posible for t in l.trades[1:] if t.t_ini.date() != t0.t_ini.date()
               or abs((t.t_ini - t0.t_ini).total_seconds()) > 300)
    # lejos en el tiempo: sin aviso
    ctx_ops[0]["hora"] = "03:00"
    assert db.marcar_posibles_duplicados(l.trades, ops=ctx_ops) == 0
    # otro activo: sin aviso
    ctx_ops[0].update(hora=hora, activo="ZZ")
    assert db.marcar_posibles_duplicados(l.trades, ops=ctx_ops) == 0


def test_posibles_duplicados_extremos(ctx):
    import datetime as dt
    l = imp.leer(ruta("topstepx_trades_export.csv"), ctx.perfil)
    t0 = l.trades[0]
    fecha_, hh = t0.t_ini.strftime("%Y-%m-%d"), t0.t_ini.strftime("%H:%M")
    base = dict(fecha=fecha_, hora=hh, activo=t0.activo, profit=1.0)
    # una sola fila manual no se reparte entre dos trades
    mismos = [t for t in l.trades if t.t_ini.strftime("%Y-%m-%d %H:%M") == f"{fecha_} {hh}"]
    manual = dict(base, id=1, fuente=None, ext_id=None, cuenta_ext=None)
    db.marcar_posibles_duplicados(l.trades, ops=[manual])
    assert sum(1 for t in l.trades if t.posible) == 1
    # una fila consolidada de importación previa sí avisa a varios
    consol = dict(base, id=2, fuente=t0.fuente, ext_id="abc~3", cuenta_ext="Varias (3)")
    db.marcar_posibles_duplicados(l.trades, ops=[consol])
    assert all("consolidación" in t.posible for t in l.trades if t.posible)
    # misma clave exacta no se marca como "posible" (ya es duplicado exacto)
    exacta = dict(base, id=3, fuente=t0.fuente, ext_id=t0.ext_id, cuenta_ext=t0.cuenta)
    db.marcar_posibles_duplicados(l.trades, ops=[exacta])
    assert not t0.posible


def _xlsx_mt5(path, con_posiciones=True):
    """Informe de MT5 guardado como Excel: mismas secciones que el HTML, con columnas vacías de más."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Trade History Report"])
    ws.append(["Name:", None, None, "Raw Spread"])
    ws.append(["Account:", None, None, "12345678 (USD, Broker-MT5Real, real, Hedge)"])
    ws.append(["Positions"])
    ws.append(["Time", "Position", "Symbol", "Type", "Volume", "Price", "S / L", "T / P", "Time", "Price",
               "Commission", "Swap", "Profit"])
    if con_posiciones:
        ws.append(["2026.09.21 20:10:37", 111, "USTEC", "sell", "0.5", 30523.22, 30517.92, 30514.66,
                   "2026.09.21 20:11:45", 30517.92, -0.31, 0.0, 2.65])
        ws.append(["2026.09.22 10:00:00", 112, "AUDCAD", "buy", "0.02", 0.99316, 0.9, 0.99621,
                   "2026.09.22 11:00:00", 0.99482, -0.14, 0.0, 2.34])
    ws.append(["Orders"])
    ws.append(["Open Time", "Order", "Symbol", "Type", "Volume", "Price", "S / L", "T / P", "Time", "State"])
    ws.append(["Deals"])
    ws.append(["Time", "Deal", "Symbol", "Type", "Direction", "Volume", "Price", "Order", "Commission", "Fee",
               "Swap", "Profit", "Balance", "Comment"])
    ws.append(["2026.09.21 20:10:37", 1, "USTEC", "sell", "in", "0.5", 30523.22, 111, -0.31, 0, 0, 0, 100, None])
    ws.append(["2026.09.21 20:11:45", 2, "USTEC", "buy", "out", "0.5", 30517.92, None, 0, 0, 0, 2.65, 102.65,
               "[sl 30517.92000]"])
    ws.append(["Results"])
    wb.save(path)


def test_mt5_excel(tmp_path):
    p = str(tmp_path / "ReportHistory-12345678.xlsx")
    _xlsx_mt5(p)
    assert imp.detectar(p) == "mt5"
    l = imp.leer(p, perfil())
    assert l.cuentas == ["12345678"] and len(l.trades) == 2
    t = {x.activo: x for x in l.trades}
    assert t["USTEC"].lado == "Short" and t["USTEC"].bruto == 2.65 and t["USTEC"].motivo == "SL"
    assert round(t["USTEC"].comision, 2) == 0.31
    assert t["AUDCAD"].contratos == 0.02 and t["AUDCAD"].motivo == ""


def test_excel_que_no_es_mt5(tmp_path):
    import pytest
    p = str(tmp_path / "otro.xlsx")
    _xlsx_mt5(p, con_posiciones=False)
    with pytest.raises(imp.ImportError_):
        imp.detectar(p)


@pytest.mark.parametrize("nombre", ["mt4_statement.html", "mt4_detailed_statement.html"])
def test_mt4_los_dos_formatos(nombre):
    assert imp.detectar(ruta(nombre)) == "mt4"
    l = imp.leer(ruta(nombre), perfil(agrupar_segundos=0))
    assert l.cuentas == ["12345678"] and l.fuente == "mt4"
    assert len(l.trades) == 10                      # la fila «balance» (depósito) no es un trade
    assert round(sum(t.bruto for t in l.trades), 2) == -1031.98
    t = {x.ext_id: x for x in l.trades}
    assert t["302436986"].lado == "Long" and t["302436986"].activo == "BTCUSD"
    assert t["302437024"].lado == "Short" and t["302437024"].contratos == 5 and t["302437024"].bruto == 356.6
    assert all(x.comision == 0 for x in l.trades)


def test_mt4_marca_sl_si_cierra_en_el_stop():
    l = imp.leer(ruta("mt4_statement.html"), perfil(agrupar_segundos=0))
    assert all(t.motivo == "" for t in l.trades)    # ningún cierre coincide con SL/TP en el ejemplo


def test_deepcharts():
    assert imp.detectar(ruta("deepcharts_trades.csv")) == "deepcharts"
    l = imp.leer(ruta("deepcharts_trades.csv"), perfil())
    assert len(l.trades) == 4 and l.fuente == "deepcharts"
    t = l.trades[0]
    assert (t.activo, t.lado, t.contratos, t.bruto, t.comision) == ("MNQ", "Long", 2, 138.0, 2.4)
    assert t.neto == 135.6 and t.precio_ini == 20150.5 and t.precio_fin == 20185.0
    assert t.t_ini.microsecond == 125000
    assert [x.activo for x in l.trades] == ["MNQ", "ES", "MNQ", "GC"]
    assert round(sum(x.neto for x in l.trades), 2) == 1456.0

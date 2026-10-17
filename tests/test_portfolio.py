"""Cálculo del Portfolio (todas las cuentas juntas)."""
from datetime import date

import pytest

from registro import portfolio as PF

HOY = date(2026, 10, 17)      # sábado


def op(f, p, e="Lucid", c="A", h="10:00"):
    return dict(fecha=f, hora=h, profit=p, empresa=e, cuenta=c)


def ficha(e, c, cap=None, alias=None, estado=None):
    return dict(empresa=e, cuenta=c, alias=alias, capital_inicial=cap, estado=estado, tipo=None)


def test_vacio():
    r = PF.calcular([], [], HOY)
    assert r["n"] == 0 and r["neto"] == 0 and r["cuentas"] == [] and r["salud"]["nota"] is None
    assert r["curva"] == [] and r["balance"] is None and r["sharpe"] is None


def test_capital_balance_y_peso():
    rows = [op("2026-10-12", 100, "Lucid", "A"), op("2026-10-13", -40, "Lucid", "A"), op("2026-10-13", 200, "Apex", "B")]
    cs = [ficha("Lucid", "A", 50000, alias="Principal", estado="fondeada"), ficha("Apex", "B", 50000), ficha("Otra", "C")]
    r = PF.calcular(rows, cs, HOY)
    assert r["capital_inicial"] == 100000 and r["balance"] == 100260 and r["neto"] == 260
    assert r["retorno_pct"] == pytest.approx(0.26) and r["con_capital"] == 2 and r["n_cuentas"] == 3
    por = {c["titulo"]: c for c in r["cuentas"]}
    assert por["Principal"]["balance"] == 50060 and por["Principal"]["n"] == 2 and por["Principal"]["estado"] == "fondeada"
    assert por["Apex · B"]["pnl"] == 200 and por["Apex · B"]["mejor"] is True and por["Principal"]["mejor"] is False
    assert por["Otra · C"]["balance"] is None and por["Otra · C"]["peso"] is None and por["Otra · C"]["n"] == 0
    assert sum(c["peso"] for c in r["cuentas"] if c["peso"]) == pytest.approx(100)
    assert r["cuentas"][0]["titulo"] == "Apex · B"                       # mayor balance primero
    assert r["curva"][0] == ("2026-10-12", 100100) and r["curva"][-1] == ("2026-10-13", 100260)


def test_sin_capital_no_inventa_nada():
    r = PF.calcular([op("2026-10-12", 50), op("2026-10-13", -10)], [], HOY)
    assert r["capital_inicial"] is None and r["balance"] is None and r["retorno_pct"] is None
    assert r["cuentas"][0]["peso"] is None and r["salud"]["riesgo"] is None and r["dd_pct"] is None
    assert r["curva"] == [("2026-10-12", 50), ("2026-10-13", 40)]        # arranca en 0 sin capital
    assert all(m["pct"] is None for m in r["por_mes"])
    assert r["salud"]["nota"] is not None                                 # se promedia lo que sí se puede


def test_periodos_hoy_semana_mes():
    rows = [op("2026-10-17", 5), op("2026-10-12", 10), op("2026-10-11", 100), op("2026-10-01", 1000), op("2026-09-30", 7)]
    r = PF.calcular(rows, [], HOY)
    assert (r["hoy"], r["semana"], r["mes"]) == (5, 15, 1115)


def test_salud_formulas():
    # 3 días: +100, -50, +50 -> consistencia 2/3; dd = 50 sobre capital 1000 -> riesgo 100 - 5*5 = 75
    rows = [op("2026-10-12", 100), op("2026-10-13", -50), op("2026-10-14", 50)]
    r = PF.calcular(rows, [ficha("Lucid", "A", 1000)], HOY)
    s = r["salud"]
    assert s["consistencia"] == pytest.approx(66.667, abs=1e-2)
    assert r["dd_max"] == 50 and r["dd_pct"] == pytest.approx(5.0) and s["riesgo"] == pytest.approx(75.0)
    assert s["diversificacion"] == 0.0                                    # una sola cuenta
    assert s["rentabilidad"] == pytest.approx(min(100, 150 / 50 * 50))    # PF 3 -> tope 100
    assert s["nota"] == round((s["consistencia"] + 75 + 0 + 100) / 4)


def test_diversificacion_y_riesgo_acotado():
    assert PF._diversificacion([100, 100, 100, 100]) == pytest.approx(100)
    assert PF._diversificacion([100]) == 0 and PF._diversificacion([]) == 0
    assert PF._diversificacion([90, 10]) < PF._diversificacion([60, 40]) < 100
    r = PF.calcular([op("2026-10-12", 500), op("2026-10-13", -900)], [ficha("Lucid", "A", 1000)], HOY)
    assert r["salud"]["riesgo"] == 0.0                                    # dd 90% -> no baja de 0


def test_sharpe():
    assert PF._sharpe([1.0]) is None and PF._sharpe([2, 2, 2]) is None
    assert PF._sharpe([1, 3]) == pytest.approx(2 / 2 ** 0.5 * 252 ** 0.5)
    assert PF._sharpe([10, 30]) == pytest.approx(PF._sharpe([1, 3]))      # no depende de la escala


def test_cuando_y_dia_a_dia():
    rows = [op("2026-10-12", 100, "A", "1"), op("2026-10-12", -20, "B", "2"), op("2026-10-19", 60, "A", "1"),
            op("2026-09-14", 10, "A", "1")]
    r = PF.calcular(rows, [ficha("A", "1", 1000)], HOY)
    lun = r["por_dia_semana"][0]
    assert lun["dia"] == "L" and lun["n"] == 3 and lun["prom"] == pytest.approx((80 + 60 + 10) / 3)
    assert r["por_dia_semana"][1]["prom"] is None
    assert [m["mes"] for m in r["por_mes"]] == ["2026-09", "2026-10"]
    assert r["por_mes"][1]["pnl"] == 140 and r["por_mes"][1]["pct"] == pytest.approx(14.0)
    d = r["dia_a_dia"][0]
    assert d["fecha"] == "2026-10-19" and r["dia_a_dia"][1]["n"] == 2
    assert [(t[0], t[1]) for t in r["dia_a_dia"][1]["por_cuenta"]] == [("A · 1", 100), ("B · 2", -20)]


def test_ops_sin_cuenta_y_filas_invalidas():
    rows = [dict(fecha="2026-10-12", profit=10, empresa=None, cuenta=None), dict(fecha="2026-10-12", profit=None),
            dict(fecha=None, profit=5)]
    r = PF.calcular(rows, [], HOY)
    assert r["n"] == 1 and [c["titulo"] for c in r["cuentas"]] == ["Sin cuenta"]

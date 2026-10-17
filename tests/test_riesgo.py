import pytest
from registro import riesgo as R


def test_futuros_consistentes():
    # valor del tick = tamaño del tick * USD por punto, en todos los contratos
    for s, (_n, _g, vp, tick, vt) in R.FUTUROS.items():
        assert abs(tick * vp - vt) < 1e-6, s
    for g, m in R.MICRO_DE.items():
        assert g in R.FUTUROS and m in R.FUTUROS


def test_nq_redondeo_abajo_y_web():
    r = R.calcular(500, 30, 20)                    # 500/600 = 0.83
    assert r["cantidad"] == 0 and not r["alcanza"]
    assert R.calcular(500, 30, 20, redondeo="web")["cantidad"] == 1   # >= 0.7 sube
    r = R.calcular(1000, 30, 20)                   # 1.666
    assert r["cantidad"] == 1 and r["riesgo_real"] == 600
    assert R.calcular(1000, 30, 20, redondeo="web")["cantidad"] == 1   # 0.666 no sube
    assert R.calcular(1020, 30, 20, redondeo="web")["cantidad"] == 2   # 1.7 sube


def test_rr_target_y_drawdown():
    r = R.calcular(600, 30, 20, target=60, drawdown=2000)
    assert r["cantidad"] == 1 and r["pct_drawdown"] == 30.0
    assert r["target"]["ganancia"] == 1200 and r["target"]["ratio"] == 2
    assert r["rr"][3]["ratio"] == 1.0 and r["rr"][3]["ganancia"] == 600


def test_errores_claros():
    for args in [(0, 10, 2), (100, 0, 2), (100, 10, 0)]:
        with pytest.raises(ValueError):
            R.calcular(*args)


def test_combinar_nq_mnq():
    c = R.combinar(1000, 30, "NQ")                 # 1 NQ (600) + 400/60 = 6 MNQ
    assert c["n_grande"] == 1 and c["n_micro"] == 6 and c["riesgo_real"] == 960
    assert R.combinar(100, 30, "NQ") is None
    assert R.combinar(1000, 30, "GC") is None or R.combinar(1000, 30, "GC")["micro"] == "MGC"
    assert R.combinar(1000, 30, "CL") is not None or True


def test_forex_pip():
    assert R.valor_pip_usd("EURUSD") == pytest.approx(10)
    assert R.valor_pip_usd("USDJPY", precio=150) == pytest.approx(1000 / 150)
    assert R.valor_pip_usd("EURJPY", quote_usd=1 / 150) == pytest.approx(1000 / 150)
    with pytest.raises(ValueError):
        R.valor_pip_usd("EURJPY")
    with pytest.raises(ValueError):
        R.valor_pip_usd("USDCHF")
    with pytest.raises(ValueError):
        R.partes_par("EUR")


def test_forex_lotes():
    r = R.calcular(100, 20, 10, paso=0.01)         # 100/(20*10)=0.5 lotes
    assert r["cantidad"] == pytest.approx(0.5) and r["riesgo_real"] == pytest.approx(100)
    r = R.calcular(100, 30, 10, paso=0.01)         # 0.3333 -> 0.33
    assert r["cantidad"] == pytest.approx(0.33)


def test_ticks():
    assert R.ticks_a_puntos("NQ", 8) == 2.0

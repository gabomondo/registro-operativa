from registro import metricas as M


def _op(f, h, p, **k):
    return dict(fecha=f, hora=h, profit=p, **k)


def test_drawdown_y_rachas():
    rows = [_op("2026-10-01", "09:40", 100), _op("2026-10-01", "10:00", -50),
            _op("2026-10-02", "09:40", -80), _op("2026-10-02", "10:00", -20),
            _op("2026-10-03", "09:40", 60), _op("2026-10-03", "10:00", 70), _op("2026-10-03", "11:00", 10)]
    e = M.extra(rows)
    # equity: 100, 50, -30, -50, 10, 80, 90 -> pico 100, valle -50 => dd 150
    assert e["dd_max"] == 150 and e["dd_desde"] == "2026-10-01" and e["dd_hasta"] == "2026-10-02"
    assert e["dd_actual"] == 10                      # pico 100, hoy 90
    assert e["racha_gan"]["n"] == 3 and e["racha_gan"]["usd"] == 140
    assert e["racha_perd"]["n"] == 3 and e["racha_perd"]["usd"] == -150
    assert round(e["recovery"], 2) == 0.6            # 90 / 150
    assert e["mejor_trade"]["usd"] == 100 and e["peor_trade"]["usd"] == -80


def test_drawdown_desde_cero_sin_picos():
    # arranca perdiendo: el pico es el 0 inicial
    d = M.drawdown([-10, -30, -5])
    assert d["max"] == 30 and d["i_pico"] == -1 and d["actual"] == 5


def test_rachas_ignora_ceros_y_vacio():
    g, p = M.rachas([10, 0, 5, -1, 0, -2])
    assert g["n"] == 2 and g["usd"] == 15 and p["n"] == 2 and p["usd"] == -3
    assert M.extra([]) is None and M.extra([dict(fecha="2026-10-01", profit=None)]) is None


def test_comisiones_y_duracion_solo_si_hay_datos():
    rows = [_op("2026-10-01", "09:40", 90, comision=10.0, bruto=100.0, hora_fin="2026-10-01 10:10"),
            _op("2026-10-01", "11:00", 40, comision=10.0, bruto=50.0, hora_fin="2026-10-01 11:20")]
    e = M.extra(rows)
    assert e["comisiones"] == 20 and round(e["pct_comision_bruto"], 1) == 13.3
    assert e["dur_prom_min"] == 25 and e["n_con_duracion"] == 2
    manual = M.extra([_op("2026-10-01", "09:40", 5)])
    assert manual["comisiones"] is None and manual["dur_prom_min"] is None
    assert M.fmt_duracion(25) == "25 min" and M.fmt_duracion(95) == "1 h 35 min" and M.fmt_duracion(None) == "—"

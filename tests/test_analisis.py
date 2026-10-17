from registro import analisis as A

def op(f, h, p, activo="MNQ", lado=None):
    return dict(fecha=f, hora=h, profit=p, activo=activo, lado=lado)

ROWS = [op("2026-10-12", "09:31", 100), op("2026-10-12", "09:50", -40), op("2026-10-12", "10:05", 20, "NQ"),
        op("2026-10-13", "09:40", -60, lado="Long"), op("2026-10-14", "15:10", 30, lado="Short"),
        op("2026-10-14", None, None)]            # sin profit: se ignora

def test_por_dia_acumula_y_ordena():
    d = A.por_dia(ROWS)
    assert [x["label"] for x in d] == ["2026-10-14", "2026-10-13", "2026-10-12"]
    assert d[2]["n"] == 3 and d[2]["neto"] == 80 and round(d[2]["wr"], 1) == 66.7
    assert d[0]["acum"] == 50 and d[2]["acum"] == 80 and d[2]["dia"] == "Lun"
    assert d[2]["mejor"] == 100 and d[2]["peor"] == -40

def test_por_hora_y_activo_y_semana():
    h = {x["label"]: x for x in A.por_hora(ROWS)}
    assert h["09:00"]["n"] == 3 and h["09:00"]["neto"] == 0 and h["10:00"]["neto"] == 20 and "15:00" in h
    assert [x["label"] for x in A.por_activo(ROWS)][0] == "MNQ"
    s = A.por_dia_semana(ROWS)
    assert [x["label"] for x in s] == ["Lunes", "Martes", "Miércoles"]

def test_por_lado_ignora_manuales():
    assert {x["label"] for x in A.por_lado(ROWS)} == {"Long", "Short"}

def test_resumen():
    r = A.resumen(ROWS)
    assert r["n"] == 5 and r["neto"] == 50 and r["dias"] == 3 and r["dias_verdes"] == 2
    assert round(r["profit_factor"], 2) == 1.5 and round(r["payoff"], 2) == round(50 / 50, 2)
    assert r["mejor_dia"]["label"] == "2026-10-12" and r["peor_dia"]["label"] == "2026-10-13"
    assert A.resumen([]) is None

def test_sin_perdidas_no_divide_por_cero():
    r = A.resumen([op("2026-10-12", "09:00", 10)])
    assert r["profit_factor"] is None and r["payoff"] is None

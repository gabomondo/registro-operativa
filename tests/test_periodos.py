"""Rango global de fechas: atajos, validación, prefs y filtro en db."""
from datetime import date

import pytest

from registro import bootstrap, db
from registro import periodos as PR

HOY = date(2026, 10, 17)      # sábado


def test_rangos_de_los_atajos():
    r = lambda n: PR.rango(n, HOY)
    assert r("Hoy") == ("2026-10-17", "2026-10-17")
    assert r("Esta semana") == ("2026-10-12", "2026-10-17")          # lunes a hoy
    assert r("Este mes") == ("2026-10-01", "2026-10-17")
    assert r("Últimos 30 días") == ("2026-09-18", "2026-10-17")
    assert r("Mes pasado") == ("2026-09-01", "2026-09-30")
    assert r("Últimos 3 meses") == ("2026-07-18", "2026-10-17")
    assert r("Últimos 6 meses") == ("2026-04-18", "2026-10-17")
    assert r("Año pasado") == ("2025-01-01", "2025-12-31")
    assert r(PR.TODO) is None and r("otra") is None


def test_bordes_de_mes_y_anio():
    assert PR.rango("Mes pasado", date(2026, 1, 15)) == ("2025-12-01", "2025-12-31")
    assert PR.rango("Mes pasado", date(2026, 3, 31)) == ("2026-02-01", "2026-02-28")
    assert PR.rango("Últimos 3 meses", date(2026, 5, 31)) == ("2026-03-01", "2026-05-31")   # feb/abr más cortos
    assert PR.rango("Últimos 6 meses", date(2026, 3, 31)) == ("2025-10-01", "2026-03-31")


def test_validar_rango():
    assert PR.validar_rango("2026-10-01", "2026-10-17") == ("2026-10-01", "2026-10-17")
    assert PR.validar_rango("", "2026-10-17") == (None, "2026-10-17")
    assert PR.validar_rango("2026-10-01", "") == ("2026-10-01", None)
    assert PR.validar_rango("", " ") is None
    for d, h in (("1/10/2026", ""), ("2026-10-17", "2026-10-01"), ("x", "x")):
        with pytest.raises(ValueError):
            PR.validar_rango(d, h)


def test_etiqueta_y_prefs():
    assert PR.etiqueta("Este mes", ("a", "b")) == "Este mes" and PR.etiqueta(PR.TODO, None) == PR.TODO
    assert PR.etiqueta(None, ("2026-10-01", None)) == "2026-10-01 → hoy"
    assert PR.etiqueta(None, (None, "2026-10-17")) == "inicio → 2026-10-17"
    assert PR.desde_prefs({"preset": "Este mes"}, HOY) == ("Este mes", ("2026-10-01", "2026-10-17"))   # se recalcula
    assert PR.desde_prefs({"desde": "2026-10-01", "hasta": "2026-10-05"}) == (None, ("2026-10-01", "2026-10-05"))
    for malo in (None, {}, {"preset": "nada"}, {"desde": "mal"}, {"preset": PR.TODO}, "x"):
        assert PR.desde_prefs(malo) == (PR.TODO, None)


def test_db_aplica_el_periodo_global(tmp_path):
    bootstrap.iniciar(["--datos", str(tmp_path)], env={})
    op = lambda f, p, c="A": dict(fecha=f, hora="10:00", activo="MNQ", tipo="x", profit=p, empresa="E", cuenta=c,
                                   mov_sl="", tranquilo="", emo=0, comentario="", img_ini=None, img_fin=None)
    try:
        for f, p, c in (("2026-09-30", 1, "A"), ("2026-10-05", 2, "A"), ("2026-10-10", 4, "B"), ("2026-10-20", 8, "A")):
            db.db_insert(op(f, p, c))
        db.set_periodo_global(("2026-10-01", "2026-10-15"))
        assert sorted(o["profit"] for o in db.db_all()) == [2, 4]
        assert sorted(o["profit"] for o in db.db_all(fechas=False)) == [1, 2, 4, 8]       # calendario, simulador…
        assert len(db.db_all(todo=True)) == 4
        assert len(db.db_range("2026-09-01", "2026-10-31")) == 4                          # db_range recibe sus fechas
        db.set_periodo_global((None, "2026-10-05"))
        assert sorted(o["profit"] for o in db.db_all()) == [1, 2]
        db.set_periodo_global(("2026-10-06", None))
        assert sorted(o["profit"] for o in db.db_all()) == [4, 8]
        db.set_cuenta_global(("E", "A"))                                                   # se combina con la cuenta
        assert [o["profit"] for o in db.db_all()] == [8]
        db.set_periodo_global(None)
        assert sorted(o["profit"] for o in db.db_all()) == [1, 2, 8]
    finally:
        db.set_periodo_global(None); db.set_cuenta_global(None)

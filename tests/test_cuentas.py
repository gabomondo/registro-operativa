"""Tabla `cuentas` (migración 5): siembra desde lo cargado, alta automática, estado con historial."""
import sqlite3

import pytest

from registro import bootstrap, db


def _op(**kw):
    d = dict(fecha="2026-10-01", hora="10:00", activo="MNQ", tipo="ORB", profit=10, empresa="", cuenta="",
             mov_sl="", tranquilo="", emo=0, comentario="", img_ini=None, img_fin=None)
    d.update(kw)
    return d


def test_migracion_siembra_desde_operaciones(legacy_dir):
    bootstrap.iniciar(["--datos", str(legacy_dir)], env={})
    cs = {(c["empresa"], c["cuenta"]): c for c in db.db_cuentas()}
    assert set(cs) == {("TopStep", "Fondeada"), ("Lucid", "Challenge")}
    c = cs[("TopStep", "Fondeada")]
    assert c["n_ops"] == 1 and c["pnl"] == 500.0 and c["estado"] is None and c["alias"] is None


def test_alta_automatica_al_cargar(tmp_path):
    bootstrap.iniciar(["--datos", str(tmp_path)], env={})
    assert db.db_cuentas() == []
    db.db_insert(_op(empresa="Apex", cuenta="A1"))
    db.db_insert(_op(empresa="Apex", cuenta="A1", profit=-5))
    db.db_insert(_op())                                   # sin empresa ni cuenta: no crea ficha
    cs = db.db_cuentas()
    assert [(c["empresa"], c["cuenta"], c["n_ops"], c["pnl"]) for c in cs] == [("Apex", "A1", 2, 5.0)]
    oid = db.db_insert(_op(empresa="Apex", cuenta="A2"))
    db.db_update(oid, _op(empresa="Apex", cuenta="A3"))
    assert {c["cuenta"] for c in db.db_cuentas()} == {"A1", "A2", "A3"}


def test_estado_con_historial(tmp_path):
    bootstrap.iniciar(["--datos", str(tmp_path)], env={})
    cid = db.db_cuenta_guardar("Lucid", "50K-1", alias="Lucid principal", tipo="futuros", capital_inicial=50000,
                               estado="evaluacion")
    assert db.db_cuenta_set_estado(cid, "evaluacion") is False        # sin cambio: no registra
    assert db.db_cuenta_set_estado(cid, "fondeada", desde="2026-10-10") is True
    # editar datos sin tocar el estado no lo cambia ni agrega historial
    db.db_cuenta_guardar("Lucid", "50K-1", alias="Principal", tipo="futuros", capital_inicial=50000)
    c = db.db_cuentas()[0]
    assert c["estado"] == "fondeada" and c["alias"] == "Principal" and c["capital_inicial"] == 50000
    assert ("fondeada", "2026-10-10") in [(h["estado"], h["desde"]) for h in db.db_cuenta_historial(cid)]
    assert len(db.db_cuenta_historial(cid)) == 2
    db.db_cuenta_guardar("Lucid", "50K-1", estado=None)               # quitar etiqueta (opcional)
    assert db.db_cuentas()[0]["estado"] is None and len(db.db_cuenta_historial(cid)) == 3


def test_validaciones_y_borrado(tmp_path):
    bootstrap.iniciar(["--datos", str(tmp_path)], env={})
    with pytest.raises(ValueError):
        db.db_cuenta_guardar("X", "1", tipo="otra")
    with pytest.raises(ValueError):
        db.db_cuenta_guardar("X", "1", estado="rara")
    with pytest.raises(ValueError):
        db.db_cuenta_guardar("", "")
    db.db_insert(_op(empresa="Apex", cuenta="A1"))
    cid = db.db_cuentas()[0]["id"]
    db.db_cuenta_borrar(cid)
    assert db.db_cuentas() == [] and len(db.db_all()) == 1            # las operaciones quedan
    db.db_insert(_op(empresa="Apex", cuenta="A1"))                    # y la ficha reaparece
    assert len(db.db_cuentas()) == 1


def test_tipo_se_infiere_de_la_fuente(tmp_path):
    ctx = bootstrap.iniciar(["--datos", str(tmp_path)], env={})
    con = sqlite3.connect(ctx.rutas.db_path)
    for emp, fu in (("Exness", "mt5"), ("Topstep", "nt8"), ("Mixta", "mt5"), ("Mixta", "nt8"), ("Manual", "manual")):
        con.execute("INSERT INTO operaciones (fecha,empresa,cuenta,fuente,profit) VALUES ('2026-10-01',?,?,?,1)",
                    (emp, "c", fu))
    con.execute("PRAGMA user_version=4"); con.execute("DROP TABLE cuentas_estado"); con.execute("DROP TABLE cuentas")
    con.commit(); con.close()
    bootstrap.iniciar(["--datos", str(tmp_path)], env={})
    t = {c["empresa"]: c["tipo"] for c in db.db_cuentas()}
    assert t == {"Exness": "cfd", "Topstep": "futuros", "Mixta": None, "Manual": None}


def test_filtro_global_de_cuenta(tmp_path):
    bootstrap.iniciar(["--datos", str(tmp_path)], env={})
    try:
        db.db_insert(_op(empresa="Apex", cuenta="A1", profit=100))
        db.db_insert(_op(empresa="Apex", cuenta="A2", profit=-30, fecha="2026-10-02"))
        db.db_insert(_op(empresa="Lucid", cuenta="L1", profit=7, fecha="2026-10-03"))
        assert len(db.db_all()) == 3 and db.get_cuenta_global() is None
        db.set_cuenta_global(("Apex", "A1"))
        assert [o["profit"] for o in db.db_all()] == [100]
        assert [o["profit"] for o in db.db_range("2026-10-01", "2026-10-31")] == [100]
        assert len(db.db_all(todo=True)) == 3 and len(db.db_range("2026-10-01", "2026-10-31", todo=True)) == 3
        assert db.db_all({"desde": "2026-10-02"}) == []                       # se combina con los filtros propios
        db.set_cuenta_global(("Apex", "A2"))
        assert [o["profit"] for o in db.db_all({"desde": "2026-10-02"})] == [-30]
        db.set_cuenta_global(None)
        assert len(db.db_all()) == 3
    finally:
        db.set_cuenta_global(None)


def test_db_all_cuenta_false_ignora_solo_la_cuenta(tmp_path):
    bootstrap.iniciar(["--datos", str(tmp_path)], env={})
    try:
        db.db_insert(_op(empresa="A", cuenta="1", fecha="2026-10-01", profit=1))
        db.db_insert(_op(empresa="B", cuenta="2", fecha="2026-10-10", profit=2))
        db.db_insert(_op(empresa="B", cuenta="2", fecha="2026-09-10", profit=4))
        db.set_cuenta_global(("A", "1")); db.set_periodo_global(("2026-10-05", None))
        assert db.db_all() == []
        assert [o["profit"] for o in db.db_all(cuenta=False)] == [2]
    finally:
        db.set_cuenta_global(None); db.set_periodo_global(None)

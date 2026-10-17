import os, sqlite3, json
import pytest
from registro import db, perfil as P, paths, bootstrap

def rutas(d): return paths.asegurar(paths.Rutas(str(d), "argumento"))

def iniciar(d, preset=None):
    return bootstrap.iniciar(["--datos", str(d)] + (["--perfil", preset] if preset else []), env={})

# ---------- migración de una base de la versión anterior ----------
def test_migra_base_vieja_sin_perder_datos(legacy_dir):
    ctx = iniciar(legacy_dir)
    assert ctx.migracion["desde"] == 0 and ctx.migracion["hasta"] == db.SCHEMA_VERSION
    assert ctx.migracion["backup"] and os.path.exists(ctx.migracion["backup"])
    con = db.connect()
    assert con.execute("SELECT COUNT(*), SUM(profit) FROM operaciones").fetchone()[:] == (2, 300.0)
    assert con.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    assert con.execute("SELECT COUNT(*) FROM operaciones WHERE fuente='manual'").fetchone()[0] == 2
    # el plan viejo se conserva (no lo pisa el del perfil)
    assert db.db_get_plan()[0] == "mi plan viejo"
    # los checks viejos pasan a la plantilla original y conservan sus tildes
    ops = db.db_all()
    assert all(o["tpl_id"] for o in ops)
    assert json.loads(ops[0]["chk_data"])["chk_riesgo"] == 1
    con.close()

def test_backup_previo_tiene_los_datos_originales(legacy_dir):
    ctx = iniciar(legacy_dir)
    b = sqlite3.connect(ctx.migracion["backup"])
    assert b.execute("SELECT COUNT(*) FROM operaciones").fetchone()[0] == 2
    assert b.execute("PRAGMA user_version").fetchone()[0] == 0     # tal cual estaba
    b.close()

def test_migrar_es_idempotente(legacy_dir):
    iniciar(legacy_dir)
    ctx2 = iniciar(legacy_dir)
    assert ctx2.migracion == {"desde": db.SCHEMA_VERSION, "hasta": db.SCHEMA_VERSION, "backup": None}
    assert not ctx2.perfil_nuevo
    assert db.db_templates().__len__() == 1

def test_base_nueva_no_hace_backup_y_siembra_el_perfil(tmp_path):
    ctx = iniciar(tmp_path / "d")
    assert ctx.migracion["backup"] is None
    assert [t["nombre"] for t in db.db_templates()] == ["Check básico"]
    assert "Mi plan de trading" in db.db_get_plan()[0]
    assert db.db_all() == []

def test_plantilla_borrada_no_reaparece(tmp_path):
    iniciar(tmp_path / "d")
    db.db_template_delete(db.db_templates()[0]["id"])
    iniciar(tmp_path / "d")
    assert db.db_templates() == []

def test_base_mas_nueva_se_rechaza_sin_tocarla(tmp_path):
    r = rutas(tmp_path)
    con = sqlite3.connect(r.db_path); con.execute("PRAGMA user_version=99"); con.commit(); con.close()
    with pytest.raises(db.BaseMasNuevaError):
        db.migrar(r.db_path, r.backups_dir)
    assert sqlite3.connect(r.db_path).execute("PRAGMA user_version").fetchone()[0] == 99

def test_migracion_que_falla_revierte_y_deja_backup(legacy_dir):
    r = rutas(legacy_dir)
    def rota(con):
        con.execute("ALTER TABLE operaciones ADD COLUMN columna_nueva TEXT")
        raise RuntimeError("boom")
    migs = {1: db._m1_base, 2: rota}
    with pytest.raises(db.MigracionError) as e:
        db.migrar(r.db_path, r.backups_dir, migraciones=migs)
    assert "boom" in str(e.value)
    con = sqlite3.connect(r.db_path)
    cols = {c[1] for c in con.execute("PRAGMA table_info(operaciones)")}
    assert "columna_nueva" not in cols                       # revertida
    assert con.execute("PRAGMA user_version").fetchone()[0] == 1   # la 1 sí se aplicó
    assert con.execute("SELECT COUNT(*) FROM operaciones").fetchone()[0] == 2
    assert db.listar_backups(r.backups_dir)                  # y hay copia previa

# ---------- importadores: columnas + índice único ----------
def test_indice_unico_evita_duplicar_importaciones(tmp_path):
    iniciar(tmp_path / "d")
    base = dict(fecha="2026-10-14", hora="09:46", activo="MNQ", tipo="ORB", profit=10.0,
                empresa="x", cuenta="Demo", mov_sl="No", tranquilo="Sí", emo=3, comentario="",
                img_ini=None, img_fin=None, chk_data={}, tpl_id=None)
    db.db_insert({**base, "fuente": "nt8", "cuenta_ext": "A1", "ext_id": "T-1"})
    with pytest.raises(sqlite3.IntegrityError):
        db.db_insert({**base, "fuente": "nt8", "cuenta_ext": "A1", "ext_id": "T-1"})
    db.db_insert({**base, "fuente": "nt8", "cuenta_ext": "A2", "ext_id": "T-1"})   # otra cuenta: ok
    db.db_insert({**base})                                                          # manuales: sin límite
    db.db_insert({**base})
    assert len(db.db_all()) == 4

def test_insert_update_roundtrip_con_extras(tmp_path):
    iniciar(tmp_path / "d")
    base = dict(fecha="2026-10-14", hora="09:46", activo="MNQ", tipo="ORB", profit=10.0,
                empresa="x", cuenta="Demo", mov_sl="No", tranquilo="Sí", emo=3, comentario="c",
                img_ini=None, img_fin=None, chk_data={"a": 1}, tpl_id=None)
    i = db.db_insert({**base, "contratos": 3, "comision": 2.1})
    db.db_update(i, {**base, "profit": 99.0})
    o = db.db_all()[0]
    assert o["profit"] == 99.0 and o["contratos"] == 3 and o["fuente"] == "manual"

# ---------- backups ----------
def test_backup_diario_una_vez_por_dia_y_rota(tmp_path):
    iniciar(tmp_path / "d")
    r = rutas(tmp_path / "d")
    hoy = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    assert db.backup_diario(r.db_path, r.backups_dir, hoy=hoy) is None   # ya lo hizo iniciar()
    for dia in range(1, 20):
        db.backup_diario(r.db_path, r.backups_dir, mantener=5, hoy=f"2026-11-{dia:02d}")
    autos = [f for f in os.listdir(r.backups_dir) if "auto" in f]
    assert len(autos) == 5

def test_restaurar_backup_conserva_la_actual(tmp_path):
    ctx = iniciar(tmp_path / "d")
    r = ctx.rutas
    bk = db.crear_backup(r.db_path, r.backups_dir, "manual")
    base = dict(fecha="2026-10-14", hora="09:46", activo="MNQ", tipo="ORB", profit=1.0, empresa="",
                cuenta="Demo", mov_sl="No", tranquilo="Sí", emo=3, comentario="", img_ini=None,
                img_fin=None, chk_data={}, tpl_id=None)
    db.db_insert(base); assert len(db.db_all()) == 1
    previo = db.restaurar_backup(bk, r.db_path, r.backups_dir)
    assert len(db.db_all()) == 0
    assert sqlite3.connect(previo).execute("SELECT COUNT(*) FROM operaciones").fetchone()[0] == 1

def test_copiar_datos(legacy_dir, tmp_path):
    ctx = iniciar(legacy_dir)
    (legacy_dir / "capturas" / "a.png").write_bytes(b"png")
    destino = tmp_path / "drive"
    db.copiar_datos(str(legacy_dir), str(destino))
    assert (destino / "capturas" / "a.png").exists() and (destino / "perfil.json").exists()
    assert sqlite3.connect(destino / "registro.db").execute("SELECT COUNT(*) FROM operaciones").fetchone()[0] == 2

def test_borrar_operacion_borra_sus_capturas(tmp_path):
    ctx = iniciar(tmp_path / "d")
    cap = os.path.join(ctx.rutas.caps_dir, "x.png"); open(cap, "wb").write(b"1")
    base = dict(fecha="2026-10-14", hora="09:46", activo="MNQ", tipo="ORB", profit=1.0, empresa="",
                cuenta="Demo", mov_sl="No", tranquilo="Sí", emo=3, comentario="", img_ini=None,
                img_fin=os.path.join("capturas", "x.png"), chk_data={}, tpl_id=None)
    i = db.db_insert(base); db.db_delete(i)
    assert not os.path.exists(cap)

def test_migra_de_v2_a_v3_conserva_datos(tmp_path):
    """Una base creada por la fase 1 (esquema 2) sube a 3 con backup y sin perder filas."""
    ctx = iniciar(tmp_path)
    con = sqlite3.connect(ctx.rutas.db_path)
    con.execute("INSERT INTO operaciones (fecha,profit,fuente) VALUES ('2026-01-01', 50, 'manual')")
    con.execute("ALTER TABLE operaciones DROP COLUMN bruto"); con.execute("ALTER TABLE operaciones DROP COLUMN motivo_cierre")
    con.execute("PRAGMA user_version=2"); con.commit(); con.close()
    ctx2 = iniciar(tmp_path)
    assert ctx2.migracion["desde"] == 2 and ctx2.migracion["hasta"] == db.SCHEMA_VERSION and ctx2.migracion["backup"]
    ops = db.db_all()
    assert len(ops) == 1 and ops[0]["profit"] == 50 and "bruto" in ops[0] and "motivo_cierre" in ops[0]
    tipos = {r[1]: r[2] for r in sqlite3.connect(ctx2.rutas.db_path).execute("PRAGMA table_info(operaciones)")}
    assert tipos["bruto"] == "REAL" and tipos["motivo_cierre"] == "TEXT"

def test_pnl_por_dia(tmp_path):
    iniciar(tmp_path)
    for f, p in (("2026-10-01", 10), ("2026-10-01", -4), ("2026-10-02", -3)):
        con = sqlite3.connect(tmp_path / "registro.db"); con.execute("INSERT INTO operaciones (fecha,profit,fuente) VALUES (?,?,'manual')", (f, p)); con.commit(); con.close()
    assert db.db_pnl_por_dia() == {"2026-10-01": 6, "2026-10-02": -3}

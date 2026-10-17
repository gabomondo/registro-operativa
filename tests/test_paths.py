import os
from registro import paths

def args(**kw):
    a = paths.parse_args([])
    for k, v in kw.items(): setattr(a, k, v)
    return a

def test_prioridad_argumento_sobre_todo(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "app_dir", lambda: str(tmp_path / "app"))
    r = paths.resolver_datos(args(datos=str(tmp_path / "x")), env={"REGISTRO_DATOS": str(tmp_path / "y")})
    assert r.origen == "argumento" and r.data_dir == str(tmp_path / "x")

def test_entorno(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "app_dir", lambda: str(tmp_path / "app"))
    r = paths.resolver_datos(args(), env={"REGISTRO_DATOS": str(tmp_path / "y")})
    assert r.origen == "entorno"

def test_portable_si_hay_db_junto_al_programa(tmp_path, monkeypatch):
    app = tmp_path / "app"; app.mkdir(); (app / "registro.db").write_bytes(b"")
    monkeypatch.setattr(paths, "app_dir", lambda: str(app))
    monkeypatch.setattr(paths, "appdata_root", lambda: str(tmp_path / "ad"))
    r = paths.resolver_datos(args(), env={})
    assert r.origen == "portable" and r.data_dir == str(app)

def test_portable_flag(tmp_path, monkeypatch):
    app = tmp_path / "app"; app.mkdir(); (app / "portable.flag").write_text("")
    monkeypatch.setattr(paths, "app_dir", lambda: str(app))
    monkeypatch.setattr(paths, "appdata_root", lambda: str(tmp_path / "ad"))
    assert paths.resolver_datos(args(), env={}).origen == "portable"

def test_puntero_y_default(tmp_path, monkeypatch):
    app = tmp_path / "app"; app.mkdir()
    ad = tmp_path / "ad"
    monkeypatch.setattr(paths, "app_dir", lambda: str(app))
    monkeypatch.setattr(paths, "appdata_root", lambda: str(ad))
    assert paths.resolver_datos(args(), env={}).origen == "appdata"
    destino = tmp_path / "drive"; destino.mkdir()
    paths.guardar_puntero(str(destino))
    r = paths.resolver_datos(args(), env={})
    assert r.origen == "ubicacion" and r.data_dir == str(destino)
    paths.borrar_puntero()
    assert paths.resolver_datos(args(), env={}).origen == "appdata"

def test_puntero_a_carpeta_inexistente_se_ignora(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "app_dir", lambda: str(tmp_path / "app"))
    monkeypatch.setattr(paths, "appdata_root", lambda: str(tmp_path / "ad"))
    paths.guardar_puntero(str(tmp_path / "no_existe"))
    assert paths.resolver_datos(args(), env={}).origen == "appdata"

def test_asegurar_crea_carpetas(tmp_path):
    r = paths.asegurar(paths.Rutas(str(tmp_path / "datos"), "argumento"))
    for d in (r.caps_dir, r.backups_dir, r.logs_dir): assert os.path.isdir(d)

def test_asegurar_falla_claro_si_no_se_puede_escribir(tmp_path):
    archivo = tmp_path / "archivo"; archivo.write_text("x")
    import pytest
    with pytest.raises((PermissionError, OSError)):
        paths.asegurar(paths.Rutas(str(archivo / "sub"), "argumento"))

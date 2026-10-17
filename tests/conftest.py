import os, sys, sqlite3
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LEGACY_SCHEMA = """
CREATE TABLE operaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, hora TEXT, activo TEXT,
    tipo TEXT, profit REAL, empresa TEXT, cuenta TEXT, mov_sl TEXT, tranquilo TEXT,
    emo INTEGER, comentario TEXT, img_ini TEXT, img_fin TEXT,
    chk_riesgo INTEGER DEFAULT 0, chk_sl_fijo INTEGER DEFAULT 0, chk_sesgo INTEGER DEFAULT 0,
    chk_rango INTEGER DEFAULT 0, chk_ventana INTEGER DEFAULT 0, chk_num INTEGER DEFAULT 0);
CREATE TABLE plan (id INTEGER PRIMARY KEY CHECK (id = 1), texto TEXT, actualizado TEXT);
INSERT INTO plan VALUES (1, 'mi plan viejo', '2026-08-01T10:00:00');
"""

@pytest.fixture
def legacy_dir(tmp_path):
    """Carpeta con una base creada por la versión anterior (sin user_version,
    sin tpl_id/chk_data, sin plantillas)."""
    con = sqlite3.connect(tmp_path / "registro.db")
    con.executescript(LEGACY_SCHEMA)
    con.executemany(
        "INSERT INTO operaciones (fecha,hora,activo,tipo,profit,empresa,cuenta,mov_sl,tranquilo,emo,"
        "comentario,chk_riesgo,chk_sl_fijo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [("2026-08-04", "09:35", "NQ", "ORB", 500.0, "TopStep", "Fondeada", "No", "Sí", 4, "ok", 1, 1),
         ("2026-08-05", "10:10", "MNQ", "Estructura", -200.0, "Lucid", "Challenge", "Sí (en contra)", "No", 2, "mal", 1, 0)])
    con.commit(); con.close()
    return tmp_path

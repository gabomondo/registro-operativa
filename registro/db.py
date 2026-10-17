"""Capa de datos: conexión, migraciones versionadas con backup, backups y CRUD.

Conexión corta por operación + WAL (resistente a sync de Drive).

Migraciones: la versión del esquema vive en PRAGMA user_version. Antes de aplicar
cualquier migración sobre una base que ya tiene datos se hace una copia en
backups/. Cada migración corre en una transacción: si falla, se revierte y la
base queda como estaba.
"""

import glob
import json
import os
import re
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

from .constantes import CHECK_ITEMS, CHECK_KEYS, LEGACY_TEMPLATE_NAME

SCHEMA_VERSION = 5

# Columnas que agregan los importadores (migración 2). Todas opcionales.
EXTRA_COLS_V2 = ["fuente", "ext_id", "cuenta_ext", "lado", "contratos",
                 "precio_ini", "precio_fin", "hora_fin", "comision", "riesgo_plan"]
EXTRA_COLS = EXTRA_COLS_V2 + ["bruto", "motivo_cierre"]


class MigracionError(Exception):
    pass


class BaseMasNuevaError(Exception):
    pass


# ---------------------------------------------------------------------------
# Configuración (la fija bootstrap.iniciar)
# ---------------------------------------------------------------------------
_cfg = {"rutas": None, "perfil": None}


def configurar(rutas, perfil):
    _cfg["rutas"] = rutas
    _cfg["perfil"] = perfil


def set_perfil(perfil):
    _cfg["perfil"] = perfil


def _rutas():
    if _cfg["rutas"] is None:
        raise RuntimeError("db.configurar() no fue llamado")
    return _cfg["rutas"]


def connect():
    con = sqlite3.connect(_rutas().db_path, timeout=10)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.row_factory = sqlite3.Row
    return con


@contextmanager
def _tx():
    """Conexión con commit/rollback y cierre garantizados, incluso si falla
    (p. ej. IntegrityError al reimportar un trade ya cargado)."""
    con = connect()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------
def _copiar_sqlite(origen, destino):
    """Copia consistente aunque la base esté abierta o en WAL."""
    src = sqlite3.connect(origen, timeout=10)
    try:
        dst = sqlite3.connect(destino)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def crear_backup(db_path, backups_dir, etiqueta):
    os.makedirs(backups_dir, exist_ok=True)
    dest = os.path.join(backups_dir, f"registro_{etiqueta}_{datetime.now():%Y%m%d-%H%M%S}.db")
    _copiar_sqlite(db_path, dest)
    return dest


def backup_diario(db_path, backups_dir, mantener=14, hoy=None):
    """Una copia por día al abrir la app. Conserva las últimas `mantener`;
    los backups 'pre-...' (previos a migrar/restaurar) nunca se borran solos."""
    if not os.path.exists(db_path):
        return None
    hoy = hoy or datetime.now().strftime("%Y-%m-%d")
    os.makedirs(backups_dir, exist_ok=True)
    dest = os.path.join(backups_dir, f"registro_auto_{hoy}.db")
    creado = None
    if not os.path.exists(dest):
        _copiar_sqlite(db_path, dest)
        creado = dest
    autos = sorted(glob.glob(os.path.join(backups_dir, "registro_auto_*.db")))
    for viejo in autos[:-mantener]:
        try:
            os.remove(viejo)
        except OSError:
            pass
    return creado


def listar_backups(backups_dir):
    return sorted(glob.glob(os.path.join(backups_dir, "registro_*.db")), reverse=True)


def restaurar_backup(backup_path, db_path, backups_dir):
    """Reemplaza la base actual por un backup. Antes guarda la actual como
    'pre-restaurar' por si fue un error."""
    previo = None
    if os.path.exists(db_path):
        previo = crear_backup(db_path, backups_dir, "pre-restaurar")
    src = sqlite3.connect(backup_path)
    try:
        dst = sqlite3.connect(db_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return previo


def copiar_datos(src_dir, dst_dir):
    """Copia base, capturas, perfil y preferencias a otra carpeta (para mover la
    carpeta de datos, p. ej. a Google Drive)."""
    os.makedirs(dst_dir, exist_ok=True)
    db_src = os.path.join(src_dir, "registro.db")
    if os.path.exists(db_src):
        _copiar_sqlite(db_src, os.path.join(dst_dir, "registro.db"))
    for nombre in ("perfil.json", "ui_prefs.json"):
        p = os.path.join(src_dir, nombre)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(dst_dir, nombre))
    caps = os.path.join(src_dir, "capturas")
    if os.path.isdir(caps):
        shutil.copytree(caps, os.path.join(dst_dir, "capturas"), dirs_exist_ok=True)


# ---------------------------------------------------------------------------
# Migraciones
# ---------------------------------------------------------------------------
def _columnas(con, tabla):
    return {r[1] for r in con.execute(f"PRAGMA table_info({tabla})")}


def _m1_base(con):
    """Esquema original. Idempotente: sirve igual para una base nueva que para
    una creada por la versión anterior (que no tenía user_version)."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS operaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            hora TEXT,
            activo TEXT,
            tipo TEXT,
            profit REAL,
            empresa TEXT,
            cuenta TEXT,
            mov_sl TEXT,
            tranquilo TEXT,
            emo INTEGER,
            comentario TEXT,
            img_ini TEXT,
            img_fin TEXT
        )
    """)
    existing = _columnas(con, "operaciones")
    for key in CHECK_KEYS:                       # columnas del check viejo (se conservan)
        if key not in existing:
            con.execute(f"ALTER TABLE operaciones ADD COLUMN {key} INTEGER DEFAULT 0")
    if "tpl_id" not in existing:
        con.execute("ALTER TABLE operaciones ADD COLUMN tpl_id INTEGER")
    if "chk_data" not in existing:
        con.execute("ALTER TABLE operaciones ADD COLUMN chk_data TEXT")
    con.execute("""
        CREATE TABLE IF NOT EXISTS check_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            items TEXT NOT NULL,        -- JSON: [{"id": "...", "label": "..."}, ...]
            actualizado TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS plan (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            texto TEXT,
            actualizado TEXT
        )
    """)


def _m2_importadores(con):
    """Columnas para trades importados (NT8, MT5, Tradovate, TopstepX), tabla
    meta y un índice único que evita duplicar al reimportar el mismo archivo."""
    existing = _columnas(con, "operaciones")
    tipos = {"contratos": "REAL", "precio_ini": "REAL", "precio_fin": "REAL",
             "comision": "REAL", "riesgo_plan": "REAL"}
    for col in EXTRA_COLS_V2:
        if col not in existing:
            con.execute(f"ALTER TABLE operaciones ADD COLUMN {col} {tipos.get(col, 'TEXT')}")
    con.execute("UPDATE operaciones SET fuente='manual' WHERE fuente IS NULL")
    con.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS ix_ops_fecha ON operaciones(fecha)")
    con.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_ops_origen
        ON operaciones(fuente, cuenta_ext, ext_id) WHERE ext_id IS NOT NULL
    """)


def _m3_bruto_motivo(con):
    """P&L bruto (antes de costos) y motivo de cierre (SL / TP / Manual)."""
    existing = _columnas(con, "operaciones")
    if "bruto" not in existing:
        con.execute("ALTER TABLE operaciones ADD COLUMN bruto REAL")
    if "motivo_cierre" not in existing:
        con.execute("ALTER TABLE operaciones ADD COLUMN motivo_cierre TEXT")


def _m4_playbooks_notas(con):
    """Playbooks (un setup con sus reglas; se vincula a las operaciones por el
    nombre, que es el 'tipo' de entrada) y notas diarias (notebook)."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS playbooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            descripcion TEXT,
            reglas TEXT,
            actualizado TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS notas (
            fecha TEXT PRIMARY KEY,
            plan TEXT,
            que_paso TEXT,
            corregir TEXT,
            actualizado TEXT
        )
    """)


def _m5_cuentas(con):
    """Tabla `cuentas` (empresa + cuenta del diario, alias, tipo, estado y capital
    inicial opcionales) y su historial de estado. `operaciones` no cambia: se
    vincula por (empresa, cuenta). Se siembra con lo que ya hay cargado."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS cuentas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa TEXT NOT NULL DEFAULT '',
            cuenta TEXT NOT NULL DEFAULT '',
            alias TEXT,
            tipo TEXT,              -- 'futuros' | 'cfd' | NULL
            estado TEXT,            -- ver ESTADOS_CUENTA; NULL = sin etiqueta
            capital_inicial REAL,
            creada TEXT,
            actualizado TEXT,
            UNIQUE (empresa, cuenta)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS cuentas_estado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id INTEGER NOT NULL REFERENCES cuentas(id) ON DELETE CASCADE,
            estado TEXT,
            desde TEXT NOT NULL,
            nota TEXT
        )
    """)
    ahora = datetime.now().isoformat(timespec="seconds")
    filas = con.execute("""
        SELECT COALESCE(empresa,'') AS e, COALESCE(cuenta,'') AS c,
               SUM(fuente='mt5') AS n_mt5,
               SUM(fuente IN ('nt8','tradovate','topstepx')) AS n_fut
        FROM operaciones
        GROUP BY COALESCE(empresa,''), COALESCE(cuenta,'')
        HAVING e <> '' OR c <> ''
    """).fetchall()
    for e, c, n_mt5, n_fut in filas:
        tipo = "cfd" if (n_mt5 or 0) and not (n_fut or 0) else "futuros" if (n_fut or 0) and not (n_mt5 or 0) else None
        con.execute("INSERT OR IGNORE INTO cuentas (empresa,cuenta,tipo,creada,actualizado) VALUES (?,?,?,?,?)",
                    (e, c, tipo, ahora, ahora))


MIGRACIONES = {1: _m1_base, 2: _m2_importadores, 3: _m3_bruto_motivo,
               4: _m4_playbooks_notas, 5: _m5_cuentas}


def _tiene_datos(con):
    return con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0] > 0


def migrar(db_path, backups_dir, migraciones=None, version_objetivo=None):
    """Lleva la base a la última versión. Devuelve
    {'desde': n, 'hasta': n, 'backup': ruta|None}."""
    migraciones = migraciones or MIGRACIONES
    objetivo = version_objetivo or max(migraciones)
    con = sqlite3.connect(db_path, timeout=10, isolation_level=None)  # transacciones manuales
    try:
        con.execute("PRAGMA journal_mode=WAL")
        actual = con.execute("PRAGMA user_version").fetchone()[0]
        if actual > objetivo:
            raise BaseMasNuevaError(
                f"Esta base es de una versión más nueva del programa (esquema {actual}, "
                f"esta versión entiende hasta {objetivo}). Actualizá la aplicación.")
        info = {"desde": actual, "hasta": actual, "backup": None}
        pendientes = list(range(actual + 1, objetivo + 1))
        if not pendientes:
            return info
        if _tiene_datos(con):
            info["backup"] = crear_backup(db_path, backups_dir, f"pre-v{objetivo}")
        for n in pendientes:
            try:
                con.execute("BEGIN")
                migraciones[n](con)
                con.execute(f"PRAGMA user_version={n}")
                con.execute("COMMIT")
            except Exception as e:
                try:
                    con.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise MigracionError(
                    f"Falló la migración a la versión {n}: {e}. "
                    f"La base quedó como estaba"
                    + (f" y hay una copia en {info['backup']}" if info["backup"] else "")) from e
            info["hasta"] = n
        return info
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Sembrado inicial (según el perfil) y compatibilidad con datos viejos
# ---------------------------------------------------------------------------
def meta_get(con, clave, default=None):
    r = con.execute("SELECT valor FROM meta WHERE clave=?", (clave,)).fetchone()
    return r[0] if r else default


def meta_set(con, clave, valor):
    con.execute("INSERT INTO meta (clave, valor) VALUES (?,?) "
                "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor", (clave, str(valor)))


def _migrar_checks_legacy(con):
    """Operaciones viejas sin plantilla -> plantilla 'ORB NY (original)', copiando
    sus tildes chk_* a chk_data. Solo actúa si hay operaciones pendientes."""
    pending = con.execute("SELECT * FROM operaciones WHERE tpl_id IS NULL").fetchall()
    if not pending:
        return
    row = con.execute("SELECT id FROM check_templates WHERE nombre=?",
                      (LEGACY_TEMPLATE_NAME,)).fetchone()
    if row is None:
        items = [{"id": k, "label": lbl} for k, lbl in CHECK_ITEMS]
        cur = con.execute(
            "INSERT INTO check_templates (nombre, items, actualizado) VALUES (?,?,?)",
            (LEGACY_TEMPLATE_NAME, json.dumps(items, ensure_ascii=False),
             datetime.now().isoformat(timespec="seconds")))
        legacy_id = cur.lastrowid
    else:
        legacy_id = row["id"]
    for o in pending:
        data = {k: int(o[k] or 0) for k in CHECK_KEYS}
        con.execute("UPDATE operaciones SET tpl_id=?, chk_data=? WHERE id=?",
                    (legacy_id, json.dumps(data, ensure_ascii=False), o["id"]))


def _sembrar(con, perfil):
    """Plan y plantilla de check iniciales, tomados del perfil. El plan solo se
    crea si no existe fila; la plantilla solo la primera vez (si el usuario
    las borra después, no reaparecen)."""
    ahora = datetime.now().isoformat(timespec="seconds")
    if con.execute("SELECT 1 FROM plan WHERE id=1").fetchone() is None:
        con.execute("INSERT INTO plan (id, texto, actualizado) VALUES (1, ?, ?)",
                    (perfil.plan_inicial, ahora))
    if meta_get(con, "sembrado") is None:
        if con.execute("SELECT COUNT(*) FROM check_templates").fetchone()[0] == 0:
            pl = perfil.plantilla_inicial
            con.execute("INSERT INTO check_templates (nombre, items, actualizado) VALUES (?,?,?)",
                        (pl["nombre"], json.dumps(pl["items"], ensure_ascii=False), ahora))
        meta_set(con, "sembrado", "1")
        meta_set(con, "creada_con", "registro-1.0")


def init_db():
    """Migra, siembra y deja la base lista. Devuelve la info de la migración."""
    rutas = _rutas()
    info = migrar(rutas.db_path, rutas.backups_dir)
    con = connect()
    try:
        _migrar_checks_legacy(con)
        _sembrar(con, _cfg["perfil"])
        con.commit()
    finally:
        con.close()
    return info


# ---------------------------------------------------------------------------
# Plantillas de check
# ---------------------------------------------------------------------------
def _tpl_row(r):
    try:
        items = json.loads(r["items"]) or []
    except Exception:
        items = []
    return {"id": r["id"], "nombre": r["nombre"], "items": items}


def db_templates():
    """Todas las plantillas, como lista de dicts {id, nombre, items:[...]}."""
    con = connect()
    rows = con.execute("SELECT * FROM check_templates ORDER BY id").fetchall()
    con.close()
    return [_tpl_row(r) for r in rows]


def db_template(tpl_id):
    con = connect()
    r = con.execute("SELECT * FROM check_templates WHERE id=?", (tpl_id,)).fetchone()
    con.close()
    return _tpl_row(r) if r else None


def db_template_save(nombre, items, tpl_id=None):
    """Crea (tpl_id=None) o actualiza una plantilla. Devuelve el id."""
    payload = json.dumps(items, ensure_ascii=False)
    now = datetime.now().isoformat(timespec="seconds")
    with _tx() as con:
        if tpl_id is None:
            cur = con.execute(
                "INSERT INTO check_templates (nombre, items, actualizado) VALUES (?,?,?)",
                (nombre, payload, now))
            tpl_id = cur.lastrowid
        else:
            con.execute(
                "UPDATE check_templates SET nombre=?, items=?, actualizado=? WHERE id=?",
                (nombre, payload, now, tpl_id))
    return tpl_id


def db_template_delete(tpl_id):
    """Las operaciones que la usaron conservan su chk_data."""
    with _tx() as con:
        con.execute("DELETE FROM check_templates WHERE id=?", (tpl_id,))


def db_template_usage(tpl_id):
    con = connect()
    n = con.execute("SELECT COUNT(*) FROM operaciones WHERE tpl_id=?", (tpl_id,)).fetchone()[0]
    con.close()
    return n


def new_item_id():
    import uuid
    return "it_" + uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------
def db_get_plan():
    con = connect()
    row = con.execute("SELECT texto, actualizado FROM plan WHERE id=1").fetchone()
    con.close()
    if row:
        return row["texto"], row["actualizado"]
    return _cfg["perfil"].plan_inicial, None


def db_save_plan(texto):
    with _tx() as con:
        con.execute("UPDATE plan SET texto=?, actualizado=? WHERE id=1",
                    (texto, datetime.now().isoformat(timespec="seconds")))


# ---------------------------------------------------------------------------
# Operaciones
# ---------------------------------------------------------------------------
_BASE_COLS = ["fecha", "hora", "activo", "tipo", "profit", "empresa", "cuenta",
              "mov_sl", "tranquilo", "emo", "comentario", "img_ini", "img_fin"]


def _valores(data):
    """(columnas, valores) para insertar/actualizar: base + plantilla + check
    legacy + extras de importación presentes en `data`."""
    cols = list(_BASE_COLS) + ["tpl_id", "chk_data"] + list(CHECK_KEYS)
    vals = [data[c] for c in _BASE_COLS]
    vals += [data.get("tpl_id"), json.dumps(data.get("chk_data") or {}, ensure_ascii=False)]
    vals += [int(data.get(k, 0) or 0) for k in CHECK_KEYS]
    for c in EXTRA_COLS:
        if c in data:
            cols.append(c)
            vals.append(data[c])
    return cols, vals


def db_insert(data):
    data = dict(data)
    data.setdefault("fuente", "manual")
    cols, vals = _valores(data)
    with _tx() as con:
        cur = con.execute(
            f"INSERT INTO operaciones ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)
        _cuenta_asegurar(con, data.get("empresa"), data.get("cuenta"))
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Cuentas (empresa + cuenta del diario)
# ---------------------------------------------------------------------------
ESTADOS_CUENTA = {"evaluacion": "Evaluación", "fondeada": "Fondeada", "demo": "Demo (testeo)",
                  "real_futuros": "Real futuros", "real_cfd": "Real CFD"}
TIPOS_CUENTA = {"futuros": "Futuros", "cfd": "CFD"}


def _cuenta_asegurar(con, empresa, cuenta):
    """Crea la cuenta si no existe (sin pisar nada). Devuelve su id o None si
    empresa y cuenta están vacías."""
    e, c = (empresa or "").strip(), (cuenta or "").strip()
    if not e and not c:
        return None
    ahora = datetime.now().isoformat(timespec="seconds")
    con.execute("INSERT OR IGNORE INTO cuentas (empresa,cuenta,creada,actualizado) VALUES (?,?,?,?)",
                (e, c, ahora, ahora))
    return con.execute("SELECT id FROM cuentas WHERE empresa=? AND cuenta=?", (e, c)).fetchone()[0]


def db_cuentas():
    """Todas las cuentas con cantidad de operaciones y P&L acumulado."""
    con = connect()
    rows = con.execute("""
        SELECT cu.*, COUNT(o.id) AS n_ops, COALESCE(SUM(o.profit),0) AS pnl
        FROM cuentas cu
        LEFT JOIN operaciones o ON COALESCE(o.empresa,'')=cu.empresa AND COALESCE(o.cuenta,'')=cu.cuenta
        GROUP BY cu.id ORDER BY cu.empresa, cu.cuenta
    """).fetchall()
    con.close()
    return [dict(r) for r in rows]


def db_cuenta_guardar(empresa, cuenta, alias=None, tipo=None, capital_inicial=None, estado=...):
    """Alta o edición de una cuenta. `estado=...` (por defecto) no lo toca; con un
    valor (o None para quitar la etiqueta) lo cambia y registra el cambio."""
    if tipo not in (None, "") and tipo not in TIPOS_CUENTA:
        raise ValueError(f"tipo inválido: {tipo}")
    if estado is not ... and estado not in (None, "") and estado not in ESTADOS_CUENTA:
        raise ValueError(f"estado inválido: {estado}")
    with _tx() as con:
        cid = _cuenta_asegurar(con, empresa, cuenta)
        if cid is None:
            raise ValueError("la cuenta necesita empresa o nombre")
        con.execute("UPDATE cuentas SET alias=?, tipo=?, capital_inicial=?, actualizado=? WHERE id=?",
                    ((alias or "").strip() or None, tipo or None, capital_inicial,
                     datetime.now().isoformat(timespec="seconds"), cid))
        if estado is not ...:
            _cuenta_set_estado(con, cid, estado or None)
        return cid


def _cuenta_set_estado(con, cid, estado, desde=None, nota=None):
    actual = con.execute("SELECT estado FROM cuentas WHERE id=?", (cid,)).fetchone()[0]
    if actual == estado:
        return False
    con.execute("UPDATE cuentas SET estado=?, actualizado=? WHERE id=?",
                (estado, datetime.now().isoformat(timespec="seconds"), cid))
    con.execute("INSERT INTO cuentas_estado (cuenta_id,estado,desde,nota) VALUES (?,?,?,?)",
                (cid, estado, desde or date.today().isoformat(), nota))
    return True


def db_cuenta_set_estado(cid, estado, desde=None, nota=None):
    """Cambia el estado (None = sin etiqueta) y guarda la fecha del cambio.
    Devuelve False si ya tenía ese estado."""
    if estado not in (None, "") and estado not in ESTADOS_CUENTA:
        raise ValueError(f"estado inválido: {estado}")
    with _tx() as con:
        return _cuenta_set_estado(con, cid, estado or None, desde, nota)


def db_cuenta_historial(cid):
    con = connect()
    rows = con.execute("SELECT * FROM cuentas_estado WHERE cuenta_id=? ORDER BY desde, id", (cid,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def db_cuenta_borrar(cid):
    """Solo borra la ficha: las operaciones quedan (y la cuenta reaparece si se
    vuelve a cargar algo con ese empresa/cuenta)."""
    with _tx() as con:
        con.execute("DELETE FROM cuentas_estado WHERE cuenta_id=?", (cid,))
        con.execute("DELETE FROM cuentas WHERE id=?", (cid,))


def db_pnl_por_dia():
    """{'2026-10-14': pnl del día} para marcar en el calendario los días operados."""
    con = connect()
    try:
        return {r[0]: (r[1] or 0.0) for r in con.execute(
            "SELECT fecha, SUM(profit) FROM operaciones GROUP BY fecha")}
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Playbooks y notas diarias
# ---------------------------------------------------------------------------
def db_playbooks():
    con = connect()
    try:
        return [dict(r) for r in con.execute("SELECT * FROM playbooks ORDER BY nombre COLLATE NOCASE")]
    finally:
        con.close()


def db_playbook_save(nombre, descripcion="", reglas="", viejo_nombre=None):
    """Crea o actualiza un playbook. Si cambia el nombre, renombra también el
    'tipo' de las operaciones que lo usaban."""
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El playbook necesita un nombre.")
    ahora = datetime.now().isoformat(timespec="seconds")
    con = connect()
    try:
        with con:
            if viejo_nombre and viejo_nombre != nombre:
                con.execute("UPDATE playbooks SET nombre=?, descripcion=?, reglas=?, actualizado=? "
                            "WHERE nombre=?", (nombre, descripcion, reglas, ahora, viejo_nombre))
                con.execute("UPDATE operaciones SET tipo=? WHERE tipo=?", (nombre, viejo_nombre))
            else:
                con.execute("INSERT INTO playbooks (nombre, descripcion, reglas, actualizado) "
                            "VALUES (?,?,?,?) ON CONFLICT(nombre) DO UPDATE SET "
                            "descripcion=excluded.descripcion, reglas=excluded.reglas, "
                            "actualizado=excluded.actualizado", (nombre, descripcion, reglas, ahora))
    finally:
        con.close()


def db_playbook_delete(nombre):
    """Borra el playbook (las operaciones conservan su tipo)."""
    con = connect()
    try:
        with con:
            con.execute("DELETE FROM playbooks WHERE nombre=?", (nombre,))
    finally:
        con.close()


def db_nota_get(fecha):
    con = connect()
    try:
        r = con.execute("SELECT * FROM notas WHERE fecha=?", (fecha,)).fetchone()
        return dict(r) if r else {"fecha": fecha, "plan": "", "que_paso": "", "corregir": ""}
    finally:
        con.close()


def db_nota_save(fecha, plan="", que_paso="", corregir=""):
    """Guarda la nota del día; si queda toda vacía, la borra."""
    con = connect()
    try:
        with con:
            if not (plan.strip() or que_paso.strip() or corregir.strip()):
                con.execute("DELETE FROM notas WHERE fecha=?", (fecha,))
                return
            con.execute(
                "INSERT INTO notas (fecha, plan, que_paso, corregir, actualizado) VALUES (?,?,?,?,?) "
                "ON CONFLICT(fecha) DO UPDATE SET plan=excluded.plan, que_paso=excluded.que_paso, "
                "corregir=excluded.corregir, actualizado=excluded.actualizado",
                (fecha, plan, que_paso, corregir, datetime.now().isoformat(timespec="seconds")))
    finally:
        con.close()


def db_notas_rango(desde, hasta):
    """{fecha: nota} de un rango (para ver qué días tienen nota)."""
    con = connect()
    try:
        return {r["fecha"]: dict(r) for r in con.execute(
            "SELECT * FROM notas WHERE fecha>=? AND fecha<=?", (desde, hasta))}
    finally:
        con.close()


def claves_importadas():
    """{(fuente, cuenta_ext, ext_id)} de lo que ya está en la base."""
    con = connect()
    try:
        return {(r[0], r[1], r[2]) for r in con.execute(
            "SELECT fuente, cuenta_ext, ext_id FROM operaciones WHERE ext_id IS NOT NULL")}
    finally:
        con.close()


_RE_CONSOL = re.compile(r"~\d+$")


def _min_del_dia(hhmm):
    try:
        h, m = str(hhmm).split(":")[:2]
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def marcar_posibles_duplicados(trades, ops=None, tol_min=5):
    """Marca en `t.posible` los trades que no coinciden por ID con nada de la base
    pero se parecen a una operación que ya está: mismo día, mismo activo y hora
    a menos de `tol_min` minutos. Cubre lo cargado a mano (no tiene ID de
    plataforma), la misma operación importada antes consolidada o suelta, y los
    trades cortados entre dos archivos. Es un aviso: no bloquea la importación.
    Cada operación manual/suelta se asigna a un solo trade (el más cercano);
    las consolidadas pueden coincidir con varios."""
    from .importadores.util import raiz
    candidatos = [t for t in trades if not t.duplicado]
    if not candidatos:
        return 0
    if ops is None:
        fechas = sorted({t.t_ini.strftime("%Y-%m-%d") for t in candidatos})
        ops = db_all({"desde": fechas[0], "hasta": fechas[-1]})
    por_dia = {}
    for o in ops:
        m = _min_del_dia(o.get("hora"))
        if m is None or not o.get("activo"):
            continue
        por_dia.setdefault(o["fecha"], []).append((o, m, raiz(o["activo"])))
    usados, n = set(), 0
    for t in sorted(candidatos, key=lambda x: x.t_ini):
        t.posible = ""
        mt = t.t_ini.hour * 60 + t.t_ini.minute
        mejor = None
        for o, m, ra in por_dia.get(t.t_ini.strftime("%Y-%m-%d"), []):
            if ra != raiz(t.activo) or abs(m - mt) > tol_min:
                continue
            if (o["fuente"], o["cuenta_ext"], o["ext_id"]) == t.clave:
                continue
            multi = bool(o.get("ext_id") and _RE_CONSOL.search(o["ext_id"])) or t.cuentas_n > 1
            if o["id"] in usados and not multi:
                continue
            if mejor is None or abs(m - mt) < mejor[0]:
                mejor = (abs(m - mt), o, multi)
        if mejor:
            _, o, multi = mejor
            if not multi:
                usados.add(o["id"])
            if not o.get("ext_id"):
                origen = "cargado a mano"
            elif _RE_CONSOL.search(o["ext_id"]) or t.cuentas_n > 1:
                origen = "importado con otra consolidación de cuentas"
            else:
                origen = "importado antes"
            t.posible = f"parecido a uno {origen} ({o['hora']}, {o['profit']:+,.2f})"
            n += 1
    return n


def db_importar(trades, empresa="", cuenta=None):
    """Guarda trades importados (TradeImp) en una sola transacción. Los que ya
    existen (mismo fuente+cuenta+id) se saltean. `cuenta` fuerza el nombre de
    cuenta del diario; si es None se usa la de la plataforma. Devuelve
    {'nuevos', 'duplicados', 'sin_pnl'}."""
    res = {"nuevos": 0, "duplicados": 0, "sin_pnl": 0}
    with _tx() as con:
        for t in trades:
            if t.neto is None:
                res["sin_pnl"] += 1
                continue
            data = dict(
                fecha=t.t_ini.strftime("%Y-%m-%d"), hora=t.t_ini.strftime("%H:%M"),
                activo=t.activo, tipo=None, profit=round(t.neto, 2),
                empresa=empresa or None, cuenta=cuenta or None,
                mov_sl=None, tranquilo=None, emo=None, comentario=None,
                img_ini=None, img_fin=None, fuente=t.fuente, ext_id=t.ext_id,
                cuenta_ext=t.cuenta, lado=t.lado, contratos=t.contratos,
                precio_ini=round(t.precio_ini, 5), precio_fin=round(t.precio_fin, 5),
                hora_fin=t.t_fin.strftime("%Y-%m-%d %H:%M"), comision=round(t.comision, 2),
                bruto=None if t.bruto is None else round(t.bruto, 2),
                motivo_cierre=t.motivo or None)
            cols, vals = _valores(data)
            cur = con.execute(
                f"INSERT OR IGNORE INTO operaciones ({','.join(cols)}) "
                f"VALUES ({','.join('?' * len(cols))})", vals)
            if cur.rowcount:
                res["nuevos"] += 1
                _cuenta_asegurar(con, data["empresa"], data["cuenta"])
            else:
                res["duplicados"] += 1
    return res


def db_update(op_id, data):
    cols, vals = _valores(data)
    with _tx() as con:
        con.execute(f"UPDATE operaciones SET {','.join(c + '=?' for c in cols)} WHERE id=?",
                    vals + [op_id])
        _cuenta_asegurar(con, data.get("empresa"), data.get("cuenta"))


def db_delete(op_id):
    with _tx() as con:
        row = con.execute("SELECT img_ini,img_fin FROM operaciones WHERE id=?", (op_id,)).fetchone()
        con.execute("DELETE FROM operaciones WHERE id=?", (op_id,))
    base = _rutas().data_dir
    for rel in (row["img_ini"], row["img_fin"]) if row else ():
        if rel:
            p = os.path.join(base, rel)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


# Cuenta elegida en el selector global de la barra lateral: (empresa, cuenta) o None = todas.
# db_all / db_range la aplican solos; los que necesitan todo (backup, arranque, ficha de la
# cuenta) piden `todo=True`.
_SEL = {"cuenta": None, "periodo": None}      # periodo = (desde, hasta) ISO (extremos opcionales)


def set_cuenta_global(cuenta):
    """cuenta = (empresa, cuenta) o None para ver todas."""
    _SEL["cuenta"] = None if not cuenta else (cuenta[0] or "", cuenta[1] or "")


def get_cuenta_global():
    return _SEL["cuenta"]


def set_periodo_global(periodo):
    """periodo = (desde, hasta) ISO o None (todo). Lo aplica db_all (no db_range, que ya recibe fechas)."""
    _SEL["periodo"] = None if not periodo else (periodo[0] or None, periodo[1] or None)


def get_periodo_global():
    return _SEL["periodo"]


def _sql_global(todo, fechas=False, cuenta=True):
    q, p = "", []
    sel = None if (todo or not cuenta) else _SEL["cuenta"]
    if sel:
        q += " AND COALESCE(empresa,'')=? AND COALESCE(cuenta,'')=?"; p += [sel[0], sel[1]]
    per = _SEL["periodo"] if (fechas and not todo) else None
    if per:
        if per[0]: q += " AND fecha>=?"; p.append(per[0])
        if per[1]: q += " AND fecha<=?"; p.append(per[1])
    return q, p


def db_all(filters=None, todo=False, fechas=True, cuenta=True):
    """`todo=True` ignora cuenta y período globales; `fechas=False` ignora solo el período
    (para pantallas que tienen su propio manejo de fechas: calendario, simulador, exportar);
    `cuenta=False` ignora solo la cuenta elegida (Portfolio: todas las cuentas, pero con el período)."""
    con = connect()
    q = "SELECT * FROM operaciones WHERE 1=1"
    params = []
    extra, p_extra = _sql_global(todo, fechas, cuenta)
    q += extra; params += p_extra
    if filters:
        if filters.get("desde"): q += " AND fecha>=?"; params.append(filters["desde"])
        if filters.get("hasta"): q += " AND fecha<=?"; params.append(filters["hasta"])
        if filters.get("tipo"):  q += " AND tipo=?";  params.append(filters["tipo"])
        if filters.get("cuenta"): q += " AND cuenta=?"; params.append(filters["cuenta"])
        if filters.get("emo"):   q += " AND emo=?";   params.append(int(filters["emo"]))
    rows = con.execute(q, params).fetchall()
    con.close()
    return [dict(r) for r in rows]


def db_range(desde, hasta, todo=False):
    con = connect()
    extra, p_extra = _sql_global(todo)
    rows = con.execute("SELECT * FROM operaciones WHERE fecha>=? AND fecha<=?" + extra,
                       [desde, hasta] + p_extra).fetchall()
    con.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Valores usados por campo — alimentan los desplegables para que crezcan solos
# ---------------------------------------------------------------------------
_DISTINCT_COLS = {"activo", "tipo", "empresa"}


def db_distinct(campo):
    if campo not in _DISTINCT_COLS:      # whitelist: evita inyección
        return []
    con = connect()
    rows = con.execute(
        f"SELECT DISTINCT {campo} FROM operaciones "
        f"WHERE {campo} IS NOT NULL AND TRIM({campo}) <> ''").fetchall()
    con.close()
    return [r[0].strip() for r in rows if r[0] and r[0].strip()]


def merged_values(base, campo):
    """Base + valores usados, sin duplicados (case-insensitive)."""
    seen = {b.lower() for b in base}
    usados = set(db_distinct(campo))
    if campo == "tipo":                      # los playbooks también son tipos de entrada
        usados |= {p["nombre"] for p in db_playbooks()}
    extra = sorted({v for v in usados if v.lower() not in seen}, key=str.lower)
    return list(base) + extra

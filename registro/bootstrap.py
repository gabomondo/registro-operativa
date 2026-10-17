"""Arranque: rutas -> log -> perfil -> migraciones -> backup diario.

Se separa de la UI para poder probarlo sin abrir ventanas."""

from dataclasses import dataclass
from typing import Any

from . import __version__, db, logs, paths, perfil as perfil_mod


@dataclass
class Contexto:
    rutas: Any
    perfil: Any
    log: Any
    perfil_nuevo: bool      # True si este arranque creó perfil.json
    migracion: dict         # {'desde','hasta','backup'}
    backup_diario: Any      # ruta del backup de hoy si se creó ahora

    @property
    def version(self):
        return __version__


def iniciar(argv=None, env=None):
    args = paths.parse_args(argv)
    rutas = paths.asegurar(paths.resolver_datos(args, env))
    log = logs.configurar_log(rutas.logs_dir)
    log.info("Inicio v%s · datos=%s (%s)", __version__, rutas.data_dir, rutas.origen)
    perfil, nuevo = perfil_mod.cargar_o_crear(
        rutas.perfil_path, rutas.db_path, preset=args.perfil, log=log)
    db.configurar(rutas, perfil)
    migracion = db.init_db()
    if migracion["desde"] != migracion["hasta"]:
        log.info("Migración %s -> %s (backup: %s)",
                 migracion["desde"], migracion["hasta"], migracion["backup"])
    diario = db.backup_diario(rutas.db_path, rutas.backups_dir)
    return Contexto(rutas, perfil, log, nuevo, migracion, diario)

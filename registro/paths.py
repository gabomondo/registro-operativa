"""Dónde vive cada cosa.

Orden para decidir la carpeta de DATOS (base, capturas, perfil, backups, logs):

  1. argumento  --datos "C:\\ruta"
  2. variable de entorno REGISTRO_DATOS
  3. modo portable: hay un registro.db (o portable.flag) al lado del programa.
     Es lo que usa una instalación "de carpeta", como la versión original.
  4. ubicacion.json en la carpeta de usuario (el botón "Cambiar carpeta de datos")
  5. por defecto: %APPDATA%\\gabomondo\\RegistroOperativa

El programa instalado vive en Program Files / AppData\\Local\\Programs, que no
siempre se puede escribir: los datos NUNCA se guardan junto al .exe salvo modo
portable.
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass

from . import APP_VENDOR

APP_DIRNAME = "RegistroOperativa"
POINTER_NAME = "ubicacion.json"


def app_dir():
    """Carpeta del programa: la del .exe si está empaquetado, si no la que
    contiene el paquete `registro/` (donde vive registro_operativa.py)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts):
    """Archivos que viajan con el programa (fuentes, perfiles). Dentro del
    paquete de PyInstaller viven bajo sys._MEIPASS."""
    base = getattr(sys, "_MEIPASS", None) or app_dir()
    return os.path.join(base, *parts)


def appdata_root():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, APP_VENDOR, APP_DIRNAME)


@dataclass
class Rutas:
    data_dir: str
    origen: str            # "argumento" | "entorno" | "portable" | "ubicacion" | "appdata"

    @property
    def db_path(self):       return os.path.join(self.data_dir, "registro.db")
    @property
    def caps_dir(self):      return os.path.join(self.data_dir, "capturas")
    @property
    def backups_dir(self):   return os.path.join(self.data_dir, "backups")
    @property
    def logs_dir(self):      return os.path.join(self.data_dir, "logs")
    @property
    def perfil_path(self):   return os.path.join(self.data_dir, "perfil.json")
    @property
    def ui_prefs_path(self): return os.path.join(self.data_dir, "ui_prefs.json")


def parse_args(argv=None):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--datos", default=None)
    p.add_argument("--perfil", default=None,
                   help="preset inicial si todavía no hay perfil.json (neutro, gabo, ...)")
    args, _ = p.parse_known_args(argv)
    return args


def _leer_puntero():
    try:
        with open(os.path.join(appdata_root(), POINTER_NAME), encoding="utf-8") as f:
            d = json.load(f).get("datos")
        if d and os.path.isdir(d):
            return d
    except Exception:
        pass
    return None


def resolver_datos(args=None, env=None):
    args = args or parse_args([])
    env = os.environ if env is None else env
    if args.datos:
        return Rutas(os.path.abspath(args.datos), "argumento")
    if env.get("REGISTRO_DATOS"):
        return Rutas(os.path.abspath(env["REGISTRO_DATOS"]), "entorno")
    ad = app_dir()
    if os.path.exists(os.path.join(ad, "registro.db")) or \
       os.path.exists(os.path.join(ad, "portable.flag")):
        return Rutas(ad, "portable")
    ptr = _leer_puntero()
    if ptr:
        return Rutas(ptr, "ubicacion")
    return Rutas(appdata_root(), "appdata")


def guardar_puntero(carpeta):
    """Recuerda una carpeta de datos elegida por el usuario (p. ej. dentro de
    Google Drive). Se aplica en el próximo arranque."""
    os.makedirs(appdata_root(), exist_ok=True)
    with open(os.path.join(appdata_root(), POINTER_NAME), "w", encoding="utf-8") as f:
        json.dump({"datos": os.path.abspath(carpeta)}, f, ensure_ascii=False, indent=2)


def borrar_puntero():
    try:
        os.remove(os.path.join(appdata_root(), POINTER_NAME))
    except OSError:
        pass


def asegurar(rutas):
    """Crea las carpetas y comprueba que se puede escribir. Si no, falla con un
    mensaje claro en vez de un error críptico de SQLite más adelante."""
    for d in (rutas.data_dir, rutas.caps_dir, rutas.backups_dir, rutas.logs_dir):
        os.makedirs(d, exist_ok=True)
    prueba = os.path.join(rutas.data_dir, ".escritura_ok")
    try:
        with open(prueba, "w") as f:
            f.write("ok")
        os.remove(prueba)
    except OSError as e:
        raise PermissionError(
            f"No puedo escribir en la carpeta de datos:\n{rutas.data_dir}\n\n{e}") from e
    return rutas

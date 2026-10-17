"""Aviso de versión nueva (sin interfaz): lee un archivo público `version.json` de la página de gabomondo.

Solo se pide esa URL; no se envía ningún dato del usuario. Falla en silencio ante cualquier problema de red
(también mientras el archivo todavía no esté publicado). La descarga se hace desde la página, no desde GitHub.

version.json:  {"version": "1.1.0", "notas": "Qué cambió, en pocas líneas"}"""
import json
import re
import time
import urllib.request

URL_VERSION = "https://gabomondo.com/registro/version.json"   # vacío = función apagada
PAGINA = "https://gabomondo.com/registro/"                      # donde se descarga la versión nueva
INTERVALO_S = 24 * 3600   # como máximo una consulta por día
TIMEOUT_S = 4


def parse_version(txt):
    """'v1.2.3' / '1.2' -> (1, 2, 3) / (1, 2, 0); None si no es una versión."""
    m = re.match(r"^\s*v?(\d+)\.(\d+)(?:\.(\d+))?", str(txt or ""))
    return None if not m else (int(m[1]), int(m[2]), int(m[3] or 0))


def hay_nueva(actual, tag):
    a, n = parse_version(actual), parse_version(tag)
    return bool(a and n and n > a)


def info_version(data):
    """Datos útiles del version.json; None si no sirve."""
    if not isinstance(data, dict):
        return None
    v = parse_version(data.get("version"))
    if not v:
        return None
    return dict(version=".".join(map(str, v)), url=PAGINA, notas=str(data.get("notas") or "").strip())


def toca_consultar(ultimo, ahora=None, intervalo=INTERVALO_S):
    """True si pasó el intervalo desde la última consulta (timestamp) o nunca se hizo."""
    ahora = time.time() if ahora is None else ahora
    try:
        return ahora - float(ultimo) >= intervalo
    except (TypeError, ValueError):
        return True


def consultar(url=None, actual=None, abrir=None):
    """Info de la versión publicada si es posterior a `actual`; None si no hay, no aplica o falla algo."""
    url = URL_VERSION if url is None else url
    if not url:
        return None
    try:
        if actual is None:
            from . import __version__ as actual
        abrir = abrir or (lambda u: urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": "registro-operativa"}), timeout=TIMEOUT_S))
        with abrir(url) as r:
            info = info_version(json.loads(r.read().decode("utf-8")))
        return info if info and hay_nueva(actual, info["version"]) else None
    except Exception:
        return None

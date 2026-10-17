"""Estado de arranque de la UI: contexto, carpetas y preferencias de pantalla.

`_arrancar` completa CTX/BASE_DIR/CAPS_DIR/UI_PREFS y los publica en `vivo`."""

import json
from registro.bootstrap import iniciar
from registro.ui import vivo


# ----------------------------------------------------------------------------
# Arranque — rutas, perfil y base de datos (registro/bootstrap.py). Se completa
# en _arrancar(); el resto del archivo lee estos globales al usarlos.
# ----------------------------------------------------------------------------
DPI_SISTEMA = 1.0
DPI_INFO = "sin ajuste (no es Windows)"

CTX = None          # Contexto: rutas, perfil, log, migración


BASE_DIR = CAPS_DIR = UI_PREFS = None


def _arrancar(argv=None):
    global CTX, BASE_DIR, CAPS_DIR, UI_PREFS
    CTX = iniciar(argv)
    BASE_DIR = CTX.rutas.data_dir
    CAPS_DIR = CTX.rutas.caps_dir
    UI_PREFS = CTX.rutas.ui_prefs_path
    vivo.publicar(CTX=CTX, BASE_DIR=BASE_DIR, CAPS_DIR=CAPS_DIR, UI_PREFS=UI_PREFS)
    CTX.log.info("Pantalla: %s", DPI_INFO)
    return CTX


def load_ui_prefs():
    try:
        with open(UI_PREFS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_ui_prefs(prefs):
    try:
        with open(UI_PREFS, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    except Exception:
        pass


vivo.registrar(globals())

"""Log a archivo (logs/registro.log, rotativo) para poder diagnosticar errores
de usuarios sin pedirles que abran una consola."""

import logging
import logging.handlers
import os
import sys
import traceback


def configurar_log(logs_dir, nivel=logging.INFO):
    os.makedirs(logs_dir, exist_ok=True)
    log = logging.getLogger("registro")
    log.setLevel(nivel)
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in log.handlers):
        h = logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, "registro.log"),
            maxBytes=512_000, backupCount=3, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(h)
    return log


def instalar_hook(log, avisar=None):
    """Errores no capturados -> log (+ aviso opcional al usuario)."""
    def hook(tipo, valor, tb):
        texto = "".join(traceback.format_exception(tipo, valor, tb))
        log.error("Excepción no capturada:\n%s", texto)
        if avisar:
            try:
                avisar(valor, texto)
            except Exception:
                pass
    sys.excepthook = hook
    return hook

"""Fuentes de marca (DM Sans, JetBrains Mono, Instrument Serif; licencia OFL).

Viajan con el programa en assets/fonts. En Windows se registran solo para este
proceso (no se instalan en el sistema). Si algo falla, cae a fuentes seguras.
"""

import glob
import os
import sys

from .paths import resource_path

FR_PRIVATE = 0x10


def registrar_fuentes(carpeta=None):
    """Registra los .ttf de la carpeta para este proceso. Devuelve cuántos."""
    carpeta = carpeta or resource_path("assets", "fonts")
    if sys.platform != "win32":
        return 0
    n = 0
    try:
        import ctypes
        add = ctypes.windll.gdi32.AddFontResourceExW
        for ttf in glob.glob(os.path.join(carpeta, "*.ttf")):
            if add(ttf, FR_PRIVATE, 0):
                n += 1
    except Exception:
        pass
    return n


def resolver_fuentes():
    """(principal, mono, serif): la de marca si está disponible, si no una
    alternativa segura para no perder la jerarquía visual."""
    preferidas = (
        ("DM Sans", ["Segoe UI", "Helvetica Neue", "Arial", "Roboto"]),
        ("JetBrains Mono", ["Cascadia Code", "Consolas", "Menlo", "Courier New"]),
        ("Instrument Serif", ["Georgia", "Times New Roman", "serif"]),
    )
    try:
        import tkinter as tk
        from tkinter import font as tkfont
        root = tk.Tk()
        root.withdraw()
        disponibles = {f.lower() for f in tkfont.families()}
        root.destroy()
    except Exception:
        return tuple(p for p, _ in preferidas)

    def elegir(pref, alternativas):
        if pref.lower() in disponibles:
            return pref
        for a in alternativas:
            if a.lower() in disponibles:
                return a
        return pref

    return tuple(elegir(p, a) for p, a in preferidas)

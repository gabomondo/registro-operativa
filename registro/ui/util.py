"""Utilidades chicas de la UI (texto, formatos, abrir carpeta)."""

import os
import re
import subprocess
import sys
from tkinter import messagebox


def _lista_de_texto(texto):
    return [l.strip() for l in texto.splitlines() if l.strip()]


def _parse_pares(texto):
    """'MNQ=2' por línea -> ({'MNQ': 2.0}, [líneas inválidas])."""
    out, malas = {}, []
    for linea in texto.splitlines():
        l = linea.strip()
        if not l:
            continue
        m = re.match(r"^([^=:\t]+)[=:\t]\s*(.+)$", l)
        try:
            out[m.group(1).strip().upper()] = float(m.group(2).replace(",", "."))
        except (AttributeError, ValueError):
            malas.append(linea)
    return out, malas


def _pares_a_texto(d):
    return "\n".join(f"{k}={v:g}" for k, v in d.items())


def _abrir_carpeta(path):
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        messagebox.showinfo("Carpeta", path)


# ----------------------------------------------------------------------------
# Utilidades de capturas
# ----------------------------------------------------------------------------
def slugify(s):
    keep = "".join(c if c.isalnum() else "" for c in (s or ""))
    return keep or "NA"


def _fmt_precio(x):
    return f"{x:,.2f}" if abs(x) >= 100 else f"{x:.5f}".rstrip("0").rstrip(".")


def _fmt_usd(x, signo=False):
    if x is None:
        return "—"
    return f"{x:+,.2f}" if signo else f"{x:,.2f}"

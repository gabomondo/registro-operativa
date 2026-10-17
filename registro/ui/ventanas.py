"""Posición y tamaño de las ventanas emergentes (diálogos).

Todas se abren centradas sobre la ventana principal, siempre dentro del área útil del
monitor (sin pisar la barra de tareas) y, salvo que se diga lo contrario, redimensionables
arrastrando los bordes. El tamaño se pasa en unidades de CustomTkinter (se multiplican por
DPI_SISTEMA); la posición va en píxeles reales.
"""

import sys

from registro.ui import vivo
from registro.ui.estado import DPI_SISTEMA

MARGEN = 16   # px reales que se dejan libres contra el borde del área útil


def calcular_geometria(ancho, alto, esc, area, padre=None, margen=MARGEN):
    """Cálculo puro (sin tkinter).

    ancho/alto: tamaño deseado en unidades CTk. esc: escala de pantalla (DPI_SISTEMA).
    area: (x, y, ancho, alto) del área útil en píxeles reales.
    padre: (x, y, ancho, alto) de la ventana sobre la que se centra, o None para centrar en el área.
    Devuelve (w, h, x, y): tamaño en unidades CTk (recortado para que entre) y posición en px reales."""
    ax, ay, aw, ah = area
    w = max(1, min(int(ancho), int((aw - 2 * margen) / esc)))
    h = max(1, min(int(alto), int((ah - 2 * margen) / esc)))
    rw, rh = round(w * esc), round(h * esc)
    if padre:
        px, py, pw, ph = padre
        x, y = px + (pw - rw) // 2, py + (ph - rh) // 2
    else:
        x, y = ax + (aw - rw) // 2, ay + (ah - rh) // 2
    x = max(ax, min(x, ax + aw - rw))
    y = max(ay, min(y, ay + ah - rh))
    return w, h, x, y


def _area_util(ventana):
    """(x, y, ancho, alto) del área de trabajo del monitor donde está `ventana` (sin barra de tareas).
    Fuera de Windows, o si falla, usa la pantalla completa."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                            ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

            user32 = ctypes.windll.user32
            hwnd = user32.GetAncestor(wintypes.HWND(ventana.winfo_id()), 2)   # GA_ROOT
            hmon = user32.MonitorFromWindow(wintypes.HWND(hwnd), 2)           # MONITOR_DEFAULTTONEAREST
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
                r = info.rcWork
                if r.right > r.left and r.bottom > r.top:
                    return r.left, r.top, r.right - r.left, r.bottom - r.top
        except Exception:
            pass
    return 0, 0, ventana.winfo_screenwidth(), ventana.winfo_screenheight()


def _rect_padre(app):
    """(x, y, ancho, alto) de la ventana principal, o None si está minimizada o sin medir."""
    try:
        app.update_idletasks()
        if str(app.state()) == "iconic":
            return None
        r = (app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height())
        return r if r[2] > 50 and r[3] > 50 else None
    except Exception:
        return None


def centrar_dialogo(win, app, ancho, alto, min_ancho=None, min_alto=None, redimensionable=True):
    """Da tamaño y posición a un diálogo: centrado sobre `app`, dentro del área útil del monitor.

    `ancho`/`alto` en unidades CTk. Si no entra en pantalla, se achica. `min_*` fijan el tamaño
    mínimo al redimensionar (también recortado para que entre)."""
    win.update_idletasks()
    w, h, x, y = calcular_geometria(ancho, alto, DPI_SISTEMA, _area_util(app), _rect_padre(app))
    win.geometry(f"{w}x{h}+{x}+{y}")
    if redimensionable:
        win.minsize(min(int(min_ancho or ancho * 0.8), w), min(int(min_alto or alto * 0.7), h))
    win.resizable(bool(redimensionable), bool(redimensionable))


def centrar_existente(win, app):
    """Centra una ventana que ya tiene contenido (su tamaño lo da el contenido), sin cambiarlo."""
    win.update_idletasks()
    ax, ay, aw, ah = _area_util(app)
    rw, rh = win.winfo_reqwidth(), win.winfo_reqheight()
    padre = _rect_padre(app)
    if padre:
        x, y = padre[0] + (padre[2] - rw) // 2, padre[1] + (padre[3] - rh) // 2
    else:
        x, y = ax + (aw - rw) // 2, ay + (ah - rh) // 2
    x = max(ax, min(x, ax + aw - rw))
    y = max(ay, min(y, ay + ah - rh))
    win.geometry(f"+{x}+{y}")


vivo.registrar(globals())

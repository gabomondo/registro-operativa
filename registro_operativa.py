"""
Registro de operativa — gabomondo
=================================
App de escritorio para registrar operaciones de trading con enfoque psicológico.

Stack: Python + CustomTkinter + SQLite. Capturas en carpeta aparte (copiadas, no referenciadas).

Uso (desde el código fuente):
    pip install -r requirements.txt
    python registro_operativa.py [--datos "C:\\ruta"] [--perfil neutro|gabo]

Dónde guarda los datos: ver registro/paths.py (por defecto %APPDATA%\\gabomondo\\RegistroOperativa;
si hay un registro.db junto al programa, trabaja ahí en modo portable).
"""

import sys
from datetime import date

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from registro import db as _db
from registro.db import db_all, merged_values, db_playbooks, db_nota_get

from registro.ui import vivo
from registro.ui.estado import _arrancar
from registro.ui.tema import _resolve_fonts

from registro.ui.app import AppBase
from registro.ui.pantallas.cuentas import CuentasMixin
from registro.ui.pantallas.portfolio import PortfolioMixin
from registro.ui.selector import SelectorMixin
from registro.ui.periodo import PeriodoMixin
from registro.ui.modo import ModoMixin
from registro.ui.actualizacion import ActualizacionMixin
from registro.ui.pantallas.datos_io import DatosIOMixin
from registro.ui.pantallas.perfil import PerfilMixin
from registro.ui.pantallas.registro import RegistroMixin
from registro.ui.pantallas.comunes import ComunesMixin
from registro.ui.pantallas.cargar import CargarMixin
from registro.ui.pantallas.plan import PlanMixin
from registro.ui.pantallas.revision import RevisionMixin
from registro.ui.pantallas.analisis import AnalisisMixin
from registro.ui.pantallas.plantillas import PlantillasMixin
from registro.ui.pantallas.simulador import SimuladorMixin
from registro.ui.pantallas.playbooks import PlaybooksMixin
from registro.ui.pantallas.notebook import NotebookMixin
from registro.ui.pantallas.calendario import CalendarioMixin
from registro.ui.dialogos.importar import ImportarDialog
from registro.ui.dialogos.exportar import ExportarDialog
from registro.ui.dialogos.acerca import AcercaDialog
from registro.ui.dialogos.riesgo import RiesgoDialog

# Re-exportados: los usan tests/smoke_*.py y las herramientas externas (ro.ImportarDialog, ro.main...)
__all__ = ["App", "main", "ImportarDialog", "ExportarDialog", "AcercaDialog", "RiesgoDialog",
           "db_all", "db_nota_get", "db_playbooks", "merged_values", "date"]   # los usan tests/smoke_*.py

vivo.registrar(globals())


class App(AppBase, CalendarioMixin, NotebookMixin,
          PlaybooksMixin, SimuladorMixin, PlantillasMixin,
          AnalisisMixin, RevisionMixin, PlanMixin,
          CargarMixin, ComunesMixin, RegistroMixin,
          PerfilMixin, DatosIOMixin, CuentasMixin, SelectorMixin, PeriodoMixin, ModoMixin, PortfolioMixin, ActualizacionMixin):
    """La aplicación: el shell vive en ui/app.py y cada pantalla es un Mixin en ui/pantallas/."""
# Niveles de tamaño de la interfaz (igual que en el Tracker). Mediano = 1.15.
# Escala de pantalla de Windows (1.0 = 100%). Se fija UNA vez al arrancar
# (DPI_SISTEMA / DPI_INFO viven en registro/ui/estado.py y se publican con vivo).


def _enable_dpi_awareness():
    """Escalado en Windows SIN reescalar al cambiar de monitor.

    CustomTkinter, por defecto, mira cada 100 ms en qué monitor está la ventana y,
    si cambia la densidad, reescala TODOS los widgets (y baja la opacidad de la
    ventana): con la ventana a medio camino entre dos monitores eso se dispara todo
    el tiempo y se cuelga. Acá la app es 'System DPI aware', toma la escala de
    pantalla una sola vez al iniciar y se apaga ese vigilante. Al cruzar a otro
    monitor, Windows estira la ventana y nada se reacomoda. Debe correr ANTES de
    crear cualquier ventana. No-op fuera de Windows."""
    if sys.platform != "win32":
        return
    try:
        ctk.deactivate_automatic_dpi_awareness()
    except Exception:
        pass
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)      # System DPI aware
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
        except Exception:
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)     # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)
        dpi_sis = max(1.0, dpi / 96.0)
        vivo.publicar(DPI_SISTEMA=dpi_sis)
        ctk.set_window_scaling(dpi_sis)
        try:   # para el log: 0 = sin DPI, 1 = sistema, 2 = por monitor
            ctx = ctypes.windll.user32.GetThreadDpiAwarenessContext()
            modo = ctypes.windll.user32.GetAwarenessFromDpiAwarenessContext(ctx)
        except Exception:
            modo = "?"
        vivo.publicar(DPI_INFO=f"escala del sistema {dpi_sis:.2f} (dpi {dpi}), modo de conciencia DPI = {modo}")
    except Exception as e:
        vivo.publicar(DPI_INFO=f"error fijando la escala: {e}")


def _fatal(titulo, texto):
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(titulo, texto)
        root.destroy()
    except Exception:
        print(texto, file=sys.stderr)


def main(argv=None):
    _enable_dpi_awareness()
    _resolve_fonts()
    try:
        _arrancar(argv)
    except _db.BaseMasNuevaError as e:
        _fatal("Base de datos más nueva", str(e)); return 1
    except _db.MigracionError as e:
        _fatal("No pude actualizar la base", str(e)); return 1
    except PermissionError as e:
        _fatal("Carpeta de datos", str(e)); return 1
    except Exception as e:
        import logging
        logging.getLogger("registro").exception("Error al iniciar")
        _fatal("Error al iniciar", f"{e}\n\nDetalle en la carpeta logs de tus datos.")
        return 1
    App().mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Diálogo «Acerca de»: versión, marca y enlaces."""

import customtkinter as ctk
import tkinter as tk
from PIL import Image
from registro.paths import resource_path
from registro import __version__, APP_NAME, APP_VENDOR
from registro.ui import vivo
from registro.ui.tema import BLUE_HI, FONT_MAIN, FONT_MONO, FONT_SERIF, INK, MUTED, MUTED2, PAPER, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS
from registro.ui.ventanas import centrar_dialogo
from registro.ui.widgets import btn_ghost, btn_primary

vivo.registrar(globals())


class AcercaDialog(ctk.CTkToplevel):
    """Acerca de: versión, marca y enlaces. La búsqueda de versión nueva la hace la app, no este diálogo."""
    LINKS = [("gabomondo.com", "https://gabomondo.com"),
             ("YouTube", "https://youtube.com/@Gabomondo"),
             ("Instagram", "https://instagram.com/gabomondo")]

    def __init__(self, app):
        super().__init__(app)
        self.title("Acerca de")
        f = app.factor
        centrar_dialogo(self, app, int(460 * f), int(520 * f), redimensionable=False)
        self.configure(fg_color=INK)
        self.transient(app)
        self.bind("<Escape>", lambda e: self.destroy())
        try:      # el mismo ícono de la ventana y del instalador
            img = Image.open(resource_path("assets", "icono.ico")).convert("RGBA")
            self._logo = ctk.CTkImage(light_image=img, dark_image=img, size=(72, 72))
            ctk.CTkLabel(self, text="", image=self._logo).pack(pady=(SP_XL, SP_SM))
        except Exception:      # respaldo: marca dibujada (línea + línea + círculo)
            cv = tk.Canvas(self, width=64, height=64, bg=INK, highlightthickness=0)
            cv.pack(pady=(SP_XL, SP_SM))
            cv.create_line(6, 40, 58, 40, fill=PAPER, width=3)
            cv.create_line(22, 8, 22, 56, fill=BLUE_HI, width=3)
            cv.create_oval(34, 22, 50, 38, outline=BLUE_HI, width=3)
        ctk.CTkLabel(self, text=APP_NAME, font=(FONT_SERIF, 30), text_color=PAPER).pack()
        ctk.CTkLabel(self, text=f"Versión {__version__} · por {APP_VENDOR}",
                     font=(FONT_MONO, 12), text_color=MUTED).pack(pady=(SP_XS, SP_MD))
        ctk.CTkLabel(
            self, text="Diario de operativa gratuito para traders de futuros y forex. "
                       "Tus datos viven en tu computadora: la app no envía información a nadie "
                       "ni usa telemetría. Lo único que consulta es si hay una versión nueva "
                       "(se apaga en Perfil).",
            font=(FONT_MAIN, 13), text_color=PAPER, wraplength=int(380 * f), justify="center").pack(
                padx=SP_XL, pady=(0, SP_MD))
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(pady=SP_SM)
        for txt, url in self.LINKS:
            btn_ghost(fila, txt, lambda u=url: self._abrir(u), width=120, height=32).pack(
                side="left", padx=SP_XS)
        ctk.CTkLabel(
            self, text="Tipografías: Instrument Serif, DM Sans y JetBrains Mono (licencia SIL OFL).\n"
                       "Esto es un registro personal, no un consejo de inversión.",
            font=(FONT_MAIN, 11), text_color=MUTED2, justify="center").pack(pady=(SP_LG, 0))
        btn_primary(self, "Cerrar", self.destroy, width=120, height=34).pack(pady=SP_XL)
        self.after(80, self._foco)

    def _foco(self):
        try:
            self.grab_set()
            self.focus_set()
        except Exception:
            pass

    def _abrir(self, url):
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception:
            pass

"""Barra lateral de navegación (Nav) y lista de secciones de la app."""
import customtkinter as ctk

from registro.ui import vivo
from registro.ui.tema import (
    BLUE_HI, FONT_MAIN, HOVER, MUTED, MUTED2, NAV_SEL, PAPER,
    RAD_CTRL, SP_MD, SP_XL, SP_XS)

SECCIONES = [  # (grupo, nombre, subtítulo)
    ("DIARIO", "Registro", "Tu evolución y todas las operaciones"),
    ("DIARIO", "Portfolio", "Todas tus cuentas juntas"),
    ("DIARIO", "Calendario", "Tu P&L día por día"),
    ("DIARIO", "Análisis", "Dónde ganás y dónde perdés plata"),
    ("DIARIO", "Cargar operación", "Registrá una operación a mano"),
    ("REVISIÓN", "Revisión semanal", "Cómo viene la semana, con la cabeza"),
    ("REVISIÓN", "Notebook", "Qué planeaste, qué pasó y qué corregir"),
    ("REVISIÓN", "Simulador", "¿Y si hubieras seguido una regla?"),
    ("REVISIÓN", "Plan", "Reglas y plan de trading"),
    ("AJUSTES", "Cuentas", "Tus cuentas: estado, tipo y capital"),
    ("AJUSTES", "Playbooks", "Tus setups, con sus reglas y cómo rinden"),
    ("AJUSTES", "Plantillas", "Checklists reutilizables"),
    ("AJUSTES", "Perfil", "Activos, empresas y preferencias"),
]


class Nav:
    """Barra lateral de navegación. Mantiene la interfaz del CTkTabview
    (add / set / get / configure(command=)) para no tocar el resto de la app."""

    def __init__(self, app, sidebar):
        self.app = app
        self.sidebar = sidebar
        self.pages = {}
        self.buttons = {}
        self._cur = None
        self._cmd = None
        self._grupo = None

    def _cabecera(self, grupo):
        if grupo != self._grupo:
            self._grupo = grupo
            ctk.CTkLabel(self.sidebar, text=grupo, font=(FONT_MAIN, 9), text_color=MUTED2,
                         anchor="w").pack(fill="x", padx=SP_XL, pady=(SP_MD, SP_XS))

    def _boton(self, nombre, comando):
        wrap = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=34)
        wrap.pack(fill="x", padx=SP_MD, pady=1)
        wrap.pack_propagate(False)
        bar = ctk.CTkFrame(wrap, fg_color="transparent", width=3, corner_radius=2)
        bar.pack(side="left", fill="y", pady=6)
        b = ctk.CTkButton(wrap, text=nombre, anchor="w", height=32, corner_radius=RAD_CTRL,
                          fg_color="transparent", hover_color=HOVER, text_color=MUTED,
                          font=(FONT_MAIN, 13), command=comando)
        b.pack(side="left", fill="both", expand=True, padx=(SP_XS, 0))
        return b, bar

    def add_accion(self, grupo, nombre, comando):
        """Entrada de la barra que no es una página: abre una herramienta (un diálogo)."""
        self._cabecera(grupo)
        self._boton(nombre, comando)

    def add(self, nombre):
        self._cabecera(next((g for g, n, _ in SECCIONES if n == nombre), ""))
        self.buttons[nombre] = self._boton(nombre, lambda n=nombre: self._click(n))
        page = ctk.CTkFrame(self.app.page_host, fg_color="transparent", corner_radius=0)
        self.pages[nombre] = page
        return page

    def _click(self, nombre):
        self.set(nombre)
        if self._cmd:
            self._cmd()

    def configure(self, command=None, **_):
        if command is not None:
            self._cmd = command

    def get(self):
        return self._cur

    def set(self, nombre):
        if nombre not in self.pages or nombre == self._cur:
            return
        if self._cur:
            self.pages[self._cur].pack_forget()
            b, bar = self.buttons[self._cur]
            b.configure(fg_color="transparent", text_color=MUTED)
            bar.configure(fg_color="transparent")
        self._cur = nombre
        self.pages[nombre].pack(fill="both", expand=True)
        b, bar = self.buttons[nombre]
        b.configure(fg_color=NAV_SEL, text_color=PAPER, hover_color=NAV_SEL)
        bar.configure(fg_color=BLUE_HI)
        sub = next((x for _g, n, x in SECCIONES if n == nombre), "")
        self.app.lbl_titulo.configure(text=nombre)
        self.app.lbl_sub.configure(text=sub)


vivo.registrar(globals())

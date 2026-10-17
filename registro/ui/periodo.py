"""Rango de fechas global (encabezado): atajos tipo «Este mes» o un rango propio. Lo usan Registro,
Análisis y Playbooks; el resto tiene su propia navegación por fechas."""
import tkinter as tk
import customtkinter as ctk

from registro import periodos as PR
from registro.db import set_periodo_global
from registro.ui import vivo
from registro.ui.estado import save_ui_prefs
from registro.ui.tema import (
    BLUE, FONT_MAIN, INK, MUTED, MUTED2, NEG_TXT, ON_BLUE, PAPER, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SURFACE)
from registro.ui.ventanas import centrar_dialogo
from registro.ui.widgets import DatePicker, btn_ghost, btn_primary

vivo.registrar(globals())

TABS_CON_PERIODO = ("Registro", "Portfolio", "Análisis", "Playbooks")


class PeriodoDialog(ctk.CTkToplevel):
    """Rango propio: dos fechas (cualquiera puede quedar vacía = abierto)."""

    def __init__(self, app, desde, hasta, al_aplicar):
        super().__init__(app)
        self.title("Rango de fechas")
        self._al_aplicar = al_aplicar
        f = app.factor
        centrar_dialogo(self, app, int(420 * f), int(300 * f), redimensionable=False)
        self.configure(fg_color=INK)
        self.transient(app)
        self.bind("<Escape>", lambda e: self.destroy())
        ctk.CTkLabel(self, text="Rango de fechas", font=(FONT_MAIN, 16), text_color=PAPER).pack(
            anchor="w", padx=SP_XL, pady=(SP_XL, SP_XS))
        ctk.CTkLabel(self, text="Dejá una vacía para no limitar ese extremo.", font=(FONT_MAIN, 11),
                     text_color=MUTED).pack(anchor="w", padx=SP_XL)
        fila = ctk.CTkFrame(self, fg_color="transparent"); fila.pack(fill="x", padx=SP_XL, pady=SP_LG)
        for attr, txt, v in (("e_desde", "DESDE", desde), ("e_hasta", "HASTA", hasta)):
            col = ctk.CTkFrame(fila, fg_color="transparent"); col.pack(side="left", padx=(0, SP_LG))
            ctk.CTkLabel(col, text=txt, font=(FONT_MAIN, 9), text_color=MUTED2).pack(anchor="w", pady=(0, SP_XS))
            w = DatePicker(col, width=112); w.pack()
            if v:
                w.insert(0, v)
            setattr(self, attr, w)
        self.msg = ctk.CTkLabel(self, text="", font=(FONT_MAIN, 11), text_color=NEG_TXT)
        self.msg.pack(anchor="w", padx=SP_XL)
        bar = ctk.CTkFrame(self, fg_color="transparent"); bar.pack(fill="x", padx=SP_XL, pady=SP_MD)
        btn_primary(bar, "Aplicar", self._aplicar, width=110).pack(side="left")
        btn_ghost(bar, "Cancelar", self.destroy, width=110).pack(side="left", padx=SP_SM)

    def _aplicar(self):
        try:
            fechas = PR.validar_rango(self.e_desde.get(), self.e_hasta.get())
        except ValueError as e:
            self.msg.configure(text=str(e)); return
        self.destroy()
        self._al_aplicar(fechas)


class PeriodoMixin:
    def _restaurar_periodo(self):
        self._periodo_preset, self._periodo_fechas = PR.desde_prefs(self._ui_prefs.get("periodo"))
        set_periodo_global(self._periodo_fechas)

    def _build_periodo(self, parent):
        self.ctrl_global = ctk.CTkFrame(parent, fg_color="transparent")      # período + Dinero/Porcentaje
        self.btn_periodo = btn_ghost(self.ctrl_global, self._texto_periodo(), self._menu_periodo, width=190, height=34)
        self.btn_periodo.pack(side="left")
        self._periodo_visible = False

    def _texto_periodo(self):
        return "\U0001F4C5  " + PR.etiqueta(self._periodo_preset, self._periodo_fechas) + "  ▾"

    def _mostrar_periodo(self, nombre_tab):
        """El botón se ve solo en las pantallas que usan el rango global."""
        quiere = nombre_tab in TABS_CON_PERIODO
        if quiere and not self._periodo_visible:
            self.ctrl_global.pack(side="right", padx=(0, SP_SM))
        elif not quiere and self._periodo_visible:
            self.ctrl_global.pack_forget()
        self._periodo_visible = quiere

    def _menu_periodo(self):
        m = tk.Menu(self, tearoff=0, bg=SURFACE, fg=PAPER, activebackground=BLUE,
                    activeforeground=ON_BLUE, bd=0, relief="flat",
                    font=(FONT_MAIN, max(8, round(10 * self.factor))))
        for nombre in PR.PRESETS:
            marca = "✓ " if nombre == self._periodo_preset else "    "
            m.add_command(label=f"{marca}{nombre}", command=lambda n=nombre: self._elegir_periodo(n))
        m.add_separator()
        marca = "✓ " if self._periodo_preset is None else "    "
        m.add_command(label=f"{marca}Rango propio…", command=self._dialogo_periodo)
        b = self.btn_periodo
        try:
            m.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height() + 2)
        finally:
            m.grab_release()

    def _dialogo_periodo(self):
        d, h = self._periodo_fechas or (None, None)
        PeriodoDialog(self, d, h, lambda fechas: self._elegir_periodo(None, fechas))

    def _elegir_periodo(self, preset, fechas=None):
        """preset = nombre de PR.PRESETS, o None con `fechas` = (desde, hasta) propias."""
        if preset is not None:
            fechas = PR.rango(preset)
        elif not fechas:
            preset = PR.TODO
        self._periodo_preset, self._periodo_fechas = preset, fechas
        set_periodo_global(fechas)
        if preset is not None:
            self._ui_prefs["periodo"] = {"preset": preset}
        else:
            self._ui_prefs["periodo"] = {"desde": fechas[0], "hasta": fechas[1]}
        save_ui_prefs(self._ui_prefs)
        self.btn_periodo.configure(text=self._texto_periodo())
        self._table_dirty = True
        self._on_tab_change()

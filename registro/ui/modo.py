"""Toggle Dinero/Porcentaje (encabezado) y formato de importes (`self._m`). Lo usan Registro, Análisis y Portfolio."""
import customtkinter as ctk

from registro import unidades as U
from registro.db import db_cuentas, get_cuenta_global
from registro.ui import vivo
from registro.ui.estado import save_ui_prefs
from registro.ui.tema import (
    FONT_MAIN, HOVER, MUTED2, PAPER, SEG_HI, SEG_SEL, SP_SM, SURFACE)

vivo.registrar(globals())

TABS_CON_MODO = ("Registro", "Portfolio", "Análisis", "Calendario", "Revisión semanal")
_SIN_CALCULAR = object()


class ModoMixin:
    def _restaurar_modo(self):
        m = self._ui_prefs.get("modo_pnl")
        self._modo_pnl = m if m in (U.DINERO, U.PCT) else U.DINERO
        self._base_cache = _SIN_CALCULAR

    def _build_modo(self, parent):
        self.seg_modo = ctk.CTkSegmentedButton(
            parent, values=["Dinero", "Porcentaje"], height=34, font=(FONT_MAIN, 12),
            fg_color=SURFACE, selected_color=SEG_SEL, selected_hover_color=SEG_HI,
            unselected_color=SURFACE, unselected_hover_color=HOVER, text_color=PAPER,
            command=self._on_modo)
        self.seg_modo.set("Porcentaje" if self._modo_pnl == U.PCT else "Dinero")
        self.lbl_modo_aviso = ctk.CTkLabel(parent, text="", font=(FONT_MAIN, 10), text_color=MUTED2)
        self._modo_visible = False

    def _mostrar_modo(self, nombre_tab):
        """El toggle se ve solo donde hay importes agregados (no en Playbooks, que comparte el rango)."""
        quiere = nombre_tab in TABS_CON_MODO
        if quiere and not self._modo_visible:
            self.seg_modo.pack(side="left", padx=(SP_SM, 0))
            self.lbl_modo_aviso.pack(side="left", padx=(SP_SM, 0))
        elif not quiere and self._modo_visible:
            self.seg_modo.pack_forget()
            self.lbl_modo_aviso.pack_forget()
        self._modo_visible = quiere
        self._actualizar_aviso_modo()

    def _on_modo(self, valor):
        self._modo_pnl = U.PCT if valor == "Porcentaje" else U.DINERO
        self._ui_prefs["modo_pnl"] = self._modo_pnl
        save_ui_prefs(self._ui_prefs)
        self._table_dirty = True
        self._on_tab_change()

    def _reiniciar_base_pct(self):
        self._base_cache = _SIN_CALCULAR

    def _base_pct(self):
        """Capital inicial que sirve de base al porcentaje (cuenta elegida, o todas); None si falta."""
        if self._base_cache is _SIN_CALCULAR:
            try:
                self._base_cache = U.base_capital(db_cuentas(), get_cuenta_global())
            except Exception:
                self._base_cache = None
        return self._base_cache

    def _en_pct(self, base=...):
        return U.activo(self._modo_pnl, self._base_pct() if base is ... else base)

    def _m(self, v, d=0, signo=True, base=...):
        """Importe en dinero o en % según el toggle. `base` = capital propio (p. ej. el de una cuenta del Portfolio)."""
        return U.fmt(v, self._modo_pnl, self._base_pct() if base is ... else base, d, signo)

    def _unidad(self, base=...):
        """« USD» en dinero, vacío en porcentaje."""
        return "" if self._en_pct(base) else " USD"

    def _actualizar_aviso_modo(self):
        if not getattr(self, "lbl_modo_aviso", None):
            return
        falta = self._modo_pnl == U.PCT and not self._base_pct() and self.tabs.get() != "Portfolio"
        self.lbl_modo_aviso.configure(text="falta el capital inicial" if falta else "")

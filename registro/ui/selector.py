"""Selector global de cuenta (barra lateral): filtra todas las pantallas a la vez."""
import tkinter as tk
import customtkinter as ctk

from registro import cuentas as Q
from registro.db import db_cuentas, get_cuenta_global, set_cuenta_global
from registro.ui import vivo
from registro.ui.estado import save_ui_prefs
from registro.ui.tema import (
    BLUE, FONT_MAIN, HOVER, LINE2, MUTED, MUTED2, ON_BLUE, PAPER, RAD_CTRL, SP_LG, SP_XS, SURFACE)

vivo.registrar(globals())


class SelectorMixin:
    def _restaurar_cuenta(self):
        """Recupera la cuenta elegida la última vez (si todavía existe)."""
        sel = self._ui_prefs.get("cuenta_sel")
        try:
            claves = {Q.clave(c) for c in db_cuentas()}
        except Exception:
            claves = set()
        sel = tuple(sel) if isinstance(sel, (list, tuple)) and len(sel) == 2 else None
        set_cuenta_global(sel if sel in claves else None)

    def _build_selector(self, parent):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="x", padx=SP_LG, pady=(0, SP_LG))
        ctk.CTkLabel(wrap, text="CUENTA", font=(FONT_MAIN, 9), text_color=MUTED2,
                     anchor="w").pack(fill="x", padx=SP_XS, pady=(0, SP_XS))
        self.btn_cuenta = ctk.CTkButton(
            wrap, text=self._texto_cuenta(), anchor="w", height=34, corner_radius=RAD_CTRL,
            fg_color=SURFACE, hover_color=HOVER, text_color=PAPER, border_width=1, border_color=LINE2,
            font=(FONT_MAIN, 12), command=self._menu_cuenta)
        self.btn_cuenta.pack(fill="x")

    def _texto_cuenta(self):
        t = Q.texto_selector(db_cuentas(), get_cuenta_global())
        return (t if len(t) <= 22 else t[:21] + "…") + "  \u25be"

    def _menu_cuenta(self):
        actual = get_cuenta_global()
        m = tk.Menu(self, tearoff=0, bg=SURFACE, fg=PAPER, activebackground=BLUE,
                    activeforeground=ON_BLUE, bd=0, relief="flat",
                    font=(FONT_MAIN, max(8, round(10 * self.factor))))
        marca = lambda activo: "\u2713 " if activo else "    "
        m.add_command(label=f"{marca(not actual)}{Q.TODAS}", command=lambda: self._elegir_cuenta(None))
        cuentas = db_cuentas()
        for empresa, lista in Q.agrupar_por_empresa(cuentas):
            m.add_separator()
            m.add_command(label=f"  {empresa.upper()}", state="disabled", foreground=MUTED)
            for c in lista:
                signo = f"   {c['pnl']:+,.0f}" if c["n_ops"] else ""
                m.add_command(label=f"{marca(Q.clave(c) == actual)}{Q.titulo(c)}{signo}",
                              command=lambda c=c: self._elegir_cuenta(c))
        b = self.btn_cuenta
        try:
            m.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height() + 2)
        finally:
            m.grab_release()

    def _elegir_cuenta(self, c):
        """c = ficha de cuenta (dict de db_cuentas) o None para todas. Repinta la pantalla actual."""
        sel = Q.clave(c)
        set_cuenta_global(sel)
        self._ui_prefs["cuenta_sel"] = list(sel) if sel else None
        save_ui_prefs(self._ui_prefs)
        self.btn_cuenta.configure(text=self._texto_cuenta())
        self._table_dirty = True
        self._on_tab_change()

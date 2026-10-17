"""Pantalla(s) de la app como Mixin de App (_build_plan, _load_plan_into_editor, _save_plan…)."""
from tkinter import messagebox
import customtkinter as ctk

from registro.db import db_get_plan, db_save_plan
from registro.ui import vivo
from registro.ui.estado import CTX
from registro.ui.tema import (
    BLUE, BLUE_HI, FONT_MAIN, FONT_MONO, FONT_SERIF, LINE2, MUTED, PAPER, SURFACE)

vivo.registrar(globals())


class PlanMixin:
    def _build_plan(self):
        wrap = ctk.CTkFrame(self.tab_plan, fg_color="transparent")
        wrap.pack(fill="both", expand=True, pady=(6, 0))

        bar = ctk.CTkFrame(wrap, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(bar, text="Plan de trading — editable, se guarda en la base",
                     font=(FONT_SERIF, 20), text_color=PAPER).pack(side="left")
        self.plan_saved_lbl = ctk.CTkLabel(bar, text="", font=(FONT_MONO, 11), text_color=MUTED)
        self.plan_saved_lbl.pack(side="left", padx=14)
        ctk.CTkButton(bar, text="Guardar plan", width=140, height=32,
                      fg_color=BLUE, hover_color=BLUE_HI, font=(FONT_MAIN, 13),
                      command=self._save_plan).pack(side="right")
        ctk.CTkButton(bar, text="Restaurar plan por defecto", width=200, height=32,
                      fg_color="transparent", border_color=LINE2, border_width=1,
                      text_color=PAPER, hover_color=SURFACE, font=(FONT_MAIN, 12),
                      command=self._restore_plan).pack(side="right", padx=(0, 8))

        self.plan_box = ctk.CTkTextbox(wrap, font=(FONT_MONO, 13), fg_color=SURFACE,
                                       border_color=LINE2, border_width=1, wrap="word")
        self.plan_box.pack(fill="both", expand=True)
        self._load_plan_into_editor()

    def _load_plan_into_editor(self):
        if not hasattr(self, "plan_box"):
            return
        texto, actualizado = db_get_plan()
        self.plan_box.delete("1.0", "end")
        self.plan_box.insert("1.0", texto or "")
        if actualizado:
            self.plan_saved_lbl.configure(text=f"último guardado: {actualizado.replace('T', ' ')}")

    def _save_plan(self):
        texto = self.plan_box.get("1.0", "end").rstrip() + "\n"
        db_save_plan(texto)
        _, actualizado = db_get_plan()
        self.plan_saved_lbl.configure(text=f"guardado: {(actualizado or '').replace('T',' ')}")

    def _restore_plan(self):
        if messagebox.askyesno("Restaurar plan",
                               "¿Reemplazar el texto actual por el plan por defecto?\n"
                               "Se pierde lo que hayas editado."):
            self.plan_box.delete("1.0", "end")
            self.plan_box.insert("1.0", CTX.perfil.plan_inicial)

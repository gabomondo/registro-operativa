"""Pantalla(s) de la app como Mixin de App (_lbl, _section, _bar…)."""
import customtkinter as ctk

from registro.db import merged_values
from registro.ui import vivo
from registro.ui.estado import CTX
from registro.ui.tema import FONT_MAIN, FONT_MONO, FONT_SERIF, MUTED, PAPER, TRACK

vivo.registrar(globals())


class ComunesMixin:
    def _refresh_dropdowns(self):
        """Actualiza activo/tipo/empresa con base + valores usados, preservando
        lo que esté escrito ahora. Así lo que cargaste recién ya aparece."""
        for combo, base, campo in [
            (getattr(self, "e_activo", None),  CTX.perfil.activos,  "activo"),
            (getattr(self, "e_tipo", None),    CTX.perfil.tipos,    "tipo"),
            (getattr(self, "e_empresa", None), CTX.perfil.empresas, "empresa"),
        ]:
            if combo is None:
                continue
            cur = combo.get()
            combo.configure(values=merged_values(base, campo))
            if cur:
                combo.set(cur)

    def _lbl(self, parent, text):
        # label de campo: chico, en mayúsculas, tono muted — jerarquía secundaria
        return ctk.CTkLabel(parent, text=text.upper(), font=(FONT_MAIN, 10),
                            text_color=MUTED, anchor="w")

    def _section(self, parent, title):
        ctk.CTkLabel(parent, text=title, font=(FONT_SERIF,20), text_color=PAPER).pack(anchor="w", pady=(18,10))

    def _bar(self, parent, key, frac, color, mid_text, val_text, val_color=None):
        val_color = val_color or MUTED
        row = ctk.CTkFrame(parent, fg_color="transparent"); row.pack(fill="x", pady=3)
        ctk.CTkLabel(row, text=key, width=96, anchor="w", text_color=MUTED, font=(FONT_MAIN,12)).pack(side="left")
        track = ctk.CTkFrame(row, fg_color=TRACK, height=22, corner_radius=4)
        track.pack(side="left", fill="x", expand=True, padx=8)
        track.pack_propagate(False)
        relw = max(frac, 0.02)
        fill = ctk.CTkFrame(track, fg_color=color, corner_radius=4)
        fill.place(relx=0, rely=0, relwidth=relw, relheight=1)
        # si la barra es muy corta el texto no entra: lo mostramos afuera, sobre el track
        if frac >= 0.28:
            ctk.CTkLabel(fill, text=mid_text, text_color=PAPER, font=(FONT_MONO,11)).pack(side="left", padx=6)
        else:
            ctk.CTkLabel(track, text=mid_text, text_color=MUTED, font=(FONT_MONO,11)).place(relx=relw, rely=0.5, x=8, anchor="w")
        ctk.CTkLabel(row, text=val_text, width=88, anchor="e", text_color=val_color, font=(FONT_MONO,12)).pack(side="left")

    def _def(self, clave):
        """Primer valor de una lista del perfil (valor por defecto de un combo)."""
        vals = getattr(CTX.perfil, clave, None) or []
        return vals[0] if vals else ""

    def _reload_all(self):
        self._table_dirty = True
        self.render_table()
        self._reload_templates_into_combo()
        self.render_plantillas()
        self._load_plan_into_editor()
        self._refrescar_listas()

    def _refrescar_listas(self):
        """Aplica el perfil actual a los desplegables ya construidos."""
        self._refresh_dropdowns()
        p = CTX.perfil
        if hasattr(self, "e_cuenta"):
            cur = self.e_cuenta.get()
            self.e_cuenta.configure(values=list(p.tipos_cuenta))
            self.e_cuenta.set(cur if cur in p.tipos_cuenta else self._def("tipos_cuenta"))
        if hasattr(self, "flt_cuenta"):
            cur = self.flt_cuenta.get()
            vals = ["Todas"] + list(p.tipos_cuenta)
            self.flt_cuenta.configure(values=vals)
            self.flt_cuenta.set(cur if cur in vals else "Todas")
        if hasattr(self, "flt_tipo"):
            cur = self.flt_tipo.get()
            self.flt_tipo.configure(values=["Todos"] + merged_values(p.tipos, "tipo"))
            if cur:
                self.flt_tipo.set(cur)

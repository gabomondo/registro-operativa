"""Pantalla(s) de la app como Mixin de App (_build_plantillas, render_plantillas, _tpl_show_placeholder…)."""
from tkinter import messagebox
import customtkinter as ctk

from registro.db import (
    db_template_delete, db_template_save, db_template_usage, db_templates, new_item_id)
from registro.ui import vivo
from registro.ui.tema import (
    BORDER_W, FONT_MAIN, FONT_MONO, FONT_SERIF, HOVER, LINE2, MUTED, NEG_TXT, PAPER, RAD_CARD,
    RAD_CTRL, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SURFACE, SURFACE2)
from registro.ui.widgets import btn_ghost, btn_primary, styled_entry

vivo.registrar(globals())


class PlantillasMixin:
    def _build_plantillas(self):
        wrap = ctk.CTkFrame(self.tab_plantillas, fg_color="transparent")
        wrap.pack(fill="both", expand=True, pady=(SP_SM, 0))

        bar = ctk.CTkFrame(wrap, fg_color="transparent")
        bar.pack(fill="x", pady=(0, SP_MD))
        ctk.CTkLabel(bar, text="Plantillas de check — un set de reglas por estrategia",
                     font=(FONT_SERIF, 20), text_color=PAPER).pack(side="left")
        btn_primary(bar, "+ Nueva plantilla", self._tpl_new, width=170).pack(side="right")

        body = ctk.CTkFrame(wrap, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # izquierda: lista de plantillas
        left = ctk.CTkFrame(body, fg_color=SURFACE, corner_radius=RAD_CARD, width=260)
        left.pack(side="left", fill="y", padx=(0, SP_MD))
        left.pack_propagate(False)
        ctk.CTkLabel(left, text="TUS PLANTILLAS", font=(FONT_MAIN, 10),
                     text_color=MUTED).pack(anchor="w", padx=SP_LG, pady=(SP_LG, SP_SM))
        self.tpl_list_holder = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.tpl_list_holder.pack(fill="both", expand=True, padx=SP_SM, pady=(0, SP_SM))

        # derecha: editor de la plantilla seleccionada
        self.tpl_editor = ctk.CTkScrollableFrame(body, fg_color="transparent")
        self.tpl_editor.pack(side="left", fill="both", expand=True)

        self.tpl_edit_id = None       # id de la plantilla en edición (None = nueva)
        self.tpl_item_rows = []       # [(entry, item_id)] filas de ítems en el editor
        self.render_plantillas()

    def render_plantillas(self):
        """Refresca la lista de plantillas de la izquierda."""
        if not hasattr(self, "tpl_list_holder"):
            return
        for w in self.tpl_list_holder.winfo_children():
            w.destroy()
        tpls = db_templates()
        if not tpls:
            ctk.CTkLabel(self.tpl_list_holder, text="No hay plantillas.",
                         font=(FONT_MAIN, 12), text_color=MUTED).pack(anchor="w", padx=SP_SM, pady=SP_SM)
        for t in tpls:
            usage = db_template_usage(t["id"])
            sel = (t["id"] == self.tpl_edit_id)
            row = ctk.CTkFrame(self.tpl_list_holder,
                               fg_color=(HOVER if sel else "transparent"),
                               corner_radius=RAD_CTRL)
            row.pack(fill="x", pady=2)
            btn = ctk.CTkButton(row, text=t["nombre"], anchor="w",
                                fg_color="transparent", hover_color=HOVER,
                                text_color=PAPER, font=(FONT_MAIN, 13),
                                command=lambda tt=t: self._tpl_select(tt))
            btn.pack(fill="x", padx=SP_SM, pady=(SP_SM, 0))
            ctk.CTkLabel(row, text=f"{len(t['items'])} ítems · {usage} ops",
                         font=(FONT_MONO, 10), text_color=MUTED, anchor="w").pack(
                         anchor="w", padx=SP_MD, pady=(0, SP_SM))
        # si no hay nada en edición, mostrar cartel en el editor
        if self.tpl_edit_id is None and not self.tpl_item_rows:
            self._tpl_show_placeholder()

    def _tpl_show_placeholder(self):
        for w in self.tpl_editor.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.tpl_editor,
                     text="Elegí una plantilla de la izquierda para editarla,\no creá una nueva.",
                     font=(FONT_MAIN, 13), text_color=MUTED, justify="left").pack(anchor="w", pady=SP_XL)

    def _tpl_new(self):
        self.tpl_edit_id = None
        self._tpl_render_editor(nombre="", items=[])
        self.render_plantillas()

    def _tpl_select(self, tpl):
        self.tpl_edit_id = tpl["id"]
        self._tpl_render_editor(nombre=tpl["nombre"], items=list(tpl["items"]))
        self.render_plantillas()

    def _tpl_render_editor(self, nombre, items):
        """Dibuja el editor: nombre + lista editable de ítems + acciones."""
        for w in self.tpl_editor.winfo_children():
            w.destroy()
        self.tpl_item_rows = []

        head = ctk.CTkFrame(self.tpl_editor, fg_color="transparent")
        head.pack(fill="x", pady=(0, SP_MD))
        self._lbl(head, "Nombre de la plantilla").pack(anchor="w", pady=(0, SP_XS))
        self.tpl_name_entry = styled_entry(head, width=360, mono=False)
        if nombre:
            self.tpl_name_entry.insert(0, nombre)
        self.tpl_name_entry.pack(anchor="w")

        self._lbl(self.tpl_editor, "Ítems del check").pack(anchor="w", pady=(SP_MD, SP_XS))
        self.tpl_items_box = ctk.CTkFrame(self.tpl_editor, fg_color=SURFACE,
                                          corner_radius=RAD_CARD, border_color=LINE2,
                                          border_width=BORDER_W)
        self.tpl_items_box.pack(fill="x")
        for it in items:
            self._tpl_add_item_row(it.get("id"), it.get("label", ""))
        if not items:
            self._tpl_add_item_row(new_item_id(), "")

        add_row = ctk.CTkFrame(self.tpl_editor, fg_color="transparent")
        add_row.pack(fill="x", pady=(SP_SM, SP_MD))
        btn_ghost(add_row, "+ Agregar ítem", lambda: self._tpl_add_item_row(new_item_id(), ""),
                  width=160, height=32).pack(side="left")

        actions = ctk.CTkFrame(self.tpl_editor, fg_color="transparent")
        actions.pack(fill="x", pady=(SP_MD, SP_XL))
        btn_primary(actions, "Guardar plantilla", self._tpl_save, width=180, height=40).pack(side="left", padx=(0, SP_MD))
        if self.tpl_edit_id is not None:
            btn_ghost(actions, "Borrar plantilla", self._tpl_delete, width=160, height=40,
                      text_color=NEG_TXT).pack(side="left")

    def _tpl_add_item_row(self, item_id, label):
        row = ctk.CTkFrame(self.tpl_items_box, fg_color="transparent")
        row.pack(fill="x", padx=SP_MD, pady=SP_XS)
        entry = ctk.CTkEntry(row, height=32, font=(FONT_MAIN, 13),
                             fg_color=SURFACE2, border_color=LINE2, border_width=BORDER_W,
                             corner_radius=RAD_CTRL, text_color=PAPER,
                             placeholder_text="Texto de la regla…")
        if label:
            entry.insert(0, label)
        entry.pack(side="left", fill="x", expand=True, padx=(0, SP_SM))
        rec = [entry, item_id]
        def _remove():
            row.destroy()
            self.tpl_item_rows = [r for r in self.tpl_item_rows if r is not rec]
        ctk.CTkButton(row, text="✕", width=32, height=32, fg_color="transparent",
                      border_color=LINE2, border_width=BORDER_W, text_color=NEG_TXT,
                      hover_color=SURFACE, corner_radius=RAD_CTRL,
                      font=(FONT_MAIN, 13), command=_remove).pack(side="left")
        self.tpl_item_rows.append(rec)

    def _tpl_save(self):
        nombre = self.tpl_name_entry.get().strip()
        if not nombre:
            messagebox.showwarning("Plantilla", "Ponele un nombre a la plantilla.")
            return
        items = []
        for entry, iid in self.tpl_item_rows:
            try:
                txt = entry.get().strip()
            except Exception:
                continue
            if txt:
                items.append({"id": iid, "label": txt})
        if not items:
            messagebox.showwarning("Plantilla", "Agregá al menos un ítem con texto.")
            return
        new_id = db_template_save(nombre, items, tpl_id=self.tpl_edit_id)
        self.tpl_edit_id = new_id
        self.render_plantillas()
        # refrescar el combo del form de carga por si cambió algo
        self._reload_templates_into_combo(keep_id=self.cur_tpl_id)
        messagebox.showinfo("Plantilla", "Plantilla guardada.")

    def _tpl_delete(self):
        if self.tpl_edit_id is None:
            return
        usage = db_template_usage(self.tpl_edit_id)
        msg = "¿Borrar esta plantilla?"
        if usage:
            msg += (f"\n\n{usage} operaciones la usan. Esas operaciones NO se borran "
                    "y conservan sus tildes guardados, pero dejarán de estar asociadas "
                    "a una plantilla viva.")
        if not messagebox.askyesno("Borrar plantilla", msg):
            return
        db_template_delete(self.tpl_edit_id)
        self.tpl_edit_id = None
        self.tpl_item_rows = []
        self._tpl_show_placeholder()
        self.render_plantillas()
        self._reload_templates_into_combo(keep_id=self.cur_tpl_id)

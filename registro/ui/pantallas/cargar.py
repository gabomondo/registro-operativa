"""Pantalla(s) de la app como Mixin de App (_build_cargar, _reload_templates_into_combo, _on_tpl_change…)."""
from datetime import date, datetime

from tkinter import messagebox
import customtkinter as ctk

from registro.constantes import CHECK_KEYS
from registro.db import db_insert, db_templates, db_update, merged_values
from registro.stats import op_check_data
from registro.ui import vivo
from registro.ui.capturas import CaptureBox
from registro.ui.estado import CTX
from registro.ui.tema import (
    BLUE, BLUE_HI, BORDER_W, CAUTION, F_HIGH, F_LOW, F_MID, FONT_MAIN, FONT_MONO, HOVER, LINE2,
    MUTED, NEG_TXT, PAPER, POS_TXT, RAD_CARD, RAD_CTRL, SEG_HI, SEG_SEL, SP_LG, SP_MD, SP_SM,
    SP_XL, SP_XS, SURFACE)
from registro.ui.widgets import btn_ghost, DatePicker, styled_combo, styled_entry

vivo.registrar(globals())


class CargarMixin:
    def _build_cargar(self):
        f = ctk.CTkScrollableFrame(self.tab_cargar, fg_color="transparent")
        f.pack(fill="both", expand=True)

        row1 = ctk.CTkFrame(f, fg_color="transparent"); row1.pack(fill="x", pady=(SP_SM, SP_MD))
        # fecha
        c = ctk.CTkFrame(row1, fg_color="transparent"); c.pack(side="left", padx=(0, SP_LG))
        self._lbl(c, "Fecha").pack(anchor="w", pady=(0, SP_XS))
        self.e_fecha = DatePicker(c, width=130)
        self.e_fecha.insert(0, date.today().isoformat()); self.e_fecha.pack()
        # hora
        c = ctk.CTkFrame(row1, fg_color="transparent"); c.pack(side="left", padx=(0, SP_LG))
        self._lbl(c, "Hora").pack(anchor="w", pady=(0, SP_XS))
        self.e_hora = styled_entry(c, width=90, mono=True)
        self.e_hora.insert(0, datetime.now().strftime("%H:%M")); self.e_hora.pack()
        # activo
        c = ctk.CTkFrame(row1, fg_color="transparent"); c.pack(side="left", padx=(0, SP_LG))
        self._lbl(c, "Activo").pack(anchor="w", pady=(0, SP_XS))
        self.e_activo = styled_combo(c, merged_values(CTX.perfil.activos, "activo"),
                                     width=100, mono=True, default=self._def("activos"))
        self.e_activo.pack()
        # tipo
        c = ctk.CTkFrame(row1, fg_color="transparent"); c.pack(side="left", padx=(0, SP_LG))
        self._lbl(c, "Tipo de entrada").pack(anchor="w", pady=(0, SP_XS))
        self.e_tipo = styled_combo(c, merged_values(CTX.perfil.tipos, "tipo"),
                                   width=140, default=self._def("tipos"))
        self.e_tipo.pack()
        # profit
        c = ctk.CTkFrame(row1, fg_color="transparent"); c.pack(side="left", padx=(0, SP_LG))
        self._lbl(c, "Profit USD").pack(anchor="w", pady=(0, SP_XS))
        self.e_profit = styled_entry(c, width=110, mono=True, placeholder="0.00")
        self.e_profit.pack()

        row2 = ctk.CTkFrame(f, fg_color="transparent"); row2.pack(fill="x", pady=(0, SP_MD))
        # empresa
        c = ctk.CTkFrame(row2, fg_color="transparent"); c.pack(side="left", padx=(0, SP_LG))
        self._lbl(c, "Empresa").pack(anchor="w", pady=(0, SP_XS))
        self.e_empresa = styled_combo(c, merged_values(CTX.perfil.empresas, "empresa"),
                                      width=180, default="")
        self.e_empresa.pack()
        # cuenta
        c = ctk.CTkFrame(row2, fg_color="transparent"); c.pack(side="left", padx=(0, SP_LG))
        self._lbl(c, "Tipo de cuenta").pack(anchor="w", pady=(0, SP_XS))
        self.e_cuenta = styled_combo(c, list(CTX.perfil.tipos_cuenta), width=140, default=self._def("tipos_cuenta"))
        self.e_cuenta.pack()

        row3 = ctk.CTkFrame(f, fg_color="transparent"); row3.pack(fill="x", pady=(0,10))
        # mov SL — segmented, se lee de un vistazo
        c = ctk.CTkFrame(row3, fg_color="transparent"); c.pack(side="left", padx=(0,24))
        self._lbl(c, "¿Moviste el SL?").pack(anchor="w", pady=(0,4))
        self.movsl_val = ctk.StringVar(value="No")
        self.e_movsl = ctk.CTkSegmentedButton(c, variable=self.movsl_val,
            values=["No", "Sí (a favor)", "Sí (en contra)"],
            fg_color=SURFACE, selected_color=SEG_SEL, selected_hover_color=SEG_HI,
            unselected_color=SURFACE, unselected_hover_color=HOVER,
            text_color=PAPER, font=(FONT_MAIN, 12))
        self.e_movsl.set("No"); self.e_movsl.pack()
        # tranquilo — segmented
        c = ctk.CTkFrame(row3, fg_color="transparent"); c.pack(side="left", padx=(0,16))
        self._lbl(c, "¿Operaste tranquilo?").pack(anchor="w", pady=(0,4))
        self.tranq_val = ctk.StringVar(value="Sí")
        self.e_tranq = ctk.CTkSegmentedButton(c, variable=self.tranq_val,
            values=["Sí", "Más o menos", "No"],
            fg_color=SURFACE, selected_color=SEG_SEL, selected_hover_color=SEG_HI,
            unselected_color=SURFACE, unselected_hover_color=HOVER,
            text_color=PAPER, font=(FONT_MAIN, 12))
        self.e_tranq.set("Sí"); self.e_tranq.pack()

        # escala emocional
        c = ctk.CTkFrame(f, fg_color="transparent"); c.pack(fill="x", pady=(4,10))
        self._lbl(c, "Estado psicológico (1 = tilteado · 5 = en zona)").pack(anchor="w", pady=(0,6))
        scale_row = ctk.CTkFrame(c, fg_color="transparent"); scale_row.pack(anchor="w")
        self.emo_btns = []
        for v in range(1,6):
            b = ctk.CTkButton(scale_row, text=str(v), width=54, height=38,
                              fg_color="transparent", border_color=LINE2, border_width=1,
                              text_color=MUTED, hover_color=SURFACE, font=(FONT_MONO, 15),
                              command=lambda x=v: self._set_emo(x))
            b.pack(side="left", padx=(0,8))
            self.emo_btns.append(b)

        # comentario
        c = ctk.CTkFrame(f, fg_color="transparent"); c.pack(fill="x", pady=(4,10))
        self._lbl(c, "Comentario emocional").pack(anchor="w", pady=(0,6))
        self.e_coment = ctk.CTkTextbox(c, height=90, font=(FONT_MAIN, 13),
                                       fg_color=SURFACE, border_color=LINE2, border_width=1)
        self.e_coment.pack(fill="x")

        # ---- check de la operación — plantilla seleccionable + ítems dinámicos ----
        c = ctk.CTkFrame(f, fg_color="transparent"); c.pack(fill="x", pady=(SP_SM, SP_MD))
        chk_head = ctk.CTkFrame(c, fg_color="transparent"); chk_head.pack(fill="x")
        self._lbl(chk_head, "Check de la operación — tildá lo que cumpliste").pack(side="left", anchor="w", pady=(0, SP_XS))
        self.chk_count_lbl = ctk.CTkLabel(chk_head, text="", font=(FONT_MONO,12), text_color=MUTED)
        self.chk_count_lbl.pack(side="left", padx=SP_MD)

        # fila selector de plantilla
        tpl_row = ctk.CTkFrame(c, fg_color="transparent"); tpl_row.pack(fill="x", pady=(SP_XS, SP_SM))
        self._lbl(tpl_row, "Plantilla").pack(side="left", padx=(0, SP_SM))
        self.tpl_combo = styled_combo(tpl_row, [], width=240, default="")
        self.tpl_combo.configure(command=self._on_tpl_change)
        self.tpl_combo.pack(side="left")
        btn_ghost(tpl_row, "Gestionar plantillas", lambda: self.tabs.set("Plantillas"),
                  width=180, height=34).pack(side="left", padx=(SP_SM, 0))

        # grid de ítems (se rellena dinámicamente según la plantilla elegida)
        self.chk_grid = ctk.CTkFrame(c, fg_color=SURFACE, corner_radius=RAD_CARD,
                                     border_color=LINE2, border_width=BORDER_W)
        self.chk_grid.pack(fill="x")
        self.chk_vars = {}          # item_id -> IntVar
        self.chk_labels = {}        # item_id -> label (para reconstruir chk_data)
        self.cur_tpl_id = None
        self._reload_templates_into_combo()

        # capturas
        c = ctk.CTkFrame(f, fg_color="transparent"); c.pack(fill="x", pady=(6,10))
        self._lbl(c, "Capturas — recortá en NT8 y pegá con Ctrl+V").pack(anchor="w", pady=(0,6))
        caps = ctk.CTkFrame(c, fg_color="transparent"); caps.pack(fill="x")
        self.cap_ini = CaptureBox(caps, "ini", "Captura de inicio")
        self.cap_ini.pack(side="left", expand=True, fill="both", padx=(0,8))
        self.cap_fin = CaptureBox(caps, "fin", "Captura de fin")
        self.cap_fin.pack(side="left", expand=True, fill="both", padx=(8,0))

        # botones
        c = ctk.CTkFrame(f, fg_color="transparent"); c.pack(fill="x", pady=(SP_MD, SP_XL))
        self.btn_save = ctk.CTkButton(c, text="Guardar operación", width=180, height=42,
                                      fg_color=BLUE, hover_color=BLUE_HI, corner_radius=RAD_CTRL,
                                      font=(FONT_MAIN, 14), command=self.save_op)
        self.btn_save.pack(side="left", padx=(0, SP_MD))
        btn_ghost(c, "Limpiar", self.reset_form, width=110, height=42).pack(side="left")
        self.edit_note = ctk.CTkLabel(c, text="", text_color=CAUTION, font=(FONT_MAIN, 12))
        self.edit_note.pack(side="left", padx=SP_LG)

    def _reload_templates_into_combo(self, keep_id=None):
        """Refresca el combo de plantillas. Selecciona keep_id si se pasa, si no
        la primera disponible."""
        self._templates = db_templates()
        names = [t["nombre"] for t in self._templates]
        if not names:
            names = ["(sin plantillas)"]
        self.tpl_combo.configure(values=names)
        # elegir plantilla
        target = None
        if keep_id is not None:
            target = next((t for t in self._templates if t["id"] == keep_id), None)
        if target is None and self._templates:
            target = self._templates[0]
        if target:
            self.tpl_combo.set(target["nombre"])
            self._apply_template(target)
        else:
            self.tpl_combo.set("(sin plantillas)")
            self._apply_template(None)

    def _on_tpl_change(self, nombre):
        tpl = next((t for t in getattr(self, "_templates", []) if t["nombre"] == nombre), None)
        self._apply_template(tpl)

    def _apply_template(self, tpl):
        """Reconstruye el grid de checks según los ítems de la plantilla."""
        for w in self.chk_grid.winfo_children():
            w.destroy()
        self.chk_vars = {}
        self.chk_labels = {}
        self.cur_tpl_id = tpl["id"] if tpl else None

        if not tpl or not tpl["items"]:
            ctk.CTkLabel(self.chk_grid,
                         text="Esta plantilla no tiene ítems. Agregá algunos en «Gestionar plantillas».",
                         font=(FONT_MAIN, 12), text_color=MUTED).pack(anchor="w", padx=SP_LG, pady=SP_MD)
            self._update_chk_count()
            return

        for idx, item in enumerate(tpl["items"]):
            iid = item.get("id")
            label = item.get("label", "")
            var = ctk.IntVar(value=0)
            self.chk_vars[iid] = var
            self.chk_labels[iid] = label
            cb = ctk.CTkCheckBox(self.chk_grid, text=label, variable=var,
                                 font=(FONT_MAIN,13), text_color=PAPER,
                                 fg_color=BLUE, hover_color=BLUE_HI, border_color=LINE2,
                                 checkbox_width=22, checkbox_height=22,
                                 command=self._update_chk_count)
            r, col_i = divmod(idx, 2)
            cb.grid(row=r, column=col_i, sticky="w", padx=SP_LG, pady=SP_SM)
        self.chk_grid.grid_columnconfigure(0, weight=1)
        self.chk_grid.grid_columnconfigure(1, weight=1)
        self._update_chk_count()

    def _update_chk_count(self):
        n = sum(v.get() for v in self.chk_vars.values())
        total = len(self.chk_vars)
        col = POS_TXT if (total and n == total) else (CAUTION if n >= total - 1 and total else MUTED)
        self.chk_count_lbl.configure(text=f"{n}/{total} cumplidos", text_color=col)

    def _set_emo(self, v):
        self.emo_val.set(v)
        # tono según el valor elegido: rojo (tilteado) -> ámbar -> verde (en zona)
        accent = NEG_TXT if v <= 2 else (CAUTION if v == 3 else POS_TXT)
        fill   = F_LOW if v <= 2 else (F_MID if v == 3 else F_HIGH)
        for i,b in enumerate(self.emo_btns, start=1):
            if i <= v:
                b.configure(border_color=accent, fg_color=fill, text_color=PAPER)
            else:
                b.configure(border_color=LINE2, fg_color="transparent", text_color=MUTED)

    def _parse_movsl(self, s):
        if s.startswith("Sí (a favor)"): return "Sí (a favor)"
        if s.startswith("Sí (en contra)"): return "Sí (en contra)"
        return "No"

    def _parse_tranq(self, s):
        if s.startswith("Sí"): return "Sí"
        if s.startswith("No"): return "No"
        return "Más o menos"

    def save_op(self):
        fecha = self.e_fecha.get().strip()
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Fecha", "Formato de fecha inválido. Usá AAAA-MM-DD.")
            return
        try:
            profit = float(self.e_profit.get() or 0)
        except ValueError:
            messagebox.showwarning("Profit", "El profit tiene que ser un número.")
            return
        activo = self.e_activo.get().strip() or "NQ"
        tipo = self.e_tipo.get().strip()

        img_ini = self.cap_ini.commit(fecha, activo, tipo)
        img_fin = self.cap_fin.commit(fecha, activo, tipo)

        data = dict(
            fecha=fecha, hora=self.e_hora.get().strip(), activo=activo, tipo=tipo,
            profit=profit, empresa=self.e_empresa.get().strip(),
            cuenta=self.e_cuenta.get().strip(),
            mov_sl=self.e_movsl.get(),
            tranquilo=self.e_tranq.get(),
            emo=self.emo_val.get() or None,
            comentario=self.e_coment.get("1.0","end").strip(),
            img_ini=img_ini, img_fin=img_fin)
        # check dinámico: plantilla usada + resultados como datos
        data["tpl_id"] = self.cur_tpl_id
        data["chk_data"] = {iid: int(var.get()) for iid, var in self.chk_vars.items()}
        # compatibilidad legacy: si la op usa la plantilla original, además
        # llenamos las columnas chk_* viejas (mismos ids que las keys).
        for key in CHECK_KEYS:
            data[key] = int(self.chk_vars[key].get()) if key in self.chk_vars else 0

        if self.edit_id:
            db_update(self.edit_id, data)
        else:
            db_insert(data)
        self.reset_form()
        self._table_dirty = True
        self.tabs.set("Registro")
        self.render_table()

    def reset_form(self):
        self.edit_id = None
        self.e_profit.delete(0,"end")
        self.e_coment.delete("1.0","end")
        self.e_tipo.set(self._def("tipos")); self.e_empresa.set(""); self.e_cuenta.set(self._def("tipos_cuenta"))
        self.e_movsl.set("No"); self.e_tranq.set("Sí")
        self.e_activo.set(self._def("activos"))
        self.emo_val.set(0)
        for b in self.emo_btns:
            b.configure(border_color=LINE2, fg_color="transparent", text_color=MUTED)
        self.cap_ini.clear(); self.cap_fin.clear()
        # volver a la plantilla por defecto (primera) y limpiar tildes
        self._reload_templates_into_combo()
        self._update_chk_count()
        self.edit_note.configure(text="")
        self.e_fecha.delete(0,"end"); self.e_fecha.insert(0, date.today().isoformat())
        self.e_hora.delete(0,"end"); self.e_hora.insert(0, datetime.now().strftime("%H:%M"))

    def edit_op(self, op):
        self.edit_id = op["id"]
        self.e_fecha.delete(0,"end"); self.e_fecha.insert(0, op["fecha"])
        self.e_hora.delete(0,"end"); self.e_hora.insert(0, op["hora"] or "")
        self.e_activo.set(op["activo"] or self._def("activos"))
        self.e_tipo.set(op["tipo"] or self._def("tipos"))
        self.e_profit.delete(0,"end"); self.e_profit.insert(0, str(op["profit"]))
        self.e_empresa.set(op["empresa"] or "")
        self.e_cuenta.set(op["cuenta"] or self._def("tipos_cuenta"))
        self.e_movsl.set(op["mov_sl"] if op["mov_sl"] in ("No","Sí (a favor)","Sí (en contra)") else "No")
        self.e_tranq.set(op["tranquilo"] if op["tranquilo"] in ("Sí","Más o menos","No") else "Sí")
        self._set_emo(op["emo"] or 0)
        self.e_coment.delete("1.0","end"); self.e_coment.insert("1.0", op["comentario"] or "")
        self.cap_ini.load_existing(op["img_ini"])
        self.cap_fin.load_existing(op["img_fin"])
        # cargar la plantilla con la que se registró esta op y sus tildes
        op_tpl_id = op["tpl_id"] if "tpl_id" in op.keys() else None
        self._reload_templates_into_combo(keep_id=op_tpl_id)
        saved = op_check_data(op)
        for iid, var in self.chk_vars.items():
            var.set(int(saved.get(iid, 0) or 0))
        self._update_chk_count()
        self.edit_note.configure(text="Editando operación #%d" % op["id"])
        self.tabs.set("Cargar operación")

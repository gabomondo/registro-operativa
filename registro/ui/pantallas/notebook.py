"""Pantalla(s) de la app como Mixin de App (NB_CAMPOS, _build_notebook, _nb_valida…)."""
from datetime import date, datetime, timedelta

import customtkinter as ctk

from registro.db import db_nota_get, db_nota_save, db_range
from registro.ui import vivo
from registro.ui.estado import CTX
from registro.ui.tema import (
    BORDER_W, FONT_MAIN, FONT_MONO, FONT_SERIF, LINE2, MUTED, MUTED2, NEG_TXT, PAPER, POS_TXT,
    RAD_CARD, RAD_CTRL, SP_MD, SP_SM, SP_XS, SURFACE, SURFACE2, T_LOSS, T_WIN)
from registro.ui.widgets import btn_ghost, DatePicker

vivo.registrar(globals())


class NotebookMixin:
    NB_CAMPOS = [("plan", "Plan del día", "Qué vas a buscar hoy, qué vas a evitar, límites que te ponés."),
                 ("que_paso", "Qué pasó", "Cómo fue la sesión: decisiones, emociones, qué viste en el mercado."),
                 ("corregir", "Qué voy a corregir", "Una o dos cosas concretas para mañana.")]

    def _build_notebook(self):
        t = self.tab_notebook
        self.nb_fecha = date.today().isoformat()
        self._nb_job = None
        self._nb_poll_job = None
        top = ctk.CTkFrame(t, fg_color="transparent")
        top.pack(fill="x", pady=(SP_SM, SP_MD))
        btn_ghost(top, "◀", lambda: self._nb_mover(-1), width=40, height=34).pack(side="left")
        self.nb_date = DatePicker(top, width=122)
        self.nb_date.pack(side="left", padx=SP_SM)
        btn_ghost(top, "▶", lambda: self._nb_mover(1), width=40, height=34).pack(side="left")
        btn_ghost(top, "Hoy", lambda: self._nb_ir(date.today().isoformat()), width=70, height=34).pack(
            side="left", padx=(SP_MD, 0))
        self.nb_estado = ctk.CTkLabel(top, text="", font=(FONT_MAIN, 11), text_color=MUTED)
        self.nb_estado.pack(side="right")

        body = ctk.CTkFrame(t, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3, uniform="nb")
        body.grid_columnconfigure(1, weight=2, uniform="nb")
        body.grid_rowconfigure(0, weight=1)
        izq = ctk.CTkFrame(body, fg_color="transparent")
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, SP_MD))
        self.nb_boxes = {}
        for k, titulo, ayuda in self.NB_CAMPOS:
            self._lbl(izq, titulo).pack(anchor="w", pady=(SP_SM, 0))
            ctk.CTkLabel(izq, text=ayuda, font=(FONT_MAIN, 11), text_color=MUTED2, anchor="w").pack(anchor="w")
            tb = ctk.CTkTextbox(izq, height=110, font=(FONT_MAIN, 13), fg_color=SURFACE,
                                border_color=LINE2, border_width=BORDER_W, text_color=PAPER,
                                corner_radius=RAD_CTRL, wrap="word")
            tb.pack(fill="both", expand=True, pady=(SP_XS, 0))
            tb.bind("<KeyRelease>", lambda e: self._nb_programar())
            self.nb_boxes[k] = tb
        self.nb_dia = ctk.CTkScrollableFrame(body, fg_color=SURFACE, corner_radius=RAD_CARD)
        self.nb_dia.grid(row=0, column=1, sticky="nsew")

    def _nb_valida(self, f):
        try:
            datetime.strptime(f, "%Y-%m-%d"); return True
        except ValueError:
            return False

    def _nb_mover(self, d):
        self._nb_ir((datetime.strptime(self.nb_fecha, "%Y-%m-%d").date() + timedelta(days=d)).isoformat())

    def _nb_ir(self, f):
        self._nb_guardar()
        self.nb_fecha = f
        self.nb_date.set(f)
        self._nb_cargar()

    def _nb_programar(self):
        self.nb_estado.configure(text="escribiendo…")
        if self._nb_job is not None:
            self.after_cancel(self._nb_job)
        self._nb_job = self.after(800, self._nb_guardar)

    def _nb_guardar(self):
        if self._nb_job is not None:
            try: self.after_cancel(self._nb_job)
            except Exception: pass
            self._nb_job = None
        try:
            db_nota_save(self.nb_fecha, *[self.nb_boxes[k].get("1.0", "end").strip()
                                          for k, _t, _a in self.NB_CAMPOS])
            self.nb_estado.configure(text="guardado ✓")
        except Exception:
            CTX.log.exception("No pude guardar la nota")
            self.nb_estado.configure(text="no se pudo guardar")

    def _nb_cargar(self):
        n = db_nota_get(self.nb_fecha)
        for k, _t, _a in self.NB_CAMPOS:
            tb = self.nb_boxes[k]
            tb.delete("1.0", "end")
            tb.insert("1.0", n.get(k) or "")
        self.nb_estado.configure(text="")
        for w in self.nb_dia.winfo_children():
            w.destroy()
        ops = sorted(db_range(self.nb_fecha, self.nb_fecha), key=lambda o: o["hora"] or "")
        d = self.nb_dia
        ctk.CTkLabel(d, text="EL DÍA EN NÚMEROS", font=(FONT_MAIN, 10), text_color=MUTED).pack(
            anchor="w", padx=SP_MD, pady=(SP_MD, SP_XS))
        if not ops:
            ctk.CTkLabel(d, text="Sin operaciones este día.", font=(FONT_MAIN, 12),
                         text_color=MUTED).pack(anchor="w", padx=SP_MD, pady=SP_SM)
            return
        pn = sum(o["profit"] or 0 for o in ops)
        w = sum(1 for o in ops if (o["profit"] or 0) > 0)
        ctk.CTkLabel(d, text=f"{pn:+,.2f} USD", font=(FONT_SERIF, 30),
                     text_color=POS_TXT if pn >= 0 else NEG_TXT).pack(anchor="w", padx=SP_MD)
        ctk.CTkLabel(d, text=f"{len(ops)} trades · {round(w / len(ops) * 100)}% win",
                     font=(FONT_MONO, 11), text_color=MUTED).pack(anchor="w", padx=SP_MD, pady=(0, SP_SM))
        for o in ops:
            p = o["profit"] or 0
            fila = ctk.CTkFrame(d, fg_color=(T_WIN[0] if p > 0 else T_LOSS[0] if p < 0 else SURFACE2),
                                corner_radius=RAD_CTRL)
            fila.pack(fill="x", padx=SP_SM, pady=2)
            ctk.CTkLabel(fila, text=f"{o['hora'] or '—'}  {o['activo'] or ''}  {o['tipo'] or ''}".strip(),
                         font=(FONT_MONO, 11), text_color=PAPER, anchor="w").pack(side="left", padx=SP_SM, pady=SP_XS)
            ctk.CTkLabel(fila, text=f"{p:+,.2f}", font=(FONT_MONO, 11),
                         text_color=POS_TXT if p > 0 else NEG_TXT).pack(side="right", padx=SP_SM)

    def render_notebook(self):
        self.nb_date.set(self.nb_fecha)
        self._nb_cargar()
        if self._nb_poll_job is None:
            self._nb_poll()

    def _nb_poll(self):
        """Detecta que cambiaste la fecha (a mano o desde el calendario)."""
        self._nb_poll_job = None
        if self.tabs.get() != "Notebook":
            return
        f = self.nb_date.get()
        if f != self.nb_fecha and self._nb_valida(f):
            self._nb_guardar()
            self.nb_fecha = f
            self._nb_cargar()
        self._nb_poll_job = self.after(400, self._nb_poll)

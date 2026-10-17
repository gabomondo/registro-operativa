"""Pantalla(s) de la app como Mixin de App (_build_calendario, _cal_nav, _cal_ultimo…)."""
import calendar

import customtkinter as ctk

from registro import calendario as CAL
from registro.db import db_all, db_notas_rango
from registro.ui import vivo
from registro.ui.tema import (
    BORDER_W, FONT_MAIN, FONT_MONO, FONT_SERIF, LINE, LINE2, MUTED, MUTED2, NEG, NEG_TXT,
    PAPER, POS, POS_TXT, RAD_CTRL, SP_MD, SP_SM, SP_XS, SURFACE, SURFACE2, T_LOSS, T_WIN)
from registro.ui.widgets import btn_ghost

vivo.registrar(globals())


class CalendarioMixin:
    def _build_calendario(self):
        t = self.tab_calendario
        self.cal_y, self.cal_m = CAL.mes_actual_con_datos({})
        top = ctk.CTkFrame(t, fg_color="transparent")
        top.pack(fill="x", pady=(SP_SM, SP_MD))
        btn_ghost(top, "◀", lambda: self._cal_nav(-1), width=40, height=34).pack(side="left")
        self.cal_titulo = ctk.CTkLabel(top, text="", font=(FONT_SERIF, 26), text_color=PAPER, width=230)
        self.cal_titulo.pack(side="left", padx=SP_SM)
        btn_ghost(top, "▶", lambda: self._cal_nav(1), width=40, height=34).pack(side="left")
        btn_ghost(top, "Último mes con datos", self._cal_ultimo, width=170, height=34).pack(
            side="left", padx=(SP_MD, 0))
        self.cal_resumen = ctk.CTkLabel(top, text="", font=(FONT_MONO, 12), text_color=MUTED)
        self.cal_resumen.pack(side="right")
        self.cal_grid = ctk.CTkFrame(t, fg_color="transparent")
        self.cal_grid.pack(fill="both", expand=True)
        ctk.CTkLabel(t, text="Click: ver las operaciones de ese día  ·  Click derecho: abrir la nota del día  ·  ✎ = tiene nota",
                     font=(FONT_MAIN, 11), text_color=MUTED2).pack(anchor="w", pady=(SP_SM, 0))
        self._cal_inicial = True

    def _cal_nav(self, d):
        f = CAL.mes_siguiente if d > 0 else CAL.mes_anterior
        self.cal_y, self.cal_m = f(self.cal_y, self.cal_m)
        self.render_calendario()

    def _cal_ultimo(self):
        self.cal_y, self.cal_m = CAL.mes_actual_con_datos(CAL.resumen_dias(db_all(fechas=False)))
        self.render_calendario()

    def render_calendario(self):
        dias = CAL.resumen_dias(db_all(fechas=False))
        if getattr(self, "_cal_inicial", False):
            self.cal_y, self.cal_m = CAL.mes_actual_con_datos(dias)
            self._cal_inicial = False
        g = CAL.grilla(self.cal_y, self.cal_m, dias)
        ult = calendar.monthrange(self.cal_y, self.cal_m)[1]
        notas = db_notas_rango(f"{self.cal_y}-{self.cal_m:02d}-01", f"{self.cal_y}-{self.cal_m:02d}-{ult}")
        self.cal_titulo.configure(text=g["titulo"])
        col = POS_TXT if g["total"] >= 0 else NEG_TXT
        self.cal_resumen.configure(
            text=(f"{self._m(g['total'])}{self._unidad()} · {g['dias_op']} días · {g['verdes']} verdes / {g['rojos']} rojos"
                  if g["dias_op"] else "Sin operaciones este mes"),
            text_color=col if g["dias_op"] else MUTED)
        for w in self.cal_grid.winfo_children():
            w.destroy()
        ncol = 7 if g["con_finde"] else 5
        for c in range(ncol):
            self.cal_grid.grid_columnconfigure(c, weight=1, uniform="cal")
            ctk.CTkLabel(self.cal_grid, text=CAL.DIAS_CORTOS[c].upper(), font=(FONT_MAIN, 10),
                         text_color=MUTED).grid(row=0, column=c, sticky="w", padx=SP_SM, pady=(0, SP_XS))
        self.cal_grid.grid_columnconfigure(ncol, weight=1, uniform="cal")
        ctk.CTkLabel(self.cal_grid, text="SEMANA", font=(FONT_MAIN, 10), text_color=MUTED).grid(
            row=0, column=ncol, sticky="w", padx=SP_SM, pady=(0, SP_XS))
        for r, sem in enumerate(g["semanas"], start=1):
            self.cal_grid.grid_rowconfigure(r, weight=1, uniform="calr")
            for c, cel in enumerate(sem["celdas"][:ncol]):
                self._cal_celda(r, c, cel, notas)
            card = ctk.CTkFrame(self.cal_grid, fg_color=SURFACE2, corner_radius=RAD_CTRL,
                                border_color=LINE, border_width=BORDER_W)
            card.grid(row=r, column=ncol, sticky="nsew", padx=2, pady=2)
            if sem["neto"] is not None:
                ctk.CTkLabel(card, text=self._m(sem["neto"]), font=(FONT_SERIF, 20),
                             text_color=POS_TXT if sem["neto"] >= 0 else NEG_TXT).pack(expand=True, pady=(SP_SM, 0))
                ctk.CTkLabel(card, text=f"{sem['n']} trades", font=(FONT_MONO, 9),
                             text_color=MUTED).pack(pady=(0, SP_SM))

    def _cal_celda(self, r, c, cel, notas):
        if not cel["en_mes"]:
            ctk.CTkFrame(self.cal_grid, fg_color="transparent", height=10).grid(row=r, column=c)
            return
        if cel["neto"] is None:
            bg, bd = SURFACE, LINE
        elif cel["neto"] > 0:
            bg, bd = T_WIN[0], POS
        elif cel["neto"] < 0:
            bg, bd = T_LOSS[0], NEG
        else:
            bg, bd = SURFACE2, LINE2
        f = ctk.CTkFrame(self.cal_grid, fg_color=bg, corner_radius=RAD_CTRL,
                         border_color=bd if cel["neto"] is not None else LINE, border_width=BORDER_W)
        f.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
        head = ctk.CTkFrame(f, fg_color="transparent"); head.pack(fill="x", padx=SP_SM, pady=(SP_XS, 0))
        ctk.CTkLabel(head, text=str(cel["dia"]), font=(FONT_MAIN, 11),
                     text_color=MUTED if cel["neto"] is not None else MUTED2).pack(side="left")
        if cel["fecha"] in notas:
            ctk.CTkLabel(head, text="✎", font=(FONT_MAIN, 11), text_color=MUTED).pack(side="right")
        widgets = [f, head] + list(head.winfo_children())
        if cel["neto"] is not None:
            l1 = ctk.CTkLabel(f, text=self._m(cel["neto"]), font=(FONT_SERIF, 20),
                              text_color=POS_TXT if cel["neto"] > 0 else (NEG_TXT if cel["neto"] < 0 else MUTED))
            l1.pack(expand=True, pady=(0, 0))
            l2 = ctk.CTkLabel(f, text=f"{cel['n']} {'trade' if cel['n'] == 1 else 'trades'}",
                              font=(FONT_MONO, 9), text_color=MUTED)
            l2.pack(pady=(0, SP_XS))
            widgets += [l1, l2]
        for w in widgets:
            w.configure(cursor="hand2") if cel["neto"] is not None or cel["fecha"] in notas else None
            if cel["neto"] is not None:
                w.bind("<Button-1>", lambda e, d=cel["fecha"]: self._ir_a_dia(d))
            w.bind("<Button-3>", lambda e, d=cel["fecha"]: self._abrir_nota(d))

    def _ir_a_dia(self, fecha):
        self.flt_desde.delete(0, "end"); self.flt_desde.insert(0, fecha)
        self.flt_hasta.delete(0, "end"); self.flt_hasta.insert(0, fecha)
        self.tabs.set("Registro")
        self.render_table()

    def _abrir_nota(self, fecha):
        self.nb_fecha = fecha
        self.tabs.set("Notebook")
        self._on_tab_change()

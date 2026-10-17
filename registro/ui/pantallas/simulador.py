"""Pantalla(s) de la app como Mixin de App (_build_simulador, _sim_programar, _sim_limpiar…)."""
from datetime import date, timedelta

import customtkinter as ctk
import tkinter as tk

from registro import simulador as SIM
from registro.db import db_all
from registro.ui import vivo
from registro.ui.estado import DPI_SISTEMA
from registro.ui.tema import (
    BLUE_HI, FONT_MAIN, FONT_SERIF, HOVER, LINE2, MUTED, MUTED2, NEG_TXT, PAPER, POS_TXT,
    RAD_CARD, RAD_CTRL, SEG_HI, SEG_SEL, SP_LG, SP_MD, SP_SM, SP_XS, SURFACE, SURFACE2)
from registro.ui.widgets import btn_ghost, styled_combo, styled_entry

vivo.registrar(globals())


class SimuladorMixin:
    def _build_simulador(self):
        t = self.tab_simulador
        t.grid_columnconfigure(0, weight=2, uniform="sm")
        t.grid_columnconfigure(1, weight=3, uniform="sm")
        t.grid_rowconfigure(0, weight=1)
        izq = ctk.CTkScrollableFrame(t, fg_color=SURFACE, corner_radius=RAD_CARD)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, SP_MD), pady=(SP_SM, 0))
        self.sim_res = ctk.CTkScrollableFrame(t, fg_color=SURFACE, corner_radius=RAD_CARD)
        self.sim_res.grid(row=0, column=1, sticky="nsew", pady=(SP_SM, 0))

        ctk.CTkLabel(izq, text="PERÍODO", font=(FONT_MAIN, 10), text_color=MUTED).pack(
            anchor="w", padx=SP_LG, pady=(SP_LG, SP_XS))
        self.sim_periodo = ctk.CTkSegmentedButton(
            izq, values=["30 días", "Este mes", "Todo"], height=30, font=(FONT_MAIN, 12),
            fg_color=SURFACE2, selected_color=SEG_SEL, selected_hover_color=SEG_HI,
            unselected_color=SURFACE2, unselected_hover_color=HOVER, text_color=PAPER,
            command=lambda v: self.render_simulador())
        self.sim_periodo.set("Todo")
        self.sim_periodo.pack(anchor="w", padx=SP_LG)
        ctk.CTkLabel(izq, text="REGLAS A PROBAR  (dejá vacío lo que no quieras usar)", font=(FONT_MAIN, 10),
                     text_color=MUTED).pack(anchor="w", padx=SP_LG, pady=(SP_LG, SP_XS))
        self.sim_ent = {}

        def fila(clave, texto, ancho=70, ph=""):
            f = ctk.CTkFrame(izq, fg_color="transparent"); f.pack(fill="x", padx=SP_LG, pady=3)
            e = styled_entry(f, width=ancho, mono=True, placeholder=ph)
            e.pack(side="right")
            ctk.CTkLabel(f, text=texto, font=(FONT_MAIN, 12), text_color=PAPER, anchor="w",
                         wraplength=220, justify="left").pack(side="left", fill="x", expand=True)
            e.bind("<KeyRelease>", lambda ev: self._sim_programar())
            self.sim_ent[clave] = e

        fila("max_perdidas", "Cortar el día tras N pérdidas", ph="2")
        fila("max_trades", "Máximo de trades por día", ph="5")
        fila("perdida_dia", "Cortar el día al llegar a −USD", ph="300")
        fila("meta_dia", "Cortar el día al llegar a +USD", ph="500")
        fila("hora_limite", "No abrir trades desde las (HH:MM)", ph="12:00")
        f = ctk.CTkFrame(izq, fg_color="transparent"); f.pack(fill="x", padx=SP_LG, pady=3)
        self.sim_emo = styled_combo(f, ["—", "2", "3", "4"], width=70, mono=True, default="—")
        self.sim_emo.configure(command=lambda v: self.render_simulador())
        self.sim_emo.pack(side="right")
        ctk.CTkLabel(f, text="Saltear trades con estado emocional menor a", font=(FONT_MAIN, 12),
                     text_color=PAPER, anchor="w", wraplength=220, justify="left").pack(side="left")
        ctk.CTkLabel(izq, text="DÍAS QUE NO OPERARÍAS", font=(FONT_MAIN, 10), text_color=MUTED).pack(
            anchor="w", padx=SP_LG, pady=(SP_MD, SP_XS))
        dr = ctk.CTkFrame(izq, fg_color="transparent"); dr.pack(fill="x", padx=SP_LG)
        self.sim_dias = []
        for i, d in enumerate(["Lun", "Mar", "Mié", "Jue", "Vie"]):
            v = ctk.IntVar(value=0)
            ctk.CTkCheckBox(dr, text=d, variable=v, width=20, checkbox_width=18, checkbox_height=18,
                            font=(FONT_MAIN, 12), command=self.render_simulador).pack(side="left", padx=(0, SP_SM))
            self.sim_dias.append(v)
        pr = ctk.CTkFrame(izq, fg_color="transparent"); pr.pack(fill="x", padx=SP_LG, pady=(SP_LG, SP_LG))
        btn_ghost(pr, "Limpiar", self._sim_limpiar, width=90, height=30).pack(side="left")
        ctk.CTkLabel(izq, text="Es un ejercicio sobre el pasado: con otras reglas habrías operado distinto. "
                               "Sirve para ver cuánto pesan tus hábitos, no para prometer resultados.",
                     font=(FONT_MAIN, 10), text_color=MUTED2, wraplength=290, justify="left", anchor="w").pack(
                         anchor="w", padx=SP_LG, pady=(0, SP_LG))
        self._sim_job = None

    def _sim_programar(self):
        if self._sim_job is not None:
            self.after_cancel(self._sim_job)
        self._sim_job = self.after(400, self.render_simulador)

    def _sim_limpiar(self):
        for e in self.sim_ent.values():
            e.delete(0, "end")
        self.sim_emo.set("—")
        for v in self.sim_dias:
            v.set(0)
        self.render_simulador()

    def _sim_reglas(self):
        def num(k, tipo=float):
            try:
                v = self.sim_ent[k].get().strip().replace(",", ".")
                return tipo(v) if v else None
            except ValueError:
                return None
        hl = self.sim_ent["hora_limite"].get().strip()
        emo = self.sim_emo.get()
        return {"max_perdidas": num("max_perdidas", int), "max_trades": num("max_trades", int),
                "perdida_dia": num("perdida_dia"), "meta_dia": num("meta_dia"),
                "hora_limite": hl if SIM._hm(hl) is not None else None,
                "emo_min": int(emo) if emo.isdigit() else None,
                "sin_dias": [i for i, v in enumerate(self.sim_dias) if v.get()]}

    def render_simulador(self):
        self._sim_job = None
        for w in self.sim_res.winfo_children():
            w.destroy()
        hoy = date.today()
        per = self.sim_periodo.get()
        f = {}
        if per == "30 días": f["desde"] = (hoy - timedelta(days=29)).isoformat()
        elif per == "Este mes": f["desde"] = hoy.replace(day=1).isoformat()
        rows = db_all(f, fechas=False)
        reglas = self._sim_reglas()
        d = self.sim_res
        if not [o for o in rows if o.get("profit") is not None]:
            ctk.CTkLabel(d, text="Sin operaciones en este período", font=(FONT_SERIF, 24),
                         text_color=PAPER).pack(pady=(50, 4))
            return
        r = SIM.simular(rows, reglas)
        ctk.CTkLabel(d, text="RESULTADO DE LA SIMULACIÓN", font=(FONT_MAIN, 10), text_color=MUTED).pack(
            anchor="w", padx=SP_LG, pady=(SP_LG, SP_XS))
        if not SIM.hay_reglas(reglas):
            ctk.CTkLabel(d, text="Elegí una regla a la izquierda", font=(FONT_SERIF, 26), text_color=PAPER).pack(
                anchor="w", padx=SP_LG)
            ctk.CTkLabel(d, text=f"Hoy: {r['base']:+,.0f} USD en {r['n_base']} trades.", font=(FONT_MAIN, 12),
                         text_color=MUTED).pack(anchor="w", padx=SP_LG, pady=(0, SP_MD))
        else:
            col = POS_TXT if r["delta"] > 0 else (NEG_TXT if r["delta"] < 0 else MUTED)
            ctk.CTkLabel(d, text=f"{r['delta']:+,.0f} USD", font=(FONT_SERIF, 40), text_color=col).pack(
                anchor="w", padx=SP_LG)
            frase = ("Con esa regla habrías terminado mejor." if r["delta"] > 0 else
                     "Con esa regla habrías terminado peor." if r["delta"] < 0 else "No cambia el resultado.")
            ctk.CTkLabel(d, text=frase, font=(FONT_MAIN, 12), text_color=MUTED).pack(anchor="w", padx=SP_LG)
            fila = ctk.CTkFrame(d, fg_color="transparent"); fila.pack(fill="x", padx=SP_LG, pady=SP_MD)
            for i, (lab, val, c) in enumerate([
                    ("Real", f"{r['base']:+,.0f}", PAPER), ("Con la regla", f"{r['nuevo']:+,.0f}", col),
                    ("Trades", f"{r['n_nuevo']} de {r['n_base']}", PAPER)]):
                fila.grid_columnconfigure(i, weight=1, uniform="smr")
                cd = ctk.CTkFrame(fila, fg_color=SURFACE2, corner_radius=RAD_CTRL)
                cd.grid(row=0, column=i, sticky="nsew", padx=2)
                ctk.CTkLabel(cd, text=lab.upper(), font=(FONT_MAIN, 9), text_color=MUTED).pack(
                    anchor="w", padx=SP_MD, pady=(SP_SM, 0))
                ctk.CTkLabel(cd, text=val, font=(FONT_SERIF, 22), text_color=c).pack(
                    anchor="w", padx=SP_MD, pady=(0, SP_SM))
            q = r["quitados"]
            gan = [o for o in q if o["profit"] > 0]; per_ = [o for o in q if o["profit"] < 0]
            if q:
                ctk.CTkLabel(
                    d, text=(f"Te hubieras ahorrado {len(per_)} perdedores ({sum(o['profit'] for o in per_):+,.0f} USD) "
                             f"y perdido {len(gan)} ganadores ({sum(o['profit'] for o in gan):+,.0f} USD)."),
                    font=(FONT_MAIN, 12), text_color=PAPER, wraplength=480, justify="left", anchor="w").pack(
                        anchor="w", padx=SP_LG, pady=(0, SP_SM))
            else:
                ctk.CTkLabel(d, text=SIM.explicar_sin_efecto(rows, reglas), font=(FONT_MAIN, 12),
                             text_color=MUTED, wraplength=480, justify="left", anchor="w").pack(
                                 anchor="w", padx=SP_LG, pady=(0, SP_SM))
        # curvas
        H = int(190 * DPI_SISTEMA)
        cv = tk.Canvas(d, height=H, bg=SURFACE, highlightthickness=0)
        cv.pack(fill="x", padx=SP_LG, pady=(SP_SM, SP_XS))
        cv.bind("<Configure>", lambda e, c=cv, rr=r: self._sim_dibujar(c, rr))
        self.after(50, lambda c=cv, rr=r: self._sim_dibujar(c, rr))
        lg = ctk.CTkFrame(d, fg_color="transparent"); lg.pack(anchor="w", padx=SP_LG, pady=(0, SP_LG))
        ctk.CTkLabel(lg, text="━ real", font=(FONT_MAIN, 11), text_color=MUTED).pack(side="left")
        ctk.CTkLabel(lg, text="━ con la regla", font=(FONT_MAIN, 11), text_color=BLUE_HI).pack(
            side="left", padx=(SP_MD, 0))

    def _sim_dibujar(self, cv, r):
        if not cv.winfo_exists():
            return
        cv.delete("all")
        W, H = cv.winfo_width(), cv.winfo_height()
        if W < 60 or len(r["curva_base"]) < 2:
            return
        sc = self._ws()
        pl, pr, pt, pb = int(8 * sc), int(8 * sc), int(10 * sc), int(14 * sc)
        base = [0.0] + r["curva_base"]
        nv = [0.0] + r["curva_alineada"]
        lo, hi = min(base + nv), max(base + nv)
        if hi == lo:
            hi += 1; lo -= 1
        n = len(base)
        def X(i): return pl + (W - pl - pr) * i / max(1, n - 1)
        def Y(v): return pt + (H - pt - pb) * (1 - (v - lo) / (hi - lo))
        if lo <= 0 <= hi:
            cv.create_line(pl, Y(0), W - pr, Y(0), fill=LINE2, dash=(3, 3))
        cv.create_line(*[c for i, v in enumerate(base) for c in (X(i), Y(v))], fill=MUTED, width=2)
        cv.create_line(*[c for i, v in enumerate(nv) for c in (X(i), Y(v))], fill=BLUE_HI, width=2)

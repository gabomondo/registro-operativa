"""Pantalla(s) de la app como Mixin de App (_build_analisis, _analisis_filtros, render_analisis…)."""
from tkinter import ttk
import customtkinter as ctk

from registro import psico as PSI
from registro.db import db_all, db_cuentas
from registro.ui import vivo
from registro.ui.estado import CTX
from registro.ui.tema import (
    FONT_MAIN, FONT_MONO, FONT_SERIF, MUTED, MUTED2, NEG_TXT, PAPER, POS_TXT, RAD_CARD,
    SP_LG, SP_MD, SP_SM, SP_XS, SURFACE, SURFACE2, T_LOSS, T_LOSS_SOFT,
    T_WIN, T_WIN_SOFT)
from registro.ui.widgets import btn_ghost, styled_combo

vivo.registrar(globals())


class AnalisisMixin:
    def _build_analisis(self):
        t = self.tab_analisis
        top = ctk.CTkFrame(t, fg_color="transparent")
        top.pack(fill="x", pady=(SP_SM, SP_SM))
        f2 = ctk.CTkFrame(top, fg_color="transparent"); f2.pack(side="left")
        ctk.CTkLabel(f2, text="TIPO DE CUENTA", font=(FONT_MAIN, 9), text_color=MUTED2).pack(anchor="w")
        self.an_cuenta = styled_combo(f2, ["Todas"] + list(CTX.perfil.tipos_cuenta), width=150, default="Todas")
        self.an_cuenta.configure(command=lambda v: self.render_analisis())
        self.an_cuenta.pack(anchor="w", pady=(SP_XS, 0))
        btn_ghost(top, "Exportar reporte…", lambda: self.abrir_exportar(True), width=150, height=32).pack(
            side="right", anchor="s")
        self.an_body = ctk.CTkScrollableFrame(t, fg_color="transparent")
        self.an_body.pack(fill="both", expand=True)
        self._analisis_ok = True

    def _analisis_filtros(self):
        f = {}      # el período lo da el rango global (encabezado)
        c = self.an_cuenta.get()
        if c and c != "Todas":
            f["cuenta"] = c
        return f

    def render_analisis(self):
        from registro import analisis as A
        if not getattr(self, "_analisis_ok", False):
            return
        self.an_cuenta.configure(values=["Todas"] + list(CTX.perfil.tipos_cuenta))
        for w in self.an_body.winfo_children():
            w.destroy()
        rows = db_all(self._analisis_filtros())
        r = A.resumen(rows)
        if not r:
            ctk.CTkLabel(self.an_body, text="Sin operaciones en este período",
                         font=(FONT_SERIF, 24), text_color=PAPER).pack(pady=(50, 4))
            ctk.CTkLabel(self.an_body, text="Cambiá el período o cargá / importá operaciones.",
                         font=(FONT_MAIN, 13), text_color=MUTED).pack()
            return

        def num(v, d=0): return self._m(v, d if not self._en_pct() else 2)
        col = POS_TXT if r["neto"] >= 0 else NEG_TXT
        cards = [
            ("Neto", num(r["neto"]), col, f"{r['n']} trades · {r['trades_por_dia']:.1f} por día"),
            ("Win rate", f"{r['wr']:.0f}%", PAPER, f"{r['dias_verdes']}/{r['dias']} días verdes ({r['pct_dias_verdes']:.0f}%)"),
            ("Profit factor", "—" if r["profit_factor"] is None else f"{r['profit_factor']:.2f}",
             PAPER, "ganado / perdido"),
            ("Expectativa", num(r["expectativa"], 1), POS_TXT if r["expectativa"] >= 0 else NEG_TXT, "USD por trade" if not self._en_pct() else "del capital por trade"),
            ("Ganador / perdedor", f"{self._m(r['prom_ganador'])}/{self._m(r['prom_perdedor'])}", PAPER,
             "" if r["payoff"] is None else f"payoff {r['payoff']:.2f}"),
            ("Mejor / peor día", f"{self._m(r['mejor_dia']['neto'])}/{self._m(r['peor_dia']['neto'])}", PAPER,
             f"promedio {self._m(r['prom_dia'])} por día"),
        ]
        sg = ctk.CTkFrame(self.an_body, fg_color="transparent")
        sg.pack(fill="x", pady=(0, SP_LG))
        for i, (lab, val, c, sub) in enumerate(cards):
            sg.grid_columnconfigure(i, weight=1, uniform="k")
            card = ctk.CTkFrame(sg, fg_color=SURFACE, corner_radius=RAD_CARD)
            card.grid(row=0, column=i, sticky="nsew", padx=SP_XS)
            ctk.CTkLabel(card, text=lab.upper(), font=(FONT_MAIN, 9), text_color=MUTED,
                         anchor="w").pack(anchor="w", padx=SP_MD, pady=(SP_MD, 0))
            ctk.CTkLabel(card, text=val, font=(FONT_SERIF, 18 if "/" in val else 24),
                         text_color=c, anchor="w").pack(anchor="w", padx=SP_MD)
            ctk.CTkLabel(card, text=sub or " ", font=(FONT_MONO, 9), text_color=MUTED,
                         anchor="w").pack(anchor="w", padx=SP_MD, pady=(0, SP_MD))

        try:
            self._an_lectura(A, rows)
        except Exception:
            CTX.log.exception("Análisis: lectura")
        try:
            self._an_riesgo(rows)
        except Exception:
            CTX.log.exception("Análisis: métricas de riesgo")

        cols = ctk.CTkFrame(self.an_body, fg_color="transparent")
        cols.pack(fill="both", expand=True)
        cols.grid_columnconfigure(0, weight=3, uniform="c")
        cols.grid_columnconfigure(1, weight=2, uniform="c")
        izq = ctk.CTkFrame(cols, fg_color="transparent"); izq.grid(row=0, column=0, sticky="nsew", padx=(0, SP_SM))
        der = ctk.CTkFrame(cols, fg_color="transparent"); der.grid(row=0, column=1, sticky="nsew", padx=(SP_SM, 0))
        self._an_tabla_dias(izq, A.por_dia(rows))
        self._an_barras(der, "Por hora de entrada", A.por_hora(rows))
        self._an_barras(der, "Por activo", A.por_activo(rows))
        lados = A.por_lado(rows)
        if lados:
            self._an_barras(der, "Long vs Short", lados)
        self._an_barras(der, "Por día de la semana", A.por_dia_semana(rows))
        setups = A._agrupar(rows, lambda o: o.get("tipo") or None, orden=lambda x: -x["neto"])
        if setups:
            self._an_barras(der, "Por setup (playbook)", setups)
        pc = A.por_cuenta(rows, db_cuentas())
        if len(pc) > 1:      # varias cuentas en juego: ver cuál rinde
            self._an_barras(der, "Por cuenta", pc, ancho=130)
        self._an_psico(self.an_body, rows)
        ctk.CTkLabel(self.an_body, text="Barras tenues = menos de 5 trades (muestra chica, no saques conclusiones). "
                     "La hora es la de entrada, en el horario de tu registro.",
                     font=(FONT_MAIN, 10), text_color=MUTED2, anchor="w", justify="left",
                     wraplength=900).pack(anchor="w", pady=(SP_MD, SP_LG))

    def _an_lectura(self, A, rows):
        """Bloque «Lectura»: el período contado en palabras (resultado, ritmo, cuándo, qué)."""
        bloques = A.narrativa(rows, fm=lambda v: self._m(v, 0 if not self._en_pct() else 2))
        if not bloques:
            return
        card = ctk.CTkFrame(self.an_body, fg_color=SURFACE, corner_radius=RAD_CARD)
        card.pack(fill="x", pady=(0, SP_LG))
        ctk.CTkLabel(card, text="LECTURA DEL PERÍODO", font=(FONT_MAIN, 9), text_color=MUTED,
                     anchor="w").pack(anchor="w", padx=SP_LG, pady=(SP_MD, SP_SM))
        for tit, txt in bloques:
            fila = ctk.CTkFrame(card, fg_color="transparent"); fila.pack(fill="x", padx=SP_LG, pady=(0, SP_SM))
            ctk.CTkLabel(fila, text=tit, font=(FONT_SERIF, 14), text_color=PAPER, width=90,
                         anchor="nw").pack(side="left", anchor="n")
            ctk.CTkLabel(fila, text=txt, font=(FONT_MAIN, 12), text_color=MUTED, anchor="w",
                         justify="left", wraplength=820).pack(side="left", fill="x", expand=True)
        ctk.CTkFrame(card, height=SP_SM, fg_color="transparent").pack()

    def _an_riesgo(self, rows):
        """Segunda fila de tarjetas: drawdown, rachas, costos y duración."""
        from registro import metricas as MET
        e = MET.extra(rows)
        if not e:
            return
        def usd(v, d=0): return self._m(v, d)
        dd = e["dd_max"]
        sub_dd = (f"{e['dd_desde'] or 'inicio'} → {e['dd_hasta']}" if dd > 0 else "sin caídas")
        if dd > 0 and e["dd_actual"] > 0:
            sub_dd += f" · hoy −{self._m(e['dd_actual'], signo=False)}"
        rg, rp = e["racha_gan"], e["racha_perd"]
        com = e["comisiones"]
        cards = [
            ("Drawdown máx.", f"−{self._m(dd, signo=False)}" if dd > 0 else "0", NEG_TXT if dd > 0 else PAPER, sub_dd),
            ("Recovery factor", "—" if e["recovery"] is None else f"{e['recovery']:.2f}", PAPER,
             "neto / drawdown máx."),
            ("Racha ganadora", f"{rg['n']} trades", POS_TXT if rg["n"] else PAPER, usd(rg["usd"]) + self._unidad()),
            ("Racha perdedora", f"{rp['n']} trades", NEG_TXT if rp["n"] else PAPER, usd(rp["usd"]) + self._unidad()),
            ("Costos", "—" if com is None else f"−{self._m(com, signo=False)}", PAPER,
             "sin datos de costo" if com is None else (
                 f"{e['pct_comision_bruto']:.1f}% del bruto" if e["pct_comision_bruto"] is not None
                 else f"{e['n_con_comision']} trades con costo")),
            ("Duración media", MET.fmt_duracion(e["dur_prom_min"]), PAPER,
             "solo trades importados" if e["dur_prom_min"] is None else f"{e['n_con_duracion']} trades"),
        ]
        sg = ctk.CTkFrame(self.an_body, fg_color="transparent")
        sg.pack(fill="x", pady=(0, SP_LG))
        for i, (lab, val, c, sub) in enumerate(cards):
            sg.grid_columnconfigure(i, weight=1, uniform="k2")
            card = ctk.CTkFrame(sg, fg_color=SURFACE, corner_radius=RAD_CARD)
            card.grid(row=0, column=i, sticky="nsew", padx=SP_XS)
            ctk.CTkLabel(card, text=lab.upper(), font=(FONT_MAIN, 9), text_color=MUTED,
                         anchor="w").pack(anchor="w", padx=SP_MD, pady=(SP_MD, 0))
            ctk.CTkLabel(card, text=val, font=(FONT_SERIF, 22), text_color=c,
                         anchor="w").pack(anchor="w", padx=SP_MD)
            ctk.CTkLabel(card, text=sub or " ", font=(FONT_MONO, 9), text_color=MUTED,
                         anchor="w", wraplength=150, justify="left").pack(
                             anchor="w", padx=SP_MD, pady=(0, SP_MD))

    def _an_tabla_dias(self, parent, dias):
        card = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=RAD_CARD)
        card.pack(fill="x", anchor="n")      # alto propio: no se estira hasta igualar la columna derecha
        ctk.CTkLabel(card, text="POR DÍA", font=(FONT_MAIN, 10), text_color=MUTED,
                     anchor="w").pack(anchor="w", padx=SP_LG, pady=(SP_LG, SP_SM))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SP_SM, pady=(0, SP_SM))
        cols = [("fecha", "Fecha", 88, "w"), ("dia", "Día", 40, "w"), ("n", "Trades", 58, "e"),
                ("neto", "Neto", 76, "e"), ("wr", "Win", 46, "e"), ("mejor", "Mejor", 62, "e"),
                ("peor", "Peor", 62, "e"), ("acum", "Acum.", 80, "e")]
        ws = self._ws()
        tree = ttk.Treeview(inner, columns=[c[0] for c in cols], show="headings",
                            style="Gabo.Treeview", selectmode="none", height=min(max(len(dias), 3), 14))
        for k, lab, w, a in cols:
            tree.heading(k, text=lab, anchor=("w" if a == "w" else "e"))
            tree.column(k, width=int(w * ws), minwidth=int(30 * ws), anchor=a, stretch=(k == "acum"))
        for res, (a, b) in {"win": T_WIN, "loss": T_LOSS,
                            "flat": (SURFACE, SURFACE2)}.items():
            tree.tag_configure(f"{res}_a", background=a, foreground=PAPER)
            tree.tag_configure(f"{res}_b", background=b, foreground=PAPER)
        for i, d in enumerate(dias):
            res = "win" if d["neto"] > 0 else "loss" if d["neto"] < 0 else "flat"
            tree.insert("", "end", tags=(f"{res}_{'a' if i % 2 == 0 else 'b'}",), values=(
                d["label"], d["dia"], d["n"], f"{d['neto']:+,.2f}", f"{d['wr']:.0f}%",
                f"{d['mejor']:+,.2f}", f"{d['peor']:+,.2f}", f"{d['acum']:+,.2f}"))
        sb = ctk.CTkScrollbar(inner, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

    def _an_psico(self, parent, rows):
        """El costo de la psicología: cruza lo que anotás con el resultado en USD."""
        fac = PSI.analizar(rows)
        card = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=RAD_CARD)
        card.pack(fill="x", pady=(SP_MD, 0))
        ctk.CTkLabel(card, text="EL COSTO DE LA PSICOLOGÍA", font=(FONT_MAIN, 10), text_color=MUTED,
                     anchor="w").pack(anchor="w", padx=SP_LG, pady=(SP_LG, SP_XS))
        if not fac:
            ctk.CTkLabel(card, text="Cargá el estado emocional, si operaste tranquilo o el checklist en tus "
                                    "operaciones y acá vas a ver cuánto te cuesta (o te rinde) cada estado.",
                         font=(FONT_MAIN, 12), text_color=MUTED, wraplength=900, justify="left").pack(
                             anchor="w", padx=SP_LG, pady=(0, SP_LG))
            return
        costo = PSI.total_costo(fac)
        if costo > 0:
            top = max((f for f in fac if not f["chica"]), key=lambda f: f["costo"])
            mala = next(g for g in top["grupos"] if g["mala"])
            ctk.CTkLabel(card, text=f"≈ {costo:,.0f} USD", font=(FONT_SERIF, 32), text_color=NEG_TXT).pack(
                anchor="w", padx=SP_LG)
            ctk.CTkLabel(card, text=f"Es lo que rinden de menos tus trades con «{mala['label']}» "
                                    f"({top['titulo'].lower()}) frente al resto: {top['n_mala']} trades.",
                         font=(FONT_MAIN, 12), text_color=MUTED, wraplength=900, justify="left").pack(
                             anchor="w", padx=SP_LG, pady=(0, SP_SM))
        else:
            ctk.CTkLabel(card, text="Sin evidencia de costo todavía", font=(FONT_SERIF, 24),
                         text_color=PAPER).pack(anchor="w", padx=SP_LG)
            ctk.CTkLabel(card, text="Con los datos cargados no se ve que operar en mal estado te cueste plata "
                                    "(o falta muestra).", font=(FONT_MAIN, 12), text_color=MUTED,
                         wraplength=900, justify="left").pack(anchor="w", padx=SP_LG, pady=(0, SP_SM))
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=SP_SM)
        grid.grid_columnconfigure(0, weight=1, uniform="ps"); grid.grid_columnconfigure(1, weight=1, uniform="ps")
        for i, f in enumerate(fac):
            cont = ctk.CTkFrame(grid, fg_color="transparent")
            cont.grid(row=i // 2, column=i % 2, sticky="nsew", padx=SP_XS)
            self._an_barras(cont, f["titulo"] + ("  ·  muestra chica" if f["chica"] else ""), f["grupos"])
        ctk.CTkLabel(card, text="Es una correlación sobre tus propios datos, no una causa. Con menos de "
                                f"{PSI.MUESTRA_MINIMA} trades en un grupo no se saca conclusión.",
                     font=(FONT_MAIN, 10), text_color=MUTED2, anchor="w", wraplength=900, justify="left").pack(
                         anchor="w", padx=SP_LG, pady=(0, SP_LG))

    def _an_barras(self, parent, titulo, items, ancho=62):
        if not items:
            return
        card = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=RAD_CARD)
        card.pack(fill="x", pady=(0, SP_MD))
        ctk.CTkLabel(card, text=titulo.upper(), font=(FONT_MAIN, 10), text_color=MUTED,
                     anchor="w").pack(anchor="w", padx=SP_LG, pady=(SP_LG, SP_SM))
        mx = max(abs(x["neto"]) for x in items) or 1
        BW = 56
        for x in items:
            tenue = x["n"] < 5
            fila = ctk.CTkFrame(card, fg_color="transparent")
            fila.pack(fill="x", padx=SP_LG, pady=1)
            ctk.CTkLabel(fila, text=f"{x['n']} · {x['wr']:.0f}%", anchor="e", font=(FONT_MONO, 10),
                         text_color=MUTED2).pack(side="right")
            ctk.CTkLabel(fila, text=str(x["label"]), width=ancho, anchor="w", font=(FONT_MONO, 11),
                         text_color=MUTED if tenue else PAPER).pack(side="left")
            neg = ctk.CTkFrame(fila, fg_color="transparent", width=BW, height=16)
            neg.pack(side="left"); neg.pack_propagate(False)
            pos = ctk.CTkFrame(fila, fg_color="transparent", width=BW, height=16)
            pos.pack(side="left"); pos.pack_propagate(False)
            largo = max(2, int(BW * abs(x["neto"]) / mx))
            if x["neto"] < 0:
                ctk.CTkFrame(neg, fg_color=(T_LOSS_SOFT if tenue else NEG_TXT), width=largo, height=12,
                             corner_radius=2).pack(side="right")
            else:
                ctk.CTkFrame(pos, fg_color=(T_WIN_SOFT if tenue else POS_TXT), width=largo, height=12,
                             corner_radius=2).pack(side="left")
            ctk.CTkLabel(fila, text=f"{x['neto']:+,.0f}", width=58, anchor="e", font=(FONT_MONO, 11),
                         text_color=(MUTED if tenue else (POS_TXT if x["neto"] >= 0 else NEG_TXT))
                         ).pack(side="left", padx=(SP_SM, 0))
        ctk.CTkFrame(card, fg_color="transparent", height=SP_SM).pack()

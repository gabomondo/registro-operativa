"""Pantalla(s) de la app como Mixin de App (_build_revision, _shift_week, _week_bounds…)."""
from datetime import date, datetime, timedelta

import customtkinter as ctk

from registro import reporte as REP
from registro.db import db_notas_rango, db_range, db_template
from registro.stats import op_check_data, op_check_full
from registro.ui import vivo
from registro.ui.tema import (
    BLUE, BLUE_HI, FONT_MAIN, FONT_MONO, FONT_SERIF, LINE2, MUTED, NEG, NEG_TXT, PAPER, POS,
    POS_TXT, RAD_CARD, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SURFACE)
from registro.ui.widgets import btn_ghost

vivo.registrar(globals())


class RevisionMixin:
    def _build_revision(self):
        nav = ctk.CTkFrame(self.tab_revision, fg_color="transparent"); nav.pack(fill="x", pady=(6,10))
        ctk.CTkButton(nav, text="← Anterior", width=100, height=28, fg_color="transparent",
                      border_color=LINE2, border_width=1, text_color=PAPER, hover_color=SURFACE,
                      font=(FONT_MAIN,12), command=lambda: self._shift_week(-1)).pack(side="left")
        self.wk_lbl = ctk.CTkLabel(nav, text="", font=(FONT_MONO,13), text_color=PAPER, width=240)
        self.wk_lbl.pack(side="left", padx=10)
        ctk.CTkButton(nav, text="Siguiente →", width=100, height=28, fg_color="transparent",
                      border_color=LINE2, border_width=1, text_color=PAPER, hover_color=SURFACE,
                      font=(FONT_MAIN,12), command=lambda: self._shift_week(1)).pack(side="left")
        ctk.CTkButton(nav, text="Esta semana", width=110, height=28, fg_color=BLUE,
                      hover_color=BLUE_HI, font=(FONT_MAIN,12),
                      command=lambda: self._shift_week(0, reset=True)).pack(side="left", padx=(10,0))
        self.rev_holder = ctk.CTkScrollableFrame(self.tab_revision, fg_color="transparent")
        self.rev_holder.pack(fill="both", expand=True)

    def _shift_week(self, d, reset=False):
        self.wk_offset = 0 if reset else self.wk_offset + d
        self.render_revision()

    def _week_bounds(self):
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        monday = monday + timedelta(weeks=self.wk_offset)
        sunday = monday + timedelta(days=6)
        return monday.isoformat(), sunday.isoformat()

    def _rev_hallazgos(self, wk, desde, hasta):
        """Patrones que detecta el diario con reglas simples + resumen para pegar en Claude."""
        d0 = datetime.strptime(desde, "%Y-%m-%d").date()
        prev = db_range((d0 - timedelta(days=7)).isoformat(), (d0 - timedelta(days=1)).isoformat())
        hs = REP.hallazgos(wk, prev)
        card = ctk.CTkFrame(self.rev_holder, fg_color=SURFACE, corner_radius=RAD_CARD)
        card.pack(fill="x", pady=(0, SP_SM))
        cab = ctk.CTkFrame(card, fg_color="transparent"); cab.pack(fill="x", padx=SP_LG, pady=(SP_LG, SP_SM))
        ctk.CTkLabel(cab, text="LO QUE DETECTÓ TU DIARIO ESTA SEMANA", font=(FONT_MAIN, 10),
                     text_color=MUTED).pack(side="left")
        msg = ctk.CTkLabel(cab, text="", font=(FONT_MAIN, 11), text_color=MUTED)
        msg.pack(side="right", padx=(SP_SM, 0))
        btn_ghost(cab, "Copiar resumen para Claude", lambda: self._rev_copiar(wk, prev, desde, hasta, msg),
                  width=210, height=30).pack(side="right")
        if not hs:
            ctk.CTkLabel(card, text="Todavía no hay nada para marcar.", font=(FONT_MAIN, 12),
                         text_color=MUTED).pack(anchor="w", padx=SP_LG, pady=(0, SP_LG))
            return
        marca = {"bien": ("●", POS_TXT), "alerta": ("●", NEG_TXT), "info": ("●", MUTED)}
        for nivel, texto in hs[:8]:
            f = ctk.CTkFrame(card, fg_color="transparent"); f.pack(fill="x", padx=SP_LG, pady=2)
            ctk.CTkLabel(f, text=marca[nivel][0], font=(FONT_MAIN, 11), text_color=marca[nivel][1],
                         width=16).pack(side="left", anchor="n", pady=2)
            ctk.CTkLabel(f, text=texto, font=(FONT_MAIN, 13), text_color=PAPER, anchor="w",
                         justify="left", wraplength=860).pack(side="left", fill="x", expand=True)
        ctk.CTkFrame(card, fg_color="transparent", height=SP_SM).pack()

    def _rev_copiar(self, wk, prev, desde, hasta, msg):
        notas = []
        for f, n in sorted(db_notas_rango(desde, hasta).items()):
            t = " / ".join(x for x in (n.get("que_paso"), n.get("corregir")) if x)
            if t:
                notas.append((f, t.replace("\n", " ")))
        txt = REP.texto_para_claude(wk, f"semana {desde} a {hasta}", prev, notas)
        self.clipboard_clear(); self.clipboard_append(txt); self.update()
        msg.configure(text="copiado ✓ — pegalo en tu chat de Claude")

    def render_revision(self):
        for w in self.rev_holder.winfo_children(): w.destroy()
        desde, hasta = self._week_bounds()
        self.wk_lbl.configure(text=f"{desde}  →  {hasta}")
        wk = db_range(desde, hasta)
        if not wk:
            ctk.CTkLabel(self.rev_holder, text="Sin operaciones esta semana",
                         font=(FONT_SERIF,24), text_color=PAPER).pack(pady=(50,4))
            ctk.CTkLabel(self.rev_holder, text="Navegá a otra semana o cargá operaciones.",
                         font=(FONT_MAIN,13), text_color=MUTED).pack()
            return

        n = len(wk)
        wins = sum(1 for o in wk if (o["profit"] or 0)>0)
        wr = round(wins/n*100) if n else 0
        pnl = sum(o["profit"] or 0 for o in wk)
        moved = sum(1 for o in wk if (o["mov_sl"] or "").startswith("Sí"))
        moved_pct = round(moved/n*100) if n else 0
        emos = [o["emo"] for o in wk if o["emo"]]
        avg_emo = f"{sum(emos)/len(emos):.1f}" if emos else "—"

        # stat cards
        sg = ctk.CTkFrame(self.rev_holder, fg_color="transparent"); sg.pack(fill="x", pady=(SP_SM, SP_XL))
        def stat(label, val, color=PAPER):
            card = ctk.CTkFrame(sg, fg_color=SURFACE, corner_radius=RAD_CARD); card.pack(side="left", expand=True, fill="both", padx=SP_XS)
            ctk.CTkLabel(card, text=label.upper(), font=(FONT_MAIN,10), text_color=MUTED).pack(anchor="w", padx=SP_LG, pady=(SP_LG,SP_XS))
            ctk.CTkLabel(card, text=val, font=(FONT_SERIF,30), text_color=color).pack(anchor="w", padx=SP_LG, pady=(0,SP_MD))
        stat("Operaciones", str(n))
        stat("Win rate", f"{wr}%")
        stat("P&L semana", self._m(pnl), POS_TXT if pnl>=0 else NEG_TXT)
        stat("Movió SL", f"{moved_pct}%")
        stat("Emo prom.", f"{avg_emo}"+(" / 5" if avg_emo!="—" else ""))

        self._rev_hallazgos(wk, desde, hasta)

        # P&L por estado emocional
        self._section(self.rev_holder, "P&L por estado emocional")
        by_emo = {i:{"pnl":0.0,"n":0,"w":0} for i in range(1,6)}
        for o in wk:
            if o["emo"]:
                by_emo[o["emo"]]["pnl"] += o["profit"] or 0
                by_emo[o["emo"]]["n"] += 1
                if (o["profit"] or 0)>0: by_emo[o["emo"]]["w"] += 1
        max_abs = max([1]+[abs(x["pnl"]) for x in by_emo.values()])
        for i in range(5,0,-1):
            x = by_emo[i]
            if not x["n"]: continue
            self._bar(self.rev_holder, f"Emo {i} ({x['n']} ops)",
                      abs(x["pnl"])/max_abs, POS if x["pnl"]>=0 else NEG,
                      f"{self._m(x['pnl'])}{self._unidad()}",
                      f"{round(x['w']/x['n']*100)}% WR")

        # disciplina SL
        self._section(self.rev_holder, "Disciplina en el SL")
        sl_groups = {"No":{"n":0,"pnl":0.0},"Sí (a favor)":{"n":0,"pnl":0.0},"Sí (en contra)":{"n":0,"pnl":0.0}}
        for o in wk:
            k = o["mov_sl"] or "No"
            if k in sl_groups: sl_groups[k]["n"]+=1; sl_groups[k]["pnl"]+=o["profit"] or 0
        for k,x in sl_groups.items():
            if not x["n"]: continue
            self._bar(self.rev_holder, k, x["n"]/n, LINE2,
                      f"{x['n']} ops",
                      self._m(x["pnl"]),
                      val_color=POS_TXT if x["pnl"]>=0 else NEG_TXT)

        # ---- cumplimiento del check vs P&L (según la plantilla de cada op) ----
        self._section(self.rev_holder, "Cumplimiento del plan (check por operación)")
        full = [o for o in wk if op_check_full(o)]
        partial = [o for o in wk if o not in full]
        def grp_stats(g):
            if not g: return (0, 0.0, 0)
            pnl = sum(o["profit"] or 0 for o in g)
            w = sum(1 for o in g if (o["profit"] or 0) > 0)
            return (len(g), pnl, round(w/len(g)*100))
        for label, g in [("Check completo", full), ("Check incompleto", partial)]:
            ng, pnlg, wrg = grp_stats(g)
            if not ng: continue
            self._bar(self.rev_holder, label, ng/n,
                      POS if pnlg >= 0 else NEG,
                      f"{ng} ops · {wrg}% WR",
                      self._m(pnlg),
                      val_color=POS_TXT if pnlg >= 0 else NEG_TXT)

        # P&L por ítem incumplido (dónde duele romper cada regla).
        # Agrupa por ETIQUETA de ítem: si dos plantillas comparten un texto de
        # regla, se suman; si no, cada regla aparece por separado. Solo cuenta
        # ops que TENÍAN ese ítem en su plantilla y no lo cumplieron.
        item_stats = {}   # label -> [n, pnl]
        for o in wk:
            data = op_check_data(o)
            tpl = db_template(o["tpl_id"]) if ("tpl_id" in o.keys() and o["tpl_id"]) else None
            labels = {it["id"]: it["label"] for it in (tpl["items"] if tpl else [])}
            for iid, val in data.items():
                if not val:  # no cumplido
                    lbl = labels.get(iid)
                    if not lbl:
                        continue  # ítem que ya no existe en la plantilla viva
                    acc = item_stats.setdefault(lbl, [0, 0.0])
                    acc[0] += 1
                    acc[1] += o["profit"] or 0
        if item_stats:
            self._section(self.rev_holder, "P&L en trades donde NO cumpliste cada ítem")
            max_abs = max([1] + [abs(p) for _, p in item_stats.values()])
            for lbl, (cnt, pnl) in sorted(item_stats.items(), key=lambda x: x[1][1]):
                self._bar(self.rev_holder, lbl if len(lbl) <= 34 else lbl[:32]+"…",
                          abs(pnl)/max_abs, NEG if pnl < 0 else POS,
                          f"{cnt} ops sin cumplir",
                          self._m(pnl),
                          val_color=NEG_TXT if pnl < 0 else POS_TXT)

        # diario emocional
        notes = sorted([o for o in wk if o["comentario"]], key=lambda o:(o["fecha"],o["hora"] or ""))
        if notes:
            self._section(self.rev_holder, "Diario emocional de la semana")
            for o in notes:
                strip = ctk.CTkFrame(self.rev_holder, fg_color="transparent")
                strip.pack(fill="x", pady=(0,10))
                bar = ctk.CTkFrame(strip, fg_color=(POS if (o["profit"] or 0)>=0 else NEG), width=3)
                bar.pack(side="left", fill="y")
                body = ctk.CTkFrame(strip, fg_color="transparent"); body.pack(side="left", fill="x", expand=True, padx=(10,0))
                meta = f"{o['fecha']} {o['hora'] or ''} · {o['tipo']} · {self._m(o['profit'] or 0, 2)} · emo {o['emo'] or '—'}/5"
                ctk.CTkLabel(body, text=meta, anchor="w", text_color=MUTED, font=(FONT_MONO,11)).pack(anchor="w")
                ctk.CTkLabel(body, text=o["comentario"], anchor="w", justify="left",
                             text_color=PAPER, font=(FONT_MAIN,13), wraplength=980).pack(anchor="w")

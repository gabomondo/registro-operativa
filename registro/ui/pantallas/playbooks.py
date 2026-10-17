"""Pantalla(s) de la app como Mixin de App (_build_playbooks, _pb_datos, render_playbooks…)."""
from tkinter import messagebox
import customtkinter as ctk

from registro import analisis as A
from registro.db import db_all, db_playbook_delete, db_playbook_save, db_playbooks
from registro.ui import vivo
from registro.ui.tema import (
    BLUE_HI, BORDER_W, FONT_MAIN, FONT_MONO, FONT_SERIF, LINE, LINE2, MUTED, MUTED2, NAV_SEL,
    NEG_TXT, PAPER, POS_TXT, RAD_CARD, RAD_CTRL, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SURFACE,
    SURFACE2)
from registro.ui.widgets import btn_ghost, btn_primary, styled_entry

vivo.registrar(globals())


class PlaybooksMixin:
    def _build_playbooks(self):
        t = self.tab_playbooks
        self.pb_sel = None            # nombre del playbook seleccionado (None = nuevo)
        t.grid_columnconfigure(0, weight=2, uniform="pb")
        t.grid_columnconfigure(1, weight=3, uniform="pb")
        t.grid_rowconfigure(0, weight=1)
        izq = ctk.CTkFrame(t, fg_color=SURFACE, corner_radius=RAD_CARD)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, SP_MD), pady=(SP_SM, 0))
        cab = ctk.CTkFrame(izq, fg_color="transparent"); cab.pack(fill="x", padx=SP_LG, pady=(SP_LG, SP_SM))
        ctk.CTkLabel(cab, text="TUS SETUPS", font=(FONT_MAIN, 10), text_color=MUTED).pack(side="left")
        btn_primary(cab, "+ Nuevo", self._pb_nuevo, width=90, height=30).pack(side="right")
        self.pb_lista = ctk.CTkScrollableFrame(izq, fg_color="transparent")
        self.pb_lista.pack(fill="both", expand=True, padx=SP_SM, pady=(0, SP_SM))
        der = ctk.CTkFrame(t, fg_color=SURFACE, corner_radius=RAD_CARD)
        der.grid(row=0, column=1, sticky="nsew", pady=(SP_SM, 0))
        sc = ctk.CTkScrollableFrame(der, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=SP_SM, pady=SP_SM)
        self._lbl(sc, "Nombre del setup").pack(anchor="w", padx=SP_MD, pady=(SP_SM, SP_XS))
        self.pb_nombre = styled_entry(sc, width=320, mono=False)
        self.pb_nombre.pack(anchor="w", padx=SP_MD)
        self._lbl(sc, "En una línea: qué es").pack(anchor="w", padx=SP_MD, pady=(SP_MD, SP_XS))
        self.pb_desc = styled_entry(sc, width=520, mono=False)
        self.pb_desc.pack(anchor="w", padx=SP_MD)
        self._lbl(sc, "Reglas (una por línea: entrada, SL, objetivo, cuándo NO operarlo)").pack(
            anchor="w", padx=SP_MD, pady=(SP_MD, SP_XS))
        self.pb_reglas = ctk.CTkTextbox(sc, height=170, font=(FONT_MAIN, 13), fg_color=SURFACE2,
                                        border_color=LINE2, border_width=BORDER_W, text_color=PAPER,
                                        corner_radius=RAD_CTRL, wrap="word")
        self.pb_reglas.pack(fill="x", padx=SP_MD)
        bar = ctk.CTkFrame(sc, fg_color="transparent"); bar.pack(fill="x", padx=SP_MD, pady=SP_MD)
        btn_primary(bar, "Guardar", self._pb_guardar, width=110).pack(side="left")
        self.pb_btn_borrar = btn_ghost(bar, "Borrar", self._pb_borrar, width=100, text_color=NEG_TXT)
        self.pb_btn_borrar.pack(side="left", padx=SP_SM)
        self.pb_msg = ctk.CTkLabel(bar, text="", font=(FONT_MAIN, 11), text_color=MUTED)
        self.pb_msg.pack(side="left", padx=SP_SM)
        self.pb_stats = ctk.CTkFrame(sc, fg_color="transparent")
        self.pb_stats.pack(fill="x", padx=SP_MD, pady=(SP_SM, SP_MD))

    def _pb_datos(self):
        """[{nombre, descripcion, reglas, guardado, n, neto, wr}] de playbooks + tipos usados."""
        pbs = {p["nombre"]: p for p in db_playbooks()}
        ops = {}
        for o in db_all():
            if o.get("tipo") and o.get("profit") is not None:
                ops.setdefault(o["tipo"], []).append(o["profit"])
        nombres = set(pbs) | set(ops)
        out = []
        for n in nombres:
            ps = ops.get(n, [])
            p = pbs.get(n, {})
            out.append(dict(nombre=n, descripcion=p.get("descripcion") or "", reglas=p.get("reglas") or "",
                            guardado=n in pbs, n=len(ps), neto=sum(ps),
                            wr=(100 * sum(1 for x in ps if x > 0) / len(ps)) if ps else 0))
        out.sort(key=lambda d: (-d["n"], d["nombre"].lower()))
        return out

    def render_playbooks(self):
        for w in self.pb_lista.winfo_children():
            w.destroy()
        datos = self._pb_datos()
        if not datos:
            ctk.CTkLabel(self.pb_lista, text="Todavía no hay setups.\nCreá el primero con «+ Nuevo».",
                         font=(FONT_MAIN, 12), text_color=MUTED, justify="center").pack(pady=SP_XL)
        for d in datos:
            sel = d["nombre"] == self.pb_sel
            card = ctk.CTkFrame(self.pb_lista, fg_color=NAV_SEL if sel else SURFACE2, corner_radius=RAD_CTRL,
                                border_color=BLUE_HI if sel else LINE, border_width=BORDER_W, cursor="hand2")
            card.pack(fill="x", padx=SP_XS, pady=3)
            a = ctk.CTkFrame(card, fg_color="transparent"); a.pack(fill="x", padx=SP_MD, pady=(SP_SM, 0))
            ctk.CTkLabel(a, text=d["nombre"], font=(FONT_MAIN, 13), text_color=PAPER, anchor="w").pack(side="left")
            if d["n"]:
                ctk.CTkLabel(a, text=f"{d['neto']:+,.0f}", font=(FONT_SERIF, 18),
                             text_color=POS_TXT if d["neto"] >= 0 else NEG_TXT).pack(side="right")
            sub = (f"{d['n']} trades · {d['wr']:.0f}% win" if d["n"] else "sin trades") + \
                  ("" if d["guardado"] else "  ·  sin reglas escritas")
            b = ctk.CTkLabel(card, text=sub, font=(FONT_MONO, 10), text_color=MUTED, anchor="w")
            b.pack(fill="x", padx=SP_MD, pady=(0, SP_SM))
            for w in (card, a, b) + tuple(a.winfo_children()):
                w.bind("<Button-1>", lambda e, dd=d: self._pb_elegir(dd))
        sel = next((d for d in datos if d["nombre"] == self.pb_sel), None)
        self._pb_cargar_editor(sel)

    def _pb_elegir(self, d):
        self.pb_sel = d["nombre"]
        self.render_playbooks()

    def _pb_nuevo(self):
        self.pb_sel = None
        self.render_playbooks()
        self.pb_nombre.focus_set()

    def _pb_cargar_editor(self, d):
        self.pb_nombre.delete(0, "end"); self.pb_desc.delete(0, "end")
        self.pb_reglas.delete("1.0", "end")
        self.pb_msg.configure(text="")
        for w in self.pb_stats.winfo_children():
            w.destroy()
        if not d:
            self.pb_btn_borrar.configure(state="disabled")
            return
        self.pb_nombre.insert(0, d["nombre"]); self.pb_desc.insert(0, d["descripcion"])
        self.pb_reglas.insert("1.0", d["reglas"])
        self.pb_btn_borrar.configure(state="normal" if d["guardado"] else "disabled")
        ops = [o for o in db_all() if o.get("tipo") == d["nombre"] and o.get("profit") is not None]
        r = A.resumen(ops)
        if not r:
            return
        ctk.CTkLabel(self.pb_stats, text="CÓMO RINDE", font=(FONT_MAIN, 10), text_color=MUTED).pack(anchor="w")
        fila = ctk.CTkFrame(self.pb_stats, fg_color="transparent"); fila.pack(fill="x", pady=SP_XS)
        pf = "—" if r["profit_factor"] is None else f"{r['profit_factor']:.2f}"
        for i, (lab, val, col) in enumerate([
                ("Neto", f"{r['neto']:+,.0f}", POS_TXT if r["neto"] >= 0 else NEG_TXT),
                ("Win rate", f"{r['wr']:.0f}%", PAPER), ("Profit factor", pf, PAPER),
                ("Expectativa", f"{r['expectativa']:+.1f}", POS_TXT if r["expectativa"] >= 0 else NEG_TXT)]):
            fila.grid_columnconfigure(i, weight=1, uniform="pbs")
            c = ctk.CTkFrame(fila, fg_color=SURFACE2, corner_radius=RAD_CTRL)
            c.grid(row=0, column=i, sticky="nsew", padx=2)
            ctk.CTkLabel(c, text=lab.upper(), font=(FONT_MAIN, 9), text_color=MUTED).pack(anchor="w", padx=SP_MD, pady=(SP_SM, 0))
            ctk.CTkLabel(c, text=val, font=(FONT_SERIF, 22), text_color=col).pack(anchor="w", padx=SP_MD, pady=(0, SP_SM))
        if r["n"] < 20:
            ctk.CTkLabel(self.pb_stats, text=f"Ojo: son {r['n']} trades, todavía es muestra chica.",
                         font=(FONT_MAIN, 11), text_color=MUTED2).pack(anchor="w")

    def _pb_guardar(self):
        nombre = self.pb_nombre.get().strip()
        if not nombre:
            self.pb_msg.configure(text="Poné un nombre.", text_color=NEG_TXT); return
        try:
            db_playbook_save(nombre, self.pb_desc.get().strip(),
                             self.pb_reglas.get("1.0", "end").strip(), viejo_nombre=self.pb_sel)
        except Exception as e:
            self.pb_msg.configure(text=f"No se pudo guardar: {e}", text_color=NEG_TXT); return
        self.pb_sel = nombre
        self._table_dirty = True
        self.render_playbooks()
        self.pb_msg.configure(text="guardado ✓", text_color=MUTED)

    def _pb_borrar(self):
        if self.pb_sel and messagebox.askyesno(
                "Borrar playbook", f"¿Borrar las reglas de «{self.pb_sel}»?\nLas operaciones conservan su tipo."):
            db_playbook_delete(self.pb_sel)
            self.pb_sel = None
            self.render_playbooks()

"""Pantalla Portfolio como Mixin de App: todas las cuentas juntas, en secciones (capital, cuentas,
salud, cuándo, día a día). Respeta el rango de fechas global y NO el selector de cuenta."""
from datetime import datetime
import tkinter as tk
import customtkinter as ctk

from registro import portfolio as PF
from registro.db import ESTADOS_CUENTA, db_all, db_cuentas, get_cuenta_global
from registro.ui import vivo
from registro.ui.tema import (
    BLUE_HI, BORDER_W, FONT_MAIN, FONT_MONO, FONT_SERIF, LINE, MUTED, MUTED2, NEG, NEG_TXT, PAPER,
    POS, POS_TXT, RAD_CARD, RAD_CTRL, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SURFACE, SURFACE2, TRACK)

vivo.registrar(globals())

_DIAS_LARGOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def _usd(v, signo=False):
    if v is None:
        return "—"
    return f"{v:+,.0f}" if signo else f"${v:,.0f}"


def _pct(v, signo=True):
    return "—" if v is None else (f"{v:+.1f}%" if signo else f"{v:.1f}%")


def _color(v):
    return POS_TXT if (v or 0) >= 0 else NEG_TXT


class PortfolioMixin:
    def _build_portfolio(self):
        self._barra_filtros(self.tab_portfolio, "pff", self.render_portfolio).pack(fill="x", pady=(SP_SM, 0))
        self.pf_body = ctk.CTkScrollableFrame(self.tab_portfolio, fg_color="transparent")
        self.pf_body.pack(fill="both", expand=True)

    # ---- piezas ----
    def _pf_seccion(self, num, titulo, sub):
        cab = ctk.CTkFrame(self.pf_body, fg_color="transparent")
        cab.pack(fill="x", pady=(SP_XL, SP_SM))
        ctk.CTkLabel(cab, text=num, font=(FONT_MONO, 11), text_color=MUTED2, width=30, anchor="w").pack(side="left", anchor="n", pady=(6, 0))
        col = ctk.CTkFrame(cab, fg_color="transparent"); col.pack(side="left")
        ctk.CTkLabel(col, text=titulo, font=(FONT_SERIF, 22), text_color=PAPER, anchor="w").pack(anchor="w")
        ctk.CTkLabel(col, text=sub, font=(FONT_MAIN, 12), text_color=MUTED, anchor="w").pack(anchor="w")
        card = ctk.CTkFrame(self.pf_body, fg_color=SURFACE, corner_radius=RAD_CARD)
        card.pack(fill="x")
        return card

    def _pf_cifra(self, parent, rotulo, valor, color=PAPER, grande=False):
        ctk.CTkLabel(parent, text=rotulo.upper(), font=(FONT_MAIN, 9), text_color=MUTED, anchor="w").pack(anchor="w")
        ctk.CTkLabel(parent, text=valor, font=(FONT_SERIF, 40 if grande else 22), text_color=color,
                     anchor="w").pack(anchor="w", pady=(0, SP_SM))

    def _pf_curva(self, cv, serie, base):
        """Curva diaria en un tk.Canvas. `base` = capital inicial (línea punteada) o None."""
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 80 or h < 60 or not serie:
            return
        izq, der, arr, aba = 64, 12, 10, 22
        vals = [v for _f, v in serie] + ([base] if base else [])
        lo, hi = min(vals), max(vals)
        if hi - lo < 1e-9:
            lo, hi = lo - 1, hi + 1
        pad = (hi - lo) * 0.08
        lo, hi = lo - pad, hi + pad
        X = lambda i: izq + (w - izq - der) * (i / max(1, len(serie) - 1))
        Y = lambda v: arr + (h - arr - aba) * (1 - (v - lo) / (hi - lo))
        for k in range(4):
            v = lo + (hi - lo) * k / 3
            cv.create_line(izq, Y(v), w - der, Y(v), fill=LINE)
            cv.create_text(izq - 8, Y(v), text=f"{v:,.0f}", anchor="e", fill=MUTED, font=(FONT_MONO, 9))
        if base:
            cv.create_line(izq, Y(base), w - der, Y(base), fill=MUTED2, dash=(4, 4))
        pts = [c for i, (_f, v) in enumerate(serie) for c in (X(i), Y(v))]
        if len(serie) == 1:
            cv.create_oval(pts[0] - 3, pts[1] - 3, pts[0] + 3, pts[1] + 3, fill=BLUE_HI, outline=BLUE_HI)
        else:
            cv.create_line(*pts, fill=BLUE_HI, width=2, smooth=False)
        cv.create_text(izq, h - 8, text=serie[0][0], anchor="w", fill=MUTED, font=(FONT_MONO, 9))
        cv.create_text(w - der, h - 8, text=serie[-1][0], anchor="e", fill=MUTED, font=(FONT_MONO, 9))

    def _pf_nota(self, cv, nota):
        cv.delete("all")
        cv.create_oval(10, 10, 130, 130, outline=TRACK, width=10)
        if nota:
            cv.create_arc(10, 10, 130, 130, start=90, extent=-3.6 * nota, style="arc", outline=BLUE_HI, width=10)
        cv.create_text(70, 62, text="—" if nota is None else str(nota), fill=PAPER, font=(FONT_SERIF, 34))
        cv.create_text(70, 92, text="/ 100", fill=MUTED, font=(FONT_MAIN, 11))

    # ---- pantalla ----
    def render_portfolio(self):
        for w in self.pf_body.winfo_children():
            w.destroy()
        rows = db_all(cuenta=False)          # todas las cuentas, con el período global
        todas = db_cuentas()
        self._refrescar_filtros("pff", todas)
        cuentas = self._filtros_cuentas("pff", todas)
        if len(cuentas) != len(todas):       # filtro activo: solo las cuentas elegidas
            claves = {(c.get('empresa') or '', c.get('cuenta') or '') for c in cuentas}
            rows = [o for o in rows if PF._clave_op(o) in claves]
        r = PF.calcular(rows, cuentas)
        if get_cuenta_global():
            ctk.CTkLabel(self.pf_body, text="Acá se ven todas tus cuentas juntas: el selector de cuenta no aplica.",
                         font=(FONT_MAIN, 11), text_color=MUTED2, anchor="w").pack(fill="x", pady=(SP_SM, 0))
        if todas and not cuentas:
            ctk.CTkLabel(self.pf_body, text="Ninguna cuenta coincide con el filtro.",
                         font=(FONT_MAIN, 13), text_color=MUTED, justify="center").pack(pady=SP_XL * 2)
            return
        if not r["n"] and not r["cuentas"]:
            ctk.CTkLabel(self.pf_body, text="Todavía no hay operaciones ni cuentas.\nImportá trades o cargá una cuenta en Cuentas.",
                         font=(FONT_MAIN, 13), text_color=MUTED, justify="center").pack(pady=SP_XL * 2)
            return
        self._pf_capital(r)
        self._pf_cuentas(r)
        self._pf_salud(r)
        self._pf_cuando(r)
        self._pf_dias(r)

    def _pf_capital(self, r):
        card = self._pf_seccion("01", "Tu capital", "Cuánto tenés entre todas tus cuentas y cómo llegó hasta acá.")
        card.grid_columnconfigure(1, weight=1)
        cap_base = r["capital_inicial"]          # el Portfolio no usa el selector: la base es la de todas las cuentas
        izq = ctk.CTkFrame(card, fg_color="transparent"); izq.grid(row=0, column=0, sticky="nsw", padx=SP_XL, pady=SP_XL)
        if r["balance"] is not None:
            self._pf_cifra(izq, "Balance total", _usd(r["balance"]), grande=True)
            sub = f"{_usd(r['neto'], True)}  ({_pct(r['retorno_pct'])})   ·   Inicial: {_usd(r['capital_inicial'])}"
            if r["con_capital"] < r["n_cuentas"]:
                sub += f"\nSolo cuentas con capital inicial ({r['con_capital']} de {r['n_cuentas']})."
        else:
            self._pf_cifra(izq, "P&L total", self._m(r["neto"], base=cap_base), color=_color(r["neto"]), grande=True)
            sub = "Cargá el capital inicial de tus cuentas (Cuentas) para ver balance y %."
        ctk.CTkLabel(izq, text=sub, font=(FONT_MAIN, 11), text_color=_color(r["neto"]) if r["balance"] is not None else MUTED,
                     justify="left", anchor="w").pack(anchor="w", pady=(0, SP_LG))
        fila = ctk.CTkFrame(izq, fg_color="transparent"); fila.pack(anchor="w")
        for rot, v in (("Hoy", r["hoy"]), ("Esta semana", r["semana"]), ("Este mes", r["mes"])):
            c = ctk.CTkFrame(fila, fg_color="transparent"); c.pack(side="left", padx=(0, SP_XL))
            self._pf_cifra(c, rot, self._m(v, base=cap_base), color=_color(v) if v else PAPER)
        der = ctk.CTkFrame(card, fg_color="transparent"); der.grid(row=0, column=1, sticky="nsew", padx=(0, SP_XL), pady=SP_XL)
        ctk.CTkLabel(der, text="CURVA DE CAPITAL" + ("  ·  la línea punteada es tu capital inicial" if r["capital_inicial"] else "  ·  P&L acumulado"),
                     font=(FONT_MAIN, 9), text_color=MUTED, anchor="w").pack(anchor="w")
        cv = tk.Canvas(der, height=190, bg=SURFACE, highlightthickness=0)
        cv.pack(fill="x", pady=(SP_SM, 0))
        cv.bind("<Configure>", lambda e: self._pf_curva(cv, r["curva"], r["capital_inicial"]))

    def _pf_cuentas(self, r):
        pos = sum(1 for c in r["cuentas"] if c["pnl"] > 0)
        card = self._pf_seccion("02", "Tus cuentas", f"{pos} de {r['n_cuentas']} en positivo. Dónde está tu plata y qué aporta cada cuenta.")
        tabla = ctk.CTkFrame(card, fg_color="transparent"); tabla.pack(fill="x", padx=SP_LG, pady=SP_LG)
        tabla.grid_columnconfigure(0, weight=3); tabla.grid_columnconfigure(3, weight=3)
        for i, t in enumerate(("CUENTA", "BALANCE", "PESO", "APORTE AL P&L", "WIN RATE", "OPS.")):
            ctk.CTkLabel(tabla, text=t, font=(FONT_MAIN, 9), text_color=MUTED2, anchor="w" if i in (0, 3) else "e").grid(
                row=0, column=i, sticky="ew", padx=SP_SM, pady=(0, SP_SM))
        mx = max((abs(c["pnl"]) for c in r["cuentas"]), default=0) or 1
        for i, c in enumerate(r["cuentas"], start=1):
            nombre = ctk.CTkFrame(tabla, fg_color="transparent"); nombre.grid(row=i, column=0, sticky="ew", padx=SP_SM, pady=3)
            ctk.CTkLabel(nombre, text=c["titulo"], font=(FONT_MAIN, 13), text_color=PAPER, anchor="w").pack(side="left")
            if c["estado"]:
                ctk.CTkLabel(nombre, text=ESTADOS_CUENTA.get(c["estado"], c["estado"]).upper(), font=(FONT_MAIN, 9),
                             text_color=BLUE_HI).pack(side="left", padx=SP_SM)
            if c["mejor"]:
                ctk.CTkLabel(nombre, text="MEJOR", font=(FONT_MAIN, 9), text_color=POS_TXT).pack(side="left")
            ctk.CTkLabel(tabla, text=_usd(c["balance"]), font=(FONT_MONO, 12), text_color=PAPER, anchor="e").grid(row=i, column=1, sticky="e", padx=SP_SM)
            ctk.CTkLabel(tabla, text="—" if c["peso"] is None else f"{c['peso']:.1f}%", font=(FONT_MONO, 12), text_color=MUTED, anchor="e").grid(row=i, column=2, sticky="e", padx=SP_SM)
            aporte = ctk.CTkFrame(tabla, fg_color="transparent"); aporte.grid(row=i, column=3, sticky="ew", padx=SP_SM)
            ctk.CTkLabel(aporte, text=self._m(c["pnl"], base=c["capital"]) if c["n"] else "—", font=(FONT_MONO, 12), width=70, anchor="e",
                         text_color=_color(c["pnl"]) if c["n"] else MUTED).pack(side="right")
            pista = ctk.CTkFrame(aporte, fg_color=TRACK, height=8, corner_radius=4); pista.pack(side="left", fill="x", expand=True, padx=(0, SP_SM))
            pista.pack_propagate(False)
            if c["n"]:
                ctk.CTkFrame(pista, fg_color=POS if c["pnl"] >= 0 else NEG, corner_radius=4).place(
                    relx=0, rely=0, relwidth=max(abs(c["pnl"]) / mx, 0.03), relheight=1)
            ctk.CTkLabel(tabla, text=f"{c['wr']:.0f}%" if c["n"] else "—", font=(FONT_MONO, 12), text_color=PAPER, anchor="e").grid(row=i, column=4, sticky="e", padx=SP_SM)
            ctk.CTkLabel(tabla, text=str(c["n"]), font=(FONT_MONO, 12), text_color=MUTED, anchor="e").grid(row=i, column=5, sticky="e", padx=SP_SM)

    def _pf_salud(self, r):
        card = self._pf_seccion("03", "Salud", "Una nota calculada con tus operaciones, con cada fórmula a la vista.")
        card.grid_columnconfigure(1, weight=1)
        s = r["salud"]
        cv = tk.Canvas(card, width=140, height=140, bg=SURFACE, highlightthickness=0)
        cv.grid(row=0, column=0, padx=SP_XL, pady=SP_XL, sticky="n")
        self._pf_nota(cv, s["nota"])
        medio = ctk.CTkFrame(card, fg_color="transparent"); medio.grid(row=0, column=1, sticky="nsew", pady=SP_XL)
        medio.grid_columnconfigure((0, 1), weight=1, uniform="sal")
        piezas = [("Consistencia", s["consistencia"], "Días ganadores ÷ días operados"),
                  ("Gestión de riesgo", s["riesgo"], "100 − 5 por cada 1% de drawdown sobre el capital inicial"),
                  ("Diversificación", s["diversificacion"], "0 con todo en una cuenta, 100 con el capital repartido por igual"),
                  ("Rentabilidad", s["rentabilidad"], "Profit factor × 50, con máximo 100")]
        for i, (nom, v, formula) in enumerate(piezas):
            c = ctk.CTkFrame(medio, fg_color="transparent"); c.grid(row=i // 2, column=i % 2, sticky="ew", padx=SP_MD, pady=SP_SM)
            fila = ctk.CTkFrame(c, fg_color="transparent"); fila.pack(fill="x")
            ctk.CTkLabel(fila, text=nom, font=(FONT_MAIN, 13), text_color=PAPER).pack(side="left")
            ctk.CTkLabel(fila, text="—" if v is None else f"{v:.0f}", font=(FONT_MONO, 13), text_color=PAPER if v is not None else MUTED).pack(side="right")
            barra = ctk.CTkProgressBar(c, height=8, fg_color=TRACK, progress_color=BLUE_HI)
            barra.pack(fill="x", pady=(SP_XS, SP_XS)); barra.set(0 if v is None else max(0, min(1, v / 100)))
            txt = formula if v is not None or nom != "Gestión de riesgo" else "Necesita el capital inicial de tus cuentas"
            ctk.CTkLabel(c, text=txt, font=(FONT_MAIN, 10), text_color=MUTED2, anchor="w", justify="left", wraplength=330).pack(anchor="w")
        der = ctk.CTkFrame(card, fg_color=SURFACE2, corner_radius=RAD_CTRL); der.grid(row=0, column=2, sticky="ns", padx=SP_XL, pady=SP_XL)
        res, cnt = r["resumen"], r["conteo"]
        ctk.CTkLabel(der, text="TUS OPERACIONES", font=(FONT_MAIN, 9), text_color=MUTED, anchor="w").pack(anchor="w", padx=SP_LG, pady=(SP_LG, 0))
        if res:
            ctk.CTkLabel(der, text=f"Win rate {res['wr']:.1f}%   ·   {cnt['gan']} ganadoras · {cnt['tab']} en tablas · {cnt['per']} perdedoras",
                         font=(FONT_MAIN, 11), text_color=PAPER, anchor="w").pack(anchor="w", padx=SP_LG, pady=(SP_XS, SP_SM))
        for nom, val, ayuda in (
                ("Drawdown máximo", self._m(-r["dd_max"], base=r["capital_inicial"]) if r["dd_max"] else "—", "La peor caída desde un pico de tu curva"),
                ("Ratio Sharpe", "—" if r["sharpe"] is None else f"{r['sharpe']:.2f}", "Rentabilidad diaria ajustada por riesgo, anualizada"),
                ("Profit factor", "—" if not res or res["profit_factor"] is None else f"{res['profit_factor']:.2f}", "Ganancias brutas ÷ pérdidas brutas"),
                ("Riesgo / beneficio", "—" if not res or res["payoff"] is None else f"{res['payoff']:.2f}", "Ganancia media ÷ pérdida media")):
            f = ctk.CTkFrame(der, fg_color="transparent"); f.pack(fill="x", padx=SP_LG, pady=(0, SP_SM))
            fila = ctk.CTkFrame(f, fg_color="transparent"); fila.pack(fill="x")
            ctk.CTkLabel(fila, text=nom, font=(FONT_MAIN, 12), text_color=PAPER).pack(side="left")
            ctk.CTkLabel(fila, text=val, font=(FONT_MONO, 13), text_color=PAPER).pack(side="right", padx=(SP_LG, 0))
            ctk.CTkLabel(f, text=ayuda, font=(FONT_MAIN, 10), text_color=MUTED2, anchor="w").pack(anchor="w")

    def _pf_cuando(self, r):
        card = self._pf_seccion("04", "Cuándo", "Qué días y qué meses te van mejor.")
        card.grid_columnconfigure((0, 1), weight=1, uniform="cua")
        izq = ctk.CTkFrame(card, fg_color="transparent"); izq.grid(row=0, column=0, sticky="nsew", padx=SP_XL, pady=SP_LG)
        ctk.CTkLabel(izq, text="RENDIMIENTO POR DÍA  ·  P&L promedio de todas tus cuentas juntas", font=(FONT_MAIN, 9), text_color=MUTED).pack(anchor="w", pady=(0, SP_SM))
        mx = max((abs(d["prom"]) for d in r["por_dia_semana"] if d["prom"] is not None), default=0) or 1
        for i, d in enumerate(r["por_dia_semana"]):
            p = d["prom"]
            self._bar(izq, _DIAS_LARGOS[i], 0 if p is None else abs(p) / mx, POS if (p or 0) >= 0 else NEG,
                      "", "—" if p is None else self._m(p, base=r["capital_inicial"]), val_color=MUTED if p is None else _color(p))
        der = ctk.CTkFrame(card, fg_color="transparent"); der.grid(row=0, column=1, sticky="nsew", padx=SP_XL, pady=SP_LG)
        ctk.CTkLabel(der, text="RENDIMIENTO MENSUAL  ·  últimos 12 meses" + ("" if r["capital_inicial"] else "  ·  en USD"),
                     font=(FONT_MAIN, 9), text_color=MUTED).pack(anchor="w", pady=(0, SP_SM))
        if not r["por_mes"]:
            ctk.CTkLabel(der, text="Sin datos todavía.", font=(FONT_MAIN, 12), text_color=MUTED).pack(anchor="w")
        for m in reversed(r["por_mes"]):
            f = ctk.CTkFrame(der, fg_color="transparent"); f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=m["mes"], font=(FONT_MONO, 12), text_color=MUTED, width=80, anchor="w").pack(side="left")
            ctk.CTkLabel(f, text=_usd(m["pnl"], True), font=(FONT_MONO, 12), text_color=_color(m["pnl"]), width=90, anchor="e").pack(side="left")
            if m["pct"] is not None:
                ctk.CTkLabel(f, text=_pct(m["pct"]), font=(FONT_MONO, 12), text_color=_color(m["pct"]), width=70, anchor="e").pack(side="left")

    def _pf_dias(self, r):
        card = self._pf_seccion("05", "Día a día", "Los últimos días operados y qué hizo cada cuenta.")
        caja = ctk.CTkFrame(card, fg_color="transparent"); caja.pack(fill="x", padx=SP_XL, pady=SP_LG)
        if not r["dia_a_dia"]:
            ctk.CTkLabel(caja, text="Sin operaciones en el período.", font=(FONT_MAIN, 12), text_color=MUTED).pack(anchor="w")
        for d in r["dia_a_dia"]:
            f = ctk.CTkFrame(caja, fg_color=SURFACE2, corner_radius=RAD_CTRL, border_color=LINE, border_width=BORDER_W)
            f.pack(fill="x", pady=3)
            a = ctk.CTkFrame(f, fg_color="transparent"); a.pack(fill="x", padx=SP_MD, pady=(SP_SM, 0))
            try:
                dia = _DIAS_LARGOS[datetime.strptime(d["fecha"], "%Y-%m-%d").weekday()]
            except ValueError:
                dia = ""
            ctk.CTkLabel(a, text=f"{dia} {d['fecha']}", font=(FONT_MONO, 12), text_color=PAPER).pack(side="left")
            ctk.CTkLabel(a, text=f"{d['n']} trades", font=(FONT_MONO, 10), text_color=MUTED).pack(side="left", padx=SP_MD)
            ctk.CTkLabel(a, text=_usd(d["neto"], True), font=(FONT_SERIF, 18), text_color=_color(d["neto"])).pack(side="right")
            det = "   ·   ".join(f"{n} {_usd(v, True)}" for n, v, _k in d["por_cuenta"])
            ctk.CTkLabel(f, text=det, font=(FONT_MONO, 10), text_color=MUTED, anchor="w", justify="left", wraplength=900).pack(
                fill="x", padx=SP_MD, pady=(0, SP_SM))

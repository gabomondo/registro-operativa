"""Calculadora de riesgo: cuántos contratos / lotes entran en el riesgo aceptado."""

import customtkinter as ctk
from registro.ui import vivo
from registro.ui.estado import save_ui_prefs
from registro.ui.tema import BLUE, BLUE_HI, CAUTION, FONT_MAIN, FONT_MONO, FONT_SERIF, HOVER, INK, LINE2, MUTED, MUTED2, PAPER, POS_TXT, RAD_CARD, SEG_HI, SEG_SEL, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SURFACE
from registro.ui.ventanas import centrar_dialogo
from registro.ui.widgets import btn_ghost, styled_combo, styled_entry

vivo.registrar(globals())


class RiesgoDialog(ctk.CTkToplevel):
    """Calculadora de riesgo: cuántos contratos / lotes entran en el riesgo que aceptás."""
    MODOS = ["Futuros", "Forex", "Otro CFD"]

    def __init__(self, app):
        super().__init__(app)
        from registro import riesgo as RK
        self.RK = RK
        self.app = app
        self.title("Calculadora de riesgo")
        f = app.factor
        centrar_dialogo(self, app, int(820 * f), int(740 * f), int(700 * f), int(560 * f))
        self.configure(fg_color=INK)
        self.transient(app)
        self.pr = dict(app._ui_prefs.get("riesgo", {}))
        self.otros = list(app._ui_prefs.get("riesgo_otros", []))
        self._etq = {}
        for g, simbs in RK.agrupados().items():
            for s in simbs:
                self._etq[f"{s} — {RK.FUTUROS[s][0]}"] = s
        self._build()
        self.bind("<Escape>", lambda e: self.destroy())
        self._modo()
        self.after(80, self._foco)

    def _foco(self):
        try:
            self.grab_set()
            self.focus_set()
        except Exception:
            pass

    def _lab(self, parent, t):
        return ctk.CTkLabel(parent, text=t, font=(FONT_MAIN, 9), text_color=MUTED2, anchor="w")

    def _campo(self, parent, titulo, ancho, valor="", ph=""):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        self._lab(fr, titulo).pack(anchor="w")
        e = styled_entry(fr, width=ancho, placeholder=ph)
        if valor not in (None, ""):
            e.insert(0, str(valor))
        e.pack(anchor="w", pady=(SP_XS, 0))
        e.bind("<KeyRelease>", lambda ev: self._calc())
        return fr, e

    def _build(self):
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(side="bottom", fill="x", padx=SP_XL, pady=SP_LG)
        ctk.CTkLabel(pie, text="Cálculo orientativo, cuenta en USD. Confirmá el valor por punto con tu broker.",
                     font=(FONT_MAIN, 11), text_color=MUTED2, anchor="w").pack(side="left")
        btn_ghost(pie, "Cerrar", self.destroy, width=100, height=34).pack(side="right")

        ctk.CTkLabel(self, text="Calculadora de riesgo", font=(FONT_SERIF, 26),
                     text_color=PAPER).pack(anchor="w", padx=SP_XL, pady=(SP_LG, 0))
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=SP_MD)
        pr = self.pr

        self._lab(body, "INSTRUMENTO").pack(anchor="w", padx=SP_MD)
        self.seg_modo = ctk.CTkSegmentedButton(
            body, values=self.MODOS, height=32, font=(FONT_MAIN, 12), fg_color=SURFACE,
            selected_color=SEG_SEL, selected_hover_color=SEG_HI, unselected_color=SURFACE,
            unselected_hover_color=HOVER, text_color=PAPER, command=lambda v: self._modo())
        m0 = pr.get("modo", "Futuros")
        self.seg_modo.set(m0 if m0 in self.MODOS else "Futuros")
        self.seg_modo.pack(anchor="w", padx=SP_MD, pady=(SP_XS, SP_SM))

        # --- específicos de cada modo (se muestran/ocultan) ---
        self.fr_modo = ctk.CTkFrame(body, fg_color="transparent")
        self.fr_modo.pack(fill="x", padx=SP_MD)
        # futuros
        self.fr_fut = ctk.CTkFrame(self.fr_modo, fg_color="transparent")
        self._lab(self.fr_fut, "ACTIVO").pack(anchor="w")
        etqs = list(self._etq)
        self.cb_fut = styled_combo(self.fr_fut, etqs, width=330)
        self.cb_fut.set(next((e for e in etqs if self._etq[e] == pr.get("fut", "NQ")), etqs[0]))
        self.cb_fut.configure(command=lambda v: self._calc())
        self.cb_fut.pack(anchor="w", pady=(SP_XS, 0))
        self.lbl_fut = ctk.CTkLabel(self.fr_fut, text="", font=(FONT_MONO, 11), text_color=MUTED, anchor="w")
        self.lbl_fut.pack(anchor="w", pady=(SP_XS, 0))
        self.seg_unidad = ctk.CTkSegmentedButton(
            self.fr_fut, values=["Stop en puntos", "Stop en ticks"], height=28, font=(FONT_MAIN, 11),
            fg_color=SURFACE, selected_color=SEG_SEL, selected_hover_color=SEG_HI,
            unselected_color=SURFACE, unselected_hover_color=HOVER, text_color=PAPER,
            command=lambda v: self._calc())
        self.seg_unidad.set("Stop en puntos")
        self.seg_unidad.pack(anchor="w", pady=(SP_SM, 0))
        # forex
        self.fr_fx = ctk.CTkFrame(self.fr_modo, fg_color="transparent")
        f1 = ctk.CTkFrame(self.fr_fx, fg_color="transparent"); f1.pack(anchor="w")
        a = ctk.CTkFrame(f1, fg_color="transparent"); a.pack(side="left", padx=(0, SP_MD))
        self._lab(a, "PAR").pack(anchor="w")
        self.cb_par = styled_combo(a, self.RK.PARES_FOREX, width=130, mono=True, default=pr.get("par", "EURUSD"))
        self.cb_par.configure(command=lambda v: self._calc())
        self.cb_par.pack(anchor="w", pady=(SP_XS, 0))
        self.cb_par._entry.bind("<KeyRelease>", lambda ev: self._calc())
        fp, self.en_precio = self._campo(f1, "PRECIO ACTUAL DEL PAR", 150, pr.get("precio", ""), "ej. 150.25")
        fp.pack(side="left", padx=(0, SP_MD))
        self.fr_qusd, self.en_qusd = self._campo(f1, "USD POR 1 MONEDA COTIZADA", 170, pr.get("qusd", ""), "ej. 0.0067")
        self.lbl_fx = ctk.CTkLabel(self.fr_fx, text="", font=(FONT_MONO, 11), text_color=MUTED,
                                   anchor="w", justify="left", wraplength=650)
        self.lbl_fx.pack(anchor="w", pady=(SP_XS, 0))
        # otro CFD
        self.fr_ot = ctk.CTkFrame(self.fr_modo, fg_color="transparent")
        o1 = ctk.CTkFrame(self.fr_ot, fg_color="transparent"); o1.pack(anchor="w")
        a = ctk.CTkFrame(o1, fg_color="transparent"); a.pack(side="left", padx=(0, SP_MD))
        self._lab(a, "GUARDADOS").pack(anchor="w")
        self.cb_ot = styled_combo(a, [o["nombre"] for o in self.otros] or ["(ninguno)"], width=200)
        self.cb_ot.configure(command=lambda v: self._elegir_otro(v))
        self.cb_ot.pack(anchor="w", pady=(SP_XS, 0))
        fn, self.en_onom = self._campo(o1, "NOMBRE", 150, "", "ej. XAUUSD")
        fn.pack(side="left", padx=(0, SP_MD))
        fv, self.en_oval = self._campo(o1, "USD POR PUNTO POR LOTE", 180, "", "ej. 100")
        fv.pack(side="left")
        o2 = ctk.CTkFrame(self.fr_ot, fg_color="transparent"); o2.pack(anchor="w", pady=(SP_SM, 0))
        btn_ghost(o2, "Guardar este instrumento", self._guardar_otro, width=190, height=30).pack(side="left")
        btn_ghost(o2, "Borrar guardado", self._borrar_otro, width=140, height=30).pack(side="left", padx=SP_SM)
        ctk.CTkLabel(
            self.fr_ot, text="El valor por punto lo encontrás en la especificación del contrato de tu "
                             "plataforma (MT4/MT5: clic derecho en Observación del mercado → Especificación; "
                             "cTrader: ficha del símbolo). Es por 1 lote y por 1 punto de precio.",
            font=(FONT_MAIN, 11), text_color=MUTED, wraplength=650, justify="left", anchor="w").pack(
                anchor="w", pady=(SP_XS, 0))

        # --- comunes ---
        com = ctk.CTkFrame(body, fg_color="transparent")
        com.pack(fill="x", padx=SP_MD, pady=(SP_MD, 0))
        c1 = ctk.CTkFrame(com, fg_color="transparent"); c1.pack(anchor="w")
        fr, self.en_riesgo = self._campo(c1, "RIESGO MÁXIMO (USD)", 150, pr.get("riesgo", ""), "ej. 500")
        fr.pack(side="left", padx=(0, SP_MD))
        self.fr_stop, self.en_stop = self._campo(c1, "STOP LOSS", 130, pr.get("stop", ""), "")
        self.fr_stop.pack(side="left", padx=(0, SP_MD))
        self.lbl_stop = self.fr_stop.winfo_children()[0]
        fr, self.en_target = self._campo(c1, "TARGET (opcional)", 130, pr.get("target", ""), "")
        fr.pack(side="left", padx=(0, SP_MD))
        fr, self.en_dd = self._campo(c1, "DRAWDOWN PERMITIDO (USD, opc.)", 210, pr.get("dd", ""), "ej. 2000")
        fr.pack(side="left")
        self.chk_web = ctk.CTkCheckBox(
            com, text="Redondear como en gabomondo.com (sube si la fracción es 0,7 o más)",
            font=(FONT_MAIN, 12), text_color=PAPER, fg_color=BLUE, hover_color=BLUE_HI,
            border_color=LINE2, command=self._calc)
        if pr.get("web"):
            self.chk_web.select()
        self.chk_web.pack(anchor="w", pady=(SP_MD, 0))

        # --- resultado ---
        res = ctk.CTkFrame(body, fg_color=SURFACE, corner_radius=RAD_CARD)
        res.pack(fill="x", padx=SP_MD, pady=(SP_MD, SP_LG))
        self._lab(res, "RESULTADO").pack(anchor="w", padx=SP_LG, pady=(SP_MD, 0))
        self.lbl_cant = ctk.CTkLabel(res, text="—", font=(FONT_SERIF, 44), text_color=PAPER, anchor="w")
        self.lbl_cant.pack(anchor="w", padx=SP_LG)
        self.lbl_det = ctk.CTkLabel(res, text="", font=(FONT_MAIN, 13), text_color=PAPER, anchor="w",
                                    justify="left", wraplength=650)
        self.lbl_det.pack(anchor="w", padx=SP_LG)
        self.lbl_aviso = ctk.CTkLabel(res, text="", font=(FONT_MAIN, 12), text_color=CAUTION, anchor="w",
                                      justify="left", wraplength=650)
        self.lbl_aviso.pack(anchor="w", padx=SP_LG, pady=(SP_XS, 0))
        self.lbl_rr = ctk.CTkLabel(res, text="", font=(FONT_MONO, 12), text_color=MUTED, anchor="w",
                                   justify="left")
        self.lbl_rr.pack(anchor="w", padx=SP_LG, pady=(SP_SM, SP_MD))

    # ---------- modo ----------
    def _modo(self):
        modo = self.seg_modo.get()
        for fr in (self.fr_fut, self.fr_fx, self.fr_ot):
            fr.pack_forget()
        {"Futuros": self.fr_fut, "Forex": self.fr_fx, "Otro CFD": self.fr_ot}[modo].pack(anchor="w")
        self._calc()

    def _num(self, entry):
        t = entry.get().strip().replace(",", ".")
        if not t:
            return None
        try:
            return float(t)
        except ValueError:
            raise ValueError("Revisá los números: usá solo dígitos y punto decimal")

    def _elegir_otro(self, nombre):
        o = next((x for x in self.otros if x["nombre"] == nombre), None)
        if o:
            self.en_onom.delete(0, "end"); self.en_onom.insert(0, o["nombre"])
            self.en_oval.delete(0, "end"); self.en_oval.insert(0, str(o["valor"]))
        self._calc()

    def _guardar_otro(self):
        try:
            nom, val = self.en_onom.get().strip(), self._num(self.en_oval)
        except ValueError:
            return
        if not nom or not val or val <= 0:
            self.lbl_aviso.configure(text="Para guardar, completá nombre y valor por punto.")
            return
        self.otros = [o for o in self.otros if o["nombre"] != nom] + [dict(nombre=nom, valor=val)]
        self.cb_ot.configure(values=[o["nombre"] for o in self.otros])
        self.cb_ot.set(nom)
        self._persistir()
        self.lbl_aviso.configure(text=f"Guardado: {nom}")

    def _borrar_otro(self):
        nom = self.cb_ot.get()
        self.otros = [o for o in self.otros if o["nombre"] != nom]
        self.cb_ot.configure(values=[o["nombre"] for o in self.otros] or ["(ninguno)"])
        self.cb_ot.set(self.otros[0]["nombre"] if self.otros else "(ninguno)")
        self._persistir()
        self._calc()

    def _persistir(self):
        self.pr.update(modo=self.seg_modo.get(), fut=self._etq.get(self.cb_fut.get(), "NQ"),
                       par=self.cb_par.get().strip().upper(), precio=self.en_precio.get().strip(),
                       qusd=self.en_qusd.get().strip(), riesgo=self.en_riesgo.get().strip(),
                       stop=self.en_stop.get().strip(), target=self.en_target.get().strip(),
                       dd=self.en_dd.get().strip(), web=bool(self.chk_web.get()))
        self.app._ui_prefs["riesgo"] = self.pr
        self.app._ui_prefs["riesgo_otros"] = self.otros
        save_ui_prefs(self.app._ui_prefs)

    # ---------- cálculo ----------
    def _limpiar(self, aviso=""):
        self.lbl_cant.configure(text="—", text_color=PAPER)
        self.lbl_det.configure(text="")
        self.lbl_rr.configure(text="")
        self.lbl_aviso.configure(text=aviso)

    def _calc(self):
        RK = self.RK
        modo = self.seg_modo.get()
        paso, sim, cantidad_txt = 1.0, None, "contratos"
        try:
            if modo == "Futuros":
                sim = self._etq.get(self.cb_fut.get(), "NQ")
                _n, _g, vp, tick, vt = RK.FUTUROS[sim]
                self.lbl_fut.configure(text=f"{vp:,.4g} USD por punto · tick {tick:.7g} = {vt:,.3f} USD")
                en_ticks = self.seg_unidad.get().endswith("ticks")
                usd_u = vt if en_ticks else vp
                self.lbl_stop.configure(text="STOP (TICKS)" if en_ticks else "STOP (PUNTOS)")
            elif modo == "Forex":
                par = self.cb_par.get().strip().upper()
                base, quote = RK.partes_par(par)
                cruce = "USD" not in (base, quote)
                if cruce:
                    self.fr_qusd.pack(side="left")
                else:
                    self.fr_qusd.pack_forget()
                usd_u = RK.valor_pip_usd(par, self._num(self.en_precio), self._num(self.en_qusd) if cruce else None)
                self.lbl_fx.configure(text=f"1 pip ({RK.tam_pip(par):g}) = {usd_u:,.3f} USD por lote estándar (100.000)")
                self.lbl_stop.configure(text="STOP (PIPS)")
                paso, cantidad_txt = 0.01, "lotes"
            else:
                usd_u = self._num(self.en_oval)
                self.lbl_stop.configure(text="STOP (PUNTOS)")
                paso, cantidad_txt = 0.01, "lotes"
            r = RK.calcular(self._num(self.en_riesgo), self._num(self.en_stop), usd_u, paso=paso,
                            redondeo="web" if self.chk_web.get() else "abajo",
                            target=self._num(self.en_target), drawdown=self._num(self.en_dd))
        except ValueError as e:
            msg = str(e)
            pend = ("Ingresá" in msg or "Falta" in msg)
            self._limpiar(msg if pend else msg)
            return
        self._persistir()
        dec = 2 if paso < 1 else 0
        if not r["alcanza"]:
            self._limpiar(f"Ese riesgo no alcanza ni para el mínimo: necesitás {r['costo_1']:,.2f} USD "
                          f"para 1 {'lote' if paso < 1 else 'contrato'} con ese stop "
                          f"(exacto: {r['exacto']:.3f}).")
            return
        self.lbl_cant.configure(text=f"{r['cantidad']:.{dec}f} {cantidad_txt}", text_color=POS_TXT)
        det = [f"Riesgo real: {r['riesgo_real']:,.2f} USD"]
        if abs(r["exacto"] - r["cantidad"]) > 0.001:
            det.append(f"Exacto: {r['exacto']:.3f}")
        if r["pct_drawdown"] is not None:
            det.append(f"Consume {r['pct_drawdown']:.1f}% del drawdown permitido")
        if r["target"]:
            t = r["target"]
            det.append(f"Target {t['puntos']:g}: +{t['ganancia']:,.2f} USD (R:R 1:{t['ratio']:.2f})")
        self.lbl_det.configure(text="\n".join(det))
        aviso = ""
        if modo == "Futuros" and not self.seg_unidad.get().endswith("ticks"):
            c = RK.combinar(self._num(self.en_riesgo), self._num(self.en_stop), sim)
            if c:
                aviso = (f"Para aprovechar mejor el riesgo: {c['n_grande']} {c['grande']} + "
                         f"{c['n_micro']} {c['micro']} (riesgo real {c['riesgo_real']:,.2f} USD)")
        self.lbl_aviso.configure(text=aviso)
        self.lbl_rr.configure(text="\n".join(
            f"R:R 1:{x['ratio']:<5g} {x['puntos']:>8.2f}   +{x['ganancia']:>10,.2f} USD" for x in r["rr"]))

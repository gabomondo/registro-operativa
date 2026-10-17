"""Pantalla Cuentas como Mixin de App: alta/edición de cuentas, etiqueta de estado con fecha y capital inicial."""
from tkinter import messagebox
import customtkinter as ctk

from registro import analisis as A
from registro import cuentas as Q
from registro.db import (
    ESTADOS_CUENTA, TIPOS_CUENTA, db_all, db_cuenta_borrar, db_cuenta_guardar, db_cuenta_historial,
    db_cuenta_set_estado, db_cuentas, get_cuenta_global, merged_values)
from registro.ui import vivo
from registro.ui.estado import CTX
from registro.ui.tema import (
    BLUE_HI, BORDER_W, FONT_MAIN, FONT_MONO, FONT_SERIF, LINE, MUTED, MUTED2, NAV_SEL,
    NEG_TXT, PAPER, POS_TXT, RAD_CARD, RAD_CTRL, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SURFACE,
    SURFACE2)
from registro.ui.widgets import btn_ghost, btn_primary, styled_combo, styled_entry

vivo.registrar(globals())


class CuentasMixin:
    def _build_cuentas(self):
        t = self.tab_cuentas
        self.cu_sel = None            # id de la cuenta seleccionada (None = nueva)
        t.grid_columnconfigure(0, weight=2, uniform="cu")
        t.grid_columnconfigure(1, weight=3, uniform="cu")
        t.grid_rowconfigure(0, weight=1)
        izq = ctk.CTkFrame(t, fg_color=SURFACE, corner_radius=RAD_CARD)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, SP_MD), pady=(SP_SM, 0))
        cab = ctk.CTkFrame(izq, fg_color="transparent"); cab.pack(fill="x", padx=SP_LG, pady=(SP_LG, SP_SM))
        ctk.CTkLabel(cab, text="TUS CUENTAS", font=(FONT_MAIN, 10), text_color=MUTED).pack(side="left")
        btn_primary(cab, "+ Nueva", self._cu_nueva, width=90, height=30).pack(side="right")
        self._barra_filtros(izq, "cuf", self.render_cuentas, ancho=100).pack(fill="x", padx=SP_LG, pady=(0, SP_SM))
        self.cu_lista = ctk.CTkScrollableFrame(izq, fg_color="transparent")
        self.cu_lista.pack(fill="both", expand=True, padx=SP_SM, pady=(0, SP_SM))
        der = ctk.CTkFrame(t, fg_color=SURFACE, corner_radius=RAD_CARD)
        der.grid(row=0, column=1, sticky="nsew", pady=(SP_SM, 0))
        sc = ctk.CTkScrollableFrame(der, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=SP_SM, pady=SP_SM)

        fila = ctk.CTkFrame(sc, fg_color="transparent"); fila.pack(fill="x", padx=SP_MD, pady=(SP_SM, 0))
        c1 = ctk.CTkFrame(fila, fg_color="transparent"); c1.pack(side="left", padx=(0, SP_LG))
        self._lbl(c1, "Empresa").pack(anchor="w", pady=(0, SP_XS))
        self.cu_empresa = styled_combo(c1, merged_values(CTX.perfil.empresas, "empresa"), width=200, mono=False)
        self.cu_empresa.pack(anchor="w")
        c2 = ctk.CTkFrame(fila, fg_color="transparent"); c2.pack(side="left")
        self._lbl(c2, "Cuenta (id o nombre)").pack(anchor="w", pady=(0, SP_XS))
        self.cu_cuenta = styled_entry(c2, width=220, mono=False)
        self.cu_cuenta.pack(anchor="w")
        self.cu_aviso_id = ctk.CTkLabel(sc, text="", font=(FONT_MAIN, 10), text_color=MUTED2, anchor="w")
        self.cu_aviso_id.pack(fill="x", padx=SP_MD)

        self._lbl(sc, "Alias (opcional)").pack(anchor="w", padx=SP_MD, pady=(SP_MD, SP_XS))
        self.cu_alias = styled_entry(sc, width=320, mono=False)
        self.cu_alias.pack(anchor="w", padx=SP_MD)

        fila2 = ctk.CTkFrame(sc, fg_color="transparent"); fila2.pack(fill="x", padx=SP_MD, pady=(SP_MD, 0))
        for attr, titulo, vals, ancho in (("cu_tipo", "Tipo", Q.etiquetas_tipo(), 130),
                                          ("cu_estado", "Estado (opcional)", Q.etiquetas_estado(), 170)):
            col = ctk.CTkFrame(fila2, fg_color="transparent"); col.pack(side="left", padx=(0, SP_LG))
            self._lbl(col, titulo).pack(anchor="w", pady=(0, SP_XS))
            w = styled_combo(col, vals, width=ancho, mono=False, default=Q.SIN)
            w.pack(anchor="w")
            setattr(self, attr, w)
        col = ctk.CTkFrame(fila2, fg_color="transparent"); col.pack(side="left", padx=(0, SP_LG))
        self._lbl(col, "Capital inicial (opcional)").pack(anchor="w", pady=(0, SP_XS))
        self.cu_capital = styled_entry(col, width=130, placeholder="ej. 50000 o 50k")
        self.cu_capital.pack(anchor="w")
        col = ctk.CTkFrame(fila2, fg_color="transparent")
        col.pack(side="left")
        self._lbl(col, "Estado desde").pack(anchor="w", pady=(0, SP_XS))
        self.cu_desde = styled_entry(col, width=120, placeholder="AAAA-MM-DD")
        self.cu_desde.pack(anchor="w")
        ctk.CTkLabel(sc, text="«Estado desde» solo se usa si cambiás el estado; vacío = hoy.",
                     font=(FONT_MAIN, 10), text_color=MUTED2, anchor="w").pack(fill="x", padx=SP_MD, pady=(SP_XS, 0))

        bar = ctk.CTkFrame(sc, fg_color="transparent"); bar.pack(fill="x", padx=SP_MD, pady=SP_MD)
        btn_primary(bar, "Guardar", self._cu_guardar, width=110).pack(side="left")
        self.cu_btn_borrar = btn_ghost(bar, "Borrar ficha", self._cu_borrar, width=120, text_color=NEG_TXT)
        self.cu_btn_borrar.pack(side="left", padx=SP_SM)
        self.cu_msg = ctk.CTkLabel(bar, text="", font=(FONT_MAIN, 11), text_color=MUTED)
        self.cu_msg.pack(side="left", padx=SP_SM)
        self.cu_stats = ctk.CTkFrame(sc, fg_color="transparent")
        self.cu_stats.pack(fill="x", padx=SP_MD, pady=(SP_SM, SP_SM))
        self.cu_hist = ctk.CTkFrame(sc, fg_color="transparent")
        self.cu_hist.pack(fill="x", padx=SP_MD, pady=(0, SP_MD))

    # ---- filtros (también los usa Portfolio) ----
    def _barra_filtros(self, parent, pre, comando, ancho=118):
        """Tres desplegables (estado, empresa, tipo) guardados como self.<pre>_estado / _empresa / _tipo."""
        barra = ctk.CTkFrame(parent, fg_color="transparent")
        for attr, rot, vals in (("estado", "ESTADO", Q.opciones_estado()), ("empresa", "EMPRESA", [Q.TODOS]),
                                ("tipo", "TIPO", Q.opciones_tipo())):
            col = ctk.CTkFrame(barra, fg_color="transparent"); col.pack(side="left", padx=(0, SP_SM))
            ctk.CTkLabel(col, text=rot, font=(FONT_MAIN, 9), text_color=MUTED2).pack(anchor="w")
            w = styled_combo(col, vals, width=ancho, mono=False, default=Q.TODOS)
            w.configure(command=lambda v: comando())
            w.pack(anchor="w", pady=(SP_XS, 0))
            setattr(self, f"{pre}_{attr}", w)
        return barra

    def _refrescar_filtros(self, pre, cuentas):
        """Actualiza las empresas disponibles (si la elegida ya no existe, vuelve a Todos)."""
        w = getattr(self, f"{pre}_empresa")
        vals = Q.opciones_empresa(cuentas)
        w.configure(values=vals)
        if w.get() not in vals:
            w.set(Q.TODOS)

    def _filtros_cuentas(self, pre, cuentas):
        """Fichas que pasan los filtros de la barra `pre`."""
        emp = getattr(self, f"{pre}_empresa").get()
        return Q.filtrar(
            cuentas,
            estado=Q.clave_filtro_estado(getattr(self, f"{pre}_estado").get()),
            empresa=None if emp in ("", Q.TODOS) else emp,
            tipo=Q.clave_tipo(getattr(self, f"{pre}_tipo").get()))

    # ---- lista ----
    def render_cuentas(self):
        for w in self.cu_lista.winfo_children():
            w.destroy()
        todas = db_cuentas()
        self._refrescar_filtros("cuf", todas)
        datos = self._filtros_cuentas("cuf", todas)
        if todas and not datos:
            ctk.CTkLabel(self.cu_lista, text="Ninguna cuenta coincide con el filtro.",
                         font=(FONT_MAIN, 12), text_color=MUTED, justify="center").pack(pady=SP_XL)
        elif not todas:
            ctk.CTkLabel(self.cu_lista, text="Todavía no hay cuentas.\nSe crean solas al cargar operaciones,\no con «+ Nueva».",
                         font=(FONT_MAIN, 12), text_color=MUTED, justify="center").pack(pady=SP_XL)
        for d in datos:
            sel = d["id"] == self.cu_sel
            card = ctk.CTkFrame(self.cu_lista, fg_color=NAV_SEL if sel else SURFACE2, corner_radius=RAD_CTRL,
                                border_color=BLUE_HI if sel else LINE, border_width=BORDER_W, cursor="hand2")
            card.pack(fill="x", padx=SP_XS, pady=3)
            a = ctk.CTkFrame(card, fg_color="transparent"); a.pack(fill="x", padx=SP_MD, pady=(SP_SM, 0))
            ctk.CTkLabel(a, text=Q.titulo(d), font=(FONT_MAIN, 13), text_color=PAPER, anchor="w").pack(side="left")
            if d["n_ops"]:
                ctk.CTkLabel(a, text=f"{d['pnl']:+,.0f}", font=(FONT_SERIF, 18),
                             text_color=POS_TXT if d["pnl"] >= 0 else NEG_TXT).pack(side="right")
            sub = Q.detalle(d) or "sin etiqueta"
            b = ctk.CTkLabel(card, text=f"{sub}  ·  {d['n_ops']} trades", font=(FONT_MONO, 10),
                             text_color=MUTED, anchor="w")
            b.pack(fill="x", padx=SP_MD, pady=(0, SP_SM))
            for w in (card, a, b) + tuple(a.winfo_children()):
                w.bind("<Button-1>", lambda e, dd=d: self._cu_elegir(dd))
        sel = next((d for d in datos if d["id"] == self.cu_sel), None)
        self._cu_cargar_editor(sel)

    def _cu_elegir(self, d):
        self.cu_sel = d["id"]
        self.render_cuentas()

    def _cu_nueva(self):
        self.cu_sel = None
        self.render_cuentas()
        self.cu_empresa.focus_set()

    # ---- editor ----
    def _cu_cargar_editor(self, d):
        self.cu_cuenta.configure(state="normal")
        self.cu_empresa.configure(state="normal")
        self.cu_empresa.set(""); self.cu_cuenta.delete(0, "end"); self.cu_alias.delete(0, "end")
        self.cu_capital.delete(0, "end"); self.cu_desde.delete(0, "end")
        self.cu_tipo.set(Q.SIN); self.cu_estado.set(Q.SIN)
        self.cu_msg.configure(text="")
        for w in list(self.cu_stats.winfo_children()) + list(self.cu_hist.winfo_children()):
            w.destroy()
        if not d:
            self.cu_aviso_id.configure(text="")
            self.cu_btn_borrar.configure(state="disabled")
            return
        self.cu_empresa.set(d["empresa"]); self.cu_cuenta.insert(0, d["cuenta"])
        # empresa y cuenta son el vínculo con las operaciones: no se renombran desde acá
        self.cu_empresa.configure(state="disabled"); self.cu_cuenta.configure(state="disabled")
        self.cu_aviso_id.configure(text="Empresa y cuenta no se editan: son las que usan tus operaciones.")
        self.cu_alias.insert(0, d["alias"] or "")
        self.cu_tipo.set(TIPOS_CUENTA.get(d["tipo"], Q.SIN))
        self.cu_estado.set(ESTADOS_CUENTA.get(d["estado"], Q.SIN))
        self.cu_capital.insert(0, Q.fmt_capital(d["capital_inicial"]))
        self.cu_btn_borrar.configure(state="normal")
        ops = [o for o in db_all(todo=True) if (o.get("empresa") or "") == d["empresa"]
               and (o.get("cuenta") or "") == d["cuenta"] and o.get("profit") is not None]
        r = A.resumen(ops)
        if r:
            ctk.CTkLabel(self.cu_stats, text="CÓMO RINDE", font=(FONT_MAIN, 10), text_color=MUTED).pack(anchor="w")
            fila = ctk.CTkFrame(self.cu_stats, fg_color="transparent"); fila.pack(fill="x", pady=SP_XS)
            cap = d["capital_inicial"]
            tarjetas = [("Neto", f"{r['neto']:+,.0f}", POS_TXT if r["neto"] >= 0 else NEG_TXT),
                        ("Win rate", f"{r['wr']:.0f}%", PAPER),
                        ("Profit factor", "—" if r["profit_factor"] is None else f"{r['profit_factor']:.2f}", PAPER)]
            if cap:
                tarjetas.append(("Retorno", f"{100 * r['neto'] / cap:+.1f}%", POS_TXT if r["neto"] >= 0 else NEG_TXT))
            for i, (lab, val, col) in enumerate(tarjetas):
                fila.grid_columnconfigure(i, weight=1, uniform="cus")
                c = ctk.CTkFrame(fila, fg_color=SURFACE2, corner_radius=RAD_CTRL)
                c.grid(row=0, column=i, sticky="nsew", padx=2)
                ctk.CTkLabel(c, text=lab.upper(), font=(FONT_MAIN, 9), text_color=MUTED).pack(anchor="w", padx=SP_MD, pady=(SP_SM, 0))
                ctk.CTkLabel(c, text=val, font=(FONT_SERIF, 22), text_color=col).pack(anchor="w", padx=SP_MD, pady=(0, SP_SM))
        hist = db_cuenta_historial(d["id"])
        if hist:
            ctk.CTkLabel(self.cu_hist, text="HISTORIAL DE ESTADO", font=(FONT_MAIN, 10), text_color=MUTED).pack(anchor="w", pady=(SP_SM, SP_XS))
            for h in reversed(hist):
                ctk.CTkLabel(self.cu_hist, text=f"{h['desde']}   {ESTADOS_CUENTA.get(h['estado'], 'sin etiqueta')}",
                             font=(FONT_MONO, 11), text_color=PAPER, anchor="w").pack(fill="x")

    def _cu_error(self, texto):
        self.cu_msg.configure(text=texto, text_color=NEG_TXT)

    def _cu_guardar(self):
        try:
            capital = Q.parse_capital(self.cu_capital.get())
            desde = Q.parse_fecha(self.cu_desde.get())
        except ValueError as e:
            self._cu_error(str(e)); return
        tipo = Q.clave_tipo(self.cu_tipo.get())
        estado = Q.clave_estado(self.cu_estado.get())
        actual = next((c for c in db_cuentas() if c["id"] == self.cu_sel), None)
        empresa = actual["empresa"] if actual else self.cu_empresa.get().strip()
        cuenta = actual["cuenta"] if actual else self.cu_cuenta.get().strip()
        try:
            cid = db_cuenta_guardar(empresa, cuenta, alias=self.cu_alias.get(), tipo=tipo, capital_inicial=capital)
            if (actual["estado"] if actual else None) != estado:
                db_cuenta_set_estado(cid, estado, desde=desde)
        except Exception as e:
            self._cu_error(f"No se pudo guardar: {e}"); return
        self.cu_sel = cid
        self.render_cuentas()
        self.cu_msg.configure(text="guardado ✓", text_color=MUTED)

    def _cu_borrar(self):
        if self.cu_sel and messagebox.askyesno(
                "Borrar ficha de cuenta",
                "¿Borrar la ficha de esta cuenta (alias, estado, capital e historial)?\n"
                "Tus operaciones no se tocan; si cargás otra con esa cuenta, la ficha reaparece vacía."):
            actual = next((c for c in db_cuentas() if c["id"] == self.cu_sel), None)
            db_cuenta_borrar(self.cu_sel)
            if actual and Q.clave(actual) == get_cuenta_global():
                self._elegir_cuenta(None)
            self.cu_sel = None
            self.render_cuentas()

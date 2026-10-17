"""Diálogo «Importar trades» (NinjaTrader / MT5 / Tradovate / TopstepX)."""

import os
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from registro.db import merged_values
from registro.ui import vivo
from registro.ui.estado import CTX
from registro.ui.tema import BLUE, BLUE_HI, CAUTION, FONT_MAIN, FONT_SERIF, INK, LINE2, MUTED, MUTED2, PAPER, RAD_CARD, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SURFACE, SURFACE2, T_LOSS, T_WIN
from registro.ui.ventanas import centrar_dialogo
from registro.ui.util import _fmt_precio, _fmt_usd
from registro.ui.widgets import btn_ghost, btn_primary, styled_combo

vivo.registrar(globals())


# ----------------------------------------------------------------------------
# Importar trades desde NinjaTrader / MT5 / Tradovate / TopstepX
# ----------------------------------------------------------------------------


class ImportarDialog(ctk.CTkToplevel):
    COLS = [("inc", "", 34, "center"), ("fecha", "Fecha", 86, "w"), ("hora", "Hora", 52, "w"),
            ("activo", "Activo", 70, "w"), ("lado", "Lado", 56, "w"), ("cts", "Cts", 50, "e"),
            ("ent", "Entrada", 88, "e"), ("sal", "Salida", 88, "e"), ("bruto", "Bruto", 80, "e"),
            ("com", "Costo", 62, "e"), ("neto", "Neto", 84, "e"),
            ("cuenta", "Cuenta (plataforma)", 150, "w"), ("estado", "Estado", 200, "w")]

    def __init__(self, app, path=None):
        super().__init__(app)
        self.app = app
        self.title("Importar trades")
        f = app.factor
        centrar_dialogo(self, app, int(1180 * f), int(700 * f), int(980 * f), int(560 * f))
        self.configure(fg_color=INK)
        self.transient(app)
        self.lectura = None
        self.vista = []
        self.cuenta_vars = {}
        self._build()
        self.after(80, self._tomar_foco)
        if path:
            self.after(120, lambda: self._cargar(path))

    def _tomar_foco(self):
        try:
            self.grab_set()
            self.focus_set()
        except Exception:
            pass

    # ---------- UI ----------
    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=SP_XL, pady=(SP_LG, 0))
        ctk.CTkLabel(top, text="Importar trades", font=(FONT_SERIF, 26),
                     text_color=PAPER).pack(side="left")
        btn_primary(top, "Elegir archivo…", self._elegir, width=150, height=34).pack(side="right")
        self.lbl_archivo = ctk.CTkLabel(
            self, text="Elegí el archivo que exportaste de NinjaTrader 8, MetaTrader 4/5, "
                       "Tradovate, TopstepX o DeepCharts. Vas a ver una vista previa antes de guardar nada.",
            font=(FONT_MAIN, 12), text_color=MUTED, wraplength=1080, justify="left", anchor="w")
        self.lbl_archivo.pack(fill="x", padx=SP_XL, pady=(SP_XS, 0))
        self.lbl_avisos = ctk.CTkLabel(self, text="", font=(FONT_MAIN, 11), text_color=CAUTION,
                                       wraplength=1080, justify="left", anchor="w")
        self.lbl_avisos.pack(fill="x", padx=SP_XL, pady=(SP_XS, 0))

        # opciones
        self.opts = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=RAD_CARD)
        self.opts.pack(fill="x", padx=SP_XL, pady=(SP_MD, 0))
        fila = ctk.CTkFrame(self.opts, fg_color="transparent")
        fila.pack(fill="x", padx=SP_MD, pady=SP_MD)
        self.frm_cuentas = ctk.CTkFrame(fila, fg_color="transparent")
        self.frm_cuentas.pack(side="left", fill="y", anchor="n")
        der = ctk.CTkFrame(fila, fg_color="transparent")
        der.pack(side="right", anchor="n")
        self.chk_juntar = ctk.CTkCheckBox(
            der, text="Juntar el mismo trade de varias cuentas (copy trading)",
            font=(FONT_MAIN, 12), text_color=PAPER, fg_color=BLUE, hover_color=BLUE_HI,
            border_color=LINE2, command=self._aplicar)
        self.chk_juntar.select()
        self.chk_juntar.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, SP_SM))
        ctk.CTkLabel(der, text="EMPRESA", font=(FONT_MAIN, 9), text_color=MUTED2).grid(
            row=1, column=0, sticky="w")
        ctk.CTkLabel(der, text="TIPO DE CUENTA", font=(FONT_MAIN, 9), text_color=MUTED2).grid(
            row=1, column=1, sticky="w", padx=(SP_MD, 0))
        self.cb_empresa = styled_combo(der, merged_values(CTX.perfil.empresas, "empresa"), width=190)
        self.cb_empresa.set(CTX.perfil.empresas[0] if CTX.perfil.empresas else "")
        self.cb_empresa.grid(row=2, column=0, sticky="w")
        self.cb_cuenta = styled_combo(der, list(CTX.perfil.tipos_cuenta), width=150,
                                      default=self.app._def("tipos_cuenta"))
        self.cb_cuenta.grid(row=2, column=1, sticky="w", padx=(SP_MD, 0))

        # pie (se empaqueta primero para que nunca quede tapado)
        self.lbl_sel = ctk.CTkLabel(self, text="", font=(FONT_MAIN, 11), text_color=CAUTION,
                                    anchor="w", justify="left", wraplength=1080)
        self.lbl_sel.pack(side="bottom", fill="x", padx=SP_XL)
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(side="bottom", fill="x", padx=SP_XL, pady=SP_LG)
        self.lbl_resumen = ctk.CTkLabel(pie, text="", font=(FONT_MAIN, 13), text_color=PAPER,
                                        anchor="w", justify="left")
        self.lbl_resumen.pack(side="left")
        self.btn_ok = btn_primary(pie, "Importar", self._importar, width=170, height=36)
        self.btn_ok.pack(side="right")
        btn_ghost(pie, "Cancelar", self.destroy, width=110, height=36).pack(side="right", padx=SP_SM)
        btn_ghost(pie, "Ninguno", lambda: self._marcar(False), width=84, height=32).pack(
            side="right", padx=(0, SP_SM))
        btn_ghost(pie, "Todos", lambda: self._marcar(True), width=84, height=32).pack(
            side="right", padx=(0, SP_XS))
        self.btn_ok.configure(state="disabled")
        # tabla
        wrap = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=RAD_CARD)
        wrap.pack(fill="both", expand=True, padx=SP_XL, pady=(SP_MD, 0))
        inner = ctk.CTkFrame(wrap, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SP_SM, pady=SP_SM)
        cols = [c[0] for c in self.COLS]
        tree = ttk.Treeview(inner, columns=cols, show="headings", style="Gabo.Treeview",
                            selectmode="browse")
        for col, label, w, anchor in self.COLS:
            tree.heading(col, text=label, anchor="w" if anchor == "w" else anchor)
            tree.column(col, width=int(w * self.app._ws()), minwidth=int(30 * self.app._ws()),
                        anchor=anchor, stretch=(col == "estado"))
        for res, (a, b) in {"win": T_WIN, "loss": T_LOSS,
                            "flat": (SURFACE, SURFACE2)}.items():
            tree.tag_configure(f"{res}_a", background=a, foreground=PAPER)
            tree.tag_configure(f"{res}_b", background=b, foreground=PAPER)
        tree.tag_configure("off", foreground=MUTED2)
        sb = ctk.CTkScrollbar(inner, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        tree.bind("<<TreeviewSelect>>", self._on_select)
        tree.bind("<Button-1>", self._on_click)
        tree.bind("<space>", lambda e: self._toggle(tree.focus()))
        tree.bind("<Double-1>", lambda e: self._toggle(tree.identify_row(e.y)))
        self.tree = tree


    # ---------- carga ----------
    def _elegir(self):
        p = filedialog.askopenfilename(
            parent=self, title="Archivo exportado",
            filetypes=[("Exports de trading", "*.csv *.html *.htm *.xlsx"), ("Todos", "*.*")])
        if p:
            self._cargar(p)

    def _cargar(self, path):
        from registro import importadores as imp
        try:
            lec = imp.leer(path, CTX.perfil)
        except imp.ImportError_ as e:
            messagebox.showerror("Importar", str(e), parent=self)
            return
        except Exception as e:
            CTX.log.exception("Importar %s", path)
            messagebox.showerror("Importar", f"No pude leer el archivo.\n\n{e}\n\n"
                                 "El detalle quedó en el log (Perfil → Abrir carpeta de datos).",
                                 parent=self)
            return
        self.lectura = lec
        self.lbl_archivo.configure(
            text=f"{os.path.basename(path)}  ·  {lec.formato}  ·  {len(lec.trades)} trades detectados",
            text_color=PAPER)
        avisos = list(lec.avisos)
        sin_com = sum(1 for t in lec.trades if any(a.startswith("Sin comisión") for a in t.avisos))
        if sin_com:
            avisos.append(f"{sin_com} trades quedaron sin comisión. Cargá la comisión por contrato "
                          "en Perfil ANTES de importar: cerrá esta ventana, cargala y abrí el archivo de nuevo "
                          "(lo ya importado no se pisa).")
        self.lbl_avisos.configure(text="\n".join("• " + a for a in avisos))
        self._armar_cuentas()
        self._aplicar()

    def _armar_cuentas(self):
        from registro.importadores.nt8 import es_simulada
        for w in self.frm_cuentas.winfo_children():
            w.destroy()
        self.cuenta_vars = {}
        cuentas = self.lectura.cuentas
        reales = [c for c in cuentas if not es_simulada(c)]
        if len(cuentas) <= 1:
            self.frm_cuentas.pack_forget()
            self.chk_juntar.grid_remove()
            for c in cuentas:
                self.cuenta_vars[c] = tk.BooleanVar(value=True)
            return
        self.frm_cuentas.pack(side="left", fill="y", anchor="n")
        self.chk_juntar.grid()
        ctk.CTkLabel(self.frm_cuentas, text="CUENTAS A IMPORTAR", font=(FONT_MAIN, 9),
                     text_color=MUTED2).pack(anchor="w")
        caja = ctk.CTkScrollableFrame(self.frm_cuentas, fg_color="transparent", width=420,
                                      height=min(150, 28 * ((len(cuentas) + 1) // 2) + 8))
        caja.pack(anchor="w")
        for i, c in enumerate(cuentas):
            v = tk.BooleanVar(value=(c in reales) if reales else True)
            self.cuenta_vars[c] = v
            ctk.CTkCheckBox(caja, text=c + ("  (simulada)" if es_simulada(c) else ""), variable=v,
                            font=(FONT_MAIN, 11), text_color=PAPER, fg_color=BLUE,
                            hover_color=BLUE_HI, border_color=LINE2, checkbox_width=18,
                            checkbox_height=18, command=self._aplicar).grid(
                row=i // 2, column=i % 2, sticky="w", padx=(0, SP_MD), pady=2)

    def _aplicar(self):
        from registro import importadores as imp
        from registro.db import claves_importadas, marcar_posibles_duplicados
        if not self.lectura:
            return
        sel = {c for c, v in self.cuenta_vars.items() if v.get()}
        ts = [t for t in self.lectura.trades if t.cuenta in sel]
        if len(sel) > 1 and self.chk_juntar.get():
            ts = imp.consolidar_cuentas(ts, CTX.perfil.agrupar_segundos)
        ya = claves_importadas()
        for t in ts:
            t.duplicado = t.clave in ya
            t.incluir = (not t.duplicado) and t.neto is not None
        try:
            marcar_posibles_duplicados(ts)
        except Exception:
            CTX.log.exception("marcar_posibles_duplicados")   # el aviso es opcional
        for t in ts:
            if t.posible:
                t.incluir = False        # destildado: el usuario decide
        self.vista = ts
        self.lbl_sel.configure(text="")
        self._render()

    # ---------- tabla ----------
    def _estado(self, t):
        if t.duplicado:
            return "Ya importado"
        if t.neto is None:
            return "Sin P&L (revisá Perfil)"
        if t.posible:
            return "¿Duplicado? ver detalle abajo"
        partes = []
        if t.cuentas_n > 1:
            partes.append(f"{t.cuentas_n} cuentas")
        if t.motivo:
            partes.append(f"salió por {t.motivo}")
        if t.avisos:
            partes.append("⚠ ver detalle abajo")
        return " · ".join(partes) or "Nuevo"

    def _render(self):
        tree = self.tree
        tree.delete(*tree.get_children())
        for i, t in enumerate(self.vista):
            n = t.neto
            res = "flat" if n is None or n == 0 else ("win" if n > 0 else "loss")
            tags = [f"{res}_{'a' if i % 2 == 0 else 'b'}"]
            if not t.incluir:
                tags.append("off")
            tree.insert("", "end", iid=str(i), tags=tags, values=(
                "☑" if t.incluir else "☐", t.t_ini.strftime("%Y-%m-%d"), t.t_ini.strftime("%H:%M"),
                t.activo, t.lado, f"{t.contratos:g}", _fmt_precio(t.precio_ini),
                _fmt_precio(t.precio_fin), _fmt_usd(t.bruto, True), _fmt_usd(t.comision),
                _fmt_usd(n, True), t.cuenta, self._estado(t)))
        self._resumen()

    def _resumen(self):
        inc = [t for t in self.vista if t.incluir]
        dup = sum(1 for t in self.vista if t.duplicado)
        posib = sum(1 for t in self.vista if t.posible and not t.duplicado)
        sinpl = sum(1 for t in self.vista if t.neto is None)
        neto = sum(t.neto for t in inc)
        txt = f"{len(inc)} trades para importar  ·  neto {neto:+,.2f}"
        if dup:
            txt += f"  ·  {dup} ya estaban"
        if posib:
            txt += f"  ·  {posib} posibles duplicados (sin tildar)"
        if sinpl:
            txt += f"  ·  {sinpl} sin P&L"
        self.lbl_resumen.configure(text=txt)
        self.btn_ok.configure(text=f"Importar {len(inc)}", state="normal" if inc else "disabled")

    def _on_select(self, e=None):
        sel = self.tree.selection()
        t = self.vista[int(sel[0])] if sel else None
        det = ([f"Posible duplicado: {t.posible}. Tildalo solo si es otra operación."]
               if t and t.posible else []) + (t.avisos if t else [])
        self.lbl_sel.configure(text=("⚠ " + "  ·  ".join(det)) if det else "")

    def _on_click(self, e):
        if self.tree.identify_region(e.x, e.y) == "cell" and self.tree.identify_column(e.x) == "#1":
            self._toggle(self.tree.identify_row(e.y))
            return "break"

    def _toggle(self, iid):
        if not iid:
            return
        t = self.vista[int(iid)]
        if t.duplicado or t.neto is None:
            return
        t.incluir = not t.incluir
        tags = [x for x in self.tree.item(iid, "tags") if x != "off"]
        if not t.incluir:
            tags.append("off")
        vals = list(self.tree.item(iid, "values"))
        vals[0] = "☑" if t.incluir else "☐"
        self.tree.item(iid, values=vals, tags=tags)
        self._resumen()

    def _marcar(self, valor):
        for t in self.vista:
            if not t.duplicado and t.neto is not None:
                t.incluir = valor
        self._render()

    # ---------- guardar ----------
    def _importar(self):
        from registro.db import db_importar
        lista = [t for t in self.vista if t.incluir]
        if not lista:
            return
        try:
            res = db_importar(lista, empresa=self.cb_empresa.get().strip(),
                              cuenta=self.cb_cuenta.get().strip())
        except Exception as e:
            CTX.log.exception("db_importar")
            messagebox.showerror("Importar", f"No se pudo guardar: {e}", parent=self)
            return
        CTX.log.info("Importados %s trades de %s (%s dup)", res["nuevos"],
                     self.lectura.formato, res["duplicados"])
        self.app._table_dirty = True
        self.app._refresh_dropdowns()
        self.app.render_table()
        self.app.tabs.set("Registro")
        msg = f"Se importaron {res['nuevos']} trades."
        if res["duplicados"]:
            msg += f"\n{res['duplicados']} ya estaban y se saltearon."
        messagebox.showinfo("Importar", msg, parent=self)
        self.destroy()

"""Diálogo «Exportar reporte» (PDF / HTML / Excel / CSV)."""

import os
import sys
import subprocess
from datetime import datetime, timedelta, date
import customtkinter as ctk
from tkinter import filedialog
from registro.db import db_all, merged_values
from registro.ui import vivo
from registro.ui.estado import CTX, save_ui_prefs
from registro.ui.tema import TEMA_ACTUAL, BLUE, BLUE_HI, CAUTION, FONT_MAIN, FONT_SERIF, HOVER, INK, LINE2, MUTED, MUTED2, NEG_TXT, PAPER, POS_TXT, RAD_CARD, SEG_HI, SEG_SEL, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SURFACE
from registro.ui.ventanas import centrar_dialogo
from registro.ui.widgets import DatePicker, btn_ghost, btn_primary, styled_combo, styled_entry

vivo.registrar(globals())


# ----------------------------------------------------------------------------
# App principal
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# Exportar reporte (PDF / HTML / Excel / CSV)
# ----------------------------------------------------------------------------
class ExportarDialog(ctk.CTkToplevel):
    DESC = {
        "pdf": "Documento listo para imprimir o mandar. Tablas y gráficos con tu marca.",
        "html": "Una sola página web que se abre en cualquier navegador. Se puede ordenar y filtrar el detalle.",
        "xlsx": "Planilla con una hoja por sección, fórmulas vivas y gráfico de equity.",
        "csv": "Solo el detalle de operaciones, para abrir en otra herramienta.",
    }
    PERIODOS = ["7 días", "30 días", "Este mes", "Todo", "Rango"]

    def __init__(self, app, periodo=None, cuenta=None):
        super().__init__(app)
        from registro import exportar as EX
        self.EX = EX
        self.app = app
        self.title("Exportar reporte")
        f = app.factor
        centrar_dialogo(self, app, int(780 * f), int(760 * f), int(680 * f), int(560 * f))
        self.configure(fg_color=INK)
        self.transient(app)
        pr = dict(app._ui_prefs.get("exportar", {}))
        self.pr = pr
        self.sec_vars = {}
        self.ruta_ok = None
        self._build(periodo, cuenta)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self._exportar())
        self._cambio_formato()
        self._actualizar()
        self.after(80, self._tomar_foco)

    def _tomar_foco(self):
        try:
            self.grab_set()
            self.focus_set()
        except Exception:
            pass

    def _seg(self, parent, values, command, default):
        s = ctk.CTkSegmentedButton(
            parent, values=values, height=32, font=(FONT_MAIN, 12), fg_color=SURFACE,
            selected_color=SEG_SEL, selected_hover_color=SEG_HI, unselected_color=SURFACE,
            unselected_hover_color=HOVER, text_color=PAPER, command=command)
        s.set(default)
        return s

    def _chk(self, parent, texto, valor, command=None):
        c = ctk.CTkCheckBox(parent, text=texto, font=(FONT_MAIN, 12), text_color=PAPER,
                            fg_color=BLUE, hover_color=BLUE_HI, border_color=LINE2, command=command)
        if valor:
            c.select()
        return c

    def _label(self, parent, texto):
        return ctk.CTkLabel(parent, text=texto, font=(FONT_MAIN, 9), text_color=MUTED2, anchor="w")

    def _build(self, periodo, cuenta):
        EX, pr = self.EX, self.pr
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(side="bottom", fill="x", padx=SP_XL, pady=SP_LG)
        self.lbl_estado = ctk.CTkLabel(self, text="", font=(FONT_MAIN, 12), text_color=POS_TXT,
                                       anchor="w", justify="left", wraplength=700)
        self.lbl_estado.pack(side="bottom", fill="x", padx=SP_XL)
        self.btn_ok = btn_primary(pie, "Exportar…", self._exportar, width=160, height=36)
        self.btn_ok.pack(side="right")
        btn_ghost(pie, "Cerrar", self.destroy, width=100, height=36).pack(side="right", padx=SP_SM)
        self.btn_abrir = btn_ghost(pie, "Abrir archivo", self._abrir, width=120, height=36)
        self.btn_carpeta = btn_ghost(pie, "Mostrar en carpeta", self._carpeta, width=150, height=36)

        ctk.CTkLabel(self, text="Exportar reporte", font=(FONT_SERIF, 26),
                     text_color=PAPER).pack(anchor="w", padx=SP_XL, pady=(SP_LG, 0))
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=SP_MD, pady=(SP_SM, 0))

        # formato
        self._label(body, "FORMATO").pack(anchor="w", padx=SP_MD)
        self.seg_fmt = self._seg(body, [n for _, n, _ in EX.FORMATOS], lambda v: self._cambio_formato(),
                                 dict((k, n) for k, n, _ in EX.FORMATOS).get(pr.get("formato", "pdf"), "PDF"))
        self.seg_fmt.pack(anchor="w", padx=SP_MD, pady=(SP_XS, 0))
        self.lbl_desc = ctk.CTkLabel(body, text="", font=(FONT_MAIN, 12), text_color=MUTED,
                                     anchor="w", justify="left", wraplength=680)
        self.lbl_desc.pack(anchor="w", padx=SP_MD, pady=(SP_XS, SP_MD))

        # período y filtros
        fila = ctk.CTkFrame(body, fg_color="transparent")
        fila.pack(fill="x", padx=SP_MD)
        a = ctk.CTkFrame(fila, fg_color="transparent"); a.pack(side="left", padx=(0, SP_XL))
        self._label(a, "PERÍODO").pack(anchor="w")
        per0 = periodo if periodo in self.PERIODOS else pr.get("periodo", "Todo")
        self.seg_per = self._seg(a, self.PERIODOS, lambda v: self._cambio_periodo(),
                                 per0 if per0 in self.PERIODOS else "Todo")
        self.seg_per.pack(anchor="w", pady=(SP_XS, 0))
        b = ctk.CTkFrame(fila, fg_color="transparent"); b.pack(side="left")
        self._label(b, "TIPO DE CUENTA").pack(anchor="w")
        self.cb_cuenta = styled_combo(b, ["Todas"] + list(CTX.perfil.tipos_cuenta), width=140,
                                      default=cuenta or "Todas")
        self.cb_cuenta.configure(command=lambda v: self._actualizar())
        self.cb_cuenta.pack(anchor="w", pady=(SP_XS, 0))
        c = ctk.CTkFrame(fila, fg_color="transparent"); c.pack(side="left", padx=(SP_MD, 0))
        self._label(c, "EMPRESA").pack(anchor="w")
        self.cb_empresa = styled_combo(c, ["Todas"] + merged_values(CTX.perfil.empresas, "empresa"),
                                       width=170, default="Todas")
        self.cb_empresa.configure(command=lambda v: self._actualizar())
        self.cb_empresa.pack(anchor="w", pady=(SP_XS, 0))

        self.frm_rango = ctk.CTkFrame(body, fg_color="transparent")
        self._label(self.frm_rango, "DESDE").grid(row=0, column=0, sticky="w")
        self._label(self.frm_rango, "HASTA").grid(row=0, column=1, sticky="w", padx=(SP_MD, 0))
        self.dp_desde = DatePicker(self.frm_rango, width=130)
        self.dp_hasta = DatePicker(self.frm_rango, width=130)
        self.dp_desde.grid(row=1, column=0, sticky="w")
        self.dp_hasta.grid(row=1, column=1, sticky="w", padx=(SP_MD, 0))
        self.dp_desde.set(pr.get("desde") or (date.today() - timedelta(days=29)).isoformat())
        self.dp_hasta.set(pr.get("hasta") or date.today().isoformat())
        for dp in (self.dp_desde, self.dp_hasta):
            dp.entry.bind("<KeyRelease>", lambda e: self._actualizar())
            dp.entry.bind("<FocusOut>", lambda e: self._actualizar())

        self.lbl_resumen = ctk.CTkLabel(body, text="", font=(FONT_MAIN, 13), text_color=PAPER,
                                        anchor="w", justify="left", wraplength=680)
        self.lbl_resumen.pack(anchor="w", padx=SP_MD, pady=(SP_MD, 0))

        # secciones
        self.frm_sec = ctk.CTkFrame(body, fg_color=SURFACE, corner_radius=RAD_CARD)
        self.frm_sec.pack(fill="x", padx=SP_MD, pady=(SP_MD, 0))
        cab = ctk.CTkFrame(self.frm_sec, fg_color="transparent")
        cab.pack(fill="x", padx=SP_MD, pady=(SP_SM, 0))
        self._label(cab, "QUÉ INCLUIR").pack(side="left")
        btn_ghost(cab, "Nada", lambda: self._marcar(False), width=64, height=26).pack(side="right")
        btn_ghost(cab, "Todo", lambda: self._marcar(True), width=64, height=26).pack(side="right", padx=SP_XS)
        elegidas = set(pr.get("secciones") or [s for s, _ in EX.SECCIONES])
        self.chk_sec = {}
        for k, nombre in EX.SECCIONES:
            ch = self._chk(self.frm_sec, nombre, k in elegidas, self._actualizar)
            ch.pack(anchor="w", padx=SP_MD, pady=3)
            self.chk_sec[k] = ch
        self.lbl_csv = ctk.CTkLabel(self.frm_sec, text="En CSV solo se exporta el detalle de operaciones.",
                                    font=(FONT_MAIN, 11), text_color=MUTED, anchor="w")
        ctk.CTkFrame(self.frm_sec, height=SP_SM, fg_color="transparent").pack()

        # opciones
        self.frm_opt = ctk.CTkFrame(body, fg_color=SURFACE, corner_radius=RAD_CARD)
        self.frm_opt.pack(fill="x", padx=SP_MD, pady=(SP_MD, 0))
        self._label(self.frm_opt, "OPCIONES").pack(anchor="w", padx=SP_MD, pady=(SP_SM, 0))
        self.chk_coment = self._chk(self.frm_opt, "Incluir mis comentarios de cada operación",
                                    pr.get("comentarios", False))
        self.chk_coment.pack(anchor="w", padx=SP_MD, pady=3)
        self.chk_anon = self._chk(self.frm_opt, "Ocultar nombres de empresa y cuenta (Cuenta A, B…) para compartir",
                                  pr.get("anonimizar", False))
        self.chk_anon.pack(anchor="w", padx=SP_MD, pady=3)
        self.chk_marca = self._chk(self.frm_opt, "Pie «Hecho con Registro de operativa»", pr.get("marca", True))
        self.chk_marca.pack(anchor="w", padx=SP_MD, pady=3)
        self.chk_fuentes = self._chk(self.frm_opt, "Incrustar tipografías (HTML; pesa más pero se ve igual en cualquier PC)",
                                     pr.get("fuentes", True))
        self.chk_fuentes.pack(anchor="w", padx=SP_MD, pady=3)
        self.frm_estilo = ctk.CTkFrame(self.frm_opt, fg_color="transparent")
        self.frm_estilo.pack(anchor="w", padx=SP_MD, pady=(SP_SM, 0))
        self._label(self.frm_estilo, "ESTILO").pack(anchor="w")
        self._temas = dict((k, n) for k, n in EX.TEMAS)
        self.cb_tema = styled_combo(self.frm_estilo, [n for _, n in EX.TEMAS], width=260,
                                    default=self._temas["blanco" if TEMA_ACTUAL == "claro" else "oscuro"])   # sigue el tema de la app
        self.cb_tema.pack(anchor="w", pady=(SP_XS, 0))
        self.frm_sep = ctk.CTkFrame(self.frm_opt, fg_color="transparent")
        self.frm_sep.pack(anchor="w", padx=SP_MD, pady=(SP_SM, 0))
        self._label(self.frm_sep, "SEPARADOR CSV (punto y coma si tu Excel está en español)").pack(anchor="w")
        self.seg_sep = self._seg(self.frm_sep, ["Coma ,", "Punto y coma ;"], None,
                                 "Punto y coma ;" if pr.get("csv_sep") == ";" else "Coma ,")
        self.seg_sep.pack(anchor="w", pady=(SP_XS, 0))
        self.lbl_titulo = self._label(self.frm_opt, "TÍTULO DEL REPORTE")
        self.lbl_titulo.pack(anchor="w", padx=SP_MD, pady=(SP_SM, 0))
        self.en_titulo = styled_entry(self.frm_opt, width=420, mono=False)
        self.en_titulo.insert(0, pr.get("titulo") or "Reporte de operativa")
        self.en_titulo.pack(anchor="w", padx=SP_MD, pady=(SP_XS, SP_MD))

    # ---------- lógica ----------
    def _formato(self):
        n = self.seg_fmt.get()
        return next((k for k, nom, _ in self.EX.FORMATOS if nom == n), "pdf")

    def _cambio_formato(self):
        fmt = self._formato()
        self.lbl_desc.configure(text=self.DESC[fmt])
        csv_ = fmt == "csv"
        for k, ch in self.chk_sec.items():
            ch.configure(state="disabled" if csv_ else "normal")
        if csv_:
            self.lbl_csv.pack(anchor="w", padx=SP_MD)
        else:
            self.lbl_csv.pack_forget()
        for w, vis in ((self.chk_marca, fmt != "csv"), (self.chk_fuentes, fmt == "html"),
                       (self.frm_estilo, fmt in ("pdf", "html")), (self.frm_sep, csv_)):
            w.pack_forget()
            if vis:
                w.pack(anchor="w", padx=SP_MD, before=self.lbl_titulo,
                       pady=(SP_SM, 0) if w in (self.frm_estilo, self.frm_sep) else 3)
        self.lbl_estado.configure(text="")
        self._mostrar_post(False)
        self._actualizar()

    def _cambio_periodo(self):
        if self.seg_per.get() == "Rango":
            self.frm_rango.pack(anchor="w", padx=SP_MD, pady=(SP_SM, 0), after=self.cb_cuenta.master.master)
        else:
            self.frm_rango.pack_forget()
        self._actualizar()

    def _marcar(self, v):
        for ch in self.chk_sec.values():
            (ch.select if v else ch.deselect)()
        self._actualizar()

    def _filtros(self):
        hoy = date.today()
        per, f = self.seg_per.get(), {}
        if per == "7 días":
            f["desde"] = (hoy - timedelta(days=6)).isoformat()
        elif per == "30 días":
            f["desde"] = (hoy - timedelta(days=29)).isoformat()
        elif per == "Este mes":
            f["desde"] = hoy.replace(day=1).isoformat()
        elif per == "Rango":
            for k, dp in (("desde", self.dp_desde), ("hasta", self.dp_hasta)):
                v = dp.get()
                try:
                    datetime.strptime(v, "%Y-%m-%d")
                    f[k] = v
                except ValueError:
                    return None
        c = self.cb_cuenta.get()
        if c and c != "Todas":
            f["cuenta"] = c
        return f

    def _filas(self):
        f = self._filtros()
        if f is None:
            return None
        rows = db_all(f, fechas=False)
        emp = self.cb_empresa.get()
        if emp and emp != "Todas":
            rows = [r for r in rows if (r.get("empresa") or "") == emp]
        return [r for r in rows if r.get("profit") is not None and r.get("fecha")]

    def _secciones(self):
        return [k for k, ch in self.chk_sec.items() if ch.get()]

    def _actualizar(self):
        rows = self._filas()
        self._mostrar_post(False)
        if rows is None:
            self.lbl_resumen.configure(text="Revisá las fechas: formato AAAA-MM-DD.", text_color=CAUTION)
            self.btn_ok.configure(state="disabled")
            return
        if not rows:
            self.lbl_resumen.configure(text="No hay operaciones con ese filtro.", text_color=CAUTION)
            self.btn_ok.configure(state="disabled")
            return
        neto = sum(float(r["profit"]) for r in rows)
        fechas = sorted(r["fecha"] for r in rows)
        self.lbl_resumen.configure(
            text=f"{len(rows)} operaciones · {fechas[0]} a {fechas[-1]} · neto {neto:+,.2f} USD",
            text_color=PAPER)
        ok = self._formato() == "csv" or bool(self._secciones())
        self.btn_ok.configure(state="normal" if ok else "disabled")
        if not ok:
            self.lbl_estado.configure(text="Tildá al menos una sección.", text_color=CAUTION)
        elif self.lbl_estado.cget("text") == "Tildá al menos una sección.":
            self.lbl_estado.configure(text="")

    def _periodo_texto(self, rows):
        per = self.seg_per.get()
        fechas = sorted(r["fecha"] for r in rows)
        rango = f"{self.EX._f(fechas[0])} a {self.EX._f(fechas[-1])}"
        return rango if per == "Todo" else f"{per} · {rango}"

    def _filtros_texto(self, anon):
        partes = []
        c, e = self.cb_cuenta.get(), self.cb_empresa.get()
        if c and c != "Todas":
            partes.append(f"Tipo de cuenta: {c}")
        if e and e != "Todas" and not anon:
            partes.append(f"Empresa: {e}")
        return " · ".join(partes)

    def _guardar_prefs(self, fmt):
        tema = next((k for k, n in self.EX.TEMAS if n == self.cb_tema.get()), "blanco")
        self.pr.update(formato=fmt, periodo=self.seg_per.get(), secciones=self._secciones(),
                       comentarios=bool(self.chk_coment.get()), anonimizar=bool(self.chk_anon.get()),
                       marca=bool(self.chk_marca.get()), fuentes=bool(self.chk_fuentes.get()),
                       tema=tema, csv_sep=";" if self.seg_sep.get().startswith("Punto") else ",",
                       titulo=self.en_titulo.get().strip(),
                       desde=self.dp_desde.get(), hasta=self.dp_hasta.get())
        self.app._ui_prefs["exportar"] = self.pr
        save_ui_prefs(self.app._ui_prefs)
        return tema

    def _exportar(self):
        if str(self.btn_ok.cget("state")) == "disabled":
            return
        EX = self.EX
        fmt = self._formato()
        rows = self._filas()
        if not rows:
            return
        tema = self._guardar_prefs(fmt)
        op = dict(secciones=self._secciones() or [s for s, _ in EX.SECCIONES],
                  comentarios=self.pr["comentarios"], anonimizar=self.pr["anonimizar"],
                  marca=self.pr["marca"], tema=tema, fuentes=self.pr["fuentes"], csv_sep=self.pr["csv_sep"])
        try:
            D = EX.armar(rows, titulo=self.pr["titulo"] or "Reporte de operativa",
                         periodo=self._periodo_texto(rows),
                         filtros=self._filtros_texto(op["anonimizar"]), opciones=op)
        except Exception as e:
            CTX.log.exception("Exportar: armar")
            self._error(f"No se pudo preparar el reporte: {e}")
            return
        ext = next(e for k, _, e in EX.FORMATOS if k == fmt)
        nombre = next(n for k, n, _ in EX.FORMATOS if k == fmt)
        ruta = filedialog.asksaveasfilename(
            parent=self, defaultextension=ext, initialfile=EX.nombre_sugerido(D, ext),
            initialdir=self.pr.get("carpeta") or os.path.expanduser("~"),
            filetypes=[(nombre, "*" + ext)], title="Guardar reporte")
        if not ruta:
            return
        self.btn_ok.configure(state="disabled", text="Generando…")
        self.lbl_estado.configure(text="", text_color=POS_TXT)
        self.update_idletasks()
        try:
            EX.exportar(fmt, D, ruta)
        except EX.ExportError as e:
            self._error(str(e))
            return
        except Exception as e:
            CTX.log.exception("Exportar: escribir")
            self._error(f"No se pudo guardar el archivo: {e}")
            return
        finally:
            self.btn_ok.configure(text="Exportar…")
            self._actualizar()
        self.pr["carpeta"] = os.path.dirname(ruta)
        self.app._ui_prefs["exportar"] = self.pr
        save_ui_prefs(self.app._ui_prefs)
        self.ruta_ok = ruta
        self.lbl_estado.configure(text=f"Listo: {os.path.basename(ruta)}", text_color=POS_TXT)
        self._mostrar_post(True)

    def _error(self, msg):
        self.btn_ok.configure(text="Exportar…")
        self._actualizar()
        self.lbl_estado.configure(text=msg, text_color=NEG_TXT)

    def _mostrar_post(self, v):
        if v:
            self.btn_carpeta.pack(side="left")
            self.btn_abrir.pack(side="left", padx=(0, SP_SM))
            self.btn_carpeta.pack_configure(padx=(0, SP_SM))
        else:
            self.btn_abrir.pack_forget()
            self.btn_carpeta.pack_forget()

    def _abrir(self):
        if not self.ruta_ok:
            return
        try:
            if sys.platform == "win32":
                os.startfile(self.ruta_ok)
            else:
                subprocess.Popen(["xdg-open", self.ruta_ok])
        except Exception as e:
            self._error(f"No pude abrir el archivo: {e}")

    def _carpeta(self):
        if not self.ruta_ok:
            return
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(self.ruta_ok)])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(self.ruta_ok)])
        except Exception as e:
            self._error(f"No pude abrir la carpeta: {e}")

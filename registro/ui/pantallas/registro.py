"""Pantalla(s) de la app como Mixin de App (_build_registro, _render_equity, _toggle_equity…)."""
import os

from PIL import Image
from tkinter import messagebox, ttk
import customtkinter as ctk

from registro.db import db_all, db_delete, get_cuenta_global, get_periodo_global, merged_values
from registro.stats import compute_stats, op_check_counts
from registro.ui import vivo
from registro.ui.capturas import load_thumb
from registro.ui.disposicion import MIN_FILAS_TABLA, plan_columnas
from registro.ui.estado import BASE_DIR, CTX, DPI_SISTEMA, save_ui_prefs
from registro.ui.tema import (
    BLUE, BLUE_HI, BORDER_W, CAUTION, F_NEG, F_POS, FONT_MAIN, FONT_MONO, FONT_SERIF, INK,
    LINE, LINE2, MUTED, MUTED2, NEG, NEG_TXT, ON_BLUE, PAPER, POS, POS_TXT, RAD_CARD, RAD_CTRL,
    SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SURFACE, SURFACE2, T_LOSS, T_WIN)
from registro.ui.util import _fmt_precio, _fmt_usd
from registro.ui.ventanas import centrar_existente
from registro.ui.widgets import btn_ghost, btn_primary, DatePicker, styled_combo

vivo.registrar(globals())


class RegistroMixin:
    # columnas visibles según el ancho (ver registro/ui/disposicion.py)
    _cols_con_datos = None
    _firma_cols = None

    def _pagina_con_scroll(self, parent):
        """Contenedor con scroll vertical: si la ventana es baja la página se desplaza en vez de
        recortar la tabla. La tabla y el panel de detalle conservan su propio scroll con la rueda.
        Devuelve el frame donde va el contenido."""
        import tkinter as tk
        cont = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        cont.pack(fill="both", expand=True)
        canvas = tk.Canvas(cont, highlightthickness=0, bd=0, bg=INK, yscrollincrement=40)
        vsb = ctk.CTkScrollbar(cont, command=canvas.yview, fg_color="transparent",
                               button_color=LINE2, button_hover_color=MUTED2)
        canvas.pack(side="left", fill="both", expand=True)
        inner = ctk.CTkFrame(canvas, fg_color="transparent", corner_radius=0)
        item = canvas.create_window(0, 0, window=inner, anchor="nw")
        visible = [False]

        def set_scroll(lo, hi):
            vsb.set(lo, hi)
            hace_falta = not (float(lo) <= 0.0 and float(hi) >= 1.0)
            if hace_falta != visible[0]:       # la barra aparece solo cuando la página no entra
                visible[0] = hace_falta
                if hace_falta:
                    vsb.pack(side="right", fill="y", before=canvas)
                else:
                    vsb.pack_forget()
        canvas.configure(yscrollcommand=set_scroll)

        def ajustar(_e=None):
            ancho, alto = canvas.winfo_width(), canvas.winfo_height()
            if ancho < 10 or alto < 10:
                return
            necesario = inner.winfo_reqheight()
            # si el contenido entra, ocupa todo el alto (la tabla crece); si no, tamaño natural + scroll
            canvas.itemconfigure(item, width=ancho, height=max(alto, necesario))
            canvas.configure(scrollregion=(0, 0, ancho, max(alto, necesario)))
        canvas.bind("<Configure>", ajustar)
        inner.bind("<Configure>", ajustar, add="+")
        self._ajustar_pagina = ajustar
        self._pag_canvas = canvas

        def rueda(e):
            if not canvas.winfo_ismapped():
                return
            w = self.winfo_containing(e.x_root, e.y_root)
            if w is None or not self._dentro_de(w, canvas):
                return
            if self._dentro_de(w, self.tree) or self._dentro_de(w, self.detail):
                return                         # la tabla y el detalle se desplazan solos
            canvas.yview_scroll(-2 if e.delta > 0 else 2, "units")
        self.bind_all("<MouseWheel>", rueda, add="+")
        return inner

    @staticmethod
    def _dentro_de(widget, ancestro):
        while widget is not None:
            if widget is ancestro:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _build_registro(self):
        page = self._pagina_con_scroll(self.tab_registro)
        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(fill="x", pady=(6,12))

        def col(label):
            c = ctk.CTkFrame(top, fg_color="transparent")
            c.pack(side="left", padx=(0, SP_MD), anchor="s")
            self._lbl(c, label).pack(anchor="w", pady=(0, SP_XS))
            return c

        c = col("Desde")
        self.flt_desde = DatePicker(c, width=112)
        self.flt_desde.pack()
        c = col("Hasta")
        self.flt_hasta = DatePicker(c, width=112)
        self.flt_hasta.pack()
        c = col("Tipo")
        self.flt_tipo = styled_combo(c, ["Todos"]+merged_values(CTX.perfil.tipos, "tipo"),
                                     width=130, default="Todos")
        self.flt_tipo.pack()
        c = col("Cuenta")
        self.flt_cuenta = styled_combo(c, ["Todas"]+list(CTX.perfil.tipos_cuenta), width=120, default="Todas")
        self.flt_cuenta.pack()
        c = col("Emo")
        self.flt_emo = styled_combo(c, ["Todos","1","2","3","4","5"], width=84, default="Todos")
        self.flt_emo.pack()

        btns = ctk.CTkFrame(top, fg_color="transparent")
        btns.pack(side="left", padx=(SP_XS, 0), anchor="s")
        btn_primary(btns, "Aplicar", self.render_table, width=92, height=34).pack(side="left", padx=(0, SP_SM))
        btn_ghost(btns, "Limpiar", self.clear_filters, width=92, height=34).pack(side="left")

        # ---- barra de KPIs (resumen del set filtrado, siempre visible) ----
        self.kpi_bar = ctk.CTkFrame(page, fg_color="transparent")
        self.kpi_bar.pack(fill="x", pady=(0, SP_XL), padx=(0, 2))

        # ---- equity curve (P&L acumulado en el tiempo, dibujada a mano) ----
        self.equity_wrap = ctk.CTkFrame(page, fg_color=SURFACE, corner_radius=RAD_CARD)
        self.equity_wrap.pack(fill="x", pady=(0, SP_XL), padx=(0, 2))
        self.equity_canvas = None

        # ---- tabla nativa (ttk.Treeview) + panel de detalle ----
        # Antes cada fila eran ~20 widgets CTk (cada uno un Canvas redibujando
        # esquinas): con 70+ ops eran miles de objetos y el render se arrastraba.
        # El Treeview dibuja todas las filas en un solo widget -> instantáneo.
        body = ctk.CTkFrame(page, fg_color="transparent")
        body.pack(fill="both", expand=True)
        self._build_tree(body)
        # si el contenido cambia de alto, la página recalcula su zona de scroll
        for w in (top, self.kpi_bar, self.equity_wrap, body):
            w.bind("<Configure>", self._ajustar_pagina, add="+")

    def _render_equity(self, rows):
        """Curva de equity (P&L acumulado) sobre el set filtrado, ordenado por fecha+hora.
        Dibujada en un tkinter.Canvas para no depender de matplotlib."""
        import tkinter as tk
        self._equity_rows = rows
        for w in self.equity_wrap.winfo_children():
            w.destroy()
        if self._equity_redraw_job is not None:
            try:
                self.after_cancel(self._equity_redraw_job)
            except Exception:
                pass
            self._equity_redraw_job = None
        collapsed = self._equity_collapsed

        ops = [o for o in rows if o.get("profit") is not None]
        ops.sort(key=lambda o: (o.get("fecha") or "", o.get("hora") or ""))

        # encabezado clickeable: colapsa/expande la curva (se recuerda entre sesiones)
        head = ctk.CTkFrame(self.equity_wrap, fg_color="transparent", cursor="hand2")
        head.pack(fill="x", padx=16, pady=(12, 12 if collapsed else 0))
        title = ctk.CTkLabel(head, text=("▸  " if collapsed else "▾  ") + "CURVA DE EQUITY",
                             font=(FONT_MAIN, 10), text_color=MUTED, anchor="w", cursor="hand2")
        title.pack(side="left")
        hint = ctk.CTkLabel(head, text=("mostrar" if collapsed else "ocultar"),
                            font=(FONT_MAIN, 10), text_color=MUTED2, anchor="w", cursor="hand2")
        hint.pack(side="left", padx=(SP_SM, 0))
        if len(ops) >= 2:
            final = sum(o["profit"] or 0 for o in ops)
            summ = ctk.CTkLabel(head, text=f"{'+' if final>=0 else ''}{final:.0f} USD acumulado · {len(ops)} ops",
                         font=(FONT_MONO, 10),
                         text_color=(POS_TXT if final >= 0 else NEG_TXT),
                         anchor="e", cursor="hand2")
            summ.pack(side="right")
            summ.bind("<Button-1>", lambda e: self._toggle_equity())
        for w in (head, title, hint):
            w.bind("<Button-1>", lambda e: self._toggle_equity())
            w.bind("<Enter>", lambda e, h=hint: h.configure(text_color=PAPER))
            w.bind("<Leave>", lambda e, h=hint: h.configure(text_color=MUTED2))

        if collapsed:
            return

        if len(ops) < 2:
            ctk.CTkLabel(self.equity_wrap,
                         text="Necesitás al menos 2 operaciones para trazar la curva.",
                         font=(FONT_MAIN, 12), text_color=MUTED).pack(padx=16, pady=(6, 16))
            return

        H = int(160 * DPI_SISTEMA)   # no crece con el tamaño elegido
        canvas = tk.Canvas(self.equity_wrap, height=H, bg=SURFACE,
                           highlightthickness=0, bd=0)
        canvas.pack(fill="x", expand=True, padx=16, pady=(6, 16))
        self.equity_canvas = canvas
        if self._equity_redraw_job is not None:
            try:
                self.after_cancel(self._equity_redraw_job)
            except Exception:
                pass
        self._equity_redraw_job = None

        # El ancho real se conoce recién al mapear el widget -> dibujamos on-resize.
        # Debounce: al mover entre monitores llegan eventos <Configure> en ráfaga
        # mientras CTk reescala. Redibujar en cada uno colgaba la ventana; ahora
        # esperamos ~80ms a que se asiente y dibujamos una sola vez.
        def _on_configure(e, c=canvas, o=ops):
            if self._equity_redraw_job is not None:
                try:
                    self.after_cancel(self._equity_redraw_job)
                except Exception:
                    pass
            w, h = e.width, e.height
            if h < 40:          # evento intermedio mientras se reacomoda
                return
            self._equity_redraw_job = self.after(
                80, lambda: self._draw_equity(c, o, w, h))
        canvas.bind("<Configure>", _on_configure)

    def _toggle_equity(self):
        self._equity_collapsed = not self._equity_collapsed
        self._ui_prefs["equity_collapsed"] = self._equity_collapsed
        save_ui_prefs(self._ui_prefs)
        self._render_equity(self._equity_rows)

    def _draw_equity(self, canvas, ops, W, H):
        if not canvas.winfo_exists():   # la tabla se re-renderizó mientras tanto
            return
        canvas.delete("all")
        if W < 40:
            return
        sc = self._ws()
        pad_l, pad_r, pad_t, pad_b = int(8 * sc), int(8 * sc), int(14 * sc), int(18 * sc)
        fnt = (FONT_MONO, max(7, round(8 * self.factor)))

        # serie acumulada, arrancando en 0 (línea base = capital inicial relativo)
        cum, running = [0.0], 0.0
        for o in ops:
            running += o["profit"] or 0
            cum.append(running)
        lo, hi = min(cum), max(cum)
        if hi == lo:
            hi += 1; lo -= 1
        span = hi - lo

        plot_w = W - pad_l - pad_r
        plot_h = H - pad_t - pad_b

        def X(i): return pad_l + (plot_w * i / (len(cum) - 1))
        def Y(v): return pad_t + plot_h * (1 - (v - lo) / span)

        # línea del cero (breakeven) si el rango la cruza
        if lo <= 0 <= hi:
            y0 = Y(0)
            canvas.create_line(pad_l, y0, W - pad_r, y0, fill=LINE2, dash=(3, 3))
            canvas.create_text(pad_l + 2, y0 - 8, text="0", anchor="w",
                               fill=MUTED2, font=fnt)

        # máximo y mínimo como referencia
        canvas.create_text(W - pad_r, Y(hi) - 2, text=self._m(hi), anchor="se",
                           fill=MUTED, font=fnt)
        canvas.create_text(W - pad_r, Y(lo) + 2, text=self._m(lo), anchor="ne",
                           fill=MUTED, font=fnt)

        pts = [(X(i), Y(v)) for i, v in enumerate(cum)]

        # relleno suave bajo la curva (hacia la línea base 0 o el piso)
        base_y = Y(0) if lo <= 0 <= hi else Y(lo)
        final_pos = cum[-1] >= 0
        fill_col = F_POS if final_pos else F_NEG
        poly = [pad_l, base_y] + [c for p in pts for c in p] + [W - pad_r, base_y]
        canvas.create_polygon(poly, fill=fill_col, outline="")

        # segmentos coloreados según suban o bajen respecto al punto previo
        for i in range(1, len(pts)):
            up = cum[i] >= cum[i - 1]
            canvas.create_line(pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1],
                               fill=(POS_TXT if up else NEG_TXT), width=2)

        # punto final destacado
        fx, fy = pts[-1]
        dot = POS_TXT if final_pos else NEG_TXT
        canvas.create_oval(fx - 3, fy - 3, fx + 3, fy + 3, fill=dot, outline=SURFACE)

        # tooltip al pasar el mouse: fecha, trade y acumulado en ese punto
        canvas._eq = dict(pts=pts, cum=cum, ops=ops, W=W, H=H, pad_t=pad_t,
                          pad_b=pad_b, sc=sc, fnt=fnt)
        canvas.bind("<Motion>", lambda e, c=canvas: self._equity_hover(c, e.x))
        canvas.bind("<Leave>", lambda e, c=canvas: c.delete("tip"))

    def _equity_hover(self, canvas, mx):
        d = getattr(canvas, "_eq", None)
        if not d or not canvas.winfo_exists():
            return
        pts = d["pts"]
        i = min(range(len(pts)), key=lambda k: abs(pts[k][0] - mx))
        x, y = pts[i]
        cum, ops, W, sc, fnt = d["cum"], d["ops"], d["W"], d["sc"], d["fnt"]
        canvas.delete("tip")
        top, bot = d["pad_t"] - int(6 * sc), d["H"] - d["pad_b"] + int(4 * sc)
        canvas.create_line(x, top, x, bot, fill=LINE2, tags="tip")
        col = POS_TXT if cum[i] >= 0 else NEG_TXT
        canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=col, outline=SURFACE, width=2, tags="tip")
        if i == 0:
            lineas = [("Inicio", MUTED), ("0.00", PAPER)]
        else:
            o = ops[i - 1]
            p = o["profit"] or 0
            lineas = [(f"{o['fecha']}  {o['hora'] or ''}".strip(), MUTED),
                      (f"{o['activo'] or '—'}   {p:+,.2f}", POS_TXT if p >= 0 else NEG_TXT),
                      (f"Acumulado  {cum[i]:+,.2f}", PAPER)]
        pad = int(8 * sc)
        lh = int(15 * sc)
        tw = max(len(t) for t, _c in lineas) * int(7 * sc) + 2 * pad
        th = lh * len(lineas) + 2 * pad - int(4 * sc)
        bx = x + int(12 * sc)
        if bx + tw > W - 4:
            bx = x - int(12 * sc) - tw
        by = max(2, min(y - th // 2, d["H"] - th - 2))
        canvas.create_rectangle(bx, by, bx + tw, by + th, fill=SURFACE2, outline=LINE2, tags="tip")
        for k, (t, c) in enumerate(lineas):
            canvas.create_text(bx + pad, by + pad + k * lh, text=t, anchor="nw",
                               fill=c, font=fnt, tags="tip")

    def _render_kpis(self, rows):
        for w in self.kpi_bar.winfo_children():
            w.destroy()
        s = compute_stats(rows)

        def card(label, value, value_color=PAPER, sub=None, sub_color=MUTED, accent=BLUE):
            card = ctk.CTkFrame(self.kpi_bar, fg_color=SURFACE, corner_radius=RAD_CARD,
                                width=60, height=96)
            card.pack(side="left", expand=True, fill="x", padx=SP_XS)
            card.pack_propagate(False)
            strip = ctk.CTkFrame(card, fg_color=accent, width=3, corner_radius=2)
            strip.pack(side="left", fill="y")
            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(side="left", expand=True, fill="both")
            ctk.CTkLabel(body, text=label.upper(), font=(FONT_MAIN, 10),
                         text_color=MUTED, anchor="w").pack(anchor="w", padx=SP_LG, pady=(SP_LG, 0))
            # valor en serif: le da el aire editorial de marca (igual que los headers)
            ctk.CTkLabel(body, text=value, font=(FONT_SERIF, 28),
                         text_color=value_color, anchor="w").pack(anchor="w", padx=SP_LG, pady=(SP_XS, 0))
            ctk.CTkLabel(body, text=(sub or " "), font=(FONT_MONO, 10),
                         text_color=sub_color, anchor="w").pack(anchor="w", padx=SP_LG, pady=(SP_XS, SP_MD))

        if s["n"] == 0:
            card("Operaciones", "0", MUTED, "sin datos en el filtro", accent=LINE2)
            return

        pnl_col = POS_TXT if s["pnl"] >= 0 else NEG_TXT
        card("P&L acumulado", self._m(s["pnl"]),
             pnl_col, "USD" if not self._en_pct() else "del capital inicial", accent=(POS if s["pnl"] >= 0 else NEG))

        wr_col = POS_TXT if s["wr"] >= 50 else (CAUTION if s["wr"] >= 40 else NEG_TXT)
        card("Win rate", f"{s['wr']}%", wr_col,
             f"{s['wins']}W · {s['losses']}L", accent=BLUE)

        card("Operaciones", str(s["n"]), PAPER,
             f"mejor {self._m(s['best'])} · peor {self._m(s['worst'])}", accent=BLUE)

        if s["streak_sign"] > 0:
            st_txt, st_col, st_acc = f"{s['streak']}", POS_TXT, POS
            st_sub = "ganadas seguidas"
        elif s["streak_sign"] < 0:
            st_txt, st_col, st_acc = f"{s['streak']}", NEG_TXT, NEG
            st_sub = "perdidas seguidas"
        else:
            st_txt, st_col, st_acc, st_sub = "—", MUTED, LINE2, "sin racha"
        card("Racha actual", st_txt, st_col, st_sub, accent=st_acc)

        if s.get("chk_n", 0) == 0:
            card("Disciplina", "—", MUTED, "sin checklist cargado", accent=LINE2)
        else:
            chk_col = POS_TXT if s["chk_pct"] >= 80 else (CAUTION if s["chk_pct"] >= 50 else NEG_TXT)
            card("Disciplina", f"{s['chk_pct']}%", chk_col,
                 f"{s['chk_n']} ops con check", accent=chk_col)

        if s["avg_emo"] is not None:
            emo_col = self._emo_color(round(s["avg_emo"]))
            card("Emo prom.", f"{s['avg_emo']:.1f}", emo_col, "/ 5", accent=emo_col)
        else:
            card("Emo prom.", "—", MUTED, "sin registro", accent=LINE2)

    def clear_filters(self):
        self.flt_desde.delete(0,"end"); self.flt_hasta.delete(0,"end")
        self.flt_tipo.set("Todos"); self.flt_cuenta.set("Todas"); self.flt_emo.set("Todos")
        self.render_table()

    def _current_filters(self):
        f = {}
        if self.flt_desde.get().strip(): f["desde"] = self.flt_desde.get().strip()
        if self.flt_hasta.get().strip(): f["hasta"] = self.flt_hasta.get().strip()
        if self.flt_tipo.get() != "Todos": f["tipo"] = self.flt_tipo.get()
        if self.flt_cuenta.get() != "Todas": f["cuenta"] = self.flt_cuenta.get()
        if self.flt_emo.get() != "Todos": f["emo"] = self.flt_emo.get()
        return f

    def render_table(self, force=True):
        # Firma del estado visible: filtros + columna/orden. Si nada cambió y
        # no hay datos nuevos, salimos sin reconstruir (clave al cambiar de tab).
        sig = (tuple(sorted(self._current_filters().items())),
               self.sort_col, self.sort_desc)
        if not force and not self._table_dirty and sig == self._last_render_sig:
            return
        self._last_render_sig = sig
        self._table_dirty = False

        self._thumbs.clear()
        # el filtro de tipo también aprende de los tipos usados
        if hasattr(self, "flt_tipo"):
            cur = self.flt_tipo.get()
            self.flt_tipo.configure(values=["Todos"]+merged_values(CTX.perfil.tipos, "tipo"))
            if cur:
                self.flt_tipo.set(cur)
        rows = db_all(self._current_filters())
        self._render_kpis(rows)
        self._render_equity(rows)
        if self.sort_col == "_chk":
            rows.sort(key=lambda o: op_check_counts(o)[0], reverse=self.sort_desc)
        else:
            rows.sort(key=lambda o: (o.get(self.sort_col) is None, o.get(self.sort_col)),
                      reverse=self.sort_desc)

        tree = self.tree
        prev_sel = tree.selection()
        prev_id = prev_sel[0] if prev_sel else None
        tree.delete(*tree.get_children())
        self._rows_by_id = {}

        # flechita de orden en el encabezado activo
        for col, label, _w, _a in self.TREE_COLS:
            arrow = ("  ↓" if self.sort_desc else "  ↑") if self.sort_col == col else ""
            tree.heading(col, text=label + arrow)

        vistos = set()      # columnas con algún dato real (el resto se oculta)
        for idx, o in enumerate(rows):
            pnl_val = o["profit"] or 0
            n_chk, tot_chk = op_check_counts(o)
            psign = "+" if pnl_val >= 0 else ""
            caps = ("◧" if o["img_ini"] else "·") + ("◨" if o["img_fin"] else "·")
            coment = (o["comentario"] or "").replace("\n", " ").strip()
            res = "win" if pnl_val > 0 else ("loss" if pnl_val < 0 else "flat")
            zebra = "a" if idx % 2 == 0 else "b"
            iid = str(o["id"])
            self._rows_by_id[iid] = o
            tree.insert("", "end", iid=iid, tags=(f"{res}_{zebra}",), values=(
                o["fecha"], o["hora"] or "—", o["activo"] or "—", o["tipo"] or "—",
                f"{psign}{pnl_val:.2f}", o["empresa"] or "—", o["cuenta"] or "—",
                o["mov_sl"] or "—", self._emo_str(o["emo"]),
                f"{n_chk}/{tot_chk}" if tot_chk else "—", caps, coment))
            vals = tree.item(iid, "values")
            for (col, *_r), v in zip(self.TREE_COLS, vals):
                if str(v) not in ("—", "··", ""):
                    vistos.add(col)

        # ocultar columnas sin datos (en una importación casi todo viene vacío)
        siempre = {"fecha", "hora", "activo", "profit", "empresa", "cuenta"}
        visibles = [c[0] for c in self.TREE_COLS if c[0] in siempre or c[0] in vistos]
        self._cols_con_datos = visibles
        self._firma_cols = None
        self._ajustar_columnas()

        # estado vacío
        if rows:
            self.empty_box.place_forget()
        else:
            if self._current_filters() or get_cuenta_global() or get_periodo_global():
                self.empty_tit.configure(text="Sin resultados")
                self.empty_txt.configure(text="Ninguna operación coincide con el filtro.")
                self.empty_btn.pack_forget()
            else:
                self.empty_tit.configure(text="Todavía no hay operaciones")
                self.empty_txt.configure(text="Importá tus trades desde NinjaTrader, MT5,\nTradovate o TopstepX, o cargalos a mano.")
                self.empty_btn.pack()
            self.empty_box.place(relx=0.5, rely=0.5, anchor="center")
            self.empty_box.lift()

        if prev_id and prev_id in self._rows_by_id:
            tree.selection_set(prev_id); tree.see(prev_id)
        else:
            self._show_detail(None, empty=not rows)

    TREE_COLS = [  # (clave, título, ancho, anchor)
        ("fecha", "Fecha", 92, "w"), ("hora", "Hora", 56, "w"),
        ("activo", "Activo", 58, "w"), ("tipo", "Tipo", 88, "w"),
        ("profit", "Profit", 84, "e"), ("empresa", "Empresa", 128, "w"),
        ("cuenta", "Cuenta", 104, "w"), ("mov_sl", "SL", 96, "w"),
        ("emo", "Emo", 66, "w"), ("_chk", "Check", 56, "center"),
        ("_caps", "Caps", 46, "center"), ("comentario", "Comentario", 180, "w"),
    ]

    def _ws(self):
        """Escala real de los widgets (tamaño elegido x escala de pantalla)."""
        try:
            return self._get_widget_scaling()
        except Exception:
            return self.factor * DPI_SISTEMA

    def _estilo_tree(self):
        """Estilo del Treeview (ttk no lo escala CustomTkinter: lo hacemos acá)."""
        scale = self._ws()
        fs, fh = max(7, round(10 * self.factor)), max(7, round(9 * self.factor))
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("Gabo.Treeview", background=SURFACE, fieldbackground=SURFACE,
                     foreground=PAPER, bordercolor=LINE, lightcolor=SURFACE,
                     darkcolor=SURFACE, borderwidth=0, rowheight=int(30 * scale),
                     font=(FONT_MAIN, fs))
        st.map("Gabo.Treeview", background=[("selected", BLUE)],
               foreground=[("selected", ON_BLUE)])
        st.configure("Gabo.Treeview.Heading", background=INK, foreground=MUTED,
                     bordercolor=LINE, lightcolor=INK, darkcolor=INK, relief="flat",
                     font=(FONT_MAIN, fh), padding=(6, 6))
        st.map("Gabo.Treeview.Heading", background=[("active", SURFACE)],
               foreground=[("active", PAPER)])
        st.layout("Gabo.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    def _ancho_columnas_tree(self):
        scale = self._ws()
        for col, _label, w, _a in self.TREE_COLS:
            self.tree.column(col, width=int(w * scale), minwidth=int(40 * scale))
        self._firma_cols = None
        self._ajustar_columnas()

    # ---------- columnas según el ancho disponible ----------
    def _ajustar_columnas(self):
        """Muestra las columnas que entran en el ancho actual (ver disposicion.plan_columnas)."""
        cols = self._cols_con_datos
        if not cols:
            return
        base = {c: w for c, _l, w, _a in self.TREE_COLS}
        escala = self._ws()
        ancho = self.tree.winfo_width() - 4
        if ancho < 150:          # todavía sin mapear: se muestran todas con su ancho nominal
            mostrar, anchos = list(cols), {c: int(w * escala) for c, w in base.items()}
        else:
            mostrar, anchos = plan_columnas(ancho, cols, base, escala)
        firma = (tuple(mostrar), tuple(sorted(anchos.items())))
        if firma == self._firma_cols:
            return
        self._firma_cols = firma
        self.tree["displaycolumns"] = mostrar
        for col, w in anchos.items():
            self.tree.column(col, width=w, stretch=(col == mostrar[-1]))

    def _build_tree(self, parent):
        self._estilo_tree()
        scale = self._ws()

        # ancho "pedido" chico + sin propagación: la tabla se achica antes de
        # aplastar el panel de detalle (si no, con ventanas angostas el detalle
        # queda cortado).
        # alto mínimo: MIN_FILAS_TABLA filas + encabezado (si la ventana es más baja, scrollea la página)
        alto_min = MIN_FILAS_TABLA * 30 + 28 + 2 * SP_SM + 8
        wrap = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=RAD_CARD, width=300,
                            height=alto_min)
        wrap.pack(side="left", fill="both", expand=True)
        wrap.pack_propagate(False)
        inner = ctk.CTkFrame(wrap, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SP_SM, pady=SP_SM)

        cols = [c[0] for c in self.TREE_COLS]
        tree = ttk.Treeview(inner, columns=cols, show="headings",
                            style="Gabo.Treeview", selectmode="browse")
        for col, label, w, anchor in self.TREE_COLS:
            sortable = col not in ("_caps", "comentario")
            tree.heading(col, text=label, anchor="w" if anchor == "w" else anchor,
                         command=(lambda c=col: self._set_sort(c)) if sortable else "")
            tree.column(col, width=int(w * scale), minwidth=int(40 * scale), anchor=anchor,
                        stretch=(col == "comentario"))
        # color por resultado (tinte sutil) + zebra
        tints = {"win": T_WIN, "loss": T_LOSS,
                 "flat": (SURFACE, SURFACE2)}
        fgs = {"win": POS_TXT, "loss": NEG_TXT, "flat": MUTED}
        for res, (a, b) in tints.items():
            tree.tag_configure(f"{res}_a", background=a, foreground=fgs[res])
            tree.tag_configure(f"{res}_b", background=b, foreground=fgs[res])

        sb = ctk.CTkScrollbar(inner, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

        # estado vacío (se muestra encima de la tabla cuando no hay filas)
        self.empty_box = ctk.CTkFrame(wrap, fg_color="transparent")
        self.empty_tit = ctk.CTkLabel(self.empty_box, text="", font=(FONT_SERIF, 24),
                                      text_color=PAPER)
        self.empty_tit.pack()
        self.empty_txt = ctk.CTkLabel(self.empty_box, text="", font=(FONT_MAIN, 12),
                                      text_color=MUTED, justify="center")
        self.empty_txt.pack(pady=(SP_XS, SP_LG))
        self.empty_btn = btn_primary(self.empty_box, "Importar trades", self.abrir_importar,
                                     width=160, height=36)
        self.empty_btn.pack()

        tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        tree.bind("<Double-1>", self._on_tree_double)
        tree.bind("<Return>", self._on_tree_double)
        tree.bind("<Delete>", lambda e: self._del_selected())
        tree.bind("<Configure>", lambda e: self._ajustar_columnas(), add="+")
        self.tree = tree
        self._rows_by_id = {}

        self.detail = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=RAD_CARD,
                                   width=300)
        self.detail.pack(side="left", fill="y", padx=(SP_MD, 2))
        self.detail.pack_propagate(False)
        self._show_detail(None)

    def _selected_op(self):
        sel = self.tree.selection()
        return self._rows_by_id.get(sel[0]) if sel else None

    def _on_tree_select(self, _e=None):
        self._show_detail(self._selected_op())

    def _on_tree_double(self, e=None):
        # doble click sobre el encabezado = ordenar, no editar
        if e is not None and getattr(e, "x", None) is not None and \
                self.tree.identify_region(e.x, e.y) == "heading":
            return
        op = self._selected_op()
        if op: self.edit_op(op)

    def _del_selected(self):
        op = self._selected_op()
        if op: self._del(op["id"])

    def _show_detail(self, o, empty=False):
        d = self.detail
        for w in d.winfo_children():
            w.destroy()
        if o is None:
            msg = ("" if empty else "Seleccioná una operación\npara ver el detalle.\n\n"
                                 "Doble click → editar\nSupr → borrar")
            ctk.CTkLabel(d, text=msg, text_color=MUTED, font=(FONT_MAIN, 12),
                         justify="center").pack(expand=True)
            return
        pad = SP_LG
        bar = ctk.CTkFrame(d, fg_color="transparent")
        bar.pack(side="bottom", fill="x", padx=pad, pady=(SP_SM, pad))
        ctk.CTkButton(bar, text="Editar", width=120, height=30, fg_color=BLUE,
                      hover_color=BLUE_HI, text_color=ON_BLUE, font=(FONT_MAIN, 12),
                      command=lambda op=o: self.edit_op(op)).pack(side="left")
        ctk.CTkButton(bar, text="Borrar", width=120, height=30, fg_color="transparent",
                      border_color=LINE2, border_width=1, text_color=NEG_TXT, hover_color=INK,
                      font=(FONT_MAIN, 12),
                      command=lambda i=o["id"]: self._del(i)).pack(side="right")
        d = ctk.CTkScrollableFrame(d, fg_color="transparent")
        d.pack(fill="both", expand=True, padx=(0, 2), pady=(SP_XS, 0))
        pad = SP_MD
        pnl_val = o["profit"] or 0
        pcol = POS_TXT if pnl_val >= 0 else NEG_TXT
        ctk.CTkLabel(d, text=f"#{o['id']} · {o['fecha']} {o['hora'] or ''}".strip(),
                     font=(FONT_MONO, 11), text_color=MUTED).pack(anchor="w", padx=pad, pady=(pad, 0))
        ctk.CTkLabel(d, text=f"{o['activo'] or '—'} · {o['tipo'] or '—'}",
                     font=(FONT_MAIN, 15), text_color=PAPER).pack(anchor="w", padx=pad)
        ctk.CTkLabel(d, text=f"{'+' if pnl_val>=0 else ''}{pnl_val:.2f} USD",
                     font=(FONT_SERIF, 30), text_color=pcol).pack(anchor="w", padx=pad, pady=(0, SP_SM))

        n_chk, tot_chk = op_check_counts(o)
        info = [("Empresa", o["empresa"] or "—"), ("Cuenta", o["cuenta"] or "—"),
                ("Mov. SL", o["mov_sl"] or "—"), ("Tranquilo", o.get("tranquilo") or "—"),
                ("Emo", self._emo_str(o["emo"])),
                ("Check", f"{n_chk}/{tot_chk}" if tot_chk else "—")]
        # lo que no se cargó (típico en trades importados) no ocupa lugar
        info = [(k, v) for k, v in info if v != "—" or k in ("Empresa", "Cuenta")]
        grid = ctk.CTkFrame(d, fg_color="transparent"); grid.pack(fill="x", padx=pad)
        for i, (k, v) in enumerate(info):
            ctk.CTkLabel(grid, text=k.upper(), font=(FONT_MAIN, 9), text_color=MUTED2,
                         anchor="w").grid(row=i, column=0, sticky="w", pady=1)
            col = self._emo_color(o["emo"]) if k == "Emo" else PAPER
            ctk.CTkLabel(grid, text=v, font=(FONT_MAIN, 11), text_color=col,
                         anchor="w").grid(row=i, column=1, sticky="w", padx=(SP_MD, 0), pady=1)

        if o.get("fuente") and o["fuente"] != "manual":
            nombres = {"nt8": "NinjaTrader", "mt4": "MetaTrader 4", "mt5": "MetaTrader 5",
                       "tradovate": "Tradovate", "topstepx": "TopstepX", "deepcharts": "DeepCharts"}
            imp_rows = [("Origen", nombres.get(o["fuente"], o["fuente"])),
                        ("Lado", f"{o.get('lado') or '—'} · {o['contratos']:g}" if o.get("contratos") else (o.get("lado") or "—")),
                        ("Entrada", _fmt_precio(o["precio_ini"]) if o.get("precio_ini") is not None else "—"),
                        ("Salida", (_fmt_precio(o["precio_fin"]) if o.get("precio_fin") is not None else "—")
                                   + (f"  ({o['hora_fin'][-5:]})" if o.get("hora_fin") else "")
                                   + (f" · {o['motivo_cierre']}" if o.get("motivo_cierre") else "")),
                        ("Bruto", _fmt_usd(o.get("bruto"), True)),
                        ("Costo", _fmt_usd(o.get("comision")))]
            card = ctk.CTkFrame(d, fg_color=SURFACE2, corner_radius=RAD_CTRL,
                                border_color=LINE, border_width=BORDER_W)
            card.pack(fill="x", padx=pad, pady=(SP_MD, 0))
            ctk.CTkLabel(card, text="IMPORTADO · " + nombres.get(o["fuente"], o["fuente"]).upper(),
                         font=(FONT_MAIN, 9), text_color=MUTED).pack(
                             anchor="w", padx=SP_MD, pady=(SP_SM, 0))
            imp_rows = [r for r in imp_rows if r[0] != "Origen" and r[1] != "—"]
            g2 = ctk.CTkFrame(card, fg_color="transparent"); g2.pack(fill="x", padx=SP_MD, pady=(SP_XS, SP_SM))
            for i, (k, v) in enumerate(imp_rows):
                ctk.CTkLabel(g2, text=k.upper(), font=(FONT_MAIN, 9), text_color=MUTED2,
                             anchor="w").grid(row=i, column=0, sticky="w", pady=1)
                ctk.CTkLabel(g2, text=v, font=(FONT_MONO, 11), text_color=PAPER,
                             anchor="w").grid(row=i, column=1, sticky="w", padx=(SP_MD, 0), pady=1)

        if o["comentario"]:
            ctk.CTkLabel(d, text=o["comentario"], font=(FONT_MAIN, 11), text_color=MUTED,
                         wraplength=245, justify="left", anchor="w").pack(
                             anchor="w", fill="x", padx=pad, pady=(SP_MD, 0))

        for lbl_txt, rel in (("INICIO", o["img_ini"]), ("FIN", o["img_fin"])):
            th = load_thumb(rel, (250, 140))
            if not th: continue
            self._thumbs.append(th)
            ctk.CTkLabel(d, text=lbl_txt, font=(FONT_MAIN, 9), text_color=MUTED2).pack(
                anchor="w", padx=pad, pady=(SP_MD, 2))
            im = ctk.CTkLabel(d, image=th, text="", cursor="hand2")
            im.pack(anchor="w", padx=pad)
            im.bind("<Button-1>", lambda e, p=rel: self._open_full(p))

    def _emo_str(self, v): return "●"*(v or 0) + "○"*(5-(v or 0)) if v else "—"

    def _emo_color(self, v):
        if not v: return MUTED2
        return NEG_TXT if v<=2 else (CAUTION if v==3 else POS_TXT)

    def _set_sort(self, col):
        if self.sort_col==col: self.sort_desc = not self.sort_desc
        else: self.sort_col=col; self.sort_desc=True
        self.render_table()

    def _del(self, op_id):
        if messagebox.askyesno("Borrar", "¿Borrar esta operación y sus capturas?"):
            db_delete(op_id); self._table_dirty = True; self.render_table()

    def _open_full(self, rel):
        p = os.path.join(BASE_DIR, rel)
        if not os.path.exists(p): return
        top = ctk.CTkToplevel(self); top.title("Captura"); top.configure(fg_color=INK)
        img = Image.open(p)
        img.thumbnail((1100, 800))
        ci = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        self._thumbs.append(ci)
        ctk.CTkLabel(top, image=ci, text="").pack(padx=10, pady=10)
        centrar_existente(top, self)

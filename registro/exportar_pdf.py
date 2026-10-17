"""Escritor de PDF del reporte (fpdf2, solo Python). Usa las tipografías de marca."""

from .exportar import (ExportError, MARCA_TEXTO, _escribir, _f, columnas_ops, kpis_resumen, kpis_riesgo,
                       tono, usd)
from .paths import resource_path


def _rgb(hexa):
    h = hexa.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def a_pdf(D, ruta):
    try:
        from fpdf import FPDF
        from fpdf.fonts import FontFace
    except ImportError as e:
        raise ExportError(f"Falta el componente de PDF (fpdf2): {e}. Reinstalá la aplicación.")
    if not D["secciones"]:
        raise ExportError("Elegí al menos una sección para exportar.")
    if not D["n"]:
        raise ExportError("No hay operaciones en ese período.")

    P = {k: _rgb(v) for k, v in D["paleta"].items()}
    op, sec = D["opciones"], D["secciones"]
    pintar_fondo = op.get("tema") in ("papel", "oscuro")
    color_tono = {"pos": P["pos"], "neg": P["neg"], "neu": P["text"]}

    class Doc(FPDF):
        def header(self):
            if pintar_fondo:
                self.set_fill_color(*P["bg"])
                self.rect(0, 0, self.w, self.h, style="F")

        def footer(self):
            self.set_y(-11)
            self.set_font("mono", size=6.5)
            self.set_text_color(*P["muted"])
            self.cell(0, 4, (MARCA_TEXTO if op.get("marca") else D["titulo"]), align="L")
            self.set_x(self.l_margin)
            self.cell(0, 4, f"{self.page_no()} / {{nb}}", align="R")

    pdf = Doc("P", "mm", "A4")
    pdf.set_margins(10, 12, 10)
    pdf.set_auto_page_break(True, 16)
    pdf.alias_nb_pages()
    for fam, arch in (("sans", "DMSans-Regular.ttf"), ("serif", "InstrumentSerif-Regular.ttf"),
                      ("mono", "JetBrainsMono-Regular.ttf")):
        try:
            pdf.add_font(fam, fname=resource_path("assets", "fonts", arch))
        except Exception:
            raise ExportError("No encontré las tipografías de la aplicación. Reinstalá el programa.")
    pdf.set_title(D["titulo"])
    pdf.set_author("Registro de operativa")
    pdf.set_creator(f"Registro de operativa {D['version']}")
    pdf.set_subject(D["periodo"] or "Reporte de operativa")
    try:
        pdf.set_lang("es")
    except Exception:
        pass
    pdf.add_page()
    W = pdf.epw

    # ---- encabezado
    x0, y0 = pdf.l_margin, pdf.get_y()
    pdf.set_draw_color(*P["text"]); pdf.set_line_width(0.5)
    pdf.line(x0, y0 + 5.5, x0 + 8.5, y0 + 5.5)
    pdf.set_draw_color(*P["signal"])
    pdf.line(x0 + 6.3, y0 + 5.5, x0 + 6.3, y0 + 1.8)
    pdf.set_fill_color(*P["signal"]); pdf.circle(x0 + 6.3, y0 + 1.3, 0.95, style="F")
    pdf.set_xy(x0 + 11, y0 + 1)
    pdf.set_font("mono", size=7); pdf.set_text_color(*P["muted"])
    pdf.cell(0, 4, "REGISTRO DE OPERATIVA")
    pdf.set_xy(x0, y0 + 9)
    pdf.set_font("serif", size=28); pdf.set_text_color(*P["text"])
    pdf.multi_cell(W, 11, D["titulo"], new_x="LMARGIN", new_y="NEXT")
    meta = " · ".join(x for x in (D["periodo"], D["filtros"], f"{D['n']} trades") if x)
    pdf.set_font("mono", size=7.5); pdf.set_text_color(*P["muted"])
    pdf.multi_cell(W, 4.5, meta, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def seccion(titulo, alto_min=40):
        if pdf.get_y() + alto_min > pdf.page_break_trigger:
            pdf.add_page()
        pdf.ln(4)
        pdf.set_font("serif", size=17); pdf.set_text_color(*P["text"])
        pdf.cell(0, 8, titulo, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*P["line"]); pdf.set_line_width(0.3)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + W, pdf.get_y())
        pdf.ln(3)

    def tarjetas(items, por_fila=4):
        gap = 3
        w = (W - gap * (por_fila - 1)) / por_fila
        h = 19
        for i in range(0, len(items), por_fila):
            if pdf.get_y() + h > pdf.page_break_trigger:
                pdf.add_page()
            y = pdf.get_y()
            for j, (lab, val, det, t) in enumerate(items[i:i + por_fila]):
                x = pdf.l_margin + j * (w + gap)
                pdf.set_fill_color(*P["card"]); pdf.set_draw_color(*P["line"]); pdf.set_line_width(0.3)
                pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=1.5)
                pdf.set_xy(x + 2.5, y + 2)
                pdf.set_font("mono", size=5.8); pdf.set_text_color(*P["muted"])
                pdf.cell(w - 5, 3, lab.upper()[:34])
                pdf.set_xy(x + 2.5, y + 6)
                pdf.set_font("serif", size=15 if len(val) < 14 else 11.5); pdf.set_text_color(*color_tono[t])
                pdf.cell(w - 5, 6.5, val)
                pdf.set_xy(x + 2.5, y + 13.5)
                pdf.set_font("mono", size=5.8); pdf.set_text_color(*P["muted"])
                pdf.cell(w - 5, 3.5, det[:44])
            pdf.set_y(y + h + gap)

    def tabla(headers, filas, pesos, alineacion, tonos=None, comentarios=None):
        """filas: lista de listas de str. tonos: {(i, j): 'pos'|'neg'}. comentarios: {i: texto}."""
        hs = FontFace(color=P["head_fg"], fill_color=P["head_bg"], size_pt=7)
        pdf.set_font("sans", size=8)
        pdf.set_text_color(*P["text"]); pdf.set_draw_color(*P["line"])
        with pdf.table(col_widths=pesos, text_align=alineacion, borders_layout="HORIZONTAL_LINES",
                       headings_style=hs, line_height=4.6, width=W) as t:
            r = t.row()
            for h in headers:
                r.cell(h)
            for i, fila in enumerate(filas):
                r = t.row()
                for j, v in enumerate(fila):
                    tn = (tonos or {}).get((i, j))
                    r.cell(v, style=FontFace(color=color_tono[tn]) if tn else None)
                if comentarios and comentarios.get(i):
                    r = t.row()
                    r.cell(comentarios[i], colspan=len(headers),
                           style=FontFace(color=P["muted"], size_pt=7))
        pdf.ln(2)

    # ---- secciones
    if "resumen" in sec:
        seccion("Resumen y métricas clave", 50)
        tarjetas(kpis_resumen(D), 3)
    if "riesgo" in sec:
        seccion("Riesgo: drawdown, rachas y costos", 50)
        tarjetas(kpis_riesgo(D), 4)
    if "curva" in sec and len(D["curva"]) >= 2:
        seccion("Curva de equity", 80)
        x, y, w, h = pdf.l_margin + 14, pdf.get_y() + 2, W - 16, 58
        vals = D["curva"]
        pts = vals if len(vals) <= 600 else [vals[int(i * (len(vals) - 1) / 599)] for i in range(600)]
        lo, hi = min(0.0, min(pts)), max(0.0, max(pts))
        if hi == lo:
            hi, lo = hi + 1, lo - 1
        X = lambda i: x + w * i / (len(pts) - 1)
        Y = lambda v: y + h * (1 - (v - lo) / (hi - lo))
        pdf.set_draw_color(*P["muted"]); pdf.set_line_width(0.2)
        pdf.set_dash_pattern(dash=1.2, gap=1.2)
        pdf.line(x, Y(0), x + w, Y(0))
        pdf.set_dash_pattern()
        pdf.set_draw_color(*P["signal"]); pdf.set_line_width(0.55)
        pdf.polyline([(X(i), Y(v)) for i, v in enumerate(pts)], style="D")
        pdf.set_font("mono", size=6.5); pdf.set_text_color(*P["muted"])
        for v in sorted({hi, 0.0, lo}):
            pdf.set_xy(pdf.l_margin, Y(v) - 1.8)
            pdf.cell(13, 3.6, f"{v:+,.0f}" if v else "0", align="R")
        pdf.set_xy(x, y + h + 1.5)
        pdf.cell(w / 2, 3.6, _f(D["curva_fechas"][0]))
        pdf.cell(w / 2, 3.6, _f(D["curva_fechas"][-1]), align="R")
        pdf.set_y(y + h + 8)
    if "dias" in sec:
        seccion("Resultado por día", 40)
        filas, tonos = [], {}
        for i, d in enumerate(D["dias"]):
            filas.append([f"{_f(d['label'])} {d['dia']}", str(d["n"]), usd(d["neto"], dec=0),
                          f"{d['wr']:.0f}%", usd(d["acum"], dec=0)])
            tonos[(i, 2)], tonos[(i, 4)] = tono(d["neto"]), tono(d["acum"])
        tabla(["Día", "Trades", "Neto", "Win rate", "Acumulado"], filas, (30, 14, 20, 16, 22),
              ("LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"), tonos)
    for clave, titulo in (("hora", "Por hora de entrada"), ("activo", "Por activo"),
                          ("semana", "Por día de la semana"), ("setup", "Por setup (playbook)")):
        if clave in sec and D.get(clave):
            seccion(titulo, 30)
            filas, tonos = [], {}
            for i, g in enumerate(D[clave]):
                filas.append([str(g["label"]), str(g["n"]), usd(g["neto"], dec=0), f"{g['wr']:.0f}%",
                              usd(g["prom"], dec=1)])
                tonos[(i, 2)] = tono(g["neto"])
            tabla(["Grupo", "Trades", "Neto", "Win rate", "Promedio"], filas, (30, 14, 20, 16, 18),
                  ("LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"), tonos)
    if "ops" in sec:
        seccion("Detalle de operaciones", 30)
        cols = columnas_ops(D)
        peso = dict(fecha=21, hora=11, activo=15, lado=11, contratos=9, setup=20, bruto=16, costo=13,
                    neto=17, empresa=22, cuenta=20, emo=8)
        izq = {"fecha", "hora", "activo", "lado", "setup", "empresa", "cuenta"}
        filas, tonos, coms = [], {}, {}
        for i, o in enumerate(D["ops"]):
            fila = []
            for j, (k, _) in enumerate(cols):
                v = o.get(k)
                if k == "fecha":
                    fila.append(_f(v))
                elif k in ("bruto", "costo", "neto"):
                    fila.append(usd(v))
                elif k in ("contratos", "emo"):
                    fila.append("" if v is None else f"{v:g}")
                else:
                    fila.append(str(v or ""))
                if k == "neto":
                    tonos[(i, j)] = tono(v)
            filas.append(fila)
            if o.get("comentario"):
                coms[i] = o["comentario"]
        tabla([h for _, h in cols], filas, tuple(peso.get(k, 14) for k, _ in cols),
              tuple("LEFT" if k in izq else "RIGHT" for k, _ in cols), tonos, coms)

    return _escribir(ruta, lambda tmp: pdf.output(tmp))

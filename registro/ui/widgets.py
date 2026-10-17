"""Widgets y helpers de estilo compartidos: entradas, combos, botones y selector de fecha."""

from registro.ui import vivo
import calendar
import customtkinter as ctk
from datetime import date
from datetime import datetime
from registro import db as _db
from registro.ui.estado import DPI_SISTEMA
from registro.ui.tema import (BLUE, BLUE_HI, BORDER_W, FONT_MAIN, FONT_MONO, HOVER, LINE2, MUTED, MUTED2, NEG_TXT, PAPER, POS_TXT, RAD_CARD, RAD_CTRL, SP_MD, SP_SM, SP_XS, SURFACE, SURFACE2)


# ----------------------------------------------------------------------------
# Helpers de estilo — un solo lugar define cómo se ven inputs y botones.
# Mantiene esquinas, bordes y fondos consistentes en toda la app.
# ----------------------------------------------------------------------------
def styled_entry(parent, width=130, mono=True, placeholder=None):
    return ctk.CTkEntry(
        parent, width=width, height=34,
        font=((FONT_MONO if mono else FONT_MAIN), 13),
        fg_color=SURFACE2, border_color=LINE2, border_width=BORDER_W,
        corner_radius=RAD_CTRL, text_color=PAPER,
        placeholder_text=placeholder or "")


def styled_combo(parent, values, width=130, mono=False, default=None):
    cb = ctk.CTkComboBox(
        parent, values=values, width=width, height=34,
        font=((FONT_MONO if mono else FONT_MAIN), 13),
        fg_color=SURFACE2, border_color=LINE2, border_width=BORDER_W,
        corner_radius=RAD_CTRL, text_color=PAPER,
        button_color=LINE2, button_hover_color=MUTED2,   # botón de la flecha bien visible
        dropdown_fg_color=SURFACE, dropdown_hover_color=HOVER,
        dropdown_text_color=PAPER)
    if default is not None:
        cb.set(default)
    return cb


MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
            "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


DIAS_ES = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]


class DatePicker(ctk.CTkFrame):
    """Campo de fecha (se puede tipear AAAA-MM-DD) + botón que abre un calendario.
    Los días en que operaste se ven en verde/rojo según el resultado del día.
    Misma interfaz que un CTkEntry: get(), insert(), delete()."""

    def __init__(self, parent, width=130, placeholder="AAAA-MM-DD", con_marcas=True, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._popup = None
        self._con_marcas = con_marcas
        self.entry = styled_entry(self, width=width, mono=True, placeholder=placeholder)
        self.entry.pack(side="left")
        self.btn = ctk.CTkButton(
            self, text="📅", width=34, height=34, font=(FONT_MAIN, 14), fg_color=SURFACE2,
            text_color=PAPER, hover_color=HOVER, border_color=LINE2, border_width=BORDER_W,
            corner_radius=RAD_CTRL, command=self._abrir)
        self.btn.pack(side="left", padx=(SP_XS, 0))

    # ---- interfaz tipo Entry ----
    def get(self):
        return self.entry.get().strip()

    def insert(self, index, texto):
        self.entry.insert(index, texto)

    def delete(self, a, b=None):
        self.entry.delete(a, b)

    def set(self, valor):
        self.entry.delete(0, "end")
        if valor:
            self.entry.insert(0, valor)

    # ---- calendario ----
    def _fecha_actual(self):
        try:
            return datetime.strptime(self.get(), "%Y-%m-%d").date()
        except ValueError:
            return date.today()

    def _abrir(self):
        if self._popup is not None:          # el botón alterna abrir/cerrar
            self._cerrar()
            return
        f = self._fecha_actual()
        self._year, self._month, self._sel = f.year, f.month, f
        self._marcas = {}
        if self._con_marcas:
            try:
                self._marcas = _db.db_pnl_por_dia()
            except Exception:
                self._marcas = {}
        root = self.winfo_toplevel()
        k = getattr(root, "factor", 1.0)
        pw, ph = int(268 * k), int(300 * k)
        self._popup = ctk.CTkToplevel(self)
        self._popup.withdraw()
        self._popup.overrideredirect(True)
        self._popup.configure(fg_color=SURFACE)
        self._popup.bind("<Escape>", lambda e: self._cerrar())
        self.update_idletasks()
        x = self.btn.winfo_rootx() + self.btn.winfo_width() - int(pw * DPI_SISTEMA)
        y = self.btn.winfo_rooty() + self.btn.winfo_height() + 4
        x = max(root.winfo_rootx() + 4, x)
        # no salirse de la pantalla por abajo: si no entra, abrir hacia arriba
        if y + int(ph * DPI_SISTEMA) > self.winfo_screenheight():
            y = max(0, self.btn.winfo_rooty() - int(ph * DPI_SISTEMA) - 4)
        self._popup.geometry(f"{pw}x{ph}+{x}+{y}")
        self._cont = ctk.CTkFrame(self._popup, fg_color=SURFACE, border_color=BLUE,
                                  border_width=1, corner_radius=RAD_CARD)
        self._cont.pack(fill="both", expand=True, padx=1, pady=1)
        self._render_cal()
        self._popup.deiconify()
        self._popup.lift()
        self._click_id = None
        self._popup.after(150, self._click_afuera_on)

    def _click_afuera_on(self):
        if self._popup is None:
            return
        self._click_id = self.winfo_toplevel().bind("<Button-1>", self._click_global, add="+")

    def _click_global(self, e):
        if self._popup is None:
            return
        def dentro(w):
            return (w.winfo_rootx() <= e.x_root <= w.winfo_rootx() + w.winfo_width()
                    and w.winfo_rooty() <= e.y_root <= w.winfo_rooty() + w.winfo_height())
        if not dentro(self._popup) and not dentro(self.btn):
            self._cerrar()

    def _cerrar(self):
        p, self._popup = self._popup, None
        try:
            if getattr(self, "_click_id", None):
                self.winfo_toplevel().unbind("<Button-1>", self._click_id)
        except Exception:
            pass
        self._click_id = None
        if p is not None:
            try:
                p.destroy()
            except Exception:
                pass

    def _render_cal(self):
        for w in self._cont.winfo_children():
            w.destroy()
        head = ctk.CTkFrame(self._cont, fg_color="transparent")
        head.pack(fill="x", padx=SP_MD, pady=(SP_MD, SP_XS))
        for txt, cmd, lado in (("‹", self._mes_ant, "left"), ("›", self._mes_sig, "right")):
            ctk.CTkButton(head, text=txt, width=30, height=28, font=(FONT_MAIN, 16),
                          fg_color=SURFACE2, hover_color=HOVER, command=cmd).pack(side=lado)
        ctk.CTkLabel(head, text=f"{MESES_ES[self._month - 1]} {self._year}",
                     font=(FONT_MAIN, 13, "bold"), text_color=PAPER).pack(expand=True)
        grid = ctk.CTkFrame(self._cont, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=SP_MD)
        for i in range(7):
            grid.grid_columnconfigure(i, weight=1, uniform="d")
            ctk.CTkLabel(grid, text=DIAS_ES[i], font=(FONT_MONO, 10), text_color=MUTED,
                         width=30).grid(row=0, column=i, pady=2)
        hoy = date.today()
        for fila, semana in enumerate(calendar.Calendar(0).monthdayscalendar(self._year, self._month), 1):
            for col, dia in enumerate(semana):
                if not dia:
                    continue
                d = date(self._year, self._month, dia)
                pnl = self._marcas.get(d.isoformat())
                sel = d == self._sel
                color = (PAPER if sel else POS_TXT if (pnl or 0) > 0 else NEG_TXT if (pnl or 0) < 0
                         else PAPER if pnl is not None else (PAPER if d == hoy else MUTED))
                ctk.CTkButton(
                    grid, text=str(dia), width=30, height=28,
                    font=(FONT_MONO, 12, "bold" if (sel or d == hoy or pnl is not None) else "normal"),
                    fg_color=BLUE if sel else "transparent", text_color=color, hover_color=HOVER,
                    border_color=(PAPER if d == hoy and not sel else BLUE),
                    border_width=(1 if d == hoy and not sel else 0), corner_radius=6,
                    command=lambda dd=d: self._elegir(dd)).grid(row=fila, column=col, padx=1, pady=1)
        pie = ctk.CTkFrame(self._cont, fg_color="transparent")
        pie.pack(fill="x", padx=SP_MD, pady=(SP_XS, SP_MD))
        ctk.CTkButton(pie, text="Hoy", height=26, font=(FONT_MAIN, 11), fg_color=SURFACE2,
                      hover_color=HOVER, command=lambda: self._elegir(date.today())).pack(side="left", expand=True, fill="x")
        if self._marcas:
            ctk.CTkLabel(pie, text="días operados en color", font=(FONT_MAIN, 9),
                         text_color=MUTED2).pack(side="right", padx=(SP_SM, 0))

    def _mes_ant(self):
        self._month, self._year = (12, self._year - 1) if self._month == 1 else (self._month - 1, self._year)
        self._render_cal()

    def _mes_sig(self):
        self._month, self._year = (1, self._year + 1) if self._month == 12 else (self._month + 1, self._year)
        self._render_cal()

    def _elegir(self, d):
        self.set(d.isoformat())
        self._cerrar()


def btn_primary(parent, text, command, width=140, height=34):
    return ctk.CTkButton(
        parent, text=text, width=width, height=height,
        fg_color=BLUE, hover_color=BLUE_HI, corner_radius=RAD_CTRL,
        font=(FONT_MAIN, 13), command=command)


def btn_ghost(parent, text, command, width=140, height=34, text_color=None):
    text_color = text_color or PAPER
    return ctk.CTkButton(
        parent, text=text, width=width, height=height,
        fg_color="transparent", border_color=LINE2, border_width=BORDER_W,
        corner_radius=RAD_CTRL, text_color=text_color, hover_color=SURFACE,
        font=(FONT_MAIN, 13), command=command)


vivo.registrar(globals())

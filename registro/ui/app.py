"""Shell de la aplicación: ventana, escala, barra lateral, menú Datos, pestañas, tema y reinicio.

`AppBase` no conoce las pantallas: las construye y las pinta a través de los métodos que
aportan las clases que la completan (hoy `App` en registro_operativa.py; luego, Mixins)."""
import os
import sys
import subprocess

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from registro import __version__, APP_NAME
from registro.db import db_all
from registro.ui import vivo
from registro.ui.capturas import CaptureBox
from registro.ui.estado import CTX, DPI_SISTEMA, load_ui_prefs, save_ui_prefs
from registro.ui.nav import Nav, SECCIONES
from registro.ui.tema import (
    TEMA_POR_DEFECTO, TEMA_ACTUAL, MODO, aplicar_tema,
    BLUE, FONT_MAIN, FONT_SERIF, HOVER, INK, LINE, LINE2, MUTED, MUTED2, ON_BLUE, PAPER,
    RAD_CTRL, SEG_HI, SEG_SEL, SIDEBAR, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SP_XXL, SURFACE)
from registro.ui.widgets import btn_ghost, btn_primary

from registro.ui.dialogos.importar import ImportarDialog
from registro.ui.dialogos.exportar import ExportarDialog
from registro.ui.dialogos.acerca import AcercaDialog
from registro.ui.dialogos.riesgo import RiesgoDialog

vivo.registrar(globals())

UI_SCALES = {"chico": 1.00, "mediano": 1.15, "grande": 1.30}
UI_SCALE_DEFAULT = "mediano"
BASE_W, BASE_H = 1180, 820
BASE_MIN_W, BASE_MIN_H = 980, 640


class AppBase(ctk.CTk):
    SECCIONES = SECCIONES

    def __init__(self):
        prefs0 = load_ui_prefs()
        aplicar_tema(prefs0.get("tema", TEMA_POR_DEFECTO))
        nivel = prefs0.get("ui_scale")
        self.ui_scale = nivel if nivel in UI_SCALES else UI_SCALE_DEFAULT
        self.factor = UI_SCALES[self.ui_scale]
        super().__init__()
        ctk.set_widget_scaling(self.factor * DPI_SISTEMA)
        self.title(f"{APP_NAME} — gabomondo · v{__version__}")
        self._aplicar_geometria(self.factor, centrar=True)
        self.configure(fg_color=INK)
        ctk.set_appearance_mode(MODO)

        self.edit_id = None
        self.emo_val = ctk.IntVar(value=0)
        self.sort_col = "fecha"
        self.sort_desc = True
        self.wk_offset = 0
        self._thumbs = []  # refs para que no las recoja el GC
        self._equity_redraw_job = None  # debounce del redibujado de la equity
        self._ui_prefs = load_ui_prefs()
        self._equity_collapsed = bool(self._ui_prefs.get("equity_collapsed", False))
        self._equity_rows = []
        # Control de repintado: solo reconstruimos la tabla si cambiaron datos
        # (alta/edición/borrado) o el filtro/orden. Cambiar de pestaña y volver
        # a Registro sin tocar nada ya no reconstruye ~1000 widgets al pedo.
        self._table_dirty = True
        self._last_render_sig = None

        self._restaurar_cuenta()
        self._restaurar_periodo()
        self._restaurar_modo()
        self._build_shell()
        self._build_tabs()

        # Ctrl+V global -> caja con foco
        self.bind_all("<Control-v>", self._on_paste)
        self.bind_all("<Control-V>", self._on_paste)
        self.after(500, self._avisos_inicio)
        self.after(2500, self._buscar_actualizacion)
        self._elegir_pestana_inicial()
        self._vigilar_lag()

    def _aplicar_geometria(self, factor, centrar=False):
        esc = DPI_SISTEMA            # CTk multiplica el tamaño de la ventana por esta escala
        w, h = int(BASE_W * factor), int(BASE_H * factor)
        sw = int(self.winfo_screenwidth() / esc)
        sh = int(self.winfo_screenheight() / esc)
        w, h = min(w, sw - 40), min(h, sh - 80)
        self.minsize(min(int(BASE_MIN_W * factor), w), min(int(BASE_MIN_H * factor), h))
        if centrar:
            # la posición va en píxeles reales (no se escala)
            x = max(0, (self.winfo_screenwidth() - int(w * esc)) // 2)
            y = max(0, (self.winfo_screenheight() - int(h * esc)) // 2 - 20)
            self.geometry(f"{w}x{h}+{x}+{y}")
        else:
            self.geometry(f"{w}x{h}")

    def _on_cambiar_tamano(self, label):
        self.cambiar_escala({"Chico": "chico", "Mediano": "mediano",
                             "Grande": "grande"}.get(label, UI_SCALE_DEFAULT))

    def cambiar_escala(self, nivel):
        """Cambia el tamaño de toda la interfaz en caliente y lo recuerda."""
        if nivel == self.ui_scale or nivel not in UI_SCALES:
            return
        self.ui_scale, self.factor = nivel, UI_SCALES[nivel]
        self.seg_tamano.set(nivel.capitalize())
        self._ui_prefs["ui_scale"] = nivel
        save_ui_prefs(self._ui_prefs)
        self.after(10, self._aplicar_escala)

    def _aplicar_escala(self):
        try:
            ctk.set_widget_scaling(self.factor * DPI_SISTEMA)
        except Exception:
            CTX.log.exception("No pude cambiar el tamaño de la interfaz")
            return
        self._aplicar_geometria(self.factor)
        self._estilo_tree()
        self._ancho_columnas_tree()
        self._table_dirty = True
        self.render_table(force=True)
        self._render_equity(self._equity_rows)
        if self.tabs.get() == "Análisis":
            self.render_analisis()
        self.update_idletasks()

    def _elegir_pestana_inicial(self):
        """Abre en Registro (curva y métricas). Si todavía no hay operaciones,
        en Plan, que es por donde conviene empezar."""
        try:
            hay = bool(db_all(todo=True))
        except Exception:
            hay = False
        self.tabs.set("Registro" if hay else "Plan")
        self._on_tab_change()

    def _vigilar_lag(self):
        """Anota en el log cuando la interfaz se queda 'colgada' (más de 0,4 s sin
        atender eventos): sirve para diagnosticar cuelgues al mover la ventana."""
        import time
        previo = getattr(self, "_lag_t", None)
        ahora = time.monotonic()
        if previo is not None and (ahora - previo) > 0.5:
            try:
                geo = self.geometry()
            except Exception:
                geo = "?"
            CTX.log.warning("Interfaz sin responder %.0f ms (ventana %s)", (ahora - previo - 0.1) * 1000, geo)
        self._lag_t = ahora
        self.after(100, self._vigilar_lag)

    def _build_shell(self):
        self.sidebar = ctk.CTkFrame(self, fg_color=SIDEBAR, corner_radius=0, width=196)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        ctk.CTkFrame(self, fg_color=LINE, width=1, corner_radius=0).pack(side="left", fill="y")

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=SP_XL, pady=(SP_XL, SP_LG))
        ctk.CTkLabel(brand, text="Registro", font=(FONT_SERIF, 30), text_color=PAPER).pack(anchor="w")
        ctk.CTkLabel(brand, text="de operativa", font=(FONT_MAIN, 12), text_color=MUTED).pack(anchor="w")

        foot = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        foot.pack(side="bottom", fill="x", padx=SP_LG, pady=(0, SP_LG))
        pie = ctk.CTkFrame(foot, fg_color="transparent")
        pie.pack(side="bottom", fill="x", pady=(SP_SM, 0))
        ctk.CTkLabel(pie, text=f"v{__version__}", font=(FONT_MAIN, 10),
                     text_color=MUTED2).pack(side="left", padx=SP_XS)
        ctk.CTkButton(pie, text="Acerca de", width=70, height=22, corner_radius=RAD_CTRL,
                      fg_color="transparent", hover_color=HOVER, text_color=MUTED,
                      font=(FONT_MAIN, 11), command=lambda: AcercaDialog(self)).pack(side="right")
        self._build_aviso_actualizacion(foot, pie)
        self.seg_tamano = ctk.CTkSegmentedButton(
            foot, values=["Chico", "Mediano", "Grande"], height=28,
            font=(FONT_MAIN, 11), fg_color=SURFACE, selected_color=SEG_SEL,
            selected_hover_color=SEG_HI, unselected_color=SURFACE,
            unselected_hover_color=HOVER, text_color=PAPER, command=self._on_cambiar_tamano)
        self.seg_tamano.set(self.ui_scale.capitalize())
        self.seg_tamano.pack(side="bottom", fill="x")
        ctk.CTkLabel(foot, text="TAMAÑO DE LETRA", font=(FONT_MAIN, 9),
                     text_color=MUTED2).pack(side="bottom", anchor="w", padx=SP_XS, pady=(0, SP_XS))

        self._build_selector(self.sidebar)

        # las secciones van en una lista con scroll: si la ventana es baja o la letra grande,
        # el pie (tamaño de letra, versión) queda siempre visible y el resto se desplaza
        self.nav_lista = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=LINE2, scrollbar_button_hover_color=MUTED2)
        self.nav_lista.pack(side="top", fill="both", expand=True)
        self.nav = Nav(self, self.nav_lista)
        self.tabs = self.nav       # misma interfaz que usaba el CTkTabview

        # contenido
        main = ctk.CTkFrame(self, fg_color=INK, corner_radius=0)
        main.pack(side="left", fill="both", expand=True)
        top = ctk.CTkFrame(main, fg_color="transparent")
        top.pack(fill="x", padx=SP_XXL, pady=(SP_XL, SP_MD))
        tl = ctk.CTkFrame(top, fg_color="transparent"); tl.pack(side="left", anchor="w")
        self.lbl_titulo = ctk.CTkLabel(tl, text="", font=(FONT_SERIF, 30), text_color=PAPER)
        self.lbl_titulo.pack(anchor="w")
        self.lbl_sub = ctk.CTkLabel(tl, text="", font=(FONT_MAIN, 12), text_color=MUTED)
        self.lbl_sub.pack(anchor="w")
        tr = ctk.CTkFrame(top, fg_color="transparent"); tr.pack(side="right", anchor="e")
        self.btn_datos = btn_ghost(tr, "Datos  ▾", self._menu_datos, width=96, height=34)
        self.btn_datos.pack(side="right", padx=(SP_SM, 0))
        btn_primary(tr, "Importar trades", self.abrir_importar, width=148, height=34).pack(side="right")
        self._build_periodo(tr)
        self._build_modo(self.ctrl_global)
        ctk.CTkFrame(main, fg_color=LINE, height=1, corner_radius=0).pack(fill="x", padx=SP_XXL)
        self.page_host = ctk.CTkFrame(main, fg_color="transparent", corner_radius=0)
        self.page_host.pack(fill="both", expand=True, padx=SP_XXL, pady=(SP_MD, SP_MD))

    def _menu_datos(self):
        m = tk.Menu(self, tearoff=0, bg=SURFACE, fg=PAPER, activebackground=BLUE,
                    activeforeground=ON_BLUE, bd=0, relief="flat",
                    font=(FONT_MAIN, max(8, round(10 * self.factor))))
        m.add_command(label="  Backup JSON (guardar todo)", command=self.export_json)
        m.add_command(label="  Importar JSON (restaurar)", command=self.import_json)
        m.add_separator()
        m.add_command(label="  Exportar reporte (PDF, HTML, Excel)…", command=self.abrir_exportar)
        m.add_command(label="  Exportar CSV rápido", command=self.export_csv)
        m.add_separator()
        otro = "claro" if TEMA_ACTUAL == "oscuro" else "oscuro"
        m.add_command(label=f"  Cambiar a tema {otro}…", command=self._alternar_tema)
        b = self.btn_datos
        try:
            m.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height() + 2)
        finally:
            m.grab_release()

    def _build_tabs(self):
        herramientas = False
        for g, nombre, _sub in self.SECCIONES:
            if g == "AJUSTES" and not herramientas:      # herramientas: justo antes de Ajustes
                herramientas = True
                self.nav.add_accion("HERRAMIENTAS", "Calculadora de riesgo",
                                    lambda: RiesgoDialog(self))
            self.nav.add(nombre)
        self.tab_plan = self.nav.pages["Plan"]
        self.tab_cargar = self.nav.pages["Cargar operación"]
        self.tab_registro = self.nav.pages["Registro"]
        self.tab_analisis = self.nav.pages["Análisis"]
        self.tab_revision = self.nav.pages["Revisión semanal"]
        self.tab_plantillas = self.nav.pages["Plantillas"]
        self.tab_perfil = self.nav.pages["Perfil"]
        self.tab_calendario = self.nav.pages["Calendario"]
        self.tab_notebook = self.nav.pages["Notebook"]
        self.tab_simulador = self.nav.pages["Simulador"]
        self.tab_playbooks = self.nav.pages["Playbooks"]
        self.tab_cuentas = self.nav.pages["Cuentas"]
        self.tab_portfolio = self.nav.pages["Portfolio"]
        self.nav.configure(command=self._on_tab_change)

        self._build_plan()
        self._build_cargar()
        self._build_registro()
        self._build_analisis()
        self._build_revision()
        self._build_plantillas()
        self._build_perfil()
        self._build_calendario()
        self._build_notebook()
        self._build_simulador()
        self._build_playbooks()
        self._build_cuentas()
        self._build_portfolio()

    def _on_tab_change(self):
        name = self.tabs.get()
        if getattr(self, "_pag_prev", None) == "Notebook" and name != "Notebook":
            self._nb_guardar()
        self._pag_prev = name
        self._reiniciar_base_pct()
        self._mostrar_periodo(name)
        self._mostrar_modo(name)
        if name == "Registro": self.render_table(force=False)
        elif name == "Análisis": self.render_analisis()
        elif name == "Revisión semanal": self.render_revision()
        elif name == "Plan": self._load_plan_into_editor()
        elif name == "Plantillas": self.render_plantillas()
        elif name == "Perfil": self._cargar_perfil_en_ui()
        elif name == "Calendario": self.render_calendario()
        elif name == "Notebook": self.render_notebook()
        elif name == "Simulador": self.render_simulador()
        elif name == "Playbooks": self.render_playbooks()
        elif name == "Cuentas": self.render_cuentas()
        elif name == "Portfolio": self.render_portfolio()
        elif name == "Cargar operación":
            self._reload_templates_into_combo(keep_id=self.cur_tpl_id)
            self._refresh_dropdowns()

    def _on_paste(self, event=None):
        w = self.focus_get()
        # subir por el árbol hasta encontrar una CaptureBox
        while w is not None:
            if isinstance(w, CaptureBox):
                w.paste_from_clipboard()
                return "break"
            w = getattr(w, "master", None)
        # si el foco está en un CaptureBox marcado manualmente
        if getattr(self, "_last_capture", None) is not None:
            self._last_capture.paste_from_clipboard()
            return "break"

    def report_callback_exception(self, exc, val, tb):
        """Errores dentro de callbacks de Tk: al log y un aviso, sin cerrar la app."""
        import traceback
        try:
            CTX.log.error("Error en la interfaz:\n%s", "".join(traceback.format_exception(exc, val, tb)))
        except Exception:
            pass
        try:
            messagebox.showerror("Algo salió mal",
                                 f"{val}\n\nQuedó registrado en:\n{CTX.rutas.logs_dir}")
        except Exception:
            pass

    def _avisos_inicio(self):
        m = CTX.migracion
        if m["desde"] != m["hasta"] and m["backup"]:
            messagebox.showinfo(
                "Base actualizada",
                f"Actualicé tu base de datos a la versión {m['hasta']}.\n\n"
                f"Antes guardé una copia por seguridad en:\n{m['backup']}")
        elif CTX.perfil_nuevo and CTX.rutas.origen == "appdata":
            messagebox.showinfo(
                "Bienvenido",
                "Para empezar:\n\n1. Pestaña Perfil: tus activos, tipos de entrada y empresas.\n"
                "2. Pestaña Plan: escribí tu plan de trading.\n"
                "3. Pestaña Plantillas: armá tu check de disciplina.\n\n"
                f"Tus datos se guardan en:\n{CTX.rutas.data_dir}")

    def _alternar_tema(self):
        """Datos → Cambiar a tema claro/oscuro: guarda la preferencia y reinicia el programa."""
        nuevo = "claro" if TEMA_ACTUAL == "oscuro" else "oscuro"
        if not messagebox.askyesno(
                "Cambiar tema",
                f"Se cambia al tema {nuevo}. Para verlo el programa se cierra y se vuelve a abrir.\n"
                "Lo que tengas sin guardar en un formulario se pierde.\n\n¿Reiniciar ahora?"):
            return
        self._ui_prefs["tema"] = nuevo
        save_ui_prefs(self._ui_prefs)
        self._reiniciar()

    def _reiniciar_con_aviso(self):
        if messagebox.askyesno(
                "Reiniciar",
                "El programa se cierra y se vuelve a abrir.\n"
                "Lo que tengas sin guardar en un formulario se pierde.\n\n¿Reiniciar ahora?"):
            self._reiniciar()

    def _reiniciar(self):
        """Cierra el programa y lo vuelve a abrir con los mismos argumentos (--datos, --perfil)."""
        if getattr(self, "_nb_job", None) is not None:      # nota del notebook con guardado pendiente
            self._nb_guardar()
        if getattr(sys, "frozen", False):
            args = [sys.executable] + sys.argv[1:]
        else:
            args = [sys.executable, os.path.abspath(sys.argv[0])] + sys.argv[1:]
        kw = {}
        if sys.platform == "win32":
            kw["creationflags"] = 0x00000008 | 0x00000200      # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        try:
            subprocess.Popen(args, cwd=os.getcwd(), close_fds=True, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
        except Exception as e:
            CTX.log.exception("No pude reiniciar")
            messagebox.showerror("Reiniciar", f"No pude reabrir el programa solo: {e}\n"
                                              "Cerralo y abrilo a mano.")
            return
        self.destroy()

    def abrir_importar(self):
        ImportarDialog(self)

    def abrir_exportar(self, desde_analisis=False):
        per = cta = None
        if desde_analisis:
            from registro.db import get_periodo_global
            from registro import periodos as PR
            per = {PR.rango("Últimos 30 días"): "30 días", PR.rango("Este mes"): "Este mes"}.get(get_periodo_global())
            cta = self.an_cuenta.get()
        ExportarDialog(self, periodo=per, cuenta=cta)

"""Pantalla(s) de la app como Mixin de App (_on_cambiar_tema, _build_perfil, _set_box…)."""
from datetime import datetime
import os

from tkinter import filedialog, messagebox
import customtkinter as ctk

from registro import __version__, APP_NAME, db as _db, paths as _paths, perfil as _perfil_mod
from registro.db import init_db
from registro.ui import vivo
from registro.ui.estado import CTX, save_ui_prefs
from registro.ui.tema import (
    FONT_MAIN, FONT_MONO, FONT_SERIF, HOVER, LINE2, MUTED, PAPER, SEG_HI, SEG_SEL, SP_LG,
    SP_MD, SP_SM, SP_XL, SP_XS, SURFACE, TEMA_ACTUAL)
from registro.ui.util import _abrir_carpeta, _lista_de_texto, _pares_a_texto, _parse_pares
from registro.ui.widgets import btn_ghost, btn_primary, styled_entry

vivo.registrar(globals())


class PerfilMixin:
    def _on_cambiar_tema(self, label):
        nombre = label.lower()
        self._ui_prefs["tema"] = nombre
        save_ui_prefs(self._ui_prefs)
        cambio = nombre != TEMA_ACTUAL
        self.lbl_tema.configure(
            text="Listo: el tema nuevo se ve al reiniciar el programa." if cambio else "")
        if cambio:
            self.btn_reiniciar.pack(anchor="w", pady=(SP_SM, 0))
        else:
            self.btn_reiniciar.pack_forget()

    def _build_perfil(self):
        f = ctk.CTkScrollableFrame(self.tab_perfil, fg_color="transparent")
        f.pack(fill="both", expand=True)

        def titulo(txt, sub=None):
            ctk.CTkLabel(f, text=txt, font=(FONT_SERIF, 20), text_color=PAPER).pack(
                anchor="w", pady=(SP_XL, 0))
            if sub:
                ctk.CTkLabel(f, text=sub, font=(FONT_MAIN, 12), text_color=MUTED,
                             justify="left", wraplength=980).pack(anchor="w", pady=(SP_XS, SP_SM))

        def caja(parent, alto):
            tb = ctk.CTkTextbox(parent, height=alto, font=(FONT_MONO, 12), fg_color=SURFACE,
                                border_color=LINE2, border_width=1)
            return tb

        titulo("Perfil", "Lo que cambia de un trader a otro. Se guarda en perfil.json, dentro de tu carpeta de datos.")
        c = ctk.CTkFrame(f, fg_color="transparent"); c.pack(fill="x")
        self._lbl(c, "Nombre del perfil").pack(anchor="w", pady=(0, SP_XS))
        self.p_nombre = styled_entry(c, width=280, mono=False)
        self.p_nombre.pack(anchor="w")

        titulo("Apariencia", "Tema de colores. También lo podés cambiar desde el menú Datos. Se aplica al reiniciar el programa.")
        ap = ctk.CTkFrame(f, fg_color="transparent"); ap.pack(fill="x")
        self.seg_tema = ctk.CTkSegmentedButton(
            ap, values=["Oscuro", "Claro"], width=220, height=32, font=(FONT_MAIN, 12),
            fg_color=SURFACE, selected_color=SEG_SEL, selected_hover_color=SEG_HI,
            unselected_color=SURFACE, unselected_hover_color=HOVER, text_color=PAPER,
            command=self._on_cambiar_tema)
        self.seg_tema.set(TEMA_ACTUAL.capitalize())
        self.seg_tema.pack(anchor="w")
        self.lbl_tema = ctk.CTkLabel(ap, text="", font=(FONT_MAIN, 11), text_color=MUTED)
        self.lbl_tema.pack(anchor="w", pady=(SP_XS, 0))
        self.btn_reiniciar = btn_ghost(ap, "Reiniciar ahora", self._reiniciar_con_aviso,
                                       width=150, height=32)       # se muestra al elegir otro tema

        titulo("Actualizaciones", "Al abrir (una vez por día) la app mira en gabomondo.com si hay una versión nueva. "
               "Solo lee un archivo público con el número de versión: no envía nada tuyo. Podés apagarlo.")
        self.sw_actualiz = ctk.CTkSwitch(f, text="Avisarme si hay una versión nueva", font=(FONT_MAIN, 12),
                                         text_color=PAPER, command=self._on_toggle_actualizaciones)
        if self._ui_prefs.get("buscar_actualizaciones", True):
            self.sw_actualiz.select()
        self.sw_actualiz.pack(anchor="w", pady=(0, SP_SM))

        titulo("Listas de los desplegables",
               "Una por línea. Lo que cargues en tus operaciones también aparece solo.")
        grid = ctk.CTkFrame(f, fg_color="transparent"); grid.pack(fill="x")
        self.p_boxes = {}
        for i, (key, label) in enumerate([("activos", "Activos"), ("tipos", "Tipos de entrada"),
                                          ("empresas", "Empresas"), ("tipos_cuenta", "Tipos de cuenta")]):
            col = ctk.CTkFrame(grid, fg_color="transparent")
            col.grid(row=0, column=i, padx=(0, SP_MD), sticky="nsew")
            grid.grid_columnconfigure(i, weight=1)
            self._lbl(col, label).pack(anchor="w", pady=(0, SP_XS))
            self.p_boxes[key] = caja(col, 130)
            self.p_boxes[key].pack(fill="x")

        titulo("Contratos y costos",
               "Formato  SÍMBOLO=valor, uno por línea. Se usan al importar trades desde tu plataforma.")
        grid2 = ctk.CTkFrame(f, fg_color="transparent"); grid2.pack(fill="x")
        for i, (key, label) in enumerate([("valor_punto", "Valor del punto (USD por contrato)"),
                                          ("comision_contrato", "Comisión por contrato (USD, ida y vuelta)")]):
            col = ctk.CTkFrame(grid2, fg_color="transparent")
            col.grid(row=0, column=i, padx=(0, SP_MD), sticky="nsew")
            grid2.grid_columnconfigure(i, weight=1)
            self._lbl(col, label).pack(anchor="w", pady=(0, SP_XS))
            self.p_boxes[key] = caja(col, 170)
            self.p_boxes[key].pack(fill="x")

        titulo("Importación de trades",
               "Horas de diferencia entre el horario del servidor y el tuyo (MT4/MT5, Tradovate), y cuántos "
               "segundos pueden separar los cierres de entradas que cuentan como un mismo trade.")
        r = ctk.CTkFrame(f, fg_color="transparent"); r.pack(fill="x")
        self.p_ent = {}
        for key, label, w in [("mt5", "Offset MT4/MT5 (horas)", 110), ("tradovate", "Offset Tradovate (horas)", 110),
                              ("seg", "Agrupar cierres dentro de (seg)", 150)]:
            col = ctk.CTkFrame(r, fg_color="transparent"); col.pack(side="left", padx=(0, SP_LG))
            self._lbl(col, label).pack(anchor="w", pady=(0, SP_XS))
            self.p_ent[key] = styled_entry(col, width=w, mono=True)
            self.p_ent[key].pack()

        bar = ctk.CTkFrame(f, fg_color="transparent"); bar.pack(fill="x", pady=(SP_LG, 0))
        btn_primary(bar, "Guardar perfil", self._guardar_perfil, width=160, height=38).pack(side="left")
        self.p_estado = ctk.CTkLabel(bar, text="", font=(FONT_MONO, 11), text_color=MUTED)
        self.p_estado.pack(side="left", padx=SP_MD)

        titulo("Datos y backups")
        origen = {"argumento": "indicada con --datos", "entorno": "indicada por REGISTRO_DATOS",
                  "portable": "modo portable (junto al programa)", "ubicacion": "carpeta elegida por vos",
                  "appdata": "carpeta estándar del usuario"}.get(CTX.rutas.origen, CTX.rutas.origen)
        ctk.CTkLabel(f, text=CTX.rutas.data_dir, font=(FONT_MONO, 12), text_color=PAPER,
                     justify="left", wraplength=980).pack(anchor="w")
        ctk.CTkLabel(f, text=f"Carpeta de datos — {origen}. Se hace una copia automática por día (backups/).",
                     font=(FONT_MAIN, 12), text_color=MUTED).pack(anchor="w", pady=(SP_XS, SP_SM))
        b = ctk.CTkFrame(f, fg_color="transparent"); b.pack(fill="x")
        for txt, cmd, w in [("Abrir carpeta", lambda: _abrir_carpeta(CTX.rutas.data_dir), 130),
                            ("Cambiar carpeta…", self._cambiar_carpeta, 150),
                            ("Backup ahora", self._backup_ahora, 130),
                            ("Restaurar backup…", self._restaurar_backup, 160)]:
            btn_ghost(b, txt, cmd, width=w, height=34).pack(side="left", padx=(0, SP_SM))

        titulo("Acerca de")
        ctk.CTkLabel(f, text=f"{APP_NAME} v{__version__} — gabomondo\n"
                             "Tipografías DM Sans, JetBrains Mono e Instrument Serif (licencia SIL OFL 1.1).\n"
                             "Tus datos quedan en tu computadora; la app no envía nada a ningún servidor.",
                     font=(FONT_MAIN, 12), text_color=MUTED, justify="left").pack(anchor="w", pady=(0, SP_XL))
        self._cargar_perfil_en_ui()

    def _set_box(self, key, texto):
        tb = self.p_boxes[key]
        tb.delete("1.0", "end")
        tb.insert("1.0", texto)

    def _cargar_perfil_en_ui(self):
        if not hasattr(self, "p_boxes"):
            return
        p = CTX.perfil
        self.p_nombre.delete(0, "end"); self.p_nombre.insert(0, p.nombre)
        for k in ("activos", "tipos", "empresas", "tipos_cuenta"):
            self._set_box(k, "\n".join(getattr(p, k)))
        self._set_box("valor_punto", _pares_a_texto(p.valor_punto))
        self._set_box("comision_contrato", _pares_a_texto(p.comision_contrato))
        for key, val in (("mt5", p.offset_horas.get("mt5", 0)), ("tradovate", p.offset_horas.get("tradovate", 0)),
                         ("seg", p.agrupar_segundos)):
            self.p_ent[key].delete(0, "end"); self.p_ent[key].insert(0, f"{val:g}")

    def _guardar_perfil(self):
        d = {"nombre": self.p_nombre.get().strip()}
        for k in ("activos", "tipos", "empresas", "tipos_cuenta"):
            d[k] = _lista_de_texto(self.p_boxes[k].get("1.0", "end"))
        for k, nombre in (("activos", "Activos"), ("tipos", "Tipos de entrada"), ("tipos_cuenta", "Tipos de cuenta")):
            if not d[k]:
                messagebox.showwarning("Perfil", f"La lista «{nombre}» no puede quedar vacía."); return
        d["valor_punto"], malas1 = _parse_pares(self.p_boxes["valor_punto"].get("1.0", "end"))
        d["comision_contrato"], malas2 = _parse_pares(self.p_boxes["comision_contrato"].get("1.0", "end"))
        if malas1 or malas2:
            messagebox.showwarning("Perfil", "Estas líneas no son válidas (usá SÍMBOLO=número):\n\n" +
                                   "\n".join(malas1 + malas2)); return
        try:
            d["offset_horas"] = {"mt5": float(self.p_ent["mt5"].get().replace(",", ".") or 0),
                                 "tradovate": float(self.p_ent["tradovate"].get().replace(",", ".") or 0)}
            d["agrupar_segundos"] = float(self.p_ent["seg"].get().replace(",", ".") or 0)
        except ValueError:
            messagebox.showwarning("Perfil", "Los offsets y los segundos tienen que ser números."); return
        nuevo = _perfil_mod.Perfil.from_dict(d, base=CTX.perfil)
        _perfil_mod.guardar(CTX.rutas.perfil_path, nuevo)
        CTX.perfil = nuevo
        _db.set_perfil(nuevo)
        self._refrescar_listas()
        self._cargar_perfil_en_ui()
        self.p_estado.configure(text=f"guardado {datetime.now():%H:%M:%S}")

    def _cambiar_carpeta(self):
        if CTX.rutas.origen in ("argumento", "entorno", "portable"):
            messagebox.showinfo(
                "Cambiar carpeta",
                "Esta copia del programa se abrió con una carpeta fija "
                "(--datos, REGISTRO_DATOS o modo portable), así que el cambio no tendría efecto.\n\n"
                "Para usar otra carpeta, abrila con --datos \"ruta\".")
            return
        destino = filedialog.askdirectory(title="Elegí la carpeta nueva para tus datos")
        if not destino or os.path.abspath(destino) == os.path.abspath(CTX.rutas.data_dir):
            return
        copiar = messagebox.askyesnocancel(
            "Cambiar carpeta",
            f"Nueva carpeta:\n{destino}\n\nSí = copiar mis datos ahí y usarla\n"
            "No = usarla tal cual (si ya tiene datos míos)\nCancelar = no hacer nada")
        if copiar is None:
            return
        try:
            if copiar:
                _db.copiar_datos(CTX.rutas.data_dir, destino)
            _paths.guardar_puntero(destino)
        except Exception as e:
            CTX.log.exception("cambiar carpeta")
            messagebox.showerror("Cambiar carpeta", f"No pude hacerlo:\n{e}"); return
        messagebox.showinfo("Cambiar carpeta",
                            "Listo. Cerrá y volvé a abrir la aplicación para usar la carpeta nueva.\n\n"
                            "La carpeta anterior queda intacta como respaldo.")

    def _backup_ahora(self):
        try:
            ruta = _db.crear_backup(CTX.rutas.db_path, CTX.rutas.backups_dir, "manual")
        except Exception as e:
            CTX.log.exception("backup manual")
            messagebox.showerror("Backup", f"No pude crear el backup:\n{e}"); return
        messagebox.showinfo("Backup", f"Copia guardada en:\n{ruta}\n\n"
                                      "Las capturas están en la carpeta 'capturas': respaldala también.")

    def _restaurar_backup(self):
        ruta = filedialog.askopenfilename(title="Elegí el backup a restaurar",
                                          initialdir=CTX.rutas.backups_dir,
                                          filetypes=[("Base de datos", "*.db")])
        if not ruta:
            return
        if not messagebox.askyesno("Restaurar backup",
                                   "Esto reemplaza TODA tu base actual por el backup elegido.\n"
                                   "Antes guardo una copia de la actual por si te arrepentís.\n\n¿Seguir?"):
            return
        try:
            previo = _db.restaurar_backup(ruta, CTX.rutas.db_path, CTX.rutas.backups_dir)
            init_db()
        except Exception as e:
            CTX.log.exception("restaurar backup")
            messagebox.showerror("Restaurar", f"No pude restaurar:\n{e}"); return
        self._reload_all()
        messagebox.showinfo("Restaurar", "Listo, backup restaurado." +
                            (f"\n\nTu base anterior quedó en:\n{previo}" if previo else ""))

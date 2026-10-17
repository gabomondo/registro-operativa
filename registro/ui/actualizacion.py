"""Aviso de versión nueva en la interfaz (AppBase + ActualizacionMixin): consulta en segundo plano al abrir."""
import threading
import time
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

from registro import __version__, actualizaciones as ACT
from registro.ui import vivo
from registro.ui.estado import save_ui_prefs
from registro.ui.tema import FONT_MAIN, HOVER, POS_TXT, RAD_CTRL, SP_SM

vivo.registrar(globals())


class ActualizacionMixin:
    def _build_aviso_actualizacion(self, foot, pie):
        """Botón oculto sobre la versión; se muestra solo si hay una release más nueva."""
        self.btn_actualiz = ctk.CTkButton(
            foot, text="", height=24, corner_radius=RAD_CTRL, fg_color="transparent", hover_color=HOVER,
            text_color=POS_TXT, font=(FONT_MAIN, 11), command=self._abrir_actualizacion)
        self._act_pack = dict(side="bottom", fill="x", after=pie, pady=(SP_SM, 0))
        self._act_info = None
        self._act_res = None

    def _buscar_actualizacion(self):
        """Arranca la consulta (una por día como máximo) si está activada y hay repo configurado."""
        if not ACT.URL_VERSION or not self._ui_prefs.get("buscar_actualizaciones", True):
            return
        if not ACT.toca_consultar(self._ui_prefs.get("ult_chequeo")):
            self._act_mostrar(self._ui_prefs.get("act_pendiente"))     # ya se sabía de una versión nueva
            return

        def trabajo():
            self._act_res = ("listo", ACT.consultar())
        threading.Thread(target=trabajo, daemon=True).start()
        self.after(500, self._act_esperar)

    def _act_esperar(self, n=0):
        if self._act_res is None:
            if n < 40:                       # hasta ~20 s; después se abandona sin ruido
                self.after(500, lambda: self._act_esperar(n + 1))
            return
        info = self._act_res[1]
        self._ui_prefs["ult_chequeo"] = time.time()
        self._ui_prefs["act_pendiente"] = info
        save_ui_prefs(self._ui_prefs)
        self._act_mostrar(info)

    def _act_mostrar(self, info):
        if not info or not ACT.hay_nueva(__version__, info.get("version")):
            return
        if self._ui_prefs.get("act_ignorada") == info["version"]:
            return
        self._act_info = info
        self.btn_actualiz.configure(text=f"↑ Versión {info['version']} disponible")
        self.btn_actualiz.pack(**self._act_pack)

    def _abrir_actualizacion(self):
        info = self._act_info
        if not info:
            return
        notas = (info.get("notas") or "").strip()
        notas = (notas[:600] + "…") if len(notas) > 600 else notas
        r = messagebox.askyesnocancel(
            "Versión nueva",
            f"Hay una versión nueva: {info['version']} (tenés la {__version__}).\n\n"
            + (notas + "\n\n" if notas else "")
            + "Sí = abrir la página de descarga (gabomondo.com) · No = no avisarme de esta versión · Cancelar = más tarde.")
        if r:
            webbrowser.open(info["url"])
        elif r is False:
            self._ui_prefs["act_ignorada"] = info["version"]
            save_ui_prefs(self._ui_prefs)
            self.btn_actualiz.pack_forget()

    def _on_toggle_actualizaciones(self):
        on = bool(self.sw_actualiz.get())
        self._ui_prefs["buscar_actualizaciones"] = on
        save_ui_prefs(self._ui_prefs)
        if not on:
            self.btn_actualiz.pack_forget()

"""Capturas de pantalla: guardado, miniaturas y el cuadro de pegado (CaptureBox)."""

from registro.ui import vivo
import customtkinter as ctk
import os
from PIL import Image
from PIL import ImageGrab
from datetime import datetime
from tkinter import filedialog
from tkinter import messagebox
from registro.ui.estado import BASE_DIR, CAPS_DIR
from registro.ui.tema import (FONT_MAIN, LINE2, MUTED, PAPER, SURFACE)
from registro.ui.util import slugify


def save_capture(pil_img, fecha, activo, tipo, slot):
    """Copia/guarda una PIL image en capturas/ con nombre consistente. Devuelve ruta relativa."""
    stamp = datetime.now().strftime("%H%M%S")
    fname = f"{fecha}_{slugify(activo)}_{slugify(tipo)}_{slot}_{stamp}.png"
    dest = os.path.join(CAPS_DIR, fname)
    pil_img.convert("RGB").save(dest, "PNG")
    return os.path.join("capturas", fname)  # relativa


# Cache de thumbnails a nivel módulo. Clave: (ruta, mtime, size).
# El CTkImage queda vivo acá (ref fuerte), así que el GC no lo recoge y
# no hace falta releer/redimensionar el PNG en cada render de la tabla.
_THUMB_CACHE = {}


def load_thumb(rel_path, size):
    if not rel_path: return None
    p = os.path.join(BASE_DIR, rel_path)
    if not os.path.exists(p): return None
    try:
        key = (p, os.path.getmtime(p), size)
    except OSError:
        return None
    cached = _THUMB_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        img = Image.open(p)
        img.thumbnail(size)
        ci = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        _THUMB_CACHE[key] = ci
        return ci
    except Exception:
        return None


# ----------------------------------------------------------------------------
# Widget de captura (pegar con Ctrl+V, o botón elegir archivo)
# ----------------------------------------------------------------------------
class CaptureBox(ctk.CTkFrame):
    def __init__(self, master, slot, label):
        super().__init__(master, fg_color=SURFACE, border_color=LINE2,
                         border_width=1, corner_radius=8)
        self.slot = slot
        self.label_txt = label
        self.pil_img = None       # PIL en memoria (nueva captura sin guardar)
        self.existing_rel = None  # ruta relativa si viene de edición
        self._preview = None

        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(expand=True, fill="both", padx=8, pady=8)
        self._show_empty()

        # click para pegar / foco
        self.bind("<Button-1>", lambda e: self.focus_set())
        self.inner.bind("<Button-1>", lambda e: self.focus_set())

    def _clear_inner(self):
        for w in self.inner.winfo_children():
            w.destroy()

    def _show_empty(self):
        self._clear_inner()
        ctk.CTkLabel(self.inner, text=self.label_txt, text_color=PAPER,
                     font=(FONT_MAIN, 13)).pack(pady=(18,2))
        ctk.CTkLabel(self.inner, text="Ctrl+V para pegar",
                     text_color=MUTED, font=(FONT_MAIN, 11)).pack()
        ctk.CTkButton(self.inner, text="elegir archivo", width=110, height=26,
                      fg_color="transparent", border_color=LINE2, border_width=1,
                      text_color=PAPER, hover_color=SURFACE,
                      font=(FONT_MAIN, 11), command=self.pick_file).pack(pady=(10,4))

    def _show_preview(self, pil_img):
        self._clear_inner()
        thumb = pil_img.copy()
        thumb.thumbnail((260, 150))
        self._preview = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
        ctk.CTkLabel(self.inner, image=self._preview, text="").pack(pady=(4,4))
        ctk.CTkButton(self.inner, text="quitar", width=70, height=22,
                      fg_color="transparent", border_color=LINE2, border_width=1,
                      text_color=PAPER, hover_color=SURFACE,
                      font=(FONT_MAIN, 11), command=self.clear).pack()

    def paste_from_clipboard(self):
        try:
            img = ImageGrab.grabclipboard()
        except Exception as e:
            messagebox.showwarning("Portapapeles", f"No pude leer el portapapeles:\n{e}")
            return False
        if isinstance(img, Image.Image):
            self.pil_img = img
            self.existing_rel = None
            self._show_preview(img)
            return True
        # en Windows a veces devuelve lista de rutas de archivo
        if isinstance(img, list) and img:
            try:
                loaded = Image.open(img[0])
                self.pil_img = loaded
                self.existing_rel = None
                self._show_preview(loaded)
                return True
            except Exception:
                pass
        return False

    def pick_file(self):
        path = filedialog.askopenfilename(
            title="Elegir captura",
            filetypes=[("Imágenes","*.png *.jpg *.jpeg *.bmp *.gif")])
        if not path: return
        try:
            img = Image.open(path)
            self.pil_img = img
            self.existing_rel = None
            self._show_preview(img)
        except Exception as e:
            messagebox.showerror("Error", f"No pude abrir la imagen:\n{e}")

    def load_existing(self, rel_path):
        self.existing_rel = rel_path
        self.pil_img = None
        p = os.path.join(BASE_DIR, rel_path) if rel_path else None
        if p and os.path.exists(p):
            try:
                self._show_preview(Image.open(p))
                return
            except Exception:
                pass
        self._show_empty()

    def clear(self):
        self.pil_img = None
        self.existing_rel = None
        self._show_empty()

    def commit(self, fecha, activo, tipo):
        """Devuelve la ruta relativa a guardar en DB. Copia la captura nueva si hay."""
        if self.pil_img is not None:
            return save_capture(self.pil_img, fecha, activo, tipo, self.slot)
        return self.existing_rel  # se mantiene la existente (o None)


vivo.registrar(globals())

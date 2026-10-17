"""Reemplazos minimos de tkinter/customtkinter/PIL.ImageTk para poder IMPORTAR la UI sin pantalla."""
import sys, types

class _Dummy:
    def __init__(self, *a, **k): pass
    def __getattr__(self, n): return _Dummy()
    def __call__(self, *a, **k): return _Dummy()

def _mod(nombre):
    m = types.ModuleType(nombre)
    def __getattr__(n):
        if n.startswith("__"): raise AttributeError(n)
        c = type(n, (_Dummy,), {})
        setattr(m, n, c)
        return c
    m.__getattr__ = __getattr__
    return m

def instalar():
    ctk = _mod("customtkinter"); sys.modules["customtkinter"] = ctk
    tk = _mod("tkinter"); sys.modules["tkinter"] = tk
    for sub in ("filedialog", "messagebox", "ttk", "font", "simpledialog", "colorchooser"):
        s = _mod("tkinter." + sub); sys.modules["tkinter." + sub] = s; setattr(tk, sub, s)
    try:
        import PIL.ImageTk  # noqa
    except Exception:
        pit = _mod("PIL.ImageTk"); sys.modules["PIL.ImageTk"] = pit

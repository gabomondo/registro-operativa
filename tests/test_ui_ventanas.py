"""Posición de los diálogos: centrados, dentro del área útil y recortados si no entran."""
from registro.ui.ventanas import calcular_geometria


def _dentro(area, x, y, w, h, esc):
    ax, ay, aw, ah = area
    return x >= ax and y >= ay and x + round(w * esc) <= ax + aw and y + round(h * esc) <= ay + ah


def test_centrado_sobre_la_ventana_principal():
    area, padre = (0, 0, 1920, 1032), (100, 50, 1200, 800)
    w, h, x, y = calcular_geometria(780, 600, 1.0, area, padre)
    assert (w, h) == (780, 600)
    assert x == 100 + (1200 - 780) // 2 and y == 50 + (800 - 600) // 2


def test_caso_real_pantalla_125_con_barra_de_tareas():
    # 1920x1080 al 125%, barra de tareas de 48 px; el popup de Exportar medía ~950 px reales
    area, padre = (0, 0, 1920, 1032), (0, 0, 1917, 1020)
    w, h, x, y = calcular_geometria(780, 760, 1.25, area, padre)
    assert (w, h) == (780, 760)
    assert _dentro(area, x, y, w, h, 1.25)


def test_si_no_entra_se_achica_y_queda_dentro():
    area = (0, 0, 1366, 728)          # notebook chico con barra de tareas
    w, h, x, y = calcular_geometria(1180, 700, 1.25, area, (0, 0, 1366, 700))
    assert h < 700 and w < 1180
    assert _dentro(area, x, y, w, h, 1.25)


def test_ventana_principal_a_medio_salir_no_arrastra_al_popup_afuera():
    area = (0, 0, 1920, 1032)
    w, h, x, y = calcular_geometria(780, 760, 1.0, area, (-400, 600, 1200, 800))
    assert _dentro(area, x, y, w, h, 1.0)


def test_sin_padre_centra_en_el_area():
    area = (0, 0, 1920, 1032)
    w, h, x, y = calcular_geometria(800, 600, 1.0, area, None)
    assert (x, y) == ((1920 - 800) // 2, (1032 - 600) // 2)


def test_segundo_monitor_a_la_izquierda():
    area = (-1920, 0, 1920, 1032)
    w, h, x, y = calcular_geometria(780, 760, 1.0, area, (-1800, 40, 1700, 900))
    assert _dentro(area, x, y, w, h, 1.0)


class _Ventana:
    def __init__(self, rootx=0, rooty=0, w=1900, h=1000, estado="normal", req=(400, 300)):
        self.log, self._r, self._estado, self._req = [], (rootx, rooty, w, h), estado, req

    def update_idletasks(self): pass
    def state(self): return self._estado
    def winfo_rootx(self): return self._r[0]
    def winfo_rooty(self): return self._r[1]
    def winfo_width(self): return self._r[2]
    def winfo_height(self): return self._r[3]
    def winfo_reqwidth(self): return self._req[0]
    def winfo_reqheight(self): return self._req[1]
    def winfo_screenwidth(self): return 1920
    def winfo_screenheight(self): return 1080
    def geometry(self, g): self.log.append(("geometry", g))
    def minsize(self, w, h): self.log.append(("minsize", w, h))
    def resizable(self, a, b): self.log.append(("resizable", a, b))


def test_centrar_dialogo_redimensionable(monkeypatch):
    from registro.ui import ventanas
    monkeypatch.setattr(ventanas, "_area_util", lambda v: (0, 0, 1920, 1032))
    monkeypatch.setattr(ventanas, "DPI_SISTEMA", 1.0)
    win, app = _Ventana(), _Ventana()
    ventanas.centrar_dialogo(win, app, 780, 760, 680, 560)
    assert ("geometry", "780x760+560+120") in win.log
    assert ("minsize", 680, 560) in win.log and ("resizable", True, True) in win.log


def test_centrar_dialogo_fijo_no_se_redimensiona(monkeypatch):
    from registro.ui import ventanas
    monkeypatch.setattr(ventanas, "_area_util", lambda v: (0, 0, 1920, 1032))
    monkeypatch.setattr(ventanas, "DPI_SISTEMA", 1.0)
    win = _Ventana()
    ventanas.centrar_dialogo(win, _Ventana(), 460, 520, redimensionable=False)
    assert ("resizable", False, False) in win.log and not any(l[0] == "minsize" for l in win.log)


def test_principal_minimizada_centra_en_el_area(monkeypatch):
    from registro.ui import ventanas
    monkeypatch.setattr(ventanas, "_area_util", lambda v: (0, 0, 1920, 1032))
    monkeypatch.setattr(ventanas, "DPI_SISTEMA", 1.0)
    win = _Ventana()
    ventanas.centrar_dialogo(win, _Ventana(estado="iconic"), 800, 600)
    assert ("geometry", "800x600+560+216") in win.log


def test_centrar_existente_solo_posiciona(monkeypatch):
    from registro.ui import ventanas
    monkeypatch.setattr(ventanas, "_area_util", lambda v: (0, 0, 1920, 1032))
    win = _Ventana(req=(400, 300))
    ventanas.centrar_existente(win, _Ventana(rootx=100, rooty=50, w=1000, h=700))
    assert win.log == [("geometry", "+400+250")]

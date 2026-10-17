"""Cableado de la UI sin pantalla: tema, fuentes, rutas y escala llegan a todos los módulos.

Corre en un subproceso con tkinter/customtkinter simulados, para no contaminar
al resto de las pruebas ni depender de que haya pantalla."""
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CODIGO = r"""
import sys
sys.path.insert(0, %(tests)r); sys.path.insert(0, %(raiz)r)
import _stubs_gui; _stubs_gui.instalar()
import registro_operativa as ro
from registro.ui import tema, estado, widgets, capturas, vivo, app as ap, nav

assert tema.TEMA_POR_DEFECTO == "claro" and ap.TEMA_ACTUAL == "claro" and ap.MODO == "light"
assert widgets.MUTED == capturas.MUTED == ap.MUTED == nav.MUTED == tema.TEMAS["claro"]["MUTED"]
tema.aplicar_tema("oscuro")
oscuro = tema.TEMAS["oscuro"]
assert widgets.MUTED == capturas.MUTED == ap.MUTED == nav.MUTED == oscuro["MUTED"]
assert ap.TEMA_ACTUAL == "oscuro" and ap.MODO == "dark"
tema.aplicar_tema("no_existe")
assert ap.TEMA_ACTUAL == "claro"      # un nombre inválido cae al tema por defecto
from registro.ui.dialogos import importar, exportar, acerca, riesgo
tema.aplicar_tema("oscuro")      # los diálogos también reciben el tema y las fuentes
for m in (importar, exportar, acerca, riesgo):
    assert m.MUTED == oscuro["MUTED"] and m.PAPER == oscuro["PAPER"], m.__name__
assert (ro.ImportarDialog is importar.ImportarDialog and ro.ExportarDialog is exportar.ExportarDialog
        and ro.AcercaDialog is acerca.AcercaDialog and ro.RiesgoDialog is riesgo.RiesgoDialog)
from registro.ui.pantallas import calendario, notebook, playbooks, simulador, plantillas, analisis, revision, plan, cargar, comunes, perfil, datos_io, cuentas, portfolio as portfolio_ui
from registro.ui.pantallas import registro as reg
from registro.ui import selector, periodo, modo
tema.aplicar_tema("oscuro")      # las pantallas (Mixins) también reciben el tema
for m in (calendario, notebook, playbooks, simulador, plantillas, analisis, revision, plan, cargar, comunes, reg, perfil, cuentas, selector, periodo, portfolio_ui):
    assert m.MUTED == oscuro["MUTED"] and m.PAPER == oscuro["PAPER"], m.__name__
assert all(issubclass(ro.App, c) for c in (calendario.CalendarioMixin, notebook.NotebookMixin, playbooks.PlaybooksMixin,
                                          simulador.SimuladorMixin, plantillas.PlantillasMixin, analisis.AnalisisMixin,
                                          revision.RevisionMixin, plan.PlanMixin, cargar.CargarMixin,
                                          comunes.ComunesMixin, reg.RegistroMixin, perfil.PerfilMixin,
                                          datos_io.DatosIOMixin, cuentas.CuentasMixin, selector.SelectorMixin, periodo.PeriodoMixin, portfolio_ui.PortfolioMixin, modo.ModoMixin))
assert all(hasattr(ro.App, f) for f in ("render_playbooks", "render_simulador", "render_plantillas", "render_analisis", "render_revision", "render_table", "render_cuentas", "_menu_cuenta", "_elegir_cuenta", "_menu_periodo", "_elegir_periodo", "render_portfolio", "_m", "_on_modo"))
assert hasattr(ro.App, "render_calendario") and hasattr(ro.App, "render_notebook") and ro.App.NB_CAMPOS
tema.aplicar_tema("claro")
vivo.publicar(FONT_MAIN="F1")
assert widgets.FONT_MAIN == capturas.FONT_MAIN == ap.FONT_MAIN == nav.FONT_MAIN == calendario.FONT_MAIN == "F1"

class R: data_dir = "/d"; caps_dir = "/d/c"; ui_prefs_path = "/d/ui.json"
class L:
    def info(self, *a): pass
class C: rutas = R(); log = L()
estado.iniciar = lambda argv=None: C()
ro._arrancar([])
assert (reg.BASE_DIR, capturas.BASE_DIR, capturas.CAPS_DIR, estado.UI_PREFS) == ("/d", "/d", "/d/c", "/d/ui.json")
assert ap.CTX is estado.CTX is notebook.CTX
vivo.publicar(DPI_SISTEMA=1.5)
assert widgets.DPI_SISTEMA == estado.DPI_SISTEMA == ap.DPI_SISTEMA == 1.5
# el shell vive en ui/app.py y las secciones en ui/nav.py; App los hereda
assert issubclass(ro.App, ap.AppBase) and ro.App.SECCIONES is nav.SECCIONES
assert "Cuentas" in [n for _g, n, _s in nav.SECCIONES] and "Registro" in [n for _g, n, _s in nav.SECCIONES] and ap.UI_SCALES["mediano"] == 1.15
print("OK")
"""


def test_cableado_ui_sin_pantalla():
    codigo = CODIGO % {"tests": os.path.join(RAIZ, "tests"), "raiz": RAIZ}
    r = subprocess.run([sys.executable, "-I", "-c", codigo], capture_output=True, text=True, cwd=RAIZ)
    assert r.returncode == 0 and r.stdout.strip().endswith("OK"), r.stdout + r.stderr


CODIGO_REINICIO = r"""
import sys, types
sys.path.insert(0, %(tests)r); sys.path.insert(0, %(raiz)r)
import _stubs_gui; _stubs_gui.instalar()
import registro_operativa as ro
from registro.ui import app as ap

lanzados, guardados = [], []
ap.subprocess = types.SimpleNamespace(Popen=lambda args, **kw: lanzados.append((args, kw)),
                                      DEVNULL=-3)
ap.save_ui_prefs = lambda p: guardados.append(dict(p))
ap.CTX = types.SimpleNamespace(log=types.SimpleNamespace(exception=lambda *a, **k: None))

class Falsa:
    _nb_job = None
    def __init__(self): self.cerrada = False; self._ui_prefs = {}
    def destroy(self): self.cerrada = True
    def _reiniciar(self): return ro.App._reiniciar(self)
    def _nb_guardar(self): self.guardo_nota = True

# reinicio: relanza con los mismos argumentos y cierra
sys.argv = ["registro_operativa.py", "--datos", "C:/x", "--perfil", "gabo"]
f = Falsa(); ro.App._reiniciar(f)
args, kw = lanzados[0]
assert args[0] == sys.executable and args[-4:] == ["--datos", "C:/x", "--perfil", "gabo"], args
assert args[1].endswith("registro_operativa.py") and f.cerrada

# nota pendiente: se guarda antes de cerrar
f = Falsa(); f._nb_job = "x"; ro.App._reiniciar(f)
assert getattr(f, "guardo_nota", False)

# alternar tema: pregunta, guarda la preferencia nueva y reinicia; si dice que no, no toca nada
ap.messagebox = types.SimpleNamespace(askyesno=lambda *a, **k: False, showerror=lambda *a, **k: None)
f = Falsa(); n = len(guardados); ro.App._alternar_tema(f)
assert not f.cerrada and len(guardados) == n
ap.messagebox = types.SimpleNamespace(askyesno=lambda *a, **k: True, showerror=lambda *a, **k: None)
f = Falsa(); ro.App._alternar_tema(f)
assert guardados[-1]["tema"] == "oscuro" and f.cerrada      # el tema actual (por defecto) es "claro"

# si Popen falla: avisa y NO cierra
ap.subprocess = types.SimpleNamespace(Popen=lambda *a, **k: (_ for _ in ()).throw(OSError("x")), DEVNULL=-3)
f = Falsa(); ro.App._reiniciar(f)
assert not f.cerrada
print("OK")
"""


def test_reinicio_y_cambio_de_tema():
    codigo = CODIGO_REINICIO % {"tests": os.path.join(RAIZ, "tests"), "raiz": RAIZ}
    r = subprocess.run([sys.executable, "-I", "-c", codigo], capture_output=True, text=True, cwd=RAIZ)
    assert r.returncode == 0 and r.stdout.strip().endswith("OK"), r.stdout + r.stderr

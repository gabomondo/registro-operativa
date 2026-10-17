"""Prueba de humo de la interfaz (necesita pantalla; en Linux: xvfb-run -a python tests/smoke_ui.py DATOS [OUT_PNG_DIR]).
Abre la app contra una carpeta de datos, recorre todas las pestañas, guarda un perfil
y carga una operación. Los diálogos se interceptan y se imprimen."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tkinter import messagebox
dialogos = []
for n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, n, (lambda nombre: lambda *a, **k: dialogos.append((nombre, a[0], (a[1] if len(a) > 1 else "")[:90])))(n))
messagebox.askyesno = lambda *a, **k: True

import registro_operativa as ro
datos = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else None
argv = ["--datos", datos] + sys.argv[3:]
ro._enable_dpi_awareness(); ro._resolve_fonts()
ctx = ro._arrancar(argv)
print("perfil:", ctx.perfil.nombre, "| migración:", ctx.migracion["desde"], "->", ctx.migracion["hasta"])
app = ro.App(); app.update()
print("fuentes:", ro.FONT_MAIN, ro.FONT_MONO, ro.FONT_SERIF)

def shot(nombre):
    if not out: return
    from PIL import ImageGrab
    app.update_idletasks(); app.update()
    ImageGrab.grab().save(os.path.join(out, nombre + ".png"))

app.geometry("1280x900+0+0")
for tab in ["Plan", "Cargar operación", "Registro", "Revisión semanal", "Plantillas", "Perfil"]:
    app.tabs.set(tab); app._on_tab_change(); app.update()
    shot("tab_" + tab.split()[0].lower())
print("pestañas ok:", app.tabs._name_list if hasattr(app.tabs, "_name_list") else "")

# --- perfil: editar y guardar
app.tabs.set("Perfil"); app._on_tab_change()
app._set_box("activos", "EURUSD\nUSTEC\nNQ")
app._set_box("tipos_cuenta", "Real\nDemo")
app._set_box("comision_contrato", "MNQ=0.74")
app.p_ent["mt5"].delete(0, "end"); app.p_ent["mt5"].insert(0, "-3")
app._guardar_perfil()
p = json.load(open(ctx.rutas.perfil_path, encoding="utf-8"))
assert p["activos"] == ["EURUSD", "USTEC", "NQ"] and p["comision_contrato"] == {"MNQ": 0.74}
assert p["offset_horas"]["mt5"] == -3.0, p["offset_horas"]
assert app.e_activo.cget("values")[:3] == ["EURUSD", "USTEC", "NQ"]
print("perfil guardado y combos actualizados ok")
# validación: lista vacía
app._set_box("tipos", ""); app._guardar_perfil()
assert dialogos and dialogos[-1][0] == "showwarning", dialogos
app._cargar_perfil_en_ui()

# --- cargar una operación
app.tabs.set("Cargar operación"); app._on_tab_change(); app.update()
n0 = len(ro.db_all())
app.e_profit.delete(0, "end"); app.e_profit.insert(0, "123.5")
app.save_op(); app.update()
n1 = len(ro.db_all())
print("operaciones:", n0, "->", n1, "| último fuente:", ro.db_all()[-1]["fuente"])
assert n1 == n0 + 1
app.tabs.set("Registro"); app._on_tab_change(); app.update(); shot("registro_final")

# --- calendario, notebook, playbooks, simulador, reporte
app.tabs.set("Calendario"); app._on_tab_change(); app.update()
app._cal_nav(-1); app._cal_nav(1); app._cal_ultimo(); app.update()
hoy = ro.date.today().isoformat()
app._abrir_nota(hoy); app.update()
assert app.tabs.get() == "Notebook"
app.nb_boxes["que_paso"].insert("1.0", "nota de prueba"); app._nb_guardar()
assert ro.db_nota_get(hoy)["que_paso"] == "nota de prueba"
app.tabs.set("Playbooks"); app._on_tab_change(); app.update()
app._pb_nuevo(); app.pb_nombre.insert(0, "Breakout test"); app.pb_reglas.insert("1.0", "regla 1")
app._pb_guardar(); app.update()
assert [p["nombre"] for p in ro.db_playbooks()] == ["Breakout test"]
assert "Breakout test" in ro.merged_values([], "tipo")
app.tabs.set("Cuentas"); app._on_tab_change(); app.update()
app._cu_nueva(); app.cu_empresa.set("Apex"); app.cu_cuenta.insert(0, "A1"); app.cu_capital.insert(0, "50k")
app.cu_estado.set("Evaluación"); app._cu_guardar(); app.update()
assert [(c["empresa"], c["estado"], c["capital_inicial"]) for c in __import__("registro.db", fromlist=["x"]).db_cuentas()][-1] == ("Apex", "evaluacion", 50000.0)
_c = [c for c in __import__("registro.db", fromlist=["x"]).db_cuentas() if c["empresa"] == "Apex"][0]
app._elegir_cuenta(_c); app.update()
assert app.btn_cuenta.cget("text").startswith("Apex") and ro.db_all() == []
app._elegir_cuenta(None); app.update()
app.tabs.set("Registro"); app._on_tab_change(); app.update(); assert app._periodo_visible
app._elegir_periodo("Este mes"); app.update()
app._elegir_periodo(None, ("2000-01-01", "2000-01-02")); app.update()
assert ro.db_all() == [] and len(ro.db_all(todo=True)) >= 1
app._elegir_periodo("Todo el período"); app.update()
app.tabs.set("Calendario"); app._on_tab_change(); app.update(); assert not app._periodo_visible
app.tabs.set("Portfolio"); app._on_tab_change(); app.update()
assert app._periodo_visible and app._modo_visible
app._on_modo("Porcentaje"); app.update(); app._on_modo("Dinero"); app.update()
app.tabs.set("Playbooks"); app._on_tab_change(); app.update(); assert not app._modo_visible
app.tabs.set("Simulador"); app._on_tab_change(); app.update()
app.sim_ent["max_trades"].insert(0, "1"); app.render_simulador(); app.update()
app.tabs.set("Revisión semanal"); app._on_tab_change(); app.update()
app._an_psico  # existe
app.tabs.set("Análisis"); app._on_tab_change(); app.update()
print("pantallas nuevas ok")
print("diálogos:", dialogos)
app.destroy(); print("SMOKE OK")

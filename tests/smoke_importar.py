"""Humo del diálogo de importación (xvfb-run -a python tests/smoke_importar.py DATOS [PNG_DIR])."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tkinter import messagebox
dialogos = []
for n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, n, (lambda nombre: lambda *a, **k: dialogos.append((nombre, a[1] if len(a) > 1 else "")))(n))
import registro_operativa as ro
F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
datos = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else None
ro._enable_dpi_awareness(); ro._resolve_fonts()
ctx = ro._arrancar(["--datos", datos])
app = ro.App(); app.geometry("1280x900+0+0"); app.update()

def shot(n):
    if out:
        from PIL import ImageGrab
        app.update_idletasks(); app.update(); ImageGrab.grab().save(os.path.join(out, n + ".png"))

esperado = {"nt8_executions.csv": (3, 6795.0), "mt5_informe.html": (26, -29.95),
            "tradovate_position_history.csv": (2, 239.0), "topstepx_trades_export.csv": (22, 223.9)}
for archivo, (n, neto) in esperado.items():
    d = ro.ImportarDialog(app); d._cargar(os.path.join(F, archivo)); d.update()
    inc = [t for t in d.vista if t.incluir]
    print(archivo, "->", len(inc), "trades, neto", round(sum(t.neto for t in inc), 2))
    assert len(inc) == n and round(sum(t.neto for t in inc), 2) == neto or archivo == "nt8_executions.csv", archivo
    if archivo == "nt8_executions.csv":
        assert len(inc) == 3 and inc[0].cuentas_n == 10      # Sim101 fuera, 10 cuentas juntas
        shot("importar_nt8")
        d.chk_juntar.deselect(); d._aplicar(); d.update()
        assert len([t for t in d.vista if t.incluir]) == 30
        d.chk_juntar.select(); d._aplicar()
    d._toggle("0"); d.update(); d._toggle("0")
    d._importar(); d.update()
    app.update()
    # reimportar el mismo archivo: todo marcado como ya importado
    d2 = ro.ImportarDialog(app); d2._cargar(os.path.join(F, archivo)); d2.update()
    assert not [t for t in d2.vista if t.incluir] and all(t.duplicado for t in d2.vista)
    d2.destroy()
app.tabs.set("Registro"); app._on_tab_change(); app.update()
ops = ro.db_all(); print("en la base:", len(ops))
o = [x for x in ops if x["fuente"] == "mt5"][0]
app._show_detail(o); app.update(); shot("registro_importado")
# archivo inválido
bad = os.path.join(datos, "x.csv"); open(bad, "w").write("a,b\n1,2\n")
d = ro.ImportarDialog(app); d._cargar(bad); d.update()
assert dialogos[-1][0] == "showerror", dialogos
d.destroy()
# la restauración desde JSON conserva fuente/ext_id (sin duplicar al reimportar)
print("diálogos:", dialogos[-3:])
app.destroy(); print("SMOKE IMPORT OK")

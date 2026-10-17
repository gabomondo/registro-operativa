# -*- mode: python ; coding: utf-8 -*-
# Empaquetado con PyInstaller (modo carpeta, más rápido de abrir y con menos
# falsos positivos de antivirus que --onefile):  pyinstaller --noconfirm --clean registro_operativa.spec
from PyInstaller.utils.hooks import collect_data_files

import os

datas = collect_data_files("customtkinter") + [
    ("assets/fonts", "assets/fonts"),        # tipografías (OFL)
    ("assets/icono.ico", "assets"),          # logo de «Acerca de»
    ("perfiles/neutro.json", "perfiles"),    # preset neutro: viaja siempre
]
# Solo el build PERSONAL (build.bat gabo) lleva el preset gabo. build.bat pone RO_PERSONAL=1.
# El build público lo deja vacío, y además build.bat aborta si encuentra gabo.json en él.
if os.environ.get("RO_PERSONAL") == "1":
    datas.append(("perfiles/gabo.json", "perfiles"))

a = Analysis(
    ["registro_operativa.py"],
    pathex=["."],
    datas=datas,
    hiddenimports=["PIL._tkinter_finder", "registro.importadores", "registro.importadores.nt8", "registro.importadores.mt5", "registro.importadores.mt4", "registro.importadores.deepcharts", "registro.importadores.tradovate", "registro.importadores.topstepx", "registro.ui", "registro.ui.vivo", "registro.ui.tema", "registro.ui.estado", "registro.ui.util", "registro.ui.capturas", "registro.ui.widgets", "registro.ui.ventanas", "registro.ui.nav", "registro.ui.pantallas.datos_io", "registro.ui.pantallas.cuentas", "registro.ui.pantallas.portfolio", "registro.portfolio", "registro.ui.selector", "registro.ui.periodo", "registro.ui.modo", "registro.ui.actualizacion", "registro.actualizaciones", "registro.unidades", "registro.periodos", "registro.cuentas", "registro.ui.pantallas.perfil", "registro.ui.disposicion", "registro.ui.pantallas.registro", "registro.ui.pantallas.comunes", "registro.ui.pantallas.cargar", "registro.ui.pantallas.plan", "registro.ui.pantallas.revision", "registro.ui.pantallas.analisis", "registro.ui.pantallas.plantillas", "registro.ui.pantallas.simulador", "registro.ui.pantallas.playbooks", "registro.ui.pantallas.notebook", "registro.ui.pantallas.calendario", "registro.ui.pantallas", "registro.ui.app", "registro.ui.dialogos", "registro.ui.dialogos.importar", "registro.ui.dialogos.exportar", "registro.ui.dialogos.acerca", "registro.ui.dialogos.riesgo", "registro.exportar", "registro.exportar_pdf", "registro.metricas", "openpyxl", "fpdf"],
    # OJO: NO excluir unittest.mock: fpdf2 (fpdf/sign.py) lo importa al cargar y el PDF fallaba con "Falta el componente".
    excludes=["pytest", "pydoc", "doctest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="RegistroOperativa",
    console=False,                 # sin ventana de consola
    icon="assets/icono.ico",
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="RegistroOperativa", upx=False)

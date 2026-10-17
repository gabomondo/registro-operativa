import csv
import os

import pytest

from registro import exportar as EX


def _rows():
    base = [("2026-10-01", "09:40", 120.0, "NQ", "Cuenta real", "Topstep", "Ruptura", "Salí bien"),
            ("2026-10-01", "10:15", -45.5, "NQ", "Cuenta real", "Topstep", "Ruptura", ""),
            ("2026-10-02", "09:35", -80.0, "MNQ", "Eval", "Apex", "Pullback", "Entré tarde"),
            ("2026-10-05", "10:05", 200.0, "NQ", "Cuenta real", "Topstep", "Pullback", "")]
    return [dict(fecha=f, hora=h, profit=p, activo=a, cuenta=c, empresa=e, tipo=t,
                 comentario=co, contratos=1, lado="Long", bruto=p + 2, comision=2.0, emo=3)
            for f, h, p, a, c, e, t, co in base]


def _D(**op):
    return EX.armar(_rows(), "Test", "2026-10-01 a 2026-10-05", "", op)


@pytest.mark.parametrize("fmt,ext", [("pdf", ".pdf"), ("html", ".html"), ("xlsx", ".xlsx"), ("csv", ".csv")])
def test_exporta_todos_los_formatos(tmp_path, fmt, ext):
    ruta = tmp_path / f"r{ext}"
    EX.exportar(fmt, _D(), str(ruta))
    assert ruta.exists() and ruta.stat().st_size > 200
    assert not [p for p in tmp_path.iterdir() if p.name != ruta.name]   # sin temporales


def test_csv_separador_y_comentarios(tmp_path):
    ruta = tmp_path / "r.csv"
    EX.exportar("csv", _D(csv_sep=";", comentarios=True), str(ruta))
    txt = ruta.read_text(encoding="utf-8-sig")
    assert ";" in txt.splitlines()[0] and "Entré tarde" in txt
    EX.exportar("csv", _D(csv_sep=","), str(ruta))
    assert "Entré tarde" not in ruta.read_text(encoding="utf-8-sig")


def test_anonimizar_oculta_nombres(tmp_path):
    ruta = tmp_path / "r.html"
    EX.exportar("html", _D(anonimizar=True), str(ruta))
    h = ruta.read_text(encoding="utf-8")
    assert "Topstep" not in h and "Apex" not in h and "Eval" not in h and "Cuenta A" in h


def test_comentarios_solo_si_se_piden(tmp_path):
    ruta = tmp_path / "r.html"
    EX.exportar("html", _D(comentarios=False), str(ruta))
    assert "Entré tarde" not in ruta.read_text(encoding="utf-8")
    EX.exportar("html", _D(comentarios=True), str(ruta))
    assert "Entré tarde" in ruta.read_text(encoding="utf-8")


def test_html_marca_opcional(tmp_path):
    ruta = tmp_path / "r.html"
    EX.exportar("html", _D(marca=False), str(ruta))
    assert "Hecho con Registro de operativa" not in ruta.read_text(encoding="utf-8")
    EX.exportar("html", _D(marca=True), str(ruta))
    assert "Hecho con Registro de operativa" in ruta.read_text(encoding="utf-8")


def test_sin_operaciones_da_error_amigable(tmp_path):
    D = EX.armar([], "Vacío", "", "", {})
    assert D["n"] == 0
    with pytest.raises(EX.ExportError):
        EX.exportar("csv", D, str(tmp_path / "x.csv"))


def test_ruta_invalida_da_exporterror(tmp_path):
    with pytest.raises(EX.ExportError):
        EX.exportar("html", _D(), str(tmp_path / "no_existe" / "x.html"))


def test_secciones_elegidas(tmp_path):
    D = _D(secciones=["resumen"])
    assert D["secciones"] == ["resumen"]
    ruta = tmp_path / "r.html"
    EX.exportar("html", D, str(ruta))
    assert "Detalle de operaciones" not in ruta.read_text(encoding="utf-8")


def test_nombre_sugerido():
    assert EX.nombre_sugerido(_D(), ".pdf") == "registro-operativa_2026-10-01_a_2026-10-05.pdf"


def test_xlsx_tiene_hojas(tmp_path):
    import openpyxl
    ruta = tmp_path / "r.xlsx"
    EX.exportar("xlsx", _D(), str(ruta))
    wb = openpyxl.load_workbook(ruta)
    assert len(wb.sheetnames) >= 3

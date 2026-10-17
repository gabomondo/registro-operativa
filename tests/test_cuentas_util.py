"""Utilidades puras de la pantalla Cuentas."""
import pytest

from registro import cuentas as Q


@pytest.mark.parametrize("txt,esperado", [
    ("", None), ("  ", None), ("50000", 50000.0), ("50.000", 50000.0), ("50,000", 50000.0),
    ("$ 50k", 50000.0), ("2.5k", 2500.0), ("1.250.000", 1250000.0), ("1,250,000.50", 1250000.5),
    ("25000,5", 25000.5), ("0", 0.0)])
def test_parse_capital(txt, esperado):
    assert Q.parse_capital(txt) == esperado


@pytest.mark.parametrize("txt", ["abc", "-5", "5x", "k"])
def test_parse_capital_invalido(txt):
    with pytest.raises(ValueError):
        Q.parse_capital(txt)


def test_fmt_capital():
    assert Q.fmt_capital(None) == "" and Q.fmt_capital(50000.0) == "50000" and Q.fmt_capital(1234.5) == "1234.50"


def test_parse_fecha():
    from datetime import date
    assert Q.parse_fecha("") == date.today().isoformat()
    assert Q.parse_fecha("2026-10-10") == "2026-10-10"
    for mala in ("10/10/2026", "2026-13-01", "ayer"):
        with pytest.raises(ValueError):
            Q.parse_fecha(mala)


def test_titulo_detalle_y_claves():
    c = dict(empresa="Lucid", cuenta="50K-1", alias="Principal", estado="fondeada", tipo="futuros")
    assert Q.titulo(c) == "Principal" and Q.detalle(c) == "Lucid · 50K-1  ·  Fondeada  ·  Futuros"
    assert Q.titulo(dict(empresa="Apex", cuenta="A1")) == "Apex · A1" and Q.detalle(dict(empresa="Apex", cuenta="A1")) == ""
    assert Q.titulo(dict(empresa="", cuenta="")) == "(sin nombre)"
    assert Q.clave_estado("Demo (testeo)") == "demo" and Q.clave_estado(Q.SIN) is None
    assert Q.clave_tipo("CFD") == "cfd" and Q.clave_tipo(Q.SIN) is None
    assert Q.etiquetas_estado()[0] == Q.SIN and len(Q.etiquetas_estado()) == 6


def test_agrupar_y_texto_selector():
    cs = [dict(empresa="Lucid", cuenta="B", alias="Zeta"), dict(empresa="Apex", cuenta="A1"),
          dict(empresa="Lucid", cuenta="A", alias=None), dict(empresa="", cuenta="x")]
    g = Q.agrupar_por_empresa(cs)
    assert [e for e, _ in g] == ["Apex", "Lucid", "Sin empresa"]
    assert [Q.titulo(c) for c in g[1][1]] == ["Lucid · A", "Zeta"]
    assert Q.clave(cs[0]) == ("Lucid", "B") and Q.clave(None) is None
    assert Q.texto_selector(cs, None) == Q.TODAS
    assert Q.texto_selector(cs, ("Lucid", "B")) == "Zeta"
    assert Q.texto_selector(cs, ["Apex", "A1"]) == "Apex · A1"
    assert Q.texto_selector([], ("Gone", "9")) == "Gone · 9"


def test_filtros_de_cuentas():
    cs = [dict(empresa="Lucid", cuenta="1", estado="fondeada", tipo="futuros"),
          dict(empresa="Lucid", cuenta="2", estado="evaluacion", tipo="futuros"),
          dict(empresa="Exness", cuenta="3", estado=None, tipo="cfd"),
          dict(empresa="Apex", cuenta="4", estado="fondeada", tipo=None)]
    ids = lambda r: [c["cuenta"] for c in r]
    assert ids(Q.filtrar(cs)) == ["1", "2", "3", "4"]
    assert ids(Q.filtrar(cs, estado="fondeada")) == ["1", "4"]
    assert ids(Q.filtrar(cs, estado="__sin__")) == ["3"]
    assert ids(Q.filtrar(cs, empresa="Lucid")) == ["1", "2"]
    assert ids(Q.filtrar(cs, tipo="cfd")) == ["3"]
    assert ids(Q.filtrar(cs, estado="fondeada", empresa="Lucid", tipo="futuros")) == ["1"]
    assert Q.filtrar(cs, empresa="Nada") == []
    assert Q.opciones_empresa(cs) == [Q.TODOS, "Apex", "Exness", "Lucid"]
    assert Q.opciones_estado()[0] == Q.TODOS and Q.opciones_estado()[-1] == Q.SIN_ETIQUETA
    assert Q.opciones_tipo() == [Q.TODOS, "Futuros", "CFD"]
    assert Q.clave_filtro_estado(Q.TODOS) is None and Q.clave_filtro_estado(Q.SIN_ETIQUETA) == "__sin__"
    assert Q.clave_filtro_estado("Fondeada") == "fondeada"

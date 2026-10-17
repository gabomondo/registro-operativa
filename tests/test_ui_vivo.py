"""El registro `vivo` reparte valores publicados a los módulos suscriptos (sin pantalla)."""
from registro.ui import vivo


def _ns(**kw):
    return dict(kw)


def test_publicar_actualiza_solo_nombres_existentes():
    a, b = _ns(MUTED="x", OTRO=1), _ns(PAPER="p")
    vivo.registrar(a); vivo.registrar(b)
    vivo.publicar(MUTED="nuevo", PAPER="papel", NO_ESTA="z")
    assert a["MUTED"] == "nuevo" and a["OTRO"] == 1 and "PAPER" not in a
    assert b["PAPER"] == "papel" and "MUTED" not in b and "NO_ESTA" not in a and "NO_ESTA" not in b


def test_registrar_recibe_valores_ya_publicados():
    vivo.publicar(VALOR_TARDIO_T=42)
    ns = _ns(VALOR_TARDIO_T=0)
    vivo.registrar(ns)
    assert ns["VALOR_TARDIO_T"] == 42


def test_registrar_dos_veces_no_duplica():
    ns = _ns(DUP_T=1)
    n0 = len(vivo._NAMESPACES)
    vivo.registrar(ns); vivo.registrar(ns)
    assert len(vivo._NAMESPACES) == n0 + 1

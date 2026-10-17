import io
import json

from registro import actualizaciones as ACT


class _R(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


def _abrir(data):
    return lambda url: _R(json.dumps(data).encode())


def test_versiones():
    assert ACT.parse_version("v1.2.3") == (1, 2, 3) and ACT.parse_version("1.2") == (1, 2, 0)
    assert ACT.parse_version("hola") is None and ACT.parse_version(None) is None
    assert ACT.hay_nueva("1.0.0", "v1.0.1") and ACT.hay_nueva("1.9.0", "v1.10.0")
    assert not ACT.hay_nueva("1.0.0", "v1.0.0") and not ACT.hay_nueva("1.1.0", "v1.0.9")
    assert not ACT.hay_nueva("1.0.0", "basura")


def test_info_version():
    r = ACT.info_version(dict(version="v1.2.0", notas=" cosas "))
    assert r == dict(version="1.2.0", url=ACT.PAGINA, notas="cosas")
    assert ACT.info_version(dict(version="x")) is None and ACT.info_version(None) is None


def test_intervalo():
    assert ACT.toca_consultar(None) and ACT.toca_consultar("x")
    assert not ACT.toca_consultar(1000, ahora=1000 + 60)
    assert ACT.toca_consultar(1000, ahora=1000 + ACT.INTERVALO_S)


def test_consultar():
    rel = dict(version="2.0.0", notas="")
    assert ACT.consultar("http://x", "1.0.0", _abrir(rel))["version"] == "2.0.0"
    assert ACT.consultar("http://x", "2.0.0", _abrir(rel)) is None      # ya está al día
    assert ACT.consultar("", "1.0.0", _abrir(rel)) is None               # función apagada
    def falla(url): raise OSError("sin red / 404")
    assert ACT.consultar("http://x", "1.0.0", falla) is None             # nunca explota

import json, os
from registro import perfil as P

def test_from_dict_tolerante_a_basura():
    p = P.Perfil.from_dict({"activos": "no es lista", "tipos": ["A", "a", " ", 3, "B"],
                            "valor_punto": {"nq": "20", "x": "abc", "y": -1},
                            "agrupar_segundos": 999, "plantilla_inicial": {"nombre": "x", "items": "mal"}})
    assert p.activos == P.Perfil().activos            # inválido -> default
    assert p.tipos == ["A", "B"]                      # dedup case-insensitive, sin vacíos
    assert p.valor_punto == {"NQ": 20.0}              # normaliza mayúsculas y descarta inválidos
    assert p.agrupar_segundos == 60                   # acotado
    assert p.plantilla_inicial["nombre"] == "Check básico"

def test_valor_punto_de_simbolos_reales():
    p = P.Perfil()
    assert p.valor_punto_de("MNQ DEC26") == 2.0
    assert p.valor_punto_de("MNQZ6") == 2.0
    assert p.valor_punto_de("NQ 12-26") == 20.0
    assert p.valor_punto_de("USTEC") is None

def test_crear_neutro_por_defecto(tmp_path):
    path = str(tmp_path / "perfil.json")
    p, nuevo = P.cargar_o_crear(path, str(tmp_path / "registro.db"))
    assert nuevo and p.nombre == "Neutro" and os.path.exists(path)
    p2, nuevo2 = P.cargar_o_crear(path, str(tmp_path / "registro.db"))
    assert not nuevo2 and p2.to_dict() == p.to_dict()

def test_preset_inexistente_cae_al_neutro(tmp_path):
    p, _ = P.cargar_o_crear(str(tmp_path / "perfil.json"), str(tmp_path / "x.db"), preset="no_existe")
    assert p.nombre == "Neutro"

def test_base_vieja_con_operaciones_hereda_preset_gabo(legacy_dir):
    p, nuevo = P.cargar_o_crear(str(legacy_dir / "perfil.json"), str(legacy_dir / "registro.db"))
    assert nuevo and p.nombre.startswith("Gabo") and "TopStep" in p.empresas

def test_perfil_corrupto_se_aparta(tmp_path):
    path = tmp_path / "perfil.json"; path.write_text("{no json")
    p, nuevo = P.cargar_o_crear(str(path), str(tmp_path / "x.db"))
    assert nuevo and p.nombre == "Neutro"
    assert any(f.startswith("perfil.json.corrupto") for f in os.listdir(tmp_path))

def test_guardar_es_atomico_y_legible(tmp_path):
    path = str(tmp_path / "perfil.json")
    p = P.Perfil(); p.activos = ["EURUSD"]; P.guardar(path, p)
    assert json.load(open(path, encoding="utf-8"))["activos"] == ["EURUSD"]
    assert not os.path.exists(path + ".tmp")

def test_empresas_se_puede_vaciar_pero_activos_no():
    base = P.Perfil(empresas=["X"], activos=["NQ"])
    p = P.Perfil.from_dict({"empresas": [], "activos": []}, base=base)
    assert p.empresas == [] and p.activos == ["NQ"]

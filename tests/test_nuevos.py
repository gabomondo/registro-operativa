import pytest
from registro import db, bootstrap, calendario, psico, simulador, reporte


def op(fecha, hora, profit, **kw):
    d = dict(id=1, fecha=fecha, hora=hora, profit=profit, emo=None, tranquilo=None,
             mov_sl=None, tipo=None, chk_data="{}", hora_fin=None)
    d.update(kw)
    return d


# ---------- calendario ----------
def test_grilla_totales_y_semanas():
    rows = [op("2026-10-05", "10:00", 100), op("2026-10-05", "11:00", -30),
            op("2026-10-07", "10:00", -50), op("2026-10-14", "10:00", 20)]
    g = calendario.grilla(2026, 10, calendario.resumen_dias(rows))
    assert g["total"] == 40 and g["n"] == 4 and g["dias_op"] == 3
    assert g["verdes"] == 2 and g["rojos"] == 1 and not g["con_finde"]
    sem = [s for s in g["semanas"] if s["neto"] is not None]
    assert [s["neto"] for s in sem] == [20, 20]
    assert all(len(s["celdas"]) == 7 for s in g["semanas"])
    # los días de otro mes no suman
    assert sum(1 for s in g["semanas"] for c in s["celdas"] if c["en_mes"]) == 31


def test_grilla_detecta_finde_y_navegacion():
    g = calendario.grilla(2026, 10, calendario.resumen_dias([op("2026-10-10", "10:00", 5)]))
    assert g["con_finde"]
    assert calendario.mes_anterior(2026, 1) == (2025, 12)
    assert calendario.mes_siguiente(2026, 12) == (2027, 1)


# ---------- psicología ----------
def test_costo_psicologia():
    rows = ([op("2026-10-0%d" % (i % 5 + 1), "10:00", 50, emo=4) for i in range(8)] +
            [op("2026-10-0%d" % (i % 5 + 1), "11:00", -40, emo=1) for i in range(6)])
    f = {x["clave"]: x for x in psico.analizar(rows)}["emo"]
    assert f["n_mala"] == 6 and f["neto_mala"] == -240 and not f["chica"]
    assert f["costo"] == pytest.approx((50 + 40) * 6)
    assert psico.total_costo([f]) == pytest.approx(540)


def test_psicologia_muestra_chica_y_sin_datos():
    assert psico.analizar([op("2026-10-01", "10:00", 10)]) == []
    f = psico.analizar([op("2026-10-01", "10:00", -10, emo=1), op("2026-10-01", "11:00", 10, emo=5)])[0]
    assert f["chica"]


# ---------- simulador ----------
def dia(fecha, profits):
    return [op(fecha, "%02d:00" % (9 + i), p) for i, p in enumerate(profits)]


def test_simulador_corte_por_perdidas():
    rows = dia("2026-10-01", [-10, -10, 50, 50])       # cortando tras 2 pérdidas se pierde lo bueno
    r = simulador.simular(rows, {"max_perdidas": 2})
    assert r["base"] == 80 and r["nuevo"] == -20 and r["n_nuevo"] == 2 and len(r["quitados"]) == 2
    assert r["delta"] == -100


def test_simulador_reglas_combinadas():
    rows = dia("2026-10-01", [10, -30, -30, -30]) + dia("2026-10-02", [20, 20])
    assert simulador.simular(rows, {"perdida_dia": 50})["nuevo"] == 10 - 30 - 30 + 40
    assert simulador.simular(rows, {"max_trades": 1})["nuevo"] == 30
    assert simulador.simular(rows, {"hora_limite": "10:30"})["nuevo"] == 10 - 30 + 20 + 20
    assert simulador.simular(rows, {"meta_dia": 20})["nuevo"] == 10 - 30 - 30 - 30 + 20
    assert simulador.simular(rows, {"sin_dias": [3]})["nuevo"] == 40   # 2026-10-01 es jueves
    assert not simulador.hay_reglas({})
    assert simulador.simular(rows, {})["delta"] == 0


def test_simulador_emo_min_ignora_sin_dato():
    rows = [op("2026-10-01", "09:00", -10, emo=1), op("2026-10-01", "10:00", 5)]
    r = simulador.simular(rows, {"emo_min": 3})
    assert r["n_nuevo"] == 1 and r["nuevo"] == 5


# ---------- reporte ----------
def test_reporte_detecta_patrones():
    rows = (dia("2026-10-05", [-10, -10, -10, -10, -10]) + dia("2026-10-06", [30, 20]) +
            dia("2026-10-07", [10, 10]))
    h = dict((t, n) for n, t in reporte.hallazgos(rows))
    assert any("pérdidas seguidas" in t for t in h)
    assert any("Mejor día" in t for t in h)
    assert any("sobreoperación" in t for t in h)
    assert reporte.hallazgos([]) == []
    txt = reporte.texto_para_claude(rows, "Semana de prueba", notas=[("2026-10-05", "tilt")])
    assert "Semana de prueba" in txt and "tilt" in txt and "coach" in txt
    assert "Sin operaciones" in reporte.texto_para_claude([], "x")


# ---------- DB v4 ----------
def test_playbooks_y_notas(tmp_path):
    bootstrap.iniciar(["--datos", str(tmp_path)], env={})
    assert db.SCHEMA_VERSION == 5
    db.db_playbook_save("Breakout", "rompe el rango", "1. Esperar cierre\n2. SL fijo")
    db.db_playbook_save("Breakout", "otra desc", "r")
    assert [p["nombre"] for p in db.db_playbooks()] == ["Breakout"]
    db.db_insert(dict(fecha="2026-10-01", hora="10:00", activo="MNQ", tipo="Breakout", profit=10,
                      empresa="", cuenta="", mov_sl="", tranquilo="", emo=0, comentario="",
                      img_ini="", img_fin=""))
    db.db_playbook_save("Ruptura", "x", "y", viejo_nombre="Breakout")
    assert [p["nombre"] for p in db.db_playbooks()] == ["Ruptura"]
    assert db.db_all()[0]["tipo"] == "Ruptura"
    db.db_playbook_delete("Ruptura")
    assert db.db_playbooks() == [] and db.db_all()[0]["tipo"] == "Ruptura"
    with pytest.raises(ValueError):
        db.db_playbook_save("  ")
    db.db_nota_save("2026-10-01", "plan", "pasó", "corregir")
    assert db.db_nota_get("2026-10-01")["que_paso"] == "pasó"
    assert "2026-10-01" in db.db_notas_rango("2026-10-01", "2026-10-31")
    db.db_nota_save("2026-10-01", " ", "", "")
    assert db.db_nota_get("2026-10-01")["plan"] == "" and not db.db_notas_rango("2026-10-01", "2026-10-31")


def test_simulador_explica_cuando_no_cambia_nada():
    from registro import simulador as S
    rows = [dict(fecha=f"2026-10-{d}", hora="09:40", profit=100.0, emo=None) for d in (12, 13, 14, 15)]
    reglas = dict(max_perdidas=2, max_trades=2, perdida_dia=200, meta_dia=200)
    r = S.simular(rows, reglas)
    assert r["delta"] == 0 and not r["quitados"]
    assert "1 trade por día" in S.explicar_sin_efecto(rows, reglas)
    # con varios trades en un día y reglas que sí se activan, quita trades
    rows = [dict(fecha="2026-10-15", hora=h, profit=p, emo=None)
            for h, p in (("09:40", 250), ("10:10", -80), ("10:30", -90), ("11:00", 200))]
    r = S.simular(rows, reglas)
    assert r["quitados"] and r["delta"] == -30


def test_narrativa_analisis():
    from registro import analisis as A
    assert A.narrativa([]) == []
    rows = []
    for i in range(6):
        rows.append(dict(fecha=f"2026-10-0{i+1}", hora="09:30", profit=100.0, activo="NQ", lado="long", tipo="ORB"))
        rows.append(dict(fecha=f"2026-10-0{i+1}", hora="14:10", profit=-40.0, activo="EURUSD", lado="short", tipo="Rev"))
    n = dict(A.narrativa(rows))
    assert list(n) == ["Resultado", "Ritmo", "Cuándo", "Qué"]
    assert "12 trades" in n["Resultado"] and "6 días" in n["Resultado"]
    assert "09:00" in n["Cuándo"] and "14:00" in n["Cuándo"]
    assert "NQ" in n["Qué"] and "EURUSD" in n["Qué"]
    poco = dict(A.narrativa(rows[:2]))
    assert "Todavía no hay" in poco["Cuándo"]


def test_por_cuenta():
    from registro import analisis as A
    rows = [dict(fecha="2026-10-01", profit=50, empresa="Lucid", cuenta="1"),
            dict(fecha="2026-10-01", profit=-20, empresa="Exness", cuenta="9"),
            dict(fecha="2026-10-02", profit=70, empresa="Lucid", cuenta="1"),
            dict(fecha="2026-10-02", profit=5)]
    r = A.por_cuenta(rows, [dict(empresa="Lucid", cuenta="1", alias="Fondeada A")])
    assert [(x["label"], x["n"], x["neto"]) for x in r] == [("Fondeada A", 2, 120), ("Exness · 9", 1, -20)]

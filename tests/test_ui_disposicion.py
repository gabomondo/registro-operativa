"""Reparto del ancho de la tabla de Registro (funciones puras)."""
from registro.ui.disposicion import FACTOR_MIN_COL, plan_columnas

BASE = {"fecha": 92, "hora": 56, "activo": 58, "tipo": 88, "profit": 84, "empresa": 128,
        "cuenta": 104, "mov_sl": 96, "emo": 66, "_chk": 56, "_caps": 46, "comentario": 180}
TODAS = list(BASE)
ESCALA = 1.15 * 1.25          # "Mediano" en una pantalla al 125%


def test_captura_de_gabo_se_achica_y_oculta_lo_menos_importante():
    # tabla de ~1040 px (la de la captura): antes se cortaba Emo y no se veía lo demás
    cols, anchos = plan_columnas(1040 - 4, TODAS, BASE, ESCALA)
    assert sum(anchos[c] for c in cols) <= 1040
    assert cols[:5] == ["fecha", "hora", "activo", "tipo", "profit"]
    for c in ("fecha", "hora", "activo", "profit", "emo"):          # las fijas no se achican
        assert c in cols and anchos[c] == int(BASE[c] * ESCALA)
    assert "comentario" not in cols and "_caps" not in cols         # se ocultan primero
    assert all(anchos[c] >= int(BASE[c] * ESCALA * FACTOR_MIN_COL) - 1 for c in cols if c in ("tipo", "empresa", "cuenta"))


def test_con_espacio_de_sobra_se_muestra_todo_sin_achicar():
    cols, anchos = plan_columnas(3000, TODAS, BASE, 1.0)
    assert cols == TODAS
    assert all(anchos[c] == (90 if c == "comentario" else BASE[c]) for c in TODAS)


def test_orden_de_ocultamiento_y_ventana_muy_angosta():
    elasticas = ("tipo", "empresa", "cuenta", "mov_sl")
    fijo = sum(BASE[c] for c in TODAS if c not in elasticas + ("comentario",)) * ESCALA
    el = sum(BASE[c] for c in elasticas) * ESCALA
    justo = int(fijo + FACTOR_MIN_COL * el) + 2                      # entra sin comentario, no con él
    cols, _ = plan_columnas(justo, TODAS, BASE, ESCALA)
    assert "comentario" not in cols and "_caps" in cols and "_chk" in cols and "mov_sl" in cols
    cols, _ = plan_columnas(justo - 60, TODAS, BASE, ESCALA)         # un poco menos: cae también Caps
    assert "comentario" not in cols and "_caps" not in cols and "_chk" in cols
    cols, anchos = plan_columnas(300, TODAS, BASE, ESCALA)           # ni así entra: no se rompe
    assert cols and all(a > 0 for a in anchos.values())
    assert "fecha" in cols and "profit" in cols


def test_solo_se_muestran_columnas_con_datos():
    visibles = ["fecha", "hora", "activo", "profit", "empresa", "cuenta"]
    cols, anchos = plan_columnas(2000, visibles, BASE, 1.0)
    assert cols == visibles and set(anchos) == set(BASE)            # anchos para todas (también las ocultas)

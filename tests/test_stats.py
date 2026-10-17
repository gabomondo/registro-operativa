from registro.stats import compute_stats, op_check_full, op_check_counts

def op(profit, chk, emo=3, fecha="2026-10-01", hora="10:00"):
    import json
    return {"profit": profit, "chk_data": json.dumps(chk), "emo": emo, "fecha": fecha, "hora": hora}

def test_vacio():
    s = compute_stats([]); assert s["n"] == 0 and s["pnl"] == 0.0

def test_basico():
    rows = [op(100, {"a": 1, "b": 1}, fecha="2026-10-01"), op(-50, {"a": 1, "b": 0}, fecha="2026-10-02"),
            op(-20, {"a": 1, "b": 1}, fecha="2026-10-03")]
    s = compute_stats(rows)
    assert s["n"] == 3 and s["pnl"] == 30 and s["wins"] == 1 and s["losses"] == 2
    assert s["wr"] == 33 and s["streak"] == 2 and s["streak_sign"] == -1
    assert s["chk_pct"] == 67 and s["best"] == 100 and s["worst"] == -50

def test_check_por_plantilla_propia():
    assert op_check_counts(op(1, {"a": 1, "b": 0, "c": 1})) == (2, 3)
    assert op_check_full(op(1, {"a": 1})) is True

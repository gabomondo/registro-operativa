from registro import unidades as U

CS = [dict(empresa="A", cuenta="1", capital_inicial=50000), dict(empresa="B", cuenta="2", capital_inicial=None),
      dict(empresa="C", cuenta="3", capital_inicial=25000)]


def test_base_capital():
    assert U.base_capital(CS) == 75000
    assert U.base_capital(CS, ("A", "1")) == 50000 and U.base_capital(CS, ["C", "3"]) == 25000
    assert U.base_capital(CS, ("B", "2")) is None and U.base_capital(CS, ("X", "9")) is None
    assert U.base_capital([]) is None and U.base_capital([dict(empresa="B", cuenta="2")]) is None


def test_fmt():
    assert U.fmt(1234.6) == "+1,235" and U.fmt(-50, d=1) == "-50.0" and U.fmt(1234, signo=False) == "1,234"
    assert U.fmt(500, U.PCT, 50000) == "+1.00%" and U.fmt(-250, U.PCT, 50000) == "-0.50%"
    assert U.fmt(250, U.PCT, 50000, signo=False) == "0.50%"
    assert U.fmt(500, U.PCT, None) == "+500" and U.fmt(500, U.PCT, 0) == "+500"      # sin capital: dinero
    assert U.fmt(None, U.PCT, 1000) == "—"


def test_activo():
    assert U.activo(U.PCT, 1000) and not U.activo(U.PCT, None) and not U.activo(U.DINERO, 1000)

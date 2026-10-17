"""Modelo común: todos los lectores devuelven TradeImp."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TradeImp:
    fuente: str                 # nt8 | nt8_ordenes | mt4 | mt5 | tradovate | topstepx | deepcharts
    cuenta: str
    ext_id: str
    activo: str
    lado: str                   # Long | Short
    contratos: float
    t_ini: datetime
    t_fin: datetime
    precio_ini: float
    precio_fin: float
    bruto: float = None         # None = no se pudo calcular
    comision: float = 0.0       # costo positivo (comisión + swap)
    motivo: str = ""            # SL | TP | Manual | ""
    avisos: list = field(default_factory=list)
    incluir: bool = True
    duplicado: bool = False
    posible: str = ""          # texto si se parece a un trade que ya está (manual u otra importación)
    cuentas_n: int = 1

    @property
    def neto(self):
        return None if self.bruto is None else self.bruto - self.comision

    @property
    def clave(self):
        return (self.fuente, self.cuenta, self.ext_id)


@dataclass
class Lectura:
    """Resultado de leer un archivo."""
    formato: str                # nombre legible
    fuente: str
    trades: list
    avisos: list = field(default_factory=list)
    cuentas: list = field(default_factory=list)


class ImportError_(Exception):
    """Archivo ilegible o de un formato desconocido (mensaje apto para el usuario)."""

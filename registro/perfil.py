"""Perfiles: lo que cambia entre un trader y otro, sin tocar el código.

Un perfil vive en <carpeta de datos>/perfil.json y se edita desde la pestaña
"Perfil". Los presets (perfiles/*.json junto al programa) solo sirven para
arrancar la primera vez.
"""

import json
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime

from .paths import resource_path

PERFIL_VERSION = 1

# Valor en USD de 1 punto de precio por contrato (futuros). Editable por perfil.
VALOR_PUNTO_BASE = {
    "NQ": 20.0, "MNQ": 2.0, "ES": 50.0, "MES": 5.0,
    "YM": 5.0, "MYM": 0.5, "RTY": 50.0, "M2K": 5.0,
    "GC": 100.0, "MGC": 10.0, "CL": 1000.0, "MCL": 100.0,
}

PLAN_NEUTRO = """# Mi plan de trading

Instrumento y sesión: (completá)
Estrategia: (completá)

## 1. Tesis
¿Por qué operás este mercado y este horario? ¿Qué ventaja creés tener?

## 2. Setup
- Condiciones de entrada:
- Condiciones que invalidan el trade:
- Horario / ventana permitida:

## 3. Gestión de riesgo
- Riesgo por trade:
- Máximo de trades por sesión:
- Corte diario (pérdida máxima o cantidad de SL seguidos):

## 4. Objetivo del día
- Cuándo parás de operar:

## 5. Reglas no negociables
1.
2.
3.
"""

PLANTILLA_NEUTRA = {
    "nombre": "Check básico",
    "items": [
        {"id": "n_plan",    "label": "Operé dentro de mi plan y mi horario"},
        {"id": "n_sl",      "label": "Definí el SL antes de entrar"},
        {"id": "n_sl_fijo", "label": "No moví el SL en contra"},
        {"id": "n_riesgo",  "label": "Riesgo dentro de lo que definí"},
        {"id": "n_setup",   "label": "Setup válido, sin entrar por impulso"},
    ],
}


@dataclass
class Perfil:
    nombre: str = "Neutro"
    activos: list = field(default_factory=lambda: ["NQ", "MNQ", "ES", "MES"])
    tipos: list = field(default_factory=lambda: ["Breakout", "Retest", "Reversión", "Continuación"])
    empresas: list = field(default_factory=lambda: ["Cuenta propia"])
    tipos_cuenta: list = field(default_factory=lambda: ["Fondeada", "Challenge", "Real", "Demo"])
    valor_punto: dict = field(default_factory=lambda: dict(VALOR_PUNTO_BASE))
    comision_contrato: dict = field(default_factory=dict)   # USD por contrato (ida y vuelta)
    offset_horas: dict = field(default_factory=lambda: {"mt5": 0.0, "tradovate": 0.0})
    agrupar_segundos: int = 2
    plan_inicial: str = PLAN_NEUTRO
    plantilla_inicial: dict = field(default_factory=lambda: json.loads(json.dumps(PLANTILLA_NEUTRA)))
    version: int = PERFIL_VERSION

    # ---------- serialización ----------
    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d, base=None):
        """Construye un perfil tolerante: campos que faltan o vienen mal toman
        el valor de `base` (o del perfil neutro). Nunca lanza por datos sucios."""
        base = base or cls()
        d = d if isinstance(d, dict) else {}
        p = cls(**{k: getattr(base, k) for k in cls.__dataclass_fields__})
        p.nombre = _txt(d.get("nombre")) or base.nombre
        for campo in ("activos", "tipos", "empresas", "tipos_cuenta"):
            vals = _lista(d.get(campo))
            # 'empresas' puede quedar vacía a propósito; las demás listas no
            if vals or (campo == "empresas" and isinstance(d.get(campo), list)):
                setattr(p, campo, vals)
        vp = _num_dict(d.get("valor_punto"), minimo_exclusivo=0)
        if vp:
            p.valor_punto = vp
        if "comision_contrato" in d:
            p.comision_contrato = _num_dict(d.get("comision_contrato"), minimo=0)
        off = d.get("offset_horas")
        if isinstance(off, dict):
            p.offset_horas = {str(k).lower(): _num(v, 0.0) for k, v in off.items()}
        seg = _num(d.get("agrupar_segundos"), None)
        if seg is not None:
            p.agrupar_segundos = int(max(0, min(60, seg)))
        if _txt(d.get("plan_inicial")):
            p.plan_inicial = d["plan_inicial"]
        pl = d.get("plantilla_inicial")
        if isinstance(pl, dict) and _txt(pl.get("nombre")) and isinstance(pl.get("items"), list):
            items = []
            for i, it in enumerate(pl["items"]):
                if isinstance(it, dict) and _txt(it.get("label")):
                    items.append({"id": _txt(it.get("id")) or f"it_{i+1}", "label": _txt(it["label"])})
            if items:
                p.plantilla_inicial = {"nombre": _txt(pl["nombre"]), "items": items}
        return p

    def valor_punto_de(self, activo):
        """USD por punto para un símbolo como 'MNQ DEC26', 'MNQZ6' o 'MNQ'."""
        s = (activo or "").upper().replace(" ", "")
        for k in sorted(self.valor_punto, key=len, reverse=True):
            if s.startswith(k.upper()):
                return self.valor_punto[k]
        return None


# ---------- helpers de validación ----------
def _txt(v):
    return v.strip() if isinstance(v, str) and v.strip() else ""


def _num(v, default):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _lista(v):
    if not isinstance(v, list):
        return []
    out, vistos = [], set()
    for x in v:
        t = _txt(x)
        if t and t.lower() not in vistos:
            vistos.add(t.lower())
            out.append(t)
    return out


def _num_dict(v, minimo=None, minimo_exclusivo=None):
    out = {}
    if not isinstance(v, dict):
        return out
    for k, x in v.items():
        n = _num(x, None)
        if n is None or not _txt(str(k)):
            continue
        if minimo is not None and n < minimo:
            continue
        if minimo_exclusivo is not None and n <= minimo_exclusivo:
            continue
        out[str(k).strip().upper()] = n
    return out


# ---------- presets ----------
def carpeta_presets():
    return resource_path("perfiles")


def listar_presets():
    try:
        return sorted(f[:-5] for f in os.listdir(carpeta_presets()) if f.endswith(".json"))
    except OSError:
        return []


def cargar_preset(nombre):
    """Devuelve el preset pedido; si no existe (p. ej. 'gabo' en el instalador
    público) cae al neutro."""
    path = os.path.join(carpeta_presets(), f"{nombre}.json")
    try:
        with open(path, encoding="utf-8") as f:
            return Perfil.from_dict(json.load(f))
    except Exception:
        return Perfil()


# ---------- archivo del perfil ----------
def guardar(path, perfil):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(perfil.to_dict(), f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _db_tiene_operaciones(db_path):
    if not os.path.exists(db_path):
        return False
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            return con.execute("SELECT COUNT(*) FROM operaciones").fetchone()[0] > 0
        finally:
            con.close()
    except Exception:
        return False


def cargar_o_crear(path, db_path, preset=None, log=None):
    """Lee perfil.json. Si no existe lo crea:
       - con el preset pedido (--perfil), o
       - si ya había una base con operaciones (versión anterior sin perfiles), con
         el preset 'gabo' para que nada cambie, o
       - con el preset neutro.
    Si el archivo está corrupto lo aparta (.corrupto) y arranca con el neutro."""
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return Perfil.from_dict(json.load(f)), False
        except Exception as e:
            apartado = f"{path}.corrupto-{datetime.now():%Y%m%d-%H%M%S}"
            try:
                os.replace(path, apartado)
            except OSError:
                pass
            if log:
                log.warning("perfil.json ilegible (%s); apartado en %s", e, apartado)
    nombre = preset or ("gabo" if _db_tiene_operaciones(db_path) else "neutro")
    perfil = cargar_preset(nombre) if nombre in listar_presets() else Perfil()
    guardar(path, perfil)
    return perfil, True

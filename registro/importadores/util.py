import re
from datetime import datetime

from .modelo import ImportError_


def leer_texto(path):
    """Lee un archivo detectando la codificación (BOM, UTF-8, UTF-16, cp1252)."""
    try:
        raw = open(path, "rb").read()
    except OSError as e:
        raise ImportError_(f"No pude abrir el archivo: {e}")
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8", errors="replace")
    if b"\x00" in raw[:200]:
        try:
            return raw.decode("utf-16-le")
        except UnicodeDecodeError:
            pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def num(s, coma_decimal=False):
    """'1.234,50' / '1,234.50' / '$ 0,00' / '-3.5' -> float. None si vacío."""
    if s is None:
        return None
    t = str(s).strip().replace("\xa0", "").replace(" ", "").replace("$", "")
    if t in ("", "-"):
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        if coma_decimal or not re.match(r"^-?\d{1,3}(,\d{3})+$", t):
            t = t.replace(",", ".")
        else:
            t = t.replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def fecha(s, formatos):
    s = (s or "").strip()
    for f in formatos:
        try:
            return datetime.strptime(s, f)
        except ValueError:
            continue
    return None


_RE_VENC1 = re.compile(r"^(.+?)\s+(?:[A-Z]{3}\d{2}|\d{1,2}-\d{2})$")
_RE_VENC2 = re.compile(r"^([A-Z0-9]{1,4}?)[FGHJKMNQUVXZ]\d{1,2}$")


def raiz(simbolo):
    """'MNQ DEC26' / 'MNQZ6' -> 'MNQ'. Lo que no parece futuro queda igual."""
    s = (simbolo or "").strip().upper()
    m = _RE_VENC1.match(s) or _RE_VENC2.match(s)
    return m.group(1) if m else s


def comision_de(perfil, activo, contratos):
    """USD de comisión según el perfil (por contrato, ida y vuelta) o None."""
    r = raiz(activo)
    for k in sorted(perfil.comision_contrato, key=len, reverse=True):
        if r.startswith(k.upper()):
            return perfil.comision_contrato[k] * contratos
    return None


def sumar_horas(dt, horas):
    from datetime import timedelta
    return dt + timedelta(hours=horas) if horas else dt


def filas_xlsx(path):
    """Primera hoja de un .xlsx como lista de filas de texto ('' en las celdas vacías). Sin dependencias:
    un .xlsx es un zip con XML, así que alcanza con la librería estándar."""
    import re as _re
    import zipfile
    from xml.etree import ElementTree as ET
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    try:
        with zipfile.ZipFile(path) as z:
            nombres = z.namelist()
            compartidas = []
            if "xl/sharedStrings.xml" in nombres:
                for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{ns}si"):
                    compartidas.append("".join(t.text or "" for t in si.iter(f"{ns}t")))
            hojas = sorted((n for n in nombres if _re.match(r"xl/worksheets/sheet\d+\.xml$", n)),
                           key=lambda n: int(_re.findall(r"\d+", n)[-1]))
            if not hojas:
                raise ImportError_("El Excel no tiene hojas.")
            filas = []
            for row in ET.fromstring(z.read(hojas[0])).iter(f"{ns}row"):
                celdas = {}
                for c in row.iter(f"{ns}c"):
                    col = 0
                    for ch in _re.match(r"[A-Z]+", c.get("r", "A")).group(0):
                        col = col * 26 + ord(ch) - 64
                    t = c.get("t")
                    if t == "inlineStr":
                        txt = "".join(x.text or "" for x in c.iter(f"{ns}t"))
                    else:
                        v = c.find(f"{ns}v")
                        txt = "" if v is None or v.text is None else v.text
                        if t == "s" and txt != "":
                            txt = compartidas[int(txt)]
                    celdas[col - 1] = txt.strip()
                n = max(celdas) + 1 if celdas else 0
                filas.append([celdas.get(i, "") for i in range(n)])
            return filas
    except ImportError_:
        raise
    except Exception as e:
        raise ImportError_(f"No pude abrir el Excel: {e}")

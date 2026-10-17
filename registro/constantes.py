"""Constantes históricas del check original (estrategia ORB).

Se conservan para (a) mantener compatibilidad con las columnas chk_* viejas, que
NO se borran, y (b) migrar bases anteriores a las plantillas de check.
"""

CHECK_ITEMS = [
    ("chk_riesgo",   "Riesgo = $2K (ni más ni menos)"),
    ("chk_sl_fijo",  "SL puesto y NO se movió"),
    ("chk_sesgo",    "A favor del sesgo macro (DXY / bancos)"),
    ("chk_rango",    "Puntos de SL calculados según el rango ORB"),
    ("chk_ventana",  "Dentro de la ventana / setup válido"),
    ("chk_num",      "Dentro de los 4 trades de la sesión"),
]
CHECK_KEYS = [k for k, _ in CHECK_ITEMS]
LEGACY_TEMPLATE_NAME = "ORB NY (original)"

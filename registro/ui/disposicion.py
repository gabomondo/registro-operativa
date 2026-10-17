"""Reparto del ancho de la tabla de Registro (funciones puras, sin tkinter, con tests).

Las columnas de texto se achican un poco y, si todavía no entran, se ocultan las menos
importantes (siguen visibles en el panel de detalle). El alto lo resuelve el scroll de la página."""

MIN_FILAS_TABLA = 7          # filas que la tabla muestra como mínimo (si no entra todo, scrollea la página)
FACTOR_MIN_COL = 0.8         # cuánto pueden achicarse las columnas de texto antes de ocultar otras
PISO_FACTOR = 0.6            # último recurso (ventana muy angosta)
ANCHO_BASE_COMENTARIO = 90   # el comentario es elástico: se mide con este ancho
ELASTICAS = ("tipo", "empresa", "cuenta", "mov_sl", "comentario")   # las únicas que se achican
OCULTAR_EN_ORDEN = ("comentario", "_caps", "_chk", "mov_sl")        # se ocultan en este orden


def plan_columnas(ancho, visibles, base, escala):
    """Decide qué columnas mostrar y con qué ancho (px) para que entren en `ancho` px.

    visibles: columnas con datos, en orden. base: {columna: ancho nominal sin escala}.
    Devuelve (columnas_a_mostrar, {columna: ancho_px}) para TODAS las de `base`
    (las ocultas conservan su ancho nominal)."""
    nominal = {c: (ANCHO_BASE_COMENTARIO if c == "comentario" else w) * escala
               for c, w in base.items()}
    cols = list(visibles)

    def sumas():
        fijo = sum(nominal[c] for c in cols if c not in ELASTICAS)
        elastico = sum(nominal[c] for c in cols if c in ELASTICAS)
        return fijo, elastico

    while True:
        fijo, elastico = sumas()
        if elastico == 0 or (ancho - fijo) / elastico >= FACTOR_MIN_COL:
            break
        quitar = next((c for c in OCULTAR_EN_ORDEN if c in cols), None)
        if quitar is None or len(cols) <= 1:
            break
        cols.remove(quitar)
    fijo, elastico = sumas()
    f = 1.0 if elastico == 0 else min(1.0, max(PISO_FACTOR, (ancho - fijo) / elastico))
    anchos = {c: max(1, int(nominal[c] * (f if c in ELASTICAS else 1.0))) for c in base}
    return cols, anchos

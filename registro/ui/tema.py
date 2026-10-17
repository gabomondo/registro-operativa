"""Tema (paleta), tipografías y espaciado de la interfaz.

`aplicar_tema` y `_resolve_fonts` publican los valores en `vivo`: todos los módulos
de la UI que se registraron con `vivo.registrar(globals())` los ven actualizados."""

from registro import fonts as _fonts
from registro.ui import vivo


# ----------------------------------------------------------------------------
# Paleta gabomondo
# ----------------------------------------------------------------------------
TEMAS = {
    "oscuro": dict(
        INK="#0E1116", PAPER="#F2EEE6", BLUE="#2C5AA0", BLUE_HI="#356BC0", ON_BLUE="#F5F1EA",
        POS="#3a6b3a", NEG="#8B3A2E", CAUTION="#a87f2b", POS_TXT="#6fb06f", NEG_TXT="#d08a78",
        LINE="#1F242B", LINE2="#2E343D", MUTED="#9B968A", MUTED2="#75716A",
        SURFACE="#151920", SURFACE2="#11151B", HOVER="#1B2028", TRACK="#1c2129",
        SIDEBAR="#0B0E12", NAV_SEL="#1A2230", SEG_SEL="#2C5AA0", SEG_HI="#356BC0",
        T_WIN=("#17221a", "#141d17"), T_LOSS=("#241917", "#1f1614"),
        T_WIN_SOFT="#2f4a2f", T_LOSS_SOFT="#6b3a33",
        F_LOW="#2b1c18", F_MID="#2b2618", F_HIGH="#1d2b1d",
        F_POS="#16241b", F_NEG="#241717", MODO="dark"),
    "claro": dict(
        INK="#F5F3EE", PAPER="#1C2028", BLUE="#2C5AA0", BLUE_HI="#3A6DBE", ON_BLUE="#FFFFFF",
        POS="#3a6b3a", NEG="#8B3A2E", CAUTION="#a87f2b", POS_TXT="#2E7A3F", NEG_TXT="#B2432E",
        LINE="#E3DED2", LINE2="#CFC9BB", MUTED="#6A665C", MUTED2="#8D897E",
        SURFACE="#FFFFFF", SURFACE2="#FAF8F4", HOVER="#EFEBE2", TRACK="#E9E5DB",
        SIDEBAR="#ECE8DF", NAV_SEL="#DDE5F2", SEG_SEL="#CBD9F0", SEG_HI="#BCCFEA",
        T_WIN=("#E6F2E8", "#DDEEE0"), T_LOSS=("#F6E5E1", "#F1DAD5"),
        T_WIN_SOFT="#A9CDAF", T_LOSS_SOFT="#D9A79D",
        F_LOW="#F6E1DB", F_MID="#F4EBD3", F_HIGH="#DDEEDF",
        F_POS="#E1F0E4", F_NEG="#F6E3DF", MODO="light"),
}


# Tema con el que se abre el programa si el usuario nunca eligió otro (Perfil → Apariencia).
TEMA_POR_DEFECTO = "claro"
TEMA_ACTUAL = TEMA_POR_DEFECTO


def aplicar_tema(nombre):
    """Define la paleta global. Hay que llamarla antes de construir la ventana."""
    global TEMA_ACTUAL
    nombre = nombre if nombre in TEMAS else TEMA_POR_DEFECTO
    TEMA_ACTUAL = nombre
    globals().update(TEMAS[nombre])
    vivo.publicar(TEMA_ACTUAL=nombre, **TEMAS[nombre])


aplicar_tema(TEMA_POR_DEFECTO)


FONT_MAIN = "DM Sans"


FONT_MONO = "JetBrains Mono"


FONT_SERIF = "Instrument Serif"


# ----------------------------------------------------------------------------
# Sistema de espaciado y forma — escala única, aplicada parejo en toda la app.
# Antes cada bloque usaba números sueltos (16, 12, 24...); centralizar acá es
# lo que separa "hecho a mano" de "diseñado".
# ----------------------------------------------------------------------------
SP_XS = 4


SP_SM = 8


SP_MD = 12


SP_LG = 16


SP_XL = 24


SP_XXL = 28


RAD_CARD  = 12   # tarjetas (KPI, equity, contenedores)


RAD_CTRL  = 8    # controles (inputs, botones, badges)


RAD_PILL  = 8    # badges/píldoras


BORDER_W  = 1    # borde fino, consistente (nada grueso)


def _resolve_fonts():
    """Registra las fuentes de marca que viajan con el programa y, si alguna no
    está disponible, cae a alternativas seguras."""
    global FONT_MAIN, FONT_MONO, FONT_SERIF
    _fonts.registrar_fuentes()
    FONT_MAIN, FONT_MONO, FONT_SERIF = _fonts.resolver_fuentes()
    vivo.publicar(FONT_MAIN=FONT_MAIN, FONT_MONO=FONT_MONO, FONT_SERIF=FONT_SERIF)

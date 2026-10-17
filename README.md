# Registro de operativa — gabomondo

Diario de trading de escritorio (Windows) con foco psicológico: registrás cada operación,
tildás un check de disciplina propio, adjuntás capturas y revisás la semana. **Gratis.
Tus datos quedan en tu computadora**: la app no envía nada a ningún servidor.

## Instalar (usuarios)
1. Descargá `RegistroOperativa-Setup-X.Y.Z.exe` desde la sección **Releases** de este repositorio.
2. Ejecutalo. No pide permisos de administrador.
3. Windows puede mostrar «Windows protegió su PC» (SmartScreen) porque el instalador todavía no está
   firmado: **Más información → Ejecutar de todas formas**.
4. Al abrir por primera vez: pestaña **Perfil** (tus activos, tipos de entrada, empresas), **Plan** y **Plantillas** (tu check).

Desinstalar **no borra tus datos**. Viven en `%APPDATA%\gabomondo\RegistroOperativa`.

## Correr desde el código
```
pip install -r requirements.txt
python registro_operativa.py                 # datos en %APPDATA%\gabomondo\RegistroOperativa
python registro_operativa.py --datos "D:\mi\carpeta"
python registro_operativa.py --datos "D:\mi\carpeta" --perfil gabo   # preset inicial si no hay perfil.json
```
`launch.bat` hace lo mismo. `launch_gabo.bat` abre **tus** datos (la carpeta de arriba, donde está `registro.db`) con tu perfil.

## Importar trades

Botón **Importar trades** (arriba a la derecha). Elegís el archivo, el programa detecta el formato solo y
muestra una vista previa; recién al apretar *Importar* se guarda algo. Podés destildar trades, elegir qué
cuentas entran y a qué empresa / tipo de cuenta se asignan.

| Plataforma | Archivo | Notas |
|---|---|---|
| NinjaTrader 8 | Grilla **Executions** (recomendada) u **Orders** | Orders es aproximado (hora de la orden). Las cuentas `Sim…` vienen destildadas. |
| MetaTrader 5 | Informe de historial en HTML (cuenta Hedge) | Horarios del servidor: ajustá el desfase en Perfil. |
| Tradovate | `Position_History.csv` | No trae comisión: se estima con Perfil. |
| TopstepX | `trades_export.csv` | Costo = columna `Fees`. |

- Varias entradas que cierran juntas (±`agrupar_segundos` del Perfil) cuentan como **un** trade.
- Copy trading: la opción *Juntar el mismo trade de varias cuentas* suma las cuentas en un solo trade.
- Reimportar el mismo archivo no duplica: se identifica cada trade por plataforma + cuenta + id.
- El P&L usa el valor del punto y la comisión por contrato de **Perfil** cuando el archivo no los trae.

## Análisis
Pestaña **Análisis**: neto, win rate, profit factor, expectativa, promedio ganador/perdedor y mejor/peor día;
tabla **por día** con acumulado y barras **por hora de entrada, activo, Long/Short y día de la semana**.
Filtra por período y por tipo de cuenta. Las barras tenues son grupos de menos de 5 trades.

## Apariencia

- Navegación en barra lateral (Registro, Análisis, Cargar operación, Revisión semanal, Plan, Plantillas, Perfil).
- Tamaño de letra (Chico / Mediano / Grande): abajo en la barra lateral.
- Tema claro (por defecto) u oscuro: en **Perfil → Apariencia** o en **Datos → Cambiar a tema…** (se aplica al reiniciar el programa).
- Backup / restaurar JSON y exportar CSV: menú **Datos** arriba a la derecha.
- La curva de equity muestra fecha, trade y acumulado al pasar el mouse.

## Herramientas de análisis y revisión

- **Calendario:** P&L día por día y total por semana. Click en un día = sus operaciones; click derecho = su nota.
- **Análisis → El costo de la psicología:** cruza estado emocional, tranquilidad, movimiento del SL y checklist con tus dólares. Es una correlación, no una causa (con menos de 5 trades por grupo no concluye).
- **Playbooks:** cada setup con sus reglas escritas y cómo rinde (neto, win rate, profit factor). Se vinculan a las operaciones por el «tipo de entrada».
- **Simulador:** probá reglas sobre tus trades reales (cortar tras N pérdidas, máximo de trades, límite diario, hora límite, saltear estados emocionales bajos, días sin operar) y compará contra lo que hiciste.
- **Notebook:** una nota por día (plan, qué pasó, qué corregir), con las operaciones del día al lado. Se guarda sola.
- **Revisión semanal:** patrones detectados con reglas simples (sobreoperación, rachas, reentradas apuradas, mejor/peor hora y setup, checklist) y un botón para **copiar un resumen** y pegarlo en tu chat con Claude. No se envía nada a ningún servidor.

## Dónde guarda los datos
En este orden: `--datos` → variable `REGISTRO_DATOS` → modo portable (hay un `registro.db` o un
`portable.flag` junto al programa) → carpeta elegida en Perfil → `Cambiar carpeta…` → `%APPDATA%\gabomondo\RegistroOperativa`.
Dentro: `registro.db`, `capturas/`, `perfil.json`, `backups/`, `logs/`.
Para sincronizar con Google Drive o similar: Perfil → **Cambiar carpeta…**.

## Perfiles
Un perfil (`perfil.json`) define lo que cambia entre traders: listas de activos, tipos de entrada, empresas y tipos de cuenta,
valor del punto y comisión por contrato, offsets horarios y tolerancia de agrupado (para la importación de trades).
Se edita en la pestaña **Perfil**. Los presets iniciales viven en `perfiles/*.json`; el instalador solo incluye `neutro.json`
(`perfiles/gabo.json` es personal y está en `.gitignore`).
Si existe una base de la versión anterior sin `perfil.json`, se usa el preset `gabo` para que nada cambie.

## Seguridad de los datos
- **Migraciones versionadas** (`PRAGMA user_version`). Antes de migrar una base con datos se guarda `backups/registro_pre-vN_….db`
  y cada migración corre en una transacción: si falla, se revierte.
- **Backup automático diario** al abrir (se conservan 14) + botón *Backup ahora* + *Restaurar backup…* (guarda antes la base actual).
- Una base creada por una versión **más nueva** se rechaza sin tocarla.
- Errores: `logs/registro.log` (rotativo).

## Generar los instaladores (en Windows)
Requisitos: Python 3.10+ y [Inno Setup 6](https://jrsoftware.org/isdl.php).
```
build.bat          :: instalador PÚBLICO   -> dist\RegistroOperativa-Setup-<versión>.exe
build.bat gabo     :: instalador PERSONAL  -> dist\RegistroOperativa-Gabo-Setup-<versión>.exe
build.bat todo     :: los dos
```
Corre los tests, empaqueta con PyInstaller y compila con Inno Setup. La versión sale de `registro/__init__.py`.

- **Público**: perfil neutro, datos en `%APPDATA%\gabomondo\RegistroOperativa`. El script aborta si por error se coló `gabo.json`.
- **Personal**: incluye el preset `gabo` y sus accesos directos abren con `--datos "D:\Docs2\Trade\Journal\Registro_operativa" --perfil gabo` (tu base actual). Para otra carpeta: `iscc installer.iss /DMyAppVersion=1.0.0 /DPersonal /DDatosGabo="E:\otra"`.
- Tienen `AppId` distinto: se pueden instalar los dos a la vez. **No cambiar los `AppId`**: permiten que una versión nueva actualice a la anterior.
- Cuidado: no abras la versión personal y `launch_gabo.bat` al mismo tiempo (usan la misma base).

## Publicar una versión en GitHub
1. Subir la versión en `registro/__init__.py` y correr `build.bat`.
2. Probar el instalador en una PC limpia (o carpeta de usuario nueva): instalar, abrir, cargar una operación, desinstalar.
3. Crear el release:
   ```
   gh release create vX.Y.Z dist\RegistroOperativa-Setup-X.Y.Z.exe --title "vX.Y.Z" --notes "Cambios: ..."
   ```
4. Enlazar el asset desde la web de descarga.

## Tests
```
pip install -r requirements-build.txt
python -m pytest tests -q
```
`tests/smoke_ui.py` abre la interfaz completa y recorre las pestañas (en Linux: `xvfb-run -a python tests/smoke_ui.py CARPETA`).

## Licencia
Pendiente de definir por el autor. Las tipografías (DM Sans, JetBrains Mono, Instrument Serif) se distribuyen bajo SIL OFL 1.1
(`assets/fonts/OFL-*.txt`).

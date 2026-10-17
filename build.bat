@echo off
rem Genera instaladores.
rem   build.bat          -> instalador PUBLICO  (dist\RegistroOperativa-Setup-X.exe)
rem   build.bat gabo     -> instalador PERSONAL (dist\RegistroOperativa-Gabo-Setup-X.exe)
rem   build.bat todo     -> los dos
rem Requisitos: Python 3.10+ en el PATH e Inno Setup 6 (https://jrsoftware.org/isdl.php)
setlocal
cd /d "%~dp0"
set MODO=%1
if "%MODO%"=="" set MODO=publico
if /i not "%MODO%"=="publico" if /i not "%MODO%"=="gabo" if /i not "%MODO%"=="todo" (
  echo Uso: build.bat [publico^|gabo^|todo]
  exit /b 1
)

rem Si el venv quedo roto de una corrida anterior (por ejemplo "~ip" en site-packages), se recrea.
if exist .venv_build\Lib\site-packages\~ip* rmdir /s /q .venv_build
if exist .venv_build\Scripts\python.exe (
  .venv_build\Scripts\python.exe -c "import pytest, PyInstaller" >nul 2>&1 || rmdir /s /q .venv_build
)
if not exist .venv_build\Scripts\python.exe (
  python -m venv .venv_build || goto :err
)
call .venv_build\Scripts\activate.bat
rem No se actualiza pip dentro del venv: en Windows puede dejarlo a medio instalar.
python -m pip install -r requirements-build.txt --disable-pip-version-check || goto :err

echo.
echo === Tests ===
python -m pytest tests -q || goto :err

for /f %%v in ('python -c "from registro import __version__; print(__version__)"') do set VER=%%v

set "ISCC="
where iscc >nul 2>&1 && set "ISCC=iscc"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"

if /i "%MODO%"=="publico" call :publico || goto :err
if /i "%MODO%"=="gabo"    call :gabo    || goto :err
if /i "%MODO%"=="todo" (
  call :publico || goto :err
  call :gabo    || goto :err
)
goto :fin

:publico
echo.
echo === Empaquetando PUBLICO v%VER% ===
set RO_PERSONAL=
call :borrar dist\RegistroOperativa || (echo *** No pude borrar dist\RegistroOperativa: cerra el Explorador o la app que la use. *** & exit /b 1)
set "WP=build\publico_%RANDOM%%RANDOM%"
pyinstaller --noconfirm --clean --distpath dist --workpath %WP% registro_operativa.spec || exit /b 1
call :limpiar_build
rem seguridad: el publico NUNCA debe llevar el preset personal ni datos de nadie
dir /s /b "dist\RegistroOperativa\gabo.json" >nul 2>&1 && (
  echo *** El build publico incluye gabo.json. Abortado. ***
  exit /b 1
)
dir /s /b "dist\RegistroOperativa\*.db" "dist\RegistroOperativa\perfil.json" >nul 2>&1 && (
  echo *** El build publico incluye una base o un perfil.json. Abortado. ***
  exit /b 1
)
if not defined ISCC goto :sin_inno
"%ISCC%" installer.iss /DMyAppVersion=%VER% || exit /b 1
echo Listo: dist\RegistroOperativa-Setup-%VER%.exe
exit /b 0

:gabo
echo.
echo === Empaquetando PERSONAL v%VER% ===
set RO_PERSONAL=1
call :borrar dist\gabo || (echo *** No pude borrar dist\gabo: cerra el Explorador o la app que la use. *** & exit /b 1)
set "WP=build\gabo_%RANDOM%%RANDOM%"
pyinstaller --noconfirm --clean --distpath dist\gabo --workpath %WP% registro_operativa.spec || exit /b 1
call :limpiar_build
set RO_PERSONAL=
rem seguridad: el personal TIENE que llevar el preset gabo
if not exist "dist\gabo\RegistroOperativa\_internal\perfiles\gabo.json" (
  echo *** El build personal no incluye perfiles\gabo.json. Abortado. ***
  exit /b 1
)
if not defined ISCC goto :sin_inno
"%ISCC%" installer.iss /DMyAppVersion=%VER% /DPersonal || exit /b 1
echo Listo: dist\RegistroOperativa-Gabo-Setup-%VER%.exe
exit /b 0

:sin_inno
echo.
echo No encontre Inno Setup 6. Instalalo y volve a correr build.bat.
echo La carpeta empaquetada ya esta lista para probar dentro de dist\.
exit /b 0

:borrar
rem Borra una carpeta con reintentos: en Windows a veces la tiene tomada un instante
rem el antivirus, el indexador o una ventana del Explorador ("Acceso denegado").
if not exist "%~1" exit /b 0
for /l %%i in (1,1,5) do (
  attrib -r "%~1\*" /s /d >nul 2>&1
  rmdir /s /q "%~1" >nul 2>&1
  if not exist "%~1" exit /b 0
  timeout /t 2 /nobreak >nul
)
exit /b 1

:limpiar_build
rem Limpieza de las carpetas de trabajo de PyInstaller. Es opcional: cada corrida usa una
rem carpeta nueva (build\publico_N), asi que una que no se pueda borrar no molesta.
for /d %%D in (build\publico* build\gabo*) do call :borrar "%%D"
exit /b 0

:err
echo.
echo *** Fallo el build. Revisa el mensaje de arriba. ***
exit /b 1
:fin
endlocal

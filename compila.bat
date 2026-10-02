@echo off
REM Compila PyFE con PyInstaller.
REM
REM Se usa "python -m PyInstaller" en vez de llamar al .venv a pelo: el
REM .venv queda atado al Python de la maquina donde se creo, y si se
REM copia el proyecto a otra maquina el .venv apunta a un interprete que
REM no existe y el build falla sin avisar nada util. Con este metodo
REM compila el Python que este activo en la consola.
REM
REM Para compilar con un entorno propio, activalo antes:
REM     .venv\Scripts\activate
REM     compila.bat

rd /S /Q dist\main
rd /S /Q dist\main.exe

python -m PyInstaller --clean --hidden-import=httplib2 --collect-data httplib2 --version-file=version.txt -w -F --workpath "%TEMP%\pyfe-build" --icon="imagenes\marca\logo-vogel.ico" main.py
if errorlevel 1 (
    echo.
    echo ERROR: fallo PyInstaller. Revisar que "python" tenga PyQt5, peewee,
    echo cryptography, future, PySimpleSOAP, qrcode, XlsxWriter y PyInstaller.
    exit /b 1
)

if not exist dist\plantillas mkdir dist\plantillas
copy /Y plantillas\factura_marca.csv dist\plantillas\ >nul
copy /Y plantillas\logo-vogel-ejemplo.png dist\plantillas\ >nul
copy /Y plantillas\factura-fondo-vogel-ejemplo.png dist\plantillas\ >nul

REM conf\, imagenes\ y temas\ van SUELTOS junto al .exe, no empaquetados
REM adentro. El sistema.ini los referencia con rutas relativas
REM (cacert = conf/afip_ca_info.crt, certificados/...), asi que tienen que
REM existir como archivos al lado del ejecutable.
REM
REM temas\ es el tema de la interfaz (pyfe.css y sus recursos graficos).
REM Si falta, la app arranca igual pero sin estilos: en el ejecutable se veria
REM con el aspecto crudo, que es justo lo que se vino a arreglar.
REM xcopy NO borra lo que quedo de una build anterior, asi que sin esto los
REM .css viejos del tema seguian viajando al instalador para siempre.
rd /S /Q dist\temas
if not exist dist\conf mkdir dist\conf
xcopy /E /I /Y conf dist\conf >nul
xcopy /E /I /Y imagenes dist\imagenes >nul
xcopy /E /I /Y temas dist\temas >nul
if not exist dist\certificados mkdir dist\certificados
if not exist dist\excel mkdir dist\excel

REM El instalador de Inno Setup lee la plantilla desde la raiz del repo,
REM pero el ejecutable arranca sin ella (la copia el instalador).
if not exist dist\sistema.ini.example copy /Y sistema.ini.example dist\ >nul

echo.
echo Listo: dist\main.exe
echo Para chequear que no falte nada:  python installer\verificar_dist.py
echo Para armar el instalador:         cd installer ^&^& iscc PyFE.iss

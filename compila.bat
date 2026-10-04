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

REM plantillas\ son el PAPEL de la factura: sin ellas no hay PDF, por mas que
REM la app autorice y guarde el comprobante. factura_qr.csv es el formato por
REM defecto, factura-fce.csv el de las FCE, logo.png el que se imprime, y
REM remito.csv el de los remitos.
REM
REM Se copian TODAS las .csv y los .png del ejemplo, y no una lista escrita a
REM mano: la lista anterior se habia quedado corta y el instalador deliveraba
REM una app sin poder facturar en papel. Se copian enteras y sin /B para que
REM la fecha de los archivos no varies en cada build.
if not exist dist\plantillas mkdir dist\plantillas
xcopy /E /I /Y /D plantillas\*.csv dist\plantillas\ >nul
xcopy /E /I /Y /D plantillas\*.png dist\plantillas\ >nul
REM El logo de la marca va aparte porque tiene su propia carpeta en imagenes.
if not exist dist\plantillas\factura-fondo-vogel-ejemplo.png copy /Y plantillas\factura-fondo-vogel-ejemplo.png dist\plantillas\ >nul
if not exist dist\plantillas\logo-vogel-ejemplo.png copy /Y plantillas\logo-vogel-ejemplo.png dist\plantillas\ >nul

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

REM version.txt va DOS veces en el build, y no es redundancia:
REM  - --version-file lo mete DENTRO del .exe, para que Windows muestre la
REM    version en el explorador de archivos.
REM  - esta copia lo deja SUELTO al lado, que es como la app lo lee en
REM    tiempo de ejecucion (vistas/Main.py::_version busca el archivo en las
REM    carpetas de la app). Sin el archivo suelto, la barra de estado y el
REM    dialogo de Acerca de mostraban la version vacia en el ejecutable,
REM    aunque en desarrollo se vieran bien.
copy /Y version.txt dist\ >nul

REM data\ son los datos maestros que se cargan al crear la base (alicuotas de
REM IVA, tipos de comprobante, formas de pago, provincias, etc). La migracion
REM los lee con rutas relativas ("data/tipoiva.csv"), asi que tienen que estar
REM sueltos al lado del .exe.
REM
REM Sin esto, instalando en una maquina nueva la base se creaba VACIA: no
REM habia ni una alicuota de IVA ni una forma de pago, y no se podia emitir
REM nada. Solo seEDIA al instalar.
REM
REM Se copian solo los .csv, no toda la carpeta: data\ trae tambien pablo.db,
REM que es una base de pruebas ajena al producto.
if not exist dist\data mkdir dist\data
copy /Y data\*.csv dist\data\ >nul

REM El instalador de Inno Setup lee la plantilla desde la raiz del repo,
REM pero el ejecutable arranca sin ella (la copia el instalador).
if not exist dist\sistema.ini.example copy /Y sistema.ini.example dist\ >nul

echo.
echo Listo: dist\main.exe
echo Para chequear que no falte nada:  python installer\verificar_dist.py
echo Para armar el instalador:         cd installer ^&^& iscc PyFE.iss

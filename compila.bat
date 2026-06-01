rd /S /Q dist\main
.\.venv\Scripts\pyinstaller.exe --clean --hidden-import=httplib2 --collect-data httplib2 --version-file=version.txt -w -F --workpath "C:\temp" --icon="imagenes\Logo S-01.ico" main.py
if not exist dist\plantillas mkdir dist\plantillas
copy /Y plantillas\factura_marca.csv dist\plantillas\
copy /Y plantillas\logo-vogel-ejemplo.png dist\plantillas\
copy /Y plantillas\factura-fondo-vogel-ejemplo.png dist\plantillas\

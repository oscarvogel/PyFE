rd /S /Q dist\main
pyinstaller --clean --version-file=version.txt -w -F --workpath "C:\temp" --icon="imagenes\Logo S-01.ico" main.py
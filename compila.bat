rd /S /Q dist\main
pyinstaller --clean --win-private-assemblies --version-file=version.txt -F --icon="imagenes\Logo S-01.ico" main.py
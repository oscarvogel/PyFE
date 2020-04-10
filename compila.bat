rd /S /Q dist\main
pyinstaller --clean --win-private-assemblies --version-file=version.txt -F -w --icon="imagenes\Logo S-01.ico" main.py
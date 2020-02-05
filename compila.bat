rd /S /Q dist\main
pyinstaller --clean --win-private-assemblies --version-file=version.txt --windowed -F --icon="imagenes\Logo S-01.ico" main.py -p H:\envs\FE\Lib\site-packages\PyQt4
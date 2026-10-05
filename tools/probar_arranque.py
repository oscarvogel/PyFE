# coding=utf-8
"""Prueba solo la cadena de imports que hace main.py al arrancar.

No abre ninguna ventana. Es la diferencia entre "los tests pasan" y "la app
arranca": los tests importan lo que necesitan, y ninguno importa
`controladores.Main`, que es lo que se carga al inicio y lo que puede romper
con un `NameError` en un archivo que nadie importa en un test.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("PYFE_CARPETA_DATOS",
                      os.path.join(RAIZ, "_sandbox_prueba"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

MODULOS = [
    "modelos.Proveedores",
    "modelos.Articulos",
    "vistas.Articulos",
    "controladores.Articulos",
    "controladores.Stock",
    "controladores.VentaSimple",
    "controladores.Main",
]

fallos = []
for nombre in MODULOS:
    try:
        __import__(nombre)
        print("  ok    {}".format(nombre))
    except Exception as error:
        print("  FALLA {}: {}: {}".format(
            nombre, type(error).__name__, error))
        fallos.append((nombre, error))

print()
if fallos:
    print("{} modulo(s) no importan. La app no arranca.".format(len(fallos)))
    sys.exit(1)

print("La cadena completa de imports levanta.")
print("Por que esto no lo cubria ningun test: los tests importan lo que")
print("necesitan, y `controladores.Main` no es de ninguno.")
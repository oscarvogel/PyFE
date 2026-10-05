"""Captura pantallas que se venian viendo apretadas, antes y despues.

No todas: solo las que el diagnostico marcó, mas un par de control. El
proposito es verlas, porque un numero dice "no se recorta" y no dice si la
columna queda legible.
"""

import ast
import importlib
import os
import sys

if len(sys.argv) > 1 and sys.argv[1] == "offscreen":
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
else:
    os.environ.pop("QT_QPA_PLATFORM", None)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

from PyQt5.QtWidgets import QApplication  # noqa: E402

SALIDA = os.path.join(RAIZ, "_capturas")
if not os.path.isdir(SALIDA):
    os.makedirs(SALIDA)

app = QApplication.instance() or QApplication([])

from libs.tema import aplicar_tema  # noqa: E402

try:
    aplicar_tema(app)
except Exception:
    pass

# Las que el diagnostico marco como apretadas, mas un par de control.
INTERESAN = {
    "reimprimir-remito": "antes_301px",
    "correo-reportes": "antes_460px",
    "categorias-mono": "antes_columnas_56px",
    "iva-ventas": "antes_678px",
    "tipo-responsable": "antes_941px",
    "nueva-venta": "control_ok",
    "productos": "control_ok",
    "stock": "control_ok",
}


def _controladores():
    ruta = os.path.join(RAIZ, "controladores", "Main.py")
    arbol = ast.parse(open(ruta, encoding="utf-8").read(), ruta)
    imports = {}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module and \
                nodo.module.startswith("controladores."):
            for alias in nodo.names:
                imports[alias.asname or alias.name] = nodo.module
    destinos = {}
    for nodo in ast.walk(arbol):
        if not (isinstance(nodo, ast.FunctionDef) and nodo.name == "DESTINOS"):
            continue
        for sub in ast.walk(nodo):
            if not isinstance(sub, ast.Dict):
                continue
            for clave, valor in zip(sub.keys, sub.values):
                if not isinstance(clave, ast.Constant):
                    continue
                llamada = valor.body if isinstance(valor, ast.Lambda) else valor
                if not isinstance(llamada, ast.Call):
                    continue
                args = [a for a in llamada.args if isinstance(a, ast.Name)]
                if args and args[0].id in imports:
                    destinos[clave.value] = (imports[args[0].id], args[0].id)
    return destinos


destinos = _controladores()
for clave, sufijo in INTERESAN.items():
    if clave not in destinos:
        print("no esta en el menu:", clave)
        continue
    modulo, clase = destinos[clave]
    try:
        controlador = getattr(importlib.import_module(modulo), clase)()
        ventana = controlador.view
        ventana.show()
        ventana.raise_()
        ventana.activateWindow()
        for _ in range(10):
            app.processEvents()
        ruta = os.path.join(SALIDA, "{}_{}.png".format(clave, sufijo))
        ventana.grab().save(ruta)
        print("{:<22} {:>5}x{:<5} {}".format(
            clave, ventana.width(), ventana.height(), ruta))
        ventana.close()
    except Exception as e:
        print("{:<22} FALLA {}".format(clave, e))

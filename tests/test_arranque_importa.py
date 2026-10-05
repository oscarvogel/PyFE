"""La app tiene que importar. Es un test, no un script.

Que esta comprobando
--------------------
Que los modulos que `main.py` carga al arrancar se puedan importar: la cadena
`modelos -> vistas -> controladores -> controladores.Main`.

Por que hace falta si hay 800 tests en verde
---------------------------------------------
Porque los tests importan **lo que necesitan**, y `controladores.Main` no es de
ninguno. Un `NameError` en un archivo que solo importa el arranque no lo ve
nadie: la suite pasa entera y la app no abre.

Paso de verdad: faltaba `from libs.ComboBox import ComboSQL` en
`modelos/Proveedores.py`, que usa en la clase `ComboProveedor`. Los 800 tests
daban verde con ese archivo roto.

Que NO comprueba
---------------
Que la ventana abra ni que se vea bien. Importa, y ya.
"""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture(scope="module")
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# La cadena del arranque, en el orden en que la carga main.py. Los modulos que
# van por debajo se列表an tambien porque el error aparece en el mas bajo del
# ciclo: si `modelos.Proveedores` no importa bien, el `NameError` salta cuando
# `vistas.Articulos` lo pide, tres niveles mas arriba.
CADENA = [
    "modelos.Proveedores",
    "modelos.Articulos",
    "vistas.Articulos",
    "controladores.Articulos",
    "controladores.Stock",
    "controladores.VentaSimple",
    "controladores.Main",
]


@pytest.mark.parametrize("nombre", CADENA)
def test_cada_modulo_del_arranque_importa(qt, nombre):
    """Cada eslabon de la cadena, por separado.

    Parametrizado y no en un solo test que importa todo: si falla, el nombre
    del modulo que se rompio esta en el cartel, y no hay que leer el traceback
    entero para averiguarlo.
    """
    __import__(nombre)


def test_los_que_definen_combo_ya_tienen_el_import(qt):
    """El bug que motivo este archivo, Formato de un aserto.

    `modelos/Proveedores.py` define `class ComboProveedor(ComboSQL)` y usa
    `ComboSQL` sin importarlo. Con `from libs.ComboBox import ComboSQL`
    ausente, el archivo importa bien... no: revienta al definir la clase, con
    un `NameError` que sale tres niveles mas arriba, en la linea donde
    `vistas.Articulos` lo pide.

    El aserto mira el archivo como texto y no como modulo, a proposito: asi
    cubre tambien el caso de que el modulo este importado en cache por otro
    test y la cadena de imports de arriba no llegue a ejecutarlo de verdad.
    """
    import ast
    import io

    ruta = os.path.join(RAIZ, "modelos", "Proveedores.py")
    with io.open(ruta, encoding="utf-8") as f:
        arbol = ast.parse(f.read(), ruta)

    # Los nombres que las clases heredan tienen que estar definidos en el
    # modulo: en la raiz del arbol, o importados explicitamente.
    definidos = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Import, ast.ImportFrom)):
            for alias in nodo.names:
                definidos.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(nodo, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            definidos.add(nodo.name)
        elif isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Store):
            definidos.add(nodo.id)

    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.ClassDef):
            continue
        for base in nodo.bases:
            nombres = []
            if isinstance(base, ast.Name):
                nombres = [base.id]
            elif isinstance(base, ast.Attribute):
                nombres = [base.attr]
            for nombre in nombres:
                assert nombre in definidos, \
                    "{}: la clase {} hereda de {} pero el modulo no lo " \
                    "define ni lo importa".format(ruta, nodo.name, nombre)
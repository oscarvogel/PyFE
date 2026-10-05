"""Ninguna pantalla del menu puede caerse al abrirse.

Que esta comprobando
--------------------
Que se puede abrir cada pantalla del menu sin que reviente. Es lo mas barato
que hay y evita lo que mas molesta de una app de escritorio: una pantalla que
tira un traceback en la consola cada vez que la abris, con la ventana
funcionando y el operador pensando que se rompio algo.

Que se haya encontrado asi
--------------------------
Los errores que aparecen aca no son de la logica de la pantalla: son de
construccion. El primero fue un `IndexError` en `Grillas._reparte_anchos`,
porque `ControladorBaseABM` construia un `ABM()` sin columnas y lo descartaba
al tiro, y ese `ABM()` vacio era el que repartia anchos. La pantalla andaba
igual: se veia el traceback y nada mas, que es peor, porque parece un error y
no un defecto.

De donde salen las pantallas
---------------------------
Del propio `controladores/Main.py`, leido con `ast`: se sacan los `import` y
los controladores que cada clave del menu abre. Un mapa escrito a mano en el
test se queda viejo en cuanto se agrega una pantalla, y el test deja de mirar
la pantalla nueva sin avisar; asi que el mapa no existe.
"""

import ast
import importlib
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

RUTA_MAIN = os.path.join(RAIZ, "controladores", "Main.py")


def _claves_del_menu():
    """Las claves de SECCIONES, en el orden en que se ven."""
    from vistas.Main import SECCIONES

    claves = []
    for _titulo, _icono, items in SECCIONES:
        for clave, _etiqueta, _icono in items:
            claves.append(clave)
    return claves


def _controladores_del_menu():
    """{clave: (modulo, clase)} leyendo Main.py con ast.

    Se lee el codigo y no se llama a DESTINOS(), porque DESTINOS() devuelve
    lambdas que ABREN la ventana: para saber que clase usan habria que
    abrirlas todas, que es justo lo que se quiere comprobar.
    """
    arbol = ast.parse(open(RUTA_MAIN, encoding="utf-8").read(), RUTA_MAIN)

    imports = {}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module and \
                nodo.module.startswith("controladores."):
            for alias in nodo.names:
                imports[alias.asname or alias.name] = nodo.module

    destinos = {}
    for nodo in ast.walk(arbol):
        if not (isinstance(nodo, ast.FunctionDef)
                and nodo.name == "DESTINOS"):
            continue
        for sub in ast.walk(nodo):
            if not isinstance(sub, ast.Dict):
                continue
            for clave, valor in zip(sub.keys, sub.values):
                if not isinstance(clave, ast.Constant):
                    continue
                # El valor es `lambda: self._abrir(AlgoController, ...)`, o
                # sea: la llamada esta DENTRO de la lambda, no es la lambda.
                # Y hay entradas que son un metodo directo
                # (`self.diagnostico_arca`), que no abren una pantalla y se
                # dejan pasar.
                if isinstance(valor, ast.Lambda):
                    llamada = valor.body
                else:
                    llamada = valor
                if not isinstance(llamada, ast.Call):
                    continue
                args = [a for a in llamada.args if isinstance(a, ast.Name)]
                if not args:
                    continue
                clase = args[0].id
                if clase in imports:
                    destinos[clave.value] = (imports[clase], clase)
    return destinos


@pytest.fixture(scope="module")
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_las_claves_del_menu_se_abren(qt):
    """El menu entero, de una, dizendo cual se cae.

    Un test por pantalla con `@parametrize` da 30 lineas de PASSED y una de
    FAILED sin contexto. Este recorre todas y al final dice que pantalla
    fue, que es lo que hace falta para arreglarlo.
    """
    destinos = _controladores_del_menu()
    claves = _claves_del_menu()

    # Estas no abren un controlador propio: son metodos de Main que hacen su
    # cosa. Se listan aca y no se las ignora en silencio, asi que si una deja
    # de ser un metodo y pasa a ser un controlador, el test lo dice.
    SIN_CONTROLADOR_PROPIO = {"diagnostico"}

    sin_controlador = [c for c in claves
                       if c not in destinos and c not in SIN_CONTROLADOR_PROPIO]
    assert not sin_controlador, \
        "estas entradas del menu no se sabe que abren: {}. Si es un metodo " \
        "propio de Main y no un controlador, agregalo a " \
        "SIN_CONTROLADOR_PROPIO; si no, se perdio el mapeo.".format(
            sin_controlador)

    caidas = []
    for clave in claves:
        if clave not in destinos:
            continue
        modulo, clase = destinos[clave]
        try:
            controlador = getattr(importlib.import_module(modulo), clase)()
            qt.processEvents()

            tabla = getattr(controlador.view, "tableView", None)
            if tabla is not None and tabla.columnCount() == 0:
                raise AssertionError("abrio con la grilla sin columnas")

            controlador.view.show()
            qt.processEvents()
            controlador.view.close()
        except Exception as e:
            ultimas = [linea for linea in str(e).splitlines() if linea.strip()]
            mensaje = ultimas[-1] if ultimas else e.__class__.__name__
            caidas.append("{} ({}): {}".format(clave, clase, mensaje))

    assert not caidas, "estas pantallas se caen al abrir:\n  " + \
        "\n  ".join(caidas)

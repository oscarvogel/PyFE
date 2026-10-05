# coding=utf-8
"""El sistema.ini se edita a mano, y una clave mala no puede tumbar la app.

Por que existe
--------------
La pantalla de Comprobantes se caia con:

    ValueError: invalid literal for int() with base 10: ''

porque hacia int(LeerIni(clave='cat_iva', key='WSFEv1')) sin proteccion, y la
clave no estaba. Eso no tumba un campo: tumba la pantalla entera. Y la misma
lectura se repetia en 12 lugares, entre ellos la consulta de CAE y la de rinde
de CAEA.

Ademas paso que dos pantallas leyeran el punto de venta con nombres distintos
('punto_venta' y 'pto_vta'), y solo una funcionaba: la otra mostraba siempre
vacio sin avisar.

Estos tests cubren las dos cosas.
"""

import ast
import os
import re
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

CARPETAS = ("libs", "vistas", "controladores", "modelos")


def _fuentes():
    for carpeta in CARPETAS:
        base = os.path.join(RAIZ, carpeta)
        if not os.path.isdir(base):
            continue
        for nombre in sorted(os.listdir(base)):
            if not nombre.endswith(".py"):
                continue
            ruta = os.path.join(base, nombre)
            with open(ruta, "rb") as f:
                crudo = f.read()
            try:
                yield "{}/{}".format(carpeta, nombre), crudo.decode("utf-8")
            except UnicodeDecodeError:
                yield "{}/{}".format(carpeta, nombre), crudo.decode("latin-1")


# -- 1. Ninguna conversion numerica de configuracion sin proteccion ---------

def test_no_quedan_conversiones_de_configuracion_sin_proteger():
    """int(LeerIni(...)) pelado tumba la pantalla si la clave falta o esta vacia."""
    siglas = re.compile(r"\b(int|float)\(\s*LeerIni\(")
    offenders = []
    for rel, texto in _fuentes():
        for numero, linea in enumerate(texto.splitlines(), 1):
            if siglas.search(linea):
                offenders.append("{}:{} -> {}".format(rel, numero, linea.strip()[:90]))

    assert not offenders, (
        "conversiones de configuracion sin proteger (una clave vacia tumba la "
        "pantalla entera):\n  " + "\n  ".join(offenders))


def test_a_entero_no_tumba_con_ningun_valor():
    from libs.Utiles import a_entero

    assert a_entero("5") == 5
    assert a_entero(" 7 ") == 7
    assert a_entero(9) == 9
    # Lo que se<KeyEvent> viejo rompia
    assert a_entero("") == 0
    assert a_entero(None) == 0
    assert a_entero("hola") == 0
    assert a_entero("cinco", 3) == 3
    # Y los que Aun tienen sentido
    assert a_entero("5.0") == 5
    assert a_entero("5,0") == 5
    # Con defecto propio
    assert a_entero("", 1) == 1
    assert a_entero("nada", 1) == 1


def test_a_decimal_distingue_cero_de_desconocido():
    import decimal

    from libs.Utiles import a_decimal

    assert a_decimal("10.5") == decimal.Decimal("10.5")
    assert a_decimal("10,5") == decimal.Decimal("10.5")
    # Cero es un importe; None es 'no hay dato'. No es lo mismo y se usa para
    # distinguir, asi que no se pueden mezclar.
    assert a_decimal("0") == decimal.Decimal("0")
    assert a_decimal("0") is not None
    assert a_decimal("") is None
    assert a_decimal("nada") is None
    assert a_decimal("nada", decimal.Decimal("1")) == decimal.Decimal("1")


# -- 2. Una sola clave por concepto ----------------------------------------

def test_el_punto_de_venta_se_llama_igual_en_todo_el_codigo():
    """Habia dos nombres para lo mismo: 'pto_vta' y 'punto_venta'.

    La que lee el codigo al emitir es 'pto_vta'. La otra, la de la barra de
    estado, nunca encontraba nada y mostraba el campo vacio sin avisar.
    """
    nombres = set()
    donde = {}
    patron = re.compile(r"clave=['\"](pto_vta|punto_venta|punto_vta)['\"]")
    for rel, texto in _fuentes():
        for numero, linea in enumerate(texto.splitlines(), 1):
            m = patron.search(linea)
            if m:
                nombres.add(m.group(1))
                donde.setdefault(m.group(1), []).append(
                    "{}:{}".format(rel, numero))

    assert nombres == {"pto_vta"}, (
        "el punto de venta se lee con mas de un nombre: {}. La que funciona es "
        "'pto_vta'; las demas muestran siempre vacio.\n  {}".format(
            nombres, donde))


def test_toda_clave_de_configuracion_convertida_existe_en_el_ini():
    """Si el codigo convierte una clave a numero, tiene que existir en el .ini.

    Ojo: el nombre de la clave importa. Con [WSFEv1] categoria_iva en vez de
    cat_iva, la pantalla de Comprobantes no abria.
    """
    ini = os.path.join(RAIZ, "sistema.ini")
    if not os.path.isfile(ini):
        pytest.skip("no hay sistema.ini en este entorno")

    import configparser
    with open(ini, "r", encoding="utf-8", errors="replace") as f:
        configuracion = configparser.ConfigParser()
        configuracion.read_string(f.read())
    # ConfigParser baja las claves a minuscula, asi que el .ini no distingue.
    existentes = {clave.lower() for seccion in configuracion.sections()
                  for clave in configuracion.options(seccion)}
    existentes.add("cacert")  # la lee el codigo, no siempre esta en el .ini

    leidas = set()
    patron = re.compile(r"clave='([A-Za-z_0-9]+)'\s*,\s*key='WSFEv1'")
    for _rel, texto in _fuentes():
        leidas.update(patron.findall(texto))

    faltan = sorted(c for c in leidas if c.lower() not in existentes)
    assert not faltan, (
        "estas claves de [WSFEv1] las lee el codigo pero no estan en el "
        "sistema.ini: {}. Con una vacia, int() revienta y la pantalla no "
        "abre.".format(faltan))

# -- Jerarquia de acciones ------------------------------------------------

# vistas/ABM.py tiene dos primarios a proposito: "Nuevo" vive en la pestaña
# Lista y "Guardar" en la pestana Detalle. Nunca se ven juntos, y cada
# pestana tiene su propia accion principal.
#
# vistas/Stock.py es lo mismo con ventanas en vez de pestanas: "Ajustar" es
# la accion principal de la consulta y "Grabar" de la de ajuste. La de ajuste
# se abre desde la de consulta, asi que las dos ventanas nunca coexisten.
# vistas/Facturas.py tiene dos primarios a proposito: "Emitir factura" esta
# visible antes de autorizar y "Imprimir" despues. Son el mismo boton en dos
# estados, no dos acciones que compitan.
#
# vistas/Stock.py es lo mismo con ventanas en vez de estados: "Ajustar" es la
# accion principal de la consulta y "Grabar" de la de ajuste. La de ajuste
# se abre desde la de consulta, asi que las dos ventanas nunca coexisten.
EXCEPCIONES_PRIMARIOS = {"vistas/ABM.py": 2, "vistas/Stock.py": 2,
                         "vistas/Facturas.py": 2}


def test_ninguna_pantalla_tiene_dos_acciones_principales():
    """Dos botones en azul en la misma pantalla no dicen nada.

    Con "Agrega" y "Emitir" los dos azules, el ojo no sabe donde termina la
    carga de la pantalla y donde se emite. La accion principal es una sola.
    """
    import os
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    marcador = "estilo='primario'"

    ofensores = []
    for carpeta in ("vistas", "libs", "controladores"):
        for ruta in sorted((raiz / carpeta).glob("*.py")):
            texto = ruta.read_text(encoding="utf-8", errors="replace")
            cantidad = texto.count(marcador)
            if cantidad == 0:
                continue
            rel = "{}/{}".format(carpeta, ruta.name)
            if rel == "libs/Botones.py":
                continue  # es la definicion de las clases, no una pantalla
            limite = EXCEPCIONES_PRIMARIOS.get(rel, 1)
            if cantidad > limite:
                ofensores.append("{}: {} primarios (maximo {})".format(
                    rel, cantidad, limite))

    assert not ofensores, (
        "pantallas con mas de una accion principal:\n  " + "\n  ".join(ofensores))

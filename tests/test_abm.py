# coding=utf-8
"""El ABM de clientes: la pantalla de alta, baja y modificacion.

Por que existe este archivo
---------------------------
Dos cosas se rompieron juntas y las dos se ven en esta misma pantalla.

1) ``libs.tema.limpiar_estado()`` llamaba a un nombre que no existia
   (``marca_estado`` en vez de ``marcar_estado``). ``Agrega()`` y
   ``CargaDatos()`` la llaman para cada control, asi que el boton "Nuevo" y el
   boton "Editar" tiraban ``NameError`` en los doce ABM de la app. No lo
   agarra ningun test de grilla ni de tema: hace falta apretar el boton.

2) La columna de codigo se llevaba 732 de los 959 px de la tabla y los
   clientes se veian como "1,00". Las dos cosas vienen de decisiones de la
   grilla compartida, no de esta pantalla: el ABM de clientes es donde se ven.

Va con QT_QPA_PLATFORM=offscreen y una base sqlite en memoria: no toca la base
del sandbox, no necesita ARCA y no muestra ventanas.
"""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


# Nombres reales, no "cliente 1": con un nombre corto la columna de texto entra
# justa en cualquier ancho y la prueba del layout no probaria nada.
CLIENTES = [
    (1, "CONSUMIDOR FINAL"),
    (2, "MUNICIPALIDAD DE PTO. RICO"),
    (3, "TRANS. DOÑA ROSA SOC. DE FDO. Nº 1"),
    (4, "ADRIMAR SRL"),
    (5, "MUNICIPALIDAD DE GARUHAPE"),
]


@pytest.fixture(scope="module")
def app():
    from PyQt5.QtWidgets import QApplication
    aplicacion = QApplication.instance() or QApplication(sys.argv)
    from libs.tema import aplicar_tema
    aplicar_tema(aplicacion)
    return aplicacion


@pytest.fixture
def vista(app):
    """La pantalla de clientes con datos, contra una base en memoria.

    Los modelos quedan atados a una base propia mientras dura el test y se
    vuelven a atar a la del sandbox al final: si se olvidara, el resto de la
    suite pasaria a escribir en una base que no es la de siempre.
    """
    from peewee import SqliteDatabase

    from modelos.Clientes import Cliente
    from modelos.Formaspago import Formapago
    from modelos.Impuestos import Impuesto
    from modelos.Localidades import Localidad
    from modelos.Tipodoc import Tipodoc
    from modelos.Tiporesp import Tiporesp

    modelos = (Cliente, Localidad, Tipodoc, Tiporesp, Formapago, Impuesto)
    anteriores = [m._meta.database for m in modelos]

    memoria = SqliteDatabase(":memory:")
    for modelo in modelos:
        modelo.bind(memoria)
    memoria.connect()
    for modelo in (Localidad, Tipodoc, Tiporesp, Formapago, Impuesto, Cliente):
        modelo.create_table(safe=True)

    # insert_many es perezoso en peewee: sin .execute() no inserta nada y la
    # grilla se abre vacia sin decir por que.
    Cliente.insert_many([
        {"idcliente": i, "nombre": n, "domicilio": "x", "telefono": "",
         "idLocalidad": 1, "cuit": "20123456789", "dni": 0, "tipodocu": 1,
         "tiporesp": 1, "formapago": 1, "percepcion": 1}
        for i, n in CLIENTES]).execute()
    assert Cliente.select().count() == len(CLIENTES), "no entraron los clientes"

    from vistas.Clientes import ClientesView
    v = ClientesView()
    v.ArmaTabla()
    v.resize(906, 584)
    v.show()
    app.processEvents()
    yield v
    v.close()
    for modelo, anterior in zip(modelos, anteriores):
        modelo.bind(anterior)


# -- El boton "Nuevo" y el boton "Editar" tienen que funcionar ---------------

def test_editar_no_revienta(app, vista):
    """Editar una fila completa los campos con los datos del cliente.

    Antes tiraba NameError apenas cargaba el primer control.
    """
    vista.tableView.setCurrentCell(0, 0)
    vista.Modifica()
    assert vista.controles["nombre"].text() == CLIENTES[0][1]
    assert vista.controles["domicilio"].text() == "x"
    # Y quedo en la pestana de detalle, que es donde se carga.
    assert vista.tabWidget.currentIndex() == 1


def test_nuevo_deja_los_campos_vacios_y_abre_el_detalle(app, vista):
    """El "Nuevo" limpia los campos para cargar uno desde cero.

    Antes tiraba NameError en la primera llamada a ``limpiar_estado``, asi que
    no habia forma de dar de alta un cliente.
    """
    vista.Agrega()
    assert vista.controles["nombre"].text() == ""
    assert vista.controles["domicilio"].text() == ""
    assert vista.tabWidget.currentIndex() == 1
    # Volver a la lista es lo que deja seguir dando de alta.
    vista.btnCancelarClicked()
    assert vista.tabWidget.currentIndex() == 0


# -- Que la pantalla se vea bien ---------------------------------------------

def test_la_columna_de_codigo_no_se_come_la_tabla(app, vista):
    """El nombre tiene que ocupar la pantalla, no el id.

    Con la tabla vacia la columna que se estira se elige por el texto del
    encabezado, y "Idcliente" (9 letras) le ganaba a "Nombre" (6): el codigo
    se llevaba 732 de 959 px y los nombres quedaban partidos en dos renglones.

    Se comparan columnas y no pixeles: cuanto mide un encabezado depende de
    la fuente de la maquina.
    """
    tabla = vista.tableView
    codigo, nombre = tabla.columnWidth(0), tabla.columnWidth(1)
    assert codigo < tabla.viewport().width() / 3, (
        "Idcliente mide {} px de {}: se esta comiendo la tabla".format(
            codigo, tabla.viewport().width()))
    assert nombre > codigo * 3, (
        "Idcliente {} px contra Nombre {} px: el sobrante no llego a la "
        "columna que se lee".format(codigo, nombre))


def test_el_cliente_se_muestra_entero_y_no_con_decimales(app, vista):
    for fila in range(vista.tableView.rowCount()):
        celda = vista.tableView.item(fila, 0)
        assert celda.text() == str(CLIENTES[fila][0]), (
            "el cliente {} se muestra como {!r}".format(
                CLIENTES[fila][1], celda.text()))


def test_el_titulo_no_esta_repetido_dentro_de_la_pantalla(app, vista):
    """El titulo va en la barra de la ventana, no tambien como etiqueta.

    Con los dos, arriba de la lista hay dos lineas que dicen lo mismo. La
    ventana ademas se titula con el nombre de la tabla ("Clientes") y no con
    "ABM de Clientes": la pantalla se abre desde la barra lateral, donde ya se
    sabe que es un alta-baja-modificacion.
    """
    from PyQt5.QtWidgets import QLabel

    assert vista.windowTitle() == "Clientes"

    repetidos = [etiqueta.text() for etiqueta in vista.findChildren(QLabel)
                 if etiqueta.text().strip() == "Clientes"]
    assert not repetidos, (
        "el titulo esta dos veces: ademas de la barra, hay una etiqueta adentro")

# coding=utf-8
"""Buscar clientes cuando hay miles y no tres.

Por que existe este archivo
---------------------------
Con tres clientes, escribir "muni" y elegir de una lista de tres parece que
alcanza. El problema aparece con la base real, que ya tiene 57 clientes y va
para miles, y son tres cosas distintas:

1. **La consulta no tenia tope.** ``list(Cliente.select().where(...))`` traia
   todas las coincidencias a memoria y las volcaba todas en la lista. Con un
   fragmento corto tipo "a" son cientos de filas, y no habia forma de acotar:
   la unica salida era cerrar el dialogo y volver a escribir desde la venta.

2. **Las tildes dependian del motor de base.** ``campo.contains(texto)``
   compila a ``LIKE '%texto%'``, y SQLite (el sandbox) no ignora tildes
   mientras que MySQL depende de la collation. Una busqueda que funciona en la
   maquina del desarrollador puede no encontrar nada en la del cliente, y ahi
   "no lo encuentra" se lee como "el cliente no esta cargado".

3. **El buscador F2 declaraba un ``limite`` que nunca usaba**, y ademas contaba
   las filas con ``len(consulta)``, que ejecuta la consulta entera.

Va con QT_QPA_PLATFORM=offscreen y una base sqlite en memoria con 1200 clientes:
si el tope o el contador estuvieran rotos, con 57 clientes de prueba no se
vería.
"""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

CANTIDAD_CLIENTES = 1200
LIMITE = 100


@pytest.fixture(scope="module")
def app():
    from PyQt5.QtWidgets import QApplication
    aplicacion = QApplication.instance() or QApplication(sys.argv)
    from libs.tema import aplicar_tema
    aplicar_tema(aplicacion)
    return aplicacion


@pytest.fixture
def clientes(app):
    """1200 clientes en memoria, con y sin tilde, para que el filtro se note.

    Se restauran los modelos al final: si se olvidara, el resto de la suite
    pasaria a leer de una base que no es la de siempre.
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

    # Nombres con tilde, sin tilde y con ñ, que es donde el filtro se rompe.
    Cliente.insert_many([
        {"idcliente": i, "nombre": nombre, "domicilio": "x", "telefono": "",
         "idLocalidad": 1, "cuit": cuit, "dni": dni, "tipodocu": 1,
         "tiporesp": 1, "formapago": 1, "percepcion": 1}
        for i, (nombre, cuit, dni) in enumerate(_CLIENTES, start=1)]).execute()
    assert Cliente.select().count() == CANTIDAD_CLIENTES

    yield Cliente

    for modelo, anterior in zip(modelos, anteriores):
        modelo.bind(anterior)


def _generar_clientes():
    """1200 clientes: los que importan para las pruebas, repetidos.

    - 3 "Municipalidad ..." con tilde y sin tilde
    - 1 "Cristián" con tilde, que es el caso que antes no se encontraba
    - 1 "Compañía" con ñ
    - el resto con nombres comunes que hacen que cualquier fragmento corto
      devuelva cientos de filas
    """
    fila = []
    # Los CUIT son inventados a proposito. Los de verdad (los del padron, que
    # son datos de clientes reales) no van a un repo: ya paso con otro CUIT y
    # se limpio en 8c3feda.
    especiales = [
        ("MUNICIPALIDAD DE CAPIOVI", "30-11111111-1", 0),
        ("MUNICIPALIDAD DE GARUHAPE", "30-22222222-2", 0),
        ("MUNICIPALIDAD DE PTO. RICO", "30333333333", 0),
        ("CRISTIÁN ALEGRE", "20-12345678-9", 0),
        ("COMPAÑÍA DEL NORTE SA", "30-44444444-4", 0),
    ]
    for nombre, cuit, dni in especiales:
        fila.append((nombre, cuit, dni))
    genericos = [
        "DISTRIBUIDORA DEL SUR SRL",
        "FERRETERIA LA ESQUINA",
        "AGROINSUMOS DEL LITORAL",
        "TRANSPORTES DEL NORTE",
        "SUPERMERCADO SAN JUAN",
        "COOPERATIVA DE TRABAJO",
        "METALURGICA DEL CENTRO",
    ]
    for i in range(CANTIDAD_CLIENTES - len(especiales)):
        base = genericos[i % len(genericos)]
        # El numero al final hace que cada fila sea un cliente distinto.
        fila.append(("{} N{}".format(base, i), "20{:08d}-{}".format(i, i % 10), 0))
    return fila


# El nombre generico con salto de linea se parte para que la linea del
# generico sea legible en el archivo.
_CLIENTES = _generar_clientes()


# -- El texto se busca igual con y sin tilde ---------------------------------

def test_busca_con_tilde_y_sin_tilde(clientes):
    from libs.busqueda import normalizar

    assert normalizar("Municipalidad") == "municipalidad"
    assert normalizar("CRISTIÁN") == "cristian"
    assert normalizar("Compañía") == "compania"
    assert normalizar("Ñoño") == "nono"


def test_la_consulta_encuentra_las_tres_formas_de_ese_nombre(clientes):
    """Buscar 'municipalidad' tiene que traer las tres, tilde o no tilde.

    Con el LIKE de antes, "MUNICIPALIDAD DE PTO. RICO" (sin tilde) se
    encontraba y las otras dos no. El nombre del cliente existe, el filtro
    mentia.
    """
    from libs.busqueda import contiene
    from modelos.Clientes import Cliente

    encontrados = list(Cliente.select().where(contiene(Cliente.nombre, "municipalidad")))
    nombres = {c.nombre for c in encontrados}
    assert nombres == {
        "MUNICIPALIDAD DE CAPIOVI",
        "MUNICIPALIDAD DE GARUHAPE",
        "MUNICIPALIDAD DE PTO. RICO",
    }


def test_buscar_sin_tilde_encuentra_el_nombre_con_tilde(clientes):
    from libs.busqueda import contiene
    from modelos.Clientes import Cliente

    encontrados = list(Cliente.select().where(contiene(Cliente.nombre, "cristian")))
    assert [c.nombre for c in encontrados] == ["CRISTIÁN ALEGRE"]


def test_la_enie_no_se_traga(clientes):
    from libs.busqueda import contiene
    from modelos.Clientes import Cliente

    encontrados = list(Cliente.select().where(contiene(Cliente.nombre, "compania")))
    assert [c.nombre for c in encontrados] == ["COMPAÑÍA DEL NORTE SA"]


# -- El tope de resultados y el total ---------------------------------------

@pytest.fixture
def controlador(clientes):
    from controladores.VentaSimple import VentaSimpleController
    return VentaSimpleController()


def test_la_lista_no_se_pasa_del_tope(controlador, clientes):
    """Un fragmento corto trae cientos; la lista trae 100 y el total, todos."""
    coincidencias, total = controlador._coincidencias_clientes("super")
    assert total > LIMITE, (
        "el caso de prueba no sirve: con 1200 clientes deberia superar el tope")
    assert len(coincidencias) == LIMITE
    assert total > len(coincidencias), (
        "el total tiene que avisar que la lista esta recortada, si no el "
        "operador cree que ya los vio a todos")


def test_acotar_muestra_el_total_real(controlador, clientes):
    """Con un termino mas largo bajan las coincidencias y ya no hay recorte."""
    _, total = controlador._coincidencias_clientes("cristian")
    assert total == 1


def test_sin_texto_no_trae_todos_los_clientes(controlador, clientes):
    """Un texto vacio no significa "mostrame los 1200".

    Volcar la tabla entera no es una busqueda: es una pantalla imposible de
    usar, y ademas esconde que hay que acotar.
    """
    assert controlador.buscar_clientes("") == []
    assert controlador._coincidencias_clientes("") == ([], 0)


# -- Buscar por codigo, CUIT o DNI sigue siendo exacto -----------------------

def test_el_codigo_se_encuentra_exacto(controlador, clientes):
    encontrados = controlador.buscar_clientes("42")
    assert [c.idcliente for c in encontrados] == [42]


def test_el_cuit_se_encuentra_con_y_sin_guiones(controlador, clientes):
    """Las dos formas del mismo CUIT tienen que dar el mismo cliente.

    En la base el CUIT se guarda sin guiones ("30333333333") y el operador lo
    escribe como lo ve en la factura ("30-33333333-3").
    """
    con_guiones = controlador.buscar_clientes("30-33333333-3")
    sin_guiones = controlador.buscar_clientes("30333333333")
    assert con_guiones[0].nombre == "MUNICIPALIDAD DE PTO. RICO"
    assert sin_guiones[0].nombre == "MUNICIPALIDAD DE PTO. RICO"


def test_un_cuit_parcial_no_trae_cualquier_cosa(controlador, clientes):
    """"3033" no matchea todos los CUIT que arrancan con 3033.

    Buscar por documento es igualdad exacta a proposito: un contains sobre el
    CUIT devuelve cualquier cliente que comparta los primeros digitos, y en
    una venta eso es elegir al cliente equivocado.
    """
    assert controlador.buscar_clientes("3033") == []


# -- El dialogo deja acotar sin cerrar ---------------------------------------

def test_el_dialogo_tiene_buscador_y_no_se_cierra_al_acotar(app, controlador, clientes):
    """El caso que reporto el usuario, con 1200 clientes en vez de 57.

    Antes: la lista llegaba fija, y para acotar había que cerrar el dialogo y
    volver a escribir desde la venta.
    """
    from PyQt5.QtWidgets import QDialog
    from vistas.VentaSimple import VentaSimpleSeleccionClienteDialog

    dialogo = VentaSimpleSeleccionClienteDialog(controlador._coincidencias_clientes,
                                               busqueda="super")
    dialogo.show()
    app.processEvents()

    assert dialogo.listaClientes.count() == LIMITE

    # Y dice cuantos hay en total, que es lo que permite saber que la lista
    # esta recortada. Con 57 clientes de prueba el recorte no se veria, por eso
    # la base tiene 1200.
    _, total = controlador._coincidencias_clientes("super")
    assert total > LIMITE, "el caso de prueba no alcanza para probar el recorte"
    assert "de {} coincidencias".format(total) in dialogo.lblCuenta.text(), (
        "tiene que avisar cuantos hay en total: {}".format(dialogo.lblCuenta.text()))

    # Acota escribiendo en el buscador del propio dialogo, sin cerrarlo.
    dialogo.txtBuscar.setText("cristian")
    app.processEvents()
    assert dialogo.listaClientes.count() == 1
    assert dialogo.listaClientes.item(0).text().startswith("4 - CRISTIÁN")

    # Y elige el de la lista.
    dialogo._aceptar_primero()
    assert dialogo.result() == QDialog.Accepted
    assert dialogo.cliente.nombre == "CRISTIÁN ALEGRE"
    dialogo.close()


def test_el_dialogo_vacio_no_vuelca_la_tabla(app, controlador, clientes):
    from vistas.VentaSimple import VentaSimpleSeleccionClienteDialog

    dialogo = VentaSimpleSeleccionClienteDialog(controlador._coincidencias_clientes,
                                               busqueda="")
    dialogo.show()
    app.processEvents()
    assert dialogo.listaClientes.count() == 0
    assert "Escribi" in dialogo.lblCuenta.text()
    dialogo.close()


# -- El buscador F2 usa el limite que declaraba ------------------------------

def test_el_buscador_f2_respeta_su_limite(app, clientes):
    """F2 declaraba `limite = 100` y nunca lo usaba.

    Ademas contaba con `len(consulta)`, que en peewee ejecuta la consulta
    entera: con una tabla grande traia todas las filas a memoria en cada tecla.
    """
    from vistas.Busqueda import UiBusqueda

    ventana = _ventana_f2(clientes, campos_como_nombres=True)

    ventana.lineEdit.setText("super")
    app.processEvents()

    assert ventana.tableView.rowCount() == 100, (
        "trajo {} filas: el limite no se esta aplicando".format(
            ventana.tableView.rowCount()))
    assert "coincidencias" in ventana.lblCuenta.text()
    ventana.close()


def test_el_buscador_f2_acepta_los_dos_formatos_de_campos(app, clientes):
    """`campos` puede ser una lista de nombres o de campos de peewee.

    No es un detalle: `CargaDatos` corre dentro del slot de `textChanged`, y
    una excepcion ahi no se muestra, PyQt5 aborta el proceso sin dejar traza.
    Antes, pasar un campo de peewee (que es lo natural) reventaba la app entera.
    """
    for como_campos in (True, False):
        ventana = _ventana_f2(clientes, campos_como_nombres=como_campos)
        ventana.lineEdit.setText("cristian")
        app.processEvents()
        assert ventana.tableView.rowCount() == 1, (
            "con campos_como_nombres={} trajo {} filas".format(
                como_campos, ventana.tableView.rowCount()))
        assert ventana.tableView.horizontalHeaderItem(1).text() == "Nombre"
        ventana.close()


def _ventana_f2(clientes, campos_como_nombres):
    from vistas.Busqueda import UiBusqueda

    ventana = UiBusqueda()
    ventana.modelo = clientes
    ventana.campoBusqueda = clientes.nombre
    ventana.campoRetorno = clientes.idcliente
    # Es lo que pasan los que llaman hoy (Validaciones: ['idcliente', 'nombre']).
    ventana.campos = (["idcliente", "nombre"] if campos_como_nombres
                      else [clientes.idcliente, clientes.nombre])
    ventana.show()
    return ventana


# -- La barra lateral y la base usan el mismo criterio ------------------------

def test_la_barra_lateral_y_la_base_normalizan_igual(app):
    """Si la barra acepta 'configuracion' y la base no, el operador concluye
    que el cliente no existe."""
    from libs.busqueda import normalizar
    from vistas.Main import MainView

    shell = MainView()
    shell.initUi()
    assert shell._normalizar("Configuración") == normalizar("Configuración")
    assert shell._normalizar("CONFIGURACION") == normalizar("Configuración")

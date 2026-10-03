# coding=utf-8
"""Componentes de la etapa 3: formato de importes y buscador de la barra.

El foco esta en una trampa concreta que casi se lleva por delante los totales
de las facturas: si una celda muestra "1.234,56" y otro codigo la lee con
re.sub("[^0123456789.]", "", texto), obtiene 1.23456. No da error, la tabla se
ve bien, y el total sale mal. Por eso el valor crudo va aparte del texto y la
lectura tiene que saber tomar el correcto.
"""

import decimal
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


@pytest.fixture(scope="module")
def app():
    """Aplicacion con el tema real.

    Va local a este archivo y no se importa del otro de smoke: los tests de
    cada pieza tienen que poder correr solos.
    """
    from PyQt5.QtWidgets import QApplication
    aplicacion = QApplication.instance() or QApplication(sys.argv)
    from libs.tema import aplicar_tema
    aplicar_tema(aplicacion)
    return aplicacion


# -- Formato de importes ---------------------------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("1.234.567,89", 1234567.89),
    ("1.500,50", 1500.5),
    ("-1.500,50", -1500.5),
    ("1500,00", 1500),
    ("0,00", 0),
    ("21,00", 21),
    ("1.234", 1234),          # solo punto: en argentino es separador de miles
    ("1,234", 1234),          # solo coma con 3 decimales: tambien miles
    ("1234.5", 1234.5),       # el punto como decimal, tal como venia antes
    ("1,23", 1.23),
    ("", 0),
    ("   ", 0),
    (None, 0),
    (1500, 1500),
    (1500.5, 1500.5),
])
def test_leer_un_importe_escrito_para_verse(texto, esperado):
    from libs.Grillas import _a_numero_texto
    assert _a_numero_texto(texto) == pytest.approx(esperado, abs=0.01)


def test_importe_ylectura_vuelven_a_lo_mismo():
    """Ida y vuelta: formatear y volver a leer tiene que dar el mismo numero.

    Es la garantia de que se puede formatear para mostrar sin miedo a romper
    los calculos.
    """
    from libs.Grillas import _a_numero_texto, _formato_importe

    import random
    random.seed(11)
    for _ in range(2000):
        valor = round(random.uniform(-9999999, 9999999), 2)
        assert _a_numero_texto(_formato_importe(valor)) == pytest.approx(
            valor, abs=0.01), "el importe {} no vuelve igual".format(valor)


def test_cantidad_no_muestra_ceros_de_mas():
    from libs.Grillas import _formato_cantidad

    assert _formato_cantidad(2) == "2"
    assert _formato_cantidad(150) == "150"
    assert _formato_cantidad(1.5) == "1,5"
    assert _formato_cantidad(0.25) == "0,25"
    assert _formato_cantidad(-3) == "-3"


def test_importe_si_lleva_los_dos_decimales():
    from libs.Grillas import _formato_importe

    assert _formato_importe(1500) == "1.500,00"
    assert _formato_importe(1234567.89) == "1.234.567,89"
    assert _formato_importe(0) == "0,00"


# -- La grilla -------------------------------------------------------------

@pytest.fixture
def grilla(app):
    from libs.Grillas import Grilla
    g = Grilla(tamanio=10)
    g.ArmaCabeceras(
        cabeceras=["Cant.", "Codigo", "Detalle", "Unitario", "IVA", "SubTotal"],
        formatos=["Cantidad", "String", "String", "Moneda", "Entero", "Moneda"])
    g.columnasHabilitadas = [0, 1, 2, 3, 4]
    g.resize(900, 260)
    g.show()
    app.processEvents()
    yield g
    g.close()


def test_la_celda_muestra_importe_pero_guarda_el_numero(app, grilla):
    """Lo que se ve es lindo; lo que se calcula es el numero entero.

    Es el punto critico: si la celda guardara solo el texto con puntos de
    miles, cualquier suma leeria 1.234 en vez de 1234.
    """
    from PyQt5.QtCore import Qt

    grilla.AgregaItem([2, "TORN-1", "Tornillo", 1250.5, 21, 3025.21])
    app.processEvents()

    assert grilla.item(0, 3).text() == "1.250,50"
    assert grilla.item(0, 3).data(Qt.UserRole) == 1250.5
    assert grilla.ObtenerItemNumerico(fila=0, col="Unitario") == pytest.approx(1250.5)


def test_la_cantidad_se_muestra_sin_ceros(app, grilla):
    from PyQt5.QtCore import Qt

    grilla.AgregaItem([2, "TORN-1", "Tornillo", 1250.5, 21, 3025.21])
    app.processEvents()
    assert grilla.item(0, 0).text() == "2"
    assert grilla.item(0, 0).data(Qt.UserRole) == 2


def test_el_iva_no_muestra_decimales(app, grilla):
    grilla.AgregaItem([2, "TORN-1", "Tornillo", 1250.5, 21, 3025.21])
    app.processEvents()
    assert grilla.item(0, 4).text() == "21"


def test_la_suma_de_la_columna_sale_bien(app, grilla):
    """La prueba que importa: el total de la tabla tiene que coincidir."""
    filas = [
        [2, "TORN-1", "Tornillo", 1250.5, 21, 3025.21],
        [1, "ARAND-1", "Arandela", 85.9, 21, 103.94],
        [150, "TUE-8", "Tubo", 18450.0, 21, 336117.0],
        [1, "SERV-1", "Mano de obra", 485000.0, 0, 485000.0],
    ]
    for f in filas:
        grilla.AgregaItem(f)
    app.processEvents()

    total_celda = sum(grilla.ObtenerItemNumerico(fila=i, col="SubTotal")
                      for i in range(len(filas)))
    total_esperado = sum(decimal.Decimal(str(f[5])) for f in filas)
    assert total_celda == pytest.approx(float(total_esperado), abs=0.01), (
        "el total leido de las celdas no coincide: {} contra {}".format(
            total_celda, total_esperado))


def test_el_encabezado_de_importes_va_a_la_derecha(app, grilla):
    """Con los titulos a la izquierda y los numeros a la derecha, una columna
    de importes se ve rota."""
    from PyQt5.QtCore import Qt

    for col, nombre in ((0, "Cant."), (3, "Unitario"), (4, "IVA"), (5, "SubTotal")):
        alineacion = grilla.horizontalHeaderItem(col).textAlignment()
        assert alineacion & Qt.AlignRight, (
            "el encabezado de {} deberia ir a la derecha".format(nombre))
    for col, nombre in ((1, "Codigo"), (2, "Detalle")):
        alineacion = grilla.horizontalHeaderItem(col).textAlignment()
        assert not alineacion & Qt.AlignRight, (
            "el encabezado de {} deberia ir a la izquierda".format(nombre))


def test_la_columna_cantidad_no_se_comedia_la_fila(app, grilla):
    """"Cant." con dos digitos y una coma se comia media fila; el ancho sale
    de la longitud del encabezado, no del contenido."""
    ancho = grilla.columnWidth(0)
    assert ancho <= 110, (
        "la columna Cant. mide {} px: deberia ser angosta".format(ancho))
    assert grilla.columnWidth(2) > ancho, (
        "la columna Detalle deberia ser mas ancha que la cantidad")


def test_el_ancho_sobrante_no_lo_gana_una_columna_de_codigo(app):
    """Un codigo angosto no puede quedarse con media tabla.

    Con la tabla vacia la columna que se estira se elige por el texto del
    encabezado, y en el ABM de clientes eso daba "Idcliente" (9 letras) por
    sobre "Nombre" (6): el codigo se llevaba 732 de 959 px y los nombres
    quedaban partidos en dos renglones, con 700 px de blanco al lado.

    Con la primera fila ya se sabe que hay en cada columna, y un codigo es
    numerico: los numericos no compiten por el sobrante.

    La comparacion es entre columnas y no en pixeles fijos a proposito: cuanto
    mide un encabezado depende de la fuente instalada, y una prueba que falla
    en la maquina de otro por un cambio de tipografia no sirve para nada.
    """
    from libs.Grillas import Grilla

    g = Grilla(tamanio=10)
    g.ArmaCabeceras(cabeceras=["Idcliente", "Nombre"],
                    formatos=["Entero", "String"])
    g.resize(900, 260)
    g.show()
    app.processEvents()
    g.AgregaItem([1, "MUNICIPALIDAD DE PTO. RICO"])
    app.processEvents()

    codigo, nombre = g.columnWidth(0), g.columnWidth(1)
    assert codigo < g.viewport().width() / 3, (
        "la columna de codigo mide {} px de {}: se esta comiendo la tabla".format(
            codigo, g.viewport().width()))
    assert nombre > codigo * 3, (
        "la columna de texto mide {} px contra {} del codigo: el sobrante no "
        "llego a donde se lee".format(nombre, codigo))
    g.close()


def test_un_codigo_no_se_muestra_con_decimales(app):
    """El id de un cliente es 1, no "1,00": alcanza con declararlo Entero.

    Que lo declare quien arma la tabla y no que la grilla lo adivine con el
    valor de la primera fila es a proposito: una columna de importes a la que
    se le pasa un 0 de arranque se volveria "Entero" y ahi los 1.234,56 se
    muestran como 1.235. Ver test_un_importe_no_se_redondea_sin_declarar_tipo.
    """
    from libs.Grillas import Grilla

    g = Grilla(tamanio=10)
    g.ArmaCabeceras(cabeceras=["Idcliente", "Nombre"],
                    formatos=["Entero", "String"])
    g.AgregaItem([1, "CONSUMIDOR FINAL"])
    app.processEvents()
    assert g.item(0, 0).text() == "1", (
        "el codigo se muestra como {!r}".format(g.item(0, 0).text()))
    # Y el valor que se lee sigue siendo el numero, no el texto.
    assert g.ObtenerItem(fila=0, col=0) == 1
    g.close()


def test_un_importe_no_se_redondea_sin_declarar_tipo(app):
    """Sin tipo declarado se asume Decimal, que es lo que corresponde a un
    importe: 1500 se ve 1.500,00 y no 1.500."""
    from libs.Grillas import Grilla

    g = Grilla(tamanio=10)
    g.ArmaCabeceras(cabeceras=["Detalle", "Unitario"])
    g.AgregaItem(["Tornillo", 1500])
    app.processEvents()
    assert g.item(0, 1).text() == "1.500,00", (
        "un importe se esta mostrando como {!r}".format(g.item(0, 1).text()))
    g.close()


def test_la_primera_fila_no_poisona_el_resto_de_la_columna(app):
    """La fila de "Saldo Inicial" de la ficha del cliente arranca con 0.

    Si ese 0 definiera el tipo de la columna, los importes de las filas que
    siguen se verian redondeados: por eso el tipo se declara, y por eso el
    valor de la primera fila no toca el formato.
    """
    from libs.Grillas import Grilla

    g = Grilla(tamanio=10)
    g.ArmaCabeceras(cabeceras=["Detalle", "Debe"])
    g.AgregaItem(["Saldo Inicial", 0])          # el 0 de arranque, entero
    g.AgregaItem(["Factura 1", 1234.56])
    app.processEvents()

    assert g.item(0, 1).text() == "0,00", (
        "el cero de arranque quedo como {!r}".format(g.item(0, 1).text()))
    assert g.item(1, 1).text() == "1.234,56", (
        "el importe quedo como {!r}".format(g.item(1, 1).text()))
    g.close()


# -- Buscador de la barra lateral -----------------------------------------

@pytest.fixture
def shell(app):
    from vistas.Main import MainView
    v = MainView()
    v.initUi()
    v.show()
    app.processEvents()
    return v


def _acciones_de_la_seccion(nombre):
    """Cuantas acciones tiene una seccion, contadas desde la definicion."""
    from vistas.Main import SECCIONES
    for titulo, _clave, items in SECCIONES:
        if titulo == nombre:
            return len(items)
    raise AssertionError("no existe la seccion {}".format(nombre))


def _total_de_acciones():
    from vistas.Main import SECCIONES
    return sum(len(items) for _, _, items in SECCIONES)


def _visibles(vista):
    return [b.text() for b in vista.botonesNav.values() if b.isVisible()]


def test_el_buscador_empieza_mostrando_todo(shell):
    """Todas las acciones de la barra lateral, sin que ninguna quede afuera.

    El numero sale de SECCIONES y no de un numero fijo: si uno agrega una
    pantalla y no actualiza el test, este lo dice, y al revés, si se saca una
    pantalla sin querer, tambien.
    """
    from vistas.Main import SECCIONES

    esperadas = sum(len(items) for _, _, items in SECCIONES)
    assert len(_visibles(shell)) == len(shell.botonesNav) == esperadas


def test_toda_accion_de_la_barra_lateral_tiene_pantalla(shell):
    """Una accion sin destino abre un error en vez de no hacer nada.

    Se agrega un boton a la barra lateral y se lo conecta a algo, pero si el
    destino no existe el clic no hace nada y no se ve ningun error: la accion
    queda muerta en pantalla.
    """
    from controladores.Main import Main
    from vistas.Main import SECCIONES

    # DESTINOS es un metodo: devuelve el mapa clave -> como abrir la pantalla.
    destinos = set(Main().DESTINOS())
    for _, _, items in SECCIONES:
        for clave, etiqueta, _icono in items:
            assert clave in destinos, \
                "la acción '{}' ({}) no tiene destino en DESTINOS".format(
                    etiqueta, clave)


@pytest.mark.parametrize("consulta,esperado", [
    ("proveedor", 1),
    ("rinde", 1),
    ("iva", 2),
    ("compra", 5),           # las cinco de la seccion Compras
])
def test_el_buscador_filtra_por_texto(shell, consulta, esperado):
    shell.buscar(consulta)
    assert len(_visibles(shell)) == esperado


def test_el_buscador_ignora_tildes_y_mayusculas(shell):
    """Escribir 'CONFIGURACION' tiene que encontrar 'Configuración'."""
    shell.buscar("CONFIGURACION")
    con_mayusculas = _visibles(shell)
    shell.buscar("configuración")
    con_tilde = _visibles(shell)
    shell.buscar("configuracion")
    sin_tilde = _visibles(shell)

    assert con_mayusculas == con_tilde == sin_tilde
    assert len(sin_tilde) == _acciones_de_la_seccion("Configuraci\u00f3n")


def test_el_buscador_also_busca_por_nombre_de_seccion(shell):
    shell.buscar("monotributo")
    assert _visibles(shell) == ["Categorías", "Informe de recategorización"]


def test_el_buscador_avisa_cuando_no_encuentra_nada(shell):
    shell.buscar("xyzxyzxyz")
    assert _visibles(shell) == []
    assert shell.lblSinResultados.isVisible()


def test_borrar_la_busqueda_deja_todo_visible(shell):
    shell.buscar("proveedor")
    shell.buscar("")
    assert len(_visibles(shell)) == _total_de_acciones()
    assert not shell.lblSinResultados.isVisible()


def test_una_seccion_se_esconde_solo_si_no_queda_nada(shell):
    """Con 'compra' tienen que verse los cinco botones de Compras y su titulo,
    y las demas secciones tienen que desaparecer."""
    shell.buscar("compra")
    assert len(_visibles(shell)) == 5
    assert shell._seccion_de["proveedores"].isVisible()
    assert not shell._seccion_de["nueva-venta"].isVisible()


# -- El encabezado se alinea solo ------------------------------------------

def test_el_encabezado_se_alinea_solo_sin_declarar_tipos(app):
    """La mayoria de las pantallas arman el encabezado sin declarar tipos.

    Con la primera fila se descubre que hay en cada columna, y a partir de ahi
    el encabezado se alinea solo. Asi ninguna tabla queda con los titulos a la
    izquierda y los numeros a la derecha, sin tocar las 30 pantallas una por
    una.
    """
    from PyQt5.QtCore import Qt
    from libs.Grillas import Grilla

    g = Grilla(tamanio=10)
    # Sin formatos: es como la llaman casi todas las pantallas.
    g.ArmaCabeceras(cabeceras=["Descripcion", "Importe"])
    g.show()
    app.processEvents()

    g.AgregaItem(["Tornillo", 1250.5])
    app.processEvents()

    assert g.horizontalHeaderItem(1).textAlignment() & Qt.AlignRight
    assert not g.horizontalHeaderItem(0).textAlignment() & Qt.AlignRight
    g.close()

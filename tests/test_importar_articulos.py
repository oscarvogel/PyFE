# coding=utf-8
"""Tests de la importacion de articulos desde Excel.

Que se prueba y que no
----------------------
Se prueba la logica de `libs/importararticulos.py`: leer el Excel, calcular el
precio, resolver el grupo y decidir que se actualiza y que se crea. Todo con
base en memoria y sin Qt, asi que estos tests corren en cualquier maquina y
sin MySQL.

La pantalla no se prueba aca. Un test que verifica que el boton existe no
dice nada sobre si el precio quedo bien, y el precio es lo unico que importa.

Por que el `base` es un fixture
------------------------------
Porque `base_memoria()` es un contextmanager: si se usara con un `with` en cada
test, las consultas Habrian que hacer DENTRO del bloque, y cualquiera que se
quede afuera despues del `with` estara consultando la base real de
desarrollo. Este fixture mantiene la base en memoria viva durante todo el test,
que es lo que evita ese error (ver tests/test_stock_ui.py, que ya lo usa asi).
"""

import os
import sys
from decimal import Decimal

import pytest

# No hay conftest.py en este repo: cada test arma su propio sys.path (ver
# tests/test_semilla_stock.py). El directorio de tests va tambien porque
# `ayuda_stock` se importa como modulo suelto, no como `tests.ayuda_stock`.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _ruta in (RAIZ, os.path.dirname(os.path.abspath(__file__))):
    if _ruta not in sys.path:
        sys.path.insert(0, _ruta)

from libs import importararticulos
from modelos.Articulos import Articulo
from modelos.Grupos import Grupo

ARCHIVO_REAL = r"C:\Users\Usuario\Downloads\Importacion compuesta.xlsx"

# La planilla que motivo el trabajo. Se arma aca y no se usa la de Downloads
# para que el test no dependa de un archivo de otra carpeta: estos tests tienen
# que seguir dando lo mismo en la maquina de cualquiera.
CABECERA = ["CODIGO DE BARRA", "NOMBRE1", "Nombre2", "Nombre3", "Nombre4",
            "GRUPO", "PROVEEDOR", "COSTO", "GANANCIA", "IVA"]


@pytest.fixture
def base():
    """Base en memoria con el catalogo minimo. Ver tests/ayuda_stock.py.

    Necesaria de verdad: estos tests escriben articulos, y sin ella una
    importacion de prueba queda metida en la base de desarrollo.
    """
    from ayuda_stock import base_memoria

    with base_memoria() as memoria:
        yield memoria


def arma_xlsx(tmp_path, filas, cabeceras=None, nombre="lista.xlsx"):
    """Una planilla de prueba, con las filas tal cual se las pasa."""
    from openpyxl import Workbook

    libro = Workbook()
    hoja = libro.active
    hoja.append(cabeceras or CABECERA)
    for fila in filas:
        hoja.append(fila)
    archivo = str(tmp_path / nombre)
    libro.save(archivo)
    return archivo


def crudo(nombre):
    """El renglon del articulo con los valores CRUDOS, o None.

    Hace falta porque leer un modelo con peewee devuelve el OBJETO
    relacionado en las claves foraneas: `articulo.tipoiva` es un
    `<Tipoiva: 02>`, no un "02". Comparar eso contra un texto en un test
    falla por la razon equivocada y hace creer que el IVA esta mal cuando lo
    que esta mal es la asercion.

    `.dicts()` devuelve los escalares: el mismo camino que usa
    `_mismo_que_ya_esta` para decidir si algo cambio de verdad.
    """
    return Articulo.select().where(Articulo.nombre == nombre).dicts().get()


# -- Lectura -----------------------------------------------------------------

def test_lee_los_datos_de_la_planilla(tmp_path):
    archivo = arma_xlsx(tmp_path, [[
        "7791234567890", "WHEY PROTEIN", None, None, None,
        "SUPLEMENTOS", "NORDESTE", 10142, 1.4, 0]])

    registros = importararticulos.leer_filas(archivo)

    assert len(registros) == 1
    registro = registros[0]
    assert registro["nombre"] == "WHEY PROTEIN"
    assert registro["costo"] == Decimal("10142")
    assert registro["ganancia"] == Decimal("1.4")
    assert registro["grupo"] == "SUPLEMENTOS"
    assert registro["codbarra"] == "7791234567890"
    # La 1 son los titulos, asi que el primer dato es la fila 2 de Excel.
    assert registro["numero"] == 2


def test_une_las_cuatro_partes_del_nombre(tmp_path):
    """El nombre viene partido en columnas y hay que pegarlo.

    Este es el motivo de que existan NOMBRE1..NOMBRE4: si solo se leyera
    NOMBRE1, el articulo se llamaria "WHEY CUTTER 1080G PROTE+QUEMADOR SPX"
    y se venderia sin la presentacion.
    """
    archivo = arma_xlsx(tmp_path, [[
        None, "WHEY CUTTER", "PROTE+QUEMADOR", "SPX", "VAINILLA",
        "SUPLEMENTOS", "NORDESTE", 10142, 1.4, 0]])

    registros = importararticulos.leer_filas(archivo)

    assert registros[0]["nombre"] == "WHEY CUTTER PROTE+QUEMADOR SPX VAINILLA"


def test_ignora_las_filas_vacias(tmp_path):
    """El Excel arrastra filas en blanco y no son articulos.

    Sin esto el resumen contaria articulos que nadie escribio, y el operador
    pensaria que se perdio informacion.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "PRODUCTO UNO", None, None, None, "SUP", "N", 100, 1.2, 0],
        [None, None, None, None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None, None, None],
        [None, "PRODUCTO DOS", None, None, None, "SUP", "N", 200, 1.3, 0],
    ])

    assert len(importararticulos.leer_filas(archivo)) == 2


def test_avisa_si_falta_la_columna_de_nombres(tmp_path):
    archivo = arma_xlsx(tmp_path, [[10142, "NORDESTE"]],
                        cabeceras=["COSTO", "PROVEEDOR"])

    with pytest.raises(importararticulos.ErrorImportacion) as error:
        importararticulos.leer_filas(archivo)

    assert "NOMBRE1" in str(error.value)


# -- El separador de miles ----------------------------------------------------

def test_costo_con_punto_de_miles_no_es_una_decima():
    """'10.142' son diez mil ciento cuarenta y dos, no diez con mil.

    Este es el test mas importante del modulo. Sin esto el costo entra mil
    veces mas chico y el precio sale con tres ceros de mas, y el error no se ve
    hasta que la factura no cierra.
    """
    assert importararticulos._numero("10.142", "COSTO") == Decimal("10142")
    assert importararticulos._numero("1.234,56", "COSTO") == Decimal("1234.56")
    assert importararticulos._numero("1234,56", "COSTO") == Decimal("1234.56")


def test_la_ganancia_si_toma_el_punto_como_decimal():
    """'1.4' en GANANCIA es 1.4, y '1,4' tambien.

    Al reves que en COSTO, y a proposito: '1.400' como costo son mil
    cuatrocientos, pero como ganancia son mil cuatrocientos, que no existe en
    una lista de precios. La regla del punto de miles va solo en COSTO.
    """
    assert importararticulos._numero("1.4", "GANANCIA") == Decimal("1.4")
    assert importararticulos._numero("1,4", "GANANCIA") == Decimal("1.4")
    assert importararticulos._numero("1.400", "GANANCIA") == Decimal("1.400")


def test_una_ganancia_ilegible_no_tira_la_carga(tmp_path, base):
    """Una fila con "veinte" en COSTO se avisa, las otras se importan."""
    archivo = arma_xlsx(tmp_path, [
        [None, "BUENO", None, None, None, "SUP", "N", 100, 1.2, 0],
        [None, "MALO", None, None, None, "SUP", "N", "veinte", 1.2, 0],
    ])

    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert resultado.creados == ["BUENO"]
    assert len(resultado.filas_con_error) == 1
    # El numero de fila es el del Excel: el operador abre el archivo y va.
    assert resultado.filas_con_error[0][0] == 3


# -- El precio ----------------------------------------------------------------

def test_el_precio_es_el_costo_por_la_ganancia():
    """10142 x 1.4 = 14198.80. El caso que motivo todo esto."""
    assert importararticulos.calcula_precio(
        Decimal("10142"), Decimal("1.4")) == Decimal("14198.8000")


def test_el_precio_respeta_cuatro_decimales():
    """`preciopub` es DECIMAL(12,4) y MySQL cortaria lo que sobra."""
    precio = importararticulos.calcula_precio(Decimal("100"),
                                              Decimal("1.33333"))
    # 100 x 1.33333 = 133.333 exacto; a cuatro decimales queda 133.3330.
    assert precio == Decimal("133.3330")
    assert str(precio).split(".")[1] == "3330"


def test_un_costo_negativo_no_se_importa(tmp_path, base):
    archivo = arma_xlsx(tmp_path, [
        [None, "NEGATIVO", None, None, None, "SUP", "N", -50, 1.2, 0]])

    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert resultado.creados == []
    assert "negativo" in resultado.filas_con_error[0][1]


# -- Los grupos ---------------------------------------------------------------

def test_crea_el_grupo_que_no_existe(tmp_path, base):
    """SUPLEMENTOS no esta en la base y se crea solo.

    Es la decision que se tomo: preguntar por cada grupo de una lista de
    cientos de filas es hacerselo a mano al operador.
    """
    assert Grupo.get_or_none(Grupo.nombre == "SUPLEMENTOS") is None

    archivo = arma_xlsx(tmp_path, [
        [None, "WHEY", None, None, None, "SUPLEMENTOS", "NORDESTE", 10142, 1.4, 0]])
    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    grupo = Grupo.get_or_none(Grupo.nombre == "SUPLEMENTOS")
    assert grupo is not None, "el grupo no se creo"
    assert resultado.grupos_creados == ["SUPLEMENTOS"]
    assert Articulo.select().where(
        Articulo.grupo == grupo.idgrupo).count() == 1


def test_no_parte_el_grupo_por_las_mayusculas(tmp_path, base):
    """"Suplementos" y "SUPLEMENTOS" son el mismo grupo.

    Si se crearan dos, el catalogo queda partido y los reportes por grupo
    muestran dos renglones que son el mismo.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "UNO", None, None, None, "Suplementos", "N", 100, 1.2, 0],
        [None, "DOS", None, None, None, "SUPLEMENTOS", "N", 200, 1.2, 0],
    ])

    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    # Se crea UNA vez, con la grafia de la primera fila que la menciona: es
    # el nombre que eligio el proveedor y cambiarlo seria inventar.
    assert resultado.grupos_creados == ["Suplementos"]

    # La base sembrada ya trae un grupo (VARIOS), asi que el conteo absoluto no
    # dice nada: lo que no puede haber es DOS grupos con el mismo nombre.
    con_ese_nombre = [g.nombre for g in Grupo.select()
                      if g.nombre.upper() == "SUPLEMENTOS"]
    assert con_ese_nombre == ["Suplementos"], \
        "se creo un grupo repetido: {}".format(con_ese_nombre)


def test_reusa_el_grupo_que_ya_existe(tmp_path, base):
    """El grupo VARIOS ya esta en la base sembrada y no se duplica."""
    archivo = arma_xlsx(tmp_path, [
        [None, "UNO", None, None, None, "VARIOS", "N", 100, 1.2, 0]])

    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert resultado.grupos_creados == []
    assert Grupo.select().count() == 1


# -- Alta y actualizacion -----------------------------------------------------

def test_importa_los_precios_bien(tmp_path, base):
    """El archivo real, de punta a punta: costo, ganancia y precio."""
    archivo = arma_xlsx(tmp_path, [
        [None, "WHEY", None, None, None, "SUPLEMENTOS", "NORDESTE", 10142, 1.4, 0],
        [None, "VITAMINA D", None, None, None, "SUPLEMENTOS", "NORDESTE", 6010, 1.5, 0],
    ])

    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert len(resultado.creados) == 2
    assert resultado.filas_con_error == []

    whey = crudo("WHEY")
    assert whey["costo"] == Decimal("10142")
    assert whey["preciopub"] == Decimal("14198.8000")
    assert whey["provppal"] == 1
    assert whey["tipoiva"] == "01"

    assert crudo("VITAMINA D")["preciopub"] == Decimal("9015")


def test_el_nombre_del_ticket_se_recorta(tmp_path, base):
    """`nombre` es CHAR(100) y `nombreticket` CHAR(30): los nombres de esta
    lista pasan de los cien caracteres y MySQL cortaria en silencio, dejando
    dos productos con el nombre igual."""
    largo = "PRODUCTO " + ("X" * 150)
    archivo = arma_xlsx(tmp_path, [
        [None, largo, None, None, None, "VARIOS", "N", 100, 1.2, 0]])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    fila = Articulo.select().where(
        Articulo.nombre.startswith("PRODUCTO")).dicts().get()
    assert len(fila["nombre"]) == 100
    assert len(fila["nombreticket"]) == 30


def test_actualiza_el_articulo_que_ya_existe(tmp_path, base):
    """Una lista recargada actualiza costo y precio, no duplica.

    Es la segunda de las cuatro decisiones: si el articulo ya existe se le
    cambian costo, precio y proveedor. Una lista de precios se recarga, no se
    duplica.
    """
    # GASOLINA esta sembrada con costo 80 y precio 100.
    antes = Articulo.get(Articulo.nombre == "GASOLINA")
    antes.codbarra = "779111"
    antes.save()
    # La siembra de test ya dejo dos articulos: se compara contra esa cuenta.
    articulos_previos = Articulo.select().count()

    archivo = arma_xlsx(tmp_path, [
        ["779111", "GASOLINA", None, None, None, "VARIOS", "N", 20000, 1.5, 0]])
    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert Articulo.select().count() == articulos_previos, \
        "no debe crear un duplicado"
    assert resultado.actualizados == ["GASOLINA"]
    actualizado = (Articulo.select()
                     .where(Articulo.idarticulo == antes.idarticulo)
                     .dicts().get())
    assert actualizado["costo"] == Decimal("20000")
    assert actualizado["preciopub"] == Decimal("30000")


def test_una_recarga_sin_cambios_no_dice_que_actualizo(tmp_path, base):
    """Importar dos veces lo mismo no puede reportar "400 actualizados".

    El resumen que miente deja de ser util: el operador deja de mirarlo y no
    se da cuenta cuando SI cambio algo.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "WHEY", None, None, None, "SUPLEMENTOS", "N", 100, 1.2, 0]])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")
    articulos_previos = Articulo.select().count()

    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert resultado.actualizados == []
    assert resultado.sin_cambios == ["WHEY"]
    assert Articulo.select().count() == articulos_previos


def test_busca_por_nombre_normalizado_sin_codigo(tmp_path, base):
    """Sin codigo de barras, el nombre normalizado es la clave.

    Se importa "whey protein" y despues "WHEY   PROTEIN": son el mismo
    producto escrito de otra forma y no pueden quedar como dos.
    """
    primero = arma_xlsx(tmp_path, [
        [None, "whey protein", None, None, None, "VARIOS", "N", 500, 2, 0]],
        nombre="a.xlsx")
    segundo = arma_xlsx(tmp_path, [
        [None, "WHEY   PROTEIN", None, None, None, "VARIOS", "N", 500, 2, 0]],
        nombre="b.xlsx")

    r1 = importararticulos.importa(primero, proveedor_id=1, tipoiva="01")
    r2 = importararticulos.importa(segundo, proveedor_id=1, tipoiva="01")

    assert r1.creados == ["whey protein"]
    # El nombre guardado va con los espacios colapsados: es lo que hace
    # _nombre_de_fila y es lo que evita dos productos que son el mismo.
    assert r2.actualizados == ["WHEY PROTEIN"]
    # Dos de la siembra de test mas el unico producto importado.
    assert Articulo.select().count() == 3, "no debe crear un duplicado"
    assert crudo("WHEY PROTEIN")["preciopub"] == Decimal("1000")


def test_el_codigo_generado_no_se_repite(tmp_path, base):
    """Dos renglones sin codigo reciben codigos distintos."""
    archivo = arma_xlsx(tmp_path, [
        [None, "IGUAL UNO", None, None, None, "VARIOS", "N", 100, 1.2, 0],
        [None, "IGUAL UNO", None, None, None, "VARIOS", "N", 200, 1.2, 0],
    ])

    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    codigos = [a.codbarra for a in Articulo.select(Articulo.codbarra)
               if a.codbarra.startswith(importararticulos.PREFIJO_CODBARRA_INTERNO)]
    assert len(codigos) == 2
    assert len(set(codigos)) == 2, "codigos repetidos: {}".format(codigos)


def test_el_proveedor_es_el_que_se_eligio(tmp_path, base):
    """La columna PROVEEDOR del archivo no manda: el id elegido en pantalla si.

    El archivo trae "NORDESTE" en texto libre y la base lo tiene como id. Si
    se usara el texto, habria que crear un proveedor por cada lista y el
    catalogo de proveedores se llenaria de copias.
    """
    from modelos.Proveedores import Proveedor

    Proveedor.create(idproveedor=2, nombre="NORDESTE", tiporesp=1,
                     idlocalidad=1)

    archivo = arma_xlsx(tmp_path, [
        [None, "WHEY", None, None, None, "VARIOS", "NORDESTE", 100, 1.2, 0]])
    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert resultado.creados == ["WHEY"]
    # Se eligio el 1 (el que estaba sembrado), no el 2 que se creo con el
    # nombre del archivo.
    assert crudo("WHEY")["provppal"] == 1


def test_sin_proveedor_no_importa_nada(tmp_path, base):
    """Sin proveedor no se importa: mejor que un "SIN PROVEEDOR" falso."""
    archivo = arma_xlsx(tmp_path, [
        [None, "WHEY", None, None, None, "VARIOS", "N", 100, 1.2, 0]])

    with pytest.raises(importararticulos.ErrorImportacion):
        importararticulos.importa(archivo, proveedor_id=None, tipoiva="01")


# -- La ganancia por defecto --------------------------------------------------

def test_usa_la_ganancia_de_la_planilla_cuando_trae(tmp_path, base):
    """1.4 y 1.5 mezclados: cada renglon usa la suya.

    El archivo trae la ganancia renglon por renglon y esa manda. La ganancia
    por defecto de la pantalla es solo para los que no traen, asi que un 9 de
    respaldo no puede pisar el 1.4 del renglon.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "UNO", None, None, None, "VARIOS", "N", 100, 1.4, 0],
        [None, "DOS", None, None, None, "VARIOS", "N", 100, 1.5, 0],
    ])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01",
                              ganancia_defecto=Decimal("9"))

    assert crudo("UNO")["preciopub"] == Decimal("140")
    assert crudo("DOS")["preciopub"] == Decimal("150")


def test_la_ganancia_por_defecto_cubre_los_renglones_sin_ganancia(tmp_path, base):
    """Un renglon sin GANANCIA usa la que eligio el operador."""
    archivo = arma_xlsx(tmp_path, [
        [None, "SIN GANANCIA", None, None, None, "VARIOS", "N", 100, None, 0],
    ])

    resultado = importararticulos.importa(
        archivo, proveedor_id=1, tipoiva="01", ganancia_defecto=Decimal("2"))

    assert resultado.creados == ["SIN GANANCIA"]
    assert crudo("SIN GANANCIA")["preciopub"] == Decimal("200")


def test_un_renglon_sin_ganancia_sin_defecto_no_entra(tmp_path, base):
    """Sin ganancia propia y sin defecto, esa fila se avisa y las otras van."""
    archivo = arma_xlsx(tmp_path, [
        [None, "OK", None, None, None, "VARIOS", "N", 100, 1.2, 0],
        [None, "SIN GANANCIA", None, None, None, "VARIOS", "N", 100, None, 0],
    ])

    resultado = importararticulos.importa(
        archivo, proveedor_id=1, tipoiva="01", ganancia_defecto=None)

    assert resultado.creados == ["OK"]
    assert len(resultado.filas_con_error) == 1


# -- El IVA del archivo -------------------------------------------------------

def test_el_iva_lo_manda_la_pantalla_no_la_columna_del_archivo(tmp_path, base):
    """La columna IVA con 0 no es "exento": es "no lo se".

    El archivo trae 0 en todas las filas. Si eso se tomara como alicuota cero,
    el catalogo entero quedaria con el impuesto equivocado y nadie se
    enteraria hasta ver la factura.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "WHEY", None, None, None, "VARIOS", "N", 100, 1.2, 0]])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="02")

    assert crudo("WHEY")["tipoiva"] == "02"


# -- Stock --------------------------------------------------------------------

def test_el_control_de_stock_se_pide_una_sola_vez(tmp_path, base):
    """Es una propiedad de toda la carga, no de cada renglon."""
    archivo = arma_xlsx(tmp_path, [
        [None, "UNO", None, None, None, "VARIOS", "N", 100, 1.2, 0],
        [None, "DOS", None, None, None, "VARIOS", "N", 200, 1.2, 0],
    ])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01",
                              controlastock=False, stockminimo=7)

    importados = [a for a in Articulo.select() if a.nombre in ("UNO", "DOS")]
    assert len(importados) == 2
    for articulo in importados:
        assert not importararticulos._a_bit(articulo.controlastock)


# -- El archivo de verdad -----------------------------------------------------

@pytest.mark.skipif(not os.path.exists(ARCHIVO_REAL),
                    reason="la planilla original no esta en esta maquina")
def test_la_planilla_original_se_importa_como_corresponde(base):
    """La planilla que motivo el trabajo, leida de verdad.

    Este test no sirve si se arma una planilla a mano: el problema nacio de
    ESTE archivo y sus particularidades (nombres partidos, ganancia con punto,
    IVA en cero) tienen que estar probados contra el.
    """
    resultado = importararticulos.importa(ARCHIVO_REAL, proveedor_id=1,
                                          tipoiva="01")

    # Todas las filas del archivo entran: ninguna queda afuera.
    assert resultado.filas_con_error == []
    assert resultado.total_importados == resultado.total_leidas
    assert resultado.total_importados > 0

    # El precio sale del costo por la ganancia, y ninguno queda en cero.
    for fila in Articulo.select().dicts():
        assert fila["preciopub"] > 0, "{} quedo en precio {}".format(
            fila["nombre"], fila["preciopub"])

    # Los nombres de la planilla son largos: ninguno se corto a 100.
    for fila in Articulo.select().dicts():
        assert len(fila["nombre"]) <= 100
        assert len(fila["nombreticket"]) <= 30


@pytest.mark.skipif(not os.path.exists(ARCHIVO_REAL),
                    reason="la planilla original no esta en esta maquina")
def test_la_planilla_original_es_idempotente(base):
    """Importarla dos veces no crea ni actualiza nada.

    Es la garantia de que el operador puede recargar una lista corregida sin
    miedo: si la segunda pasada moviera algo, no podria volver atras.
    """
    importararticulos.importa(ARCHIVO_REAL, proveedor_id=1, tipoiva="01")
    # El numero de articulos ya incluye los dos de la siembra de test: lo que
    # importa es que la segunda pasada NO lo haga crecer.
    articulos_tras_primera = Articulo.select().count()

    segunda = importararticulos.importa(ARCHIVO_REAL, proveedor_id=1,
                                        tipoiva="01")

    assert segunda.creados == []
    assert segunda.actualizados == []
    assert len(segunda.sin_cambios) == segunda.total_leidas
    assert Articulo.select().count() == articulos_tras_primera

# -- La pantalla --------------------------------------------------------------

@pytest.fixture
def qapp():
    """Una QApplication. Va una sola vez por proceso, como en el resto."""
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def vista(base, qapp):
    """La pantalla real, con un proveedor de verdad para elegir.

    No un stub. Los controles son los que el operador va a tocar: si el combo
    de IVA por defecto cae en el 10.5% o si el boton arranca habilitado sin
    planilla, eso se ve aca y no en produccion.
    """
    from modelos.Proveedores import Proveedor
    from vistas.ImportarArticulos import ImportarArticulosView

    Proveedor.create(idproveedor=2, nombre="NORDESTE", tiporesp=1,
                     idlocalidad=1)
    pantalla = ImportarArticulosView()
    pantalla.ConectarWidgets()
    return pantalla


def test_la_pantalla_se_abre_con_los_catalogos_cargados(vista):
    assert vista.windowTitle()
    assert vista.cboProveedor.count() == 2, "no listo los proveedores"
    assert vista.cboTipoIva.count() == 2
    assert vista.cboUnidad.text() == "UN"
    # Sin planilla elegida no se importa nada.
    assert vista.btnImportar.isEnabled() is False


def test_el_iva_por_defecto_es_el_general_no_el_10_5(vista):
    """El 10.5% ordenado por descripcion queda primero y es el que NO va.

    Si el importador por defecto fuera el 10.5, TODO articulo nuevo entraria
    con el impuesto bajo, el error estaria en el catalogo entero y pareceria
    correcto. Por eso se fuerza el 01.
    """
    assert vista.cboTipoIva.itemText(0) == "10.5", \
        "el test dejaria de probar nada si el orden cambia"
    assert vista.cboTipoIva.text() == "01"
    assert vista.cboTipoIva.currentText() == "IVA GENERAL"


def test_la_pantalla_avisa_cuantas_filas_tiene_el_archivo(vista, tmp_path):
    archivo = arma_xlsx(tmp_path, [
        [None, "UNO", None, None, None, "SUP", "N", 100, 1.2, 0],
        [None, "DOS", None, None, None, "SUP", "N", 200, 1.3, 0],
    ])

    vista.txtArchivo.setText(archivo)

    assert "2 filas" in vista.lblResumen.text()
    assert vista.btnImportar.isEnabled() is True


def test_la_pantalla_no_importa_si_falta_la_planilla(vista, monkeypatch):
    """Sin archivo no se importa nada, ni a medias.

    Se comprueba sobre los articulos, no sobre un banderín: lo que importa es
    que la base no se toque.
    """
    import libs.Ventanas as Ventanas

    avisado = []
    monkeypatch.setattr(Ventanas, "showAlert",
                        lambda t, m: avisado.append(m))
    antes = Articulo.select().count()

    vista.txtArchivo.setText("")
    vista.importar()

    assert avisado, "tenia que avisar que falta la planilla"
    assert Articulo.select().count() == antes, "escribio sin planilla"


def test_importar_desde_la_pantalla_crea_los_articulos(vista, tmp_path,
                                                       monkeypatch):
    """El camino completo: elegir planilla, confirmar y que se escriba.

    Se parchean los dos dialogos porque son modales y en un test no hay nadie
    para apretarlos. El resto --leer el archivo, calcular el precio, resolver
    el proveedor, el IVA y el grupo y escribir-- es el de verdad.
    """
    import libs.Ventanas as Ventanas
    from modelos.Grupos import Grupo

    archivo = arma_xlsx(tmp_path, [
        [None, "WHEY", None, None, None, "SUPLEMENTOS", "NORDESTE", 10142, 1.4, 0],
        [None, "VITAMINA D", None, None, None, "SUPLEMENTOS", "NORDESTE", 6010, 1.5, 0],
    ])

    confirmados = []
    monkeypatch.setattr(Ventanas, "showConfirmation",
                        lambda *a, **k: confirmados.append(a) or True)
    mostrados = []
    monkeypatch.setattr(Ventanas, "showAlert",
                        lambda t, m: mostrados.append(m))

    vista.cboProveedor.setCurrentIndex(
        vista.cboProveedor.findText("NORDESTE"))
    vista.spnGanancia.setValue(1.5)
    vista.txtArchivo.setText(archivo)

    vista.importar()

    # Se pidio confirmacion antes de escribir.
    assert confirmados, "importo sin preguntar"
    assert Articulo.select().count() == 4, "no se crearon los dos articulos"

    fila = crudo("WHEY")
    # 10142 x 1.4 = 14198.80, y el IVA es el general que eligio la pantalla.
    assert fila["preciopub"] == Decimal("14198.8000")
    assert fila["tipoiva"] == "01"
    assert fila["provppal"] == 2, "no tomo el proveedor elegido"
    # El grupo vino del archivo y se creo solo.
    assert Grupo.get_or_none(Grupo.nombre == "SUPLEMENTOS") is not None
    # Y el resumen lo dice.
    assert any("2 articulos" in m for m in mostrados), mostrados

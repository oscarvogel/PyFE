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


def test_el_precio_sigue_al_margen_que_se_guarda():
    """El precio sale del margen redondeado, no del multiplicador entero.

    `incre1` es DECIMAL(12,2): un multiplicador de 1.33333 es un margen de
    33.333 que no entra, se guarda 33.33, y el precio se calcula DESPUES con
    ese 33.33. Si se calculara antes, el artículo quedaría con un precio que no
    sale de la cuenta que tiene escrita al lado, y al reimportarlo se movería
    un centavo sin que nadie lo haya tocado.

    Con un multiplicador de dos decimales, que es el caso de las listas de
    precios reales, el precio es exactamente el de siempre.
    """
    precio = importararticulos.calcula_precio(Decimal("100"),
                                              Decimal("1.33333"))
    assert precio == Decimal("133.3300"), precio

    # El caso normal: 1.5 entra entero y no hay nada que redondear.
    assert importararticulos.calcula_precio(
        Decimal("10142"), Decimal("1.5")) == Decimal("15213.0000")


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
    """Dos filas con el MISMO nombre y sin codigo son UN articulo.

    CAMBIO (2026-10-08). Antes este test pedia dos codigos distintos para dos
    filas con nombre identico, y con razon aparente: "si son el mismo nombre,
    que no queden con el mismo codigo". Pero sin codigo de barras el nombre
    es la unica clave, asi que dos filas con el mismo nombre son el MISMO
    producto con dos costos: la segunda actualiza a la primera. Pedir dos
    articulos seria crear un duplicado del mismo producto, que es peor.

    Lo que importa y se sigue verificando es que el codigo generado no se
    repita con el de OTRO producto distinto, y que la fila repetida no se
    quede con un codigo interno que se come un sufijo al pedo.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "IGUAL UNO", None, None, None, "VARIOS", "N", 100, 1.2, 0],
        [None, "IGUAL UNO", None, None, None, "VARIOS", "N", 200, 1.2, 0],
    ])

    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    codigos = [a.codbarra for a in Articulo.select(Articulo.codbarra)
               if a.codbarra.startswith(importararticulos.PREFIJO_CODBARRA_INTERNO)]
    # Un solo articulo, con un solo codigo, sin sufijo: la segunda fila
    # actualiza a la primera en vez de crear un "-2" que no le corresponde.
    assert len(codigos) == 1, "codigos internos de mas: {}".format(codigos)
    assert codigos == ["INTIGUALUNO"], \
        "se genero un codigo con sufijo para una fila que actualiza: {}".format(codigos)
    assert resultado.actualizados == ["IGUAL UNO"], \
        "la segunda fila deberia actualizar al primero, no crear otro"
    assert resultado.nombres_repetidos == ["IGUAL UNO"], \
        "no aviso que el nombre estaba repetido en el archivo"


def test_dos_productos_distintos_no_comparten_codigo(tmp_path, base):
    """Nombres que arrancan igual pero NO son iguales: codigos distintos.

    Es el caso que el test anterior cubria sin verlo: dos productos reales
    que el generador de codigos internos no puede distinguir porque trunca el
    nombre a 18 caracteres. Si los dos dieran el mismo codigo, el segundo
    actualizaria al primero y se perderia un producto del catalogo.
    """
    largo_a = "PRODUCTO MUY LARGO NUMERO UNO"
    largo_b = "PRODUCTO MUY LARGO NUMERO DOS"
    archivo = arma_xlsx(tmp_path, [
        [None, largo_a, None, None, None, "VARIOS", "N", 100, 1.2, 0],
        [None, largo_b, None, None, None, "VARIOS", "N", 200, 1.2, 0],
    ])

    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    codigos = [a.codbarra for a in Articulo.select(Articulo.codbarra)
               if a.codbarra.startswith(importararticulos.PREFIJO_CODBARRA_INTERNO)]
    assert len(codigos) == 2, "los dos productos comparten un solo codigo: {}".format(codigos)
    assert len(set(codigos)) == 2, "codigos repetidos: {}".format(codigos)
    assert len(resultado.creados) == 2


def test_el_proveedor_es_el_de_la_fila_si_esta_cargado(tmp_path, base):
    """Si el nombre de la columna PROVEEDOR esta en la base, MANDA ese.

    CAMBIO DE REGLA (2026-10-08). Antes este test se llamaba
    `test_el_proveedor_es_el_que_se_eligio` y afirmaba lo contrario: que la
    columna del archivo NO mandaba y que todos los articulos tomaban el del
    desplegable. Ese era el comportamiento viejo y se dio vuelta.

    Por que se dio vuelta: el operador pidio importar planillas con mas de un
    proveedor segun lo que dice cada fila. Con la regla anterior, una planilla
    compuesta entraba entera con el proveedor del desplegable y el catalogo
    quedaba mal atribuido, sin ningun rastro de cual habia sido el error.

    Lo que NO cambio, y sigue siendo lo importante: no se crea un proveedor
    que no exista. Ver `test_un_proveedor_que_no_esta_cargado_se_avisa` en
    tests/test_importar_proveedores_y_ganancia.py.
    """
    from modelos.Proveedores import Proveedor

    Proveedor.create(idproveedor=2, nombre="NORDESTE", tiporesp=1,
                     idlocalidad=1)

    archivo = arma_xlsx(tmp_path, [
        [None, "WHEY", None, None, None, "VARIOS", "NORDESTE", 100, 1.2, 0]])
    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert resultado.creados == ["WHEY"]
    # El 2, que es el que dice la fila, y no el 1 del desplegable.
    assert crudo("WHEY")["provppal"] == 2


def test_proveedor_no_cargado_usa_el_que_se_eligio(tmp_path, base):
    """El nombre de la fila que NO esta en la base: gana el del desplegable.

    Esta es la parte que el cambio de regla tiene que conservar. Antes, este
    caso se resolvia descartando la columna entera; ahora se resuelve nombre a
    nombre, asi que el caso del nombre desconocido tiene que seguir cayendo
    en el proveedor elegido.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "WHEY", None, None, None, "VARIOS", "PROVEEDOR INEXISTENTE",
         100, 1.2, 0]])
    resultado = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert resultado.creados == ["WHEY"]
    assert crudo("WHEY")["provppal"] == 1
    assert resultado.proveedores_no_encontrados == ["PROVEEDOR INEXISTENTE"]


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
    por defecto de la pantalla es solo para los que no traen, asi que un 90%
    de respaldo no puede pisar el 1.4 del renglon.

    Y el multiplicador queda ESCRITO como porcentaje: 1.4 es 40 y 1.5 es 50.
    Sin eso el ABM le muestra 0% a un artículo cuyo precio esta al 50%.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "UNO", None, None, None, "VARIOS", "N", 100, 1.4, 0],
        [None, "DOS", None, None, None, "VARIOS", "N", 100, 1.5, 0],
    ])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01",
                              ganancia_defecto=Decimal("90"))

    assert crudo("UNO")["preciopub"] == Decimal("140")
    assert crudo("DOS")["preciopub"] == Decimal("150")
    assert crudo("UNO")["incre1"] == Decimal("40.00"), \
        "el 1.4 del archivo no quedo escrito como 40%: {}".format(
            crudo("UNO")["incre1"])
    assert crudo("DOS")["incre1"] == Decimal("50.00"), \
        "el 1.5 del archivo no quedo escrito como 50%: {}".format(
            crudo("DOS")["incre1"])


def test_la_ganancia_por_defecto_cubre_los_renglones_sin_ganancia(tmp_path, base):
    """Un renglon sin GANANCIA usa el porcentaje que eligio el operador.

    El campo de la pantalla es un porcentaje (50 = 50%), no el multiplicador
    1.5 de la planilla: con 100 de costo y 50% el precio es 150, no 5000.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "SIN GANANCIA", None, None, None, "VARIOS", "N", 100, None, 0],
    ])

    resultado = importararticulos.importa(
        archivo, proveedor_id=1, tipoiva="01", ganancia_defecto=Decimal("50"))

    assert resultado.creados == ["SIN GANANCIA"]
    assert crudo("SIN GANANCIA")["preciopub"] == Decimal("150")
    assert crudo("SIN GANANCIA")["incre1"] == Decimal("50.00")


def test_reimportar_una_base_sin_margen_lo_completa(tmp_path, base):
    """El caso del operador: los precios ya estaban, el margen no.

    Es lo que paso con 704 articulos importados antes de que existiera el
    campo: el precio estaba puesto (costo x 1.5) pero `incre1` en 0, y el ABM
    le mostraba "Ganancia % 0,00" a un producto con el precio al 50%. Editar
    704 articulos a mano no es una opcion, pero reimportar la misma planilla
    completa el dato sin mover un solo precio.

    Y al reimportar se detectan como ACTUALIZADOS, no como "sin cambio": si
    el margen no entrara en la comparacion, la columna se llenaria sola una
    vez y jamas se volveria a actualizar al cambiar el margen del archivo.
    """
    archivo = arma_xlsx(tmp_path, [
        [1001, "UNO", None, None, None, "VARIOS", "N", 100, 1.5, 0],
        [1002, "DOS", None, None, None, "VARIOS", "N", 200, 1.5, 0],
    ])
    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    # Estado en el que quedo el catalogo: precio puesto, margen en cero.
    Articulo.update(incre1=0).execute()
    assert crudo("UNO")["incre1"] == 0
    assert crudo("UNO")["preciopub"] == Decimal("150")

    segunda = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert sorted(segunda.actualizados) == ["DOS", "UNO"], segunda.actualizados
    assert crudo("UNO")["incre1"] == Decimal("50.00")
    # Y el precio NO se movio: el margen se completo, no se recalculo otra vez.
    assert crudo("UNO")["preciopub"] == Decimal("150")
    assert crudo("DOS")["preciopub"] == Decimal("300")

    # Y una tercera pasada no vuelve a mover nada.
    tercera = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")
    assert tercera.actualizados == [], tercera.actualizados
    assert sorted(tercera.sin_cambios) == ["DOS", "UNO"], tercera.sin_cambios


def test_el_precio_es_siempre_el_del_margen_guardado(tmp_path, base):
    """Precio y margen no pueden contradecirse.

    Si se calcularan por separado, un margen que se redondea a dos decimales
    dejaria un precio que no sale de la cuenta que el operador tiene escrita al
    lado, y al reimportarlo se moveria un centavo sin que nadie lo haya tocado.
    """
    archivo = arma_xlsx(tmp_path, [
        [1001, "UNO", None, None, None, "VARIOS", "N", 100, 1.5, 0],
    ])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    fila = crudo("UNO")
    esperado = Decimal(fila["costo"]) * (1 + Decimal(fila["incre1"]) / 100)
    assert abs(fila["preciopub"] - esperado) < Decimal("0.01"), \
        "precio {} no sale de costo {} con margen {}".format(
            fila["preciopub"], fila["costo"], fila["incre1"])


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

# 20 de las 704 filas de la planilla real NO traen GANANCIA. Sin margen por
# defecto el importador las rechaza con "no tiene GANANCIA y no se eligio una
# por defecto", y entonces este test, que quiere probar que la planilla REAL
# entra completa, estaria probando una planilla que el operador no tiene.
#
# Se pasa el margen como lo pasa la pantalla (`vistas/ImportarArticulos.py` lo
# lee del spinner y lo manda). El numero no importa para lo que este test
# verifica --que no quede ninguna fila afuera y que ninguna quede en precio
# cero-- pero tiene que ser POSITIVO, porque en cero el precio sale igual al
# costo y el ABM trata el 0 como "no hay regla cargada".
GANANCIA_DEFECTO = Decimal("30")


@pytest.mark.skipif(not os.path.exists(ARCHIVO_REAL),
                    reason="la planilla original no esta en esta maquina")
def test_la_planilla_original_se_importa_como_corresponde(base):
    """La planilla que motivo el trabajo, leida de verdad.

    Este test no sirve si se arma una planilla a mano: el problema nacio de
    ESTE archivo y sus particularidades (nombres partidos, ganancia con punto,
    IVA en cero, 20 renglones sin ganancia) tienen que estar probados contra
    el.
    """
    resultado = importararticulos.importa(
        ARCHIVO_REAL, proveedor_id=1, tipoiva="01",
        ganancia_defecto=GANANCIA_DEFECTO)

    # Todas las filas del archivo entran: ninguna queda afuera.
    assert resultado.filas_con_error == []
    assert resultado.total_importados == resultado.total_leidas
    assert resultado.total_importados > 0

    # El precio sale del costo por la ganancia, con una salvedad que la
    # planilla REAL impone y que aca no se puede inventar:
    #
    # 5 de sus renglones traen COSTO 0, y con costo 0 el precio sale 0 por
    # mas margen que se le ponga. Y hay que mirarlos antes de decidir que son
    # un error de carga:
    #
    #   TELEFONIA (RECUPERO DE GASTOS)   y   VOUCHER REGALO $60000 PESOS
    #
    # Costo 0 es lo correcto para esos dos: no son cosas que se compren y se
    # vendan, son conceptos. El precio lo carga el operador en el momento de
    # la venta, que es exactamente para lo que esta
    # `VentaSimpleCantidadPrecioDialog`. Un precio en cero significa "no hay
    # precio cargado", no "vender a costo" (ver `docs/ARTICULOS-INCRE1.md`).
    #
    # Los otros tres (un mouse, dos sueteres) SI son productos para revender, y
    # ahi el costo 0 huele a error del proveedor. Se importa igual, pero queda
    # anotado aca para que no se pierda: si alguna vez hay que pedirle la lista
    # corregida al proveedor, estos son los que hay que preguntar.
    # `creados` y no `Articulo.select()`: la base del fixture ya viene con un
    # catalogo minimo sembrado (MANTENIMIENTO y otro), y recorrerlo todo mezcla
    # datos de la semilla con datos de la planilla. Antes pasaba de milagro
    # porque el precio de la semilla es 5000.
    importados = set(resultado.creados)
    sin_costo = 0
    for fila in Articulo.select().dicts():
        if fila["nombre"] not in importados:
            continue
        costo = Decimal(str(fila["costo"] or 0))
        if costo == 0:
            sin_costo += 1
            # Con costo 0 el precio tiene que quedar en 0, no inventarse uno.
            assert Decimal(str(fila["preciopub"])) == 0, (
                "{} tiene costo 0 pero quedo en precio {}".format(
                    fila["nombre"], fila["preciopub"]))
            continue
        assert fila["preciopub"] > 0, "{} quedo en precio {}".format(
            fila["nombre"], fila["preciopub"])

    # La planilla tiene que seguir trayendo los renglones sin costo. Si este
    # numero baja a cero, el proveedor corrigio la lista y este comentario
    # quedo viejo: hay que revisarlo antes de borrarlo.
    assert sin_costo > 0, (
        "la planilla real ya no tiene renglones con costo 0: el comentario "
        "de arriba y la regla del precio en cero hay que revisarlas")

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
    # La MISMA ganancia por defecto que en el test de arriba. Si las dos
    # pasadas usaran margenes distintos, la segunda moveria los 20 articulos
    # que no traen ganancia y este test fallaria por el motivo equivocado:
    # parece que la importacion no es idempotente cuando lo que cambio es el
    # margen que le pasamos.
    importararticulos.importa(ARCHIVO_REAL, proveedor_id=1, tipoiva="01",
                              ganancia_defecto=GANANCIA_DEFECTO)
    # El numero de articulos ya incluye los dos de la siembra de test: lo que
    # importa es que la segunda pasada NO lo haga crecer.
    articulos_tras_primera = Articulo.select().count()

    segunda = importararticulos.importa(ARCHIVO_REAL, proveedor_id=1,
                                        tipoiva="01",
                                        ganancia_defecto=GANANCIA_DEFECTO)

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
# -- El IVA por renglon ------------------------------------------------------
#
# Que se decide aca
# ------------------
# La columna IVA del archivo trae 0 en todas las filas de estas planillas, y un
# 0 en una lista de precios de mercaderia no es "exento": es "no lo se". Cuando
# el proveedor si manda una alicuota real, se respeta fila por fila, que es lo
# que hace falta cuando el mismo Excel trae productos al 21 y al 10.5.
#
# El 0 sigue siendo "no lo se" y usa el valor que eligio el operador. Y una
# alicuota que no esta en el catalogo no se adivina: la fila no entra.
#
# Ojo con las filas: la cabecera tiene DIEZ columnas, con Nombre2..Nombre4 en el
# medio. Una fila de siete valores no da error, corre todo de lugar y el test
# falla por un motivo que no tiene nada que ver con lo que prueba.


def test_el_iva_del_archivo_manda_cuando_tiene_alicuota(base, tmp_path):
    archivo = arma_xlsx(tmp_path, [
        [1001, "PRODUCTO 21", None, None, None, "G1", "PROV", 100, 1.5, 21],
        [1002, "PRODUCTO 10.5", None, None, None, "G1", "PROV", 100, 1.5, 10.5],
    ])

    res = importararticulos.importa(archivo, proveedor_id=1, tipoiva="02")

    assert res.filas_con_error == [], res.filas_con_error
    assert Articulo.get(Articulo.codbarra == "1001").tipoiva_id == "01"
    assert Articulo.get(Articulo.codbarra == "1002").tipoiva_id == "02"


def test_el_iva_cero_usa_el_que_eligio_el_operador(base, tmp_path):
    """El 0 del archivo es "no lo se", no "exento".

    Si el 0 se tomara por exento, una lista de precios de mercaderia entera
    entraria con el codigo 50 CONCEP. NO GRAVADOS y las facturas saldrian sin
    impuesto. El error es invisible hasta que hay que cobrar.
    """
    archivo = arma_xlsx(tmp_path, [
        [1001, "PRODUCTO SIN IVA", None, None, None, "G1", "PROV", 100, 1.5, 0],
    ])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="02")

    assert Articulo.get(Articulo.codbarra == "1001").tipoiva_id == "02"


def test_una_planilla_sin_columna_iva_usa_el_del_operador(base, tmp_path):
    """No todas las planillas traen la columna, y eso no puede ser un error."""
    archivo = arma_xlsx(
        tmp_path,
        [[1001, "PRODUCTO", None, None, None, "G1", "PROV", 100, 1.5]],
        cabeceras=["CODIGO DE BARRA", "NOMBRE1", "Nombre2", "Nombre3",
                   "Nombre4", "GRUPO", "PROVEEDOR", "COSTO", "GANANCIA"])

    res = importararticulos.importa(archivo, proveedor_id=1, tipoiva="02")

    assert res.filas_con_error == [], res.filas_con_error
    assert Articulo.get(Articulo.codbarra == "1001").tipoiva_id == "02"


def test_un_iva_que_no_esta_en_el_catalogo_no_importa_la_fila(base, tmp_path):
    """Adivinar un impuesto es peor que no importar esa fila.

    Una alicuota de 5.5 no tiene codigo en el catalogo. Si se usara la del
    operador, el articulo entraria con el 21 cuando el proveedor cobro 5.5, y
    eso se descubre cuando hay que emitir, no antes.
    """
    archivo = arma_xlsx(tmp_path, [
        [1001, "PRODUCTO RARO", None, None, None, "G1", "PROV", 100, 1.5, 5.5],
        [1002, "PRODUCTO NORMAL", None, None, None, "G1", "PROV", 100, 1.5, 21],
    ])

    res = importararticulos.importa(archivo, proveedor_id=1, tipoiva="02")

    assert res.creados == ["PRODUCTO NORMAL"], res.creados
    assert Articulo.get_or_none(Articulo.codbarra == "1001") is None
    assert res.filas_con_error, "la fila rara no se aviso"
    numero, motivo = res.filas_con_error[0]
    assert numero == 2, "el numero de fila no es el del Excel"
    assert "5.5" in motivo, motivo


def test_el_iva_por_fila_no_rompe_la_recarga(base, tmp_path):
    """Importar dos veces la misma lista no mueve nada.

    El IVA ahora es un valor por renglon y el nombre es el mismo de siempre: si
    la comparacion de "cambio" no lo tiene en cuenta, una recarga de la lista
    que ya estaba entra toda como actualizada.
    """
    archivo = arma_xlsx(tmp_path, [
        [1001, "PRODUCTO 21", None, None, None, "G1", "PROV", 100, 1.5, 21],
        [1002, "PRODUCTO 10.5", None, None, None, "G1", "PROV", 100, 1.5, 10.5],
    ])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="02")
    segunda = importararticulos.importa(archivo, proveedor_id=1, tipoiva="02")

    assert segunda.actualizados == [], segunda.actualizados
    assert segunda.sin_cambios == ["PRODUCTO 21", "PRODUCTO 10.5"], \
        segunda.sin_cambios


def test_cambiar_el_iva_de_la_planilla_cambia_el_articulo(base, tmp_path):
    """Si el proveedor sube la alicuota, el articulo tiene que reflejarlo."""
    antes = arma_xlsx(tmp_path, [
        [1001, "PRODUCTO", None, None, None, "G1", "PROV", 100, 1.5, 0],
    ], nombre="antes.xlsx")
    importararticulos.importa(antes, proveedor_id=1, tipoiva="01")

    despues = arma_xlsx(tmp_path, [
        [1001, "PRODUCTO", None, None, None, "G1", "PROV", 100, 1.5, 10.5],
    ], nombre="despues.xlsx")
    segunda = importararticulos.importa(despues, proveedor_id=1, tipoiva="01")

    assert segunda.actualizados == ["PRODUCTO"], segunda.actualizados
    assert Articulo.get(Articulo.codbarra == "1001").tipoiva_id == "02"


# -- Cuantas filas dependen de la ganancia por defecto ------------------------


def test_cuenta_las_filas_que_necesitan_la_ganancia_por_defecto(tmp_path):
    """El numero que el operador necesita ver ANTES de importar.

    Sin esto se entera cuando ya escribio 400 articulos: el error por fila
    aparece en el resumen final y la carga entera hay que rehacerla.
    """
    archivo = arma_xlsx(tmp_path, [
        [1001, "CON GANANCIA", None, None, None, "G1", "PROV", 100, 1.5, 0],
        [1002, "SIN GANANCIA", None, None, None, "G1", "PROV", 100, None, 0],
        [1003, "SIN GANANCIA", None, None, None, "G1", "PROV", 100, None, 0],
        [1004, "GANANCIA CERO", None, None, None, "G1", "PROV", 100, 0, 0],
    ])

    registros = importararticulos.leer_filas(archivo)

    assert len(importararticulos.filas_sin_ganancia(registros)) == 3


def test_no_cuenta_una_fila_que_ya_esta_rota_por_otra_cosa(tmp_path):
    """Una fila ilegible va a fallar por eso, no por la ganancia.

    Contarla aca seria decir "esto necesita la ganancia por defecto" de una
    fila que en realidad se va a rechazar por un costo que no se puede leer, y
    el operador carga un valor que no arregla nada.
    """
    archivo = arma_xlsx(tmp_path, [
        [1001, "COSTO ILEGIBLE", None, None, None, "G1", "PROV",
         "no es un numero", 1.5, 0],
        [1002, "SIN GANANCIA", None, None, None, "G1", "PROV", 100, None, 0],
    ])

    registros = importararticulos.leer_filas(archivo)
    sin_ganancia = importararticulos.filas_sin_ganancia(registros)

    assert [r["nombre"] for r in sin_ganancia] == ["SIN GANANCIA"], \
        [r["nombre"] for r in sin_ganancia]


def test_una_planilla_completa_no_necesita_la_ganancia_por_defecto(tmp_path):
    """El caso normal: no hay nada que avisar y el campo no estorba."""
    archivo = arma_xlsx(tmp_path, [
        [1001, "UNO", None, None, None, "G1", "PROV", 100, 1.5, 0],
        [1002, "DOS", None, None, None, "G1", "PROV", 100, 1.4, 0],
    ])

    registros = importararticulos.leer_filas(archivo)

    assert importararticulos.filas_sin_ganancia(registros) == []

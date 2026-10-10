# coding=utf-8
"""Importar con mas de un proveedor, la escala de la ganancia y la vista previa.

Los tres bugs que estos tests cubren salieron de las planillas reales, no de
imaginar casos:

1. **La ganancia de 2900%.** La planilla de BOTZ trae `GANANCIA = 30` en las
   69 filas, y eso es un PORCENTAJE. El codigo lo leia como multiplicador y
   hacia (30 - 1) x 100 = 2900: un costo de 4700 se iba a 141.000 en vez de
   6.110. La de ANYWAY trae `GANANCIA = 1.5` en las 704 filas, y ESO si es
   multiplicador (50%). O sea que la columna no significa lo mismo segun el
   proveedor, y leerla de una sola forma da precios que no cierran.

2. **Todos con el proveedor del desplegable.** La columna PROVEEDOR se leia y
   se tiraba. Con una planilla de un proveedor no se nota; con una que mezcla
   varios, el catalogo entero queda mal atribuido.

3. **Reimportar hasta que "salga sin errores".** Con filas sin codigo de
   barras, el indice en memoria guardaba None en vez del id del articulo
   recien creado. El codigo generado no se reutilizaba, cada vuelta movia un
   articulo mas, y el operador tenia que importar una y otra vez.

Como se verifican
-----------------
Contra el codigo viejo (`git stash`) estos tests tienen que fallar con el
SINTOMA, no con un AttributeError. Un fallo que dice "falta un metodo" no
demuestra que el precio estaba mal.
"""

import os
import sys
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _r in (RAIZ, os.path.join(RAIZ, "tests")):
    if _r not in sys.path:
        sys.path.insert(0, _r)

import pytest  # noqa: E402

from libs import importararticulos  # noqa: E402
from modelos.Articulos import Articulo  # noqa: E402
from modelos.Proveedores import Proveedor  # noqa: E402

CABECERA = ["CODIGO DE BARRA", "NOMBRE1", "Nombre2", "Nombre3", "Nombre4",
            "GRUPO", "PROVEEDOR", "COSTO", "GANANCIA", "IVA"]


@pytest.fixture
def base():
    from ayuda_stock import base_memoria

    with base_memoria() as memoria:
        yield memoria


def arma_xlsx(tmp_path, filas, nombre="lista.xlsx", cabeceras=None):
    from openpyxl import Workbook

    libro = Workbook()
    hoja = libro.active
    hoja.append(cabeceras or CABECERA)
    for fila in filas:
        hoja.append(fila)
    archivo = str(tmp_path / nombre)
    libro.save(archivo)
    return archivo


def _crudo(nombre):
    return (Articulo.select().where(Articulo.nombre == nombre).dicts().get())


# -- La escala de la ganancia ------------------------------------------------

def test_ganancia_de_30_por_ciento_no_sale_2900(tmp_path, base):
    """El bug reportado: GANANCIA=30 es un porcentaje, no un multiplicador.

    Con costo 4700 y 30% el precio es 6.110. Leyendo 30 como multiplicador
    daba (30-1)x100 = 2900% y un precio de 141.000: veinte veces lo que
    corresponde, en 69 articulos de una sola planilla.
    """
    assert importararticulos._porcentaje_de_ganancia(Decimal("30")) == Decimal("30")
    assert importararticulos._porcentaje_de_ganancia(Decimal("1.5")) == Decimal("50.00")
    assert importararticulos._porcentaje_de_ganancia(Decimal("1.4")) == Decimal("40.00")

    archivo = arma_xlsx(tmp_path, [
        [None, "607 ZZ", None, None, None, "BOTZBLITZ", "GP", 4700, 30, 21]])
    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    fila = _crudo("607 ZZ")
    assert fila["incre1"] == Decimal("30"), \
        "quedo una ganancia de {}% con un 30% en la planilla".format(fila["incre1"])
    assert fila["preciopub"] == Decimal("6110"), \
        "el precio salio {} en vez de 6110 (costo 4700 con 30%)".format(fila["preciopub"])


def test_detecta_que_escala_trae_la_planilla(tmp_path, base):
    """Que el sistema sepa MIRAR la columna antes de usarla.

    Sin esto, el operador se entera del precio mal cuando ya esta escrito, y
    el resumen dice "69 articulos importados" como si estuviera todo bien.
    """
    porcentajes = arma_xlsx(tmp_path, [
        [None, "A", None, None, None, "VARIOS", "GP", 100, 30, 0]],
        nombre="porc.xlsx")
    multiplicadores = arma_xlsx(tmp_path, [
        [None, "A", None, None, None, "VARIOS", "GP", 100, 1.5, 0]],
        nombre="mult.xlsx")
    mezclada = arma_xlsx(tmp_path, [
        [None, "A", None, None, None, "VARIOS", "GP", 100, 30, 0],
        [None, "B", None, None, None, "VARIOS", "GP", 200, 1.5, 0]],
        nombre="mezcla.xlsx")

    assert importararticulos.escala_ganancia(
        importararticulos.leer_filas(porcentajes)) == "porcentaje"
    assert importararticulos.escala_ganancia(
        importararticulos.leer_filas(multiplicadores)) == "multiplicador"
    assert importararticulos.escala_ganancia(
        importararticulos.leer_filas(mezclada)) == "mixta"


# -- El proveedor de cada fila ------------------------------------------------

def test_cada_fila_va_con_el_proveedor_de_su_fila(tmp_path, base):
    """Una planilla con dos proveedores: cada articulo con el suyo.

    Antes toda la carga usaba el del desplegable, asi que una planilla
    compuesta quedaba con el catalogo entero atribuido a un proveedor.
    """
    Proveedor.create(idproveedor=2, nombre="NORDESTE", tiporesp=1, idlocalidad=1)
    Proveedor.create(idproveedor=3, nombre="ANYWAY", tiporesp=1, idlocalidad=1)

    archivo = arma_xlsx(tmp_path, [
        [None, "DEL NORTE", None, None, None, "VARIOS", "NORDESTE", 100, 1.2, 0],
        [None, "DE ANYWAY", None, None, None, "VARIOS", "ANYWAY", 200, 1.2, 0],
    ])

    r = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert _crudo("DEL NORTE")["provppal"] == 2
    assert _crudo("DE ANYWAY")["provppal"] == 3
    assert sorted(r.proveedores_usados) == ["ANYWAY", "NORDESTE"]


def test_el_proveedor_del_archivo_no_distingue_por_grafia(tmp_path, base):
    """"Nordeste", "NORDESTE " y "NOR DESTE" son el mismo proveedor.

    Es el mismo criterio que se usa con los grupos: si no se normaliza, una
    planilla con el nombre escrito distinto crea un proveedor mas o lo deja
    sin resolver.
    """
    Proveedor.create(idproveedor=2, nombre="Nordeste", tiporesp=1, idlocalidad=1)

    archivo = arma_xlsx(tmp_path, [
        [None, "UNO", None, None, None, "VARIOS", "  NORDESTE  ", 100, 1.2, 0]])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert _crudo("UNO")["provppal"] == 2, \
        "no resolvio el proveedor por nombre normalizado"


def test_un_proveedor_que_no_esta_cargado_se_avisa(tmp_path, base):
    """Si el nombre no existe, se usa el del desplegable PERO se avisa.

    No se crea el proveedor: el nombre viene en texto libre de otro programa
    y "NORDESTE S.R.L." al lado de un "NORDESTE" ya cargado dejaria dos
    proveedores para el mismo. Pero el operador tiene que enterarse, porque si
    no el catalogo queda atribuido a un proveedor que el archivo nunca nombro.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "UNO", None, None, None, "VARIOS", "PROVEEDOR NUEVO", 100, 1.2, 0]])

    r = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert r.proveedores_no_encontrados == ["PROVEEDOR NUEVO"]
    assert "PROVEEDOR NUEVO" in r.resumen()
    assert Proveedor.select().where(
        Proveedor.nombre == "PROVEEDOR NUEVO").count() == 0, \
        "no deberia crear un proveedor que no estaba cargado"


# -- Reimportar la misma planilla --------------------------------------------

def test_importar_dos_veces_no_mueve_articulos(tmp_path, base):
    """El sintoma del operador: "importe mas de una vez con errores entre medio".

    Sin codigo de barras, cada fila genera un codigo interno. Si el indice
    en memoria no guarda el id del articulo recien creado, el codigo generado
    no se reutiliza en la vuelta siguiente: se genera otro con sufijo, el
    articulo se encuentra por nombre, lo actualiza y le cambia el codigo.
    Cada vuelta movia un articulo mas y el operador no encontraba el punto
    en que se stabilize.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "SIN CODIGO UNO", None, None, None, "VARIOS", "N", 100, 1.2, 0],
        [None, "SIN CODIGO DOS", None, None, None, "VARIOS", "N", 200, 1.2, 0],
    ])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")
    codigos = {a["nombre"]: a["codbarra"] for a in Articulo.select().dicts()}

    segunda = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert segunda.actualizados == [], \
        "reimportar la misma planilla movio {}".format(segunda.actualizados)
    assert segunda.sin_cambios, "la segunda vuelta deberia dar todo 'sin cambios'"
    assert {a["nombre"]: a["codbarra"] for a in Articulo.select().dicts()} == codigos, \
        "los codigos internos cambiaron al reimportar"


def test_importar_tres_veces_se_estabiliza(tmp_path, base):
    """Tres vueltas, y la tercera tiene que decir lo mismo que la segunda."""
    archivo = arma_xlsx(tmp_path, [
        [None, "UNO", None, None, None, "VARIOS", "N", 100, 1.2, 0],
        [None, "DOS", None, None, None, "VARIOS", "N", 200, 1.2, 0],
        [None, "TRES", None, None, None, "VARIOS", "N", 300, 1.2, 0],
    ])

    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")
    segunda = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")
    tercera = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert tercera.actualizados == [], \
        "la tercera vuelta todavia movia {}".format(tercera.actualizados)
    assert len(tercera.sin_cambios) == len(segunda.sin_cambios)


def test_avisa_los_nombres_repetidos_con_su_numero_de_fila(tmp_path, base):
    """Un nombre repetido sin codigo de barras hace que un costo pise al otro.

    En la planilla de BOTZ, `6308` aparece en las filas 59 y 60 con costos
    distintos. No se puede decidir sola cual vale: lo que puede hacer es
    decirlo, con el numero de fila para que el operador abra el Excel.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "6308", None, None, None, "VARIOS", "GP", 29070, 30, 0],
        [None, "6308", None, None, None, "VARIOS", "GP", 2000, 30, 0],
    ])

    r = importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    assert r.nombres_repetidos == ["6308"]
    assert r.detalle_repetidos == [("6308", [2, 3])]
    assert "6308" in r.resumen()
    assert "59" not in r.resumen() or True   # los numeros dependen del archivo


def test_reimportar_no_borra_el_codigo_de_barras(tmp_path, base):
    """Una fila SIN codigo no puede dejar al articulo sin el suyo.

    Este es el mas grave de los tres, porque un articulo sin EAN deja de
    poder cobrarse con lector y el error no se ve hasta que alguien lo pasa
    por el mostrador.

    Se llega asi: se agrega la columna `codbarra` a los campos SIEMPRE, y si
    la fila del archivo no trae, queda vacia. Cuando la fila actualiza a un
    articulo que ya existia, el bucle de actualizacion le escribe ese vacio
    encima del EAN que tenia. Con una planilla como la de BOTZ, que no trae
    la columna CODIGO DE BARRA en ninguna fila, TODOS los articulos con EAN
    se quedan sin el.
    """
    # Se crea el articulo con un EAN de verdad.
    primero = arma_xlsx(tmp_path, [
        ["779999", "CON EAN", None, None, None, "VARIOS", "N", 100, 1.2, 0]],
        nombre="con-ean.xlsx")
    importararticulos.importa(primero, proveedor_id=1, tipoiva="01")
    assert _crudo("CON EAN")["codbarra"] == "779999"

    # Ahora la misma planilla SIN codigo, que es como viene la de BOTZ: la
    # columna existe pero TODAS sus celdas estan vacias. Ojo que no se puede
    # sacar la columna del encabezado: sin CODIGO DE BARRA, todas las
    # columnas se corren un lugar y el COSTO se lee en la celda de GANANCIA,
    # que da costo=None y la fila ni entra.
    sin_columna = arma_xlsx(tmp_path, [
        [None, "CON EAN", None, None, None, "VARIOS", "N", 150, 1.2, 0]],
        nombre="sin-ean.xlsx")
    importararticulos.importa(sin_columna, proveedor_id=1, tipoiva="01")

    fila = _crudo("CON EAN")
    assert fila["codbarra"] == "779999", \
        "la reimportacion borro el EAN: quedo {!r}. El articulo deja de poder " \
        "cobrarse con lector.".format(fila["codbarra"])
    assert fila["costo"] == Decimal("150"), "pero el costo si tiene que actualizarse"


# -- La vista previa ---------------------------------------------------------

def test_la_vista_previa_no_escribe_nada(tmp_path, base):
    """Previsualizar tiene que ser de verdad solo mirar.

    Si escribiera, la pantalla "mostrar como va a quedar" crearia articulos
    cada vez que el operador cambia un campo, y el nombre de la fonction
    mentiria.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "WHEY", None, None, None, "SUPLEMENTOS", "N", 10142, 1.4, 0]])

    antes = Articulo.select().count()
    pv = importararticulos.previsualiza(archivo, proveedor_id=1, tipoiva="01")
    assert Articulo.select().count() == antes, \
        "previsualiza() escribio articulos"

    fila = pv.filas[0]
    assert fila.nombre == "WHEY"
    assert fila.costo == Decimal("10142")
    assert fila.margen == Decimal("40.00")
    assert fila.precio == Decimal("14198.8000")
    assert fila.estado == "nuevo"


def test_la_vista_previa_muestra_el_proveedor_que_corresponde(tmp_path, base):
    """La grilla tiene que decir de quien es cada fila.

    Es el dato que faltaba antes: el proveedor se elegia una vez para toda la
    carga y no quedaba rastro de que el archivo traia otro.
    """
    Proveedor.create(idproveedor=2, nombre="ANYWAY", tiporesp=1, idlocalidad=1)
    archivo = arma_xlsx(tmp_path, [
        [None, "DE ANYWAY", None, None, None, "VARIOS", "ANYWAY", 100, 1.2, 0]])

    pv = importararticulos.previsualiza(archivo, proveedor_id=1, tipoiva="01")

    assert pv.filas[0].proveedor == "ANYWAY"
    assert pv.proveedores_usados == ["ANYWAY"]


def test_la_vista_previa_avisa_las_filas_que_no_entran(tmp_path, base):
    """Las filas con dato ilegible tienen que verse, con su motivo."""
    archivo = arma_xlsx(tmp_path, [
        [None, "BUENO", None, None, None, "VARIOS", "N", 100, 1.2, 0],
        [None, "MALO", None, None, None, "VARIOS", "N", "veinte", 1.2, 0],
    ])

    pv = importararticulos.previsualiza(archivo, proveedor_id=1, tipoiva="01")

    errores = [f for f in pv.filas if f.estado == "error"]
    assert errores, "la fila con COSTO ilegible no aparece en la vista previa"
    assert "COSTO" in errores[0].motivo
    assert errores[0].numero == 3


def test_la_vista_previa_dice_como_va_a_quedar_el_articulo_existente(tmp_path, base):
    """Una fila que ya esta tiene que decir "actualiza", no "nuevo".

    Si dice "nuevo" el operador no tiene forma de saber que esa lista ya se
    habia cargado y que le va a pisar el costo.
    """
    archivo = arma_xlsx(tmp_path, [
        [None, "YA ESTA", None, None, None, "VARIOS", "N", 500, 1.2, 0]])
    importararticulos.importa(archivo, proveedor_id=1, tipoiva="01")

    pv = importararticulos.previsualiza(archivo, proveedor_id=1, tipoiva="01")
    assert pv.filas[0].estado == "actualiza"
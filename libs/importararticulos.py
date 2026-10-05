# coding=utf-8
"""Importacion de articulos desde el Excel del proveedor.

Que hay aca y que no
--------------------
Aca esta toda la importacion menos la pantalla: leer el Excel, calcular el
precio, resolver los catalogos (grupo, unidad) y escribir el articulo. No
importa Qt ni PyQt5, y eso es a proposito: la parte que decide si un costo de
10142 con ganancia 1.4 tiene que dejar un precio de 14198.80 se puede probar
sin QApplication, que es la unica forma de saber que anda.

La pantalla esta en `vistas/ImportarArticulos.py` y no hace mas que juntar los
datos que se piden aca.

El formato del archivo
----------------------
El archivo trae estos titulos, en cualquier orden, con espacios de mas y con
acentos o sin ellos:

    CODIGO DE BARRA | NOMBRE1 | Nombre2 | Nombre3 | Nombre4 |
    GRUPO | PROVEEDOR | COSTO | GANANCIA | IVA

`NOMBRE1..NOMBRE4` son partes de un mismo nombre, no cuatro nombres: el
proveedor exporta el nombre partido en columnas y hay que volver a pegarlo.

Por que GANANCIA es un multiplicador
------------------------------------
Porque es como vienen las listas de precios: si el costo es 10142 y la
ganancia 1.4, el precio al publico es 14198.80. Es un factor, no un
porcentaje. No es una regla que se pueda deducir del archivo: esta escrita aca
y en el dialogo porque es una decision del operador, y cambiarla tiene que ser
cambiar una linea.

Por que el IVA 0 del archivo no es "exento"
-------------------------------------------
El 0 de la columna IVA no significa alicuota cero. Significa "no me digas vos,
dejame el que eligio el operador": un Excel de proveedor con la columna IVA en
cero en todas las filas no esta opinando sobre el impuesto, esta esperando que
lo carguen. Si se tomara como exento, el resultado seria un catalogo entero con
el impuesto equivocado y nadie se enteraria hasta ver la factura.

Por que se actualiza lo que ya existe
-------------------------------------
Una lista de precios se recarga, no se duplica. Si el articulo ya esta, se le
cambian costo, precio y proveedor y se cuenta como actualizado. Buscar por
codigo de barra es lo primero: es el unico identificador que el proveedor y el
sistema comparten de verdad. Cuando no hay codigo se cae al nombre normalizado,
porque un nombre escrito de otra forma es el mismo producto.

Y si no cambio nada, no se escribe: una recarga de la misma lista tiene que
decir "400 ya estaban igual", no "400 actualizados", o el operador deja de
mirar el resumen.
"""

import os
import unicodedata
from decimal import Decimal, InvalidOperation

from openpyxl import load_workbook

from modelos.Articulos import Articulo
from modelos.Grupos import Grupo
from modelos.ModeloBase import _a_bit
from modelos.Unidades import Unidad

# Un articulo sin codigo de barras no se puede cobrar con lector. Para eso esta
# el prefijo en el codigo que se genera: que se vea que es interno y que nadie
# lo escanee en el mostrador pensando que es el EAN del producto.
PREFIJO_CODBARRA_INTERNO = "INT"


class ErrorImportacion(Exception):
    """El archivo no se puede importar. El mensaje va para el operador."""


class FilaInvalida(Exception):
    """Una fila del Excel no tiene lo minimo para ser un articulo."""

    def __init__(self, motivo, numero=None):
        self.numero = numero
        self.motivo = motivo
        super().__init__(motivo)


class Resultado:
    """Que paso con la importacion. Lo lee el resumen de la pantalla."""

    def __init__(self):
        self.creados = []
        self.actualizados = []
        self.sin_cambios = []
        self.filas_con_error = []       # [(numero de fila, motivo), ...]
        self.grupos_creados = []

    @property
    def total_leidas(self):
        return (len(self.creados) + len(self.actualizados)
                + len(self.sin_cambios) + len(self.filas_con_error))

    @property
    def total_importados(self):
        return len(self.creados) + len(self.actualizados)

    def resumen(self):
        """El texto del aviso final."""
        partes = [
            "Se importaron {} articulos: {} nuevos y {} actualizados.".format(
                self.total_importados, len(self.creados), len(self.actualizados)),
        ]
        if self.sin_cambios:
            partes.append("{} ya estaban igual y quedaron como estaban.".format(
                len(self.sin_cambios)))
        if self.grupos_creados:
            partes.append("Grupos creados: {}.".format(
                ", ".join(self.grupos_creados)))
        if self.filas_con_error:
            partes.append("{} filas no se importaron (la primera: fila {}, {}).".format(
                len(self.filas_con_error),
                self.filas_con_error[0][0], self.filas_con_error[0][1]))
        return " ".join(partes)


# -- Lectura del Excel -------------------------------------------------------

def _texto(valor):
    """El valor de una celda como texto limpio, o '' si no hay nada."""
    if valor is None:
        return ""
    return str(valor).strip()


def _normaliza_texto(texto):
    """Sin acentos, en mayusculas y con espacios colapsados.

    Sirve para comparar dos cosas que alguien escribe distinto: "Suplementos" y
    "SUPLEMENTOS" son el mismo grupo, y un nombre de producto con un espacio de
    mas es el mismo producto.
    """
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.upper().split())


def _normaliza_titulo(titulo):
    """'  Nombre2 ' -> 'nombre2'. Para comparar cabeceras sin sorpresas."""
    return _normaliza_texto(titulo).lower()


def _numero(valor, campo):
    """El numero de la celda como Decimal, o None si la celda esta vacia.

    Lo separatir de miles importa y es peligroso por partida doble. En un Excel
    en configuracion regional argentina "10.142" son diez mil ciento cuarenta y
    dos, y `Decimal("10.142")` son diez con mil y cuatro centesimas: el costo
    entra mil veces mas chico y el precio sale con tres ceros de mas. Nadie lo
    va a notar hasta que la factura no cierra.

    La regla es por columna y no general, porque "1.400" es un costo de mil
    cuatrocientos en COSTO y una ganancia de mil cuatrocientos en GANANCIA, y
    las dos cosas tienen que salir bien:

    * COSTO: el punto con exactamente tres digitos despues es de miles. Un
      costo con tres decimales no existe en una lista de precios.
    * GANANCIA: el punto es decimal siempre. "1.4" es una ganancia de 1.4 y
      "1,4" tambien.
    """
    if valor is None:
        return None

    # Una celda numerica de Excel no tiene separador: no hay nada que
    # adivinar y pasar por el camino de texto solo agrega chances de errar.
    if isinstance(valor, (int, float, Decimal)):
        return Decimal(str(valor))

    texto = _texto(valor)
    if not texto:
        return None

    texto = texto.replace(" ", "")
    if "," in texto and "." in texto:
        # El separador decimal es el ULTIMO. En "1.234,56" es la coma; en
        # "1,234.56" es el punto.
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    elif "." in texto and campo == "COSTO":
        entero, _, decimal = texto.partition(".")
        if len(decimal) == 3 and entero.lstrip("-").isdigit() and decimal.isdigit():
            texto = entero + decimal      # "10.142" -> 10142

    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        raise FilaInvalida("{} no es un numero: {!r}".format(campo, _texto(valor)))


def _nombre_de_fila(partes):
    """Pega las partes del nombre en una sola cadena.

    'WHEY CUTTER', 'PROTE+QUEMADOR', 'VANILLA'
        -> 'WHEY CUTTER PROTE+QUEMADOR VANILLA'

    Las partes vacias se ignoran y los espacios se colapsan, para que un
    nombre partido con un espacio de mas al final no termine con doble espacio
    ni en el catalogo ni en el ticket.
    """
    return " ".join(" ".join(p for p in (_texto(x) for x in partes) if p).split())


def _cabeceras(hoja):
    """Lee la fila de titulos: devuelve ({titulo normalizado: indice}, filas)."""
    filas = hoja.iter_rows(values_only=True)
    try:
        primera = next(filas)
    except StopIteration:
        raise ErrorImportacion("El archivo esta vacio.")

    mapa = {}
    for indice, titulo in enumerate(primera):
        clave = _normaliza_titulo(titulo)
        if clave and clave not in mapa:
            mapa[clave] = indice
    return mapa, filas


def _columna(mapa, *titulos):
    """El indice de la primera cabecera que exista, o None."""
    for titulo in titulos:
        clave = _normaliza_titulo(titulo)
        if clave in mapa:
            return mapa[clave]
    return None


def leer_filas(archivo):
    """Devuelve [(numero de fila, datos)] del Excel, sin tocar la base.

    El numero de fila es el de Excel (arranca en 2, porque la 1 son los
    titulos) y es el que se muestra en el error: si algo no entra, el operador
    tiene que poder abrir el archivo y buscar esa fila.

    Las filas totalmente vacias se descartan. Un Excel exportado con formato
    de mas arrastra decenas de filas en blanco al final, y sin este filtro el
    resumen contaria articulos que no existen.
    """
    if not archivo or not os.path.exists(archivo):
        raise ErrorImportacion("No se encuentra el archivo '{}'.".format(archivo))

    try:
        libro = load_workbook(archivo, data_only=True, read_only=True)
    except Exception as error:
        raise ErrorImportacion("No se pudo abrir el archivo: {}".format(error))

    try:
        hoja = libro[libro.sheetnames[0]]
        mapa, filas = _cabeceras(hoja)

        # Las columnas se resuelven UNA vez. Buscarlas por cada fila hacia que
        # leer 400 renglones sea 400 veces mas lento por nada.
        col_codigo = _columna(mapa, "CODIGO DE BARRA")
        col_nombre = _columna(mapa, "NOMBRE1")
        col_grupo = _columna(mapa, "GRUPO")
        col_costo = _columna(mapa, "COSTO")
        col_ganancia = _columna(mapa, "GANANCIA")
        col_proveedor = _columna(mapa, "PROVEEDOR")
        cols_nombre = [col_nombre,
                       _columna(mapa, "NOMBRE2"),
                       _columna(mapa, "NOMBRE3"),
                       _columna(mapa, "NOMBRE4")]

        if col_nombre is None or col_costo is None:
            faltan = []
            if col_nombre is None:
                faltan.append("NOMBRE1")
            if col_costo is None:
                faltan.append("COSTO")
            raise ErrorImportacion(
                "El archivo no tiene las columnas {}. Revisa que la primera "
                "fila sea la de los titulos.".format(" ni ".join(faltan)))

        registros = []
        for numero, fila in enumerate(filas, start=2):

            def celda(indice):
                if indice is None or indice >= len(fila):
                    return None
                return fila[indice]

            nombre = _nombre_de_fila([celda(i) for i in cols_nombre])
            if not nombre:
                continue        # fila en blanco: no es un articulo

            try:
                registros.append({
                    "numero": numero,
                    "codbarra": _texto(celda(col_codigo)),
                    # `nombre` es CHAR(100) y `nombreticket` CHAR(30): los
                    # nombres de esta lista pasan de cien caracteres y MySQL
                    # cortaria en silencio, dejando dos productos con el
                    # nombre igual.
                    "nombre": nombre[:100],
                    "nombreticket": nombre[:30],
                    "costo": _numero(celda(col_costo), "COSTO"),
                    "ganancia": _numero(celda(col_ganancia), "GANANCIA"),
                    "grupo": _texto(celda(col_grupo)),
                    "proveedor": _texto(celda(col_proveedor)),
                })
            except FilaInvalida as error:
                # Un numero ilegible no tira toda la carga: la fila se lleva el
                # error y el operador lo ve en el resumen con su numero.
                registros.append({
                    "numero": numero, "error": error.motivo,
                    "codbarra": "", "nombre": nombre[:100],
                    "nombreticket": nombre[:30],
                    "costo": None, "ganancia": None, "grupo": "", "proveedor": "",
                })

        if not registros:
            raise ErrorImportacion("El archivo no tiene filas de datos.")
        return registros
    finally:
        libro.close()


# -- Calculo del precio ------------------------------------------------------

CUATRO_DECIMALES = Decimal("0.0001")


def calcula_precio(costo, ganancia):
    """El precio al publico: costo x ganancia, redondeado a 4 decimales.

    `preciopub` es DECIMAL(12,4), asi que el redondeo es el del modelo y no un
    capricho: con mas decimales el numero entra y MySQL lo guarda truncado, y
    el operador ve un precio distinto del que se calculo.
    """
    if costo is None:
        raise FilaInvalida("no tiene costo")
    if ganancia is None:
        raise FilaInvalida("no tiene ganancia")

    return (Decimal(costo) * Decimal(ganancia)).quantize(CUATRO_DECIMALES)


# -- Catalogos ---------------------------------------------------------------

def _impuesto_por_defecto():
    """El impuesto que se pone a un grupo nuevo.

    Sin percepcion es el default del modelo (`Grupo.impuesto` default=1) y lo
    que el ABM de grupos usa cuando no se toca el campo. Inventario sin
    percepcion es el caso normal de un producto de reventa, y el grupo se
    corrige despues en la pantalla de Grupos si hace falta.
    """
    return 1


def _resolver_grupo(nombre, cache, creados):
    """El id del grupo, creandolo si hace falta.

    Se busca por nombre normalizado porque el archivo puede traer
    "Suplementos" y la base tener "SUPLEMENTOS": son el mismo grupo, y crear
    un segundo dejaria el catalogo partido en dos.

    El `cache` evita volver a recorrer la tabla por cada fila: los grupos de
    una lista de precios son pocos y se repiten en todas las filas.

    `creados` recibe el nombre de cada grupo nuevo. No es un detalle para el
    resumen: el operador tiene que saber que la pantalla le creo un grupo,
    porque un grupo que se creo solo es un grupo que nadie reviso y que
    despues aparece en un reporte de ventas con un nombre que nadie eligio.
    """
    nombre = (nombre or "").strip() or "SIN GRUPO"
    clave = _normaliza_texto(nombre)
    if clave in cache:
        return cache[clave]

    for grupo in Grupo.select():
        if _normaliza_texto(grupo.nombre) == clave:
            cache[clave] = grupo.idgrupo
            return grupo.idgrupo

    grupo = Grupo.create(nombre=nombre[:30], impuesto=_impuesto_por_defecto())
    cache[clave] = grupo.idgrupo
    if grupo.nombre not in creados:
        creados.append(grupo.nombre)
    return grupo.idgrupo


def _resolver_unidad(codigo):
    """La unidad elegida, o 'UN' si esa unidad no existe en la base.

    Un 'UN' en vez de un error: la unidad casi siempre es UN en una lista de
    precios, y frenar toda la carga porque el codigo de la unidad no este
    cargado es una perdida de tiempo para todos.
    """
    codigo = (codigo or "").strip() or "UN"
    existe = Unidad.get_or_none(Unidad.unidad == codigo)
    return existe.unidad if existe else "UN"


# -- Importacion -------------------------------------------------------------

def _indice_de_existentes():
    """(codigo -> id, nombre normalizado -> id) de lo que ya esta cargado.

    Se arma una vez. Buscar con una consulta por fila es la diferencia entre
    importar 400 articulos en un segundo y en media hora.
    """
    por_codigo = {}
    por_nombre = {}
    for articulo in Articulo.select():
        if articulo.codbarra:
            por_codigo.setdefault(articulo.codbarra, articulo.idarticulo)
        por_nombre.setdefault(_normaliza_texto(articulo.nombre), articulo.idarticulo)
    return por_codigo, por_nombre


def _busca_existente(registro, por_codigo, por_nombre):
    """El id del articulo que este renglon actualiza, o None si es nuevo.

    El codigo manda: si el renglon trae un codigo que NO esta en la base, es un
    producto nuevo aunque se parezca en el nombre a uno viejo con codigo. Un
    codigo de barras no se reasigna solo, y pisar por nombre un articulo que ya
    se cobra con lector es peor que duplicar.
    """
    codigo = registro.get("codbarra")
    if codigo:
        return por_codigo.get(codigo)

    return por_nombre.get(_normaliza_texto(registro["nombre"]))


def _genera_codbarra(nombre, existentes):
    """Un codigo interno para un articulo que vino sin codigo de barras.

    Sale del nombre, que es lo unico estable que hay, y si ya esta ocupado se
    le agrega un numero. El prefijo lo delata como interno.
    """
    base = "{}{}".format(
        PREFIJO_CODBARRA_INTERNO,
        "".join(c for c in _texto(nombre).upper() if c.isalnum())[:18])
    codigo = base or PREFIJO_CODBARRA_INTERNO
    sufijo = 1
    while codigo in existentes:
        sufijo += 1
        codigo = "{}-{}".format(base, sufijo)
    existentes.add(codigo)
    return codigo


def _mismo_que_ya_esta(guardado, campos):
    """True si escribir estos campos no cambiaria nada.

    `guardado` es el renglon del articulo YA EN LA BASE, leido con
    `.dicts()`. No es un objeto `Articulo` y esa diferencia es todo el punto:

    Cuando se lee un modelo con peewee, los campos que son claves foraneas
    devuelven el OBJETO relacionado, no el numero: `articulo.grupo` es un
    `<Grupo: 2>`, `articulo.tipoiva` es un `<Tipoiva: 01>`. Comparar eso con
    el `2` o el `"01"` que uno tiene en la mano dice siempre "cambio", y el
    resultado es que una recarga de la misma lista de precios reporta
    "400 actualizados" y no toca nada. Con `.dicts()` llegan los escalares
    crudos y la comparacion es la que uno cree que esta haciendo.

    Los bits van por `_a_bit`: MySQL devuelve un BIT(1) como b'\\x01', que
    nunca es igual a True con `==`.
    """
    for campo, valor in campos.items():
        if campo == "codbarra":
            continue        # el codigo se genera, no se compara

        actual = guardado.get(campo)

        if campo == "controlastock":
            if _a_bit(actual) != _a_bit(valor):
                return False
        elif campo in ("grupo", "provppal"):
            if int(actual or 0) != int(valor or 0):
                return False
        elif isinstance(actual, Decimal) or isinstance(valor, Decimal):
            try:
                if Decimal(str(actual)) != Decimal(str(valor)):
                    return False
            except (InvalidOperation, TypeError):
                return False
        else:
            if str(actual if actual is not None else "") != str(
                    valor if valor is not None else ""):
                return False
    return True


def importa(archivo, proveedor_id, tipoiva, unidad="UN",
            ganancia_defecto=None, concepto="1", controlastock=True,
            stockminimo=0):
    """Importa el Excel y devuelve un `Resultado`.

    Los parametros son los que se piden en la pantalla:

    * `proveedor_id`: de que proveedor es la lista. Es el mismo para todas las
      filas y se elige una vez; el nombre de la columna PROVEEDOR del archivo
      se lee pero no manda, porque un Excel puede traer el proveedor en texto
      libre y la base lo tiene como id.
    * `tipoiva`: el IVA que se aplica a todas las filas. El 0 de la columna IVA
      del archivo es lo que hace que se pregunte (ver el modulo).
    * `ganancia_defecto`: la ganancia para los renglones que no traen una. Los
      que la traen usan la del renglon, que es lo que hace que una lista con
      1.4 y 1.5 mezclados respete la diferencia.
    * `unidad`: la unidad de medida de los articulos importados.
    * `controlastock`: si participan del control de stock. Por defecto si: es
      una lista de precios de mercaderia, no un catalogo de servicios.

    `proveedor_id` no tiene default a proposito. Si faltara, los articulos
    quedarian con el proveedor 1, que en una base recien sembrada es "SIN
    PROVEEDOR", y eso es un dato falso que nadie va a corregir.
    """
    if proveedor_id is None:
        raise ErrorImportacion("No se eligio proveedor.")

    registros = leer_filas(archivo)

    resultado = Resultado()
    try:
        stockminimo = Decimal(str(stockminimo or 0))
    except (InvalidOperation, ValueError, TypeError):
        stockminimo = Decimal(0)

    por_codigo, por_nombre = _indice_de_existentes()
    existentes = set(por_codigo)
    cache_grupos = {}
    codigo_unidad = _resolver_unidad(unidad)
    iva = str(tipoiva).zfill(2)

    for registro in registros:
        numero = registro["numero"]
        try:
            if registro.get("error"):
                raise FilaInvalida(registro["error"], numero)

            nombre = registro["nombre"].strip()
            if not nombre:
                raise FilaInvalida("el nombre quedo vacio", numero)

            costo = registro["costo"]
            if costo is None:
                raise FilaInvalida("no tiene COSTO", numero)
            if costo < 0:
                raise FilaInvalida(
                    "el costo {} es negativo".format(costo), numero)

            ganancia = registro["ganancia"]
            if ganancia is None or ganancia <= 0:
                if ganancia_defecto is None:
                    raise FilaInvalida(
                        "no tiene GANANCIA y no se eligio una por defecto", numero)
                ganancia = Decimal(str(ganancia_defecto))

            campos = {
                "nombre": nombre,
                "nombreticket": registro["nombreticket"],
                "costo": costo,
                "preciopub": calcula_precio(costo, ganancia),
                "grupo": _resolver_grupo(registro["grupo"], cache_grupos,
                                         resultado.grupos_creados),
                "provppal": proveedor_id,
                "tipoiva": iva,
                "unidad": codigo_unidad,
                "concepto": str(concepto),
                "codbarra": registro["codbarra"],
                "controlastock": controlastock,
                "stockminimo": stockminimo,
            }

            codigo = campos["codbarra"]
            if not codigo:
                codigo = _genera_codbarra(nombre, existentes)
                campos["codbarra"] = codigo

            id_articulo = _busca_existente(registro, por_codigo, por_nombre)

            if id_articulo is None:
                Articulo.create(**campos)
                por_codigo.setdefault(codigo, None)
                por_nombre.setdefault(_normaliza_texto(nombre), None)
                resultado.creados.append(nombre)
            else:
                # Se relee con .dicts() a proposito: un Articulo tiene los
                # grupos, el proveedor y el IVA como OBJETOS relacionados y la
                # comparacion de "cambio" no podria hacerse. Ver
                # _mismo_que_ya_esta.
                guardado = Articulo.select().where(
                    Articulo.idarticulo == id_articulo).dicts().get()

                if guardado is not None and _mismo_que_ya_esta(guardado, campos):
                    resultado.sin_cambios.append(nombre)
                else:
                    existente = Articulo.get_by_id(id_articulo)
                    for campo, valor in campos.items():
                        setattr(existente, campo, valor)
                    existente.save()
                    resultado.actualizados.append(nombre)

        except FilaInvalida as error:
            resultado.filas_con_error.append(
                (error.numero or numero, error.motivo))
        except Exception as error:
            # Una fila mala no tira las otras 399. Se guarda el motivo y se
            # sigue; el operador lo ve en el resumen con el numero de fila.
            resultado.filas_con_error.append((numero, str(error)))

    return resultado
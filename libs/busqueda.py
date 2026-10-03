# coding=utf-8
"""Buscar texto en la base, igual en SQLite y en MySQL.

Por que existe
--------------
``campo.contains(texto)`` compila a ``LIKE '%texto%'``, y el ``LIKE`` no se
porta igual en los dos motores que usa la app:

- **SQLite** (el sandbox) ignora mayusculas para el alfabeto ASCII, pero las
  tildes no: buscar "municipio" encuentra "MUNICIPALIDAD", y buscar "cristian"
  NO encuentra "Cristián".
- **MySQL** (produccion) depende de la collation de la tabla. Con
  ``utf8mb4_general_ci`` pasa lo mismo: las tildes cuentan.

O sea que una busqueda que funciona en la maquina del desarrollador puede no
encontrar nada en la del cliente. En un sistema donde se factura, "no lo
encuentra" se lee como "el cliente no esta cargado", y ahi el operador da de
alta un cliente que ya existia.

La solucion sin tocar el esquema: el texto que se busca se pasa a una version
sin tildes y en minusculas, y del lado de la base se aplica lo mismo con
``REPLACE``, que existe en los dos motores.

Que se paga: un recorrido de la tabla, asi que esto es para texto. Los codigos,
los CUIT y los DNI se buscan con igualdad exacta, que si usa indice.
"""

import unicodedata

from peewee import fn

# Los caracteres que aparecen de verdad en nombres y razones sociales. La ñ se
# incluye: si no, buscar "municipalidad de la noria" no encontraria
# "Municipalidad de La Noria".
REEMPLAZOS = (
    ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u"),
    ("ñ", "n"), ("Á", "a"), ("É", "e"), ("Í", "i"), ("Ó", "o"), ("Ú", "u"),
    ("Ü", "u"), ("Ñ", "n"),
)


def normalizar(texto):
    """Minúsculas y sin tildes: 'Configuración' -> 'configuracion'."""
    descompuesto = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).strip()


def sin_tildes(campo):
    """La expresion de SQL que deja `campo` en minusculas y sin tildes.

    Solo para MySQL y SQLite, que son los dos motores con los que corre la app.
    """
    expresion = campo
    for con_tilde, sin_tilde in REEMPLAZOS:
        expresion = fn.REPLACE(expresion, con_tilde, sin_tilde)
    return fn.LOWER(expresion)


def contiene(campo, texto):
    """`campo` contiene `texto`, ignorando mayusculas y tildes.

    Un texto vacio devuelve la expresion que matchea todo, como hace
    ``campo.contains('')``. Quien use esto para acotar una lista tiene que
    decidir que hacer con el vacio antes: volcar los 5.000 clientes en una
    lista no es una busqueda, es una pantalla imposible de usar.
    """
    consulta = normalizar(texto)
    if not consulta:
        return campo.contains("")
    return sin_tildes(campo).contains(consulta)

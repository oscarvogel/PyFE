# coding=utf-8
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

#Modelo base del cual derivan todos los modelos del sistema

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2020 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.5"

from peewee import MySQLDatabase, Model, BooleanField, SqliteDatabase

from libs.Utiles import LeerIni

if LeerIni(clave='base') == 'sqlite':
    if LeerIni(clave='usa_nombre_db') == 'S':
        db = SqliteDatabase(f'{LeerIni("basedatos")}.db')
        print(f'Usando {LeerIni("basedatos")}')
    else:
        db = SqliteDatabase(f'sistema.db')
        print("Usando sistema.db")
else:
    # El password se resuelve aca, sin mostrar ningun dialogo: este modulo se
    # importa antes de que exista una QApplication. Si no esta disponible
    # (el usuario todavia no lo tipeo) queda vacio y la conexion falla con un
    # error claro, en vez de romper el arranque.
    from libs.secretos import resolver_password_base
    _password_base = resolver_password_base() or ''
    if not _password_base:
        print("Falta el password de la base. Se va a pedir al usuario.")
    db = MySQLDatabase(LeerIni("basedatos"), user=LeerIni("usuario"),
                       password=_password_base,
                   host=LeerIni("host"), port=3306)

class ModeloBase(Model):

    def __init__(self, *args, **kwargs):
        super(ModeloBase, self).__init__(*args, **kwargs)

    def getDb(self):
        return db

    def connect(self):
        db.connect(reuse_if_open=True)

    """A base model that will use our MySQL database"""
    class Meta:
        database = db


# Las formas en que un bit puede llegar. El CSV es la fuente de los maestros
# y ahi todo es TEXTO, asi que '1' es lo habitual y no un caso raro.
_BIT_VERDADEROS = ('1', 'true', 't', 's', 'si', 'sí', 'x', 'y')


def _a_bit(valor):
    """Normaliza a un booleano cualquier forma en que llegue un bit.

    Antes el codigo hacia `value == 1`, y en un CSV los valores son texto:
    '1' == 1 es False en Python. O sea que TODOS los bits de los CSV se
    guardaban en cero sin que nadie se enterara: cargar 15 filas y devolver
    15, como si hubiera ido bien.
    """
    if valor is None:
        return False
    if isinstance(valor, (bytes, bytearray)):
        # MySQL devuelve un BIT(1) como b'\x01' / b'\x00'.
        return any(valor)
    if isinstance(valor, str):
        return valor.strip().lower() in _BIT_VERDADEROS
    return bool(valor)


class BitBooleanField(BooleanField):
    field_type = 'Bit'

    def db_value(self, value):
        if isinstance(db, SqliteDatabase):
            return _a_bit(value)
        # En MySQL el valor pasaba tal cual. No se toca: no hay evidencia de
        # que ese camino este mal, y no se puede probar desde aca.
        return value

    def python_value(self, value):
        return _a_bit(value)
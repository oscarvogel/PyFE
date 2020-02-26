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
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"

from peewee import MySQLDatabase, Model, BooleanField, SqliteDatabase

from libs.Utiles import LeerIni, desencriptar

if LeerIni(clave='base') == 'sqlite':
    db = SqliteDatabase('sistema.db')
else:
    db = MySQLDatabase(LeerIni("basedatos"), user=LeerIni("usuario"),
                       password=desencriptar(LeerIni('password').encode(),LeerIni('key').encode()),
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


class BitBooleanField(BooleanField):
    field_type = 'Bit'

    def db_value(self, value):
        if isinstance(db, SqliteDatabase):
            return value == 1
        return value == b'\01'

    def python_value(self, value):
        if isinstance(db, SqliteDatabase):
            return value == 1
        return value == b'\01'
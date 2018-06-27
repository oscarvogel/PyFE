# coding=utf-8
from peewee import MySQLDatabase, Model, Field, BooleanField, SqliteDatabase

from libs.Utiles import LeerIni, desencriptar

if LeerIni(clave='base') == 'sqlite':
    db = SqliteDatabase('sistema.db')
else:
    db = MySQLDatabase(LeerIni("basedatos"), user=LeerIni("usuario"), password=desencriptar(LeerIni('password'),
                                                                                        LeerIni('key')),
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
        return value  == b'\01'

    def python_value(self, value):
        return value == b'\01'
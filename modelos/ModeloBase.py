# coding=utf-8
from peewee import MySQLDatabase, Model, Field

from libs.Utiles import LeerIni, desencriptar

mysql_db = MySQLDatabase(LeerIni("BaseDatos"), user=LeerIni("Usuario"), password=desencriptar(LeerIni('Password'),
                                                                                              LeerIni('Key')),
                         host=LeerIni("Host"), port=3306)

class ModeloBase(Model):

    def __init__(self, *args, **kwargs):
        super(ModeloBase, self).__init__(*args, **kwargs)

    def getDb(self):
        return mysql_db

    def connect(self):
        mysql_db.connect(reuse_if_open=True)

    """A base model that will use our MySQL database"""
    class Meta:
        database = mysql_db


class BitBooleanField(Field):
    field_type = 'BitBooleanField'

    def db_value(self, value):
        return value  == b'\01'

    def python_value(self, value):
        return value == b'\01'
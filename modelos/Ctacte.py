# coding=utf-8
from datetime import datetime

from peewee import AutoField, DateField, ForeignKeyField, DecimalField, CharField

from modelos.Cabfact import Cabfact
from modelos.ModeloBase import ModeloBase


class CtaCte(ModeloBase):

    idctacte = AutoField()
    fecha = DateField(default='0000-00-00')
    idfactura = ForeignKeyField(Cabfact)
    idrecibo = ForeignKeyField(Cabfact)
    monto = DecimalField(decimal_places=4, max_digits=12)
    usuario = CharField(default='', db_column='_usuario')
    fechagraba = DateField(default=datetime.now(), db_column='_fecha')
    hora = CharField(default=datetime.now().strftime('%H:%M:%S'), db_column='_hora')

# coding=utf-8
from peewee import AutoField, IntegerField, ForeignKeyField, DecimalField

from modelos.CabFacProv import CabFactProv
from modelos.ModeloBase import ModeloBase


class PercepDGR(ModeloBase):

    idpercepdgr = AutoField()
    codjur = IntegerField()
    idpcabecera = ForeignKeyField(CabFactProv, db_column='idpcabecera')
    monto = DecimalField(max_digits=12, decimal_places=4, default=0)

    class Meta:
        table_name = "percepdgr"
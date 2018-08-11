# coding=utf-8
from peewee import AutoField, ForeignKeyField, DecimalField, CharField

from modelos.CabFacProv import CabFactProv
from modelos.CentroCostos import CentroCosto
from modelos.ModeloBase import ModeloBase


class DetFactProv(ModeloBase):

    idpdetalle = AutoField(db_column='idpdetalle')
    idpcabecera = ForeignKeyField(CabFactProv, db_column='idpcabecera', default=1)
    idctrocosto = ForeignKeyField(CentroCosto, db_column='idctrocosto', default=1)
    iva = DecimalField(max_digits=6, decimal_places=2, default=0)
    neto = DecimalField(max_digits=12, decimal_places=4, default=0)
    detalle = CharField(max_length=50)
    descuento = DecimalField(max_digits=12, decimal_places=4, default=0)
    cantidad = DecimalField(max_digits=12, decimal_places=4, default=0)

    class Meta:
        table_name = "pdetalle"
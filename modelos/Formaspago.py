# coding=utf-8
from peewee import IntegerField, CharField, BitField, AutoField, DecimalField

from modelos.ModeloBase import ModeloBase, BitBooleanField


class Formapago(ModeloBase):

    idformapago = AutoField(db_column='idformapago')
    detalle = CharField(max_length=30, default='')
    ctacte = BitBooleanField(default=0)
    descuento = DecimalField(max_digits=12, decimal_places=2, default=0)
    recargo = DecimalField(max_digits=12, decimal_places=2, default=0)
    mensual = BitBooleanField(default=0)
    tarjeta = BitBooleanField(default=0)
    #ctacte = BitField()

    class Meta:
        table_name = 'formapago'
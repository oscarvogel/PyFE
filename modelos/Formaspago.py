# coding=utf-8
from peewee import IntegerField, CharField

from modelos.ModeloBase import ModeloBase, BitBooleanField


class Formapago(ModeloBase):

    idformapago = IntegerField(primary_key=True)
    detalle = CharField(max_length=30)
    ctacte = BitBooleanField()

    class Meta:
        table_name = 'formapago'
# coding=utf-8
from peewee import AutoField, CharField

from modelos.ModeloBase import ModeloBase, BitBooleanField


class Cajero(ModeloBase):

    idcajero = AutoField(primary_key=True)
    nombre = CharField(max_length=30)
    telefono = CharField(max_length=30)
    activo = BitBooleanField(db_column='activo')
# coding=utf-8
from peewee import IntegerField, CharField

from modelos.ModeloBase import ModeloBase


class Provincia(ModeloBase):

    codjur = IntegerField(primary_key=True, column_name='codjur')
    nombre = CharField(max_length=50, default='')

    class Meta:
        table_name = "provincias"
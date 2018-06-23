# coding=utf-8
from peewee import IntegerField, CharField

from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase


class Tipodoc(ModeloBase):
    codigo = IntegerField(primary_key=True)
    tipo = CharField(max_length=1)
    nombre = CharField(max_length=30)

    class Meta:
        table_name = 'tipodoc'


class Valida(Validaciones):
    modelo = Tipodoc
    cOrden = Tipodoc.nombre
    campoRetorno = Tipodoc.codigo
    campoNombre = Tipodoc.nombre
    campos = ['codigo','nombre']



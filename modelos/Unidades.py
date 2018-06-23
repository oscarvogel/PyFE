# coding=utf-8
from peewee import CharField

from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase


class Unidad(ModeloBase):
    unidad = CharField(primary_key=True, max_length=8)
    descripcion = CharField(max_length=30)

    class Meta:
        table_name = 'unimedi'


class Valida(Validaciones):
    modelo = Unidad
    cOrden = Unidad.descripcion
    campoRetorno = Unidad.unidad
    campoNombre = Unidad.descripcion
    campos = ['unidad', 'descripcion']

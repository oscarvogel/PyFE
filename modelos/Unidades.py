# coding=utf-8
from peewee import CharField

from libs.ComboBox import ComboSQL
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

class ComboUnidad(ComboSQL):
    model = Unidad
    cOrden = Unidad.descripcion
    campovalor = Unidad.unidad.name
    campo1 = Unidad.descripcion.name



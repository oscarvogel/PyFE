# coding=utf-8
from peewee import AutoField, CharField

from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase


class CentroCosto(ModeloBase):

    idctrocosto = AutoField(db_column='idctrocosto')
    nombre = CharField(max_length=100)

    class Meta:
        table_name = 'ctrocostos'

class Valida(Validaciones):
    modelo = CentroCosto
    cOrden = CentroCosto.nombre
    campoRetorno = CentroCosto.idctrocosto
    campoNombre = CentroCosto.nombre
    campos = ['idctrocosto', 'nombre']

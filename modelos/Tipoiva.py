# coding=utf-8
from peewee import IntegerField, CharField, DecimalField

from libs.ComboBox import ComboSQL
from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase


class Tipoiva(ModeloBase):
    codigo = CharField(max_length=2, primary_key=True)
    descrip = CharField(max_length=30)
    iva = DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        table_name = 'tipoiva'


class Valida(Validaciones):
    modelo = Tipoiva
    cOrden = Tipoiva.descrip
    campoRetorno = Tipoiva.codigo
    campoNombre = Tipoiva.descrip
    campos = ['codigo', 'descrip']

class ComboIVA(ComboSQL):
    model = Tipoiva
    cOrden = Tipoiva.descrip
    campovalor = 'codigo'
    campo1 = 'descrip'
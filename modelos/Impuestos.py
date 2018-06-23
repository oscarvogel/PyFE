# coding=utf-8
from peewee import IntegerField, CharField, DecimalField

from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase

class Impuesto(ModeloBase):

    idimpuesto = IntegerField(primary_key=True)
    detalle = CharField(max_length=30)
    porcentaje = DecimalField(max_digits=12, decimal_places=2)
    minimo = DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        table_name = "impuestos"

class Valida(Validaciones):
    modelo = Impuesto
    cOrden = Impuesto.detalle
    campoRetorno = Impuesto.idimpuesto
    campoNombre = Impuesto.detalle
    campos = ['idimpuesto', 'detalle']

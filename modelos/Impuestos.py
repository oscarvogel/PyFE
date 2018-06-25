# coding=utf-8
from peewee import IntegerField, CharField, DecimalField, AutoField

from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase

class Impuesto(ModeloBase):

    idimpuesto = AutoField()
    detalle = CharField(max_length=30, default='')
    porcentaje = DecimalField(max_digits=12, decimal_places=2, default=0)
    minimo = DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        table_name = "impuestos"

class Valida(Validaciones):
    modelo = Impuesto
    cOrden = Impuesto.detalle
    campoRetorno = Impuesto.idimpuesto
    campoNombre = Impuesto.detalle
    campos = ['idimpuesto', 'detalle']

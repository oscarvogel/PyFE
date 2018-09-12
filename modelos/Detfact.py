# coding=utf-8
from peewee import AutoField, ForeignKeyField, DecimalField, CharField

from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.ModeloBase import ModeloBase
from modelos.Tipoiva import Tipoiva
from modelos.Unidades import Unidad


class Detfact(ModeloBase):
    iddetfact = AutoField()
    idcabfact = ForeignKeyField(Cabfact, backref='cabfact', column_name='idcabfact')
    idarticulo = ForeignKeyField(Articulo, backref='articulo', column_name='idarticulo')
    cantidad = DecimalField(max_digits=12, decimal_places=4)
    unidad = ForeignKeyField(Unidad, column_name='unidad')
    costo = DecimalField(max_digits=12, decimal_places=4)
    precio = DecimalField(max_digits=12, decimal_places=4)
    tipoiva = ForeignKeyField(Tipoiva, backref='tipoiva', column_name='tipoiva')
    montoiva = DecimalField(max_digits=12, decimal_places=4)
    montodgr = DecimalField(max_digits=12, decimal_places=4)
    montomuni = DecimalField(max_digits=12, decimal_places=4)
    descad = CharField(max_length=200, default='')
    detalle = CharField(max_length=40, default='')
    descuento = DecimalField(max_digits=12, decimal_places=4)
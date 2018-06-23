# coding=utf-8
from peewee import AutoField, CharField, ForeignKeyField, DecimalField

from modelos.Grupos import Grupo
from modelos.ModeloBase import ModeloBase, BitBooleanField
from modelos.Proveedores import Proveedor
from modelos.Tipoiva import Tipoiva
from modelos.Unidades import Unidad


class Articulo(ModeloBase):
    idarticulo = AutoField()
    nombre = CharField(max_length=100)
    nombreticket = CharField(max_length=30)
    unidad = ForeignKeyField(Unidad, backref='unidad', column_name='unidad')
    grupo = ForeignKeyField(Grupo, backref='grupo', column_name='idgrupo')
    costo = DecimalField(max_digits=12, decimal_places=2)
    provppal = ForeignKeyField(Proveedor, backref='proveedor', column_name='provppal')
    tipoiva = ForeignKeyField(Tipoiva, backref='tipoiva', column_name='tipoiva')
    modificaprecios = BitBooleanField(default=False)
    preciopub = DecimalField(max_digits=12, decimal_places=4)

    class Meta:
        table_name = 'articulos'


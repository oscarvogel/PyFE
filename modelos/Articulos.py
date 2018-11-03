# coding=utf-8
from peewee import AutoField, CharField, ForeignKeyField, DecimalField

from modelos.Grupos import Grupo
from modelos.ModeloBase import ModeloBase, BitBooleanField
from modelos.Proveedores import Proveedor
from modelos.Tipoiva import Tipoiva
from modelos.Unidades import Unidad


class Articulo(ModeloBase):
    idarticulo = AutoField()
    nombre = CharField(max_length=100, default='')
    nombreticket = CharField(max_length=30, default='')
    unidad = ForeignKeyField(Unidad, column_name='unidad', related_name='articulo', default='UN')
    grupo = ForeignKeyField(Grupo, backref='grupo', column_name='idgrupo', default=1)
    costo = DecimalField(max_digits=12, decimal_places=2, default=1)
    provppal = ForeignKeyField(Proveedor, backref='proveedor', column_name='provppal', default=1)
    tipoiva = ForeignKeyField(Tipoiva, backref='tipoiva', column_name='tipoiva', default='01')
    modificaprecios = BitBooleanField(default=False)
    preciopub = DecimalField(max_digits=12, decimal_places=4, default=1)
    concepto = CharField(max_length=1, default='1')
    codbarra = CharField(max_length=20, default='', column_name='codbarraart')

    class Meta:
        table_name = 'articulos'


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
    unidad = ForeignKeyField(Unidad, column_name='unidad', backref='articulo', default='UN')
    grupo = ForeignKeyField(Grupo, backref='grupo', column_name='idgrupo', default=1)
    costo = DecimalField(max_digits=12, decimal_places=2, default=1)
    provppal = ForeignKeyField(Proveedor, backref='proveedor', column_name='provppal', default=1)
    tipoiva = ForeignKeyField(Tipoiva, backref='tipoiva', column_name='tipoiva', default='01')
    modificaprecios = BitBooleanField(default=False)
    preciopub = DecimalField(max_digits=12, decimal_places=4, default=1)
    concepto = CharField(max_length=1, default='1')
    codbarra = CharField(max_length=20, default='', column_name='codbarraart')

    # -- Stock ---------------------------------------------------------------
    # controlastock es el que decide si este articulo participa del control.
    # Viene en False a proposito y no derivado de 'concepto': en un mismo
    # catalogo conviven productos y servicios, pero tambien hay articulos de
    # consumo interno que no se inventan, y una regla que adivine va a
    # fallar en algun caso y nadie va a saber cual. Explicito, y si alguien
    # se olvida de marcar un producto, el reporte de Stock lo muestra como
    # "sin controlar" en vez de hacerlo desaparecer.
    #
    # NO hay columna de stock actual. El stock es la suma de los movimientos
    # (modelos/MovStock.py), y explicarlo en dos lineas aca es la unica
    # garantía de que nadie lo agrega Thinking of it as a cache.
    controlastock = BitBooleanField(default=False)
    stockminimo = DecimalField(max_digits=12, decimal_places=4, default=0)

    class Meta:
        table_name = 'articulos'


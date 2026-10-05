# coding=utf-8
from peewee import AutoField, ForeignKeyField, DecimalField, CharField

from modelos.Articulos import Articulo
from modelos.CabFacProv import CabFactProv
from modelos.CentroCostos import CentroCosto
from modelos.ModeloBase import ModeloBase


class DetFactProv(ModeloBase):

    idpdetalle = AutoField(column_name='idpdetalle')
    idpcabecera = ForeignKeyField(CabFactProv, column_name='idpcabecera', default=1)
    idctrocosto = ForeignKeyField(CentroCosto, column_name='idctrocosto', default=1)
    iva = DecimalField(max_digits=6, decimal_places=2, default=0)
    neto = DecimalField(max_digits=12, decimal_places=4, default=0)
    detalle = CharField(max_length=50)
    descuento = DecimalField(max_digits=12, decimal_places=4, default=0)
    cantidad = DecimalField(max_digits=12, decimal_places=4, default=0)

    # Que articulo del catalogo compro este renglon. Antes no existia: el
    # renglon de una factura de proveedor era solo un texto en 'detalle', y
    # sin esto la compra no puede mover el stock. Va en null porque las
    # facturas de proveedor que ya estan cargadas y las que se cargan sin
    # elegir articulo (gastos, servicios, impuestos) siguen siendo validas.
    idarticulo = ForeignKeyField(Articulo, backref='movstock_compra_detalle',
                                 column_name='idarticulo', null=True)

    class Meta:
        table_name = "pdetalle"
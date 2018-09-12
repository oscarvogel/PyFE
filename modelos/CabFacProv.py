# coding=utf-8
from datetime import datetime

from peewee import AutoField, DateField, ForeignKeyField, CharField, DecimalField

from modelos.ModeloBase import ModeloBase
from modelos.Proveedores import Proveedor
from modelos.Tipocomprobantes import TipoComprobante


class CabFactProv(ModeloBase):

    idpcabfact = AutoField()
    fecha = DateField(default=datetime.now().date())
    fechaem = DateField(default=datetime.now().date())
    idproveedor = ForeignKeyField(Proveedor, db_column='idproveedor')
    tipocomp = ForeignKeyField(TipoComprobante, db_column='tipocomp')
    numero = CharField(max_length=12, default='')
    neto = DecimalField(max_digits=12, decimal_places=4, default=0)
    iva = DecimalField(max_digits=12, decimal_places=4, default=0)
    percepciondgr = DecimalField(max_digits=12, decimal_places=4, default=0)
    impuestos = DecimalField(max_digits=12, decimal_places=4, default=0)
    percepcioniva = DecimalField(max_digits=12, decimal_places=4, default=0)
    exentos = DecimalField(max_digits=12, decimal_places=4, default=0)
    nogravados = DecimalField(max_digits=12, decimal_places=4, default=0)
    cai = CharField(max_length=14, default='')
    modocpte = CharField(max_length=4, default='')
    periodo = CharField(max_length=6, default='')

    class Meta:
        table_name = "pcabecera"
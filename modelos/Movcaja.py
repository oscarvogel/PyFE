# coding=utf-8
from datetime import datetime

from peewee import AutoField, DateField, ForeignKeyField, CharField, DecimalField, IntegerField

from modelos.ModeloBase import ModeloBase
from modelos.Tipocomprobantes import TipoComprobante


class MovCajaModel(ModeloBase):

    idmovcaja = AutoField()
    fecha = DateField(default="0000-00-00")
    idtipocomp = ForeignKeyField(TipoComprobante, default=0, db_column='idtipocomp')
    numcomp = CharField(max_length=12, default='000000000000')
    importe = DecimalField(max_digits=12, decimal_places=2, default=0)
    banco = IntegerField(default=0)
    sucursal = IntegerField(default=0)
    numche = CharField(max_length=15, default='')
    vence = DateField(default='0000-00-00')
    cuit = CharField(max_length=13, default='')
    estado = CharField(max_length=1, default='I')
    idcabfact = IntegerField(default=0)
    idproveedor = IntegerField(default=0)
    idcliente = IntegerField(default=0)
    usuario = CharField(max_length=30, default='', db_column='_usuario')
    fechagraba = DateField(default=datetime.now(), db_column='_fecha')
    hora = CharField(db_column='_hora', default='00:00:00')

    class Meta:
        table_name = 'movcaja'
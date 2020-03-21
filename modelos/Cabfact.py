# coding=utf-8
from datetime import date

from peewee import IntegerField, ForeignKeyField, DateField, CharField, DecimalField, TextField, AutoField

from modelos import Cajeros
from modelos.Cajeros import Cajero
from modelos.Clientes import Cliente
from modelos.Formaspago import Formapago
from modelos.ModeloBase import ModeloBase
from modelos.Tipocomprobantes import TipoComprobante
from modelos.Tiporesp import Tiporesp


class Cabfact(ModeloBase):

    idcabfact = AutoField()
    tipocomp = ForeignKeyField(TipoComprobante, backref='tipocomprobante', db_column='idTipoComp')
    cliente = ForeignKeyField(Cliente, backref='cliente', db_column='idCliente')
    fecha = DateField(default=date.today())
    numero = CharField(max_length=12)
    neto = DecimalField(max_digits=12, decimal_places=2, default=0)
    iva = DecimalField(max_digits=12, decimal_places=2, default=0)
    netoa = DecimalField(max_digits=12, decimal_places=2, default=0)
    netob = DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento = DecimalField(max_digits=12, decimal_places=2, default=0)
    recargo = DecimalField(max_digits=12, decimal_places=2, default=0)
    total = DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo = DecimalField(max_digits=12, decimal_places=2, default=0)
    tipoiva = ForeignKeyField(Tiporesp, backref='tiporesp', db_column='tipoiva', default=1)
    formapago = ForeignKeyField(Formapago, backref='formapago', db_column='idFormaPago', default=1)
    cuotapago = IntegerField(db_column='idCuotaPago', default=0)
    percepciondgr = DecimalField(max_digits=12, decimal_places=2, default=0)
    nombre = CharField(max_length=100)
    domicilio = CharField(max_length=100)
    obs = TextField(default='')
    cajero = ForeignKeyField(Cajero, backref='cajero', db_column='cajero', default=Cajeros.CAJERO_POR_DEFECTO)
    cae = CharField(max_length=20, default='')
    venccae = DateField(default='0000-00-00')
    concepto = CharField(max_length=1, default='')
    desde = DateField(default='0000-00-00')
    hasta = DateField(default='0000-00-00')

    class Meta:
        table_name = 'cabfact'
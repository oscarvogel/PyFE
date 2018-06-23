# coding=utf-8
from datetime import date

from peewee import IntegerField, ForeignKeyField, DateField, CharField, DecimalField, TextField, AutoField

from modelos.Cajeros import Cajero
from modelos.Clientes import Cliente
from modelos.Formaspago import Formapago
from modelos.ModeloBase import ModeloBase
from modelos.Tipocomprobantes import TipoComprobante
from modelos.Tipoiva import Tipoiva


class Cabfact(ModeloBase):

    idcabfact = AutoField()
    tipocomp = ForeignKeyField(TipoComprobante, backref='tipocomprobante', db_column='idTipoComp')
    cliente = ForeignKeyField(Cliente, backref='cliente', db_column='idCliente')
    fecha = DateField(default=date.today())
    numero = CharField(max_length=12)
    neto = DecimalField(max_digits=12, decimal_places=2)
    iva = DecimalField(max_digits=12, decimal_places=2)
    netoa = DecimalField(max_digits=12, decimal_places=2)
    netob = DecimalField(max_digits=12, decimal_places=2)
    descuento = DecimalField(max_digits=12, decimal_places=2)
    recargo = DecimalField(max_digits=12, decimal_places=2)
    total = DecimalField(max_digits=12, decimal_places=2)
    saldo = DecimalField(max_digits=12, decimal_places=2)
    tipoiva = ForeignKeyField(Tipoiva, backref='tipoiva', db_column='tipoiva', default=1)
    formapago = ForeignKeyField(Formapago, backref='formapago', db_column='idFormaPago', default=1)
    cuotapago = IntegerField(db_column='idCuotaPago', default=0)
    percepciondgr = DecimalField(max_digits=12, decimal_places=2, default=0)
    nombre = CharField(max_length=30)
    domicilio = CharField(max_length=30)
    obs = TextField(default='')
    cajero = ForeignKeyField(Cajero, backref='cajero', db_column='cajero')
    cae = CharField(max_length=20, default='')
    venccae = DateField()
    concepto = CharField(max_length=1, default='')

    class Meta:
        table_name = 'cabfact'
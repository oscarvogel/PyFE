# coding=utf-8
from datetime import date, datetime

import peewee
from peewee import IntegerField, ForeignKeyField, DateField, CharField, DecimalField, TextField, AutoField

from libs.Utiles import LeerIni
from modelos import Cajeros
from modelos.Cajeros import Cajero
from modelos.Clientes import Cliente
from modelos.Formaspago import Formapago
from modelos.ModeloBase import ModeloBase
from modelos.Remitos import Remito
from modelos.Tipocomprobantes import TipoComprobante
from modelos.Tiporesp import Tiporesp


class Cabfact(ModeloBase):

    idcabfact = AutoField()
    tipocomp = ForeignKeyField(TipoComprobante, backref='tipocomprobante', column_name='idTipoComp')
    cliente = ForeignKeyField(Cliente, backref='cliente', column_name='idCliente')
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
    tipoiva = ForeignKeyField(Tiporesp, backref='tiporesp', column_name='tipoiva', default=1)
    formapago = ForeignKeyField(Formapago, backref='formapago', column_name='idFormaPago', default=1)
    cuotapago = IntegerField(column_name='idCuotaPago', default=0)
    percepciondgr = DecimalField(max_digits=12, decimal_places=2, default=0)
    nombre = CharField(max_length=100)
    domicilio = CharField(max_length=100)
    obs = TextField(default='')
    cajero = ForeignKeyField(Cajero, backref='cajero', column_name='cajero', default=Cajeros.CAJERO_POR_DEFECTO)
    cae = CharField(max_length=20, default='')
    venccae = DateField(default='0000-00-00')
    concepto = CharField(max_length=1, default='')
    desde = DateField(default='0000-00-00')
    hasta = DateField(default='0000-00-00')

    # El remito que documento esta factura, si hubo. Es lo que evita que la
    # mercaderia se descuente dos veces: el remito descuenta al salir, y la
    # factura solo descuenta cuando este campo esta vacio. Antes de existir
    # esta columna, una venta con remito + factura no tenia forma de saber
    # que el STOCK ya habia bajado con el remito.
    idremito = ForeignKeyField(Remito, backref='facturas',
                               column_name='idremito', null=True)

    class Meta:
        table_name = 'cabfact'

    @classmethod
    def DatosAgrupadosPeriodo(cls, desde=datetime.now().date(), hasta=datetime.now().date()):

        total = peewee.fn.Sum(Cabfact.total).alias('total')
        anio = Cabfact.fecha.year
        mes = Cabfact.fecha.month

        datos = Cabfact.select(anio.alias('anio'), mes.alias('mes'), TipoComprobante.lado, total).join(TipoComprobante)\
            .where(Cabfact.fecha.between(
                lo=desde, hi=hasta
            ),TipoComprobante.exporta == True
        ).group_by(anio, mes, TipoComprobante.lado)

        return datos

# coding=utf-8
from peewee import AutoField, DecimalField, ForeignKeyField, IntegerField

from modelos.Formaspago import Formapago
from modelos.ModeloBase import BitBooleanField, ModeloBase


class CuotaPago(ModeloBase):
    """Un plan de cuotas de una forma de pago con tarjeta.

    Cada tarjeta define sus propios planes: VISA 1 pago 0%, 3 pagos 15%,
    6 pagos 25%. El recargo es % sobre el total y lo aplica
    `aplicar_forma_pago` igual que el recargo base de la forma (issue #9).
    Si la forma no tiene planes (o estan todos inactivos), vale el
    descuento/recargo de Formapago.
    """

    idcuota = AutoField(column_name='idcuota')
    formapago = ForeignKeyField(Formapago, backref='planes',
                                column_name='idformapago')
    cuotas = IntegerField(default=1)
    recargo = DecimalField(max_digits=12, decimal_places=2, default=0)
    activo = BitBooleanField(default=1)

    class Meta:
        table_name = 'cuotaspago'

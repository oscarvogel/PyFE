# coding=utf-8
from peewee import AutoField, ForeignKeyField, CharField

from modelos.Cabfact import Cabfact
from modelos.ModeloBase import ModeloBase
from modelos.Tipocomprobantes import TipoComprobante


class CpbteRel(ModeloBase):

    id = AutoField()
    idcabfact = ForeignKeyField(Cabfact, db_column='idcabfact')
    idtipocpbte = ForeignKeyField(TipoComprobante, db_column='idtipocpbte')
    numero = CharField(max_length=12)

    class Meta:
        table_name = "cpbterel"
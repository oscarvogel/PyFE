# coding=utf-8
from peewee import IntegerField, CharField

from libs.ComboBox import Combo
from modelos.ModeloBase import ModeloBase, BitBooleanField


class TipoComprobante(ModeloBase):
    codigo = IntegerField(primary_key=True)
    nombre = CharField(max_length=30)
    abreviatura = CharField(max_length=3, db_column='abr')
    lado = CharField(max_length=1, default='')
    exporta = BitBooleanField(default=0)

    class Meta:
        table_name = "tip_comp"

class ComboTipoComp(Combo):

    valores = None
    def __init__(self, *args, **kwargs):
        Combo.__init__(self, *args, **kwargs)
        if kwargs['tiporesp'] == 6:
            self.valores = {
                11:'Factura C',
                12:'Nota de debito C',
                13:'Nota de credito C'
            }
            self.CargaDatosValores(self.valores)
        else:
            self.valores = {
                1: 'Factura A',
                2: 'Nota de debito A',
                3: 'Nota de credito A',
                6: 'Factura B',
                7: 'Nota de debito B',
                8: 'Nota de credito B'
            }
            self.CargaDatosValores(self.valores)


# coding=utf-8
from peewee import IntegerField, CharField, AutoField

from libs.ComboBox import ComboSQL
from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase, BitBooleanField


class Tiporesp(ModeloBase):
    idtiporesp = AutoField()
    nombre = CharField(max_length=30, default='')
    discrimina = BitBooleanField(default=0)
    tipoiva = CharField(max_length=1, default='')
    obligacuit = BitBooleanField(default=0)
    factura = IntegerField()
    notacredito = IntegerField()
    notadebito = IntegerField()
    tipoivaepson = CharField(max_length=1, default='')
    condicion_iva_receptor_id = IntegerField(default=5)

class Valida(Validaciones):
    modelo = Tiporesp
    cOrden = Tiporesp.nombre
    campoRetorno = Tiporesp.idtiporesp
    campoNombre = Tiporesp.nombre
    campos = ['idtiporesp','nombre']


class Combo(ComboSQL):
    model = Tiporesp
    cOrden = Tiporesp.nombre
    campovalor = 'idtiporesp'
    campo1 = 'nombre'
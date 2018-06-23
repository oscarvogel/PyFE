# coding=utf-8
from peewee import IntegerField, CharField

from libs.ComboBox import ComboSQL
from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase


class Tiporesp(ModeloBase):
    idtiporesp = IntegerField(primary_key=True)
    nombre = CharField(max_length=30)

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
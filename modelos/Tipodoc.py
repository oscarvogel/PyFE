# coding=utf-8
from peewee import IntegerField, CharField, AutoField

from libs.ComboBox import ComboSQL
from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase


class Tipodoc(ModeloBase):
    codigo = IntegerField(primary_key=True)
    tipo = CharField(max_length=1, default=0)
    nombre = CharField(max_length=30)

    class Meta:
        table_name = 'tipodoc'


class Valida(Validaciones):
    modelo = Tipodoc
    cOrden = Tipodoc.nombre
    campoRetorno = Tipodoc.codigo
    campoNombre = Tipodoc.nombre
    campos = ['codigo','nombre']

class ComboTipoDoc(ComboSQL):
    model = Tipodoc
    cOrden = Tipodoc.nombre
    campovalor = Tipodoc.codigo.name
    campo1 = Tipodoc.nombre.name



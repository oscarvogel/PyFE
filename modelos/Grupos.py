# coding=utf-8
from peewee import CharField, AutoField, ForeignKeyField

from libs.ComboBox import ComboSQL
from libs.Validaciones import Validaciones
from modelos.Impuestos import Impuesto
from modelos.ModeloBase import ModeloBase

class Grupo(ModeloBase):
    idgrupo = AutoField(primary_key=True)
    nombre = CharField(max_length=30)
    impuesto = ForeignKeyField(Impuesto, default=1, db_column='impuesto')

    class Meta:
        table_name = 'grupos'


class Valida(Validaciones):
    modelo = Grupo
    cOrden = Grupo.nombre
    campoRetorno = Grupo.idgrupo
    campoNombre = Grupo.nombre
    campos = ['idgrupo', 'nombre']

class ComboGrupo(ComboSQL):
    model = Grupo
    cOrden = Grupo.nombre
    campovalor = Grupo.idgrupo.name
    campo1 = Grupo.nombre.name
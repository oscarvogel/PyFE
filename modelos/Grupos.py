# coding=utf-8
from peewee import CharField, AutoField

from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase

class Grupo(ModeloBase):
    idgrupo = AutoField(primary_key=True)
    nombre = CharField(max_length=30)

    class Meta:
        table_name = 'grupos'


class Valida(Validaciones):
    modelo = Grupo
    cOrden = Grupo.nombre
    campoRetorno = Grupo.idgrupo
    campoNombre = Grupo.nombre
    campos = ['idgrupo', 'nombre']

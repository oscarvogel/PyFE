# coding=utf-8
from peewee import AutoField, CharField

from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase


class Localidad(ModeloBase):

    idlocalidad = AutoField()
    nombre = CharField(max_length=50)
    provincia = CharField(max_length=50)
    nacion = CharField(max_length=50)

    class Meta:
        table_name = 'localidades'

class Valida(Validaciones):
    modelo = Localidad
    cOrden = Localidad.nombre
    campoRetorno = Localidad.idlocalidad
    campoNombre = Localidad.nombre
    campos = ['idlocalidad', 'nombre']

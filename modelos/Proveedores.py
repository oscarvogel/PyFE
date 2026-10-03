# coding=utf-8
from peewee import CharField, AutoField, ForeignKeyField

from libs.Validaciones import Validaciones
from modelos.Localidades import Localidad
from modelos.ModeloBase import ModeloBase
from modelos.Tiporesp import Tiporesp


class Proveedor(ModeloBase):
    idproveedor = AutoField(column_name='idproveedor')
    nombre = CharField(max_length=60, default='')
    domicilio = CharField(max_length=60, default='')
    telefono = CharField(max_length=60, default='')
    cuit = CharField(max_length=13, default='')
    tiporesp = ForeignKeyField(Tiporesp, column_name='tiporesp')
    idlocalidad = ForeignKeyField(Localidad, column_name='idLocalidad')

    class Meta:
        table_name = 'proveedores'


class Valida(Validaciones):
    modelo = Proveedor
    cOrden = Proveedor.nombre
    campoRetorno = Proveedor.idproveedor
    campoNombre = Proveedor.nombre
    campos = ['idproveedor', 'nombre']
    largo = 4

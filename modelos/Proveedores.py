# coding=utf-8
from peewee import CharField, AutoField

from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase

class Proveedor(ModeloBase):
    idproveedor = AutoField(primary_key=True)
    nombre = CharField(max_length=30)
    domicilio = CharField(max_length=30)
    telefono = CharField(max_length=30)
    cuit = CharField(max_length=13)

    class Meta:
        table_name = 'proveedores'


class Valida(Validaciones):
    modelo = Proveedor
    cOrden = Proveedor.nombre
    campoRetorno = Proveedor.idproveedor
    campoNombre = Proveedor.nombre
    campos = ['idproveedor', 'nombre']

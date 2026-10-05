# coding=utf-8
from peewee import CharField, AutoField, ForeignKeyField

from libs.ComboBox import ComboSQL
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

class ComboProveedor(ComboSQL):
    """El proveedor como desplegable, para elegir UNO de una lista corta.

    Este combo se usa donde el proveedor se elige de entre los que ya estan
    cargados, no donde se lo busca a mano. El ABM de Proveedores usa `Valida`
    (con F2 y busqueda incremental) porque ahi el catalogo es largo; aca la
    eleccion es de una vez y para toda una carga.
    """
    model = Proveedor
    cOrden = Proveedor.nombre
    campovalor = Proveedor.idproveedor.column_name
    campo1 = Proveedor.nombre.column_name

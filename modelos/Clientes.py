# coding=utf-8
from peewee import AutoField, CharField, IntegerField, ForeignKeyField

from libs.Validaciones import Validaciones
from modelos.Formaspago import Formapago
from modelos.Impuestos import Impuesto
from modelos.Localidades import Localidad
from modelos.ModeloBase import ModeloBase
from modelos.Tipodoc import Tipodoc
from modelos.Tiporesp import Tiporesp


class Cliente(ModeloBase):
    idcliente = AutoField()
    nombre = CharField(max_length=100)
    domicilio = CharField(max_length=100)
    telefono = CharField(max_length=100, default='')
    localidad = ForeignKeyField(Localidad, backref="localidad", db_column='idLocalidad')
    cuit = CharField(max_length=13, default='')
    dni = IntegerField(default=0)
    tipodocu = ForeignKeyField(Tipodoc, backref='tipodoc', db_column='tipodocu', default=0)
    tiporesp = ForeignKeyField(Tiporesp, backref='tiporesp', db_column='tiporesp', default=1)
    formapago = ForeignKeyField(Formapago, backref='formapago', db_column='formapago', default=1)
    percepcion = ForeignKeyField(Impuesto, backref='percepcion', db_column='percepcion', default=1)

    class Meta:
        table_name = 'clientes'

class Valida(Validaciones):
    modelo = Cliente
    cOrden = Cliente.nombre
    campoRetorno = Cliente.idcliente
    campoNombre = Cliente.nombre
    campos = ['idcliente', 'nombre']

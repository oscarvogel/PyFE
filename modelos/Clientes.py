# coding=utf-8
import peewee
from peewee import AutoField, CharField, IntegerField, ForeignKeyField, fn
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

class FichaCliente(ModeloBase):

    id = AutoField(primary_key=True)
    cliente = ForeignKeyField(Cliente, db_column='cliente')
    fecha = peewee.DateField()
    detalle = peewee.TextField()
    debe = peewee.DecimalField(max_digits=12, decimal_places=2, default=0)
    haber = peewee.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        table_name = 'ficha_cliente'
        
    @classmethod
    def calcular_saldo(cls, cliente_id, fecha_hasta):
        """
        Calcula la diferencia entre las sumas de 'debe' y 'haber' para un cliente
        hasta una fecha específica.

        :param cliente_id: ID del cliente.
        :param fecha_hasta: Fecha límite (incluida).
        :return: Diferencia entre 'debe' y 'haber'.
        """
        query = cls.select(
            fn.SUM(cls.debe).alias('total_debe'),
            fn.SUM(cls.haber).alias('total_haber')
        ).where(
            (cls.cliente == cliente_id) & (cls.fecha <= fecha_hasta)
        ).dicts().get()

        total_debe = query.get('total_debe') or 0
        total_haber = query.get('total_haber') or 0
        return total_debe - total_haber        
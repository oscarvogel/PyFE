# coding=utf-8
from peewee import AutoField, ForeignKeyField, CharField

from modelos.Clientes import Cliente
from modelos.ModeloBase import ModeloBase


class EmailCliente(ModeloBase):

    idemailcliente = AutoField(column_name='idemailcliente')
    idcliente = ForeignKeyField(Cliente, column_name='idcliente')
    email = CharField(max_length=200, default='')
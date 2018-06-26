# coding=utf-8
from peewee import AutoField, ForeignKeyField, CharField

from modelos.Clientes import Cliente
from modelos.ModeloBase import ModeloBase


class EmailCliente(ModeloBase):

    idemailcliente = AutoField(db_column='idemailcliente')
    idcliente = ForeignKeyField(Cliente, db_column='idcliente')
    email = CharField(max_length=200, default='')
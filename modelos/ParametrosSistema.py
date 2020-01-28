# coding=utf-8
import peewee

from modelos.ModeloBase import ModeloBase


class ParamSist(ModeloBase):

    id = peewee.AutoField()
    parametro = peewee.CharField(unique=True, max_length=100, default='')
    valor = peewee.CharField(max_length=100, default='')

    @classmethod
    def ObtenerParametro(cls, parametro=''):
        if not parametro:
            return  ''

        try:
            retorno = ParamSist.select().where(ParamSist.parametro == parametro).get()
            valor = retorno.valor
        except ParamSist.DoesNotExist:
            param = ParamSist()
            param.parametro = parametro
            param.valor = ''
            param.save()
            valor = ''

        return valor

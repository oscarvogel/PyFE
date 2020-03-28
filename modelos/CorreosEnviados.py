from datetime import datetime

import peewee

from modelos.ModeloBase import ModeloBase


class CorreoEnviado(ModeloBase):

    id = peewee.AutoField()
    fecha_hora = peewee.DateTimeField(default=datetime.now())
    de = peewee.CharField(max_length=100)
    para = peewee.TextField(default='')
    cc = peewee.TextField(default='')
    cco = peewee.TextField(default='')
    asunto = peewee.CharField(max_length=250, default='')
    adjuntos = peewee.TextField(default='')
    mensaje = peewee.TextField(default='')

    class Meta:
        table_name = 'correos_enviados'
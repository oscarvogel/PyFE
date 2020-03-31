import peewee

from modelos.ModeloBase import ModeloBase


class CategoriaMono(ModeloBase):

    categoria = peewee.CharField(max_length=1, default='', primary_key=True)
    sup_afectada = peewee.IntegerField(default=0, verbose_name="Sup. Afectda")
    energia_electrica = peewee.IntegerField(default=0, verbose_name="Energia Electrica")
    alquileres = peewee.DecimalField(max_digits=12, decimal_places=2)
    imp_cosas_muebles = peewee.DecimalField(max_digits=12, decimal_places=2, verbose_name="Imp Cosas Muebles")
    imp_servicio = peewee.DecimalField(max_digits=12, decimal_places=2, verbose_name="Imp Servicio")
    sipa = peewee.DecimalField(max_digits=12, decimal_places=2)
    obra_social = peewee.DecimalField(max_digits=12, decimal_places=2, verbose_name="Obra social")


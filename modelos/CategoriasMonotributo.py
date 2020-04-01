import peewee

from libs.ComboBox import ComboSQL
from modelos.ModeloBase import ModeloBase


class CategoriaMono(ModeloBase):

    categoria = peewee.CharField(max_length=1, default='', primary_key=True)
    ing_brutos = peewee.DecimalField(max_digits=12, decimal_places=2, verbose_name="Ingresos brutos")
    sup_afectada = peewee.IntegerField(default=0, verbose_name="Sup. Afectda")
    energia_electrica = peewee.IntegerField(default=0, verbose_name="Energia Electrica")
    alquileres = peewee.DecimalField(max_digits=12, decimal_places=2)
    imp_cosas_muebles = peewee.DecimalField(max_digits=12, decimal_places=2, verbose_name="Imp Cosas Muebles")
    imp_servicio = peewee.DecimalField(max_digits=12, decimal_places=2, verbose_name="Imp Servicio")
    sipa = peewee.DecimalField(max_digits=12, decimal_places=2)
    obra_social = peewee.DecimalField(max_digits=12, decimal_places=2, verbose_name="Obra social")

    @classmethod
    def CategoriaMonto(cls, monto=0):

        try:
            datos = CategoriaMono.get(CategoriaMono.ing_brutos > monto)
        except:
            datos = None

        return datos

class ComboCategoriaMono(ComboSQL):

    model = CategoriaMono
    cOrden = CategoriaMono.categoria
    campovalor = CategoriaMono.categoria.name
    campo1 = CategoriaMono.categoria.name


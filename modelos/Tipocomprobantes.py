# coding=utf-8
from peewee import IntegerField, CharField

from libs.ComboBox import Combo
from libs.Validaciones import Validaciones
from modelos.ModeloBase import ModeloBase, BitBooleanField
from vistas.Busqueda import UiBusqueda

CODIGO_RECIBO = 42
FORMA_PAGO = {
    'Contado':1,
    'Cta Cte':2
}

class TipoComprobante(ModeloBase):
    codigo = IntegerField(primary_key=True, db_column='codigo')
    nombre = CharField(max_length=30)
    abreviatura = CharField(max_length=3, db_column='abr')
    lado = CharField(max_length=1, default='')
    exporta = BitBooleanField(default=0)
    ultcomp = IntegerField(default=0)

    class Meta:
        table_name = "tip_comp"

    def SiguienteNumero(self, tipocomp=0):
        tipo = self.get_by_id(tipocomp)
        retorno = tipo.ultcomp + 1
        tipo.ultcomp = retorno
        tipo.save()
        return retorno

class ComboTipoComp(Combo):

    valores = None
    def __init__(self, *args, **kwargs):
        Combo.__init__(self, *args, **kwargs)
        if kwargs['tiporesp'] == 6:
            self.valores = {
                11:'Factura C',
                12:'Nota de debito C',
                13:'Nota de credito C'
            }
            self.CargaDatosValores(self.valores)
        else:
            self.valores = {
                1: 'Factura A',
                2: 'Nota de debito A',
                3: 'Nota de credito A',
                6: 'Factura B',
                7: 'Nota de debito B',
                8: 'Nota de credito B'
            }
            self.CargaDatosValores(self.valores)

class Busqueda(UiBusqueda):
    modelo = TipoComprobante #modelo sobre la que se realiza la busqueda
    cOrden = "nombre" #orden de busqueda
    limite = 100 #maximo registros a mostrar
    campos = ["codigo", "nombre"] #campos a mostrar
    campoBusqueda = TipoComprobante.nombre #campo sobre el cual realizar la busqueda
    campoRetorno = TipoComprobante.codigo #campo del cual obtiene el dato para retornar el codigo/valor
    campoRetornoDetalle = TipoComprobante.nombre #campo que retorna el detalle


class Valida(Validaciones):
    modelo = TipoComprobante
    cOrden = TipoComprobante.nombre
    campoRetorno = TipoComprobante.codigo
    campoNombre = TipoComprobante.nombre
    campos = ['codigo', 'nombre']
    largo = 2

    def valida(self):
        if not self.text():
            return

        self.setText(str(self.text()).zfill(self.largo))
        codigo = str(self.text())

        data = None
        try:
            data = self.modelo.select().where(TipoComprobante.codigo == codigo).get()
            if data:
                self.valido = True
                self.setStyleSheet("background-color: Dodgerblue")
                self.cursor = data
                if self.widgetNombre:
                    self.widgetNombre.setText(data.nombre.strip())
            else:
                self.valido = False
                self.setStyleSheet("background-color: yellow")
                #Ventanas.showAlert("Error", "Codigo no encontrado en el sistema")
        except TipoComprobante.DoesNotExist:
            self.setStyleSheet("background-color: yellow")
        return data
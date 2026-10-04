# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Fechas import Fecha
from libs.Formulario import Formulario
from libs.Grillas import Grilla
from libs.Utiles import imagen, icono
from modelos import Clientes


class ReImprimeRemitoView(Formulario):
    """La pantalla de remitos es propia, no la de facturas reusada.

    Antes el controlador de remitos se construia con `ReImprimeFacturaView()`, y
    por eso "Reimprimir remito" abria una ventana titulada "Reimpresion de
    facturas" con un boton de enviar por correo que no tiene a quien mandarle:
    un remito no se manda, se imprime.
    """

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Reimpresión de remitos")
        self.verticalLayoutDatos = QVBoxLayout(Form)

        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.verticalLayoutDatos.addWidget(self.lblTitulo)
        self.layoutCliente = self.ArmaEntrada('cliente', control=Clientes.Valida())
        self.lblNombreCliente = Etiqueta()
        self.controles['cliente'].widgetNombre = self.lblNombreCliente
        self.layoutCliente.addWidget(self.lblNombreCliente)
        self.ArmaEntrada(boxlayout=self.layoutCliente, nombre='fecha', control=Fecha())
        self.controles['fecha'].setFecha(-30)
        self.gridDatos = Grilla()
        self.gridDatos.enabled = True
        self.gridDatos.textoVacio = "No hay remitos de este período"
        # 'idcabecera' es el idremito: lo usa el boton Imprimir para recuperar
        # el remito. Va en la fila, no a la vista.
        cabeceras = [
            'Fecha', 'Cliente', 'Remito', 'Total', 'idcabecera'
        ]
        self.verticalLayoutDatos.addWidget(self.gridDatos)
        self.gridDatos.ArmaCabeceras(cabeceras=cabeceras)
        self.gridDatos.columnasOcultas = [4]
        self.gridDatos.OcultaColumnas()
        self.layoutBotones = QHBoxLayout()
        self.btnImprimir = Boton(texto="Imprimir", imagen=icono('imprimir'))
        self.btnCargar = Boton(texto="Cargar", imagen=icono('buscar'))
        self.btnCerrar = BotonCerrarFormulario()
        self.layoutBotones.addWidget(self.btnCargar)
        self.layoutBotones.addWidget(self.btnImprimir)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.verticalLayoutDatos.addLayout(self.layoutBotones)

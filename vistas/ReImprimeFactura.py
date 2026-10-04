# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Fechas import Fecha, inicio_del_anio
from libs.Formulario import Formulario
from libs.Grillas import Grilla
from libs.Utiles import imagen, icono
from modelos import Clientes


class ReImprimeFacturaView(Formulario):

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Reimpresión de facturas")
        self.verticalLayoutDatos = QVBoxLayout(Form)

        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.verticalLayoutDatos.addWidget(self.lblTitulo)
        self.layoutCliente = self.ArmaEntrada('cliente',control=Clientes.Valida())
        self.lblNombreCliente = Etiqueta()
        self.controles['cliente'].widgetNombre = self.lblNombreCliente
        self.layoutCliente.addWidget(self.lblNombreCliente)
        self.ArmaEntrada(boxlayout=self.layoutCliente, nombre='fecha',
                         texto='Desde', control=Fecha())
        self.controles['fecha'].setFecha(inicio_del_anio())
        self.controles['fecha'].setToolTip(
            "Se listan los comprobantes desde esta fecha hasta hoy.")
        self.gridDatos = Grilla()
        self.gridDatos.enabled = True
        self.gridDatos.textoVacio = "No hay comprobantes de este período"
        # Las dos ultimas son las que usa el boton Imprimir para recuperar el
        # comprobante y el de correo para saber a quien mandarselo: hacen
        # falta en la fila, no a la vista. Escondidas liberan el ancho que se
        # iba en un nombre de campo de la base.
        cabeceras = [
            'Fecha', 'Cliente', 'Comprobante', 'Total', 'idcabecera', 'idcliente'
        ]
        self.verticalLayoutDatos.addWidget(self.gridDatos)
        self.gridDatos.ArmaCabeceras(cabeceras=cabeceras)
        self.gridDatos.columnasOcultas = [4, 5]
        self.gridDatos.OcultaColumnas()
        self.layoutBotones = QHBoxLayout()
        self.btnImprimir = Boton(texto="Imprimir", imagen=icono('imprimir'))
        self.btnCargar = Boton(texto="Cargar", imagen=icono('buscar'))
        self.envioCorreo = Boton(texto="Enviar por correo", imagen=icono('email'))
        self.btnCerrar = BotonCerrarFormulario()
        self.layoutBotones.addWidget(self.btnCargar)
        self.layoutBotones.addWidget(self.btnImprimir)
        self.layoutBotones.addWidget(self.envioCorreo)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.verticalLayoutDatos.addLayout(self.layoutBotones)

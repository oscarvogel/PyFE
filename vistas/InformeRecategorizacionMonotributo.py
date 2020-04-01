from datetime import datetime

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout

from libs.BarraProgreso import Avance
from libs.Botones import Boton, BotonCerrarFormulario
from libs.ComboBox import ComboPeriodoMonotributo, ComboActividadMono
from libs.Etiquetas import Etiqueta
from libs.GroupBox import Agrupacion
from libs.Spinner import Periodo, Spinner
from libs.Utiles import imagen
from modelos.CategoriasMonotributo import ComboCategoriaMono
from vistas.VistaBase import VistaBase


class InfRecMonotributoView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Informe de recategorizacion de monotributo")
        self.resize(650, 150)
        layoutPpal = QVBoxLayout(Form)
        self.avance = Avance()
        layoutPpal.addWidget(self.avance)

        agrupacion_datos = Agrupacion(titulo="Datos")
        layoutDatos = QGridLayout()
        lblCategoria = Etiqueta(texto="Categoria actual")
        self.cboCategoriaMono = ComboCategoriaMono()
        layoutDatos.addWidget(lblCategoria, 0, 0)
        layoutDatos.addWidget(self.cboCategoriaMono, 0, 1)
        lblCantidadAdherentesOS = Etiqueta(texto="Cantidad de adheretentes OS")
        self.spnCantAdhOS = Spinner(decimales=0)
        layoutDatos.addWidget(lblCantidadAdherentesOS, 0, 2)
        layoutDatos.addWidget(self.spnCantAdhOS, 0, 3)

        lblActividad = Etiqueta(texto="Actividad")
        self.cboActividad = ComboActividadMono()
        layoutDatos.addWidget(lblActividad, 1, 0)
        layoutDatos.addWidget(self.cboActividad, 1, 1)
        agrupacion_datos.setLayout(layoutDatos)
        layoutPpal.addWidget(agrupacion_datos)

        layoutPeriodo = QHBoxLayout()
        lblAnio = Etiqueta(texto=u"Año")
        self.spnAnio = Spinner(decimales=0)
        self.spnAnio.setText(datetime.now().date().year)
        layoutPeriodo.addWidget(lblAnio)
        layoutPeriodo.addWidget(self.spnAnio)
        lblPeriodo = Etiqueta(texto="Periodo")
        self.cboPeriodo = ComboPeriodoMonotributo()
        layoutPeriodo.addWidget(lblPeriodo)
        layoutPeriodo.addWidget(self.cboPeriodo)
        layoutPpal.addLayout(layoutPeriodo)

        layoutBotones = QHBoxLayout()
        self.btnExcel = Boton(texto="&Excel", imagen=imagen("excel.png"))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnExcel)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)